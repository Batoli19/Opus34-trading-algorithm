### 1. Data Coverage Summary
M5 data available: 2025-01-01 to 2025-02-28 (2 months).
M15/H1/H4 data continues to Dec 2025.
Because M5 is the trigger timeframe, the backtest window is strictly Jan 1 - Feb 28, 2025.
MT5 export for missing months failed (IPC timeout), so we restricted backtest to covered months.

### 2. Overall Summary
Total Trades: 33
Win Rate: 57.6% (19W / 13L)
Profit Factor: 1.40
Total Pips: +231.5
Expectancy: +5.67 pips per trade
Trades/Week: 3.9

### 3. Monthly Breakdown Table
| Month | Trades | WR | Total Pips | PF | Avg Win | Avg Loss | Status |
|---|---|---|---|---|---|---|---|
| 2025-01 | 19 | 73.7% | +350.3 | 2.40 | 43.0 | 50.2 | ✅ |
| 2025-02 | 14 | 35.7% | -118.8 | 0.63 | 41.1 | 40.5 | ❌ |

### 4. Setup Breakdown
| Setup | Trades | WR | PF | Total Pips | Avg Win | Avg Loss | Partial Rate |
|---|---|---|---|---|---|---|---|
| CHOCH | 28 | 53.6% | 1.42 | +205.1 | 46.5 | 41.1 | 53.6% |
| LIQUIDITY_SWEEP_REVERSAL | 5 | 80.0% | 1.32 | +26.4 | 27.1 | 82.1 | 80.0% |

### 5. Per-Pair Breakdown
| Pair | Trades | WR | PF | Total Pips | Avg Win | Avg Loss |
|---|---|---|---|---|---|---|
| USDJPY | 7 | 71.4% | 1.60 | +91.1 | 48.7 | 76.2 |
| GBPUSD | 18 | 50.0% | 1.23 | +79.1 | 47.4 | 43.5 |
| AUDUSD | 8 | 62.5% | 1.82 | +61.3 | 27.3 | 25.0 |

### 6. Exit Reason Breakdown
- TRAILED_SL: 9 trades (27.3%) | Avg pips: +56.9
- SL_HIT: 13 trades (39.4%) | Avg pips: -44.2
- GIVEBACK_GUARD: 10 trades (30.3%) | Avg pips: +29.4
- END_OF_DATA: 1 trades (3.0%) | Avg pips: +0.0

### 7. Kill Zone Split
- NY_OPEN: 16 trades | WR: 37.5% | PF: 0.61 | PnL: -151.6 pips
- LONDON_CLOSE: 17 trades | WR: 76.5% | PF: 3.05 | PnL: +383.1 pips

### 8. Regime Consistency Score
1 out of 2 profitable months (months with >= 2 trades).

### 9. 95% WR Confidence Interval
Sample WR: 57.6% (n=33)
95% CI Lower Bound: 40.7%
Verdict: Edge is NOT statistically significant (lower bound <= 50%).

### 10. Drawdown Analysis
Max consecutive losing trades: 3
Largest single-month loss in pips: -118.8
Worst-case max consecutive drawdown: $150 (3 trades x $50 risk)

