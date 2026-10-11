from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PromptCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    initial_content: str = Field(..., min_length=1, description="Initial plain text prompt content for version 1")
    organization_id: Optional[UUID] = Field(default=None, description="Target organization ID")


class PromptUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)


class PromptResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    published_version_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptVersionCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Plain text prompt content")


class PromptVersionResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    version_number: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
