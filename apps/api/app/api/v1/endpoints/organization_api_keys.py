from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_api_key_service,
    get_current_user,
    require_admin,
    require_member,
)
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
)
from app.services.api_key import ApiKeyService, DuplicateApiKeyError


router = APIRouter()


@router.post(
    "",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_api_key(
    organization_id: UUID,
    request: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    try:
        api_key, raw_key = await api_key_service.create_key(
            organization_id=organization_id,
            name=request.name,
            user_id=current_user.id,
            expires_at=request.expires_at,
        )
        
        base_response = ApiKeyResponse.model_validate(api_key)
        return ApiKeyCreateResponse(
            **base_response.model_dump(),
            key=raw_key
        )
    except DuplicateApiKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "",
    response_model=Sequence[ApiKeyResponse],
    dependencies=[Depends(require_member)],
)
async def list_api_keys(
    organization_id: UUID,
    skip: int = 0,
    limit: int = 100,
    api_key_service: ApiKeyService = Depends(get_api_key_service),
):
    return await api_key_service.list_keys(
        organization_id=organization_id, skip=skip, limit=limit
    )
