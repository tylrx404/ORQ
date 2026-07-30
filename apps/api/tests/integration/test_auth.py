import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.api.dependencies import get_user_repository
from app.models.user import User
from app.core.security import hash_password
from app.core.jwt import create_access_token


class MockUserRepository:
    def __init__(self):
        self.users = {}
        self.users_by_username = {}

    async def get_by_email(self, email: str):
        return self.users.get(email)

    async def get_by_username(self, username: str):
        return self.users_by_username.get(username)
        
    async def get_by_id(self, user_id):
        for user in self.users.values():
            if str(user.id) == str(user_id):
                return user
        return None

    async def create(self, user: User):
        user.id = uuid4()
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        self.users[user.email] = user
        self.users_by_username[user.username] = user
        return user


@pytest.fixture
def mock_user_repo():
    repo = MockUserRepository()
    app.dependency_overrides[get_user_repository] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


@pytest.fixture
def valid_signup_payload():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "Password123!",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient, mock_user_repo, valid_signup_payload):
    response = await client.post("/v1/auth/signup", json=valid_signup_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == valid_signup_payload["email"]
    assert data["username"] == valid_signup_payload["username"]
    assert "id" in data


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient, mock_user_repo, valid_signup_payload):
    # First signup
    await client.post("/v1/auth/signup", json=valid_signup_payload)
    
    # Second signup with same email, different username
    payload = valid_signup_payload.copy()
    payload["username"] = "different_username"
    
    response = await client.post("/v1/auth/signup", json=payload)
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_signup_duplicate_username(client: AsyncClient, mock_user_repo, valid_signup_payload):
    # First signup
    await client.post("/v1/auth/signup", json=valid_signup_payload)
    
    # Second signup with same username, different email
    payload = valid_signup_payload.copy()
    payload["email"] = "different@example.com"
    
    response = await client.post("/v1/auth/signup", json=payload)
    assert response.status_code == 409
    assert "already taken" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, mock_user_repo, valid_signup_payload):
    # Create user first
    await client.post("/v1/auth/signup", json=valid_signup_payload)
    
    login_payload = {
        "email": valid_signup_payload["email"],
        "password": valid_signup_payload["password"]
    }
    
    response = await client.post("/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, mock_user_repo, valid_signup_payload):
    # Create user first
    await client.post("/v1/auth/signup", json=valid_signup_payload)
    
    login_payload = {
        "email": valid_signup_payload["email"],
        "password": "WrongPassword!"
    }
    
    response = await client.post("/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, mock_user_repo, valid_signup_payload):
    # Create user first
    await client.post("/v1/auth/signup", json=valid_signup_payload)
    
    # Disable user in mock repo
    user = await mock_user_repo.get_by_email(valid_signup_payload["email"])
    user.is_active = False
    
    login_payload = {
        "email": valid_signup_payload["email"],
        "password": valid_signup_payload["password"]
    }
    
    response = await client.post("/v1/auth/login", json=login_payload)
    assert response.status_code == 403
    assert "User account is disabled" in response.json()["detail"]


@pytest.mark.asyncio
async def test_users_me_with_valid_token(client: AsyncClient, mock_user_repo, valid_signup_payload):
    # Create user
    signup_resp = await client.post("/v1/auth/signup", json=valid_signup_payload)
    
    # Login to get token
    login_payload = {
        "email": valid_signup_payload["email"],
        "password": valid_signup_payload["password"]
    }
    login_resp = await client.post("/v1/auth/login", json=login_payload)
    token = login_resp.json()["access_token"]
    
    # Access /users/me
    response = await client.get("/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == valid_signup_payload["email"]
    assert data["username"] == valid_signup_payload["username"]


@pytest.mark.asyncio
async def test_users_me_without_token(client: AsyncClient):
    response = await client.get("/v1/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_users_me_with_invalid_token(client: AsyncClient):
    response = await client.get("/v1/users/me", headers={"Authorization": "Bearer invalid.token.string"})
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]
