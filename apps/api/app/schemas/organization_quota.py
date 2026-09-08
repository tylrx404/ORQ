"""
app/schemas/organization_quota.py
----------------------------------
Pydantic schemas for OrganizationQuota CRUD.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationQuotaCreate(BaseModel):
    """Payload for creating a new quota on an organization."""

    request_limit: int | None = Field(
        default=None,
        ge=1,
        description="Maximum API requests per billing cycle. Omit for unlimited.",
    )
    token_limit: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens per billing cycle. Omit for unlimited.",
    )
    reset_at: datetime = Field(
        description="UTC timestamp when the current billing cycle ends.",
    )


class OrganizationQuotaUpdate(BaseModel):
    """Payload for updating an existing quota record."""

    request_limit: int | None = Field(
        default=None,
        ge=1,
        description="New request limit. Pass null to remove the limit.",
    )
    token_limit: int | None = Field(
        default=None,
        ge=1,
        description="New token limit. Pass null to remove the limit.",
    )
    reset_at: datetime | None = Field(
        default=None,
        description="New cycle end timestamp.",
    )


class OrganizationQuotaResponse(BaseModel):
    """Full quota record returned from the API."""

    id: UUID
    organization_id: UUID
    request_limit: int | None
    token_limit: int | None
    requests_used: int
    tokens_used: int
    reset_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
