"""
run_pass13a_clean.py — Personality A Clean Backtest + Bleeder Fade Test
Run from project root: python run_pass13a_clean.py

Runs in 3 phases:
  Phase 1 — Core Personality A (CHOCH + LSR + FVG + ORDER_BLOCK + ENGULFING)
  Phase 2 — Bleeder setups isolated (LH_LL + HH_HL) to collect their signals
  Phase 3 — Fade analysis: what if we took the OPPOSITE of every bleeder signal?
"""

import sys
import os
import csv
import json
import gc
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "python"))

# ── LOAD CONFIG ───────────────────────────────────────────────────────────────

with open("config/settings.json", encoding="utf-8") as f:
    BASE_CONFIG = json.load(f)

PAIRS     = ["GBPUSD", "USDJPY", "AUDUSD", "EURUSD", "GBPJPY"]
DATA_DIR  = "data/m5_xm"
DATE_FROM = datetime(2024, 11, 5, tzinfo=timezone.utc)
DATE_TO   = datetime(2026, 2, 27, tzinfo=timezone.utc)

# ── CONFIG BUILDER ────────────────────────────────────────────────────────────

def build_config(extra_disabled=None, direction_filters=None):
    import copy
    cfg = copy.deepcopy(BASE_CONFIG)

    # Core bleeders — always disabled
    always_disabled = [
        "PIN_BAR",
        "LH_LL_CONTINUATION",
        "HH_HL_CONTINUATION",
        "LIQUIDITY_GRAB_CONTINUATION",
        "FVG_CONTINUATION",
        "CONTINUATION_OB",
    ]
    disabled = always_disabled + (extra_disabled or [])

    # CRITICAL: explicitly override disabled_setups
    # This ensures settings.json values don't interfere
    cfg["disabled_setups"] = disabled

    # Kill zone times — corrected ICT
    if "ict" not in cfg:
        cfg["ict"] = {}
    if "kill_zones" not in cfg["ict"]:
        cfg["ict"]["kill_zones"] = {}
    cfg["ict"]["kill_zones"]["london_open"]  = {"start": "06:00", "end": "09:00", "tz": "UTC"}
    cfg["ict"]["kill_zones"]["ny_open"]      = {"start": "13:30", "end": "16:00", "tz": "UTC"}
    cfg["ict"]["kill_zones"]["london_close"] = {"start": "15:00", "end": "17:00", "tz": "UTC"}

    # All kill zones
    if "hybrid" not in cfg:
        cfg["hybrid"] = {}
    cfg["hybrid"]["allowed_kill_zones"] = ["LONDON_OPEN", "NY_OPEN", "LONDON_CLOSE"]

    # Direction filters
    cfg["direction_filters"] = direction_filters or {}

    # Giveback guard — 99%
    if "trade_management" not in cfg:
        cfg["trade_management"] = {}
    cfg["trade_management"]["giveback_guard"] = {
        "enabled": True,
        "activate_at_r": 0.5,
        "max_giveback_pct": 0.01,
    }
    cfg["trade_management"]["partials"] = {
        "enabled": True,
        "tp1_r": 1.0,
        "tp1_close_pct": 0.6,
        "tp1_sl_mode": "BE_PLUS",
        "tp1_be_plus_r": 0.5,
        "trail_only_after_tp1": True,
    }

    # Risk
    if "risk" not in cfg:
        cfg["risk"] = {}
    cfg["risk"]["risk_per_trade_pct"] = 1.0
    cfg["risk"]["daily_loss_limit_pct"] = None

    # Execution
    if "execution" not in cfg:
        cfg["execution"] = {}
    cfg["execution"]["min_rr"] = 1.5
    cfg["execution"]["enforce_killzones"] = True

    return cfg


# ── BACKTEST RUNNER ───────────────────────────────────────────────────────────

