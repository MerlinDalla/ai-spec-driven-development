from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from fund_transfer.core.database import Base


class AccountStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("account_number", name="uq_accounts_account_number"),
        Index("accounts_owner_id_idx", "owner_id"),
        Index("accounts_status_idx", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_number: Mapped[str] = mapped_column(String(34), unique=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AccountStatus.active.value)
    owner_pii_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
