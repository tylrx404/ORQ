import pytest
import httpx
from uuid import UUID, uuid4
from datetime import datetime, timezone

from app.models.provider import Provider, ProviderType
from app.models.provider_model import ProviderModel
from app.models.execution_log import ExecutionLog
from app.services.llm_gateway import (
    LLMGatewayService,
    ProviderNotFoundError,
    ModelNotFoundError,
    ProviderExecutionError,
    LLMGatewayError,
)


class MockProviderRepo:
    def __init__(self, providers: list[Provider] | None = None):
        self.providers = providers or []

    async def list_by_organization(self, organization_id: UUID) -> list[Provider]:
        return [p for p in self.providers if p.organization_id == organization_id]


class MockModelRepo:
    def __init__(self, models: list[ProviderModel] | None = None):
        self.models = models or []

    async def get_duplicate(self, provider_id: UUID, model_identifier: str) -> ProviderModel | None:
        for m in self.models:
            if m.provider_id == provider_id and m.model_identifier == model_identifier:
                return m
        return None


class MockExecutionLogRepo:
    def __init__(self):
        self.logs: list[ExecutionLog] = []

    async def create(self, execution_log: ExecutionLog) -> ExecutionLog:
        execution_log.id = uuid4()
        execution_log.created_at = datetime.now(timezone.utc)
        self.logs.append(execution_log)
        return execution_log


@pytest.mark.asyncio
async def test_resolve_provider_and_model_success():
    org_id = uuid4()
    provider = Provider(
        id=uuid4(),
        organization_id=org_id,
        name="OpenAI Provider",
        provider_type=ProviderType.openai,
        api_key="sk-test",
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
    log_repo = MockExecutionLogRepo()

    service = LLMGatewayService(provider_repo, model_repo, log_repo)
    res_provider, res_model = await service.resolve_provider_and_model(org_id, "gpt-4o")

    assert res_provider.id == provider.id
    assert res_model is not None
    assert res_model.id == model.id


@pytest.mark.asyncio
async def test_resolve_provider_and_model_no_active_provider():
    org_id = uuid4()
    provider_repo = MockProviderRepo([])
    model_repo = MockModelRepo([])
    log_repo = MockExecutionLogRepo()

    service = LLMGatewayService(provider_repo, model_repo, log_repo)
    with pytest.raises(ProviderNotFoundError):
        await service.resolve_provider_and_model(org_id, "gpt-4o")


@pytest.mark.asyncio
async def test_resolve_provider_and_model_inactive_provider():
    org_id = uuid4()
    inactive_provider = Provider(
        id=uuid4(),
        organization_id=org_id,
        name="Inactive OpenAI",
        provider_type=ProviderType.openai,
        api_key="sk-test",
        is_active=False,
    )
    model = ProviderModel(
        id=uuid4(),
        provider_id=inactive_provider.id,
        name="GPT-4o",
        model_identifier="gpt-4o",
        is_active=True,
    )

    provider_repo = MockProviderRepo([inactive_provider])
    model_repo = MockModelRepo([model])
    log_repo = MockExecutionLogRepo()

    service = LLMGatewayService(provider_repo, model_repo, log_repo)
    with pytest.raises(ProviderNotFoundError):
        await service.resolve_provider_and_model(org_id, "gpt-4o")


@pytest.mark.asyncio
async def test_resolve_provider_and_model_inactive_model():
    org_id = uuid4()
    provider = Provider(
        id=uuid4(),
        organization_id=org_id,
        name="OpenAI Provider",
        provider_type=ProviderType.openai,
        api_key="sk-test",
        is_active=True,
    )
    inactive_model = ProviderModel(
        id=uuid4(),
        provider_id=provider.id,
        name="GPT-4o",
        model_identifier="gpt-4o",
        is_active=False,
    )

    provider_repo = MockProviderRepo([provider])
    model_repo = MockModelRepo([inactive_model])
    log_repo = MockExecutionLogRepo()

    service = LLMGatewayService(provider_repo, model_repo, log_repo)
    with pytest.raises(ModelNotFoundError):
        await service.resolve_provider_and_model(org_id, "gpt-4o")


@pytest.mark.asyncio
async def test_resolve_provider_and_model_mismatched_organization():
    org_id_1 = uuid4()
    org_id_2 = uuid4()
    provider = Provider(
        id=uuid4(),
        organization_id=org_id_1,
        name="Org1 Provider",
        provider_type=ProviderType.openai,
        api_key="sk-test",
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
    log_repo = MockExecutionLogRepo()

    service = LLMGatewayService(provider_repo, model_repo, log_repo)
    with pytest.raises(ProviderNotFoundError):
        await service.resolve_provider_and_model(org_id_2, "gpt-4o")


@pytest.mark.asyncio
async def test_execute_chat_completion_success_mock_httpx():
    org_id = uuid4()
    api_key_id = uuid4()
    provider = Provider(
        id=uuid4(),
        organization_id=org_id,
        name="OpenAI Provider",
        provider_type=ProviderType.openai,
        api_key="sk-test",
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
    log_repo = MockExecutionLogRepo()

    mock_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677858288,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello world!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test"
        return httpx.Response(200, json=mock_response)

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        service = LLMGatewayService(provider_repo, model_repo, log_repo, http_client=http_client)
        resp_json, log = await service.execute_chat_completion(
            organization_id=org_id,
            api_key_id=api_key_id,
            model_identifier="gpt-4o",
            messages=[{"role": "user", "content": "Hi"}],
        )

    assert resp_json["id"] == "chatcmpl-123"
    assert log.status_code == 200
    assert log.prompt_tokens == 10
    assert log.completion_tokens == 5
    assert log.total_tokens == 15
    assert len(log_repo.logs) == 1


@pytest.mark.asyncio
async def test_execute_chat_completion_provider_error():
    org_id = uuid4()
    provider = Provider(
        id=uuid4(),
        organization_id=org_id,
        name="OpenAI Provider",
        provider_type=ProviderType.openai,
        api_key="sk-test",
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
    log_repo = MockExecutionLogRepo()

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized API key")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        service = LLMGatewayService(provider_repo, model_repo, log_repo, http_client=http_client)
        with pytest.raises(ProviderExecutionError) as exc_info:
            await service.execute_chat_completion(
                organization_id=org_id,
                api_key_id=None,
                model_identifier="gpt-4o",
                messages=[{"role": "user", "content": "Hi"}],
            )

    assert exc_info.value.status_code == 401
    assert len(log_repo.logs) == 1
    assert log_repo.logs[0].status_code == 401
    assert "Unauthorized" in log_repo.logs[0].error_message


@pytest.mark.asyncio
async def test_execute_chat_completion_streaming_rejected():
    org_id = uuid4()
    service = LLMGatewayService(MockProviderRepo([]), MockModelRepo([]), MockExecutionLogRepo())
    with pytest.raises(LLMGatewayError) as exc_info:
        await service.execute_chat_completion(
            organization_id=org_id,
            api_key_id=None,
            model_identifier="gpt-4o",
            messages=[{"role": "user", "content": "Hi"}],
            stream=True,
        )

    assert "Use stream_chat_completion" in str(exc_info.value)
