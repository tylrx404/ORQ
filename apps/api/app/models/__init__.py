"""
app/models/__init__.py
-----------------------
ORM model package.

Import every model module here so that SQLAlchemy's mapper registry
and Alembic's autogenerate both see all mapped classes, regardless of
which entry-point is used to start the application.
"""

from app.models.user import User
from app.models.organization import Organization

__all__ = ["User", "Organization"]
