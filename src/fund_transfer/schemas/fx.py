from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ExchangeRateSchema(BaseModel):
    from_currency: str
    to_currency: str
    rate: Decimal


class RateTableResponse(BaseModel):
    snapshot_id: uuid.UUID
    effective_at: datetime
    is_stale: bool
    rates: list[ExchangeRateSchema]


class ConversionPreviewRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: Decimal


class ConversionPreviewResponse(BaseModel):
    input_amount: Decimal
    from_currency: str
    exchange_rate: Decimal
    gross_converted_amount: Decimal
    estimated_sending_fee: Decimal
    estimated_receiving_fee: Decimal
    estimated_net_amount: Decimal
    total_sender_cost: Decimal
    snapshot_id: uuid.UUID
    effective_at: datetime
    is_stale: bool


class CrossCurrencyTransferRequest(BaseModel):
    source_account_number: str
    destination_account_number: str
    source_amount: Decimal
    source_currency: str
    destination_currency: str
    fx_snapshot_id: uuid.UUID


class CrossCurrencyTransferResponse(BaseModel):
    id: uuid.UUID
    status: str
    source_amount: Decimal
    source_currency: str
    sending_fee: Decimal
    gross_converted_amount: Decimal
    receiving_fee: Decimal
    net_credited_amount: Decimal
    destination_currency: str
    exchange_rate: Decimal
    failure_reason: str | None = None
    fx_snapshot_id: uuid.UUID | None = None
    created_at: datetime
