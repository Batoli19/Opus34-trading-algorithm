import logging
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("RISK")


@dataclass
class TradeRecord:
    ticket: int
    symbol: str
    direction: str
    volume: float
    entry: float
    sl: float
    tp: float
    open_time: datetime
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    pnl: float = 0.0
    setup_type: str = ""
    setup_id: str = ""          # ✅ NEW (unique identifier for setup)
    reason: str = ""


class RiskManager:
    def __init__(self, config: dict):
        self.cfg = config["risk"]
        self.journal: list[TradeRecord] = []

        self._today: date = datetime.utcnow().date()
        self._daily_pnl: float = 0.0
        self._daily_trades: int = 0

        # ✅ NEW: locks / gating
        self._pause_until: Optional[datetime] = None
        self._lock_reason: str = ""
        self._require_new_setup: bool = False
        self._blocked_setup_id: str = ""   # the setup_id we refuse to trade again
        self._last_seen_setup_id: str = "" # updated whenever can_trade is called with setup_id

        # Target stop sizes (informational only; we DO NOT distort risk for it)
        self.target_stop_pips = {
            "XAUUSD": 5,
            "EURUSD": 5,
            "GBPUSD": 5,
            "AUDUSD": 5,
            "USDJPY": 5,
            "US30": 8,
            "NAS100": 8,
            "SPX500": 8,
        }

    # ── Daily reset / trade permission ────────────────────────────────────────

    def _check_reset(self):
        today = datetime.utcnow().date()
        if today != self._today:
            logger.info(
                f"📅  New day {today} — resetting daily counters. "
                f"Yesterday P&L: {self._daily_pnl:+.2f}"
            )
            self._today = today
            self._daily_pnl = 0.0
            self._daily_trades = 0

            # ✅ reset locks each new day
            self._pause_until = None
            self._lock_reason = ""
            self._require_new_setup = False
            self._blocked_setup_id = ""
            self._last_seen_setup_id = ""

    def set_cooldown(
        self,
        minutes: int,
        reason: str,
        require_new_setup: bool = True,
        blocked_setup_id: str = "",
    ):
        """
        ✅ Call this when you "secure basket profit" or any protective close happens.
        - minutes: cooldown duration
        - require_new_setup: if True, bot must see a NEW setup_id before trading
        - blocked_setup_id: the setup_id that triggered the lock (to prevent instant re-entry)
        """
        now = datetime.utcnow()
        self._pause_until = now + timedelta(minutes=max(0, int(minutes)))
        self._lock_reason = reason
        self._require_new_setup = bool(require_new_setup)
        self._blocked_setup_id = blocked_setup_id or self._blocked_setup_id

        logger.warning(
            f"⏸️  Trading paused until {self._pause_until.isoformat()} | "
            f"Reason: {reason} | Require new setup: {self._require_new_setup} | "
            f"Blocked setup_id: {self._blocked_setup_id or '—'}"
        )

    def clear_lock(self):
        """Manual override if you ever need it."""
        self._pause_until = None
        self._lock_reason = ""
        self._require_new_setup = False
        self._blocked_setup_id = ""

    def can_trade(
        self,
        open_positions: list,
        account_balance: float,
        setup_id: str = "",
    ) -> tuple[bool, str]:
        self._check_reset()

        # Track last seen setup_id for diagnostics
        if setup_id:
            self._last_seen_setup_id = setup_id

        # ✅ NEW: Daily profit cap
        daily_profit_target = float(self.cfg.get("daily_profit_target_usd", 1000.0))
        if daily_profit_target > 0 and self._daily_pnl >= daily_profit_target:
            return False, f"Daily profit target hit: {self._daily_pnl:+.2f} / {daily_profit_target:+.2f}"

        # ✅ NEW: Cooldown lock
        now = datetime.utcnow()
        if self._pause_until is not None and now < self._pause_until:
            return False, f"Cooldown active until {self._pause_until.isoformat()} ({self._lock_reason})"

        # ✅ NEW: Require a new setup after lock
        if self._require_new_setup and self._blocked_setup_id:
            if setup_id and setup_id == self._blocked_setup_id:
                return False, "Waiting for a NEW setup (same setup_id blocked after protection close)"

            # If we get here and setup_id is different, unlock the requirement.
            if setup_id and setup_id != self._blocked_setup_id:
                logger.info(f"🔓  New setup detected ({setup_id}) — lifting new-setup gate.")
                self._require_new_setup = False
                self._blocked_setup_id = ""

        # Existing limits
        if len(open_positions) >= self.cfg["max_open_trades"]:
            return False, f"Max open trades reached ({self.cfg['max_open_trades']})"

        if self._daily_trades >= self.cfg["max_daily_trades"]:
            return False, f"Max daily trades reached ({self.cfg['max_daily_trades']})"

        max_loss = account_balance * (self.cfg["max_daily_loss_pct"] / 100.0)
        if self._daily_pnl <= -max_loss:
            return False, (
                f"Daily loss limit hit: {self._daily_pnl:.2f} / "
                f"-{max_loss:.2f} ({self.cfg['max_daily_loss_pct']}%)"
            )

        return True, "OK"

    # ── Lot sizing (unchanged) ───────────────────────────────────────────────

    def calculate_lot_size(
        self,
        symbol: str,
        entry: float,
        sl: float,
        tp: float,
        account_balance: float,
        confidence: float = 0.75,
        in_kill_zone: bool = False,
        pip_value_per_lot: Optional[float] = None,
        volume_min: Optional[float] = None,
        volume_max: Optional[float] = None,
        volume_step: Optional[float] = None,
    ) -> float:
        pip_size = self._get_pip_size(symbol)
        stop_pips = abs(entry - sl) / pip_size

        if stop_pips <= 0:
            logger.warning(f"{symbol}: Invalid stop distance (stop_pips={stop_pips})")
            return 0.0

        base_risk_pct = float(self.cfg.get("risk_per_trade_pct", 1.0))
        confidence_scaled = base_risk_pct * (0.8 + confidence * 0.4)
        risk_amount = account_balance * (confidence_scaled / 100.0)

        if in_kill_zone:
            kz_mult = float(self.cfg.get("kill_zone_risk_mult", 1.3))
            risk_amount *= kz_mult
            logger.info(f"🎯  Kill zone active — risk increased to ${risk_amount:.2f} (x{kz_mult:.2f})")

        pip_value = float(pip_value_per_lot or 10.0)
        if pip_value <= 0:
            logger.warning(f"{symbol}: Invalid pip_value_per_lot={pip_value}")
            return 0.0

        raw_lot = risk_amount / (stop_pips * pip_value)
        if raw_lot <= 0:
            return 0.0

        lot = raw_lot

        if volume_max is not None:
            lot = min(lot, float(volume_max))

        lot = self._round_lot_to_step(lot, volume_step)

        if volume_min is not None and lot < float(volume_min):
            min_lot = self._round_lot_to_step(float(volume_min), volume_step)
            min_risk = min_lot * stop_pips * pip_value
            if min_risk > risk_amount * 1.01:
                logger.warning(
                    f"⛔  {symbol}: Broker min lot {min_lot} would risk ${min_risk:.2f} "
                    f"> allowed ${risk_amount:.2f}. Skipping trade."
                )
                return 0.0
            lot = min_lot

        lot = max(0.0, lot)

        final_risk = lot * stop_pips * pip_value
        target_stop = self.target_stop_pips.get(symbol, None)
        extra = f" (target stop {target_stop}p)" if target_stop is not None else ""

        logger.info(
            f"💰  {symbol} | Stop: {stop_pips:.1f}p{extra} | Lot: {lot:.2f} | "
            f"Risk: ${final_risk:.2f} (target ${risk_amount:.2f}) | Conf: {confidence:.0%}"
        )

        if target_stop and stop_pips > target_stop * 1.5:
            logger.warning(f"⚠️  {symbol}: Stop wider than target ({stop_pips:.1f}p vs {target_stop}p)")

        return lot

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_pip_size(self, symbol: str) -> float:
        s = symbol.upper()
        if "JPY" in s:
            return 0.01
        if s in ("US30", "NAS100", "SPX500"):
            return 1.0
        if "XAU" in s:
            return 0.1
        return 0.0001

    def _round_lot_to_step(self, lot: float, step: Optional[float]) -> float:
        if lot <= 0:
            return 0.0

        if step is None or step <= 0:
            return float(int(lot * 100)) / 100.0

        step = float(step)
        steps = int(lot / step)
        return steps * step

    # ── Journal / stats ──────────────────────────────────────────────────────

    def record_open(self, trade: dict, setup_type: str = "", setup_id: str = "", reason: str = ""):
        self._daily_trades += 1
        record = TradeRecord(
            ticket=trade["ticket"],
            symbol=trade["symbol"],
            direction=trade["type"],
            volume=trade["volume"],
            entry=trade["price"],
            sl=trade["sl"],
            tp=trade["tp"],
            open_time=trade["time"],
            setup_type=setup_type,
            setup_id=setup_id,
            reason=reason,
        )
        self.journal.append(record)
        logger.info(
            f"📝  Trade #{trade['ticket']} recorded | {trade['type']} {trade['volume']} {trade['symbol']} "
            f"| setup_id={setup_id or '—'}"
        )

    def record_close(self, ticket: int, close_price: float, pnl: float):
        self._daily_pnl += pnl
        for r in self.journal:
            if r.ticket == ticket:
                r.close_time = datetime.utcnow()
                r.close_price = close_price
                r.pnl = pnl
                emoji = "✅" if pnl > 0 else "❌"
                logger.info(
                    f"{emoji}  Trade #{ticket} closed | P&L: {pnl:+.2f} | "
                    f"Daily P&L: {self._daily_pnl:+.2f}"
                )
                return

    def get_stats(self) -> dict:
        closed = [r for r in self.journal if r.close_time is not None]
        if not closed:
            return {
                "trades": 0,
                "winrate": 0,
                "total_pnl": 0,
                "daily_pnl": self._daily_pnl,
                "daily_trades": self._daily_trades,
            }

        wins = [r for r in closed if r.pnl > 0]
        losses = [r for r in closed if r.pnl < 0]
        total = sum(r.pnl for r in closed)

        avg_win = sum(r.pnl for r in wins) / len(wins) if wins else 0
        avg_loss = sum(r.pnl for r in losses) / len(losses) if losses else 0
        expectancy = (
            (len(wins) / len(closed) * avg_win) +
            (len(losses) / len(closed) * avg_loss)
        ) if closed else 0

        return {
            "trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "winrate": round(len(wins) / len(closed) * 100, 1),
            "total_pnl": round(total, 2),
            "daily_pnl": round(self._daily_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 2),
            "daily_trades": self._daily_trades,
        }
