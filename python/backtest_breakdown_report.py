import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def _parse_args():
    parser = argparse.ArgumentParser(description="Generate backtest breakdown report")
    parser.add_argument("--input", default="backtest_results.csv", help="CSV results path")
    parser.add_argument("--filtered", default="backtest_filtered_signals.json", help="Filtered signals JSON path")
    parser.add_argument("--output", default="backtest_report.txt", help="Report output path")
    return parser.parse_args()


_args = _parse_args()

RESULTS = Path(_args.input)
FILTERED = Path(_args.filtered)
REPORT = Path(_args.output)

RISK_PER_TRADE_USD = 50.0
TARGET_WEEKLY = 300.0


def parse_dt(s):
    s = (s or '').strip()
    if not s:
        return None
    return datetime.strptime(s, '%Y-%m-%d %H:%M')


def to_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ('1','true','yes')


def pf_from_pips(pips):
    profits = sum(x for x in pips if x > 0)
    losses = abs(sum(x for x in pips if x < 0))
    return (profits / losses) if losses > 0 else float('inf')


def win_rate(pips):
    wins = sum(1 for x in pips if x > 0)
    return (wins / len(pips) * 100.0) if pips else 0.0


rows = []
with RESULTS.open('r', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        r['entry_dt'] = parse_dt(r.get('entry_time'))
        r['exit_dt'] = parse_dt(r.get('exit_time'))
        r['pnl_pips'] = float(r.get('pnl_pips') or 0.0)
        r['rr_achieved'] = float(r.get('rr_achieved') or 0.0)
        r['confidence'] = float(r.get('confidence') or 0.0)
        r['partial_taken'] = to_bool(r.get('partial_taken'))
        r['trail_count'] = int(float(r.get('trail_count') or 0))
        r['be_applied'] = to_bool(r.get('be_applied'))
        r['peak_r'] = float(r.get('peak_r') or 0.0)
        rows.append(r)

if not rows:
    raise SystemExit('No trades found in backtest_results.csv')

# time span
trade_times = [r['entry_dt'] for r in rows if r['entry_dt']]
if trade_times:
    t0 = min(trade_times)
    t1 = max(trade_times)
    span_days = max(1.0, (t1 - t0).days + 1)
    trades_per_week = len(rows) / (span_days / 7.0)
else:
    t0 = t1 = None
    trades_per_week = 0.0

# overall
pips_all = [r['pnl_pips'] for r in rows]
rr_all = [r['rr_achieved'] for r in rows]
wr_all = win_rate(pips_all)
profit_factor = pf_from_pips(pips_all)
avg_pips = sum(pips_all) / len(pips_all)

# Expectancy in R based on win/loss distribution
w_rr = [r['rr_achieved'] for r in rows if r['pnl_pips'] > 0]
l_rr = [abs(r['rr_achieved']) for r in rows if r['pnl_pips'] < 0]
avg_win_r = sum(w_rr) / len(w_rr) if w_rr else 0.0
avg_loss_r = sum(l_rr) / len(l_rr) if l_rr else 0.0
wr = wr_all / 100.0
expectancy_r = (wr * avg_win_r) - ((1.0 - wr) * avg_loss_r)
expectancy_usd = expectancy_r * RISK_PER_TRADE_USD
weekly_run_rate = expectancy_usd * trades_per_week

# target gap
weekly_gap = TARGET_WEEKLY - weekly_run_rate

# by setup
by_setup = defaultdict(list)
for r in rows:
    by_setup[r['setup_type']].append(r)

setup_rows = []
for setup, rs in by_setup.items():
    p = [x['pnl_pips'] for x in rs]
    pf = pf_from_pips(p)
    verdict = 'KEEP' if pf > 1.2 else ('REVIEW' if pf >= 0.8 else 'DISABLE')
    setup_rows.append((setup, len(rs), win_rate(p), sum(p), pf, sum(p)/len(rs), verdict))
setup_rows.sort(key=lambda x: (-x[4], x[0]))

# by pair
by_pair = defaultdict(list)
for r in rows:
    by_pair[r['symbol']].append(r)

pair_rows = []
for sym, rs in by_pair.items():
    p = [x['pnl_pips'] for x in rs]
    pair_rows.append((sym, len(rs), win_rate(p), sum(p), pf_from_pips(p)))

# primary bleeder
pair_rows_sorted = sorted(pair_rows, key=lambda x: x[3])
primary_bleeder = pair_rows_sorted[0][0] if pair_rows_sorted else ''

# by killzone
zones = ['LONDON_OPEN', 'NY_OPEN', 'LONDON_CLOSE', 'DEAD_ZONE', 'NONE']
by_kz = defaultdict(list)
for r in rows:
    by_kz[str(r.get('killzone') or 'NONE').upper()].append(r)

kz_rows = []
for kz in zones:
    rs = by_kz.get(kz, [])
    if not rs:
        continue
    p = [x['pnl_pips'] for x in rs]
    kz_rows.append((kz, len(rs), win_rate(p), sum(p)))

# by direction per pair
by_pair_dir = defaultdict(list)
for r in rows:
    key = (r['symbol'], r['direction'])
    by_pair_dir[key].append(r)

pair_dir_rows = []
for (sym, direction), rs in sorted(by_pair_dir.items()):
    p = [x['pnl_pips'] for x in rs]
    pair_dir_rows.append((sym, direction, len(rs), win_rate(p), sum(p), pf_from_pips(p)))

# htf bias alignment
aligned = []
conflict = []
neutral = []
for r in rows:
    bias = str(r.get('htf_bias') or 'NEUTRAL').upper()
    direction = str(r.get('direction') or '').upper()
    if bias in ('BUY','SELL'):
        if bias == direction:
            aligned.append(r)
        else:
            conflict.append(r)
    else:
        neutral.append(r)


def stats_for(rs):
    p = [x['pnl_pips'] for x in rs]
    return len(rs), win_rate(p), sum(p), pf_from_pips(p)

aligned_stats = stats_for(aligned)
conflict_stats = stats_for(conflict)
neutral_stats = stats_for(neutral)

# exit reason
by_exit = defaultdict(list)
for r in rows:
    by_exit[str(r.get('exit_reason') or 'UNKNOWN')].append(r)

exit_rows = []
for reason, rs in by_exit.items():
    p = [x['pnl_pips'] for x in rs]
    exit_rows.append((reason, len(rs), sum(p), (sum(p)/len(rs)) if rs else 0.0))
exit_rows.sort(key=lambda x: -x[1])

# sniper effectiveness
filtered = []
if FILTERED.exists():
    with FILTERED.open('r', encoding='utf-8') as f:
        filtered = json.load(f)

filtered_count = len(filtered)
allowed_count = len(rows)
filter_reasons = defaultdict(int)
for s in filtered:
    reason = str(s.get('skip_reason', 'UNKNOWN'))
    filter_reasons[reason] += 1

sniper_passed_vals = {str(r.get('sniper_passed')) for r in rows}

# time of day heatmap (UTC hour)
by_hour = defaultdict(list)
for r in rows:
    dt = r['entry_dt']
    if dt is None:
        continue
    by_hour[dt.hour].append(r)

hour_rows = []
for hour in range(24):
    rs = by_hour.get(hour, [])
    if not rs:
        continue
    p = [x['pnl_pips'] for x in rs]
    hour_rows.append((hour, len(rs), win_rate(p), sum(p)))

# monthly performance
by_month = defaultdict(list)
for r in rows:
    dt = r['entry_dt']
    if dt is None:
        continue
    key = f"{dt.year:04d}-{dt.month:02d}"
    by_month[key].append(r)

month_rows = []
for m, rs in sorted(by_month.items()):
    p = [x['pnl_pips'] for x in rs]
    month_rows.append((m, len(rs), win_rate(p), sum(p), pf_from_pips(p)))

worst_month = min(month_rows, key=lambda x: x[3]) if month_rows else None
best_month = max(month_rows, key=lambda x: x[3]) if month_rows else None

lines = []
lines.append("ICT Backtest Breakdown Report")
lines.append("="*72)

# 2a overall summary
lines.append("\nOVERALL SUMMARY")
lines.append(f"Total trades: {len(rows)}")
lines.append(f"Win rate: {wr_all:.2f}%")
lines.append(f"Profit factor: {profit_factor:.2f}")
lines.append(f"Total pips: {sum(pips_all):+.2f}")
lines.append(f"Avg pips/trade: {avg_pips:+.2f}")
lines.append(f"Expectancy/trade ($50 risk): {expectancy_usd:+.2f}")
lines.append(f"Avg win R: {avg_win_r:.2f} | Avg loss R: {avg_loss_r:.2f}")
lines.append(f"Trades/week (avg): {trades_per_week:.2f}")
lines.append(f"Weekly run rate: {weekly_run_rate:+.2f} vs $300 target")
lines.append(f"Gap to target: {weekly_gap:+.2f}")

# 2b by setup
lines.append("\nBY SETUP TYPE (sorted by PF desc)")
lines.append("Setup | Trades | Win% | Total Pips | PF | Avg Pips | Verdict")
for setup, n, wr, total, pf, avg, verdict in setup_rows:
    lines.append(f"{setup} | {n:>5} | {wr:>5.1f}% | {total:>+9.1f} | {pf:>4.2f} | {avg:>+7.2f} | {verdict}")

# 2c by pair
lines.append("\nBY PAIR")
lines.append("Pair | Trades | Win% | Total Pips | PF")
for sym, n, wr, total, pf in sorted(pair_rows, key=lambda x: x[0]):
    lines.append(f"{sym} | {n:>5} | {wr:>5.1f}% | {total:>+9.1f} | {pf:>4.2f}")
lines.append(f"Primary bleeder: {primary_bleeder}")

# 2d by kill zone
lines.append("\nBY KILL ZONE")
lines.append("Kill Zone | Trades | Win% | Total Pips | Flag")
for kz, n, wr, total in kz_rows:
    flag = "RESTRICT" if wr < 35.0 else "OK"
    lines.append(f"{kz} | {n:>5} | {wr:>5.1f}% | {total:>+9.1f} | {flag}")

# 2e by direction
lines.append("\nBY DIRECTION (per pair)")
lines.append("Pair | Dir | Trades | Win% | Total Pips | PF")
for sym, direction, n, wr, total, pf in pair_dir_rows:
    lines.append(f"{sym} | {direction} | {n:>5} | {wr:>5.1f}% | {total:>+9.1f} | {pf:>4.2f}")

# 2f HTF bias alignment
lines.append("\nHTF BIAS ALIGNMENT")
lines.append("Group | Trades | Win% | Total Pips | PF")
lines.append(f"Aligned | {aligned_stats[0]:>5} | {aligned_stats[1]:>5.1f}% | {aligned_stats[2]:>+9.1f} | {aligned_stats[3]:>4.2f}")
lines.append(f"Conflict | {conflict_stats[0]:>5} | {conflict_stats[1]:>5.1f}% | {conflict_stats[2]:>+9.1f} | {conflict_stats[3]:>4.2f}")
lines.append(f"Neutral | {neutral_stats[0]:>5} | {neutral_stats[1]:>5.1f}% | {neutral_stats[2]:>+9.1f} | {neutral_stats[3]:>4.2f}")

# 2g exit reason
lines.append("\nBY EXIT REASON")
lines.append("Reason | Trades | Total Pips | Avg Pips")
for reason, n, total, avg in exit_rows:
    lines.append(f"{reason} | {n:>5} | {total:>+9.1f} | {avg:>+7.2f}")

# 2h sniper effectiveness
lines.append("\nSNIPER FILTER EFFECTIVENESS")
lines.append(f"Filtered signals: {filtered_count}")
lines.append(f"Allowed trades: {allowed_count}")
lines.append(f"Allowed trade win rate: {wr_all:.2f}%")
lines.append("Most common filter reasons:")
for reason, count in sorted(filter_reasons.items(), key=lambda x: -x[1])[:10]:
    lines.append(f"  {reason}: {count}")
if sniper_passed_vals == {'True'}:
    lines.append("CRITICAL: sniper_passed is 100% True in results.")

# 2i time of day heatmap
lines.append("\nTIME OF DAY HEATMAP (UTC hour)")
lines.append("Hour | Trades | Win% | Total Pips")
for hour, n, wr, total in hour_rows:
    lines.append(f"{hour:02d} | {n:>5} | {wr:>5.1f}% | {total:>+9.1f}")

# 2j monthly performance
lines.append("\nMONTHLY PERFORMANCE")
lines.append("Month | Trades | Win% | Total Pips | PF")
for m, n, wr, total, pf in month_rows:
    lines.append(f"{m} | {n:>5} | {wr:>5.1f}% | {total:>+9.1f} | {pf:>4.2f}")
if best_month:
    lines.append(f"Best month: {best_month[0]} ({best_month[3]:+.1f} pips)")
if worst_month:
    lines.append(f"Worst month: {worst_month[0]} ({worst_month[3]:+.1f} pips)")

report_text = "\n".join(lines)
print(report_text)
REPORT.write_text(report_text, encoding='utf-8')
print(f"\nReport saved to {REPORT}")
