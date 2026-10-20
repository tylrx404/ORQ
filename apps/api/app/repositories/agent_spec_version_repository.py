from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_spec import AgentSpecVersion


class AgentSpecVersionRepository:
    """Repository for immutable AgentSpecVersion entity database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, version_id: UUID) -> AgentSpecVersion | None:
        """Fetch an agent spec version by ID."""
        result = await self.db.execute(
            select(AgentSpecVersion).where(AgentSpecVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent_and_id(
        self, agent_spec_id: UUID, version_id: UUID
    ) -> AgentSpecVersion | None:
        """Fetch a version scoped to an agent spec ID."""
        result = await self.db.execute(
            select(AgentSpecVersion).where(
                AgentSpecVersion.id == version_id,
                AgentSpecVersion.agent_spec_id == agent_spec_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version_number(self, agent_spec_id: UUID) -> int:
        """Get the current maximum version number for an agent spec."""
        result = await self.db.execute(
            select(func.coalesce(func.max(AgentSpecVersion.version_number), 0)).where(
                AgentSpecVersion.agent_spec_id == agent_spec_id
            )
        )
        return result.scalar() or 0

    async def list_by_agent(
        self, agent_spec_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[AgentSpecVersion]:
        """List all versions for an agent spec ordered by version number descending."""
        result = await self.db.execute(
            select(AgentSpecVersion)
            .where(AgentSpecVersion.agent_spec_id == agent_spec_id)
            .order_by(AgentSpecVersion.version_number.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, version: AgentSpecVersion) -> AgentSpecVersion:
        """Persist an immutable agent spec version without committing the transaction."""
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version
