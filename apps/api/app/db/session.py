"""
app/db/session.py
-----------------
Re-exports the session factory and `get_db` dependency from the canonical
`app.core.database` module.

This shim preserves backwards-compatibility for any existing imports of
`app.db.session.get_db` or `app.db.session.AsyncSessionLocal` while keeping
the single source of truth in `app.core.database`.
"""

from app.core.database import AsyncSessionLocal, get_db

__all__ = ["AsyncSessionLocal", "get_db"]
