from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization_invitation import InvitationStatus, OrganizationInvitation


class OrganizationInvitationRepository:
    """Repository for organization invitation database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, invitation_id: UUID) -> OrganizationInvitation | None:
        """Fetch an invitation by ID."""
        result = await self.db.execute(
            select(OrganizationInvitation).where(OrganizationInvitation.id == invitation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> OrganizationInvitation | None:
        """Fetch an invitation by its token."""
        result = await self.db.execute(
            select(OrganizationInvitation).where(OrganizationInvitation.token == token)
        )
        return result.scalar_one_or_none()

    async def get_pending_by_email_and_org(
        self, organization_id: UUID, email: str
    ) -> OrganizationInvitation | None:
        """Fetch a pending invitation for a specific email in an organization."""
        result = await self.db.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == email,
                OrganizationInvitation.status == InvitationStatus.pending,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[OrganizationInvitation]:
        """List all invitations for an organization."""
        result = await self.db.execute(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(
        self, invitation: OrganizationInvitation
    ) -> OrganizationInvitation:
        """Create a new invitation."""
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def update(
        self, invitation: OrganizationInvitation
    ) -> OrganizationInvitation:
        """Update an existing invitation."""
        await self.db.commit()
        await self.db.refresh(invitation)
        return invitation

    async def delete(self, invitation: OrganizationInvitation) -> None:
        """Delete an invitation."""
        await self.db.delete(invitation)
        await self.db.commit()
