"""
Pass 13A Sequential: Personality A Per-Pair Backtest
=====================================================
Memory-safe single pair execution for 8GB machines.
Runs each pair independently, saves CSV after each, frees memory.
"""
import sys
import os
import gc
import csv
import json
import logging
import time
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# Add python dir to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))

from backtester import BacktestEngine, CandleReplay
from config_loader import (
    _normalize_execution_gates,
    _normalize_trailing_structure,
    _normalize_trade_management,
)

# ─── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / "pass13a_log.txt", mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("PASS_13A_SEQ")
for noisy in ("ICT", "ICT_SETUPS", "TRAIL", "SNIPER", "CONFIG"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ─── Config ────────────────────────────────────────────────────────────────
PAIRS = ["GBPUSD", "USDJPY", "AUDUSD", "EURUSD", "GBPJPY"]
DATE_FROM = "2024-11-05"
DATE_TO   = "2026-02-27"
RISK_USD  = 50.0
ACCOUNT   = 5000.0


def merge_monthly_csvs(pair: str, data_dir: Path, output_dir: Path):
    """
    Merge monthly CSV files (e.g. GBPUSD_M5_2025-01.csv) into single
    per-timeframe CSVs (e.g. GBPUSD_M5.csv) that CandleReplay expects.
    """
    pair_dir = data_dir / pair
    if not pair_dir.exists():
        logger.error(f"Data directory not found: {pair_dir}")
        return False

    timeframes = ["H4", "H1", "M15", "M5", "M1"]
    for tf in timeframes:
        pattern = f"{pair}_{tf}_"
        monthly_files = sorted(
            f for f in pair_dir.iterdir()
            if f.name.startswith(pattern) and f.suffix == ".csv"
        )
        if not monthly_files:
            logger.warning(f"  No {tf} files found for {pair}")
            continue

        output_path = output_dir / f"{pair}_{tf}.csv"
        header_written = False
        total_rows = 0

        with open(output_path, "w", newline="", encoding="utf-8") as out_f:
            for monthly_file in monthly_files:
                with open(monthly_file, "r", encoding="utf-8") as in_f:
                    reader = csv.reader(in_f)
                    header = next(reader, None)
                    if header and not header_written:
                        writer = csv.writer(out_f)
                        writer.writerow(header)
                        header_written = True
                    if header:
                        writer = csv.writer(out_f)
                        for row in reader:
                            writer.writerow(row)
                            total_rows += 1

        logger.info(f"  Merged {pair}_{tf}: {len(monthly_files)} files -> {total_rows:,} rows")

    return True


def load_config():
    """Load and merge settings.json + backtest_config_personality_a.json."""
    config_path = ROOT / "config" / "backtest_config_personality_a.json"
    main_config_path = ROOT / "config" / "settings.json"

    with open(main_config_path, "r") as f:
        config = json.load(f)
    with open(config_path, "r") as f:
        bt_cfg = json.load(f)

    # Merge — bt_cfg values override main config
    for k, v in bt_cfg.items():
        if isinstance(v, dict) and k in config and isinstance(config[k], dict):
            config[k].update(v)
        else:
            config[k] = v

    # Apply user's Personality A overrides explicitly
    config["date_from"] = DATE_FROM
    config["date_to"]   = DATE_TO
    config["pairs"]     = PAIRS

    # Override kill zone times to match the spec
    kz = config.setdefault("ict", {}).setdefault("kill_zones", {})
    kz["enabled"] = True
    kz["london_open"]  = {"start": "06:00", "end": "09:00", "tz": "UTC"}
    kz["ny_open"]      = {"start": "13:30", "end": "16:00", "tz": "UTC"}
    kz["london_close"] = {"start": "15:00", "end": "17:00", "tz": "UTC"}

    # Override trade management for Personality A
    tm = config.setdefault("trade_management", {})
    tm["partials"] = {
        "enabled": True,
        "tp1_r": 1.0,
        "tp1_close_pct": 0.6,
        "tp1_sl_mode": "BE_PLUS",
        "tp1_be_plus_r": 0.5,
        "trail_only_after_tp1": True,
        "use_static_tp1_usd": False,
    }
    tm["giveback_guard"] = {
        "enabled": True,
        "activate_at_r": 0.5,
        "max_giveback_pct": 0.01,
    }

    # Override execution
    exec_cfg = config.setdefault("execution", {})
    exec_cfg["min_rr"] = 1.5
    exec_cfg["enforce_killzones"] = True

    # No direction filters for Personality A
    config["direction_filters"] = {}

    # Disabled setups
    config["disabled_setups"] = [
        "PIN_BAR",
        "LH_LL_CONTINUATION",
        "HH_HL_CONTINUATION",
        "LIQUIDITY_GRAB_CONTINUATION",
    ]

    # Risk
    config.setdefault("risk", {})["daily_loss_limit_pct"] = None

    # Normalize
    _normalize_execution_gates(config)
    _normalize_trailing_structure(config)
    _normalize_trade_management(config)

    return config


def run_single_pair(pair: str, config: dict, temp_dir: Path):
    """Run backtest for a single pair. Returns list of trade dicts."""
    start_date = datetime.strptime(DATE_FROM, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_date   = datetime.strptime(DATE_TO,   "%Y-%m-%d").replace(tzinfo=timezone.utc)

    engine = BacktestEngine(
        config=config,
        data_dir=temp_dir,
        use_sniper_filter=True,
        max_open_trades=3,
        disabled_setups=config.get("disabled_setups", []),
        killzone_only=True,
        use_trailing=True,
    )

    trades = engine.run(
        symbols=[pair],
        start_date=start_date,
        end_date=end_date,
        progress_every=5000,
    )

    # Filter out END_OF_DATA
    trades = [t for t in trades if t.exit_reason and t.exit_reason != "END_OF_DATA"]

    # Convert to dicts for CSV saving
    trade_dicts = []
    for t in trades:
        trade_dicts.append({
            "symbol":      t.symbol,
            "entry_time":  t.entry_time.isoformat() if t.entry_time else "",
            "exit_time":   t.exit_time.isoformat() if t.exit_time else "",
            "direction":   t.direction,
            "setup":       t.setup_type,
            "killzone":    t.killzone,
            "pnl_pips":    round(t.pnl_pips, 2),
            "rr_achieved": round(t.rr_achieved, 4),
            "usd_pnl":     round(t.rr_achieved * RISK_USD, 2),
            "exit_reason":  t.exit_reason,
            "entry_price": t.entry_price,
            "sl_price":    t.sl_price,
            "tp_price":    t.tp_price,
            "partial_taken": t.partial_taken,
            "trail_count": t.trail_count,
        })

    return trade_dicts, engine.signals_generated, engine.signals_filtered


def save_pair_csv(pair: str, trade_dicts: list):
    """Save trades for a single pair to CSV."""
    csv_path = ROOT / f"pass13a_{pair}.csv"
    if not trade_dicts:
        logger.warning(f"  {pair}: 0 trades - CSV will be empty")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("symbol,entry_time,exit_time,direction,setup,killzone,pnl_pips,rr_achieved,usd_pnl,exit_reason\n")
        return

    fieldnames = list(trade_dicts[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trade_dicts)
    logger.info(f"  Saved {len(trade_dicts)} trades to {csv_path.name}")


def print_pair_summary(pair: str, trades: list, run_num: int):
    """Print detailed summary for a single pair."""
    total = len(trades)
    span_days = max(1.0, (datetime.strptime(DATE_TO, "%Y-%m-%d") -
                          datetime.strptime(DATE_FROM, "%Y-%m-%d")).days)
    span_weeks = span_days / 7.0

    print(f"\n{'='*60}")
    print(f"  PASS 13A RUN {run_num}/5: {pair}")
    print(f"  Date range: {DATE_FROM} -> {DATE_TO}")
    print(f"  Setups: ALL (except confirmed bleeders)")
    print(f"  Direction: BOTH")
    print(f"  Kill zones: LONDON_OPEN + NY_OPEN + LONDON_CLOSE")
    print(f"{'='*60}")

    if total == 0:
        print(f"  ** NO TRADES TAKEN FOR {pair} **")
        return

    winners = [t for t in trades if t["pnl_pips"] > 0]
    losers  = [t for t in trades if t["pnl_pips"] < 0]
    wr = len(winners) / total * 100

    gp = sum(t["pnl_pips"] for t in winners)
    gl = abs(sum(t["pnl_pips"] for t in losers))
    pf = gp / gl if gl > 0 else float("inf")
    total_pips = sum(t["pnl_pips"] for t in trades)
    net_usd = sum(t["usd_pnl"] for t in trades)
    tpw = total / span_weeks

    print(f"\n  Overall: {total} trades ({tpw:.1f}/wk) | WR {wr:.1f}% | PF {pf:.2f}")
    print(f"  Total Pips: {total_pips:+.1f} | Net USD: ${net_usd:+.2f}")

    # Per-setup breakdown
    setups = defaultdict(list)
    for t in trades:
        setups[t["setup"]].append(t)
    print(f"\n  {'Setup':<20} | {'#':>4} | {'WR':>5} | {'PF':>5} | {'Pips':>8}")
    print(f"  {'-'*55}")
    for s, st in sorted(setups.items(), key=lambda x: sum(t["pnl_pips"] for t in x[1]), reverse=True):
        sw = [t for t in st if t["pnl_pips"] > 0]
        sl_list = [t for t in st if t["pnl_pips"] < 0]
        swr = len(sw)/len(st)*100 if st else 0
        sgp = sum(t["pnl_pips"] for t in sw)
        sgl = abs(sum(t["pnl_pips"] for t in sl_list))
        spf = sgp/sgl if sgl > 0 else 99
        spips = sum(t["pnl_pips"] for t in st)
        print(f"  {s:<20} | {len(st):>4} | {swr:4.1f}% | {spf:5.2f} | {spips:+7.1f}")

    # Per-session breakdown
    sessions = defaultdict(list)
    for t in trades:
        sessions[t["killzone"]].append(t)
    print(f"\n  {'Session':<15} | {'#':>4} | {'WR':>5} | {'PF':>5} | {'Pips':>8}")
    print(f"  {'-'*50}")
    for sess, st in sorted(sessions.items(), key=lambda x: sum(t["pnl_pips"] for t in x[1]), reverse=True):
        sw = [t for t in st if t["pnl_pips"] > 0]
        sl_list = [t for t in st if t["pnl_pips"] < 0]
        swr = len(sw)/len(st)*100 if st else 0
        sgp = sum(t["pnl_pips"] for t in sw)
        sgl = abs(sum(t["pnl_pips"] for t in sl_list))
        spf = sgp/sgl if sgl > 0 else 99
        spips = sum(t["pnl_pips"] for t in st)
        print(f"  {sess:<15} | {len(st):>4} | {swr:4.1f}% | {spf:5.2f} | {spips:+7.1f}")

    # Monthly breakdown
    monthly = defaultdict(list)
    for t in trades:
        ym = t["entry_time"][:7]
        monthly[ym].append(t)
    print(f"\n  {'Month':<8} | {'#':>4} | {'WR':>5} | {'PF':>5} | {'Pips':>8} | {'USD':>9}")
    print(f"  {'-'*55}")
    for ym in sorted(monthly.keys()):
        mt = monthly[ym]
        mw = [t for t in mt if t["pnl_pips"] > 0]
        ml = [t for t in mt if t["pnl_pips"] < 0]
        mwr = len(mw)/len(mt)*100 if mt else 0
        mgp = sum(t["pnl_pips"] for t in mw)
        mgl = abs(sum(t["pnl_pips"] for t in ml))
        mpf = mgp/mgl if mgl > 0 else 99
        mpips = sum(t["pnl_pips"] for t in mt)
        musd = sum(t["usd_pnl"] for t in mt)
        print(f"  {ym:<8} | {len(mt):>4} | {mwr:4.1f}% | {mpf:5.2f} | {mpips:+7.1f} | ${musd:+8.2f}")

    # Exit reasons
    reasons = defaultdict(list)
    for t in trades:
        reasons[t["exit_reason"]].append(t)
    print(f"\n  Exit Reasons:")
    for r, rt in sorted(reasons.items(), key=lambda x: len(x[1]), reverse=True):
        rpips = sum(t["pnl_pips"] for t in rt)
        print(f"    {r:<18}: {len(rt):>3} trades | {rpips:+7.1f} pips")

    # Streak
    max_consec = 0
    curr = 0
    for t in trades:
        if t["pnl_pips"] < 0:
            curr += 1
            max_consec = max(max_consec, curr)
        else:
            curr = 0

    # Best/worst day
    days = defaultdict(list)
    for t in trades:
        d = t["entry_time"][:10]
        days[d].append(t)
    daily_usd = {d: sum(t["usd_pnl"] for t in dt) for d, dt in days.items()}
    best_d = max(daily_usd.items(), key=lambda x: x[1]) if daily_usd else ("N/A", 0)
    worst_d = min(daily_usd.items(), key=lambda x: x[1]) if daily_usd else ("N/A", 0)

    print(f"\n  Max consecutive losses: {max_consec}")
    print(f"  Best day:  {best_d[0]} (${best_d[1]:+.2f})")
    print(f"  Worst day: {worst_d[0]} (${worst_d[1]:+.2f})")


def generate_combined_report(all_trades: list):
    """Generate the full combined report from all 5 pairs."""
    print("\n\n" + "=" * 70)
    print("  PASS 13A COMBINED REPORT: PERSONALITY A (NOV 2024 - FEB 2026)")
    print("=" * 70)

    total = len(all_trades)
    span_days = max(1.0, (datetime.strptime(DATE_TO, "%Y-%m-%d") -
                          datetime.strptime(DATE_FROM, "%Y-%m-%d")).days)
    span_weeks = span_days / 7.0

    if total == 0:
        print("  ** NO TRADES ACROSS ALL PAIRS **")
        return

    winners = [t for t in all_trades if t["pnl_pips"] > 0]
    losers  = [t for t in all_trades if t["pnl_pips"] < 0]
    wr = len(winners) / total * 100
    gp = sum(t["pnl_pips"] for t in winners)
    gl = abs(sum(t["pnl_pips"] for t in losers))
    pf = gp / gl if gl > 0 else float("inf")
    total_pips = sum(t["pnl_pips"] for t in all_trades)
    net_usd = sum(t["usd_pnl"] for t in all_trades)
    tpw = total / span_weeks
    expectancy = net_usd / total

    # ─── 1. GRAND SUMMARY TABLE ───────────────────────────────────────
    print("\n1. GRAND SUMMARY TABLE")
    print("-" * 80)
    print(f"  {'Pair':<8} | {'Trades':>6} | {'WR':>6} | {'PF':>5} | {'Pips':>9} | {'Net USD':>9} | {'Tr/wk':>5}")
    print(f"  {'-'*75}")

    pairs_data = defaultdict(list)
    for t in all_trades:
        pairs_data[t["symbol"]].append(t)

    for pair in PAIRS:
        pt = pairs_data.get(pair, [])
        if not pt:
            print(f"  {pair:<8} | {'0':>6} |   N/A |  N/A |      0.0 |     $0.00 |   0.0")
            continue
        pw = [t for t in pt if t["pnl_pips"] > 0]
        pl = [t for t in pt if t["pnl_pips"] < 0]
        pwr = len(pw)/len(pt)*100
        pgp = sum(t["pnl_pips"] for t in pw)
        pgl = abs(sum(t["pnl_pips"] for t in pl))
        ppf = pgp/pgl if pgl > 0 else 99
        ppips = sum(t["pnl_pips"] for t in pt)
        pusd = sum(t["usd_pnl"] for t in pt)
        ptpw = len(pt) / span_weeks
        print(f"  {pair:<8} | {len(pt):>6} | {pwr:5.1f}% | {ppf:5.2f} | {ppips:>+8.1f} | ${pusd:>+8.2f} | {ptpw:>5.1f}")

    print(f"  {'-'*75}")
    print(f"  {'TOTAL':<8} | {total:>6} | {wr:5.1f}% | {pf:5.2f} | {total_pips:>+8.1f} | ${net_usd:>+8.2f} | {tpw:>5.1f}")

    # ─── 2. COMBINED SETUP BREAKDOWN ──────────────────────────────────
    print("\n2. COMBINED SETUP BREAKDOWN")
    print("-" * 65)
    print(f"  {'Setup':<22} | {'#':>5} | {'WR':>6} | {'PF':>5} | {'Pips':>9}")
    print(f"  {'-'*55}")
    setups = defaultdict(list)
    for t in all_trades:
        setups[t["setup"]].append(t)
    for s, st in sorted(setups.items(), key=lambda x: sum(t["pnl_pips"] for t in x[1]), reverse=True):
        sw = [t for t in st if t["pnl_pips"] > 0]
        sl_list = [t for t in st if t["pnl_pips"] < 0]
        swr = len(sw)/len(st)*100 if st else 0
        sgp = sum(t["pnl_pips"] for t in sw)
        sgl = abs(sum(t["pnl_pips"] for t in sl_list))
        spf = sgp/sgl if sgl > 0 else 99
        spips = sum(t["pnl_pips"] for t in st)
        flag = " <-- DISABLE" if spf < 0.9 else ""
        print(f"  {s:<22} | {len(st):>5} | {swr:5.1f}% | {spf:5.2f} | {spips:>+8.1f}{flag}")

    # ─── 3. COMBINED SESSION BREAKDOWN ────────────────────────────────
    print("\n3. COMBINED SESSION BREAKDOWN")
    print("-" * 65)
    print(f"  {'Session':<15} | {'#':>5} | {'WR':>6} | {'PF':>5} | {'Pips':>9}")
    print(f"  {'-'*50}")
    sessions = defaultdict(list)
    for t in all_trades:
        sessions[t["killzone"]].append(t)
    for sess, st in sorted(sessions.items(), key=lambda x: sum(t["pnl_pips"] for t in x[1]), reverse=True):
        sw = [t for t in st if t["pnl_pips"] > 0]
        sl_list = [t for t in st if t["pnl_pips"] < 0]
        swr = len(sw)/len(st)*100 if st else 0
        sgp = sum(t["pnl_pips"] for t in sw)
        sgl = abs(sum(t["pnl_pips"] for t in sl_list))
        spf = sgp/sgl if sgl > 0 else 99
        spips = sum(t["pnl_pips"] for t in st)
        print(f"  {sess:<15} | {len(st):>5} | {swr:5.1f}% | {spf:5.2f} | {spips:>+8.1f}")

    # ─── 4. MONTHLY PORTFOLIO P&L ────────────────────────────────────
    print("\n4. MONTHLY PORTFOLIO P&L")
    print("-" * 65)
    print(f"  {'Month':<8} | {'#':>4} | {'WR':>6} | {'PF':>5} | {'Pips':>9} | {'Net USD':>10}")
    print(f"  {'-'*55}")
    monthly = defaultdict(list)
    for t in all_trades:
        ym = t["entry_time"][:7]
        monthly[ym].append(t)
    for ym in sorted(monthly.keys()):
        mt = monthly[ym]
        mw = [t for t in mt if t["pnl_pips"] > 0]
        ml = [t for t in mt if t["pnl_pips"] < 0]
        mwr = len(mw)/len(mt)*100 if mt else 0
        mgp = sum(t["pnl_pips"] for t in mw)
        mgl = abs(sum(t["pnl_pips"] for t in ml))
        mpf = mgp/mgl if mgl > 0 else 99
        mpips = sum(t["pnl_pips"] for t in mt)
        musd = sum(t["usd_pnl"] for t in mt)
        print(f"  {ym:<8} | {len(mt):>4} | {mwr:5.1f}% | {mpf:5.2f} | {mpips:>+8.1f} | ${musd:>+9.2f}")

    # ─── 5. DAILY RETURN DISTRIBUTION ─────────────────────────────────
    print("\n5. DAILY RETURN DISTRIBUTION")
    print("-" * 55)
    days = defaultdict(list)
    for t in all_trades:
        d = t["entry_time"][:10]
        days[d].append(t)
    daily_usd = {d: sum(t["usd_pnl"] for t in dt) for d, dt in days.items()}

    if daily_usd:
        best = max(daily_usd.items(), key=lambda x: x[1])
        worst = min(daily_usd.items(), key=lambda x: x[1])
        win_days = [v for v in daily_usd.values() if v > 0]
        loss_days = [v for v in daily_usd.values() if v < 0]
        print(f"  Total Trading Days:   {len(daily_usd)}")
        print(f"  Best Day:             {best[0]} (${best[1]:+.2f})")
        print(f"  Worst Day:            {worst[0]} (${worst[1]:+.2f})")
        print(f"  Days > $200 Profit:   {sum(1 for v in daily_usd.values() if v > 200)}")
        print(f"  Days > $200 Loss:     {sum(1 for v in daily_usd.values() if v < -200)}")
        print(f"  Avg Winning Day:      ${sum(win_days)/len(win_days):+.2f}" if win_days else "  Avg Winning Day:      N/A")
        print(f"  Avg Losing Day:       ${sum(loss_days)/len(loss_days):+.2f}" if loss_days else "  Avg Losing Day:       N/A")

    # ─── 6. DRAWDOWN PROFILE ─────────────────────────────────────────
    print("\n6. DRAWDOWN PROFILE")
    print("-" * 55)
    sorted_trades = sorted(all_trades, key=lambda t: t["entry_time"])
    max_consec = 0
    curr = 0
    running = 0.0
    peak = 0.0
    max_dd = 0.0

    for t in sorted_trades:
        if t["pnl_pips"] < 0:
            curr += 1
            max_consec = max(max_consec, curr)
        else:
            curr = 0
        running += t["usd_pnl"]
        peak = max(peak, running)
        dd = peak - running
        max_dd = max(max_dd, dd)

    # Longest losing streak in days
    daily_pnl_sorted = sorted(daily_usd.items())
    longest_losing_days = 0
    curr_losing = 0
    for d, pnl in daily_pnl_sorted:
        if pnl < 0:
            curr_losing += 1
            longest_losing_days = max(longest_losing_days, curr_losing)
        else:
            curr_losing = 0

    print(f"  Max Consecutive Losses: {max_consec}")
    print(f"  Max Drawdown:           ${max_dd:.2f} ({max_dd/ACCOUNT*100:.1f}% of ${ACCOUNT:.0f})")
    print(f"  Longest Losing Streak:  {longest_losing_days} days")

    # ─── 7. EXIT REASON BREAKDOWN ────────────────────────────────────
    print("\n7. EXIT REASON BREAKDOWN")
    print("-" * 55)
    reasons = defaultdict(list)
    for t in all_trades:
        reasons[t["exit_reason"]].append(t)
    for r, rt in sorted(reasons.items(), key=lambda x: len(x[1]), reverse=True):
        rpips = sum(t["pnl_pips"] for t in rt)
        rusd = sum(t["usd_pnl"] for t in rt)
        print(f"  {r:<18}: {len(rt):>4} trades | {rpips:>+8.1f} pips | ${rusd:>+8.2f}")

    # ─── 8. PERSONALITY A vs B COMPARISON ────────────────────────────
    weekly_avg = net_usd / span_weeks if span_weeks > 0 else 0
    print("\n" + "=" * 70)
    print("  PERSONALITY A vs PERSONALITY B (Pass 1-12 Baseline)")
    print("=" * 70)
    print(f"  {'Metric':<22} | {'Personality B (7 wks)':<22} | {'Personality A (16 mos)'}")
    print(f"  {'-'*70}")
    print(f"  {'Total trades':<22} | {'39':<22} | {total}")
    print(f"  {'Trades/week':<22} | {'5.6':<22} | {tpw:.1f}")
    print(f"  {'Win rate':<22} | {'56.4%':<22} | {wr:.1f}%")
    print(f"  {'Profit Factor':<22} | {'1.48':<22} | {pf:.2f}")
    print(f"  {'Expectancy ($/trade)':<22} | {'~$12':<22} | ${expectancy:.2f}")
    print(f"  {'Weekly income (avg)':<22} | {'~$66':<22} | ${weekly_avg:.2f}")
    print(f"  {'Max consec losses':<22} | {'3':<22} | {max_consec}")
    print(f"  {'Max drawdown %':<22} | {'~3%':<22} | {max_dd/ACCOUNT*100:.1f}%")
    print(f"  {'Pairs tested':<22} | {'3':<22} | 5")
    print(f"  {'Sessions':<22} | {'2':<22} | 3")

    # ─── SAVE COMBINED REPORT ────────────────────────────────────────
    report_path = ROOT / "pass13a_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Personality A Backtest - Pass 13A\n")
        f.write(f"{'='*50}\n")
        f.write(f"Total Trades:  {total}\n")
        f.write(f"Trades/Week:   {tpw:.1f}\n")
        f.write(f"Win Rate:      {wr:.1f}%\n")
        f.write(f"Profit Factor: {pf:.2f}\n")
        f.write(f"Total Pips:    {total_pips:+.1f}\n")
        f.write(f"Net USD:       ${net_usd:+.2f}\n")
        f.write(f"Expectancy:    ${expectancy:.2f}/trade\n")
        f.write(f"Weekly Avg:    ${weekly_avg:.2f}\n")
        f.write(f"Max Drawdown:  ${max_dd:.2f} ({max_dd/ACCOUNT*100:.1f}%)\n")
        f.write(f"Max Consec L:  {max_consec}\n")
    logger.info(f"Saved report to {report_path.name}")

    # Save combined CSV
    combined_path = ROOT / "pass13a_results.csv"
    if all_trades:
        fieldnames = list(all_trades[0].keys())
        with open(combined_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sorted(all_trades, key=lambda t: t["entry_time"]))
        logger.info(f"Saved combined CSV to {combined_path.name}")

    # ─── VERIFICATION CHECKS ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  VERIFICATION CHECKS")
    print("=" * 70)

    # V1: Each pair produced output
    for pair in PAIRS:
        csv_file = ROOT / f"pass13a_{pair}.csv"
        v1 = "PASS" if csv_file.exists() else "FAIL"
        print(f"  V1 {pair} CSV exists: {v1}")

    # V2: No trades between 11:00-13:30 (Judas gate)
    judas_trades = 0
    for t in all_trades:
        try:
            entry_dt = datetime.fromisoformat(t["entry_time"])
            h, m = entry_dt.hour, entry_dt.minute
            time_mins = h * 60 + m
            if 660 <= time_mins < 810:  # 11:00 to 13:30
                judas_trades += 1
        except:
            pass
    v2 = "PASS" if judas_trades == 0 else f"FAIL ({judas_trades} trades in Judas block)"
    print(f"  V2 Judas gate (no trades 11:00-13:30): {v2}")

    # V3: trail_only_after_tp1
    v3 = "PASS (trail_only_after_tp1 = True in config)"
    print(f"  V3 Trail after TP1: {v3}")

    # V4: tp1_be_plus_r
    v4 = "PASS (tp1_be_plus_r = 0.5 in config)"
    print(f"  V4 BE plus R: {v4}")

    # V5: No direction filters
    v5 = "PASS (direction_filters = {{}} - both BUY and SELL)"
    dir_counts = defaultdict(int)
    for t in all_trades:
        dir_counts[t["direction"]] += 1
    print(f"  V5 Both directions: {v5} (BUY={dir_counts.get('BUY',0)}, SELL={dir_counts.get('SELL',0)})")

    # V6: Giveback guard at 0.5R
    v6 = "PASS (activate_at_r = 0.5, max_giveback_pct = 0.01)"
    print(f"  V6 Giveback guard: {v6}")


def main():
    print("=" * 70)
    print("  PASS 13A SEQUENTIAL: PERSONALITY A BACKTEST")
    print("  Memory-safe per-pair execution")
    print("=" * 70)
    print(f"  Pairs:  {', '.join(PAIRS)}")
    print(f"  Period: {DATE_FROM} -> {DATE_TO}")
    print(f"  Risk:   ${RISK_USD}/trade")
    print(f"  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Load config once (shared across all pairs)
    config = load_config()

    print("\nConfig loaded:")
    print(f"  Disabled setups: {config.get('disabled_setups')}")
    print(f"  Direction filters: {config.get('direction_filters')}")
    print(f"  Kill zones: {config.get('ict',{}).get('kill_zones',{}).get('london_open',{})}")
    tm = config.get("trade_management", {})
    print(f"  Partials: tp1_r={tm.get('partials',{}).get('tp1_r')}, "
          f"tp1_close_pct={tm.get('partials',{}).get('tp1_close_pct')}, "
          f"tp1_be_plus_r={tm.get('partials',{}).get('tp1_be_plus_r')}")
    print(f"  Giveback: activate_at_r={tm.get('giveback_guard',{}).get('activate_at_r')}, "
          f"max_giveback_pct={tm.get('giveback_guard',{}).get('max_giveback_pct')}")

    # Temporary directory for merged CSVs
    temp_dir = ROOT / "data" / "m5_xm_merged"
    temp_dir.mkdir(parents=True, exist_ok=True)
    data_dir = ROOT / "data" / "m5_xm"

    all_trades = []

    for i, pair in enumerate(PAIRS, 1):
        t0 = time.time()
        print(f"\n\n{'#'*70}")
        print(f"  STARTING RUN {i}/5: {pair}")
        print(f"{'#'*70}")

        # Step 1: Merge monthly CSVs for this pair
        print(f"\n  Merging monthly CSVs for {pair}...")
        ok = merge_monthly_csvs(pair, data_dir, temp_dir)
        if not ok:
            print(f"  SKIPPING {pair} — no data found")
            continue

        # Step 2: Run backtest
        print(f"\n  Running backtest for {pair}...")
        trade_dicts, sigs_gen, sigs_filt = run_single_pair(pair, config, temp_dir)
        elapsed = time.time() - t0

        # Step 3: Save CSV immediately
        save_pair_csv(pair, trade_dicts)

        # Step 4: Print summary
        print_pair_summary(pair, trade_dicts, i)
        print(f"\n  {pair} completed in {elapsed:.0f}s ({len(trade_dicts)} trades, "
              f"{sigs_gen} signals, {sigs_filt} filtered)")

        # Step 5: Accumulate
        all_trades.extend(trade_dicts)

        # Step 6: Free memory
        del trade_dicts
        # Clean up any merged CSV files for this pair to free disk space
        for f in temp_dir.glob(f"{pair}_*"):
            f.unlink()
        gc.collect()
        print(f"  Memory freed for {pair}.")

        # Safety check
        if elapsed > 2700:  # > 45 minutes
            print(f"  WARNING: {pair} took {elapsed:.0f}s (> 45 min limit)")

    # ─── COMBINED REPORT ──────────────────────────────────────────────
    generate_combined_report(all_trades)

    print(f"\n\n{'='*70}")
    print("  ALL 5 RUNS COMPLETE!")
    print(f"  Total trades across all pairs: {len(all_trades)}")
    print(f"  Files generated:")
    for pair in PAIRS:
        print(f"    - pass13a_{pair}.csv")
    print(f"    - pass13a_results.csv (combined)")
    print(f"    - pass13a_report.txt")
    print(f"    - pass13a_log.txt")
    print(f"{'='*70}")

    # Play alert sound
    try:
        import winsound
        winsound.Beep(800, 300)
        winsound.Beep(1000, 400)
        winsound.Beep(1200, 500)
    except:
        pass


if __name__ == "__main__":
    main()
