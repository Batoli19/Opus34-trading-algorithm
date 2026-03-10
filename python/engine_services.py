from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EntryService:
    engine: object

    async def scan_all_pairs(self) -> None:
        await self.engine._scan_all_pairs()


@dataclass
class TradeManagementService:
    engine: object

    async def manage(self) -> None:
        await self.engine.manage_open_positions()
        await self.engine._fallback_closed_trade_sync()


@dataclass
class LearningService:
    engine: object

    def maybe_validate_adaptive_rules(self) -> None:
        self.engine._maybe_validate_adaptive_rules()

