from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class CreateTransferRequest(BaseModel):
    source_account_number: Annotated[str, Field(min_length=1)]
    destination_account_number: Annotated[str, Field(min_length=1)]
    amount: Decimal

    @model_validator(mode="after")
    def validate_not_self_transfer(self) -> "CreateTransferRequest":
        if self.source_account_number == self.destination_account_number:
            raise ValueError("Source and destination accounts must be different.")
        return self

    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Transfer amount must be greater than zero.")
        return v


class TransferResponse(BaseModel):
    transfer_id: str
    source_account_number: str
    destination_account_number: str
    source_amount: str
    source_currency: str
    destination_amount: str
    destination_currency: str
    exchange_rate: str
    status: str
    rejection_reason: str | None = None
    created_at: str

    @classmethod
    def from_orm_transfer(cls, transfer) -> "TransferResponse":
        return cls(
            transfer_id=str(transfer.id),
            source_account_number=transfer.source_account_number,
            destination_account_number=transfer.destination_account_number,
            source_amount=f"{transfer.source_amount:.4f}",
            source_currency=transfer.source_currency,
            destination_amount=f"{transfer.destination_amount:.4f}",
            destination_currency=transfer.destination_currency,
            exchange_rate=f"{transfer.exchange_rate:.8f}",
            status=transfer.status,
            rejection_reason=transfer.rejection_reason,
            created_at=transfer.created_at.isoformat() if transfer.created_at else "",
        )
