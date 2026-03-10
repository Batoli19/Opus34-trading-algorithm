import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple


BACKTEST_RESULTS_DEFAULT = Path(__file__).resolve().parents[1] / "backtest_results.csv"
BACKTEST_DATA_DIR_DEFAULT = Path(__file__).resolve().parents[1] / "backtest_data"


def _parse_dt(s: str) -> datetime:
    # backtest_results.csv uses "YYYY-MM-DD HH:MM"
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")


def _ym(dt: datetime) -> Tuple[int, int]:
    return dt.year, dt.month


def pip_size(symbol: str) -> float:
    s = symbol.upper()
    if s.endswith("JPY"):
        return 0.01
    if s == "XAUUSD":
        return 0.1
    return 0.0001


def quote_ccy(symbol: str) -> str:
    s = symbol.upper()
    if len(s) == 6:
        return s[3:]
    if s == "XAUUSD":
        return "USD"
    return "USD"


def base_ccy(symbol: str) -> str:
    s = symbol.upper()
    if len(s) == 6:
        return s[:3]
    if s == "XAUUSD":
        return "XAU"
    return "USD"


@dataclass(frozen=True)
class TradeRow:
    symbol: str
    entry_time: datetime
    entry_price: float
    sl_price: float
    pnl_pips: float
    rr_achieved: float
    exit_reason: str

    @property
    def risk_pips(self) -> float:
        return abs(self.entry_price - self.sl_price) / pip_size(self.symbol)


def _load_fx_close_map(csv_path: Path) -> Dict[datetime, float]:
    """
    Load OHLCV CSVs from backtest_data into a datetime->close map (UTC-naive).
    backtest_data/* uses 'time' in '%Y-%m-%d %H:%M:%S'.
    """
    out: Dict[datetime, float] = {}
    if not csv_path.exists():
        return out
    with csv_path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            t = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S")
            out[t] = float(row["close"])
    return out


def _nearest_rate(rate_map: Dict[datetime, float], t: datetime) -> Optional[float]:
    """
    Find an exact timestamp match first, otherwise fall back to nearest earlier minute.
    backtest_results times are minute precision; backtest_data is second precision.
    """
    if not rate_map:
        return None
    if t in rate_map:
        return rate_map[t]
    # try with ":00" seconds
    t0 = t.replace(second=0)
    if t0 in rate_map:
        return rate_map[t0]
    # fallback: walk back up to 60 minutes
    for i in range(1, 61):
        tt = t0.replace(minute=t0.minute)  # no-op; keep clarity
        tt = t0 - __import__("datetime").timedelta(minutes=i)
        if tt in rate_map:
            return rate_map[tt]
    return None


def pip_value_usd_per_lot(symbol: str, entry_time: datetime, entry_price: float, data_dir: Path) -> float:
    """
    Approximate pip value per 1.0 lot in USD, assuming:
    - FX contract size = 100,000 base units
    - Gold (XAUUSD) contract size = 100 oz, pip_size=0.1
    - Account currency = USD
    """
    s = symbol.upper()
    if s == "XAUUSD":
        contract = 100.0
        return contract * pip_size(s)  # quoted in USD

    contract = 100_000.0
    pv_quote = contract * pip_size(s)  # value per pip in QUOTE ccy
    q = quote_ccy(s)

    if q == "USD":
        return pv_quote

    # If quote is JPY/CHF/etc convert quote->USD using a rate.
    # Prefer USD{quote} if available (e.g., USDJPY, USDCHF).
    pair1 = f"USD{q}"
    pair2 = f"{q}USD"

    if s == pair1:
        # USDJPY: quote->USD conversion uses the symbol price itself
        rate = entry_price
        return pv_quote / rate

    # Try to load USD{quote} close series (M5 preferred, then M15).
    for tf in ("M5", "M15", "M1", "H1"):
        rate_map = _load_fx_close_map(data_dir / f"{pair1}_{tf}.csv")
        rate = _nearest_rate(rate_map, entry_time)
        if rate:
            return pv_quote / rate

    # Try inverse ({quote}USD) if it exists
    for tf in ("M5", "M15", "M1", "H1"):
        rate_map = _load_fx_close_map(data_dir / f"{pair2}_{tf}.csv")
        rate = _nearest_rate(rate_map, entry_time)
        if rate:
            return pv_quote * rate

    # Last resort: approximate using entry_price when base is USD (USDCHF, USDJPY)
    if base_ccy(s) == "USD":
        return pv_quote / entry_price

    # Fallbacks (useful when backtest_results span beyond backtest_data coverage)
    # These are intentionally conservative, and you can override by extending
    # backtest_data with the required conversion pairs.
    if q == "JPY":
        # $ value per JPY = 1 / USDJPY. Use 150 as a rough mid-cycle anchor.
        usd_jpy = 150.0
        return pv_quote / usd_jpy
    if q == "CHF":
        usd_chf = 0.90  # 1 USD ≈ 0.90 CHF
        return pv_quote / usd_chf
    if q == "GBP":
        gbp_usd = 1.25  # 1 GBP ≈ 1.25 USD
        return pv_quote * gbp_usd
    if q == "EUR":
        eur_usd = 1.08  # 1 EUR ≈ 1.08 USD
        return pv_quote * eur_usd

    raise RuntimeError(f"Cannot convert pip value to USD for symbol={symbol} quote={q}")


