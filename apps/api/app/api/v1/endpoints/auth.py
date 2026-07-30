from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service
from app.schemas.auth import UserResponse, UserSignupRequest
from app.services.auth import AuthService, UserAlreadyExistsError

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