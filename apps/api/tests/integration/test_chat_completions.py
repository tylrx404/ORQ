import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
import httpx

from app.main import app
from app.api.dependencies import get_current_api_key, get_llm_gateway_service
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
def gateway_setup():
    org_id = uuid4()
    api_key_obj = ApiKey(
        id=uuid4(),
        organization_id=org_id,
        name="test-key",
        key_prefix="orq_sk_12345678",
        key_hash="hash",
        is_active=True,
    )
    provider = Provider(
        id=uuid4(),
        organization_id=org_id,
        name="OpenAI",
        provider_type=ProviderType.openai,
        api_key="sk-secret-key",
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

    yield {
        "org_id": org_id,
        "api_key": api_key_obj,
        "provider": provider,
        "model": model,
        "provider_repo": provider_repo,
        "model_repo": model_repo,
        "execution_log_repo": execution_log_repo,
    }


@pytest.mark.asyncio
async def test_chat_completion_success(gateway_setup):
    setup = gateway_setup
    mock_response_data = {
        "id": "chatcmpl-999",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {setup['provider'].api_key}"
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)

    gateway_service = LLMGatewayService(
        setup["provider_repo"],
        setup["model_repo"],
        setup["execution_log_repo"],
        http_client=http_client,
    )

    app.dependency_overrides[get_current_api_key] = lambda: setup["api_key"]
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": "orq_sk_valid_key"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "chatcmpl-999"
        assert data["choices"][0]["message"]["content"] == "Hello!"
        assert len(setup["execution_log_repo"].logs) == 1
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_chat_completion_invalid_api_key():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_completion_unknown_model(gateway_setup):
    setup = gateway_setup
    gateway_service = LLMGatewayService(
        setup["provider_repo"],
        setup["model_repo"],
        setup["execution_log_repo"],
    )

    app.dependency_overrides[get_current_api_key] = lambda: setup["api_key"]
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": "orq_sk_valid_key"},
                json={
                    "model": "unknown-model",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )
        assert response.status_code == 404
        assert "not configured or active" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_completion_provider_failure(gateway_setup):
    setup = gateway_setup

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Upstream provider error")

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)

    gateway_service = LLMGatewayService(
        setup["provider_repo"],
        setup["model_repo"],
        setup["execution_log_repo"],
        http_client=http_client,
    )

    app.dependency_overrides[get_current_api_key] = lambda: setup["api_key"]
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": "orq_sk_valid_key"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )
        assert response.status_code == 502
        assert "Upstream provider error" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_chat_completion_stream_success(gateway_setup):
    setup = gateway_setup

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='data: {"id":"1"}\n\n', headers={"content-type": "text/event-stream"})

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)

    gateway_service = LLMGatewayService(
        setup["provider_repo"],
        setup["model_repo"],
        setup["execution_log_repo"],
        http_client=http_client,
    )

    app.dependency_overrides[get_current_api_key] = lambda: setup["api_key"]
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": "orq_sk_valid_key"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                },
            )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()

