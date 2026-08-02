from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.organization_invitation import InvitationStatus
from app.models.organization_membership import MembershipRole


class OrganizationInvitationCreateRequest(BaseModel):
    email: EmailStr
    role: MembershipRole = Field(default=MembershipRole.member)


class OrganizationInvitationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: EmailStr
    role: MembershipRole
    token: str
    status: InvitationStatus
    created_by: UUID
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
