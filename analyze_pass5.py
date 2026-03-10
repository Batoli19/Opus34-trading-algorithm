import pandas as pd
import numpy as np

for run_name, file_name in [('Run A (Jan-Feb 2025)', 'run_a_results_pass5.csv'), ('Run B (February 2026)', 'run_b_results_pass5.csv')]:
    print(f"\\n{'='*50}\\n{run_name}\\n{'='*50}")
    try:
        df = pd.read_csv(file_name)
    except Exception as e:
        print(f"Error loading {file_name}: {e}")
        continue
    
    if len(df) == 0:
        print("0 trades.")
        continue

    # Dates
    start_date = pd.to_datetime(df['entry_time'].min())
    end_date = pd.to_datetime(df['entry_time'].max())
    weeks = max((end_date - start_date).days / 7, 1)

    # Basic stats
    total_trades = len(df)
    winners = df[df['pnl_pips'] > 0]
    losers = df[df['pnl_pips'] <= 0]
    wr = len(winners) / total_trades if total_trades else 0
    total_pips = df['pnl_pips'].sum()
    gross_win = winners['pnl_pips'].sum() if len(winners) else 0
    gross_loss = abs(losers['pnl_pips'].sum()) if len(losers) else 0
    pf = gross_win / gross_loss if gross_loss > 0 else float('inf')
    avg_win = winners['pnl_pips'].mean() if len(winners) else 0
    avg_loss = losers['pnl_pips'].mean() if len(losers) else 0
    expectancy = wr * avg_win + (1 - wr) * avg_loss

    print(f"Total trades: {total_trades}")
    print(f"Trades/week: {total_trades / weeks:.2f}")
    print(f"Win rate: {wr*100:.1f}%")
    print(f"Profit factor: {pf:.2f}")
    print(f"Total pips: {total_pips:.1f}")
    print(f"Expectancy: {expectancy:.2f} pips")

    print(f"\\n--- Per-Pair ---")
    for pair in df['symbol'].unique():
        pair_df = df[df['symbol'] == pair]
        p_total = len(pair_df)
        p_win = len(pair_df[pair_df['pnl_pips'] > 0])
        p_wr = (p_win / p_total) * 100
        p_pips = pair_df['pnl_pips'].sum()
        p_gross_win = pair_df[pair_df['pnl_pips'] > 0]['pnl_pips'].sum()
        p_gross_loss = abs(pair_df[pair_df['pnl_pips'] <= 0]['pnl_pips'].sum())
        p_pf = (p_gross_win / p_gross_loss) if p_gross_loss > 0 else float('inf')
        p_avg_win = pair_df[pair_df['pnl_pips'] > 0]['pnl_pips'].mean() if p_win > 0 else 0
        p_avg_loss = pair_df[pair_df['pnl_pips'] <= 0]['pnl_pips'].mean() if len(pair_df[pair_df['pnl_pips'] <= 0]) > 0 else 0
        print(f"{pair:>6} - Trades: {p_total:>2} | WR: {p_wr:4.1f}% | PF: {p_pf:4.2f} | PnL: {p_pips:+6.1f} | Avg Win: {p_avg_win:>5.1f} | Avg Loss: {p_avg_loss:>5.1f}")
        
        if pair == 'AUDUSD':
            p_taken = len(pair_df[pair_df['partial_taken'] == True])
            p_rate = (p_taken / p_total) * 100 if p_total else 0
            # Avg win with partial
            aw_part = pair_df[(pair_df['partial_taken'] == True) & (pair_df['pnl_pips'] > 0)]['pnl_pips'].mean()
            print(f"  -> AUDUSD partial_taken rate: {p_rate:.1f}% ({p_taken}/{p_total}) | Avg win with partial: {aw_part if pd.notna(aw_part) else 0:.1f}")

    print(f"\\n--- Exit Reason Breakdown ---")
    reasons = df['exit_reason'].value_counts()
    for r, c in reasons.items():
        print(f"  {r}: {c}")

    print(f"\\n--- V2 Verification ---")
    for setup in ['CHOCH', 'HH_HL_CONTINUATION', 'LIQUIDITY_GRAB_CONTINUATION']:
        count = len(df[df['setup_type'] == setup])
        print(f"  {setup}: {count} trades")

    print(f"\\n--- V4 Verification ---")
    count_lo = len(df[df['killzone'] == 'LONDON_OPEN'])
    print(f"  LONDON_OPEN trades: {count_lo}")

    print(f"\\n--- V5 Verification ---")
    audusd_sell = len(df[(df['symbol'] == 'AUDUSD') & (df['direction'] == 'SELL')])
    usdjpy_buy = len(df[(df['symbol'] == 'USDJPY') & (df['direction'] == 'BUY')])
    print(f"  AUDUSD SELL: {audusd_sell}")
    print(f"  USDJPY BUY: {usdjpy_buy}")

    print(f"\\n--- LSR Setup Stats ---")
    lsr = df[df['setup_type'] == 'LIQUIDITY_SWEEP_REVERSAL']
    if len(lsr) > 0:
        l_win = len(lsr[lsr['pnl_pips'] > 0])
        l_aw = lsr[lsr['pnl_pips'] > 0]['pnl_pips'].mean() if l_win > 0 else 0
        l_gw = lsr[lsr['pnl_pips'] > 0]['pnl_pips'].sum()
        l_gl = abs(lsr[lsr['pnl_pips'] <= 0]['pnl_pips'].sum())
        l_pf = (l_gw / l_gl) if l_gl > 0 else float('inf')
        print(f"  LSR Trades: {len(lsr)} | Avg Win: {l_aw:.1f} | PF: {l_pf:.2f}")
