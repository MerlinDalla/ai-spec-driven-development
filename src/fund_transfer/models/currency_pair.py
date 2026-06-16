from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CHAR, DateTime, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from fund_transfer.core.database import Base


class CurrencyPair(Base):
    __tablename__ = "currency_pairs"
    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency", name="uq_currency_pairs_direction"),
        Index("idx_currency_pair_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
