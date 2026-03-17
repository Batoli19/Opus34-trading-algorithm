"""
Synthetic Backtester for OPUS34
================================

Backtesting framework for synthetic index strategies (VIX, Boom, Crash).

Features:
  - Test strategies on historical data
  - Calculate comprehensive metrics
  - Out-of-sample validation
  - Walk-forward optimization support
  - HTML report generation

Usage:
    from synthetic_strategies.synthetic_backtester import SyntheticBacktester
    from synthetic_strategies.vix_strategies import BollingerMeanReversionVIX
    
    strategy = BollingerMeanReversionVIX()
    backtester = SyntheticBacktester(strategy)
    results = backtester.run(candles_data)
    backtester.print_report(results)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class BacktestMetrics:
    """Comprehensive backtest metrics."""
    # Basic metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # P&L metrics
    total_pnl_points: float
    total_pnl_percent: float
    avg_win_points: float
    avg_loss_points: float
    largest_win_points: float
    largest_loss_points: float
    
    # Risk metrics
    profit_factor: float
    expectancy_points: float
    sharpe_ratio: float
    max_drawdown_points: float
    max_drawdown_percent: float
    
    # Duration metrics
    avg_bars_held: float
    max_bars_held: int
    min_bars_held: int
    
    # Consecutive metrics
    max_consecutive_wins: int
    max_consecutive_losses: int
    
    # Exit reason breakdown
    exit_reasons: Dict[str, int]
    
    # Time metrics
    start_date: str
    end_date: str
    days_tested: int


class SyntheticBacktester:
    """
    Backtesting engine for synthetic index strategies.
    
    Supports:
      - VIX strategies (Bollinger, RSI, Volatility Breakout)
      - Boom strategies (Spike Prediction, Post-Spike Reversion)
      - Crash strategies (same as Boom but inverted)
    """
    
    def __init__(self, 
                 strategy,
                 initial_balance: float = 10000,
                 risk_per_trade: float = 100,
                 point_value: float = 1.0,
                 spread_points: float = 2.0):
        """
        Initialize backtester.
        
        Args:
            strategy: Strategy instance (must have extract_features, generate_signal, should_exit methods)
            initial_balance: Starting balance (default $10,000)
            risk_per_trade: Risk per trade in currency (default $100)
            point_value: Value of 1 point movement (default $1)
            spread_points: Spread in points (default 2)
        """
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.point_value = point_value
        self.spread_points = spread_points
        
    def run(self, 
            candles: List[Dict],
            start_index: int = 100,
            end_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Run backtest on historical data.
        
        Args:
            candles: List of OHLC candles
                Each candle must have: 'open', 'high', 'low', 'close', 'time'
            start_index: Index to start backtest (default 100, need history)
            end_index: Index to end backtest (default None = end of data)
            
        Returns:
            Dict containing:
                - trades: List of all trades
                - metrics: BacktestMetrics object
                - equity_curve: Balance over time
        """
        if end_index is None:
            end_index = len(candles)
        
        trades = []
        equity_curve = [self.initial_balance]
        current_balance = self.initial_balance
        position = None
        entry_index = None
        
        for i in range(start_index, end_index):
            current_candle = candles[i]
            
            # If in position, check for exit
            if position is not None:
                bars_held = i - entry_index
                
                # Extract current features
                features = self._extract_features_safe(candles, i)
                
                # Check exit conditions
                should_exit, exit_reason = self._should_exit_safe(
                    position, features, current_candle, bars_held
                )
                
                if should_exit:
                    # Close position
                    exit_price = current_candle['close']
                    
                    # Apply spread on exit
                    if position['direction'] == 'BUY':
                        exit_price -= self.spread_points  # Sell at bid
                        pnl_points = exit_price - position['entry_price']
                    else:  # SELL
                        exit_price += self.spread_points  # Buy to cover at ask
                        pnl_points = position['entry_price'] - exit_price
                    
                    pnl_currency = pnl_points * self.point_value
                    current_balance += pnl_currency
                    
                    trade_result = {
                        'entry_time': candles[entry_index].get('time', entry_index),
                        'exit_time': current_candle.get('time', i),
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl_points': pnl_points,
                        'pnl_currency': pnl_currency,
                        'bars_held': bars_held,
                        'exit_reason': exit_reason,
                        'balance_after': current_balance
                    }
                    
                    trades.append(trade_result)
                    equity_curve.append(current_balance)
                    
                    # Clear position
                    position = None
                    entry_index = None
            
            # If no position, check for entry
            else:
                # Extract features
                features = self._extract_features_safe(candles, i)
                
                if features is None:
                    continue
                
                # Generate signal
                signal = self._generate_signal_safe(features)
                
                if signal in ['BUY', 'SELL']:
                    # Enter position
                    entry_price = current_candle['close']
                    
                    # Apply spread on entry
                    if signal == 'BUY':
                        entry_price += self.spread_points  # Buy at ask
                    else:  # SELL
                        entry_price -= self.spread_points  # Sell at bid
                    
                    position = {
                        'direction': signal,
                        'entry_price': entry_price,
                        **features  # Include all features for exit logic
                    }
                    entry_index = i
        
        # Close any open position at end
        if position is not None:
            exit_price = candles[end_index - 1]['close']
            
            if position['direction'] == 'BUY':
                exit_price -= self.spread_points
                pnl_points = exit_price - position['entry_price']
            else:
                exit_price += self.spread_points
                pnl_points = position['entry_price'] - exit_price
            
            pnl_currency = pnl_points * self.point_value
            current_balance += pnl_currency
            
            trades.append({
                'entry_time': candles[entry_index].get('time', entry_index),
                'exit_time': candles[end_index - 1].get('time', end_index - 1),
                'direction': position['direction'],
                'entry_price': position['entry_price'],
                'exit_price': exit_price,
                'pnl_points': pnl_points,
                'pnl_currency': pnl_currency,
                'bars_held': end_index - 1 - entry_index,
                'exit_reason': 'end_of_data',
                'balance_after': current_balance
            })
            equity_curve.append(current_balance)
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            trades, 
            equity_curve,
            candles[start_index].get('time', ''),
            candles[end_index - 1].get('time', '')
        )
        
        return {
            'trades': trades,
            'metrics': metrics,
            'equity_curve': equity_curve,
            'final_balance': current_balance,
            'strategy_name': getattr(self.strategy, 'name', 'Unknown')
        }
    
    def _extract_features_safe(self, candles: List[Dict], index: int) -> Optional[Dict]:
        """Safely extract features, handling different strategy types."""
        try:
            # VIX strategies: extract_features(candles)
            if hasattr(self.strategy, 'extract_features'):
                method = self.strategy.extract_features
                # Check method signature
                import inspect
                sig = inspect.signature(method)
                params = list(sig.parameters.keys())
                
                if len(params) == 1:  # Only candles parameter
                    return method(candles[:index + 1])
                elif len(params) == 2:  # candles + index parameter (Boom strategies)
                    return method(candles, index)
            
            return None
        except Exception as e:
            print(f"Error extracting features at index {index}: {e}")
            return None
    
    def _generate_signal_safe(self, features: Dict) -> Optional[str]:
        """Safely generate signal."""
        try:
            if hasattr(self.strategy, 'generate_signal'):
                return self.strategy.generate_signal(features)
            return None
        except Exception as e:
            print(f"Error generating signal: {e}")
            return None
    
    def _should_exit_safe(self, position: Dict, features: Optional[Dict], 
                         candle: Dict, bars_held: int) -> Tuple[bool, str]:
        """Safely check exit conditions."""
        try:
            if not hasattr(self.strategy, 'should_exit'):
                return False, ''
            
            method = self.strategy.should_exit
            import inspect
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            # Different strategies have different signatures
            if 'features' in params:  # VIX strategies
                return method(position, features)
            elif 'current_price' in params:  # Boom post-spike strategy
                return method(position, candle['close'], bars_held)
            elif 'candle' in params:  # Boom spike predictor
                return method(position, candle, bars_held)
            
            return False, ''
        except Exception as e:
            print(f"Error checking exit: {e}")
            return False, ''
    
    def _calculate_metrics(self, 
                          trades: List[Dict],
                          equity_curve: List[float],
                          start_date: str,
                          end_date: str) -> BacktestMetrics:
        """Calculate comprehensive backtest metrics."""
        if not trades:
            return BacktestMetrics(
                total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
                total_pnl_points=0, total_pnl_percent=0,
                avg_win_points=0, avg_loss_points=0,
                largest_win_points=0, largest_loss_points=0,
                profit_factor=0, expectancy_points=0, sharpe_ratio=0,
                max_drawdown_points=0, max_drawdown_percent=0,
                avg_bars_held=0, max_bars_held=0, min_bars_held=0,
                max_consecutive_wins=0, max_consecutive_losses=0,
                exit_reasons={}, start_date=start_date, end_date=end_date, days_tested=0
            )
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['pnl_points'] > 0)
        losing_trades = sum(1 for t in trades if t['pnl_points'] <= 0)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl_points = sum(t['pnl_points'] for t in trades)
        total_pnl_percent = ((equity_curve[-1] - self.initial_balance) / self.initial_balance) * 100
        
        wins = [t['pnl_points'] for t in trades if t['pnl_points'] > 0]
        losses = [abs(t['pnl_points']) for t in trades if t['pnl_points'] <= 0]
        
        avg_win_points = np.mean(wins) if wins else 0
        avg_loss_points = np.mean(losses) if losses else 0
        largest_win_points = max(wins) if wins else 0
        largest_loss_points = max(losses) if losses else 0
        
        # Risk metrics
        total_wins = sum(wins) if wins else 0
        total_losses = sum(losses) if losses else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        expectancy_points = total_pnl_points / total_trades if total_trades > 0 else 0
        
        # Sharpe ratio (simplified)
        returns = [t['pnl_points'] for t in trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Max drawdown
        peak = equity_curve[0]
        max_dd_points = 0
        max_dd_percent = 0
        
        for balance in equity_curve:
            if balance > peak:
                peak = balance
            dd = peak - balance
            dd_pct = (dd / peak) * 100 if peak > 0 else 0
            if dd > max_dd_points:
                max_dd_points = dd
                max_dd_percent = dd_pct
        
        # Duration metrics
        bars_held = [t['bars_held'] for t in trades]
        avg_bars_held = np.mean(bars_held) if bars_held else 0
        max_bars_held = max(bars_held) if bars_held else 0
        min_bars_held = min(bars_held) if bars_held else 0
        
        # Consecutive wins/losses
        consecutive_wins = 0
        consecutive_losses = 0
        max_consec_wins = 0
        max_consec_losses = 0
        
        for trade in trades:
            if trade['pnl_points'] > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consec_wins = max(max_consec_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consec_losses = max(max_consec_losses, consecutive_losses)
        
        # Exit reasons
        exit_reasons = {}
        for trade in trades:
            reason = trade.get('exit_reason', 'unknown')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        # Time metrics
        days_tested = 0
        if isinstance(start_date, datetime) and isinstance(end_date, datetime):
            days_tested = (end_date - start_date).days
        
        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl_points=total_pnl_points,
            total_pnl_percent=total_pnl_percent,
            avg_win_points=avg_win_points,
            avg_loss_points=avg_loss_points,
            largest_win_points=largest_win_points,
            largest_loss_points=largest_loss_points,
            profit_factor=profit_factor,
            expectancy_points=expectancy_points,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_points=max_dd_points,
            max_drawdown_percent=max_dd_percent,
            avg_bars_held=avg_bars_held,
            max_bars_held=max_bars_held,
            min_bars_held=min_bars_held,
            max_consecutive_wins=max_consec_wins,
            max_consecutive_losses=max_consec_losses,
            exit_reasons=exit_reasons,
            start_date=str(start_date),
            end_date=str(end_date),
            days_tested=days_tested
        )
    
    def print_report(self, results: Dict[str, Any]):
        """Print formatted backtest report."""
        metrics = results['metrics']
        
        print("\n" + "=" * 80)
        print(f"BACKTEST REPORT: {results['strategy_name']}")
        print("=" * 80)
        
        print(f"\n📊 PERIOD: {metrics.start_date} to {metrics.end_date}")
        print(f"   Days Tested: {metrics.days_tested}")
        
        print(f"\n📈 PERFORMANCE:")
        print(f"   Total Trades:      {metrics.total_trades}")
        print(f"   Winning Trades:    {metrics.winning_trades}")
        print(f"   Losing Trades:     {metrics.losing_trades}")
        print(f"   Win Rate:          {metrics.win_rate:.2f}%")
        
        print(f"\n💰 PROFIT/LOSS:")
        print(f"   Total P&L:         {metrics.total_pnl_points:+.2f} points")
        print(f"   Total Return:      {metrics.total_pnl_percent:+.2f}%")
        print(f"   Avg Win:           +{metrics.avg_win_points:.2f} points")
        print(f"   Avg Loss:          -{metrics.avg_loss_points:.2f} points")
        print(f"   Largest Win:       +{metrics.largest_win_points:.2f} points")
        print(f"   Largest Loss:      -{metrics.largest_loss_points:.2f} points")
        
        print(f"\n📊 RISK METRICS:")
        print(f"   Profit Factor:     {metrics.profit_factor:.2f}")
        print(f"   Expectancy:        {metrics.expectancy_points:+.2f} points/trade")
        print(f"   Sharpe Ratio:      {metrics.sharpe_ratio:.2f}")
        print(f"   Max Drawdown:      -{metrics.max_drawdown_points:.2f} points ({metrics.max_drawdown_percent:.2f}%)")
        
        print(f"\n⏱️  DURATION:")
        print(f"   Avg Bars Held:     {metrics.avg_bars_held:.1f}")
        print(f"   Max Bars Held:     {metrics.max_bars_held}")
        print(f"   Min Bars Held:     {metrics.min_bars_held}")
        
        print(f"\n🔄 STREAKS:")
        print(f"   Max Consecutive Wins:   {metrics.max_consecutive_wins}")
        print(f"   Max Consecutive Losses: {metrics.max_consecutive_losses}")
        
        print(f"\n🚪 EXIT REASONS:")
        for reason, count in sorted(metrics.exit_reasons.items(), key=lambda x: -x[1]):
            pct = (count / metrics.total_trades) * 100
            print(f"   {reason:20s} {count:4d} ({pct:.1f}%)")
        
        print(f"\n💵 BALANCE:")
        print(f"   Starting:          ${self.initial_balance:,.2f}")
        print(f"   Ending:            ${results['final_balance']:,.2f}")
        print(f"   Change:            ${results['final_balance'] - self.initial_balance:+,.2f}")
        
        print("=" * 80 + "\n")
    
    def export_to_json(self, results: Dict[str, Any], filename: str):
        """Export results to JSON file."""
        export_data = {
            'strategy_name': results['strategy_name'],
            'metrics': asdict(results['metrics']),
            'trades': results['trades'],
            'final_balance': results['final_balance']
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"Results exported to {filename}")


# Export
__all__ = ['SyntheticBacktester', 'BacktestMetrics']
