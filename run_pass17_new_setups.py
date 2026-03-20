"""
run_pass17_new_setups.py — PASS 17: NR7 + 3-Bar Play
======================================================
Tests two academically validated setups on our 16 months of M5 data.
Zero ICT branding. Pure price mechanics.

Setup 1 — NR7 (Toby Crabel, 1990)
  Narrowest range bar in 7 bars → breakout of that bar's range
  Entry: bar N+1 breaks above NR7 high (BUY) or below NR7 low (SELL)
  SL:    opposite side of NR7 bar
  TP:    2× NR7 range
  Filter: H4 EMA 50/200 trend alignment

Setup 2 — 3-Bar Play (Raschke & Connors, Street Smarts 1995)
  3 consecutive closes in same direction → bar 4 breakout
  Entry: bar 4 breaks bar 3's extreme
  SL:    bar 3's opposite extreme
  TP:    1.5× range of bars 1-3
  Filter: bars 1-3 combined range < 1.5× ATR (not overextended)
  Filter: H4 EMA 50/200 trend alignment

Configs:
  A — NR7 only, all direction combos
  B — NR7 with direction filters (GBPUSD SELL, USDJPY BUY, EURUSD both)
  C — 3-Bar Play only, all direction combos
  D — 3-Bar Play with direction filters
  E — NR7 + 3-Bar Play combined with direction filters

Run from project root:
  python run_pass17_new_setups.py
"""

import sys, gc, csv
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "python"))

DATA_DIR  = "data/m5_xm"
DATE_FROM = datetime(2024, 11, 5, tzinfo=timezone.utc)
DATE_TO   = datetime(2026, 2, 27, tzinfo=timezone.utc)
WEEKS     = (DATE_TO - DATE_FROM).days / 7
PAIRS     = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD"]
RISK_USD  = 50.0
AVG_SL_P  = 32.0
DPIP      = RISK_USD / AVG_SL_P

BAD_COMBOS = {("GBPUSD", "BUY"), ("USDJPY", "SELL")}

# ── DATA LOADER ───────────────────────────────────────────────────────────────
def load_m5(pair):
    from backtester import BacktestEngine
    import json
    with open("config/settings.json") as f:
        cfg = json.load(f)
    eng = BacktestEngine.__new__(BacktestEngine)
    candles = eng._load_candles_for_symbol.__func__(
        eng, pair, DATA_DIR, DATE_FROM, DATE_TO
    ) if hasattr(eng, '_load_candles_for_symbol') else None

    # Fallback: read CSVs directly
    if candles is None:
        pair_dir = Path(DATA_DIR) / f"{pair}_M5"
        if not pair_dir.exists():
            pair_dir = Path(DATA_DIR)
        files = sorted(pair_dir.glob(f"{pair}*M5*.csv")) or \
                sorted(Path(DATA_DIR).glob(f"{pair}*m5*.csv"))
        import pandas as pd
        frames = []
        for f in files:
            try:
                df = pd.read_csv(f, parse_dates=[0])
                frames.append(df)
            except Exception:
                pass
        if not frames:
            return []
        all_df = pd.concat(frames).drop_duplicates().sort_values(by=frames[0].columns[0])
        candles = []
        for _, row in all_df.iterrows():
            try:
                candles.append({
                    "time":  pd.Timestamp(row.iloc[0]).to_pydatetime().replace(tzinfo=timezone.utc),
                    "open":  float(row.iloc[1]),
                    "high":  float(row.iloc[2]),
                    "low":   float(row.iloc[3]),
                    "close": float(row.iloc[4]),
                    "volume": float(row.iloc[5]) if len(row) > 5 else 1.0,
                })
            except Exception:
                pass
    return candles


def load_h4(pair):
    pair_dir = Path(DATA_DIR)
    files = sorted(pair_dir.glob(f"{pair}*H4*.csv")) or \
            sorted(pair_dir.glob(f"{pair}*h4*.csv"))
    import pandas as pd
    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, parse_dates=[0])
            frames.append(df)
        except Exception:
            pass
    if not frames:
        return []
    all_df = pd.concat(frames).drop_duplicates().sort_values(by=frames[0].columns[0])
    candles = []
    for _, row in all_df.iterrows():
        try:
            candles.append({
                "time":  pd.Timestamp(row.iloc[0]).to_pydatetime().replace(tzinfo=timezone.utc),
                "close": float(row.iloc[4]),
            })
        except Exception:
            pass
    return candles


