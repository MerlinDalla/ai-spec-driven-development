"""Cross-currency transfer schema

Revision ID: 003
Revises: 002
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_rate_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("provider_source", sa.String(100), nullable=False),
        sa.Column("rates", postgresql.JSONB, nullable=False),
    )
    op.create_index("idx_fx_rate_snapshot_effective_at", "fx_rate_snapshot", ["effective_at"])
    op.create_index("idx_fx_rate_snapshot_is_stale", "fx_rate_snapshot", ["is_stale"])

    op.create_table(
        "currency_pairs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("from_currency", sa.CHAR(3), nullable=False),
        sa.Column("to_currency", sa.CHAR(3), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("from_currency", "to_currency", name="uq_currency_pairs_direction"),
    )
    op.create_index("idx_currency_pair_active", "currency_pairs", ["is_active"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recipient_account_number", sa.String(34), nullable=False),
        sa.Column("transfer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transfers.id"), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("source_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("source_currency", sa.CHAR(3), nullable=False),
        sa.Column("net_credited_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("net_credited_currency", sa.CHAR(3), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_notifications_recipient_read", "notifications", ["recipient_account_number", "read_at"])
    op.create_index("idx_notifications_transfer_id", "notifications", ["transfer_id"])

    op.add_column("transfers", sa.Column("transfer_type", sa.String(30), nullable=True))
    op.add_column("transfers", sa.Column("sending_fee", sa.Numeric(19, 4), nullable=True))
    op.add_column("transfers", sa.Column("sending_fee_currency", sa.CHAR(3), nullable=True))
    op.add_column("transfers", sa.Column("receiving_fee", sa.Numeric(19, 4), nullable=True))
    op.add_column("transfers", sa.Column("receiving_fee_currency", sa.CHAR(3), nullable=True))
    op.add_column("transfers", sa.Column("fx_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("transfers", sa.Column("rate_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("transfers", sa.Column("source_amount_usd", sa.Numeric(19, 4), nullable=True))
    op.alter_column("transfers", "rejection_reason", new_column_name="failure_reason")


def downgrade() -> None:
    op.alter_column("transfers", "failure_reason", new_column_name="rejection_reason")
    op.drop_column("transfers", "source_amount_usd")
    op.drop_column("transfers", "rate_confirmed_at")
    op.drop_column("transfers", "fx_snapshot_id")
    op.drop_column("transfers", "receiving_fee_currency")
    op.drop_column("transfers", "receiving_fee")
    op.drop_column("transfers", "sending_fee_currency")
    op.drop_column("transfers", "sending_fee")
    op.drop_column("transfers", "transfer_type")
    op.drop_table("notifications")
    op.drop_table("currency_pairs")
    op.drop_table("fx_rate_snapshot")
