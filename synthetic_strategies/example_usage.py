"""
Example Usage: OPUS34 Synthetic Strategies
===========================================

This file shows how to use the synthetic strategies module.

To run:
    1. Download historical data (V75, Boom 1000, etc.)
    2. Convert to list of dicts with keys: 'open', 'high', 'low', 'close', 'time'
    3. Run backtests using this script
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import strategies
from vix_strategies import (
    BollingerMeanReversionVIX,
    RSIMeanReversionVIX,
    VolatilityBreakoutVIX
)

from boom_strategies import (
    SpikePredictorBoom,
    PostSpikeMeanReversionBoom
)

from synthetic_backtester import SyntheticBacktester


# ============================================================================
# EXAMPLE 1: Test VIX Bollinger Strategy on V75
# ============================================================================

def example_v75_bollinger():
    """Example: Backtest Bollinger Mean Reversion on V75 data."""
    
    print("=" * 80)
    print("EXAMPLE 1: V75 Bollinger Mean Reversion Strategy")
    print("=" * 80)
    
    # Load your V75 data here
    # This is just example data structure
    candles = load_v75_data('v75_m1_6months.csv')
    
    # Create strategy instance
    strategy = BollingerMeanReversionVIX(
        period=20,
        std_multiplier=2.0,
        exit_at_mean=True
    )
    
    # Create backtester
    backtester = SyntheticBacktester(
        strategy=strategy,
        initial_balance=10000,
        risk_per_trade=100,
        point_value=1.0,
        spread_points=2.0
    )
    
    # Run backtest
    print("\nRunning backtest...")
    results = backtester.run(candles)
    
    # Print results
    backtester.print_report(results)
    
    # Export to JSON
    backtester.export_to_json(results, 'v75_bollinger_results.json')
    
    return results


# ============================================================================
# EXAMPLE 2: Test VIX RSI Strategy on V75
# ============================================================================

def example_v75_rsi():
    """Example: Backtest RSI Mean Reversion on V75 data."""
    
    print("=" * 80)
    print("EXAMPLE 2: V75 RSI Mean Reversion Strategy")
    print("=" * 80)
    
    candles = load_v75_data('v75_m1_6months.csv')
    
    strategy = RSIMeanReversionVIX(
        rsi_period=14,
        overbought=75,
        oversold=25
    )
    
    backtester = SyntheticBacktester(
        strategy=strategy,
        initial_balance=10000,
        point_value=1.0,
        spread_points=2.0
    )
    
    print("\nRunning backtest...")
    results = backtester.run(candles)
    
    backtester.print_report(results)
    backtester.export_to_json(results, 'v75_rsi_results.json')
    
    return results


# ============================================================================
# EXAMPLE 3: Test Boom Spike Prediction on Boom 1000
# ============================================================================

def example_boom_spike_prediction():
    """Example: Backtest Spike Predictor on Boom 1000 data."""
    
    print("=" * 80)
    print("EXAMPLE 3: Boom 1000 Spike Prediction Strategy")
    print("=" * 80)
    
    candles = load_boom_data('boom1000_m1_6months.csv')
    
    strategy = SpikePredictorBoom(
        index_type='boom_1000',
        spike_threshold=10,
        overdue_ratio=0.8
    )
    
    backtester = SyntheticBacktester(
        strategy=strategy,
        initial_balance=10000,
        point_value=1.0,
        spread_points=5.0  # Boom has higher spreads
    )
    
    print("\nRunning backtest...")
    results = backtester.run(candles)
    
    backtester.print_report(results)
    backtester.export_to_json(results, 'boom1000_spike_results.json')
    
    return results


# ============================================================================
# EXAMPLE 4: Test Boom Post-Spike Reversion on Boom 1000
# ============================================================================

def example_boom_post_spike():
    """Example: Backtest Post-Spike Mean Reversion on Boom 1000."""
    
    print("=" * 80)
    print("EXAMPLE 4: Boom 1000 Post-Spike Mean Reversion Strategy")
    print("=" * 80)
    
    candles = load_boom_data('boom1000_m1_6months.csv')
    
    strategy = PostSpikeMeanReversionBoom(
        spike_threshold=10,
        retracement_target=0.6,  # 60% retracement
        max_hold_bars=25
    )
    
    backtester = SyntheticBacktester(
        strategy=strategy,
        initial_balance=10000,
        point_value=1.0,
        spread_points=5.0
    )
    
    print("\nRunning backtest...")
    results = backtester.run(candles)
    
    backtester.print_report(results)
    backtester.export_to_json(results, 'boom1000_post_spike_results.json')
    
    return results


# ============================================================================
# EXAMPLE 5: Compare All V75 Strategies
# ============================================================================

def example_compare_v75_strategies():
    """Example: Compare all V75 strategies side-by-side."""
    
    print("=" * 80)
    print("EXAMPLE 5: Compare All V75 Strategies")
    print("=" * 80)
    
    candles = load_v75_data('v75_m1_6months.csv')
    
    strategies = [
        ('Bollinger Mean Reversion', BollingerMeanReversionVIX()),
        ('RSI Mean Reversion', RSIMeanReversionVIX()),
        ('Volatility Breakout', VolatilityBreakoutVIX())
    ]
    
    all_results = []
    
    for name, strategy in strategies:
        print(f"\n{'=' * 80}")
        print(f"Testing: {name}")
        print('=' * 80)
        
        backtester = SyntheticBacktester(
            strategy=strategy,
            initial_balance=10000,
            spread_points=2.0
        )
        
        results = backtester.run(candles)
        backtester.print_report(results)
        
        all_results.append({
            'name': name,
            'metrics': results['metrics']
        })
    
    # Print comparison
    print("\n" + "=" * 80)
    print("STRATEGY COMPARISON")
    print("=" * 80)
    print(f"{'Strategy':<30} {'Trades':<10} {'WR %':<10} {'PF':<10} {'Return %':<10}")
    print("-" * 80)
    
    for result in all_results:
        m = result['metrics']
        print(f"{result['name']:<30} {m.total_trades:<10} {m.win_rate:<10.2f} {m.profit_factor:<10.2f} {m.total_pnl_percent:<10.2f}")
    
    print("=" * 80)
    
    return all_results


# ============================================================================
# DATA LOADING HELPERS
# ============================================================================

def load_v75_data(filename: str) -> list:
    """
    Load V75 data from CSV file.
    
    Expected CSV format:
        time,open,high,low,close,volume
        2024-01-01 00:00:00,8234.5,8245.2,8230.1,8242.3,100
        ...
    
    Returns:
        List of candle dicts
    """
    try:
        df = pd.read_csv(filename)
        df['time'] = pd.to_datetime(df['time'])
        
        candles = []
        for _, row in df.iterrows():
            candles.append({
                'time': row['time'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row.get('volume', 0)
            })
        
        print(f"Loaded {len(candles)} candles from {filename}")
        return candles
        
    except FileNotFoundError:
        print(f"ERROR: File {filename} not found")
        print("Please download V75 historical data first")
        return generate_sample_v75_data()


def load_boom_data(filename: str) -> list:
    """Load Boom data from CSV file."""
    try:
        df = pd.read_csv(filename)
        df['time'] = pd.to_datetime(df['time'])
        
        candles = []
        for _, row in df.iterrows():
            candles.append({
                'time': row['time'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row.get('volume', 0)
            })
        
        print(f"Loaded {len(candles)} candles from {filename}")
        return candles
        
    except FileNotFoundError:
        print(f"ERROR: File {filename} not found")
        print("Please download Boom historical data first")
        return generate_sample_boom_data()


def generate_sample_v75_data(n_candles: int = 10000) -> list:
    """
    Generate sample V75 data for testing.
    V75 = mean reverting random walk with 75% annual volatility.
    """
    print("\nGenerating sample V75 data (for testing only)...")
    
    np.random.seed(42)
    candles = []
    
    base_price = 8000
    current_price = base_price
    current_time = datetime(2024, 1, 1)
    
    for i in range(n_candles):
        # V75 behavior: mean-reverting
        deviation = current_price - base_price
        mean_reversion = -deviation * 0.05
        
        # Random volatility (75% annual = ~0.5% per minute)
        random_move = np.random.normal(0, base_price * 0.005)
        
        # Price movement
        price_change = mean_reversion + random_move
        
        open_price = current_price
        close_price = current_price + price_change
        high_price = max(open_price, close_price) + abs(np.random.normal(0, base_price * 0.002))
        low_price = min(open_price, close_price) - abs(np.random.normal(0, base_price * 0.002))
        
        candles.append({
            'time': current_time,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': np.random.randint(50, 200)
        })
        
        current_price = close_price
        current_time += timedelta(minutes=1)
    
    print(f"Generated {len(candles)} sample V75 candles")
    return candles


def generate_sample_boom_data(n_candles: int = 10000) -> list:
    """
    Generate sample Boom 1000 data for testing.
    Boom = normal drift down with periodic upward spikes.
    """
    print("\nGenerating sample Boom 1000 data (for testing only)...")
    
    np.random.seed(42)
    candles = []
    
    current_price = 5000
    current_time = datetime(2024, 1, 1)
    last_spike = 0
    
    for i in range(n_candles):
        # Normal downward drift
        drift = -np.random.uniform(0, 2)
        
        # Check if spike should occur (roughly every 1000 candles)
        spike = False
        if i - last_spike > 800 and np.random.random() < 0.01:
            spike = True
            last_spike = i
        
        if spike:
            # Spike: big upward move
            spike_size = np.random.uniform(15, 35)
            open_price = current_price
            close_price = current_price + spike_size
            high_price = close_price + np.random.uniform(0, 5)
            low_price = open_price - np.random.uniform(0, 2)
        else:
            # Normal candle
            open_price = current_price
            close_price = current_price + drift + np.random.normal(0, 1)
            high_price = max(open_price, close_price) + abs(np.random.normal(0, 0.5))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, 0.5))
        
        candles.append({
            'time': current_time,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': np.random.randint(50, 200)
        })
        
        current_price = close_price
        current_time += timedelta(minutes=1)
    
    print(f"Generated {len(candles)} sample Boom 1000 candles")
    return candles


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    """
    Run examples.
    
    To use with real data:
      1. Download V75/Boom data from Deriv
      2. Save as CSV with columns: time,open,high,low,close,volume
      3. Update filenames in load_*_data functions above
      4. Run this script
    """
    
    print("\n" + "=" * 80)
    print("OPUS34 SYNTHETIC STRATEGIES - EXAMPLES")
    print("=" * 80)
    print("\nNote: Using generated sample data for demonstration")
    print("For real backtests, download actual V75/Boom data from Deriv")
    print("=" * 80)
    
    # Run examples
    print("\n\nRunning Example 1: V75 Bollinger Strategy...")
    input("Press Enter to continue...")
    example_v75_bollinger()
    
    print("\n\nRunning Example 2: V75 RSI Strategy...")
    input("Press Enter to continue...")
    example_v75_rsi()
    
    print("\n\nRunning Example 3: Boom Spike Prediction...")
    input("Press Enter to continue...")
    example_boom_spike_prediction()
    
    print("\n\nRunning Example 4: Boom Post-Spike Reversion...")
    input("Press Enter to continue...")
    example_boom_post_spike()
    
    print("\n\nRunning Example 5: Compare All V75 Strategies...")
    input("Press Enter to continue...")
    example_compare_v75_strategies()
    
    print("\n" + "=" * 80)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Download real V75/Boom data from Deriv")
    print("2. Run backtests on real data")
    print("3. Validate strategies with 65%+ win rate")
    print("4. Paper trade on Deriv demo")
    print("5. Go live with proven strategies")
    print("=" * 80 + "\n")