# ── EMA ───────────────────────────────────────────────────────────────────────
def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def get_h4_bias(h4_closes):
    """Returns 1 (bullish), -1 (bearish), 0 (neutral)"""
    if len(h4_closes) < 200:
        return 0
    fast = ema(h4_closes, 50)
    slow = ema(h4_closes, 200)
    if fast is None or slow is None:
        return 0
    if fast > slow * 1.0001:
        return 1
    elif fast < slow * 0.9999:
        return -1
    return 0


# ── PIP SIZE ──────────────────────────────────────────────────────────────────
def pip_size(symbol):
    if "JPY" in symbol:
        return 0.01
    if "XAU" in symbol or "XAG" in symbol:
        return 0.1
    return 0.0001


# ── ATR ───────────────────────────────────────────────────────────────────────
def atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i-1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


# ── TRADE RECORD ─────────────────────────────────────────────────────────────
class Trade:
    def __init__(self, symbol, direction, setup, entry, sl, tp,
                 entry_time, exit_time=None, exit_price=None, reason=None):
        self.symbol     = symbol
        self.direction  = direction
        self.setup_type = setup
        self.entry_price = entry
        self.sl_price   = sl
        self.tp_price   = tp
        self.entry_time = entry_time
        self.exit_time  = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        pip = pip_size(symbol)
        if exit_price and entry:
            if direction == "BUY":
                self.pnl_pips = (exit_price - entry) / pip
            else:
                self.pnl_pips = (entry - exit_price) / pip
        else:
            self.pnl_pips = 0.0


# ── NR7 SCANNER ───────────────────────────────────────────────────────────────
def scan_nr7(candles, idx, symbol, h4_bias, direction_filter):
    """
    Returns a list of trade signals at candle[idx] if NR7 conditions met.
    NR7: candle[idx-1] has narrowest range in the 7 bars ending at idx-1.
    Entry: current bar (idx) breaks above/below NR7 bar.
    """
    if idx < 8:
        return []

    pip = pip_size(symbol)
    nr7_bar = candles[idx - 1]
    nr7_range = nr7_bar["high"] - nr7_bar["low"]

    # Check if bar[idx-1] is the narrowest of the last 7 bars
    min_range = min(
        candles[i]["high"] - candles[i]["low"]
        for i in range(idx - 7, idx)
    )
    if nr7_range > min_range * 1.0001:
        return []  # not NR7

    # Minimum range filter — avoid spread noise
    if nr7_range < pip * 3:
        return []

    current = candles[idx]
    signals = []

    # BUY signal: current bar breaks above NR7 high
    if current["close"] > nr7_bar["high"]:
        if h4_bias >= 0:  # neutral or bullish
            entry = current["close"]
            sl    = nr7_bar["low"] - pip * 1  # 1 pip below NR7 low
            tp    = entry + 2 * nr7_range      # 2R

            sl_pips = (entry - sl) / pip
            if sl_pips < 3 or sl_pips > 80:
                return []

            combo = (symbol, "BUY")
            if direction_filter and combo in BAD_COMBOS:
                return []

            signals.append(Trade(
                symbol=symbol, direction="BUY", setup="NR7",
                entry=entry, sl=sl, tp=tp,
                entry_time=current["time"]
            ))

    # SELL signal: current bar breaks below NR7 low
    elif current["close"] < nr7_bar["low"]:
        if h4_bias <= 0:  # neutral or bearish
            entry = current["close"]
            sl    = nr7_bar["high"] + pip * 1
            tp    = entry - 2 * nr7_range

            sl_pips = (sl - entry) / pip
            if sl_pips < 3 or sl_pips > 80:
                return []

            combo = (symbol, "SELL")
            if direction_filter and combo in BAD_COMBOS:
                return []

            signals.append(Trade(
                symbol=symbol, direction="SELL", setup="NR7",
                entry=entry, sl=sl, tp=tp,
                entry_time=current["time"]
            ))

    return signals


