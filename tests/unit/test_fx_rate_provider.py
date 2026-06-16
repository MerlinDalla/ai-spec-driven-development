from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fund_transfer.core.exceptions import UnsupportedCurrencyPairError
from fund_transfer.services.fx_rate_provider import StaticFxRateProvider, TreasuryFeedAdapter


@pytest.mark.asyncio
async def test_static_is_stale_always_false(exchange_rate_config):
    provider = StaticFxRateProvider(exchange_rate_config)
    assert await provider.is_stale() is False


@pytest.mark.asyncio
async def test_static_get_rate_returns_correct_rate(exchange_rate_config):
    provider = StaticFxRateProvider(exchange_rate_config)
    assert await provider.get_rate("EUR", "USD") == Decimal("1.08500000")


@pytest.mark.asyncio
async def test_static_unsupported_currency_raises(exchange_rate_config):
    provider = StaticFxRateProvider(exchange_rate_config)
    with pytest.raises(UnsupportedCurrencyPairError):
        await provider.get_rate("EUR", "XYZ")


@pytest.mark.asyncio
async def test_treasury_feed_success():
    provider = TreasuryFeedAdapter("http://example.test/rates")
    response = MagicMock()
    response.json.return_value = {"EUR": {"USD": "1.0850"}}
    response.raise_for_status.return_value = None
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    with patch("fund_transfer.services.fx_rate_provider.httpx.AsyncClient", return_value=client):
        snapshot = await provider.get_snapshot()
    assert snapshot.rates["EUR"]["USD"] == Decimal("1.0850")


@pytest.mark.asyncio
async def test_treasury_feed_timeout_marks_stale_after_3_failures():
    provider = TreasuryFeedAdapter("http://example.test/rates")
    client = AsyncMock()
    client.get.side_effect = TimeoutError("timeout")
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    with patch("fund_transfer.services.fx_rate_provider.httpx.AsyncClient", return_value=client):
        await provider.refresh()
    assert await provider.is_stale() is True
