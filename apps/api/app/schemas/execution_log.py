from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExecutionLogCreateRequest(BaseModel):
    organization_id: UUID
    api_key_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    model_name: str = Field(..., max_length=255)
    status_code: int
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    error_message: Optional[str] = None


class ExecutionLogResponse(BaseModel):
    id: UUID
    organization_id: UUID
    api_key_id: Optional[UUID]
    provider_id: Optional[UUID]
    model_id: Optional[UUID]
    model_name: str
    status_code: int
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    latency_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
