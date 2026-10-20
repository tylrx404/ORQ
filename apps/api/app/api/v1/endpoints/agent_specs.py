from typing import Optional, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.dependencies import (
    get_agent_spec_service,
    get_current_user,
    get_organization_membership_repository,
    require_agent_spec_admin,
    require_agent_spec_member,
)
from app.core.permissions import Permission, has_permission
from app.models.agent_spec import AgentSpec
from app.models.user import User
from app.repositories.organization_membership_repository import OrganizationMembershipRepository
from app.schemas.agent_spec import (
    AgentSpecCreateRequest,
    AgentSpecResponse,
    AgentSpecUpdateRequest,
)
from app.services.agent_spec import (
    AgentSpecNotFoundError,
    AgentSpecService,
    DuplicateAgentSpecError,
    InvalidModelReferenceError,
    InvalidPromptReferenceError,
    InvalidPromptVersionReferenceError,
    InvalidProviderReferenceError,
)

router = APIRouter()


async def _resolve_and_verify_org_membership(
    org_id: Optional[UUID],
    current_user: User,
    membership_repo: OrganizationMembershipRepository,
    required_permission: Permission = Permission.VIEW_MEMBERS,
) -> UUID:
    """Validate organization presence, membership, and permissions."""
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id is required (in body, query parameter, or X-Organization-Id header).",
        )

    membership = await membership_repo.get_membership(org_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization membership not found.",
        )

    if not has_permission(membership.role, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Requires {required_permission.value}.",
        )

    return org_id


@router.post(
    "",
    response_model=AgentSpecResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_spec(
    request: AgentSpecCreateRequest,
    organization_id: Optional[UUID] = Query(None),
    x_organization_id: Optional[UUID] = Header(None, alias="X-Organization-Id"),
    current_user: User = Depends(get_current_user),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
    agent_spec_service: AgentSpecService = Depends(get_agent_spec_service),
):
    """Create a new agent specification scoped to an organization."""
    resolved_org_id = request.organization_id or organization_id or x_organization_id

    org_id = await _resolve_and_verify_org_membership(
        resolved_org_id,
        current_user,
        membership_repo,
        required_permission=Permission.VIEW_MEMBERS,
    )

    try:
        return await agent_spec_service.create_agent_spec(
            organization_id=org_id,
            name=request.name,
            description=request.description,
            prompt_id=request.prompt_id,
            prompt_version_id=request.prompt_version_id,
            provider_id=request.provider_id,
            model_id=request.model_id,
            tool_identifiers=request.tool_identifiers,
            memory_policy=request.memory_policy,
            is_active=request.is_active,
        )
    except DuplicateAgentSpecError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except (
        InvalidPromptReferenceError,
        InvalidPromptVersionReferenceError,
        InvalidProviderReferenceError,
        InvalidModelReferenceError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=Sequence[AgentSpecResponse],
)
async def list_agent_specs(
    organization_id: Optional[UUID] = Query(None),
    x_organization_id: Optional[UUID] = Header(None, alias="X-Organization-Id"),
    is_active: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
    agent_spec_service: AgentSpecService = Depends(get_agent_spec_service),
):
    """List agent specifications for an organization with optional filtering and pagination."""
    resolved_org_id = organization_id or x_organization_id

    org_id = await _resolve_and_verify_org_membership(
        resolved_org_id,
        current_user,
        membership_repo,
        required_permission=Permission.VIEW_MEMBERS,
    )

    return await agent_spec_service.list_agent_specs(
        organization_id=org_id,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )


@router.get(
    "/{agent_id}",
    response_model=AgentSpecResponse,
)
async def get_agent_spec(
    agent_spec: AgentSpec = Depends(require_agent_spec_member),
):
    """Retrieve an agent specification by ID."""
    return agent_spec


@router.patch(
    "/{agent_id}",
    response_model=AgentSpecResponse,
)
async def update_agent_spec(
    request: AgentSpecUpdateRequest,
    agent_spec: AgentSpec = Depends(require_agent_spec_member),
    agent_spec_service: AgentSpecService = Depends(get_agent_spec_service),
):
    """Apply partial updates to an agent specification."""
    try:
        return await agent_spec_service.update_agent_spec(
            organization_id=agent_spec.organization_id,
            agent_id=agent_spec.id,
            update_data=request.model_dump(exclude_unset=True),
        )
    except AgentSpecNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DuplicateAgentSpecError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except (
        InvalidPromptReferenceError,
        InvalidPromptVersionReferenceError,
        InvalidProviderReferenceError,
        InvalidModelReferenceError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_agent_spec(
    agent_spec: AgentSpec = Depends(require_agent_spec_admin),
    agent_spec_service: AgentSpecService = Depends(get_agent_spec_service),
):
    """Delete an agent specification. Requires admin or owner role."""
    try:
        await agent_spec_service.delete_agent_spec(
            organization_id=agent_spec.organization_id,
            agent_id=agent_spec.id,
        )
    except AgentSpecNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