def run_single_pair(pair, config, label=""):
    from backtester import BacktestEngine

    print(f"\n  [{label}] {pair} starting @ {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Disabled: {config['disabled_setups']}")

    engine = BacktestEngine(
        config=config,
        data_dir=DATA_DIR,
        use_sniper_filter=False,
        max_open_trades=2,
        one_trade_per_symbol=True,
        signal_cooldown_bars=6,
        disabled_setups=config["disabled_setups"],
        killzone_only=True,
        use_trailing=True,
    )

    trades = engine.run(
        symbols=[pair],
        start_date=DATE_FROM,
        end_date=DATE_TO,
        progress_every=3000,
    )

    closed = [t for t in trades if t.exit_price is not None]
    print(f"  [{label}] {pair} done @ {datetime.now().strftime('%H:%M:%S')} — {len(closed)} trades")

    del engine, trades
    gc.collect()
    return closed


def save_csv(trades, filename):
    if not trades:
        print(f"  No trades to save → {filename}")
        return
    fields = [
        'symbol', 'setup_type', 'direction', 'kill_zone',
        'entry_time', 'exit_time', 'entry_price', 'exit_price',
        'sl_price', 'tp_price', 'pnl_pips', 'exit_reason',
        'partial_taken', 'htf_bias',
    ]
    with open(filename, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for t in trades:
            row = {field: getattr(t, field, '') for field in fields}
            # handle killzone attribute name variations
            if not row['kill_zone']:
                row['kill_zone'] = getattr(t, 'killzone', '')
            w.writerow(row)
    print(f"  Saved {len(trades)} trades → {filename}")


# ── REPORTING ─────────────────────────────────────────────────────────────────

def summarize(trades, label):
    if not trades:
        print(f"\n  {label}: 0 trades")
        return {}

    wins   = [t for t in trades if float(t.pnl_pips or 0) > 0]
    losses = [t for t in trades if float(t.pnl_pips or 0) <= 0]
    total_pips = sum(float(t.pnl_pips or 0) for t in trades)
    wr  = len(wins) / len(trades) * 100
    gw  = sum(float(t.pnl_pips or 0) for t in wins)
    gl  = abs(sum(float(t.pnl_pips or 0) for t in losses))
    pf  = gw / gl if gl > 0 else float('inf')
    weeks = (DATE_TO - DATE_FROM).days / 7
    avg_win  = gw / len(wins)   if wins   else 0
    avg_loss = gl / len(losses) if losses else 0

    print(f"\n{'='*58}")
    print(f"  {label}")
    print(f"{'='*58}")
    print(f"  Trades:        {len(trades)} ({len(trades)/weeks:.1f}/week)")
    print(f"  Win Rate:      {wr:.1f}%  ({len(wins)}W / {len(losses)}L)")
    print(f"  Profit Factor: {pf:.2f}")
    print(f"  Total Pips:    {total_pips:+.1f}")
    print(f"  Avg Win:       +{avg_win:.1f} pips")
    print(f"  Avg Loss:      -{avg_loss:.1f} pips")

    # Per setup
    by_setup = defaultdict(list)
    for t in trades:
        by_setup[getattr(t, 'setup_type', 'UNKNOWN')].append(t)
    print(f"\n  By Setup:")
    for s, st in sorted(by_setup.items(), key=lambda x: -sum(float(t.pnl_pips or 0) for t in x[1])):
        sw  = [t for t in st if float(t.pnl_pips or 0) > 0]
        sp  = sum(float(t.pnl_pips or 0) for t in st)
        sgw = sum(float(t.pnl_pips or 0) for t in sw)
        sgl = abs(sum(float(t.pnl_pips or 0) for t in st if float(t.pnl_pips or 0) <= 0))
        spf = sgw / sgl if sgl > 0 else float('inf')
        verdict = "✅" if spf > 1.0 else "❌"
        print(f"  {verdict} {s:<35} {len(st):>3}tr | WR {len(sw)/len(st)*100:.0f}% | PF {spf:.2f} | {sp:+.1f}p")

    # Per session
    by_kz = defaultdict(list)
    for t in trades:
        kz = getattr(t, 'kill_zone', '') or getattr(t, 'killzone', '') or 'UNKNOWN'
        by_kz[kz].append(t)
    print(f"\n  By Session:")
    for kz, kt in sorted(by_kz.items()):
        kw  = [t for t in kt if float(t.pnl_pips or 0) > 0]
        kp  = sum(float(t.pnl_pips or 0) for t in kt)
        kgw = sum(float(t.pnl_pips or 0) for t in kw)
        kgl = abs(sum(float(t.pnl_pips or 0) for t in kt if float(t.pnl_pips or 0) <= 0))
        kpf = kgw / kgl if kgl > 0 else float('inf')
        print(f"    {kz:<20} {len(kt):>3}tr | WR {len(kw)/len(kt)*100:.0f}% | PF {kpf:.2f} | {kp:+.1f}p")

    # Per pair
    by_pair = defaultdict(list)
    for t in trades:
        by_pair[getattr(t, 'symbol', 'UNKNOWN')].append(t)
    print(f"\n  By Pair:")
    for pair, pt in sorted(by_pair.items()):
        pw  = [t for t in pt if float(t.pnl_pips or 0) > 0]
        pp  = sum(float(t.pnl_pips or 0) for t in pt)
        pgw = sum(float(t.pnl_pips or 0) for t in pw)
        pgl = abs(sum(float(t.pnl_pips or 0) for t in pt if float(t.pnl_pips or 0) <= 0))
        ppf = pgw / pgl if pgl > 0 else float('inf')
        print(f"    {pair:<10} {len(pt):>3}tr | WR {len(pw)/len(pt)*100:.0f}% | PF {ppf:.2f} | {pp:+.1f}p")

    # Monthly
    by_month = defaultdict(list)
    for t in trades:
        try:
            et = str(getattr(t, 'entry_time', ''))[:7]
            by_month[et].append(t)
        except:
            pass
    print(f"\n  Monthly:")
    for month in sorted(by_month.keys()):
        mt  = by_month[month]
        mw  = [t for t in mt if float(t.pnl_pips or 0) > 0]
        mp  = sum(float(t.pnl_pips or 0) for t in mt)
        mgw = sum(float(t.pnl_pips or 0) for t in mw)
        mgl = abs(sum(float(t.pnl_pips or 0) for t in mt if float(t.pnl_pips or 0) <= 0))
        mpf = mgw / mgl if mgl > 0 else float('inf')
        status = "✅" if mp > 0 else "❌"
        print(f"    {status} {month}  {len(mt):>3}tr | WR {len(mw)/len(mt)*100:.0f}% | PF {mpf:.2f} | {mp:+.1f}p")

    print(f"{'='*58}\n")
    return {"trades": len(trades), "wr": wr, "pf": pf, "pips": total_pips,
            "tpw": len(trades)/weeks}


def fade_analysis(bleeder_trades, label):
    """
    Simulate taking the OPPOSITE direction of every bleeder signal.
    Flips BUY→SELL and SELL→BUY, inverts the pnl_pips.
    """
    if not bleeder_trades:
        print(f"\n  Fade analysis: no trades for {label}")
        return

    print(f"\n{'='*58}")
    print(f"  FADE ANALYSIS — {label}")
    print(f"  (Taking OPPOSITE direction of every signal)")
    print(f"{'='*58}")

    # Original performance
    orig_pips = sum(float(t.pnl_pips or 0) for t in bleeder_trades)
    orig_wins = [t for t in bleeder_trades if float(t.pnl_pips or 0) > 0]
    orig_wr   = len(orig_wins) / len(bleeder_trades) * 100

    # Faded performance — flip the pnl sign
    faded_pips  = -orig_pips
    faded_wins  = len(bleeder_trades) - len(orig_wins)
    faded_wr    = faded_wins / len(bleeder_trades) * 100
    faded_w_pips = abs(sum(float(t.pnl_pips or 0) for t in bleeder_trades if float(t.pnl_pips or 0) < 0))
    faded_l_pips = sum(float(t.pnl_pips or 0) for t in bleeder_trades if float(t.pnl_pips or 0) > 0)
    faded_pf    = faded_w_pips / faded_l_pips if faded_l_pips > 0 else float('inf')

    print(f"\n  Original (as-is):")
    print(f"    Trades:  {len(bleeder_trades)}")
    print(f"    WR:      {orig_wr:.1f}%")
    print(f"    Pips:    {orig_pips:+.1f}")

    print(f"\n  Faded (opposite direction):")
    print(f"    Trades:  {len(bleeder_trades)}  (same entries, flipped direction)")
    print(f"    WR:      {faded_wr:.1f}%")
    print(f"    Pips:    {faded_pips:+.1f}")
    print(f"    PF:      {faded_pf:.2f}")

    verdict = "✅ VIABLE — fading this setup adds value" if faded_pf > 1.2 else \
              "⚠️  MARGINAL — not strong enough to trade" if faded_pf > 1.0 else \
              "❌ NOT VIABLE — fading still loses"
    print(f"\n  Verdict: {verdict}")

    # Monthly fade breakdown
    by_month = defaultdict(list)
    for t in bleeder_trades:
        et = str(getattr(t, 'entry_time', ''))[:7]
        by_month[et].append(t)

    print(f"\n  Monthly fade P&L:")
    for month in sorted(by_month.keys()):
        mt = by_month[month]
        mp = -sum(float(t.pnl_pips or 0) for t in mt)  # flipped
        status = "✅" if mp > 0 else "❌"
        print(f"    {status} {month}  {len(mt):>3}tr | Faded pips: {mp:+.1f}")

    print(f"{'='*58}\n")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  PASS 13A CLEAN — PERSONALITY A + BLEEDER FADE TEST")
    print("="*60)
    print(f"  Pairs:      {PAIRS}")
    print(f"  Date range: {DATE_FROM.date()} → {DATE_TO.date()}")
    print(f"  Data dir:   {DATA_DIR}")
    print()
    print("  PHASE 1 — Core Personality A")
    print("    Setups ON:  CHOCH, LSR, FVG, ORDER_BLOCK, ENGULFING, SCALP, SNIPER")
    print("    Setups OFF: LH_LL, HH_HL, LIQUIDITY_GRAB, PIN_BAR, FVG_CONT, CONT_OB")
    print()
    print("  PHASE 2 — Confirmed Bleeders Isolated")
    print("    Setups ON:  LH_LL_CONTINUATION + HH_HL_CONTINUATION ONLY")
    print("    (to collect their signals for fade analysis)")
    print()
    print("  PHASE 3 — Fade Analysis")
    print("    Simulate taking OPPOSITE direction of every bleeder signal")
    print("    If faded PF > 1.2 → new setup viable")
    print("="*60)

    # ── PHASE 1: CORE PERSONALITY A ──────────────────────────────────────────
    print("\n\n>>> PHASE 1 — CORE PERSONALITY A\n")

    phase1_config = build_config(
        extra_disabled=[],  # only the always_disabled list applies
    )

    # Verify CHOCH is NOT in disabled list
    assert "CHOCH" not in [s.upper() for s in phase1_config["disabled_setups"]], \
        "ERROR: CHOCH is disabled — fix config!"
    print(f"  ✅ Config check: CHOCH is enabled")
    print(f"  Disabled setups: {phase1_config['disabled_setups']}\n")

    phase1_trades = []
    phase1_summary = {}

    for pair in PAIRS:
        trades = run_single_pair(pair, phase1_config, label="P1")
        phase1_trades.extend(trades)
        save_csv(trades, f"pass13a_{pair}.csv")
        gc.collect()

    phase1_summary = summarize(phase1_trades, "PHASE 1 — PERSONALITY A (CHOCH+LSR+FVG+OB+ENG)")
    save_csv(phase1_trades, "pass13a_phase1_all.csv")

    # ── PHASE 2: BLEEDERS ISOLATED ───────────────────────────────────────────
    print("\n\n>>> PHASE 2 — CONFIRMED BLEEDERS ISOLATED\n")
    print("  Running LH_LL + HH_HL only to collect signals for fade test\n")

    # Enable ONLY the two bleeders — disable everything else including CHOCH
    bleeder_config = build_config(
        extra_disabled=[
            "CHOCH",
            "LIQUIDITY_SWEEP_REVERSAL",
            "FVG",
            "ORDER_BLOCK",
            "ENGULFING",
            "SCALP",
            "SNIPER",
        ]
    )
    # Re-enable the bleeders we want to test
    bleeder_config["disabled_setups"] = [
        s for s in bleeder_config["disabled_setups"]
        if s not in ["LH_LL_CONTINUATION", "HH_HL_CONTINUATION"]
    ]

    print(f"  Bleeder config disabled: {bleeder_config['disabled_setups']}")
    print(f"  (LH_LL + HH_HL should be ACTIVE)\n")

    bleeder_trades = []
    for pair in PAIRS:
        trades = run_single_pair(pair, bleeder_config, label="P2-BLEEDERS")
        bleeder_trades.extend(trades)
        gc.collect()

    summarize(bleeder_trades, "PHASE 2 — BLEEDERS (LH_LL + HH_HL)")
    save_csv(bleeder_trades, "pass13a_phase2_bleeders.csv")

    # Split by setup for individual fade analysis
    lh_ll_trades = [t for t in bleeder_trades
                    if getattr(t, 'setup_type', '') == 'LH_LL_CONTINUATION']
    hh_hl_trades = [t for t in bleeder_trades
                    if getattr(t, 'setup_type', '') == 'HH_HL_CONTINUATION']

    # ── PHASE 3: FADE ANALYSIS ───────────────────────────────────────────────
    print("\n\n>>> PHASE 3 — FADE ANALYSIS\n")

    fade_analysis(bleeder_trades, "ALL BLEEDERS COMBINED (LH_LL + HH_HL)")
    fade_analysis(lh_ll_trades,   "LH_LL_CONTINUATION only")
    fade_analysis(hh_hl_trades,   "HH_HL_CONTINUATION only")

    # ── GRAND COMPARISON ─────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  FINAL VERDICT")
    print("="*60)

    p1_pf   = phase1_summary.get('pf', 0)
    p1_pips = phase1_summary.get('pips', 0)
    p1_tpw  = phase1_summary.get('tpw', 0)

    faded_pips = -sum(float(t.pnl_pips or 0) for t in bleeder_trades)
    combined_pips = p1_pips + faded_pips

    print(f"\n  Personality A (Phase 1):         {p1_pips:+.1f} pips | PF {p1_pf:.2f}")
    print(f"  Faded bleeders (Phase 3):        {faded_pips:+.1f} pips")
    print(f"  Combined if both run:            {combined_pips:+.1f} pips")
    print()

    if faded_pips > 0:
        print("  ✅ Fading bleeders ADDS value — worth building as a separate signal")
        print("     Recommendation: implement ANTI_LH_LL and ANTI_HH_HL as new setups")
        print("     that take the OPPOSITE direction with the same SL/TP structure")
    else:
        print("  ❌ Fading bleeders does NOT add value")
        print("     The losses come from bad timing/R:R not wrong direction")
        print("     Keep bleeders permanently disabled, do not attempt to fade them")

    print()
    print(f"  Personality B baseline (Pass 12): +338.4 pips | PF 2.13")
    print(f"  Personality A (this run):          {p1_pips:+.1f} pips | PF {p1_pf:.2f}")

    if p1_pf > 2.13:
        print("  ✅ Personality A BEATS Personality B — use as primary system")
    elif p1_pf > 1.5:
        print("  ✅ Personality A viable — higher frequency offsets lower PF")
    else:
        print("  ⚠️  Personality A underperforms — Personality B remains primary")

    print("\n" + "="*60)
    print("  Pass 13A complete.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()