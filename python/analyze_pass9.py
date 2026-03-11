import csv
from datetime import datetime
import math
import sys

sys.stdout = open("pass9_report.md", "w", encoding="utf-8")

def calculate_confidence_interval(wr, n):
    if n == 0: return 0
    # Lower bound formula: WR − 1.96 × √(WR × (1−WR) / n)
    margin = 1.96 * math.sqrt((wr * (1 - wr)) / n)
    return wr - margin

def analyze():
    trades = []
    with open("../backtest_results.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    
    n_total = len(trades)
    winners = [t for t in trades if float(t["pnl_pips"]) > 0]
    losers = [t for t in trades if float(t["pnl_pips"]) <= 0 and t["exit_reason"] != "END_OF_DATA"]
    end_of_data = [t for t in trades if t["exit_reason"] == "END_OF_DATA"]
    
    n_win = len(winners)
    n_loss = len(losers)
    n_resolved = n_win + n_loss
    wr = n_win / n_total if n_total > 0 else 0
    
    gross_profit = sum(float(t["pnl_pips"]) for t in winners)
    gross_loss = sum(abs(float(t["pnl_pips"])) for t in losers)
    net_pips = gross_profit - gross_loss
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    
    avg_win = gross_profit / n_win if n_win > 0 else 0
    avg_loss = gross_loss / n_loss if n_loss > 0 else 0
    expectancy = (wr * avg_win) - ((1 - wr) * avg_loss)
    
    days = 60 # Jan + Feb approx
    weeks = days / 7
    trades_per_week = n_total / weeks if weeks > 0 else 0
    
    # 1. Data Coverage
    print("### 1. Data Coverage Summary")
    print("M5 data available: 2025-01-01 to 2025-02-28 (2 months).")
    print("M15/H1/H4 data continues to Dec 2025.")
    print("Because M5 is the trigger timeframe, the backtest window is strictly Jan 1 - Feb 28, 2025.")
    print("MT5 export for missing months failed (IPC timeout), so we restricted backtest to covered months.")
    print()
    
    # 2. Overall Summary
    print("### 2. Overall Summary")
    print(f"Total Trades: {n_total}")
    print(f"Win Rate: {wr*100:.1f}% ({n_win}W / {n_loss}L)")
    print(f"Profit Factor: {pf:.2f}")
    print(f"Total Pips: {net_pips:+.1f}")
    print(f"Expectancy: {expectancy:+.2f} pips per trade")
    print(f"Trades/Week: {trades_per_week:.1f}")
    print()
    
    # 3. Monthly Breakdown
    print("### 3. Monthly Breakdown Table")
    print("| Month | Trades | WR | Total Pips | PF | Avg Win | Avg Loss | Status |")
    print("|---|---|---|---|---|---|---|---|")
    
    months = ["2025-01", "2025-02"]
    profitable_months = 0
    valid_months = 0
    
    for m in months:
        m_trades = [t for t in trades if t["entry_time"].startswith(m)]
        m_total = len(m_trades)
        if m_total == 0:
            print(f"| {m} | 0 | - | - | - | - | - | ➖ |")
            continue
            
        m_win = [t for t in m_trades if float(t["pnl_pips"]) > 0]
        m_loss = [t for t in m_trades if float(t["pnl_pips"]) <= 0 and t["exit_reason"] != "END_OF_DATA"]
        m_wr = len(m_win) / m_total
        m_gp = sum(float(t["pnl_pips"]) for t in m_win)
        m_gl = sum(abs(float(t["pnl_pips"])) for t in m_loss)
        m_net = m_gp - m_gl
        m_pf = m_gp / m_gl if m_gl > 0 else 99.9
        m_aw = m_gp / len(m_win) if len(m_win) > 0 else 0
        m_al = m_gl / len(m_loss) if len(m_loss) > 0 else 0
        
        status = "✅" if m_pf >= 1.0 else "❌"
        if m_total >= 2:
            valid_months += 1
            if m_pf >= 1.0:
                profitable_months += 1
                
        print(f"| {m} | {m_total} | {m_wr*100:.1f}% | {m_net:+.1f} | {m_pf:.2f} | {m_aw:.1f} | {m_al:.1f} | {status} |")
    print()
    
    # 4. Setup Breakdown
    print("### 4. Setup Breakdown")
    print("| Setup | Trades | WR | PF | Total Pips | Avg Win | Avg Loss | Partial Rate |")
    print("|---|---|---|---|---|---|---|---|")
    for stp in ["CHOCH", "LIQUIDITY_SWEEP_REVERSAL"]:
        s_trades = [t for t in trades if t["setup_type"] == stp]
        s_total = len(s_trades)
        if s_total == 0:
            print(f"| {stp} | 0 | - | - | - | - | - | - |")
            continue
        s_win = [t for t in s_trades if float(t["pnl_pips"]) > 0]
        s_loss = [t for t in s_trades if float(t["pnl_pips"]) <= 0 and t["exit_reason"] != "END_OF_DATA"]
        s_wr = len(s_win) / s_total
        s_gp = sum(float(t["pnl_pips"]) for t in s_win)
        s_gl = sum(abs(float(t["pnl_pips"])) for t in s_loss)
        s_net = s_gp - s_gl
        s_pf = s_gp / s_gl if s_gl > 0 else 99.9
        s_aw = s_gp / len(s_win) if len(s_win) > 0 else 0
        s_al = s_gl / len(s_loss) if len(s_loss) > 0 else 0
        s_part = sum(1 for t in s_trades if t.get("partial_taken","") == "True")
        s_part_rate = s_part / s_total if s_total > 0 else 0
        print(f"| {stp} | {s_total} | {s_wr*100:.1f}% | {s_pf:.2f} | {s_net:+.1f} | {s_aw:.1f} | {s_al:.1f} | {s_part_rate*100:.1f}% |")
    print()
    
    # 5. Per-Pair Breakdown
    print("### 5. Per-Pair Breakdown")
    print("| Pair | Trades | WR | PF | Total Pips | Avg Win | Avg Loss |")
    print("|---|---|---|---|---|---|---|")
    for pair in ["USDJPY", "GBPUSD", "AUDUSD"]:
        p_trades = [t for t in trades if t["symbol"] == pair]
        p_total = len(p_trades)
        if p_total == 0:
            print(f"| {pair} | 0 | - | - | - | - | - |")
            continue
        p_win = [t for t in p_trades if float(t["pnl_pips"]) > 0]
        p_loss = [t for t in p_trades if float(t["pnl_pips"]) <= 0 and t["exit_reason"] != "END_OF_DATA"]
        p_wr = len(p_win) / p_total
        p_gp = sum(float(t["pnl_pips"]) for t in p_win)
        p_gl = sum(abs(float(t["pnl_pips"])) for t in p_loss)
        p_net = p_gp - p_gl
        p_pf = p_gp / p_gl if p_gl > 0 else 99.9
        p_aw = p_gp / len(p_win) if len(p_win) > 0 else 0
        p_al = p_gl / len(p_loss) if len(p_loss) > 0 else 0
        print(f"| {pair} | {p_total} | {p_wr*100:.1f}% | {p_pf:.2f} | {p_net:+.1f} | {p_aw:.1f} | {p_al:.1f} |")
    print()
    
    # 6. Exit Reason Breakdown
    print("### 6. Exit Reason Breakdown")
    reasons = {}
    for t in trades:
        er = t["exit_reason"]
        if not er: er = "END_OF_DATA"
        if er not in reasons: reasons[er] = []
        reasons[er].append(float(t["pnl_pips"]))
        
    for er, pnl_list in reasons.items():
        count = len(pnl_list)
        pct = count / n_total * 100
        avg = sum(pnl_list) / count if count > 0 else 0
        print(f"- {er}: {count} trades ({pct:.1f}%) | Avg pips: {avg:+.1f}")
    print()
    
    # 7. Kill Zone Split
    print("### 7. Kill Zone Split")
    for kz in ["NY_OPEN", "LONDON_CLOSE"]:
        k_trades = [t for t in trades if t["killzone"] == kz]
        k_total = len(k_trades)
        if k_total == 0:
            print(f"- {kz}: 0 trades")
            continue
        k_win = [t for t in k_trades if float(t["pnl_pips"]) > 0]
        k_loss = [t for t in k_trades if float(t["pnl_pips"]) <= 0 and t["exit_reason"] != "END_OF_DATA"]
        k_wr = len(k_win) / k_total
        k_gp = sum(float(t["pnl_pips"]) for t in k_win)
        k_gl = sum(abs(float(t["pnl_pips"])) for t in k_loss)
        k_pf = k_gp / k_gl if k_gl > 0 else 99.9
        k_net = k_gp - k_gl
        print(f"- {kz}: {k_total} trades | WR: {k_wr*100:.1f}% | PF: {k_pf:.2f} | PnL: {k_net:+.1f} pips")
    print()
    
    # 8. Regime Consistency Score
    print("### 8. Regime Consistency Score")
    print(f"{profitable_months} out of {valid_months} profitable months (months with >= 2 trades).")
    print()
    
    # 9. 95% WR Confidence Interval
    print("### 9. 95% WR Confidence Interval")
    lower_bound = calculate_confidence_interval(wr, n_total)
    print(f"Sample WR: {wr*100:.1f}% (n={n_total})")
    print(f"95% CI Lower Bound: {lower_bound*100:.1f}%")
    if lower_bound > 0.5:
        print("Verdict: Edge is statistically significant (lower bound > 50%).")
    else:
        print("Verdict: Edge is NOT statistically significant (lower bound <= 50%).")
    print()
    
    # 10. Drawdown Analysis
    print("### 10. Drawdown Analysis")
    max_consec_loss = 0
    current_consec = 0
    for t in trades:
        if float(t["pnl_pips"]) <= 0 and t["exit_reason"] != "END_OF_DATA":
            current_consec += 1
            if current_consec > max_consec_loss:
                max_consec_loss = current_consec
        elif float(t["pnl_pips"]) > 0:
            current_consec = 0
            
    print(f"Max consecutive losing trades: {max_consec_loss}")
    
    month_pnls = {}
    for m in months:
        m_trades = [t for t in trades if t["entry_time"].startswith(m)]
        m_net = sum(float(t["pnl_pips"]) for t in m_trades)
        month_pnls[m] = m_net
        
    worst_month_pips = min(month_pnls.values()) if month_pnls else 0
    print(f"Largest single-month loss in pips: {worst_month_pips:+.1f}")
    
    # At $50 risk per trade
    # max_consec_loss * 50
    # worst_month USD
    # Here avg loss is roughly representing 1R
    print(f"Worst-case max consecutive drawdown: ${max_consec_loss * 50} ({max_consec_loss} trades x $50 risk)")
    print()
    
if __name__ == "__main__":
    analyze()
