"""
app/db/base.py
--------------
Central import point for SQLAlchemy's DeclarativeBase.

Convention
----------
All ORM models must:
  1. Inherit from ``Base`` defined here.
  2. Be imported in ``app/db/registry.py`` (NOT here) so that
     ``Base.metadata`` contains every table when Alembic autogenerates
     migrations, without causing circular imports.

Usage in models:
    from app.db.base import Base

    class MyModel(Base):
        __tablename__ = "my_table"
        ...
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Application-wide declarative base.

    All ORM models inherit from this class.  Alembic's env.py imports
    ``Base.metadata`` from here after first importing ``app.db.registry``
    to ensure all mapped classes are registered.
    """
