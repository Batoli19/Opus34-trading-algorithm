import os
import sys
import unittest

sys.path.append(os.path.dirname(__file__))

from risk_manager import RiskManager


class TestRiskLotSizingPipMath(unittest.TestCase):
    def test_stop_distance_uses_symbol_pip_size(self):
        cfg = {
            "risk": {"max_risk_per_trade_usd": 50, "risk_per_trade_pct": 1.0},
            "execution": {"max_sl_usd": 0},
            "mode": {"type": "normal"},
        }
        rm = RiskManager(cfg)

        # USDJPY: 0.10 price difference = 10 pips
        lot = rm.calculate_lot_size(
            symbol="USDJPY",
            entry=150.00,
            sl=149.90,
            tp=150.20,
            account_balance=10_000.0,
            confidence=1.0,
            pip_value_per_lot=6.5,  # approx at this price
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            rr=2.0,
        )
        self.assertGreater(lot, 0.0)

    def test_zero_stop_distance_returns_zero_lot(self):
        cfg = {
            "risk": {"max_risk_per_trade_usd": 50, "risk_per_trade_pct": 1.0},
            "execution": {"max_sl_usd": 0},
            "mode": {"type": "normal"},
        }
        rm = RiskManager(cfg)
        lot = rm.calculate_lot_size(
            symbol="EURUSD",
            entry=1.1000,
            sl=1.1000,
            tp=1.1050,
            account_balance=10_000.0,
            confidence=1.0,
            pip_value_per_lot=10.0,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            rr=2.0,
        )
        self.assertEqual(lot, 0.0)


if __name__ == "__main__":
    unittest.main()

