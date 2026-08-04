from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_provider_service,
    require_admin,
    require_member,
)
from app.schemas.provider import ProviderCreateRequest, ProviderResponse
from app.services.provider import DuplicateProviderError, ProviderService

router = APIRouter()


@router.post(
    "",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_provider(
    organization_id: UUID,
    request: ProviderCreateRequest,
    provider_service: ProviderService = Depends(get_provider_service),
):
    try:
        return await provider_service.create_provider(
            organization_id=organization_id,
            name=request.name,
            provider_type=request.provider_type,
            api_key=request.api_key,
            base_url=request.base_url,
            default_model=request.default_model,
        )
    except DuplicateProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "",
    response_model=Sequence[ProviderResponse],
    dependencies=[Depends(require_member)],
)
async def list_providers(
    organization_id: UUID,
    skip: int = 0,
    limit: int = 100,
    provider_service: ProviderService = Depends(get_provider_service),
):
    return await provider_service.list_providers(
        organization_id=organization_id, skip=skip, limit=limit
    )
