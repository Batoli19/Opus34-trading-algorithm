from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=256)
def pip_size(symbol: str) -> float:
    s = str(symbol or "").upper()
    if s.endswith("JPY") or "JPY" in s:
        return 0.01
    if s in ("US30", "NAS100", "SPX500"):
        return 1.0
    if "XAU" in s:
        return 0.1
    return 0.0001


def to_pips(price_diff: float, symbol: str) -> float:
    ps = pip_size(symbol)
    return abs(float(price_diff)) / ps if ps else 0.0


def from_pips(pips: float, symbol: str) -> float:
    return float(pips) * pip_size(symbol)

