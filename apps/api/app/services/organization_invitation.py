import secrets
from datetime import datetime, timedelta, timezone
from typing import Sequence
from uuid import UUID

from app.models.organization_invitation import InvitationStatus, OrganizationInvitation
from app.models.organization_membership import MembershipRole
from app.repositories.organization_invitation_repository import OrganizationInvitationRepository
from app.services.organization_membership import OrganizationMembershipService


class InvitationException(Exception):
    pass


class DuplicateInvitationError(InvitationException):
    pass


class InvitationNotFoundError(InvitationException):
    pass


class InvitationExpiredError(InvitationException):
    pass


class InvitationAlreadyAcceptedError(InvitationException):
    pass


class InvitationInvalidStatusError(InvitationException):
    pass


class OrganizationInvitationService:
    def __init__(
        self,
        invitation_repository: OrganizationInvitationRepository,
        membership_service: OrganizationMembershipService,
    ):
        self._invitation_repo = invitation_repository
        self._membership_service = membership_service

    async def create_invitation(
        self,
        organization_id: UUID,
        email: str,
        role: MembershipRole,
        created_by: UUID,
    ) -> OrganizationInvitation:
        # Check if there is already a pending invitation for this email
        existing = await self._invitation_repo.get_pending_by_email_and_org(
            organization_id, email
        )
        if existing:
            raise DuplicateInvitationError(
                f"A pending invitation already exists for {email} in this organization."
            )

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = OrganizationInvitation(
            organization_id=organization_id,
            email=email,
            role=role,
            token=token,
            status=InvitationStatus.pending,
            created_by=created_by,
            expires_at=expires_at,
        )
        return await self._invitation_repo.create(invitation)

    async def accept_invitation(
        self,
        token: str,
        user_id: UUID,
    ) -> OrganizationInvitation:
        invitation = await self._invitation_repo.get_by_token(token)
        if not invitation:
            raise InvitationNotFoundError("Invitation token is invalid or does not exist.")

        if invitation.status == InvitationStatus.accepted:
            raise InvitationAlreadyAcceptedError("This invitation has already been accepted.")
            
        if invitation.status == InvitationStatus.revoked:
            raise InvitationInvalidStatusError("This invitation has been revoked.")

        if invitation.status == InvitationStatus.expired or invitation.expires_at < datetime.now(timezone.utc):
            if invitation.status != InvitationStatus.expired:
                invitation.status = InvitationStatus.expired
                await self._invitation_repo.update(invitation)
            raise InvitationExpiredError("This invitation has expired.")

        # Create the organization membership
        await self._membership_service.add_member(
            organization_id=invitation.organization_id,
            user_id=user_id,
            role=invitation.role,
        )

        invitation.status = InvitationStatus.accepted
        invitation.accepted_at = datetime.now(timezone.utc)
        return await self._invitation_repo.update(invitation)

    async def revoke_invitation(
        self,
        invitation_id: UUID,
    ) -> OrganizationInvitation:
        invitation = await self._invitation_repo.get_by_id(invitation_id)
        if not invitation:
            raise InvitationNotFoundError("Invitation not found.")

        if invitation.status != InvitationStatus.pending:
            raise InvitationInvalidStatusError(f"Cannot revoke invitation with status {invitation.status.value}")

        invitation.status = InvitationStatus.revoked
        return await self._invitation_repo.update(invitation)

    async def list_invitations(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[OrganizationInvitation]:
        return await self._invitation_repo.list_by_organization(
            organization_id=organization_id, skip=skip, limit=limit
        )

    async def delete_invitation(
        self,
        invitation_id: UUID,
    ) -> None:
        invitation = await self._invitation_repo.get_by_id(invitation_id)
        if not invitation:
            raise InvitationNotFoundError("Invitation not found.")
        await self._invitation_repo.delete(invitation)
