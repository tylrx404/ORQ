"""
app/core/database.py
--------------------
Single-responsibility module for async SQLAlchemy engine and session factory.

Provides:
  - `engine`              — The application-level AsyncEngine.
  - `AsyncSessionLocal`   — Configured async session factory.
  - `get_db`              — FastAPI dependency that yields an AsyncSession.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# pool_pre_ping=True: validates connections before checkout (handles stale
#   connections after a database restart).
# pool_size / max_overflow: sized for a modest production workload; tune via
#   env vars in future phases.
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield an AsyncSession and guarantee it is closed on exit."""
    async with AsyncSessionLocal() as session:
        yield session
