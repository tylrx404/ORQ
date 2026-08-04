import pytest
from httpx import AsyncClient, ASGITransport
from uuid import UUID, uuid4

from app.main import app
from app.api.dependencies import (
    get_current_user,
    require_admin,
    require_member,
    require_provider_admin,
    get_provider_repository,
    get_provider_service,
)
from app.models.user import User
from app.models.provider import Provider, ProviderType
from app.services.provider import ProviderNotFoundError, DuplicateProviderError


from datetime import datetime, timezone

class MockProviderRepository:
    def __init__(self):
        self.providers = {}

    async def get_by_id(self, provider_id):
        return self.providers.get(provider_id)

    async def get_by_name_and_org(self, organization_id, name):
        for provider in self.providers.values():
            if provider.organization_id == organization_id and provider.name == name:
                return provider
        return None

    async def list_by_organization(self, organization_id, skip=0, limit=100):
        return [
            provider for provider in self.providers.values() if provider.organization_id == organization_id
        ]

    async def create(self, provider):
        provider.id = uuid4()
        provider.created_at = datetime.now(timezone.utc)
        provider.updated_at = datetime.now(timezone.utc)
        provider.is_active = getattr(provider, "is_active", None)
        if provider.is_active is None:
            provider.is_active = True
        provider.base_url = getattr(provider, "base_url", None)
        provider.default_model = getattr(provider, "default_model", None)
        self.providers[provider.id] = provider
        return provider

    async def update(self, provider):
        provider.updated_at = datetime.now(timezone.utc)
        self.providers[provider.id] = provider
        return provider

    async def delete(self, provider):
        if provider.id in self.providers:
            del self.providers[provider.id]


@pytest.fixture
def mock_dependencies():
    repo = MockProviderRepository()

    mock_user = User(
        id=uuid4(),
        email="admin@example.com",
        is_active=True,
    )

    async def mock_require_provider_admin(provider_id: UUID):
        provider = await repo.get_by_id(provider_id)
        if not provider:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
        return provider

    app.dependency_overrides[get_provider_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[require_member] = lambda: None
    app.dependency_overrides[require_provider_admin] = mock_require_provider_admin

    yield repo, mock_user
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_provider(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            f"/api/v1/organizations/{org_id}/providers",
            json={
                "name": "My OpenAI",
                "provider_type": "openai",
                "api_key": "sk-12345",
                "default_model": "gpt-4"
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My OpenAI"
    assert data["provider_type"] == "openai"


@pytest.mark.asyncio
async def test_duplicate_provider(mock_dependencies):
    repo, user = mock_dependencies
    org_id = str(uuid4())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            f"/api/v1/organizations/{org_id}/providers",
            json={"name": "My OpenAI", "provider_type": "openai", "api_key": "sk-12345"},
        )
        response = await ac.post(
            f"/api/v1/organizations/{org_id}/providers",
            json={"name": "My OpenAI", "provider_type": "openai", "api_key": "sk-12345"},
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_provider(mock_dependencies):
    repo, user = mock_dependencies
    org_id = uuid4()
    provider = Provider(
        organization_id=org_id,
        name="Anthropic",
        provider_type=ProviderType.anthropic,
        api_key="ant-123",
    )
    provider = await repo.create(provider)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/providers/{provider.id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Anthropic"


@pytest.mark.asyncio
async def test_update_provider(mock_dependencies):
    repo, user = mock_dependencies
    org_id = uuid4()
    provider = Provider(
        organization_id=org_id,
        name="Anthropic",
        provider_type=ProviderType.anthropic,
        api_key="ant-123",
    )
    provider = await repo.create(provider)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/providers/{provider.id}",
            json={"default_model": "claude-3"},
        )

    assert response.status_code == 200
    assert response.json()["default_model"] == "claude-3"


@pytest.mark.asyncio
async def test_delete_provider(mock_dependencies):
    repo, user = mock_dependencies
    org_id = uuid4()
    provider = Provider(
        organization_id=org_id,
        name="Gemini",
        provider_type=ProviderType.gemini,
        api_key="gem-123",
    )
    provider = await repo.create(provider)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.delete(f"/api/v1/providers/{provider.id}")

    assert response.status_code == 204
    assert await repo.get_by_id(provider.id) is None
