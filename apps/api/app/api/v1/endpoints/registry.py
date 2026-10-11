from typing import Optional, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.dependencies import (
    get_current_user,
    get_organization_membership_repository,
    get_prompt_service,
    require_prompt_admin,
    require_prompt_member,
)
from app.core.permissions import Permission, has_permission
from app.models.prompt import Prompt
from app.models.user import User
from app.repositories.organization_membership_repository import OrganizationMembershipRepository
from app.schemas.prompt import (
    PromptCreateRequest,
    PromptResponse,
    PromptUpdateRequest,
    PromptVersionCreateRequest,
    PromptVersionResponse,
)
from app.services.prompt import (
    DuplicatePromptError,
    PromptNotFoundError,
    PromptService,
    PromptVersionNotFoundError,
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
    "/prompts",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    request: PromptCreateRequest,
    organization_id: Optional[UUID] = Query(None),
    x_organization_id: Optional[UUID] = Header(None, alias="X-Organization-Id"),
    current_user: User = Depends(get_current_user),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    resolved_org_id = request.organization_id or organization_id or x_organization_id

    org_id = await _resolve_and_verify_org_membership(
        resolved_org_id,
        current_user,
        membership_repo,
        required_permission=Permission.VIEW_MEMBERS,
    )

    try:
        prompt, _ = await prompt_service.create_prompt(
            organization_id=org_id,
            name=request.name,
            initial_content=request.initial_content,
            description=request.description,
        )
        return prompt
    except DuplicatePromptError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/prompts",
    response_model=Sequence[PromptResponse],
)
async def list_prompts(
    organization_id: Optional[UUID] = Query(None),
    x_organization_id: Optional[UUID] = Header(None, alias="X-Organization-Id"),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    resolved_org_id = organization_id or x_organization_id

    org_id = await _resolve_and_verify_org_membership(
        resolved_org_id,
        current_user,
        membership_repo,
        required_permission=Permission.VIEW_MEMBERS,
    )

    return await prompt_service.list_prompts(
        organization_id=org_id, skip=skip, limit=limit
    )


@router.get(
    "/prompts/{prompt_id}",
    response_model=PromptResponse,
)
async def get_prompt(
    prompt: Prompt = Depends(require_prompt_member),
):
    return prompt


@router.patch(
    "/prompts/{prompt_id}",
    response_model=PromptResponse,
)
async def update_prompt(
    request: PromptUpdateRequest,
    prompt: Prompt = Depends(require_prompt_member),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    try:
        return await prompt_service.update_prompt(
            organization_id=prompt.organization_id,
            prompt_id=prompt.id,
            update_data=request.model_dump(exclude_unset=True),
        )
    except DuplicatePromptError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/prompts/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_prompt(
    prompt: Prompt = Depends(require_prompt_admin),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    await prompt_service.delete_prompt(prompt.organization_id, prompt.id)


@router.post(
    "/prompts/{prompt_id}/versions",
    response_model=PromptVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_version(
    request: PromptVersionCreateRequest,
    prompt: Prompt = Depends(require_prompt_member),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    return await prompt_service.create_version(
        organization_id=prompt.organization_id,
        prompt_id=prompt.id,
        content=request.content,
    )


@router.get(
    "/prompts/{prompt_id}/versions",
    response_model=Sequence[PromptVersionResponse],
)
async def list_prompt_versions(
    prompt: Prompt = Depends(require_prompt_member),
    skip: int = 0,
    limit: int = 100,
    prompt_service: PromptService = Depends(get_prompt_service),
):
    return await prompt_service.list_versions(
        organization_id=prompt.organization_id,
        prompt_id=prompt.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/prompts/{prompt_id}/versions/{version_id}",
    response_model=PromptVersionResponse,
)
async def get_prompt_version(
    version_id: UUID,
    prompt: Prompt = Depends(require_prompt_member),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    try:
        return await prompt_service.get_version(
            organization_id=prompt.organization_id,
            prompt_id=prompt.id,
            version_id=version_id,
        )
    except PromptVersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/prompts/{prompt_id}/versions/{version_id}/publish",
    response_model=PromptResponse,
)
async def publish_prompt_version(
    version_id: UUID,
    prompt: Prompt = Depends(require_prompt_member),
    prompt_service: PromptService = Depends(get_prompt_service),
):
    try:
        return await prompt_service.publish_version(
            organization_id=prompt.organization_id,
            prompt_id=prompt.id,
            version_id=version_id,
        )
    except PromptVersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
