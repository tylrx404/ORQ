from uuid import UUID

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import TokenError, decode_access_token
from app.core.permissions import Permission, has_permission
from app.models.organization_membership import OrganizationMembership
from app.models.organization_invitation import OrganizationInvitation
from app.models.user import User
from app.models.provider import Provider
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.organization_membership_repository import OrganizationMembershipRepository
from app.repositories.organization_invitation_repository import OrganizationInvitationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.provider_repository import ProviderRepository
from app.models.provider_model import ProviderModel
from app.models.api_key import ApiKey
from app.models.execution_log import ExecutionLog
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.organization_membership_repository import OrganizationMembershipRepository
from app.repositories.organization_invitation_repository import OrganizationInvitationRepository
from app.repositories.user_repository import UserRepository
from app.repositories.provider_repository import ProviderRepository
from app.repositories.provider_model_repository import ProviderModelRepository
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.services.auth import AuthService
from app.services.organization import OrganizationService
from app.services.organization_membership import OrganizationMembershipService
from app.services.organization_invitation import OrganizationInvitationService
from app.services.provider import ProviderService
from app.services.provider_model import ProviderModelService
from app.services.api_key import ApiKeyService, InvalidApiKeyError
from app.services.llm_gateway import LLMGatewayService
from app.services.usage import UsageService
from app.services.rate_limit import RateLimitService
from app.services.organization_quota import OrganizationQuotaService
from app.repositories.organization_quota_repository import OrganizationQuotaRepository
from app.redis.client import redis_manager

from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/auth/login"
)

