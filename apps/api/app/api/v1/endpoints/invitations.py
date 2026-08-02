from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_organization_invitation_service
from app.models.user import User
from app.schemas.organization_invitation import OrganizationInvitationResponse
from app.services.organization_invitation import (
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationInvalidStatusError,
    InvitationNotFoundError,
    OrganizationInvitationService,
)

router = APIRouter()


@router.post(
    "/{token}/accept",
    response_model=OrganizationInvitationResponse,
    summary="Accept an organization invitation",
)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    service: OrganizationInvitationService = Depends(get_organization_invitation_service),
) -> OrganizationInvitationResponse:
    try:
        invitation = await service.accept_invitation(
            token=token,
            user_id=current_user.id,
        )
        return OrganizationInvitationResponse.model_validate(invitation)
    except InvitationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except (
        InvitationExpiredError,
        InvitationAlreadyAcceptedError,
        InvitationInvalidStatusError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
