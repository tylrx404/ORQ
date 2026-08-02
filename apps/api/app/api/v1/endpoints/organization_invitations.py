from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_current_user,
    get_organization_invitation_service,
    require_admin,
)
from app.models.user import User
from app.schemas.organization_invitation import (
    OrganizationInvitationCreateRequest,
    OrganizationInvitationResponse,
)
from app.services.organization_invitation import (
    DuplicateInvitationError,
    InvitationInvalidStatusError,
    InvitationNotFoundError,
    OrganizationInvitationService,
)

router = APIRouter()


@router.post(
    "",
    response_model=OrganizationInvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization invitation",
    dependencies=[Depends(require_admin)],
)
async def create_invitation(
    organization_id: UUID,
    request: OrganizationInvitationCreateRequest,
    current_user: User = Depends(get_current_user),
    service: OrganizationInvitationService = Depends(get_organization_invitation_service),
) -> OrganizationInvitationResponse:
    try:
        invitation = await service.create_invitation(
            organization_id=organization_id,
            email=request.email,
            role=request.role,
            created_by=current_user.id,
        )
        return OrganizationInvitationResponse.model_validate(invitation)
    except DuplicateInvitationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.get(
    "",
    response_model=List[OrganizationInvitationResponse],
    summary="List organization invitations",
    dependencies=[Depends(require_admin)],
)
async def list_invitations(
    organization_id: UUID,
    skip: int = 0,
    limit: int = 100,
    service: OrganizationInvitationService = Depends(get_organization_invitation_service),
) -> List[OrganizationInvitationResponse]:
    invitations = await service.list_invitations(
        organization_id=organization_id, skip=skip, limit=limit
    )
    return [OrganizationInvitationResponse.model_validate(inv) for inv in invitations]


@router.delete(
    "/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an organization invitation",
    dependencies=[Depends(require_admin)],
)
async def revoke_invitation(
    organization_id: UUID,
    invitation_id: UUID,
    service: OrganizationInvitationService = Depends(get_organization_invitation_service),
):
    try:
        await service.revoke_invitation(invitation_id=invitation_id)
    except InvitationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except InvitationInvalidStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
