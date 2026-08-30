from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_api_key_service,
    require_api_key_admin,
)
from app.schemas.api_key import ApiKeyResponse, ApiKeyUpdateRequest
from app.services.api_key import (
    ApiKeyNotFoundError,
    ApiKeyService,
    DuplicateApiKeyError,
)

router = APIRouter()


@router.get(
    "/{key_id}",
    response_model=ApiKeyResponse,
    dependencies=[Depends(require_api_key_admin)],
)
async def get_api_key(
    key_id: UUID,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    try:
        return await api_key_service.get_key(key_id)
    except ApiKeyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{key_id}",
    response_model=ApiKeyResponse,
    dependencies=[Depends(require_api_key_admin)],
)
async def update_api_key(
    key_id: UUID,
    request: ApiKeyUpdateRequest,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    try:
        return await api_key_service.update_key(
            key_id=key_id,
            name=request.name,
            is_active=request.is_active,
        )
    except ApiKeyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DuplicateApiKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key_admin)],
)
async def delete_api_key(
    key_id: UUID,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    try:
        await api_key_service.delete_key(key_id)
    except ApiKeyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
