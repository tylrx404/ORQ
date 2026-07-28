"""
alembic/env.py
--------------
Alembic migration environment.

Reads the database URL from the application settings (via environment
variables / .env file) rather than from alembic.ini, so that credentials
are never stored in source control.

Supports both:
  - Offline mode  (generates SQL without a live database connection)
  - Online mode   (connects to PostgreSQL and runs migrations directly)
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so `from app.xxx` works when Alembic
# is invoked from the apps/api directory.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Import application objects AFTER adjusting sys.path.
# ---------------------------------------------------------------------------
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic Config object (gives access to alembic.ini values).
# ---------------------------------------------------------------------------
config = context.config

# Override the sqlalchemy.url with the value from application settings so
# the .env / environment variables are always the source of truth.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up logging as configured in alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide the metadata for autogenerate support.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations without a live database connection.

    Emits SQL to stdout / a file instead of executing it directly.
    Useful for dry-run reviews or when the database is unreachable.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (async)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside a sync callback."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
