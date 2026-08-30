import pytest
import asyncio
import httpx
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

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
def streaming_setup():
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
async def test_successful_streaming(streaming_setup):
    setup = streaming_setup
    sse_body = (
        'data: {"id":"1","choices":[{"delta":{"content":"Hello"}}]}\n\n'
        'data: {"id":"1","choices":[{"delta":{"content":" world"}}]}\n\n'
        'data: [DONE]\n\n'
    )

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {setup['provider'].api_key}"
        return httpx.Response(200, text=sse_body, headers={"content-type": "text/event-stream"})

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
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        assert 'data: {"id":"1","choices":[{"delta":{"content":"Hello"}}]}' in content
        assert "data: [DONE]" in content
        assert len(setup["execution_log_repo"].logs) == 1
        assert setup["execution_log_repo"].logs[0].status_code == 200
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_provider_initial_error_before_stream(streaming_setup):
    setup = streaming_setup

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized key")

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
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
            )

        assert response.status_code == 401
        assert "Unauthorized key" in response.json()["detail"]
        assert len(setup["execution_log_repo"].logs) == 1
        assert setup["execution_log_repo"].logs[0].status_code == 401
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_usage_extraction_and_logging(streaming_setup):
    setup = streaming_setup
    sse_body = (
        'data: {"id":"1","choices":[{"delta":{"content":"Hi"}}]}\n\n'
        'data: {"id":"1","choices":[],"usage":{"prompt_tokens":12,"completion_tokens":8,"total_tokens":20}}\n\n'
        'data: [DONE]\n\n'
    )

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=sse_body, headers={"content-type": "text/event-stream"})

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
                    "messages": [{"role": "user", "content": "Hi"}],
                    "stream": True,
                },
            )

        assert response.status_code == 200
        assert len(setup["execution_log_repo"].logs) == 1
        log = setup["execution_log_repo"].logs[0]
        assert log.prompt_tokens == 12
        assert log.completion_tokens == 8
        assert log.total_tokens == 20
    finally:
        app.dependency_overrides.clear()
        await http_client.aclose()


@pytest.mark.asyncio
async def test_stream_failure_during_stream(streaming_setup):
    setup = streaming_setup

    class FailingStream:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","choices":[{"delta":{"content":"Part"}}]}\n\n'
            raise RuntimeError("Stream disconnected unexpectedly")

    class FailingClient:
        def stream(self, method, url, json=None, headers=None):
            return FailingStream()

    gateway_service = LLMGatewayService(
        setup["provider_repo"],
        setup["model_repo"],
        setup["execution_log_repo"],
        http_client=FailingClient(),
    )

    gen = await gateway_service.stream_chat_completion(
        organization_id=setup["org_id"],
        api_key_id=setup["api_key"].id,
        model_identifier="gpt-4o",
        messages=[{"role": "user", "content": "Hi"}],
    )

    chunks = []
    with pytest.raises(RuntimeError) as exc_info:
        async for chunk in gen:
            chunks.append(chunk)

    assert "Stream disconnected unexpectedly" in str(exc_info.value)
    assert len(chunks) == 1
    assert len(setup["execution_log_repo"].logs) == 1
    log = setup["execution_log_repo"].logs[0]
    assert log.status_code == 500
    assert "Stream disconnected" in log.error_message


@pytest.mark.asyncio
async def test_client_disconnect_cancellation(streaming_setup):
    setup = streaming_setup

    class SlowStream:
        def __init__(self):
            self.status_code = 200
            self.headers = {"content-type": "text/event-stream"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def aiter_lines(self):
            yield 'data: {"id":"1","choices":[{"delta":{"content":"Part 1"}}]}\n\n'
            raise asyncio.CancelledError("Client disconnected")

    class SlowClient:
        def stream(self, method, url, json=None, headers=None):
            return SlowStream()

    gateway_service = LLMGatewayService(
        setup["provider_repo"],
        setup["model_repo"],
        setup["execution_log_repo"],
        http_client=SlowClient(),
    )

    gen = await gateway_service.stream_chat_completion(
        organization_id=setup["org_id"],
        api_key_id=setup["api_key"].id,
        model_identifier="gpt-4o",
        messages=[{"role": "user", "content": "Hi"}],
    )

    with pytest.raises(asyncio.CancelledError):
        async for _ in gen:
            pass

    assert len(setup["execution_log_repo"].logs) == 1
    log = setup["execution_log_repo"].logs[0]
    assert "Client disconnected" in log.error_message
