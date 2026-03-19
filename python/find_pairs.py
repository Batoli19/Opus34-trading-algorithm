# Fix 1: Find where bot_engine loads pairs
with open("python/bot_engine.py", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "XAUUSD" in line or "GBPJPY" in line or ("pairs" in line.lower() and ("symbol" in line.lower() or "[" in line)):
        print(f"Line {i+1}: {line.rstrip()}")
