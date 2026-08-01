from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_membership import OrganizationMembership


class OrganizationMembershipRepository:
    """Repository for organization membership database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_membership(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership | None:
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[OrganizationMembership]:
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(
        self, membership: OrganizationMembership
    ) -> OrganizationMembership:
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def update(
        self, membership: OrganizationMembership
    ) -> OrganizationMembership:
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def delete(
        self,
        membership: OrganizationMembership,
        ) -> OrganizationMembership:
            await self.db.delete(membership)
            await self.db.commit()
            return membership
