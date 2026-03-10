import os
import sys
import unittest

sys.path.append(os.path.dirname(__file__))

from market_math import from_pips, pip_size, to_pips
from ict_strategy import ICTStrategy


class TestMarketMathConsistency(unittest.TestCase):
    def test_pip_sizes(self):
        self.assertEqual(pip_size("EURUSD"), 0.0001)
        self.assertEqual(pip_size("GBPUSD"), 0.0001)
        self.assertEqual(pip_size("USDJPY"), 0.01)
        self.assertEqual(pip_size("GBPJPY"), 0.01)
        self.assertEqual(pip_size("XAUUSD"), 0.1)

    def test_roundtrip_pips_price(self):
        for sym in ("EURUSD", "USDJPY", "GBPJPY", "XAUUSD"):
            price = from_pips(12.5, sym)
            self.assertAlmostEqual(to_pips(price, sym), 12.5, places=6)

    def test_ict_strategy_uses_shared_math(self):
        strat = ICTStrategy({"ict": {}, "scalping": {}, "execution": {}})
        self.assertAlmostEqual(strat.get_pip_size("USDJPY"), 0.01)
        self.assertAlmostEqual(strat.to_pips(0.10, "USDJPY"), 10.0, places=6)


if __name__ == "__main__":
    unittest.main()

