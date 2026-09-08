from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_organization_quota_service, require_admin
from app.schemas.organization_quota import (
    OrganizationQuotaCreate,
    OrganizationQuotaResponse,
    OrganizationQuotaUpdate,
)
from app.services.organization_quota import (
    OrganizationQuotaService,
    QuotaAlreadyExistsError,
    QuotaNotFoundError,
)

router = APIRouter()


@router.get(
    "/quota",
    response_model=OrganizationQuotaResponse,
    dependencies=[Depends(require_admin)],
)
async def get_quota(
    organization_id: UUID,
    quota_service: OrganizationQuotaService = Depends(get_organization_quota_service),
) -> OrganizationQuotaResponse:
    """Return the quota record for an organization."""
    try:
        quota = await quota_service.get_quota(organization_id)
    except QuotaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return OrganizationQuotaResponse.model_validate(quota)


@router.post(
    "/quota",
    response_model=OrganizationQuotaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_quota(
    organization_id: UUID,
    body: OrganizationQuotaCreate,
    quota_service: OrganizationQuotaService = Depends(get_organization_quota_service),
) -> OrganizationQuotaResponse:
    """Create a usage quota for an organization."""
    try:
        quota = await quota_service.create_quota(organization_id, body)
    except QuotaAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return OrganizationQuotaResponse.model_validate(quota)


@router.patch(
    "/quota",
    response_model=OrganizationQuotaResponse,
    dependencies=[Depends(require_admin)],
)
async def update_quota(
    organization_id: UUID,
    body: OrganizationQuotaUpdate,
    quota_service: OrganizationQuotaService = Depends(get_organization_quota_service),
) -> OrganizationQuotaResponse:
    """Update quota limits or cycle end date for an organization."""
    try:
        quota = await quota_service.update_quota(organization_id, body)
    except QuotaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return OrganizationQuotaResponse.model_validate(quota)


@router.delete(
    "/quota",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_quota(
    organization_id: UUID,
    quota_service: OrganizationQuotaService = Depends(get_organization_quota_service),
) -> None:
    """Remove the quota record for an organization."""
    try:
        await quota_service.delete_quota(organization_id)
    except QuotaNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
