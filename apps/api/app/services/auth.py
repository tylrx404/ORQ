"""
app/services/auth.py
--------------------
Authentication and registration business logic.
"""

from app.core.jwt import create_access_token
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserLoginRequest, UserSignupRequest


class AuthException(Exception):
    """Base exception for auth service errors."""
    pass


class InvalidCredentialsError(AuthException):
    """Raised when authentication fails due to invalid credentials."""
    pass


class UserInactiveError(AuthException):
    """Raised when an inactive user attempts to authenticate."""
    pass


class UserAlreadyExistsError(AuthException):
    """Raised when attempting to register an existing user."""
    pass


class AuthService:
    """Service layer for user authentication and registration."""

    def __init__(self, user_repository: UserRepository):
        """
        Initialize the AuthService.

        Args:
            user_repository: Injected repository for user data access.
        """
        self._user_repo = user_repository

    async def register_user(self, signup_request: UserSignupRequest) -> User:
        """
        Register a new user.

        Args:
            signup_request: The validated signup data.

        Returns:
            The newly created User model instance.

        Raises:
            UserAlreadyExistsError: If the email or username is already registered.
        """
        # Check if email is already taken
        existing_email = await self._user_repo.get_by_email(email=signup_request.email)
        if existing_email:
            raise UserAlreadyExistsError("Email already registered.")

        # Check if username is already taken
        existing_username = await self._user_repo.get_by_username(username=signup_request.username)
        if existing_username:
            raise UserAlreadyExistsError("Username already taken.")

        # Hash password and create user
        hashed_password = hash_password(signup_request.password)
        
        user = User(
            email=signup_request.email,
            username=signup_request.username,
            password_hash=hashed_password,
            first_name=signup_request.first_name,
            last_name=signup_request.last_name,
        )
        
        created_user = await self._user_repo.create(user)
        return created_user

    async def authenticate_user(self, login_request: UserLoginRequest) -> str:
        """
        Authenticate a user and generate an access token.

        Args:
            login_request: The validated login credentials.

        Returns:
            The generated JWT access token string.

        Raises:
            InvalidCredentialsError: If the user is not found or password does not match.
            UserInactiveError: If the user account is disabled.
        """
        user = await self._user_repo.get_by_email(email=login_request.email)
        
        if not user or not verify_password(login_request.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
            
        if not user.is_active:
            raise UserInactiveError("User account is disabled.")
            
        # The subject of the token is typically the user ID (as a string)
        access_token = create_access_token(subject=str(user.id))
        
        return access_token
