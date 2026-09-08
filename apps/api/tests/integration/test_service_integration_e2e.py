"tests/integration/test_service_integration_e2e.py"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine
from app.main import app
from app.models.api_key import ApiKey
from app.models.execution_log import ExecutionLog
from app.models.organization import Organization
from app.models.organization_quota import OrganizationQuota
from app.models.provider import Provider, ProviderType
from app.models.provider_model import ProviderModel

from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.organization_quota_repository import OrganizationQuotaRepository
from app.repositories.provider_model_repository import ProviderModelRepository
from app.repositories.provider_repository import ProviderRepository
from app.services.api_key import ApiKeyService
from app.services.llm_gateway import LLMGatewayService
from app.services.organization_quota import OrganizationQuotaService
from app.services.rate_limit import RateLimitService
from app.services.usage import UsageService


@pytest.fixture
async def real_db_session():
    await engine.dispose()
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def real_redis_client():
    from redis.asyncio import Redis
    from app.core.config import settings
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    await client.ping()
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_fastapi_connects_to_postgres_and_redis(real_db_session: AsyncSession, real_redis_client):
    result = await real_db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1

    pong = await real_redis_client.ping()
    assert pong is True

    # Connect the global redis_manager so the /ready endpoint can use it
    from app.redis.client import redis_manager
    if redis_manager.redis_client is None:
        await redis_manager.connect()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/ready/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"] == "ok"
    assert data["redis"] == "ok"


@pytest.mark.asyncio
async def test_api_key_auth_against_real_database(real_db_session: AsyncSession):
    org = Organization(name=f"test-org-{uuid4()}", slug=f"test-slug-{uuid4()}")
    real_db_session.add(org)
    await real_db_session.flush()

    repo = ApiKeyRepository(real_db_session)
    service = ApiKeyService(repo)

    key_record, raw_key = await service.create_key(
        organization_id=org.id,
        name="integration-test-key",
        user_id=None,
    )
    assert raw_key.startswith("orq_sk_")

    validated_key = await service.validate_key(raw_key)
    assert validated_key.id == key_record.id
    assert validated_key.organization_id == org.id

    with pytest.raises(Exception):
        await service.validate_key("orq_sk_invalid_bogus_key")


@pytest.mark.asyncio
async def test_org_provider_model_lookup_real_db(real_db_session: AsyncSession):
    org = Organization(name=f"test-org-{uuid4()}", slug=f"test-slug-{uuid4()}")
    real_db_session.add(org)
    await real_db_session.flush()

    provider = Provider(
        organization_id=org.id,
        name="Integration OpenAI",
        provider_type=ProviderType.openai,
        api_key="sk-test-secret",
        is_active=True,
    )
    real_db_session.add(provider)
    await real_db_session.flush()

    model = ProviderModel(
        provider_id=provider.id,
        name="GPT-4o Test",
        model_identifier="gpt-4o",
        is_active=True,
    )
    real_db_session.add(model)
    await real_db_session.flush()

    p_repo = ProviderRepository(real_db_session)
    m_repo = ProviderModelRepository(real_db_session)
    e_repo = ExecutionLogRepository(real_db_session)

    gateway = LLMGatewayService(p_repo, m_repo, e_repo)
    resolved_p, resolved_m = await gateway.resolve_provider_and_model(org.id, "gpt-4o")

    assert resolved_p.id == provider.id
    assert resolved_m.id == model.id


@pytest.mark.asyncio
async def test_rate_limiting_real_redis(real_redis_client):
    org_id = uuid4()
    service = RateLimitService(real_redis_client)

    allowed, headers, _ = await service.check_rate_limit(organization_id=org_id, limit=2)
    assert allowed is True
    assert headers["X-RateLimit-Remaining"] == "1"

    allowed2, headers2, _ = await service.check_rate_limit(organization_id=org_id, limit=2)
    assert allowed2 is True
    assert headers2["X-RateLimit-Remaining"] == "0"

    allowed3, headers3, err = await service.check_rate_limit(organization_id=org_id, limit=2)
    assert allowed3 is False
    assert headers3["X-RateLimit-Remaining"] == "0"
    assert err["error"]["type"] == "rate_limit_error"


    await real_redis_client.delete(f"rate_limit:org:{org_id}:rpm")


