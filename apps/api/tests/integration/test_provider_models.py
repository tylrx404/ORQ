import pytest
from httpx import AsyncClient, ASGITransport
from uuid import UUID, uuid4

from app.main import app
from app.api.dependencies import (
    get_current_user,
    require_admin,
    require_member,
    require_provider_admin,
    require_provider_member,
    get_provider_model_repository,
    get_provider_model_service,
)
from app.models.user import User
from app.models.provider import Provider, ProviderType
from app.models.provider_model import ProviderModel

from datetime import datetime, timezone


class MockProviderModelRepository:
    def __init__(self):
        self.models: dict[UUID, ProviderModel] = {}

    async def get_by_id(self, model_id: UUID) -> ProviderModel | None:
        return self.models.get(model_id)

    async def get_duplicate(self, provider_id: UUID, model_identifier: str) -> ProviderModel | None:
        for m in self.models.values():
            if m.provider_id == provider_id and m.model_identifier == model_identifier:
                return m
        return None

    async def list_by_provider(self, provider_id: UUID, skip: int = 0, limit: int = 100):
        return [m for m in self.models.values() if m.provider_id == provider_id]

    async def create(self, model: ProviderModel) -> ProviderModel:
        model.id = uuid4()
        model.created_at = datetime.now(timezone.utc)
        model.updated_at = datetime.now(timezone.utc)
        self.models[model.id] = model
        return model

    async def update(self, model: ProviderModel) -> ProviderModel:
        model.updated_at = datetime.now(timezone.utc)
        self.models[model.id] = model
        return model

    async def delete(self, model: ProviderModel) -> None:
        self.models.pop(model.id, None)


def make_provider(org_id: UUID | None = None) -> Provider:
    provider = Provider(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        name="Test Provider",
        provider_type=ProviderType.openai,
        api_key="sk-test",
    )
    provider.created_at = datetime.now(timezone.utc)
    provider.updated_at = datetime.now(timezone.utc)
    provider.is_active = True
    return provider