# ── 3-BAR PLAY SCANNER ────────────────────────────────────────────────────────
def scan_3bar(candles, idx, symbol, h4_bias, direction_filter):
    """
    3-Bar Play: 3 consecutive closes in same direction → bar 4 breakout.
    Bars 1,2,3 = candles[idx-4], [idx-3], [idx-2]
    Setup confirmed at candle[idx-1] (bar 3 complete)
    Entry at candle[idx] (bar 4) if it breaks bar 3 extreme
    """
    if idx < 6:
        return []

    pip  = pip_size(symbol)
    b1   = candles[idx - 4]
    b2   = candles[idx - 3]
    b3   = candles[idx - 2]
    b4   = candles[idx - 1]  # entry bar (already closed)
    curr = candles[idx]

    # Check 3 consecutive closes in same direction
    bull = (b1["close"] > b1["open"] and
            b2["close"] > b1["close"] and
            b3["close"] > b2["close"])
    bear = (b1["close"] < b1["open"] and
            b2["close"] < b1["close"] and
            b3["close"] < b2["close"])

    if not bull and not bear:
        return []

    # Not overextended filter: combined range < 2× ATR
    combined_range = (max(b1["high"], b2["high"], b3["high"]) -
                      min(b1["low"],  b2["low"],  b3["low"]))
    atr_val = atr(candles[max(0, idx-20):idx], 14)
    if atr_val and combined_range > 2.0 * atr_val:
        return []  # already extended, fade risk too high

    signals = []

    if bull and h4_bias >= 0:
        # Bar 4 must break bar 3 high
        if curr["close"] > b3["high"]:
            entry   = curr["close"]
            sl      = b3["low"] - pip * 1
            tp_dist = b3["close"] - b1["open"]
            tp      = entry + tp_dist * 1.5

            sl_pips = (entry - sl) / pip
            if sl_pips < 3 or sl_pips > 80:
                return []

            combo = (symbol, "BUY")
            if direction_filter and combo in BAD_COMBOS:
                return []

            signals.append(Trade(
                symbol=symbol, direction="BUY", setup="THREE_BAR_PLAY",
                entry=entry, sl=sl, tp=tp,
                entry_time=curr["time"]
            ))

    elif bear and h4_bias <= 0:
        # Bar 4 must break bar 3 low
        if curr["close"] < b3["low"]:
            entry   = curr["close"]
            sl      = b3["high"] + pip * 1
            tp_dist = b1["open"] - b3["close"]
            tp      = entry - tp_dist * 1.5

            sl_pips = (sl - entry) / pip
            if sl_pips < 3 or sl_pips > 80:
                return []

            combo = (symbol, "SELL")
            if direction_filter and combo in BAD_COMBOS:
                return []

            signals.append(Trade(
                symbol=symbol, direction="SELL", setup="THREE_BAR_PLAY",
                entry=entry, sl=sl, tp=tp,
                entry_time=curr["time"]
            ))

    return signals


