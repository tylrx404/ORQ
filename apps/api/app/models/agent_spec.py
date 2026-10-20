"""
app/models/agent_spec.py
------------------------
AgentSpec and AgentSpecVersion ORM models for the Agent Registry.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, inspect, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentSpec(Base):
    """Relational mapping for the ``agent_specs`` table."""

    __tablename__ = "agent_specs"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_agent_specs_organization_id_name"),
        Index("ix_agent_specs_organization_id", "organization_id"),
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

    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "agent_spec_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_agent_specs_current_version_id",
        ),
        nullable=True,
        default=None,
    )

    prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    tool_identifiers: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    memory_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    current_version: Mapped[Optional["AgentSpecVersion"]] = relationship(
        "AgentSpecVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )

    versions: Mapped[list["AgentSpecVersion"]] = relationship(
        "AgentSpecVersion",
        back_populates="agent_spec",
        foreign_keys="AgentSpecVersion.agent_spec_id",
        cascade="all, delete-orphan",
    )

    @property
    def current_version_number(self) -> int | None:
        if self.current_version_id is None:
            return None
        try:
            state = inspect(self)
            if state is not None and "current_version" in state.dict:
                cv = state.dict["current_version"]
                if cv is not None and getattr(cv, "id", None) == self.current_version_id:
                    return getattr(cv, "version_number", None)
        except Exception:
            pass

        cached = getattr(self, "_cached_version_info", None)
        if cached is not None and cached[0] == self.current_version_id:
            return cached[1]
        return None

    @current_version_number.setter
    def current_version_number(self, value: int | None) -> None:
        if value is None or self.current_version_id is None:
            self._cached_version_info = None
        else:
            self._cached_version_info = (self.current_version_id, value)

    def __repr__(self) -> str:
        return f"<AgentSpec id={self.id} org={self.organization_id} name={self.name}>"


class AgentSpecVersion(Base):
    """Relational mapping for the ``agent_spec_versions`` table."""

    __tablename__ = "agent_spec_versions"
    __table_args__ = (
        UniqueConstraint(
            "agent_spec_id", "version_number", name="uq_agent_spec_versions_agent_spec_id_version_number"
        ),
        Index("ix_agent_spec_versions_agent_spec_id", "agent_spec_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    agent_spec_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_specs.id", ondelete="CASCADE"),
        nullable=False,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_versions.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("providers.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )

    tool_identifiers: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    memory_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    agent_spec: Mapped["AgentSpec"] = relationship(
        "AgentSpec",
        back_populates="versions",
        foreign_keys=[agent_spec_id],
    )

    def __repr__(self) -> str:
        return f"<AgentSpecVersion id={self.id} agent_spec_id={self.agent_spec_id} v={self.version_number}>"
