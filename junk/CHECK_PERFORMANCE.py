"""
CHECK_PERFORMANCE.py
Quickly view the latest backtest or live results.
"""
import pandas as pd
from pathlib import Path

def main():
    print("========================================")
    print("   ICT TRADING BOT - PERFORMANCE      ")
    print("========================================\n")
    
    results_dir = Path("03_BACKTEST_RESULTS")
    latest_csv = None
    max_time = 0
    
    for f in results_dir.rglob("*.csv"):
        if f.stat().st_mtime > max_time:
            max_time = f.stat().st_mtime
            latest_csv = f
            
    if latest_csv:
        print(f"Loading latest results from: {latest_csv.name}")
        df = pd.read_csv(latest_csv)
        total_pnl = df['pnl_pips'].sum()
        win_rate = (df['pnl_pips'] > 0).mean() * 100
        print(f"Total Pips: {total_pnl:.2f}")
        print(f"Win Rate:   {win_rate:.2f}%")
        print(f"Total Trades: {len(df)}")
    else:
        print("No result files found in 03_BACKTEST_RESULTS/")

if __name__ == "__main__":
    main()
