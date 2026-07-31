from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.jwt import TokenError, decode_access_token
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService
from app.services.organization import OrganizationService

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
