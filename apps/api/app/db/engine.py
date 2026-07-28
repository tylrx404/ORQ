"""
app/db/engine.py
----------------
Re-exports the async engine from the canonical `app.core.database` module.

This shim preserves backwards-compatibility for any existing imports of
`app.db.engine.engine` or `app.db.engine.AsyncSessionLocal` while keeping
the single source of truth in `app.core.database`.
"""

from app.core.database import AsyncSessionLocal, engine

__all__ = ["engine", "AsyncSessionLocal"]