def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Provide a UserRepository instance."""
    return UserRepository(db)


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    """Provide an AuthService instance."""
    return AuthService(user_repository)


def get_organization_repository(db: AsyncSession = Depends(get_db)) -> OrganizationRepository:
    """Provide an OrganizationRepository instance."""
    return OrganizationRepository(db)


def get_organization_service(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
) -> OrganizationService:
    """Provide an OrganizationService instance."""
    return OrganizationService(organization_repository)


def get_organization_membership_repository(db: AsyncSession = Depends(get_db)) -> OrganizationMembershipRepository:
    """Provide an OrganizationMembershipRepository instance."""
    return OrganizationMembershipRepository(db)


def get_organization_membership_service(
    membership_repository: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
) -> OrganizationMembershipService:
    """Provide an OrganizationMembershipService instance."""
    return OrganizationMembershipService(membership_repository)


def get_organization_invitation_repository(db: AsyncSession = Depends(get_db)) -> OrganizationInvitationRepository:
    """Provide an OrganizationInvitationRepository instance."""
    return OrganizationInvitationRepository(db)


def get_organization_invitation_service(
    invitation_repository: OrganizationInvitationRepository = Depends(get_organization_invitation_repository),
    membership_service: OrganizationMembershipService = Depends(get_organization_membership_service),
) -> OrganizationInvitationService:
    """Provide an OrganizationInvitationService instance."""
    return OrganizationInvitationService(invitation_repository, membership_service)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Dependency to retrieve the currently authenticated user.

    Reads the JWT from the Authorization header, validates it, and fetches the user.

    Raises:
        HTTPException 401: If token is invalid, expired, or user is not found.
        HTTPException 403: If user is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
    except TokenError as e:
        raise credentials_exception from e

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except ValueError as e:
        raise credentials_exception from e

    user = await user_repository.get_by_id(user_id)
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_membership(
    organization_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
) -> OrganizationMembership:
    """Retrieve the membership of the currently authenticated user in the requested organization."""
    membership = await membership_repo.get_membership(organization_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization membership not found."
        )
    return membership


def require_member(
    membership: OrganizationMembership = Depends(get_current_membership),
) -> OrganizationMembership:
    """Ensure the user has member permissions."""
    if not has_permission(membership.role, Permission.VIEW_MEMBERS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires member role."
        )
    return membership


def require_admin(
    membership: OrganizationMembership = Depends(get_current_membership),
) -> OrganizationMembership:
    """Ensure the user has admin permissions."""
    if not has_permission(membership.role, Permission.UPDATE_ORGANIZATION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires admin or owner role."
        )
    return membership


def require_owner(
    membership: OrganizationMembership = Depends(get_current_membership),
) -> OrganizationMembership:
    """Ensure the user has owner permissions."""
    if not has_permission(membership.role, Permission.DELETE_ORGANIZATION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires owner role."
        )
    return membership


def get_provider_repository(db: AsyncSession = Depends(get_db)) -> ProviderRepository:
    """Provide a ProviderRepository instance."""
    return ProviderRepository(db)


def get_provider_service(
    provider_repository: ProviderRepository = Depends(get_provider_repository),
) -> ProviderService:
    """Provide a ProviderService instance."""
    return ProviderService(provider_repository)


async def require_provider_admin(
    provider_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    provider_repo: ProviderRepository = Depends(get_provider_repository),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
) -> Provider:
    """Ensure the user has admin permissions for the organization owning the provider."""
    provider = await provider_repo.get_by_id(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found."
        )

    membership = await membership_repo.get_membership(provider.organization_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization membership not found."
        )

    if not has_permission(membership.role, Permission.UPDATE_ORGANIZATION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires admin or owner role."
        )
    return provider


def get_provider_model_repository(db: AsyncSession = Depends(get_db)) -> ProviderModelRepository:
    """Provide a ProviderModelRepository instance."""
    return ProviderModelRepository(db)


def get_provider_model_service(
    provider_model_repository: ProviderModelRepository = Depends(get_provider_model_repository),
) -> ProviderModelService:
    """Provide a ProviderModelService instance."""
    return ProviderModelService(provider_model_repository)


async def require_provider_member(
    provider_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    provider_repo: ProviderRepository = Depends(get_provider_repository),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
) -> Provider:
    """Ensure the user is a member of the organization owning the provider."""
    provider = await provider_repo.get_by_id(provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found."
        )

    membership = await membership_repo.get_membership(provider.organization_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization membership not found."
        )

    if not has_permission(membership.role, Permission.VIEW_MEMBERS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires member role."
        )
    return provider


def get_api_key_repository(db: AsyncSession = Depends(get_db)) -> ApiKeyRepository:
    """Provide an ApiKeyRepository instance."""
    return ApiKeyRepository(db)


def get_api_key_service(
    api_key_repository: ApiKeyRepository = Depends(get_api_key_repository),
) -> ApiKeyService:
    """Provide an ApiKeyService instance."""
    return ApiKeyService(api_key_repository)


async def require_api_key_admin(
    key_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    api_key_repo: ApiKeyRepository = Depends(get_api_key_repository),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
) -> ApiKey:
    """Ensure the user has admin permissions for the organization owning the API key."""
    api_key = await api_key_repo.get_by_id(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found."
        )

    membership = await membership_repo.get_membership(api_key.organization_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization membership not found."
        )

    if not has_permission(membership.role, Permission.UPDATE_ORGANIZATION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires admin or owner role."
        )
    return api_key


async def get_current_api_key(
    x_api_key: str = Depends(api_key_header),
    api_key_service: ApiKeyService = Depends(get_api_key_service),
) -> ApiKey:
    """
    Authenticate a machine-to-machine request using the X-API-Key header.
    Validates the key and returns the ApiKey metadata.
    """
    try:
        return await api_key_service.validate_key(x_api_key)
    except InvalidApiKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "ApiKey"},
        )


def get_execution_log_repository(
    db: AsyncSession = Depends(get_db),
) -> ExecutionLogRepository:
    """Provide an ExecutionLogRepository instance."""
    return ExecutionLogRepository(db)


def get_llm_gateway_service(
    provider_repo: ProviderRepository = Depends(get_provider_repository),
    model_repo: ProviderModelRepository = Depends(get_provider_model_repository),
    execution_log_repo: ExecutionLogRepository = Depends(get_execution_log_repository),
) -> LLMGatewayService:
    """Provide an LLMGatewayService instance."""
    return LLMGatewayService(provider_repo, model_repo, execution_log_repo)


async def require_execution_member(
    execution_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
    execution_log_repo: ExecutionLogRepository = Depends(get_execution_log_repository),
    membership_repo: OrganizationMembershipRepository = Depends(get_organization_membership_repository),
) -> ExecutionLog:
    """Ensure the user is a member of the organization owning the execution log."""
    execution_log = await execution_log_repo.get_by_id(execution_id)
    if not execution_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution log not found."
        )

    membership = await membership_repo.get_membership(execution_log.organization_id, current_user.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization membership not found."
        )

    if not has_permission(membership.role, Permission.VIEW_MEMBERS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Requires member role."
        )
    return execution_log


def get_usage_service(
    execution_log_repo: ExecutionLogRepository = Depends(get_execution_log_repository),
) -> UsageService:
    """Provide a UsageService instance."""
    return UsageService(execution_log_repo)


def get_rate_limit_service() -> RateLimitService:
    """Provide a RateLimitService instance."""
    return RateLimitService(redis_manager.get_client())


def get_organization_quota_repository(
    db: AsyncSession = Depends(get_db),
) -> OrganizationQuotaRepository:
    """Provide an OrganizationQuotaRepository instance."""
    return OrganizationQuotaRepository(db)


def get_organization_quota_service(
    repo: OrganizationQuotaRepository = Depends(get_organization_quota_repository),
) -> OrganizationQuotaService:
    """Provide an OrganizationQuotaService instance."""
    return OrganizationQuotaService(repo)