@pytest.mark.asyncio
async def test_request_and_token_quotas_real_db(real_db_session: AsyncSession):
    org = Organization(name=f"test-org-{uuid4()}", slug=f"test-slug-{uuid4()}")
    real_db_session.add(org)
    await real_db_session.flush()

    quota = OrganizationQuota(
        organization_id=org.id,
        request_limit=2,
        token_limit=100,
        requests_used=0,
        tokens_used=0,
        reset_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    real_db_session.add(quota)
    await real_db_session.commit()

    repo = OrganizationQuotaRepository(real_db_session)
    service = OrganizationQuotaService(repo)

    assert await service.check_and_increment_request_quota(org.id) is True
    assert await service.check_and_increment_request_quota(org.id) is True
    assert await service.check_and_increment_request_quota(org.id) is False

    await service.rollback_request_quota(org.id)
    assert await service.check_and_increment_request_quota(org.id) is True
    assert await service.check_and_increment_request_quota(org.id) is False

    assert await service.check_and_increment_token_quota(org.id, 60) is True
    assert await service.check_and_increment_token_quota(org.id, 50) is False
    assert await service.check_and_increment_token_quota(org.id, 40) is True


@pytest.mark.asyncio
async def test_usage_analytics_reads_real_db(real_db_session: AsyncSession):
    org = Organization(name=f"test-org-{uuid4()}", slug=f"test-slug-{uuid4()}")
    real_db_session.add(org)
    await real_db_session.flush()

    now = datetime.now(timezone.utc)
    log = ExecutionLog(
        organization_id=org.id,
        model_name="gpt-4o",
        status_code=200,
        prompt_tokens=12,
        completion_tokens=18,
        total_tokens=30,
        latency_ms=150,
        created_at=now - timedelta(minutes=5),
    )
    real_db_session.add(log)
    await real_db_session.commit()

    repo = ExecutionLogRepository(real_db_session)
    service = UsageService(repo)

    summary = await service.get_organization_usage(
        org.id,
        start=now - timedelta(hours=1),
        end=now + timedelta(hours=1),
    )

    assert summary["total_requests"] == 1
    assert summary["successful_requests"] == 1
    assert summary["total_tokens"] == 30
    assert summary["prompt_tokens"] == 12
    assert summary["completion_tokens"] == 18


@pytest.mark.asyncio
async def test_llm_gateway_execution_logging_local_mock_provider(real_db_session: AsyncSession):
    org = Organization(name=f"test-org-{uuid4()}", slug=f"test-slug-{uuid4()}")
    real_db_session.add(org)
    await real_db_session.flush()

    provider = Provider(
        organization_id=org.id,
        name="Mock Provider",
        provider_type=ProviderType.openai,
        api_key="sk-local-mock",
        is_active=True,
    )
    real_db_session.add(provider)
    await real_db_session.flush()

    model = ProviderModel(
        provider_id=provider.id,
        name="Mock Model",
        model_identifier="mock-gpt-4o",
        is_active=True,
    )
    real_db_session.add(model)
    await real_db_session.flush()

    mock_response = {
        "id": "chatcmpl-local-mock-1",
        "object": "chat.completion",
        "created": 123456789,
        "model": "mock-gpt-4o",
        "choices": [{"message": {"role": "assistant", "content": "Hello from mock!"}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20},
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response)


    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)

    p_repo = ProviderRepository(real_db_session)
    m_repo = ProviderModelRepository(real_db_session)
    e_repo = ExecutionLogRepository(real_db_session)

    gateway = LLMGatewayService(p_repo, m_repo, e_repo, http_client=http_client)

    try:
        resp_json, log = await gateway.execute_chat_completion(
            organization_id=org.id,
            api_key_id=None,
            model_identifier="mock-gpt-4o",
            messages=[{"role": "user", "content": "hi"}],
        )

        assert resp_json["id"] == "chatcmpl-local-mock-1"
        assert log is not None
        assert log.status_code == 200
        assert log.total_tokens == 20

        saved_logs = await e_repo.list_by_organization(org.id)
        assert len(saved_logs) >= 1
        assert saved_logs[0].model_name == "mock-gpt-4o"
        assert saved_logs[0].total_tokens == 20
    finally:
        await http_client.aclose()
