"""
START_BOT.py
Utility script to quickly start the live trading bot.
"""
from pathlib import Path
import subprocess
import sys

def main():
    print("========================================")
    print("   ICT TRADING BOT - INITIALIZING...  ")
    print("========================================\n")
    
    bot_path = Path("01_LIVE_BOT/bot_engine.py")
    if not bot_path.exists():
        print("Error: Bot engine not found in 01_LIVE_BOT/")
        return
        
    print(f"Starting bot engine from {bot_path.resolve()}...")
    # In a real scenario, this would launch the bot.
    # For now, it's a structural placeholder.
    subprocess.run([sys.executable, str(bot_path)])

if __name__ == "__main__":
    main()
