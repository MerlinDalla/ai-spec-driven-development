from __future__ import annotations

import enum
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class AccountStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class CreateAccountRequest(BaseModel):
    owner_id: Annotated[str, Field(min_length=1, max_length=255)]
    currency: Annotated[str, Field(min_length=3, max_length=3)]
    opening_balance: Decimal

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return v.upper()

    @field_validator("opening_balance")
    @classmethod
    def validate_opening_balance(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Opening balance must be greater than or equal to zero.")
        if v != v.quantize(Decimal("0.0001")):
            raise ValueError("Opening balance must have at most 4 decimal places.")
        return v


class AccountResponse(BaseModel):
    account_number: str
    owner_id: str
    currency: str
    balance: str
    status: str
    created_at: str
    updated_at: str | None = None

    @classmethod
    def from_orm_account(cls, account) -> "AccountResponse":
        return cls(
            account_number=account.account_number,
            owner_id=account.owner_id,
            currency=account.currency,
            balance=f"{account.balance:.4f}",
            status=account.status,
            created_at=account.created_at.isoformat() if account.created_at else "",
            updated_at=account.updated_at.isoformat() if account.updated_at else None,
        )