# ── BAR-BY-BAR SIMULATOR ──────────────────────────────────────────────────────
def simulate_pair(pair, candles_m5, candles_h4,
                  use_nr7=True, use_3bar=True,
                  direction_filter=True):
    """
    Walk through every M5 bar, fire signals, simulate exits bar by bar.
    Returns list of closed Trade objects.
    """
    pip = pip_size(pair)
    h4_closes = [c["close"] for c in candles_h4]

    trades     = []
    open_trades = []
    last_signal_bar = {}  # cooldown: 1 signal per pair per 10 bars

    for idx in range(200, len(candles_m5)):
        bar = candles_m5[idx]
        ts  = bar["time"]

        if ts < DATE_FROM or ts > DATE_TO:
            continue

        # Update H4 bias (use H4 bars up to current time)
        h4_up_to = [c["close"] for c in candles_h4
                    if c["time"] <= ts]
        bias = get_h4_bias(h4_up_to)

        # Manage open trades
        still_open = []
        for t in open_trades:
            # Check SL hit
            if t.direction == "BUY":
                if bar["low"] <= t.sl_price:
                    t.exit_price = t.sl_price
                    t.exit_time  = ts
                    t.exit_reason = "SL_HIT"
                    p = pip_size(t.symbol)
                    t.pnl_pips = (t.exit_price - t.entry_price) / p
                    trades.append(t)
                    continue
                elif bar["high"] >= t.tp_price:
                    t.exit_price = t.tp_price
                    t.exit_time  = ts
                    t.exit_reason = "TP_HIT"
                    p = pip_size(t.symbol)
                    t.pnl_pips = (t.exit_price - t.entry_price) / p
                    trades.append(t)
                    continue
            else:  # SELL
                if bar["high"] >= t.sl_price:
                    t.exit_price = t.sl_price
                    t.exit_time  = ts
                    t.exit_reason = "SL_HIT"
                    p = pip_size(t.symbol)
                    t.pnl_pips = (t.entry_price - t.exit_price) / p
                    trades.append(t)
                    continue
                elif bar["low"] <= t.tp_price:
                    t.exit_price = t.tp_price
                    t.exit_time  = ts
                    t.exit_reason = "TP_HIT"
                    p = pip_size(t.symbol)
                    t.pnl_pips = (t.entry_price - t.exit_price) / p
                    trades.append(t)
                    continue
            still_open.append(t)
        open_trades = still_open

        # Max 1 open trade per pair
        if len(open_trades) >= 1:
            continue

        # Cooldown: no signal within 10 bars of last signal
        last = last_signal_bar.get(pair, 0)
        if idx - last < 10:
            continue

        # Scan for new signals
        new_signals = []
        if use_nr7:
            new_signals += scan_nr7(
                candles_m5, idx, pair, bias, direction_filter)
        if use_3bar:
            new_signals += scan_3bar(
                candles_m5, idx, pair, bias, direction_filter)

        if new_signals:
            open_trades.append(new_signals[0])
            last_signal_bar[pair] = idx

    # Close any remaining open trades at last price
    last_close = candles_m5[-1]["close"] if candles_m5 else 0
    for t in open_trades:
        t.exit_price  = last_close
        t.exit_time   = DATE_TO
        t.exit_reason = "END_OF_DATA"
        p = pip_size(t.symbol)
        if t.direction == "BUY":
            t.pnl_pips = (t.exit_price - t.entry_price) / p
        else:
            t.pnl_pips = (t.entry_price - t.exit_price) / p
        trades.append(t)

    return trades


# ── RUN CONFIG ────────────────────────────────────────────────────────────────
def run_config(label, use_nr7, use_3bar, direction_filter):
    print(f"\n>>> {label}")
    all_trades = []

    for pair in PAIRS:
        print(f"  [{label}] {pair} @ {datetime.now().strftime('%H:%M:%S')}",
              end="", flush=True)

        # Load data — try backtester approach first, fallback to CSV
        try:
            import json
            from backtester import BacktestEngine
            with open("config/settings.json") as f:
                cfg = json.load(f)
            eng = BacktestEngine(
                config=cfg, data_dir=DATA_DIR,
                use_sniper_filter=False, max_open_trades=1,
                one_trade_per_symbol=True, signal_cooldown_bars=10,
                disabled_setups=[], killzone_only=False, use_trailing=False,
            )
            # Get candle data through engine's loader
            candles_m5 = eng._load_symbol_data(pair, "M5") \
                if hasattr(eng, '_load_symbol_data') else []
            candles_h4 = eng._load_symbol_data(pair, "H4") \
                if hasattr(eng, '_load_symbol_data') else []
        except Exception:
            candles_m5 = []
            candles_h4 = []

        # Direct CSV load fallback
        if not candles_m5:
            import pandas as pd
            data_path = Path(DATA_DIR)
            m5_files = sorted(data_path.rglob(f"*{pair}*M5*.csv")) + \
                       sorted(data_path.rglob(f"*{pair}*m5*.csv"))
            h4_files = sorted(data_path.rglob(f"*{pair}*H4*.csv")) + \
                       sorted(data_path.rglob(f"*{pair}*h4*.csv"))

            def load_csv_candles(files):
                frames = []
                for f in files:
                    try:
                        df = pd.read_csv(f)
                        frames.append(df)
                    except Exception:
                        pass
                if not frames:
                    return []
                combined = pd.concat(frames, ignore_index=True)
                combined.columns = [c.lower().strip() for c in combined.columns]
                time_col = next((c for c in combined.columns
                                 if "time" in c or "date" in c), combined.columns[0])
                combined[time_col] = pd.to_datetime(combined[time_col], utc=True,
                                                     errors="coerce")
                combined = combined.dropna(subset=[time_col]).sort_values(time_col)
                result = []
                for _, row in combined.iterrows():
                    try:
                        result.append({
                            "time":   row[time_col].to_pydatetime(),
                            "open":   float(row.get("open",  row.iloc[1])),
                            "high":   float(row.get("high",  row.iloc[2])),
                            "low":    float(row.get("low",   row.iloc[3])),
                            "close":  float(row.get("close", row.iloc[4])),
                            "volume": float(row.get("volume", 1.0)),
                        })
                    except Exception:
                        pass
                return result

            candles_m5 = load_csv_candles(m5_files)
            candles_h4 = load_csv_candles(h4_files)

        if not candles_m5:
            print(f" — NO DATA")
            continue

        trades = simulate_pair(
            pair, candles_m5, candles_h4,
            use_nr7=use_nr7, use_3bar=use_3bar,
            direction_filter=direction_filter
        )
        print(f" → {len(trades)} trades")
        all_trades.extend(trades)
        gc.collect()

    return all_trades


