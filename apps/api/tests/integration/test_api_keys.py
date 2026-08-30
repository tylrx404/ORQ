import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from uuid import UUID, uuid4

from app.main import app
from app.api.dependencies import (
    get_current_user,
    require_admin,
    require_member,
    require_api_key_admin,
    get_api_key_repository,
    get_api_key_service,
    get_current_api_key,
)
from app.models.user import User
from app.models.api_key import ApiKey
from app.services.api_key import ApiKeyService


class MockApiKeyRepository:
    def __init__(self):
        self.api_keys: dict[UUID, ApiKey] = {}

    async def get_by_id(self, key_id: UUID) -> ApiKey | None:
        return self.api_keys.get(key_id)

    async def get_by_name_and_org(self, organization_id: UUID, name: str) -> ApiKey | None:
        for k in self.api_keys.values():
            if k.organization_id == organization_id and k.name == name:
                return k
        return None

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        for k in self.api_keys.values():
            if k.key_hash == key_hash:
                return k
        return None

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ApiKey]:
        return [
            k for k in self.api_keys.values() if k.organization_id == organization_id
        ][skip : skip + limit]

    async def create(self, api_key: ApiKey) -> ApiKey:
        api_key.id = uuid4()
        api_key.created_at = datetime.now(timezone.utc)
        api_key.updated_at = datetime.now(timezone.utc)
        if api_key.is_active is None:
            api_key.is_active = True
        self.api_keys[api_key.id] = api_key
        return api_key

    async def update(self, api_key: ApiKey) -> ApiKey:
        api_key.updated_at = datetime.now(timezone.utc)
        self.api_keys[api_key.id] = api_key
        return api_key

    async def delete(self, api_key: ApiKey) -> None:
        self.api_keys.pop(api_key.id, None)


@pytest.fixture
def mock_dependencies():
    repo = MockApiKeyRepository()

    mock_user = User(
        id=uuid4(),
        email="admin@example.com",
        is_active=True,
    )

    async def mock_require_api_key_admin(key_id: UUID):
        api_key = await repo.get_by_id(key_id)
        if not api_key:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="API key not found."
            )
        return api_key

    app.dependency_overrides[get_api_key_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[require_member] = lambda: None
    app.dependency_overrides[require_api_key_admin] = mock_require_api_key_admin

    yield repo, mock_user
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_api_key(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            f"/api/v1/organizations/{org_id}/api-keys",
            json={"name": "test-key"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-key"
    assert "key" in data
    assert data["key"].startswith("orq_sk_")
    assert "key_hash" not in data
    assert data["key_prefix"] == data["key"][:15]


@pytest.mark.asyncio
async def test_create_api_key_duplicate(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res1 = await ac.post(
            f"/api/v1/organizations/{org_id}/api-keys",
            json={"name": "duplicate-key"},
        )
        assert res1.status_code == 201

        res2 = await ac.post(
            f"/api/v1/organizations/{org_id}/api-keys",
            json={"name": "duplicate-key"},
        )
        assert res2.status_code == 409


@pytest.mark.asyncio
async def test_list_api_keys(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            f"/api/v1/organizations/{org_id}/api-keys",
            json={"name": "key-1"},
        )
        response = await ac.get(f"/api/v1/organizations/{org_id}/api-keys")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "key-1"
    assert "key" not in data[0]
    assert "key_hash" not in data[0]


@pytest.mark.asyncio
async def test_get_api_key(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            f"/api/v1/organizations/{org_id}/api-keys",
            json={"name": "get-key"},
        )
        key_id = create_resp.json()["id"]

        response = await ac.get(f"/api/v1/api-keys/{key_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "get-key"
    assert "key" not in data
    assert "key_hash" not in data


@pytest.mark.asyncio
async def test_update_api_key(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            f"/api/v1/organizations/{org_id}/api-keys",
            json={"name": "update-key"},
        )
        key_id = create_resp.json()["id"]

        response = await ac.patch(
            f"/api/v1/api-keys/{key_id}",
            json={"name": "updated-key", "is_active": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated-key"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_api_key(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            f"/api/v1/organizations/{org_id}/api-keys",
            json={"name": "delete-key"},
        )
        key_id = create_resp.json()["id"]

        response = await ac.delete(f"/api/v1/api-keys/{key_id}")
        assert response.status_code == 204

        get_resp = await ac.get(f"/api/v1/api-keys/{key_id}")
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_validate_api_key_service(mock_dependencies):
    repo, user = mock_dependencies
    service = ApiKeyService(repo)
    org_id = uuid4()

    api_key_obj, raw_key = await service.create_key(
        organization_id=org_id,
        name="val-key",
        user_id=user.id,
    )

    validated = await service.validate_key(raw_key)
    assert validated.id == api_key_obj.id
    assert validated.organization_id == org_id
