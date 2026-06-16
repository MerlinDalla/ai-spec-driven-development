from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.core.config import get_settings
from fund_transfer.core.exceptions import StaleRateError, UnsupportedCurrencyPairError
from fund_transfer.repositories.fx_rate_repository import FxRateRepository
from fund_transfer.schemas.fx import ConversionPreviewResponse, ExchangeRateSchema, RateTableResponse

QUANT = Decimal("0.0001")


class FxRateService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = FxRateRepository(session)
        self._settings = get_settings()

    async def get_rate_table(self) -> RateTableResponse:
        snapshot = await self._repo.get_latest_snapshot()
        if snapshot is None:
            raise StaleRateError("No exchange rate snapshot available.")
        rates = []
        for pair in await self._repo.get_active_currency_pairs():
            rate_str = snapshot.rates.get(pair.from_currency, {}).get(pair.to_currency)
            if rate_str:
                rates.append(
                    ExchangeRateSchema(
                        from_currency=pair.from_currency,
                        to_currency=pair.to_currency,
                        rate=Decimal(str(rate_str)),
                    )
                )
        return RateTableResponse(
            snapshot_id=snapshot.id,
            effective_at=snapshot.effective_at,
            is_stale=snapshot.is_stale,
            rates=rates,
        )

    async def preview_conversion(self, from_currency: str, to_currency: str, amount: Decimal) -> ConversionPreviewResponse:
        snapshot = await self._repo.get_latest_snapshot()
        if snapshot is None or snapshot.is_stale:
            raise StaleRateError("Exchange rates are stale. Please retry shortly.")
        pairs = await self._repo.get_active_currency_pairs()
        active_pair = next(
            (pair for pair in pairs if pair.from_currency == from_currency and pair.to_currency == to_currency),
            None,
        )
        if active_pair is None:
            raise UnsupportedCurrencyPairError(f"Currency pair {from_currency}/{to_currency} is not supported.")
        rate_str = snapshot.rates.get(from_currency, {}).get(to_currency)
        if rate_str is None:
            raise UnsupportedCurrencyPairError(f"No rate for {from_currency}/{to_currency} in snapshot.")
        rate = Decimal(str(rate_str))
        sending_fee = (amount * self._settings.SENDING_FEE_PCT).quantize(QUANT, rounding=ROUND_HALF_UP)
        gross = (amount * rate).quantize(QUANT, rounding=ROUND_HALF_UP)
        receiving_fee = (gross * self._settings.RECEIVING_FEE_PCT).quantize(QUANT, rounding=ROUND_HALF_UP)
        net_amount = (gross - receiving_fee).quantize(QUANT, rounding=ROUND_HALF_UP)
        total_sender_cost = (amount + sending_fee).quantize(QUANT, rounding=ROUND_HALF_UP)
        return ConversionPreviewResponse(
            input_amount=amount,
            from_currency=from_currency,
            exchange_rate=rate,
            gross_converted_amount=gross,
            estimated_sending_fee=sending_fee,
            estimated_receiving_fee=receiving_fee,
            estimated_net_amount=net_amount,
            total_sender_cost=total_sender_cost,
            snapshot_id=snapshot.id,
            effective_at=snapshot.effective_at,
            is_stale=snapshot.is_stale,
        )
