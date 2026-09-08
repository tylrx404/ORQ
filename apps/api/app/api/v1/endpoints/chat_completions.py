from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse

from app.api.dependencies import (
    get_current_api_key,
    get_llm_gateway_service,
    get_organization_quota_service,
    get_rate_limit_service,
)
from app.core.config import settings
from app.models.api_key import ApiKey
from app.schemas.chat_completion import ChatCompletionRequest
from app.services.organization_quota import OrganizationQuotaService
from app.services.rate_limit import RateLimitService
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
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
    quota_service: OrganizationQuotaService = Depends(get_organization_quota_service),
) -> Any:
    """
    OpenAI-compatible chat completion proxy endpoint authenticated via X-API-Key.
    Supports both non-streaming (JSON) and streaming (text/event-stream) responses.
    """
    try:
        allowed, headers, error_body = await rate_limit_service.check_rate_limit(
            organization_id=current_api_key.organization_id,
            limit=settings.RATE_LIMIT_RPM,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rate limit service unavailable",
        )

    if not allowed:
        return JSONResponse(status_code=429, content=error_body, headers=headers)

    quota_allowed = await quota_service.check_and_increment_request_quota(
        organization_id=current_api_key.organization_id
    )
    if not quota_allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "message": "You have exceeded your organization's monthly usage quota. Please check your plan details.",
                    "type": "insufficient_quota",
                    "code": 429,
                }
            },
            headers=headers,
        )

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
            return StreamingResponse(stream_gen, media_type="text/event-stream", headers=headers)

        response_data, _ = await llm_gateway_service.execute_chat_completion(
            organization_id=current_api_key.organization_id,
            api_key_id=current_api_key.id,
            model_identifier=request.model,
            messages=[m.model_dump() for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )
        return JSONResponse(content=response_data, headers=headers)
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
