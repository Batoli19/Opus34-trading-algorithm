import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sniper_filter import SniperFilter


class _Val:
    def __init__(self, value: str):
        self.value = value


class DummySignal:
    def __init__(self):
        self.direction = _Val("BUY")
        self.setup_type = _Val("TURTLE_SOUP")
        self.entry = 2000.0
        self.sl = 1999.0
        self.tp = 2002.5
        self.confidence = 0.80
        self.valid = True


class DummyLowRRSignal(DummySignal):
    def __init__(self):
        super().__init__()
        self.tp = 2001.2  # RR ~= 1.2 with 1.0 risk


def _build_low_disp_candles(count: int = 40) -> list[dict]:
    candles = []
    px = 2000.0
    for i in range(count):
        o = px
        c = px + (0.06 if i % 2 else -0.05)
        if i == count - 1:
            c = px + 0.005
        h = max(o, c) + 0.08
        l = min(o, c) - 0.08
        candles.append({"open": o, "high": h, "low": l, "close": c})
        px = c
    return candles


def _build_chop_candles(count: int = 40) -> list[dict]:
    candles = []
    px = 2000.0
    for i in range(count):
        o = px
        c = px + (0.01 if i % 2 else -0.01)
        h = max(o, c) + 0.02
        l = min(o, c) - 0.02
        candles.append({"open": o, "high": h, "low": l, "close": c})
        px = c
    return candles


def _base_cfg() -> dict:
    return {
        "hybrid": {"allowed_kill_zones": ["LONDON_OPEN", "NY_OPEN", "LONDON_CLOSE"]},
        "execution": {
            "profile": "PROP_CHALLENGE",
            "min_confidence": 0.65,
            "min_rr": 2.0,
            "rr_epsilon": 0.0,
            "require_discount_premium": False,
            "max_sl_pips": {"XAUUSD": 100.0},
            "max_entry_distance_pips": {"XAUUSD": 500.0},
            "require_displacement": False,
            "min_displacement_atr_mult": 1.5,
            "require_close_beyond_structure": True,
            "avoid_chop": False,
            "chop_lookback": 24,
            "max_overlap_pct": 0.65,
            "reversal_gate_enabled": False,
            "one_trade_per_symbol_per_killzone": False,
            "reentry_requires_new_setup": False,
            "enforce_killzones": False,
        },
    }


class TestSniperRelaxedGates(unittest.TestCase):
    def test_no_displacement_still_passes(self):
        cfg = _base_cfg()
        filt = SniperFilter(cfg)
        signal = DummySignal()
        c5 = _build_low_disp_candles()
        c15 = _build_low_disp_candles(60)
        ok, reason, metrics = filt.evaluate(signal, "XAUUSD", c5, c15, c15, c15, "NONE", False)

        self.assertTrue(ok, msg=f"unexpected failure reason={reason}")
        self.assertEqual(reason, "OK")
        self.assertFalse(metrics.displacement_confirmed)

    def test_chop_range_not_blocking_when_avoid_chop_false(self):
        cfg = _base_cfg()
        cfg["execution"]["avoid_chop"] = False
        filt = SniperFilter(cfg)
        signal = DummySignal()
        c5 = _build_chop_candles()
        c15 = _build_chop_candles(60)
        ok, reason, metrics = filt.evaluate(signal, "XAUUSD", c5, c15, c15, c15, "NONE", False)

        self.assertTrue(ok, msg=f"unexpected failure reason={reason}")
        self.assertEqual(reason, "OK")
        self.assertEqual(metrics.market_state, "RANGE")

    def test_rr_hard_floor_blocks_under_1_3_even_if_min_rr_lower(self):
        cfg = _base_cfg()
        cfg["execution"]["min_rr"] = 1.0
        cfg["execution"]["rr_hard_floor"] = 1.3
        filt = SniperFilter(cfg)
        signal = DummyLowRRSignal()
        c5 = _build_low_disp_candles()
        c15 = _build_low_disp_candles(60)
        ok, reason, metrics = filt.evaluate(signal, "XAUUSD", c5, c15, c15, c15, "NONE", False)

        self.assertFalse(ok)
        self.assertEqual(reason, "LOW_RR_HARD_FLOOR")
        self.assertEqual(metrics.skip_reason, "LOW_RR_HARD_FLOOR")


if __name__ == "__main__":
    unittest.main()
