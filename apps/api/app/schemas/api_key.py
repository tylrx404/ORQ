from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    expires_at: Optional[datetime] = None


class ApiKeyUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None


class ApiKeyResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    key_prefix: str
    expires_at: Optional[datetime]
    is_active: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    key: str
