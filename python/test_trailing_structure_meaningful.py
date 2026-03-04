import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from trailing_manager import StructureTrailingManager, TrailingState


def _mk_candle(ts, o, h, l, c):
    return {"time": ts, "open": o, "high": h, "low": l, "close": c}


def _flat_candles(t0: datetime, n: int, step_minutes: int, px: float, span: float) -> list[dict]:
    out = []
    for i in range(n):
        ts = t0 + timedelta(minutes=i * step_minutes)
        o = px + ((span * 0.2) if i % 2 else -(span * 0.1))
        c = px + ((span * 0.1) if i % 3 else -(span * 0.15))
        h = max(o, c) + span
        l = min(o, c) - span
        out.append(_mk_candle(ts, o, h, l, c))
    return out


def _base_cfg() -> dict:
    return {
        "risk": {"tp_miss_protection": {"enabled": False}},
        "trailing_structure": {
            "enabled": True,
            "fractal_left": 1,
            "fractal_right": 1,
            "swing_buffer_pips": 0.8,
            "swing_tf": "M1",
            "trailing_tf": "M5",
            "min_swing_pips": 0.5,
            "min_swing_atr_mult": 0.0,
            "atr_period": 14,
            "allow_ob_trail": False,
            "ob_min_impulse_atr_mult": 0.5,
            "be_enabled": True,
            "be_min_profit_pips": 6.0,
            "be_trigger_r_multiple": 0.6,
            "be_buffer_pips": 0.8,
            "lock_be_as_floor": True,
        },
    }


