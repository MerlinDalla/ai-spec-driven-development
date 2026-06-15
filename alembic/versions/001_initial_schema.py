"""Initial schema: accounts and audit_log tables

Revision ID: 001
Revises:
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_number", sa.String(34), unique=True, nullable=False),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("balance", sa.Numeric(19, 4), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("owner_pii_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("accounts_account_number_idx", "accounts", ["account_number"], unique=True)
    op.create_index("accounts_owner_id_idx", "accounts", ["owner_id"])
    op.create_index("accounts_status_idx", "accounts", ["status"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_type", sa.String(30), nullable=False),
        sa.Column("actor_identity", sa.Text, nullable=False),
        sa.Column("affected_account_numbers", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=True),
        sa.Column("currency", sa.CHAR(3), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("detail", postgresql.JSONB, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("request_id", sa.Text, nullable=True),
    )
    op.create_index("audit_log_actor_identity_idx", "audit_log", ["actor_identity"])
    op.create_index("audit_log_affected_accounts_idx", "audit_log", ["affected_account_numbers"], postgresql_using="gin")
    op.create_index("audit_log_timestamp_idx", "audit_log", ["timestamp"])
    op.create_index("audit_log_operation_type_idx", "audit_log", ["operation_type"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("accounts")
