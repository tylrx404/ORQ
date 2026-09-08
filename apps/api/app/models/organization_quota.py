"""
app/models/organization_quota.py
---------------------------------
OrganizationQuota ORM model.

Tracks per-organization usage quota limits and current cycle counters.
One-to-one with Organization (enforced via UNIQUE constraint on organization_id).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganizationQuota(Base):
    """Relational mapping for the ``organization_quotas`` table.

    Columns
    -------
    id              : UUID primary key.
    organization_id : FK to organizations (UNIQUE – one quota per org).
    request_limit   : Maximum API requests allowed per billing cycle. NULL = unlimited.
    token_limit     : Maximum tokens (prompt + completion) per billing cycle. NULL = unlimited.
    requests_used   : Cumulative requests consumed in the current cycle.
    tokens_used     : Cumulative tokens consumed in the current cycle.
    reset_at        : Timestamp when the current cycle ends and counters reset.
    created_at      : Row creation timestamp (UTC).
    updated_at      : Last modification timestamp (UTC).
    """

    __tablename__ = "organization_quotas"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationship
    # ------------------------------------------------------------------
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Limits — NULL means unlimited
    # ------------------------------------------------------------------
    request_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
    )

    token_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        default=None,
    )

    # ------------------------------------------------------------------
    # Running counters for the current billing cycle
    # ------------------------------------------------------------------
    requests_used: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    tokens_used: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    # ------------------------------------------------------------------
    # Billing cycle end — when to reset counters
    # ------------------------------------------------------------------
    reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<OrganizationQuota org={self.organization_id} "
            f"req={self.requests_used}/{self.request_limit} "
            f"tok={self.tokens_used}/{self.token_limit} "
            f"reset={self.reset_at}>"
        )
