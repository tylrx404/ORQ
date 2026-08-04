from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProviderModelCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    model_identifier: str = Field(..., max_length=255)
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    supports_reasoning: bool = False
    is_active: bool = True


class ProviderModelUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    model_identifier: Optional[str] = Field(default=None, max_length=255)
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supports_streaming: Optional[bool] = None
    supports_tools: Optional[bool] = None
    supports_vision: Optional[bool] = None
    supports_reasoning: Optional[bool] = None
    is_active: Optional[bool] = None


class ProviderModelResponse(BaseModel):
    id: UUID
    provider_id: UUID
    name: str
    model_identifier: str
    context_window: Optional[int]
    max_output_tokens: Optional[int]
    supports_streaming: bool
    supports_tools: bool
    supports_vision: bool
    supports_reasoning: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
