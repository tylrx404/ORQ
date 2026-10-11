"""
app/models/prompt.py
--------------------
Prompt and PromptVersion ORM models for the Prompt Registry.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Prompt(Base):
    """Relational mapping for the ``prompts`` table."""

    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_prompts_organization_id_name"),
        Index("ix_prompts_organization_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    published_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "prompt_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_prompts_published_version_id",
        ),
        nullable=True,
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Prompt id={self.id} name={self.name}>"


class PromptVersion(Base):
    """Relational mapping for the ``prompt_versions`` table."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "prompt_id", "version_number", name="uq_prompt_versions_prompt_id_version_number"
        ),
        Index("ix_prompt_versions_prompt_id", "prompt_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        nullable=False,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<PromptVersion id={self.id} prompt_id={self.prompt_id} v={self.version_number}>"