class TestStructureTrailingMeaningful(unittest.TestCase):
    def test_be_plus_buy_becomes_floor(self):
        cfg = _base_cfg()
        cfg["trailing_structure"]["allow_ob_trail"] = False
        cfg["trailing_structure"]["min_swing_pips"] = 999.0
        mgr = StructureTrailingManager(cfg)
        t0 = datetime(2026, 3, 4, 8, 0, 0)
        candles_m5 = _flat_candles(t0, 40, 5, 1.1010, 0.0002)
        candles_m1 = _flat_candles(t0, 180, 1, 1.1010, 0.0001)
        pos = {
            "ticket": 1,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1200,
            "open_time": t0 + timedelta(minutes=5),
        }

        res = mgr.evaluate_position(
            position=pos,
            candles_m5=candles_m5,
            candles_m1=candles_m1,
            bid=1.1015,
            ask=1.1017,
            symbol_info={"point": 0.00001, "stops_level": 10, "freeze_level": 0},
        )
        self.assertIsNotNone(res.get("new_sl"))
        self.assertGreaterEqual(float(res["new_sl"]), 1.10008)

    def test_be_plus_sell_becomes_floor(self):
        cfg = _base_cfg()
        cfg["trailing_structure"]["allow_ob_trail"] = False
        cfg["trailing_structure"]["min_swing_pips"] = 999.0
        mgr = StructureTrailingManager(cfg)
        t0 = datetime(2026, 3, 4, 8, 0, 0)
        candles_m5 = _flat_candles(t0, 40, 5, 1.1990, 0.0002)
        candles_m1 = _flat_candles(t0, 180, 1, 1.1990, 0.0001)
        pos = {
            "ticket": 2,
            "symbol": "EURUSD",
            "type": "SELL",
            "open_price": 1.2000,
            "sl": 1.2050,
            "tp": 1.1800,
            "open_time": t0 + timedelta(minutes=5),
        }

        res = mgr.evaluate_position(
            position=pos,
            candles_m5=candles_m5,
            candles_m1=candles_m1,
            bid=1.1978,
            ask=1.1980,
            symbol_info={"point": 0.00001, "stops_level": 10, "freeze_level": 0},
        )
        self.assertIsNotNone(res.get("new_sl"))
        self.assertLessEqual(float(res["new_sl"]), 1.19992)

    def test_swing_uses_m1_prefers_higher_low_above_entry(self):
        cfg = _base_cfg()
        cfg["trailing_structure"]["be_enabled"] = False
        cfg["trailing_structure"]["allow_ob_trail"] = False
        cfg["trailing_structure"]["swing_buffer_pips"] = 0.5
        mgr = StructureTrailingManager(cfg)
        t0 = datetime(2026, 3, 4, 8, 0, 0)
        candles_m5 = _flat_candles(t0, 40, 5, 1.1003, 0.0002)
        candles_m1 = [
            _mk_candle(t0 + timedelta(minutes=0), 1.1002, 1.1004, 1.1000, 1.1003),
            _mk_candle(t0 + timedelta(minutes=1), 1.1003, 1.1005, 1.1001, 1.1004),
            _mk_candle(t0 + timedelta(minutes=2), 1.1004, 1.1006, 1.1002, 1.1005),
            _mk_candle(t0 + timedelta(minutes=3), 1.1005, 1.1007, 1.1003, 1.1006),
            _mk_candle(t0 + timedelta(minutes=4), 1.1006, 1.1008, 1.1005, 1.1007),
            _mk_candle(t0 + timedelta(minutes=5), 1.1007, 1.1008, 1.1002, 1.1006),  # HL above entry
            _mk_candle(t0 + timedelta(minutes=6), 1.1006, 1.1009, 1.1004, 1.1008),
            _mk_candle(t0 + timedelta(minutes=7), 1.1008, 1.1010, 1.1006, 1.1009),
            _mk_candle(t0 + timedelta(minutes=8), 1.1009, 1.1011, 1.1007, 1.1010),
            _mk_candle(t0 + timedelta(minutes=9), 1.1010, 1.1011, 1.0996, 1.1000),  # later low below entry
            _mk_candle(t0 + timedelta(minutes=10), 1.1000, 1.1004, 1.0999, 1.1002),
            _mk_candle(t0 + timedelta(minutes=11), 1.1002, 1.1005, 1.1000, 1.1003),
            _mk_candle(t0 + timedelta(minutes=12), 1.1003, 1.1006, 1.1001, 1.1004),
        ]
        pos = {
            "ticket": 3,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.1000,
            "sl": 1.0970,
            "tp": 1.1200,
            "open_time": t0 + timedelta(minutes=1),
        }

        res = mgr.evaluate_position(
            position=pos,
            candles_m5=candles_m5,
            candles_m1=candles_m1,
            bid=1.1011,
            ask=1.1012,
            symbol_info={"point": 0.00001, "stops_level": 10, "freeze_level": 0},
        )
        self.assertIsNotNone(res.get("new_sl"))
        self.assertGreater(float(res["new_sl"]), 1.1000)

    def test_ob_trailing_uses_m5(self):
        cfg = _base_cfg()
        cfg["trailing_structure"]["be_enabled"] = False
        cfg["trailing_structure"]["allow_ob_trail"] = True
        cfg["trailing_structure"]["min_swing_pips"] = 999.0
        cfg["trailing_structure"]["min_swing_atr_mult"] = 999.0
        mgr = StructureTrailingManager(cfg)
        t0 = datetime(2026, 3, 4, 8, 0, 0)
        candles_m5 = [
            _mk_candle(t0 + timedelta(minutes=0), 1.1002, 1.1004, 1.1000, 1.1003),
            _mk_candle(t0 + timedelta(minutes=5), 1.1005, 1.1006, 1.0998, 1.1000),  # bearish
            _mk_candle(t0 + timedelta(minutes=10), 1.1000, 1.1012, 1.0999, 1.1011),  # bullish impulse > prev high
            _mk_candle(t0 + timedelta(minutes=15), 1.1011, 1.1013, 1.1009, 1.1012),
            _mk_candle(t0 + timedelta(minutes=20), 1.1012, 1.1014, 1.1010, 1.1013),
        ]
        candles_m1 = _flat_candles(t0, 120, 1, 1.1001, 0.00005)
        pos = {
            "ticket": 4,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1200,
            "open_time": t0,
        }
        res = mgr.evaluate_position(
            position=pos,
            candles_m5=candles_m5,
            candles_m1=candles_m1,
            bid=1.1010,
            ask=1.1012,
            symbol_info={"point": 0.00001, "stops_level": 10, "freeze_level": 0},
        )
        self.assertIsNotNone(res.get("new_sl"))
        self.assertEqual(res.get("reason"), "OB")

    def test_candidate_arbitration_buy_chooses_tightest(self):
        cfg = _base_cfg()
        cfg["trailing_structure"]["be_enabled"] = True
        cfg["trailing_structure"]["allow_ob_trail"] = False
        cfg["trailing_structure"]["be_min_profit_pips"] = 1.0
        cfg["trailing_structure"]["be_buffer_pips"] = 0.8
        cfg["trailing_structure"]["swing_buffer_pips"] = 0.2
        mgr = StructureTrailingManager(cfg)
        t0 = datetime(2026, 3, 4, 8, 0, 0)
        candles_m5 = _flat_candles(t0, 40, 5, 1.1008, 0.0002)
        candles_m1 = [
            _mk_candle(t0 + timedelta(minutes=0), 1.1004, 1.1006, 1.1002, 1.1005),
            _mk_candle(t0 + timedelta(minutes=1), 1.1005, 1.1008, 1.1004, 1.1007),
            _mk_candle(t0 + timedelta(minutes=2), 1.1007, 1.1009, 1.1006, 1.1008),
            _mk_candle(t0 + timedelta(minutes=3), 1.1008, 1.1010, 1.1007, 1.1009),
            _mk_candle(t0 + timedelta(minutes=4), 1.1009, 1.1011, 1.1008, 1.1010),
            _mk_candle(t0 + timedelta(minutes=5), 1.1010, 1.1012, 1.1004, 1.1011),  # swing low > entry
            _mk_candle(t0 + timedelta(minutes=6), 1.1011, 1.1013, 1.1009, 1.1012),
            _mk_candle(t0 + timedelta(minutes=7), 1.1012, 1.1014, 1.1010, 1.1013),
        ]
        pos = {
            "ticket": 5,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.1000,
            "sl": 1.0970,
            "tp": 1.1200,
            "open_time": t0 + timedelta(minutes=1),
        }
        res = mgr.evaluate_position(
            position=pos,
            candles_m5=candles_m5,
            candles_m1=candles_m1,
            bid=1.1014,
            ask=1.1016,
            symbol_info={"point": 0.00001, "stops_level": 10, "freeze_level": 0},
        )
        self.assertIsNotNone(res.get("new_sl"))
        self.assertEqual(res.get("reason"), "SWING")
        self.assertGreater(float(res["new_sl"]), 1.10008)

    def test_no_loosening_from_state_floor(self):
        cfg = _base_cfg()
        cfg["trailing_structure"]["allow_ob_trail"] = False
        cfg["trailing_structure"]["min_swing_pips"] = 999.0
        mgr = StructureTrailingManager(cfg)
        t0 = datetime(2026, 3, 4, 8, 0, 0)
        candles_m5 = _flat_candles(t0, 40, 5, 1.1010, 0.0001)
        candles_m1 = _flat_candles(t0, 120, 1, 1.1010, 0.00005)
        pos = {
            "ticket": 6,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.1000,
            "sl": 1.1005,
            "tp": 1.1200,
            "open_time": t0 + timedelta(minutes=1),
        }
        mgr._state[6] = TrailingState(last_sl=1.1010)
        res = mgr.evaluate_position(
            position=pos,
            candles_m5=candles_m5,
            candles_m1=candles_m1,
            bid=1.1015,
            ask=1.1017,
            symbol_info={"point": 0.00001, "stops_level": 10, "freeze_level": 0},
        )
        self.assertIsNone(res.get("new_sl"))

    def test_market_filter_rejects_stop_level_or_freeze(self):
        cfg = _base_cfg()
        cfg["trailing_structure"]["allow_ob_trail"] = False
        cfg["trailing_structure"]["min_swing_pips"] = 999.0
        mgr = StructureTrailingManager(cfg)
        t0 = datetime(2026, 3, 4, 8, 0, 0)
        candles_m5 = _flat_candles(t0, 40, 5, 1.1000, 0.0001)
        candles_m1 = _flat_candles(t0, 120, 1, 1.1000, 0.00005)
        pos = {
            "ticket": 7,
            "symbol": "EURUSD",
            "type": "BUY",
            "open_price": 1.1000,
            "sl": 1.0950,
            "tp": 1.1200,
            "open_time": t0 + timedelta(minutes=1),
        }
        res = mgr.evaluate_position(
            position=pos,
            candles_m5=candles_m5,
            candles_m1=candles_m1,
            bid=1.10010,
            ask=1.10020,
            symbol_info={"point": 0.00001, "stops_level": 20, "freeze_level": 20},
        )
        self.assertIsNone(res.get("new_sl"))


if __name__ == "__main__":
    unittest.main()