# ── SUMMARIZE ─────────────────────────────────────────────────────────────────
def summarize(trades, label):
    if not trades:
        print(f"\n  {label}: NO TRADES")
        return {}

    wins   = [t for t in trades if t.pnl_pips > 0]
    losses = [t for t in trades if t.pnl_pips <= 0]

    if not wins or not losses:
        print(f"\n  {label}: insufficient data ({len(wins)}W {len(losses)}L)")
        return {}

    gw  = sum(t.pnl_pips for t in wins)
    gl  = abs(sum(t.pnl_pips for t in losses))
    net = gw - gl
    pf  = gw / gl if gl else float("inf")
    wr  = len(wins) / len(trades) * 100
    ppw = net / WEEKS
    dpw = ppw * DPIP

    print(f"\n{'='*62}")
    print(f"  {label}")
    print(f"{'='*62}")
    print(f"  Trades:    {len(trades)} ({len(trades)/WEEKS:.1f}/week)")
    print(f"  Win Rate:  {wr:.1f}%  ({len(wins)}W / {len(losses)}L)")
    print(f"  PF:        {pf:.2f}")
    print(f"  Pips:      {net:+.1f}  ({ppw:+.1f}/week)")
    print(f"  Avg Win:   +{gw/len(wins):.1f}p = +${gw/len(wins)*DPIP:.0f}")
    print(f"  Avg Loss:  -{gl/len(losses):.1f}p = -${gl/len(losses)*DPIP:.0f}")
    print(f"  $/week:    ${dpw:+.0f}  (at $5K 1% risk)")

    # By setup
    by_s = defaultdict(list)
    for t in trades:
        by_s[t.setup_type].append(t)
    print(f"\n  By Setup:")
    for s, st in sorted(by_s.items(), key=lambda x: -sum(t.pnl_pips for t in x[1])):
        sw  = [t for t in st if t.pnl_pips > 0]
        net_s = sum(t.pnl_pips for t in st)
        gw_s = sum(t.pnl_pips for t in sw)
        gl_s = abs(sum(t.pnl_pips for t in st if t.pnl_pips <= 0))
        pf_s = gw_s/gl_s if gl_s else float("inf")
        v = "✅" if net_s > 0 else "❌"
        print(f"    {v} {s:<30} {len(st):>4}tr | WR {len(sw)/len(st)*100:.0f}% | "
              f"PF {pf_s:.2f} | {net_s:+.1f}p")

    # By pair+direction
    combos = defaultdict(list)
    for t in trades:
        combos[f"{t.symbol} {t.direction}"].append(t)
    print(f"\n  By Pair+Direction:")
    for k, kt in sorted(combos.items(), key=lambda x: -sum(t.pnl_pips for t in x[1])):
        kw = [t for t in kt if t.pnl_pips > 0]
        net_k = sum(t.pnl_pips for t in kt)
        gw_k = sum(t.pnl_pips for t in kw)
        gl_k = abs(sum(t.pnl_pips for t in kt if t.pnl_pips <= 0))
        pf_k = gw_k/gl_k if gl_k else float("inf")
        v = "✅" if net_k > 0 else "❌"
        print(f"    {v} {k:<18} {len(kt):>4}tr | WR {len(kw)/len(kt)*100:.0f}% | "
              f"PF {pf_k:.2f} | {net_k:+.1f}p")

    # Monthly
    by_m = defaultdict(list)
    for t in trades:
        by_m[str(t.entry_time)[:7]].append(t)
    green = red = 0
    print(f"\n  Monthly:")
    for m in sorted(by_m.keys()):
        mt = by_m[m]
        mw = [t for t in mt if t.pnl_pips > 0]
        net_m = sum(t.pnl_pips for t in mt)
        if net_m > 0:
            green += 1
        else:
            red += 1
        print(f"    {'✅' if net_m>0 else '❌'} {m}  {len(mt):>3}tr | "
              f"WR {len(mw)/len(mt)*100:.0f}% | {net_m:+.1f}p")
    print(f"\n  Profitable months: {green}/{green+red} = "
          f"{green/(green+red)*100:.0f}%")
    print(f"{'='*62}")

    return {"trades": len(trades), "wr": wr, "pf": pf,
            "pips": net, "ppw": ppw, "dpw": dpw}


