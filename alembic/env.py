import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from fund_transfer.core.database import Base
from fund_transfer.models.account import Account  # noqa: F401
from fund_transfer.models.audit_log import AuditLogEntry  # noqa: F401
from fund_transfer.models.currency_pair import CurrencyPair  # noqa: F401
from fund_transfer.models.fx_rate_snapshot import FxRateSnapshot  # noqa: F401
from fund_transfer.models.notification import Notification  # noqa: F401
from fund_transfer.models.transfer import Transfer  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
