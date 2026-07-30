from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Retrieve the profile of the currently authenticated user.
    """
    # Pydantic will automatically validate and serialize the User model to UserResponse
    return UserResponse.model_validate(current_user)
