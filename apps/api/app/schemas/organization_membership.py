from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.organization_membership import MembershipRole


class MembershipCreateRequest(BaseModel):
    user_id: UUID
    role: MembershipRole = Field(default=MembershipRole.member)


class MembershipUpdateRequest(BaseModel):
    role: MembershipRole


class MembershipResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: MembershipRole
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
