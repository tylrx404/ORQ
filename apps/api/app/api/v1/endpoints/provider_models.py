from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_provider_model_service,
    require_provider_admin,
    require_provider_member,
)
from app.schemas.provider_model import ProviderModelResponse, ProviderModelUpdateRequest
from app.services.provider_model import (
    DuplicateProviderModelError,
    ProviderModelNotFoundError,
    ProviderModelService,
)

router = APIRouter()


@router.get(
    "/{model_id}",
    response_model=ProviderModelResponse,
    dependencies=[Depends(require_provider_member)],
)
async def get_provider_model(
    provider_id: UUID,
    model_id: UUID,
    provider_model_service: ProviderModelService = Depends(get_provider_model_service),
):
    try:
        return await provider_model_service.get_model(model_id)
    except ProviderModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{model_id}",
    response_model=ProviderModelResponse,
    dependencies=[Depends(require_provider_admin)],
)
async def update_provider_model(
    provider_id: UUID,
    model_id: UUID,
    request: ProviderModelUpdateRequest,
    provider_model_service: ProviderModelService = Depends(get_provider_model_service),
):
    try:
        return await provider_model_service.update_model(
            model_id, request.model_dump(exclude_unset=True)
        )
    except ProviderModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DuplicateProviderModelError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_provider_admin)],
)
async def delete_provider_model(
    provider_id: UUID,
    model_id: UUID,
    provider_model_service: ProviderModelService = Depends(get_provider_model_service),
):
    try:
        await provider_model_service.delete_model(model_id)
    except ProviderModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
