from typing import Sequence
from uuid import UUID

from app.models.organization_membership import MembershipRole, OrganizationMembership
from app.repositories.organization_membership_repository import (
    OrganizationMembershipRepository,
)


class MembershipException(Exception):
    pass


class MembershipAlreadyExistsError(MembershipException):
    pass


class MembershipNotFoundError(MembershipException):
    pass


class OrganizationMembershipService:
    def __init__(self, membership_repository: OrganizationMembershipRepository):
        self._membership_repo = membership_repository

    async def add_member(
        self, organization_id: UUID, user_id: UUID, role: MembershipRole
    ) -> OrganizationMembership:
        existing = await self._membership_repo.get_membership(organization_id, user_id)
        if existing:
            raise MembershipAlreadyExistsError(
                "Membership already exists."
            )

        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        return await self._membership_repo.create(membership)

    async def update_role(
        self, organization_id: UUID, user_id: UUID, role: MembershipRole
    ) -> OrganizationMembership:
        membership = await self._membership_repo.get_membership(organization_id, user_id)
        if not membership:
            raise MembershipNotFoundError(
                "Membership not found."
            )

        membership.role = role
        return await self._membership_repo.update(membership)

    async def remove_member(self, organization_id: UUID, user_id: UUID) -> OrganizationMembership:
        membership = await self._membership_repo.get_membership(organization_id, user_id)
        if not membership:
            raise MembershipNotFoundError(
                "Membership not found."
            )

        await self._membership_repo.delete(membership)

    async def list_members(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[OrganizationMembership]:
        return await self._membership_repo.list_members(
            organization_id, skip=skip, limit=limit
        )
