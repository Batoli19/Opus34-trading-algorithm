import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from trade_analyzer import TradeAnalyzer


class _DummyEngine:
    def __init__(self):
        self.mt5 = object()
        self.memory = object()
        self.brain = object()


class TestTradeAnalyzerPartialExitAggregation(unittest.TestCase):
    def setUp(self):
        self.analyzer = TradeAnalyzer(_DummyEngine())

    def test_build_exit_summary_aggregates_partial_exit_deals(self):
        db_trade = {
            "ticket": 10001,
            "order_ticket": 10001,
            "deal_ticket": 90001,
            "position_id": 10001,
            "symbol": "EURUSD",
            "entry_price": 1.10000,
            "entry_time": "2026-03-06T10:00:00",
        }
        deals = [
            {
                "deal_ticket": 91001,
                "ticket": 91001,
                "order_ticket": 10001,
                "position_id": 10001,
                "symbol": "EURUSD",
                "entry": 1,
                "type": "SELL",
                "profit": 40.0,
                "price": 1.10100,
                "volume": 0.60,
                "time": "2026-03-06T10:10:00",
            },
            {
                "deal_ticket": 91002,
                "ticket": 91002,
                "order_ticket": 10001,
                "position_id": 10001,
                "symbol": "EURUSD",
                "entry": 1,
                "type": "SELL",
                "profit": 55.0,
                "price": 1.10200,
                "volume": 0.40,
                "time": "2026-03-06T10:30:00",
            },
            {
                "deal_ticket": 92001,
                "ticket": 92001,
                "order_ticket": 20002,
                "position_id": 20002,
                "symbol": "EURUSD",
                "entry": 1,
                "type": "SELL",
                "profit": 999.0,
                "price": 1.20000,
                "volume": 1.00,
                "time": "2026-03-06T10:40:00",
            },
        ]

        summary = self.analyzer._build_exit_summary(db_trade, deals)

        self.assertIsNotNone(summary)
        self.assertEqual(int(summary["deal_ticket"]), 91002)
        self.assertEqual(int(summary["exit_deal_count"]), 2)
        self.assertAlmostEqual(float(summary["profit"]), 95.0, places=6)
        self.assertAlmostEqual(float(summary["exit_volume_total"]), 1.0, places=6)
        self.assertAlmostEqual(float(summary["price"]), 1.1014, places=6)

    def test_build_exit_summary_ignores_pre_entry_exit_deals(self):
        db_trade = {
            "ticket": 30003,
            "order_ticket": 30003,
            "deal_ticket": 80001,
            "position_id": 30003,
            "symbol": "GBPUSD",
            "entry_price": 1.33000,
            "entry_time": "2026-03-06T12:00:00",
        }
        deals = [
            {
                "deal_ticket": 81001,
                "ticket": 81001,
                "order_ticket": 30003,
                "position_id": 30003,
                "symbol": "GBPUSD",
                "entry": 1,
                "type": "SELL",
                "profit": 10.0,
                "price": 1.32950,
                "volume": 0.30,
                "time": "2026-03-06T11:30:00",
            },
            {
                "deal_ticket": 81002,
                "ticket": 81002,
                "order_ticket": 30003,
                "position_id": 30003,
                "symbol": "GBPUSD",
                "entry": 1,
                "type": "SELL",
                "profit": 15.0,
                "price": 1.32910,
                "volume": 0.70,
                "time": "2026-03-06T12:20:00",
            },
        ]

        summary = self.analyzer._build_exit_summary(db_trade, deals)

        self.assertIsNotNone(summary)
        self.assertEqual(int(summary["exit_deal_count"]), 1)
        self.assertAlmostEqual(float(summary["profit"]), 15.0, places=6)
        self.assertAlmostEqual(float(summary["price"]), 1.32910, places=6)


if __name__ == "__main__":
    unittest.main()
