from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_organization_membership_service,
    require_admin,
    require_member,
    require_owner,
)
from app.schemas.organization_membership import (
    MembershipCreateRequest,
    MembershipResponse,
    MembershipUpdateRequest,
)
from app.services.organization_membership import (
    MembershipAlreadyExistsError,
    MembershipNotFoundError,
    OrganizationMembershipService,
)

router = APIRouter()


@router.post(
    "",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to an organization",
    dependencies=[Depends(require_admin)],
)
async def add_member(
    organization_id: UUID,
    request: MembershipCreateRequest,
    service: OrganizationMembershipService = Depends(get_organization_membership_service),
) -> MembershipResponse:
    try:
        membership = await service.add_member(
            organization_id=organization_id,
            user_id=request.user_id,
            role=request.role,
        )
        return MembershipResponse.model_validate(membership)
    except MembershipAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.get(
    "",
    response_model=List[MembershipResponse],
    summary="List organization members",
    dependencies=[Depends(require_member)],
)
async def list_members(
    organization_id: UUID,
    skip: int = 0,
    limit: int = 100,
    service: OrganizationMembershipService = Depends(get_organization_membership_service),
) -> List[MembershipResponse]:
    memberships = await service.list_members(
        organization_id=organization_id, skip=skip, limit=limit
    )
    return [MembershipResponse.model_validate(m) for m in memberships]


@router.patch(
    "/{user_id}",
    response_model=MembershipResponse,
    summary="Update a member's role",
    dependencies=[Depends(require_owner)],
)
async def update_role(
    organization_id: UUID,
    user_id: UUID,
    request: MembershipUpdateRequest,
    service: OrganizationMembershipService = Depends(get_organization_membership_service),
) -> MembershipResponse:
    try:
        membership = await service.update_role(
            organization_id=organization_id,
            user_id=user_id,
            role=request.role,
        )
        return MembershipResponse.model_validate(membership)
    except MembershipNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from an organization",
    dependencies=[Depends(require_admin)],
)
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    service: OrganizationMembershipService = Depends(get_organization_membership_service),
):
    try:
        await service.remove_member(
            organization_id=organization_id, user_id=user_id
        )
    except MembershipNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
