"""
╔══════════════════════════════════════════════════════════════════════╗
║           ICT TRADING BOT - Command Center Edition                   ║
║   Markets: Forex + Stocks | Platform: MetaTrader 5                  ║
║   NEW: Flask API + Test Mode + Live Dashboard                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from bot_engine import TradingEngine
from config_loader import load_config
from logger_setup import setup_logger
from news_filter import NewsFilter
from dashboard import Dashboard
from api_server import DashboardAPI
from test_mode import TestMode

# ─── Bootstrap ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
LOG_DIR  = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = setup_logger("MAIN", LOG_DIR / "bot.log")

# ─── Graceful Shutdown ─────────────────────────────────────────────────────────
shutdown_event = asyncio.Event()

def handle_signal(sig, frame):
    logger.warning(f"⚠️  Signal {sig} received — initiating graceful shutdown...")
    shutdown_event.set()

signal.signal(signal.SIGINT,  handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# ─── Main ──────────────────────────────────────────────────────────────────────
async def main():
    logger.info("=" * 70)
    logger.info("🤖  ICT TRADING BOT - COMMAND CENTER EDITION")
    logger.info(f"🕐  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # Load config
    config = load_config(BASE_DIR / "config" / "settings.json")
    logger.info(f"✅  Config loaded | Pairs: {config['pairs']}")

    # Check for test mode flag
    test_mode_enabled = config.get('test_mode', {}).get('enabled', False)
    
    if test_mode_enabled:
        logger.warning("⚠️" * 20)
        logger.warning("⚠️  TEST MODE ACTIVATED")
        logger.warning("⚠️  Will force trades every 5 minutes")
        logger.warning("⚠️  All filters BYPASSED (kill zones, news, bias)")
        logger.warning("⚠️  USE ON DEMO ACCOUNTS ONLY!")
        logger.warning("⚠️" * 20)
    
    # Init components
    news_filter = NewsFilter(config["news"])
    engine      = TradingEngine(config, news_filter, shutdown_event)
    dashboard   = Dashboard(engine)
    api_server  = DashboardAPI(engine, host="0.0.0.0", port=5000)
    
    # Start Flask API in background thread
    api_server.run_async()
    
    # Start components
    tasks = [
        asyncio.create_task(engine.run(),          name="engine"),
        asyncio.create_task(dashboard.run(),       name="dashboard"),
        asyncio.create_task(shutdown_event.wait(), name="shutdown_watcher"),
    ]
    
    # Add test mode if enabled
    if test_mode_enabled:
        test_mode = TestMode(
            engine, 
            interval_seconds=config.get('test_mode', {}).get('interval_seconds', 300)
        )
        tasks.append(asyncio.create_task(test_mode.run(), name="test_mode"))
        logger.info("🎲  Test mode task added")
    
    logger.info("🚀  All systems running. Bot is LIVE.")
    logger.info(f"🌐  Dashboard available at: http://localhost:5000")
    logger.info(f"📊  Open command_center.html in your browser\n")

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    # Cleanup
    logger.info("🛑  Shutting down...")
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    await engine.shutdown()
    logger.info("✅  Bot shut down cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Interrupted by user]")
        sys.exit(0)
