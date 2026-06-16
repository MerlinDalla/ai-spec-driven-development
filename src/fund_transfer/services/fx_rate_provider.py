from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol, runtime_checkable

import httpx
from opentelemetry import trace

_tracer = trace.get_tracer(__name__)


@dataclass(frozen=True)
class RateSnapshot:
    rates: dict[str, dict[str, Decimal]]
    fetched_at: datetime
    provider: str


@runtime_checkable
class FxRateProvider(Protocol):
    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal: ...
    async def get_snapshot(self) -> RateSnapshot: ...
    async def is_stale(self) -> bool: ...
    async def refresh(self) -> None: ...
    def validate_currency(self, code: str) -> None: ...


class StaticFxRateProvider:
    """Wraps ExchangeRateConfig for backward compat / local dev. Never stale."""

    def __init__(self, config) -> None:
        self._config = config
        self._snapshot = RateSnapshot(
            rates=config.rates,
            fetched_at=datetime.now(timezone.utc),
            provider="static_config",
        )

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        self.validate_currency(from_currency)
        self.validate_currency(to_currency)
        try:
            return self._config.rates[from_currency][to_currency]
        except KeyError as exc:
            from fund_transfer.core.exceptions import UnsupportedCurrencyPairError

            raise UnsupportedCurrencyPairError(f"No rate for {from_currency}/{to_currency}") from exc

    async def get_snapshot(self) -> RateSnapshot:
        return self._snapshot

    async def is_stale(self) -> bool:
        return False

    async def refresh(self) -> None:
        return None

    def validate_currency(self, code: str) -> None:
        if code not in self._config.supported_currencies:
            from fund_transfer.core.exceptions import UnsupportedCurrencyPairError

            raise UnsupportedCurrencyPairError(f"Unsupported currency: {code}")


class TreasuryFeedAdapter:
    """Fetches rates from an external treasury feed."""

    def __init__(self, feed_url: str, timeout_seconds: int = 5) -> None:
        self._feed_url = feed_url
        self._timeout = timeout_seconds
        self._lock = asyncio.Lock()
        self._snapshot: RateSnapshot | None = None
        self._consecutive_failures = 0
        self._is_stale = False
        self._max_failures = 3

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        snapshot = await self.get_snapshot()
        try:
            return snapshot.rates[from_currency][to_currency]
        except KeyError as exc:
            from fund_transfer.core.exceptions import UnsupportedCurrencyPairError

            raise UnsupportedCurrencyPairError(f"No rate for {from_currency}/{to_currency}") from exc

    async def get_snapshot(self) -> RateSnapshot:
        if self._snapshot is None:
            await self.refresh()
        return self._snapshot  # type: ignore[return-value]

    async def is_stale(self) -> bool:
        return self._is_stale

    async def refresh(self) -> None:
        async with self._lock:
            await self._do_refresh()

    async def _do_refresh(self) -> None:
        timeout = httpx.Timeout(self._timeout, connect=self._timeout)
        backoff = 0.5
        for attempt in range(3):
            with _tracer.start_as_current_span("treasury_feed.refresh") as span:
                span.set_attribute("provider_url", self._feed_url)
                start = time.monotonic()
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.get(self._feed_url)
                        response.raise_for_status()
                        data = response.json()
                        rates = {
                            from_c: {to_c: Decimal(str(rate)) for to_c, rate in to_map.items()}
                            for from_c, to_map in data.items()
                        }
                        self._snapshot = RateSnapshot(
                            rates=rates,
                            fetched_at=datetime.now(timezone.utc),
                            provider="treasury_feed",
                        )
                        self._consecutive_failures = 0
                        self._is_stale = False
                        duration_ms = int((time.monotonic() - start) * 1000)
                        span.set_attribute("duration_ms", duration_ms)
                        span.set_attribute("is_stale", False)
                        return
                except Exception:
                    self._consecutive_failures += 1
                    duration_ms = int((time.monotonic() - start) * 1000)
                    span.set_attribute("duration_ms", duration_ms)
                    span.set_attribute("is_stale", self._consecutive_failures >= self._max_failures)
                    if attempt < 2:
                        await asyncio.sleep(backoff * (2**attempt))
        if self._consecutive_failures >= self._max_failures:
            self._is_stale = True

    def validate_currency(self, code: str) -> None:
        if self._snapshot is None:
            return
        has_currency = any(code in rates or code == from_currency for from_currency, rates in self._snapshot.rates.items())
        if not has_currency:
            from fund_transfer.core.exceptions import UnsupportedCurrencyPairError

            raise UnsupportedCurrencyPairError(f"Unsupported currency: {code}")
