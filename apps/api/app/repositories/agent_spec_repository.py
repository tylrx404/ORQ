from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_spec import AgentSpec


class AgentSpecRepository:
    """Repository for AgentSpec entity database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, agent_id: UUID) -> AgentSpec | None:
        """Fetch an agent spec by ID."""
        result = await self.db.execute(
            select(AgentSpec).where(AgentSpec.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self, organization_id: UUID, agent_id: UUID
    ) -> AgentSpec | None:
        """Fetch an agent spec by ID scoped to an organization."""
        result = await self.db.execute(
            select(AgentSpec).where(
                AgentSpec.id == agent_id,
                AgentSpec.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_org(
        self, organization_id: UUID, name: str
    ) -> AgentSpec | None:
        """Fetch an agent spec by unique name within an organization."""
        result = await self.db.execute(
            select(AgentSpec).where(
                AgentSpec.organization_id == organization_id,
                AgentSpec.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> Sequence[AgentSpec]:
        """List all agent specs for an organization ordered by creation time."""
        query = select(AgentSpec).where(AgentSpec.organization_id == organization_id)
        if is_active is not None:
            query = query.where(AgentSpec.is_active == is_active)
        query = query.order_by(AgentSpec.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, agent_spec: AgentSpec) -> AgentSpec:
        """Persist a new agent spec."""
        self.db.add(agent_spec)
        await self.db.commit()
        await self.db.refresh(agent_spec)
        return agent_spec

    async def update(self, agent_spec: AgentSpec) -> AgentSpec:
        """Persist updates to an existing agent spec."""
        await self.db.commit()
        await self.db.refresh(agent_spec)
        return agent_spec

    async def delete(self, agent_spec: AgentSpec) -> None:
        """Delete an agent spec."""
        await self.db.delete(agent_spec)
        await self.db.commit()
