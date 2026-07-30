from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service
from app.schemas.auth import TokenResponse, UserLoginRequest, UserResponse, UserSignupRequest
from app.services.auth import AuthService, InvalidCredentialsError, UserAlreadyExistsError, UserInactiveError

router = APIRouter()


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(
    signup_request: UserSignupRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Register a new user with the provided credentials.
    """
    try:
        user = await auth_service.register_user(signup_request)
        return UserResponse.model_validate(user)  # Pydantic will automatically validate and serialize this to UserResponse
    except UserAlreadyExistsError as e:
        raise HTTPException(    
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user and return a JWT",
)
async def login(
    login_request: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate a user using email and password.
    Returns a JWT access token if successful.
    """
    try:
        token = await auth_service.authenticate_user(login_request)
        return TokenResponse(access_token=token, token_type="bearer")
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except UserInactiveError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e