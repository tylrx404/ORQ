from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_provider_service,
    require_provider_admin,
    get_current_membership,
)
from app.schemas.provider import ProviderResponse, ProviderUpdateRequest
from app.services.provider import DuplicateProviderError, ProviderNotFoundError, ProviderService

router = APIRouter()


@router.get(
    "/{provider_id}",
    response_model=ProviderResponse,
    dependencies=[Depends(require_provider_admin)],
)
async def get_provider(
    provider_id: UUID,
    provider_service: ProviderService = Depends(get_provider_service),
):
    try:
        return await provider_service.get_provider(provider_id)
    except ProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{provider_id}",
    response_model=ProviderResponse,
    dependencies=[Depends(require_provider_admin)],
)
async def update_provider(
    provider_id: UUID,
    request: ProviderUpdateRequest,
    provider_service: ProviderService = Depends(get_provider_service),
):
    try:
        return await provider_service.update_provider(
            provider_id, request.model_dump(exclude_unset=True)
        )
    except ProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DuplicateProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_provider_admin)],
)
async def delete_provider(
    provider_id: UUID,
    provider_service: ProviderService = Depends(get_provider_service),
):
    try:
        await provider_service.delete_provider(provider_id)
    except ProviderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
