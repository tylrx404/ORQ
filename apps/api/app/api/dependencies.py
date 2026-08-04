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
from app.repositories.provider_model_repository import ProviderModelRepository
from app.services.auth import AuthService
from app.services.organization import OrganizationService
from app.services.organization_membership import OrganizationMembershipService
from app.services.organization_invitation import OrganizationInvitationService
from app.services.provider import ProviderService
from app.services.provider_model import ProviderModelService

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
