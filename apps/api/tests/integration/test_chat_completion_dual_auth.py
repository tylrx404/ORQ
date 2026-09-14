"""
Focused tests for the dual-auth chat-completion dependency.

Scenarios covered:
  1. Valid API key -> authenticated (api_key_id populated)
  2. Valid JWT + org member -> authenticated (api_key_id is None)
  3. JWT but user not a member of the org -> 403
  4. JWT but missing X-Organization-Id header -> 400
  5. JWT but invalid X-Organization-Id (not a UUID) -> 400
  6. No auth at all -> 401
  7. Invalid API key -> 401 (backward compat)
  8. JWT execution has api_key_id=None (verified via execution log)
"""

import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

import httpx

from app.main import app
from app.api.dependencies import (
    ChatCompletionAuthContext,
    get_chat_completion_auth,
    get_llm_gateway_service,
)
from app.models.api_key import ApiKey
from app.models.provider import Provider, ProviderType
from app.models.provider_model import ProviderModel
from app.services.llm_gateway import LLMGatewayService


class MockProviderRepo:
    def __init__(self, providers=None):
        self.providers = providers or []

    async def list_by_organization(self, org_id):
        return [p for p in self.providers if p.organization_id == org_id]


class MockModelRepo:
    def __init__(self, models=None):
        self.models = models or []

    async def get_duplicate(self, provider_id, model_identifier):
        for m in self.models:
            if m.provider_id == provider_id and m.model_identifier == model_identifier:
                return m
        return None


class MockExecutionLogRepo:
    def __init__(self):
        self.logs = []

    async def create(self, execution_log):
        execution_log.id = uuid4()
        self.logs.append(execution_log)
        return execution_log


@pytest.fixture
def gateway_objects():
    org_id = uuid4()
    provider = Provider(
        id=uuid4(),
        organization_id=org_id,
        name="OpenAI",
        provider_type=ProviderType.openai,
        api_key="sk-secret",
        is_active=True,
    )
    model = ProviderModel(
        id=uuid4(),
        provider_id=provider.id,
        name="GPT-4o",
        model_identifier="gpt-4o",
        is_active=True,
    )
    provider_repo = MockProviderRepo([provider])
    model_repo = MockModelRepo([model])
    execution_log_repo = MockExecutionLogRepo()
    return {
        "org_id": org_id,
        "provider": provider,
        "model": model,
        "provider_repo": provider_repo,
        "model_repo": model_repo,
        "execution_log_repo": execution_log_repo,
    }


@pytest.fixture
def mock_gateway_service(gateway_objects):
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1234567890,
                "model": "gpt-4o",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Hi!"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            },
        )

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    service = LLMGatewayService(
        gateway_objects["provider_repo"],
        gateway_objects["model_repo"],
        gateway_objects["execution_log_repo"],
        http_client=http_client,
    )
    return service, gateway_objects["execution_log_repo"], http_client


@pytest.mark.asyncio
async def test_valid_api_key_auth_succeeds(gateway_objects, mock_gateway_service):
    """Valid X-API-Key: request succeeds; api_key_id is populated in auth context."""
    org_id = gateway_objects["org_id"]
    api_key_id = uuid4()
    auth_ctx = ChatCompletionAuthContext(organization_id=org_id, api_key_id=api_key_id)

    gateway_service, _, http_client = mock_gateway_service
    app.dependency_overrides[get_chat_completion_auth] = lambda: auth_ctx
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": "orq_sk_valid"},
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 200
        assert auth_ctx.api_key_id == api_key_id
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_valid_jwt_member_auth_succeeds(gateway_objects, mock_gateway_service):
    """Valid JWT + org member: request succeeds; api_key_id is None in auth context."""
    org_id = gateway_objects["org_id"]
    auth_ctx = ChatCompletionAuthContext(organization_id=org_id, api_key_id=None)

    gateway_service, _, http_client = mock_gateway_service
    app.dependency_overrides[get_chat_completion_auth] = lambda: auth_ctx
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer some-jwt-token",
                    "X-Organization-Id": str(org_id),
                },
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 200
        assert auth_ctx.api_key_id is None
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_jwt_execution_api_key_id_is_none(gateway_objects, mock_gateway_service):
    """JWT-authenticated execution must write api_key_id=None to execution log."""
    org_id = gateway_objects["org_id"]
    auth_ctx = ChatCompletionAuthContext(organization_id=org_id, api_key_id=None)

    gateway_service, execution_log_repo, http_client = mock_gateway_service
    app.dependency_overrides[get_chat_completion_auth] = lambda: auth_ctx
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer some-jwt-token",
                    "X-Organization-Id": str(org_id),
                },
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 200
        assert len(execution_log_repo.logs) == 1
        log = execution_log_repo.logs[0]
        assert log.api_key_id is None
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_no_auth_returns_401():
    """Requests without any authentication must be rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_returns_401():
    """Invalid X-API-Key must return 401. Uses dep override to avoid DB."""
    from fastapi import HTTPException

    async def fake_auth_invalid_key():
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    app.dependency_overrides[get_chat_completion_auth] = fake_auth_invalid_key
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": "orq_sk_completely_invalid"},
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_jwt_user_not_in_org_returns_403():
    """Authenticated JWT user who is NOT a member of the requested org must be rejected."""
    from fastapi import HTTPException

    async def fake_auth():
        raise HTTPException(status_code=403, detail="You are not a member of the specified organization.")

    app.dependency_overrides[get_chat_completion_auth] = fake_auth

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer valid-jwt-but-not-member",
                    "X-Organization-Id": str(uuid4()),
                },
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_jwt_missing_org_id_header_returns_400():
    """JWT request without X-Organization-Id header must return 400."""
    from fastapi import HTTPException

    async def fake_auth():
        raise HTTPException(
            status_code=400,
            detail="X-Organization-Id header is required for JWT-authenticated requests.",
        )

    app.dependency_overrides[get_chat_completion_auth] = fake_auth

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={"Authorization": "Bearer some-jwt-token"},
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 400
        assert "X-Organization-Id" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_jwt_invalid_org_id_uuid_returns_400():
    """JWT request with non-UUID X-Organization-Id must return 400."""
    from fastapi import HTTPException

    async def fake_auth():
        raise HTTPException(
            status_code=400,
            detail="X-Organization-Id header must be a valid UUID.",
        )

    app.dependency_overrides[get_chat_completion_auth] = fake_auth

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={
                    "Authorization": "Bearer some-jwt-token",
                    "X-Organization-Id": "not-a-uuid",
                },
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}]},
            )
        assert response.status_code == 400
        assert "valid UUID" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

