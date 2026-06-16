from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from fund_transfer.core.database import Base


class FxRateSnapshot(Base):
    __tablename__ = "fx_rate_snapshot"
    __table_args__ = (
        Index("idx_fx_rate_snapshot_effective_at", "effective_at"),
        Index("idx_fx_rate_snapshot_is_stale", "is_stale"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    provider_source: Mapped[str] = mapped_column(String(100), nullable=False)
    rates: Mapped[dict] = mapped_column(JSONB, nullable=False)
