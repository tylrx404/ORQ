"""
app/db/registry.py
------------------
Model registry — the single place that imports every ORM model.

Purpose
-------
SQLAlchemy's mapper registry and Alembic's autogenerate only know about
a table if the mapped class has been imported *before* ``Base.metadata``
is inspected.  Importing models directly in ``app/db/base.py`` causes
circular imports (model → base → model).

The solution is this intermediary module:

  app/db/base.py      defines Base (no model imports)
  app/models/user.py  defines User(Base)  (imports base, not registry)
  app/db/registry.py  imports Base + all models  ← Alembic and app use this

Alembic's env.py imports ``registry`` (which populates Base.metadata)
and then reads ``Base.metadata`` for autogenerate.

Adding a new model
------------------
1. Create ``app/models/<name>.py`` that inherits from ``Base``.
2. Add the import to this file, keeping the list alphabetically sorted.
"""

# ruff: noqa: F401  (imports are intentional side-effects)
from app.db.base import Base  # noqa: F401
from app.models.agent_spec import AgentSpec, AgentSpecVersion  # noqa: F401
from app.models.api_key import ApiKey  # noqa: F401
from app.models.execution_log import ExecutionLog  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.organization_invitation import OrganizationInvitation  # noqa: F401
from app.models.organization_membership import OrganizationMembership  # noqa: F401
from app.models.organization_quota import OrganizationQuota  # noqa: F401
from app.models.prompt import Prompt, PromptVersion  # noqa: F401
from app.models.provider import Provider  # noqa: F401
from app.models.provider_model import ProviderModel  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "AgentSpec",
    "AgentSpecVersion",
    "ApiKey",
    "Base",
    "ExecutionLog",
    "Organization",
    "OrganizationInvitation",
    "OrganizationMembership",
    "OrganizationQuota",
    "Prompt",
    "PromptVersion",
    "Provider",
    "ProviderModel",
    "User",
]
