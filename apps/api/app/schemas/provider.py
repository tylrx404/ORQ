from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.provider import ProviderType


class ProviderCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    provider_type: ProviderType
    api_key: str = Field(..., max_length=2048)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    default_model: Optional[str] = Field(default=None, max_length=255)


class ProviderUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    provider_type: Optional[ProviderType] = None
    api_key: Optional[str] = Field(default=None, max_length=2048)
    base_url: Optional[str] = Field(default=None, max_length=2048)
    default_model: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class ProviderResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    provider_type: ProviderType
    base_url: Optional[str]
    default_model: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
