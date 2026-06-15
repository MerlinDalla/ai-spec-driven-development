"""Transfers and idempotency_keys tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-15 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), unique=True, nullable=False),
        sa.Column("source_account_number", sa.String(34), nullable=False),
        sa.Column("destination_account_number", sa.String(34), nullable=False),
        sa.Column("source_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("source_currency", sa.CHAR(3), nullable=False),
        sa.Column("destination_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("destination_currency", sa.CHAR(3), nullable=False),
        sa.Column("exchange_rate", sa.Numeric(20, 8), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("caller_id", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("transfers_idempotency_key_idx", "transfers", ["idempotency_key"], unique=True)
    op.create_index("transfers_source_account_idx", "transfers", ["source_account_number"])
    op.create_index("transfers_destination_account_idx", "transfers", ["destination_account_number"])
    op.create_index("transfers_created_at_idx", "transfers", ["created_at"])

    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("owner_id", sa.Text, nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_body", postgresql.JSONB, nullable=True),
        sa.Column("response_status", sa.SmallInteger, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idempotency_keys_expires_at_idx", "idempotency_keys", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("transfers")
