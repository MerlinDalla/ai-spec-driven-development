from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.models.currency_pair import CurrencyPair
from fund_transfer.models.fx_rate_snapshot import FxRateSnapshot


class FxRateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_snapshot(self) -> FxRateSnapshot | None:
        result = await self._session.execute(
            select(FxRateSnapshot)
            .where(FxRateSnapshot.is_stale == False)
            .order_by(FxRateSnapshot.effective_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshot_by_id(self, snapshot_id: uuid.UUID) -> FxRateSnapshot | None:
        result = await self._session.execute(select(FxRateSnapshot).where(FxRateSnapshot.id == snapshot_id))
        return result.scalar_one_or_none()

    async def insert_snapshot(self, rates_dict: dict, provider_source: str) -> FxRateSnapshot:
        snapshot = FxRateSnapshot(
            id=uuid.uuid4(),
            is_stale=False,
            provider_source=provider_source,
            rates={from_c: {to_c: str(r) for to_c, r in to_map.items()} for from_c, to_map in rates_dict.items()},
        )
        self._session.add(snapshot)
        await self._session.flush()
        await self._session.refresh(snapshot)
        return snapshot

    async def mark_stale(self, snapshot_id: uuid.UUID) -> None:
        await self._session.execute(update(FxRateSnapshot).where(FxRateSnapshot.id == snapshot_id).values(is_stale=True))
        await self._session.flush()

    async def get_active_currency_pairs(self) -> list[CurrencyPair]:
        result = await self._session.execute(select(CurrencyPair).where(CurrencyPair.is_active == True))
        return list(result.scalars().all())
