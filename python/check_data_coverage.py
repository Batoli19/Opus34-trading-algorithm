from backtester import CandleReplay
from pathlib import Path
import sys
import logging

logging.basicConfig(level=logging.WARNING)

data_dir = Path(r"c:\Users\user\Documents\BAC\ict_trading_bot\backtest_data")
replay = CandleReplay(data_dir)

symbols = ["USDJPY", "GBPUSD", "AUDUSD"]
timeframes = ["M1", "M5", "M15", "H1", "H4"]

for symbol in symbols:
    replay.load(symbol, timeframes)

print("\n--- DATA COVERAGE SUMMARY ---")
for symbol in symbols:
    for tf in timeframes:
        key = f"{symbol}_{tf}"
        candles = replay._data.get(key, [])
        if candles:
            start_time = candles[0]["time"]
            end_time = candles[-1]["time"]
            print(f"DATA: {symbol} {tf} | {start_time} → {end_time} | n={len(candles)}")
        else:
            print(f"DATA: {symbol} {tf} | NO DATA")
