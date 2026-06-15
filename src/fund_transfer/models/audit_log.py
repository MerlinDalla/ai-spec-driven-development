from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, DateTime, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from fund_transfer.core.database import Base


class OperationType(str, enum.Enum):
    account_created = "account_created"
    account_deleted = "account_deleted"
    transfer_completed = "transfer_completed"
    transfer_rejected = "transfer_rejected"


class AuditLogEntry(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("audit_log_actor_identity_idx", "actor_identity"),
        Index("audit_log_timestamp_idx", "timestamp"),
        Index("audit_log_operation_type_idx", "operation_type"),
        # GIN index on affected_account_numbers created in migration
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_identity: Mapped[str] = mapped_column(Text, nullable=False)
    affected_account_numbers: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4, asdecimal=True), nullable=True)
    currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
