from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from fund_transfer.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_recipient_read", "recipient_account_number", "read_at"),
        Index("idx_notifications_transfer_id", "transfer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_account_number: Mapped[str] = mapped_column(String(34), nullable=False)
    transfer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("transfers.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    source_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=False)
    source_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    net_credited_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=False)
    net_credited_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
