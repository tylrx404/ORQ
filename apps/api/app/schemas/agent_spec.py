from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class AgentSpecCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    organization_id: Optional[UUID] = Field(default=None, description="Target organization ID")
    prompt_id: Optional[UUID] = Field(default=None, description="Referenced prompt ID")
    prompt_version_id: Optional[UUID] = Field(default=None, description="Referenced prompt version ID")
    provider_id: Optional[UUID] = Field(default=None, description="Referenced provider ID")
    model_id: Optional[UUID] = Field(default=None, description="Referenced provider model ID")
    tool_identifiers: list[str] = Field(default_factory=list, description="Allowed tool identifiers")
    memory_policy: dict[str, Any] = Field(default_factory=dict, description="Memory policy configuration")
    is_active: bool = Field(default=True, description="Whether the agent specification is active")


class AgentSpecUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    prompt_id: Optional[UUID] = Field(default=None)
    prompt_version_id: Optional[UUID] = Field(default=None)
    provider_id: Optional[UUID] = Field(default=None)
    model_id: Optional[UUID] = Field(default=None)
    tool_identifiers: Optional[list[str]] = Field(default=None)
    memory_policy: Optional[dict[str, Any]] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    @field_validator("name", "tool_identifiers", "memory_policy", "is_active")
    @classmethod
    def prevent_null_non_nullable_fields(cls, v: Any, info: ValidationInfo) -> Any:
        if v is None:
            raise ValueError(f"{info.field_name} cannot be null")
        return v


class AgentSpecResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str]
    prompt_id: Optional[UUID]
    prompt_version_id: Optional[UUID]
    provider_id: Optional[UUID]
    model_id: Optional[UUID]
    tool_identifiers: list[str]
    memory_policy: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
