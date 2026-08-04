from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_provider_model_service,
    require_admin,
    require_member,
)
from app.models.provider import Provider
from app.schemas.provider_model import ProviderModelCreateRequest, ProviderModelResponse
from app.services.provider_model import DuplicateProviderModelError, ProviderModelService

router = APIRouter()


@router.post(
    "",
    response_model=ProviderModelResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_provider_model(
    organization_id: UUID,
    provider_id: UUID,
    request: ProviderModelCreateRequest,
    provider_model_service: ProviderModelService = Depends(get_provider_model_service),
):
    try:
        return await provider_model_service.create_model(
            provider_id=provider_id,
            name=request.name,
            model_identifier=request.model_identifier,
            context_window=request.context_window,
            max_output_tokens=request.max_output_tokens,
            supports_streaming=request.supports_streaming,
            supports_tools=request.supports_tools,
            supports_vision=request.supports_vision,
            supports_reasoning=request.supports_reasoning,
            is_active=request.is_active,
        )
    except DuplicateProviderModelError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "",
    response_model=Sequence[ProviderModelResponse],
    dependencies=[Depends(require_member)],
)
async def list_provider_models(
    organization_id: UUID,
    provider_id: UUID,
    skip: int = 0,
    limit: int = 100,
    provider_model_service: ProviderModelService = Depends(get_provider_model_service),
):
    return await provider_model_service.list_models(
        provider_id=provider_id, skip=skip, limit=limit
    )
