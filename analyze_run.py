import pandas as pd
import sys
from datetime import datetime

def analyze(csv_file):
    df = pd.read_csv(csv_file)
    if len(df) == 0:
        print(f"No trades in {csv_file}")
        return

    df['pnl_pips'] = pd.to_numeric(df['pnl_pips'])
    df['is_win'] = df['pnl_pips'] > 0
    df['is_loss'] = df['pnl_pips'] < 0

    print("=== SUMMARY ===")
    print(f"Total trades: {len(df)}")
    
    start_date = pd.to_datetime(df['entry_time']).min()
    end_date = pd.to_datetime(df['exit_time']).max()
    weeks = max((end_date - start_date).days / 7.0, 1)
    print(f"Trades/week: {len(df) / weeks:.2f}")

    print("\n=== TRADES BY PAIR & SETUP ===")
    print(df.groupby(['symbol', 'setup_type']).size().to_string())

    print("\n=== EXIT REASON BREAKDOWN ===")
    print(df['exit_reason'].value_counts().to_string())

    print("\n=== PAIR PERFORMANCE ===")
    for pair in df['symbol'].unique():
        pdf = df[df['symbol'] == pair]
        wins = pdf[pdf['is_win']]
        losses = pdf[pdf['is_loss']]
        
        wr = len(wins) / len(pdf) if len(pdf) > 0 else 0
        gross_profit = wins['pnl_pips'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['pnl_pips'].sum()) if len(losses) > 0 else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        total_pips = pdf['pnl_pips'].sum()
        
        avg_win = wins['pnl_pips'].mean() if len(wins) > 0 else 0
        avg_loss = abs(losses['pnl_pips'].mean()) if len(losses) > 0 else 0
        expectancy = (wr * avg_win) - ((1 - wr) * avg_loss)
        
        print(f"{pair}:")
        print(f"  Trades: {len(pdf)}")
        print(f"  WR: {wr:.1%} ({len(wins)}/{len(pdf)})")
        print(f"  PF: {pf:.2f}")
        print(f"  Total Pips: {total_pips:.1f}")
        print(f"  Avg Win: {avg_win:.1f} | Avg Loss: -{avg_loss:.1f}")
        print(f"  Expectancy: {expectancy:.2f} pips/trade")

    print("\n=== AUDUSD SPECIFICS ===")
    aud_df = df[df['symbol'] == 'AUDUSD']
    if len(aud_df) > 0:
        partials = aud_df['partial_taken'] == True
        partial_rate = partials.mean()
        
        aud_wins = aud_df[aud_df['is_win']]
        win_w_partial = aud_wins[aud_wins['partial_taken'] == True]['pnl_pips'].mean()
        win_wo_partial = aud_wins[aud_wins['partial_taken'] != True]['pnl_pips'].mean()
        
        print(f"  Partial taken rate: {partial_rate:.1%}")
        print(f"  Avg Win w/ partial: {win_w_partial:.1f} pips")
        print(f"  Avg Win w/o partial: {win_wo_partial:.1f} pips")
    
    print("\n=== VALIDATION ===")
    print(f"LONDON_OPEN Trades: {len(df[df['killzone'] == 'LONDON_OPEN'])}")
    print(f"LH_LL_CONTINUATION Trades: {len(df[df['setup_type'] == 'LH_LL_CONTINUATION'])}")

if __name__ == "__main__":
    analyze(sys.argv[1])
