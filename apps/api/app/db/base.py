"""
app/db/base.py
--------------
Central import point for SQLAlchemy's DeclarativeBase.

All ORM models must:
  1. Import `Base` from this module.
  2. Be imported here (or in a submodule imported here) so that
     `Base.metadata` contains every table when Alembic autogenerates
     migrations.

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
    ``Base.metadata`` from here to discover tables for autogeneration.
    """
