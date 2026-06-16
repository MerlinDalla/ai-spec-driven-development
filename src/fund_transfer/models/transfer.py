from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, DateTime, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from fund_transfer.core.database import Base


class TransferStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    rejected = "rejected"


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_transfers_idempotency_key"),
        Index("transfers_source_account_idx", "source_account_number"),
        Index("transfers_destination_account_idx", "destination_account_number"),
        Index("transfers_created_at_idx", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_account_number: Mapped[str] = mapped_column(String(34), nullable=False)
    destination_account_number: Mapped[str] = mapped_column(String(34), nullable=False)
    source_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=False)
    source_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    destination_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=False)
    destination_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(20, 8, asdecimal=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sending_fee: Mapped[Decimal | None] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=True)
    sending_fee_currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    receiving_fee: Mapped[Decimal | None] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=True)
    receiving_fee_currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    fx_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rate_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_amount_usd: Mapped[Decimal | None] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=True)
    caller_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def rejection_reason(self) -> str | None:
        return self.failure_reason

    @rejection_reason.setter
    def rejection_reason(self, value: str | None) -> None:
        self.failure_reason = value