@pytest.fixture
def mock_dependencies():
    repo = MockProviderModelRepository()
    provider = make_provider()

    mock_user = User(
        id=uuid4(),
        email="admin@example.com",
        is_active=True,
    )

    async def mock_require_provider_admin():
        return provider

    async def mock_require_provider_member():
        return provider

    app.dependency_overrides[get_provider_model_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[require_member] = lambda: None
    app.dependency_overrides[require_provider_admin] = mock_require_provider_admin
    app.dependency_overrides[require_provider_member] = mock_require_provider_member

    yield repo, provider, mock_user
    app.dependency_overrides.clear()


@pytest.fixture
def mock_member_dependencies():
    """Dependencies for member-only access (read-only)."""
    repo = MockProviderModelRepository()
    provider = make_provider()

    mock_user = User(
        id=uuid4(),
        email="member@example.com",
        is_active=True,
    )

    async def mock_require_provider_member():
        return provider

    app.dependency_overrides[get_provider_model_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_member] = lambda: None
    app.dependency_overrides[require_provider_member] = mock_require_provider_member

    yield repo, provider, mock_user
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_provider_model(mock_dependencies):
    repo, provider, user = mock_dependencies

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/organizations/{provider.organization_id}/providers/{provider.id}/models",
            json={
                "name": "GPT-4o",
                "model_identifier": "gpt-4o",
                "supports_streaming": True,
                "supports_tools": True,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "GPT-4o"
    assert data["model_identifier"] == "gpt-4o"
    assert data["supports_streaming"] is True
    assert data["supports_tools"] is True
    assert data["provider_id"] == str(provider.id)


@pytest.mark.asyncio
async def test_create_provider_model_duplicate(mock_dependencies):
    repo, provider, user = mock_dependencies

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(
            f"/api/v1/organizations/{provider.organization_id}/providers/{provider.id}/models",
            json={"name": "GPT-4o", "model_identifier": "gpt-4o"},
        )
        response = await ac.post(
            f"/api/v1/organizations/{provider.organization_id}/providers/{provider.id}/models",
            json={"name": "GPT-4o Again", "model_identifier": "gpt-4o"},
        )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_provider_models(mock_dependencies):
    repo, provider, user = mock_dependencies

    # Pre-seed two models
    for identifier in ("gpt-4o", "gpt-4-turbo"):
        model = ProviderModel(
            provider_id=provider.id,
            name=identifier.upper(),
            model_identifier=identifier,
            supports_streaming=False,
            supports_tools=False,
            supports_vision=False,
            supports_reasoning=False,
            is_active=True,
        )
        await repo.create(model)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/organizations/{provider.organization_id}/providers/{provider.id}/models",
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    identifiers = {m["model_identifier"] for m in data}
    assert identifiers == {"gpt-4o", "gpt-4-turbo"}


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_provider_model(mock_dependencies):
    repo, provider, user = mock_dependencies

    model = ProviderModel(
        provider_id=provider.id,
        name="Claude 3",
        model_identifier="claude-3-opus-20240229",
        supports_streaming=True,
        supports_tools=True,
        supports_vision=True,
        supports_reasoning=False,
        is_active=True,
    )
    model = await repo.create(model)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/providers/{provider.id}/models/{model.id}")

    assert response.status_code == 200
    assert response.json()["model_identifier"] == "claude-3-opus-20240229"


@pytest.mark.asyncio
async def test_get_provider_model_not_found(mock_dependencies):
    repo, provider, user = mock_dependencies

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(f"/api/v1/providers/{provider.id}/models/{uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_provider_model(mock_dependencies):
    repo, provider, user = mock_dependencies

    model = ProviderModel(
        provider_id=provider.id,
        name="Gemini Pro",
        model_identifier="gemini-1.5-pro",
        supports_streaming=False,
        supports_tools=False,
        supports_vision=False,
        supports_reasoning=False,
        is_active=True,
    )
    model = await repo.create(model)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            f"/api/v1/providers/{provider.id}/models/{model.id}",
            json={"supports_vision": True, "context_window": 1000000},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["supports_vision"] is True
    assert data["context_window"] == 1000000


@pytest.mark.asyncio
async def test_update_provider_model_duplicate_identifier(mock_dependencies):
    repo, provider, user = mock_dependencies

    # Create two models
    for identifier in ("model-a", "model-b"):
        m = ProviderModel(
            provider_id=provider.id,
            name=identifier,
            model_identifier=identifier,
            supports_streaming=False,
            supports_tools=False,
            supports_vision=False,
            supports_reasoning=False,
            is_active=True,
        )
        await repo.create(m)

    # Fetch model-a's id to try renaming it to model-b
    model_a = next(m for m in repo.models.values() if m.model_identifier == "model-a")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            f"/api/v1/providers/{provider.id}/models/{model_a.id}",
            json={"model_identifier": "model-b"},
        )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_provider_model(mock_dependencies):
    repo, provider, user = mock_dependencies

    model = ProviderModel(
        provider_id=provider.id,
        name="Groq Llama",
        model_identifier="llama-3-70b-8192",
        supports_streaming=True,
        supports_tools=False,
        supports_vision=False,
        supports_reasoning=False,
        is_active=True,
    )
    model = await repo.create(model)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(f"/api/v1/providers/{provider.id}/models/{model.id}")

    assert response.status_code == 204
    assert await repo.get_by_id(model.id) is None


@pytest.mark.asyncio
async def test_delete_provider_model_not_found(mock_dependencies):
    repo, provider, user = mock_dependencies

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.delete(f"/api/v1/providers/{provider.id}/models/{uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# AUTHORIZATION
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_member_cannot_create_model(mock_dependencies):
    """require_admin gate on POST: member override returns 403."""
    repo, provider, user = mock_dependencies

    from fastapi import HTTPException, status

    def forbid():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    app.dependency_overrides[require_admin] = forbid

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/organizations/{provider.organization_id}/providers/{provider.id}/models",
            json={"name": "X", "model_identifier": "x-model"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_member_can_list_models(mock_member_dependencies):
    """Members can list models via the org-scoped endpoint."""
    repo, provider, user = mock_member_dependencies

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            f"/api/v1/organizations/{provider.organization_id}/providers/{provider.id}/models",
        )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