def implied_lot_size(risk_usd: float, trade: TradeRow, pip_value_usd_lot: float) -> float:
    if trade.risk_pips <= 0 or pip_value_usd_lot <= 0:
        return 0.0
    return risk_usd / (trade.risk_pips * pip_value_usd_lot)


def _read_trades(path: Path) -> Iterable[TradeRow]:
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            yield TradeRow(
                symbol=row["symbol"].strip().upper(),
                entry_time=_parse_dt(row["entry_time"]),
                entry_price=float(row["entry_price"]),
                sl_price=float(row["sl_price"]),
                pnl_pips=float(row["pnl_pips"]),
                rr_achieved=float(row.get("rr_achieved") or 0.0),
                exit_reason=(row.get("exit_reason") or "").strip(),
            )


def analyze_last_month(
    results_csv: Path = BACKTEST_RESULTS_DEFAULT,
    backtest_data_dir: Path = BACKTEST_DATA_DIR_DEFAULT,
    risk_usd_per_trade: float = 50.0,
) -> str:
    trades = list(_read_trades(results_csv))
    if not trades:
        return "No trades found."

    last_month = max(_ym(t.entry_time) for t in trades)
    # also compute previous month for context
    months_sorted = sorted({_ym(t.entry_time) for t in trades})
    prev_month = None
    if len(months_sorted) >= 2:
        prev_month = months_sorted[-2]

    month_trades = [t for t in trades if _ym(t.entry_time) == last_month]
    if not month_trades:
        return "No trades found for last month."

    def _summarize(trades_in_month: list[TradeRow]):
        rows_local = []
        by_symbol = defaultdict(list)
        for t in trades_in_month:
            by_symbol[t.symbol].append(t)

        for sym, sym_trades in sorted(by_symbol.items()):
            lots = []
            pnl_usd = []
            wins = 0
            for t in sym_trades:
                pv = pip_value_usd_per_lot(sym, t.entry_time, t.entry_price, backtest_data_dir)
                lot = implied_lot_size(risk_usd_per_trade, t, pv)
                lots.append(lot)
                pnl_usd.append(t.pnl_pips * pv * lot)
                if t.pnl_pips > 0:
                    wins += 1

            n = len(sym_trades)
            avg_lot = sum(lots) / n if n else 0.0
            total_usd = sum(pnl_usd)
            total_pips = sum(t.pnl_pips for t in sym_trades)
            avg_rr = sum(t.rr_achieved for t in sym_trades) / n if n else 0.0
            winrate = (wins / n * 100.0) if n else 0.0

            rows_local.append((sym, n, winrate, avg_lot, total_pips, total_usd, avg_rr))
        return rows_local

    y, m = last_month
    out = []
    out.append(
        f"Last backtest month detected: {y:04d}-{m:02d} "
        f"({len(month_trades)} trades, assumed risk_per_trade=${risk_usd_per_trade:.2f})"
    )
    out.append("")
    out.append("| Pair | Trades | Win% | Avg lot | Total pips | Total PnL ($) | Avg R |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for sym, n, winrate, avg_lot, total_pips, total_usd, avg_rr in _summarize(month_trades):
        out.append(f"| {sym} | {n} | {winrate:0.1f}% | {avg_lot:0.3f} | {total_pips:0.2f} | {total_usd:+0.2f} | {avg_rr:0.2f} |")

    if prev_month:
        py, pm = prev_month
        prev_trades = [t for t in trades if _ym(t.entry_time) == prev_month]
        out.append("")
        out.append(f"Previous month: {py:04d}-{pm:02d} ({len(prev_trades)} trades)")
        out.append("")
        out.append("| Pair | Trades | Win% | Avg lot | Total pips | Total PnL ($) | Avg R |")
        out.append("|---|---:|---:|---:|---:|---:|---:|")
        for sym, n, winrate, avg_lot, total_pips, total_usd, avg_rr in _summarize(prev_trades):
            out.append(f"| {sym} | {n} | {winrate:0.1f}% | {avg_lot:0.3f} | {total_pips:0.2f} | {total_usd:+0.2f} | {avg_rr:0.2f} |")

    return "\n".join(out)


if __name__ == "__main__":
    print(analyze_last_month())