def save_csv(trades, filename):
    if not trades:
        return
    with open(filename, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol","setup_type","direction","entry_time",
                    "exit_time","entry_price","exit_price",
                    "sl_price","tp_price","pnl_pips","exit_reason"])
        for t in trades:
            w.writerow([t.symbol, t.setup_type, t.direction,
                        t.entry_time, t.exit_time,
                        t.entry_price, t.exit_price,
                        t.sl_price, t.tp_price,
                        round(t.pnl_pips, 2), t.exit_reason])
    print(f"  Saved → {filename}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*62)
    print("  PASS 17 — NR7 + 3-BAR PLAY")
    print("  Zero ICT. Pure price mechanics. Academic sources only.")
    print("="*62)
    print(f"  Pairs:   {PAIRS}")
    print(f"  Range:   {DATE_FROM.date()} → {DATE_TO.date()}")
    print(f"  H4 bias: EMA 50/200 (bullish = long only, bearish = short only)")
    print("="*62)

    results = {}

    # Config A — NR7 alone, no direction filter
    t_A = run_config("A — NR7 only (all directions)", True, False, False)
    results["A"] = summarize(t_A, "A — NR7, no direction filter")
    save_csv(t_A, "pass17_A_nr7_all.csv")

    # Config B — NR7 with direction filter
    t_B = run_config("B — NR7 + direction filters", True, False, True)
    results["B"] = summarize(t_B, "B — NR7 + direction filters")
    save_csv(t_B, "pass17_B_nr7_filtered.csv")

    # Config C — 3-Bar Play alone, no direction filter
    t_C = run_config("C — 3-Bar Play only (all directions)", False, True, False)
    results["C"] = summarize(t_C, "C — 3-Bar Play, no direction filter")
    save_csv(t_C, "pass17_C_3bar_all.csv")

    # Config D — 3-Bar Play with direction filter
    t_D = run_config("D — 3-Bar Play + direction filters", False, True, True)
    results["D"] = summarize(t_D, "D — 3-Bar Play + direction filters")
    save_csv(t_D, "pass17_D_3bar_filtered.csv")

    # Config E — Both setups with direction filter
    t_E = run_config("E — NR7 + 3-Bar Play combined", True, True, True)
    results["E"] = summarize(t_E, "E — Both setups + direction filters")
    save_csv(t_E, "pass17_E_combined.csv")

    # Final table
    print(f"\n\n{'='*62}")
    print(f"  PASS 17 FINAL COMPARISON")
    print(f"{'='*62}")
    print(f"\n  {'Config':<35} {'Tr/wk':>5} {'WR':>5} {'PF':>5} {'$/wk':>7}")
    print(f"  {'-'*58}")

    labels = {
        "A": "A — NR7 (no filter)",
        "B": "B — NR7 (filtered)",
        "C": "C — 3-Bar (no filter)",
        "D": "D — 3-Bar (filtered)",
        "E": "E — Combined (filtered)",
    }
    for k, lbl in labels.items():
        r = results.get(k, {})
        if r:
            verdict = "✅" if r["pf"] > 1.10 else "⚠️ " if r["pf"] > 1.0 else "❌"
            print(f"  {verdict} {lbl:<33} {r['trades']/WEEKS:>5.1f} "
                  f"{r['wr']:>4.0f}% {r['pf']:>5.2f} {r['dpw']:>+6.0f}$")

    print(f"\n  Verdict guide: ✅ PF>1.10 = add to live bot")
    print(f"                 ⚠️  PF 1.0-1.10 = borderline, more data needed")
    print(f"                 ❌ PF<1.0 = do not add")
    print(f"\n{'='*62}\n")


if __name__ == "__main__":
    main()
