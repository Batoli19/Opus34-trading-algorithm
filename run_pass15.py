"""
run_pass15.py — PASS 15: Direction Filters + FVG Fix + Giveback Guard Tuning
Run from project root: python run_pass15.py

Applies all findings from Pass 14 loss autopsy:
  Fix 1 — Direction filters: cut GBPUSD BUY + USDJPY SELL (saves -1071p of losses)
  Fix 2 — FVG restricted to London Close only (removes -171p London Open bleed)
  Fix 3 — Giveback Guard tuning: test 4 activate_at_r values vs 3 max_giveback_pct values

Configs tested:
  A — Baseline (current, no fixes)
  B — Fix 1 only (direction filters)
  C — Fix 1 + Fix 2 (direction + FVG London Close)
  D — Fix 1 + Fix 2 + Guard tuned (best guard setting)
  E — Guard matrix: 4x3 = 12 combinations on config C
"""

import sys, os, gc, json, csv, copy
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "python"))

# ── CONFIG ────────────────────────────────────────────────────────────────────
with open("config/settings.json", encoding="utf-8") as f:
    BASE_CONFIG = json.load(f)

PAIRS     = ["EURUSD", "USDJPY", "GBPUSD"]
DATA_DIR  = "data/m5_xm"
DATE_FROM = datetime(2024, 11, 5, tzinfo=timezone.utc)
DATE_TO   = datetime(2026, 2, 27, tzinfo=timezone.utc)

# Direction filters confirmed by autopsy
# USDJPY SELL: PF 0.71, -608p | GBPUSD BUY: PF 0.72, -463p
DIRECTION_FILTERS = {
    "USDJPY": "BUY",    # only allow BUY on USDJPY
    "GBPUSD": "SELL",   # only allow SELL on GBPUSD
    "EURUSD": "BOTH",   # both directions fine
}

# ── CONFIG BUILDER ────────────────────────────────────────────────────────────
def build_config(
    direction_filters=False,
    fvg_lc_only=False,
    activate_at_r=0.5,
    max_giveback_pct=0.01,
):
    cfg = copy.deepcopy(BASE_CONFIG)

    # Always disabled
    cfg["disabled_setups"] = [
        "PIN_BAR", "LH_LL_CONTINUATION", "HH_HL_CONTINUATION",
        "LIQUIDITY_GRAB_CONTINUATION", "FVG_CONTINUATION", "CONTINUATION_OB",
        "ORDER_BLOCK",
    ]

    # Kill zones — corrected ICT
    cfg.setdefault("ict", {}).setdefault("kill_zones", {}).update({
        "london_open":  {"start": "06:00", "end": "09:00", "tz": "UTC"},
        "ny_open":      {"start": "13:30", "end": "16:00", "tz": "UTC"},
        "london_close": {"start": "15:00", "end": "17:00", "tz": "UTC"},
    })
    cfg.setdefault("hybrid", {})["allowed_kill_zones"] = [
        "LONDON_OPEN", "LONDON_CLOSE"
    ]

    # Direction filters per symbol
    if direction_filters:
        cfg.setdefault("execution", {}).setdefault("per_symbol", {})
        cfg["execution"]["per_symbol"]["USDJPY"] = {"allowed_directions": ["BUY"]}
        cfg["execution"]["per_symbol"]["GBPUSD"] = {"allowed_directions": ["SELL"]}
        cfg["execution"]["per_symbol"]["EURUSD"] = {"allowed_directions": ["BUY", "SELL"]}

    # FVG London Close only
    if fvg_lc_only:
        # FVG is only allowed in LONDON_CLOSE session
        cfg.setdefault("execution", {}).setdefault("setup_session_restrictions", {})
        cfg["execution"]["setup_session_restrictions"]["FVG_ENTRY"] = ["LONDON_CLOSE"]
    else:
        # FVG allowed everywhere (baseline behaviour)
        cfg.setdefault("execution", {}).setdefault("setup_session_restrictions", {})
        cfg["execution"]["setup_session_restrictions"].pop("FVG_ENTRY", None)

    # Trade management
    cfg.setdefault("trade_management", {}).update({
        "giveback_guard": {
            "enabled": True,
            "activate_at_r": activate_at_r,
            "max_giveback_pct": max_giveback_pct,
        },
        "partials": {
            "enabled": True,
            "tp1_r": 1.0,
            "tp1_close_pct": 0.6,
            "tp1_sl_mode": "BE_PLUS",
            "tp1_be_plus_r": 0.5,
            "trail_only_after_tp1": True,
        },
    })

    cfg.setdefault("risk", {})["risk_per_trade_pct"] = 1.0
    cfg.setdefault("execution", {}).update({
        "min_rr": 1.5,
        "enforce_killzones": True,
    })

    return cfg


