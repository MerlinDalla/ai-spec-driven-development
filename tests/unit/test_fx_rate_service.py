from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from fund_transfer.core.exceptions import StaleRateError, UnsupportedCurrencyPairError
from fund_transfer.services.fx_rate_service import FxRateService


def make_snapshot(*, is_stale: bool = False, rates: dict | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        effective_at=datetime.now(timezone.utc),
        is_stale=is_stale,
        rates=rates or {"EUR": {"USD": "1.0850"}},
    )


@pytest.mark.asyncio
async def test_preview_raises_stale_rate_error():
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=make_snapshot(is_stale=True))
        service = FxRateService(AsyncMock())
        with pytest.raises(StaleRateError):
            await service.preview_conversion("EUR", "USD", Decimal("100.0000"))


@pytest.mark.asyncio
async def test_preview_raises_no_snapshot():
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=None)
        service = FxRateService(AsyncMock())
        with pytest.raises(StaleRateError):
            await service.preview_conversion("EUR", "USD", Decimal("100.0000"))


@pytest.mark.asyncio
async def test_preview_fee_calculation():
    snapshot = make_snapshot(rates={"EUR": {"USD": "1.0850"}})
    pairs = [SimpleNamespace(from_currency="EUR", to_currency="USD")]
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        repo.get_active_currency_pairs = AsyncMock(return_value=pairs)
        service = FxRateService(AsyncMock())
        response = await service.preview_conversion("EUR", "USD", Decimal("100.0000"))
    assert response.estimated_sending_fee == Decimal("0.5000")
    assert response.gross_converted_amount == Decimal("108.5000")
    assert response.estimated_receiving_fee == Decimal("0.3255")
    assert response.estimated_net_amount == Decimal("108.1745")
    assert response.total_sender_cost == Decimal("100.5000")


@pytest.mark.asyncio
async def test_preview_unsupported_pair():
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=make_snapshot())
        repo.get_active_currency_pairs = AsyncMock(return_value=[])
        service = FxRateService(AsyncMock())
        with pytest.raises(UnsupportedCurrencyPairError):
            await service.preview_conversion("EUR", "USD", Decimal("100.0000"))


@pytest.mark.asyncio
async def test_get_rate_table_success():
    snapshot = make_snapshot(rates={"EUR": {"USD": "1.0850", "GBP": "0.8570"}})
    pairs = [
        SimpleNamespace(from_currency="EUR", to_currency="USD"),
        SimpleNamespace(from_currency="EUR", to_currency="GBP"),
    ]
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=snapshot)
        repo.get_active_currency_pairs = AsyncMock(return_value=pairs)
        service = FxRateService(AsyncMock())
        response = await service.get_rate_table()
    assert response.snapshot_id == snapshot.id
    assert len(response.rates) == 2


@pytest.mark.asyncio
async def test_get_rate_table_no_snapshot():
    with patch("fund_transfer.services.fx_rate_service.FxRateRepository") as repo_cls:
        repo = repo_cls.return_value
        repo.get_latest_snapshot = AsyncMock(return_value=None)
        service = FxRateService(AsyncMock())
        with pytest.raises(StaleRateError):
            await service.get_rate_table()
