from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_current_api_key, get_llm_gateway_service
from app.models.api_key import ApiKey
from app.schemas.chat_completion import ChatCompletionRequest
from app.services.llm_gateway import (
    LLMGatewayError,
    LLMGatewayService,
    ModelNotFoundError,
    ProviderExecutionError,
    ProviderNotFoundError,
)

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_200_OK,
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    current_api_key: ApiKey = Depends(get_current_api_key),
    llm_gateway_service: LLMGatewayService = Depends(get_llm_gateway_service),
) -> Any:
    """
    OpenAI-compatible chat completion proxy endpoint authenticated via X-API-Key.
    Supports both non-streaming (JSON) and streaming (text/event-stream) responses.
    """
    try:
        if request.stream:
            stream_gen = await llm_gateway_service.stream_chat_completion(
                organization_id=current_api_key.organization_id,
                api_key_id=current_api_key.id,
                model_identifier=request.model,
                messages=[m.model_dump() for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream_options=request.stream_options,
            )
            return StreamingResponse(stream_gen, media_type="text/event-stream")

        response_data, _ = await llm_gateway_service.execute_chat_completion(
            organization_id=current_api_key.organization_id,
            api_key_id=current_api_key.id,
            model_identifier=request.model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )
        return response_data
    except (ModelNotFoundError, ProviderNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ProviderExecutionError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        )
    except LLMGatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