# ── RUNNER ────────────────────────────────────────────────────────────────────
def run_config(label, cfg, pairs=PAIRS, verbose=True):
    from backtester import BacktestEngine

    # Check if setup_session_restrictions is supported by backtester
    # If not, we handle FVG LC-only by post-filtering
    fvg_lc_restriction = cfg.get("execution", {}).get(
        "setup_session_restrictions", {}
    ).get("FVG_ENTRY")

    all_trades = []
    for pair in pairs:
        if verbose:
            print(f"  [{label}] {pair} @ {datetime.now().strftime('%H:%M:%S')}", end="", flush=True)

        engine = BacktestEngine(
            config=cfg,
            data_dir=DATA_DIR,
            use_sniper_filter=False,
            max_open_trades=2,
            one_trade_per_symbol=True,
            signal_cooldown_bars=6,
            disabled_setups=cfg["disabled_setups"],
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

        # Post-filter: if FVG LC-only restriction, remove FVG trades outside LC
        if fvg_lc_restriction:
            before = len(closed)
            closed = [
                t for t in closed
                if not (
                    str(getattr(t, "setup_type", "")).upper() == "FVG_ENTRY"
                    and str(getattr(t, "kill_zone", "") or getattr(t, "killzone", "")).upper() != "LONDON_CLOSE"
                )
            ]
            removed = before - len(closed)
            if verbose and removed:
                print(f" (FVG LC filter: -{removed})", end="", flush=True)

        if verbose:
            print(f" → {len(closed)} trades")

        all_trades.extend(closed)
        del engine, trades
        gc.collect()

    return all_trades


def trade_pnl(t):
    return float(getattr(t, "pnl_pips", 0) or 0)

def summarize(trades, label, short=False):
    if not trades:
        print(f"  {label}: 0 trades")
        return {"trades": 0, "wr": 0, "pf": 0, "pips": 0}

    wins   = [t for t in trades if trade_pnl(t) > 0]
    losses = [t for t in trades if trade_pnl(t) <= 0]
    gw  = sum(trade_pnl(t) for t in wins)
    gl  = abs(sum(trade_pnl(t) for t in losses))
    pf  = gw / gl if gl > 0 else float("inf")
    net = gw - gl
    wr  = len(wins) / len(trades) * 100
    weeks = (DATE_TO - DATE_FROM).days / 7
    avg_w = gw / len(wins)   if wins   else 0
    avg_l = gl / len(losses) if losses else 0

    if short:
        print(f"  {label:<45} {len(trades):>4}tr | WR {wr:.0f}% | PF {pf:.2f} | {net:>+8.1f}p | {net/weeks:>+6.1f}p/wk")
        return {"trades": len(trades), "wr": wr, "pf": pf, "pips": net, "ppw": net/weeks}

    print(f"\n{'='*62}")
    print(f"  {label}")
    print(f"{'='*62}")
    print(f"  Trades:    {len(trades)} ({len(trades)/weeks:.1f}/week)")
    print(f"  Win Rate:  {wr:.1f}%  ({len(wins)}W / {len(losses)}L)")
    print(f"  PF:        {pf:.2f}")
    print(f"  Pips:      {net:+.1f}  ({net/weeks:+.1f}/week)")
    print(f"  Avg Win:   +{avg_w:.1f}p  |  Avg Loss: -{avg_l:.1f}p  |  R:R {avg_w/avg_l:.2f}:1" if avg_l else "")

    # Exit reasons
    exits = defaultdict(lambda: [0, 0.0])
    for t in trades:
        r = str(getattr(t, "exit_reason", "UNKNOWN"))
        exits[r][0] += 1
        exits[r][1] += trade_pnl(t)
    print(f"\n  Exit reasons:")
    for r, (cnt, pip) in sorted(exits.items(), key=lambda x: -x[1][0]):
        print(f"    {r:<22} {cnt:>4}tr | {pip:>+8.1f}p | avg {pip/cnt:>+6.1f}p")

    # By setup
    by_setup = defaultdict(list)
    for t in trades: by_setup[str(getattr(t, "setup_type", "?"))].append(t)
    print(f"\n  By Setup:")
    for s, st in sorted(by_setup.items(), key=lambda x: -sum(trade_pnl(t) for t in x[1])):
        sw = [t for t in st if trade_pnl(t) > 0]
        net_s = sum(trade_pnl(t) for t in st)
        gw_s = sum(trade_pnl(t) for t in sw)
        gl_s = abs(sum(trade_pnl(t) for t in st if trade_pnl(t) <= 0))
        pf_s = gw_s / gl_s if gl_s > 0 else float("inf")
        v = "✅" if net_s > 0 else "❌"
        print(f"    {v} {s:<35} {len(st):>3}tr | WR {len(sw)/len(st)*100:.0f}% | PF {pf_s:.2f} | {net_s:>+8.1f}p")

    # By session
    by_kz = defaultdict(list)
    for t in trades:
        kz = str(getattr(t, "kill_zone", "") or getattr(t, "killzone", "") or "?")
        by_kz[kz].append(t)
    print(f"\n  By Session:")
    for kz, kt in sorted(by_kz.items()):
        kw = [t for t in kt if trade_pnl(t) > 0]
        net_k = sum(trade_pnl(t) for t in kt)
        gw_k = sum(trade_pnl(t) for t in kw)
        gl_k = abs(sum(trade_pnl(t) for t in kt if trade_pnl(t) <= 0))
        pf_k = gw_k / gl_k if gl_k > 0 else float("inf")
        print(f"    {kz:<22} {len(kt):>3}tr | WR {len(kw)/len(kt)*100:.0f}% | PF {pf_k:.2f} | {net_k:>+8.1f}p")

    # By pair+direction
    combos = defaultdict(list)
    for t in trades:
        combos[f"{getattr(t,'symbol','?')} {getattr(t,'direction','?')}"].append(t)
    print(f"\n  By Pair+Direction:")
    for k, kt in sorted(combos.items(), key=lambda x: -sum(trade_pnl(t) for t in x[1])):
        kw = [t for t in kt if trade_pnl(t) > 0]
        net_k = sum(trade_pnl(t) for t in kt)
        gw_k = sum(trade_pnl(t) for t in kw)
        gl_k = abs(sum(trade_pnl(t) for t in kt if trade_pnl(t) <= 0))
        pf_k = gw_k / gl_k if gl_k > 0 else float("inf")
        v = "✅" if net_k > 0 else "❌"
        print(f"    {v} {k:<15} {len(kt):>3}tr | WR {len(kw)/len(kt)*100:.0f}% | PF {pf_k:.2f} | {net_k:>+8.1f}p")

    # Monthly
    by_month = defaultdict(list)
    for t in trades:
        by_month[str(getattr(t, "entry_time", ""))[:7]].append(t)
    green = red = 0
    print(f"\n  Monthly:")
    for m in sorted(by_month.keys()):
        mt = by_month[m]; mw = [t for t in mt if trade_pnl(t) > 0]
        net_m = sum(trade_pnl(t) for t in mt)
        if net_m > 0: green += 1
        else: red += 1
        print(f"    {'✅' if net_m>0 else '❌'} {m}  {len(mt):>3}tr | WR {len(mw)/len(mt)*100:.0f}% | {net_m:>+8.1f}p")
    print(f"\n  Profitable months: {green}/{green+red} = {green/(green+red)*100:.0f}%")
    print(f"{'='*62}")

    return {"trades": len(trades), "wr": wr, "pf": pf, "pips": net, "ppw": net/weeks}


def save_csv(trades, filename):
    if not trades: return
    fields = ["symbol","setup_type","direction","kill_zone",
              "entry_time","exit_time","pnl_pips","exit_reason"]
    with open(filename, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for t in trades:
            row = {field: getattr(t, field, "") for field in fields}
            if not row["kill_zone"]:
                row["kill_zone"] = getattr(t, "killzone", "")
            w.writerow(row)
    print(f"  Saved → {filename}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "="*62)
    print("  PASS 15 — DIRECTION FILTERS + FVG FIX + GUARD TUNING")
    print("="*62)
    print(f"  Pairs:    {PAIRS}")
    print(f"  Range:    {DATE_FROM.date()} → {DATE_TO.date()}")
    print(f"\n  Fixes being tested:")
    print(f"  Fix 1 — Cut GBPUSD BUY + USDJPY SELL (autopsy: -1071p bleed)")
    print(f"  Fix 2 — FVG only in London Close (autopsy: LO kills FVG -171p)")
    print(f"  Fix 3 — Giveback Guard tuning (current: activate@0.5R, 1% cutoff)")
    print(f"           329/335 wins cut early at +28p — should be reaching +45-60p")
    print("="*62)

    results = {}

    # ── CONFIG A — BASELINE (no fixes, current settings) ─────────────────────
    print(f"\n\n>>> A — BASELINE (current, no fixes)")
    cfg_A = build_config(
        direction_filters=False,
        fvg_lc_only=False,
        activate_at_r=0.5,
        max_giveback_pct=0.01,
    )
    trades_A = run_config("A-BASELINE", cfg_A)
    results["A"] = summarize(trades_A, "A — BASELINE (CHOCH+LSR+FVG, no fixes)")
    save_csv(trades_A, "pass15_A_baseline.csv")

    # ── CONFIG B — FIX 1 ONLY: direction filters ──────────────────────────────
    print(f"\n\n>>> B — FIX 1: Direction filters only")
    cfg_B = build_config(
        direction_filters=True,
        fvg_lc_only=False,
        activate_at_r=0.5,
        max_giveback_pct=0.01,
    )
    trades_B = run_config("B-DIR_FILTER", cfg_B)
    results["B"] = summarize(trades_B, "B — Fix 1: Direction filters")
    save_csv(trades_B, "pass15_B_dir_filter.csv")

    # ── CONFIG C — FIX 1+2: direction + FVG LC only ───────────────────────────
    print(f"\n\n>>> C — FIX 1+2: Direction filters + FVG London Close only")
    cfg_C = build_config(
        direction_filters=True,
        fvg_lc_only=True,
        activate_at_r=0.5,
        max_giveback_pct=0.01,
    )
    trades_C = run_config("C-DIR+FVG_LC", cfg_C)
    results["C"] = summarize(trades_C, "C — Fix 1+2: Direction + FVG LC only")
    save_csv(trades_C, "pass15_C_dir_fvg_lc.csv")

    # ── CONFIG D — ALL 3 FIXES: best guard setting from matrix below ──────────
    # Run guard matrix first on config C setup, find best, then do full run

    print(f"\n\n>>> D — GIVEBACK GUARD MATRIX (12 combinations on C setup)")
    print(f"  Testing activate_at_r × max_giveback_pct combinations\n")

    activate_values  = [0.5, 1.0, 1.5, 2.0]
    giveback_values  = [0.15, 0.25, 0.35]

    print(f"  {'activate_at_r':>14} | {'max_gb_pct':>10} | {'Trades':>6} | {'WR':>5} | {'PF':>5} | {'Pips':>8} | {'Pips/wk':>7}")
    print(f"  {'-'*70}")

    matrix_results = []
    for act_r in activate_values:
        for gb_pct in giveback_values:
            label = f"guard_{act_r}R_{int(gb_pct*100)}pct"
            cfg_g = build_config(
                direction_filters=True,
                fvg_lc_only=True,
                activate_at_r=act_r,
                max_giveback_pct=gb_pct,
            )
            t = run_config(label, cfg_g, verbose=False)
            w = [x for x in t if trade_pnl(x) > 0]
            l = [x for x in t if trade_pnl(x) <= 0]
            gw = sum(trade_pnl(x) for x in w)
            gl = abs(sum(trade_pnl(x) for x in l))
            pf = gw/gl if gl else float("inf")
            net = gw - gl
            weeks = (DATE_TO - DATE_FROM).days / 7
            wr = len(w)/len(t)*100 if t else 0
            ppw = net/weeks

            is_best = False
            matrix_results.append((act_r, gb_pct, len(t), wr, pf, net, ppw, t))
            print(f"  {act_r:>14} | {gb_pct:>10.0%} | {len(t):>6} | {wr:>4.0f}% | {pf:>5.2f} | {net:>+8.1f} | {ppw:>+7.1f}")
            del t
            gc.collect()

    # Find best by PF
    best = max(matrix_results, key=lambda x: x[4])
    best_act_r, best_gb_pct = best[0], best[1]
    print(f"\n  ✅ Best guard setting: activate_at_r={best_act_r}, max_giveback_pct={best_gb_pct:.0%}")
    print(f"     PF {best[4]:.2f} | {best[5]:+.1f} pips | {best[6]:+.1f} pips/week")

    # Also find best by total pips
    best_pips = max(matrix_results, key=lambda x: x[5])
    if best_pips[0] != best_act_r or best_pips[1] != best_gb_pct:
        print(f"  💰 Best by total pips: activate_at_r={best_pips[0]}, max_giveback_pct={best_pips[1]:.0%}")
        print(f"     PF {best_pips[4]:.2f} | {best_pips[5]:+.1f} pips")

    # ── CONFIG D — ALL 3 FIXES WITH BEST GUARD ────────────────────────────────
    print(f"\n\n>>> E — ALL 3 FIXES with best guard (activate@{best_act_r}R, {best_gb_pct:.0%} cutoff)")
    cfg_E = build_config(
        direction_filters=True,
        fvg_lc_only=True,
        activate_at_r=best_act_r,
        max_giveback_pct=best_gb_pct,
    )
    trades_E = run_config("E-ALL_FIXES", cfg_E)
    results["E"] = summarize(trades_E, f"E — ALL 3 FIXES (guard@{best_act_r}R/{best_gb_pct:.0%})")
    save_csv(trades_E, "pass15_E_all_fixes.csv")

    # ── FINAL COMPARISON TABLE ─────────────────────────────────────────────────
    print(f"\n\n{'='*62}")
    print(f"  PASS 15 — FINAL COMPARISON")
    print(f"{'='*62}")
    print(f"\n  {'Config':<45} {'Tr':>4} {'WR':>5} {'PF':>5} {'Pips':>8} {'p/wk':>6}")
    print(f"  {'-'*72}")
    labels = {
        "A": "A — Baseline (no fixes)",
        "B": "B — Fix 1: Direction filters",
        "C": "C — Fix 1+2: + FVG London Close only",
        "E": f"E — All 3 fixes (guard@{best_act_r}R/{best_gb_pct:.0%})",
    }
    for k, lbl in labels.items():
        r = results.get(k, {})
        if r:
            ppw = r.get("ppw", r["pips"] / ((DATE_TO-DATE_FROM).days/7))
            print(f"  {lbl:<45} {r['trades']:>4} {r['wr']:>4.0f}% {r['pf']:>5.2f} {r['pips']:>+8.1f} {ppw:>+6.1f}")

    print(f"\n  Pass 12 (Personality B reference):       38tr | PF 2.13 | +338p over 2mo")
    print(f"\n  Improvement from baseline to all fixes:")
    if "A" in results and "E" in results:
        pip_gain = results["E"]["pips"] - results["A"]["pips"]
        pf_gain  = results["E"]["pf"]   - results["A"]["pf"]
        print(f"    Pips: {results['A']['pips']:+.1f} → {results['E']['pips']:+.1f} ({pip_gain:+.1f}p)")
        print(f"    PF:   {results['A']['pf']:.2f}  → {results['E']['pf']:.2f}  ({pf_gain:+.2f})")
        print(f"    Trades removed: {results['A']['trades'] - results['E']['trades']}")

    print(f"\n{'='*62}")
    print(f"  Pass 15 complete.")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
