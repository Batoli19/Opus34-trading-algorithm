import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bot_engine


class TestEnginePropDailyLossFlatten(unittest.TestCase):
    def test_manage_open_positions_flattens_on_equity_breach(self):
        engine = bot_engine.TradingEngine.__new__(bot_engine.TradingEngine)

        positions = [
            {"ticket": 101, "symbol": "EURUSD", "type": "SELL", "tp": 1.0, "sl": 2.0},
            {"ticket": 102, "symbol": "GBPUSD", "type": "SELL", "tp": 1.0, "sl": 2.0},
        ]
        pendings = [{"ticket": 201}, {"ticket": 202}]

        engine.mt5 = Mock()
        engine.mt5.get_open_positions.return_value = positions
        engine.mt5.get_account_info.return_value = {"balance": 5000.0, "equity": 4890.0}
        engine.mt5.get_pending_orders.return_value = pendings
        engine.mt5.cancel_order.return_value = True
        engine.mt5.close_position.return_value = True

        engine.memory = Mock()
        engine.memory.get_daily_summary.return_value = {"daily_pnl": -120.0}
        engine._daily_window_utc = lambda: (datetime(2026, 3, 4, 0, 0, 0), datetime(2026, 3, 4, 23, 59, 59))

        engine.risk = Mock()
        engine.risk.can_trade.return_value = (
            False,
            "MAX_DAILY_LOSS_EQUITY eq=4890.00 floor=4900.00 ref=5000.00 pct=2.00 close_all=1",
        )
        engine.risk.should_close_all_on_daily_loss_breach.return_value = True

        engine._daily_loss_flatten_last_at = None
        engine._latest_equity = 0.0

        with patch.object(bot_engine.logger, "error") as err_log:
            asyncio.run(bot_engine.TradingEngine.manage_open_positions(engine))

            self.assertEqual(engine.mt5.cancel_order.call_count, 2)
            self.assertEqual(engine.mt5.close_position.call_count, 2)
            self.assertTrue(
                any("PROP_DAILY_LOSS_BREACH_FLATTEN" in str(c.args[0]) for c in err_log.call_args_list)
            )

            call_kwargs = engine.risk.can_trade.call_args.kwargs
            self.assertEqual(float(call_kwargs.get("equity")), 4890.0)

            asyncio.run(bot_engine.TradingEngine.manage_open_positions(engine))
            self.assertEqual(engine.mt5.cancel_order.call_count, 2)
            self.assertEqual(engine.mt5.close_position.call_count, 2)


if __name__ == "__main__":
    unittest.main()
