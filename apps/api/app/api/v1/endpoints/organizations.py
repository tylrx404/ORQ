from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.api.dependencies import get_organization_service
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
)
from app.services.organization import (
    OrganizationAlreadyExistsError,
    OrganizationNotFoundError,
    OrganizationService,
)

router = APIRouter()


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
)
async def create_organization(
    request: OrganizationCreateRequest,
    organization_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    try:
        org = await organization_service.create_organization(
            name=request.name,
            slug=request.slug,
            description=request.description,
        )
        return org
    except OrganizationAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.get(
    "/",
    response_model=list[OrganizationResponse],
    summary="List organizations",
)
async def list_organizations(
    skip: int = 0,
    limit: int = 100,
    organization_service: OrganizationService = Depends(get_organization_service),
) -> list[OrganizationResponse]:
    orgs = await organization_service.list_organizations(skip=skip, limit=limit)
    return orgs


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Get an organization by ID",
)
async def get_organization(
    organization_id: UUID,
    organization_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    try:
        org = await organization_service.get_by_id(organization_id)
        return org
        
    except OrganizationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Update an organization",
)
async def update_organization(
    organization_id: UUID,
    request: OrganizationUpdateRequest,
    organization_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    try:
        update_data = request.model_dump(exclude_unset=True)
        org = await organization_service.update_organization(organization_id, update_data)
        return org
    except OrganizationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except OrganizationAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organization",
)
async def delete_organization(
    organization_id: UUID,
    organization_service: OrganizationService = Depends(get_organization_service),
) -> Response:
    try:
        await organization_service.delete_organization(organization_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except OrganizationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e