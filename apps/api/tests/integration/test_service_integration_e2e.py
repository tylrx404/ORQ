"tests/integration/test_service_integration_e2e.py"""
from datetime import datetime, timedelta, timezone
import time
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


@pytest.mark.asyncio
async def test_api_key_failure_paths_and_org_isolation(real_db_session: AsyncSession):
    from app.core.jwt import create_access_token
    from app.models.organization_membership import MembershipRole, OrganizationMembership
    from app.models.user import User

    # 1. Setup User and Org A
    user = User(
        email=f"user-{uuid4()}@example.com",
        username=f"user_{uuid4().hex[:8]}",
        password_hash="fakehash",
        is_active=True,
    )
    real_db_session.add(user)
    await real_db_session.flush()

    org_a = Organization(name=f"org-a-{uuid4()}", slug=f"slug-a-{uuid4()}")
    org_b = Organization(name=f"org-b-{uuid4()}", slug=f"slug-b-{uuid4()}")
    real_db_session.add_all([org_a, org_b])
    await real_db_session.flush()

    # User is member/admin of org_a only
    membership_a = OrganizationMembership(
        organization_id=org_a.id,
        user_id=user.id,
        role=MembershipRole.admin,
    )
    real_db_session.add(membership_a)
    await real_db_session.flush()

    repo = ApiKeyRepository(real_db_session)
    service = ApiKeyService(repo)

    # Key belonging to org_a
    key_a, raw_key_a = await service.create_key(
        organization_id=org_a.id,
        name="key-org-a",
        user_id=user.id,
    )

    # Inactive/revoked key in org_a
    key_inactive, raw_key_inactive = await service.create_key(
        organization_id=org_a.id,
        name="key-inactive",
        user_id=user.id,
    )
    await service.update_key(key_inactive.id, is_active=False)

    # Key belonging to org_b
    key_b, raw_key_b = await service.create_key(
        organization_id=org_b.id,
        name="key-org-b",
        user_id=None,
    )
    await real_db_session.commit()

    user_token = create_access_token(str(user.id))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Invalid X-API-Key format / token -> 401
        res = await ac.post(
            "/api/v1/chat/completions",
            headers={"X-API-Key": "orq_sk_invalid_bogus_key"},
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert res.status_code == 401

        # 2. Inactive/revoked API key -> 401
        res = await ac.post(
            "/api/v1/chat/completions",
            headers={"X-API-Key": raw_key_inactive},
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert res.status_code == 401

        # 3. User with Org A membership trying to access/modify Org B's API key -> 404 (not in org)
        res = await ac.get(
            f"/api/v1/api-keys/{key_b.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_missing_provider_and_missing_model_gateway_errors(real_db_session: AsyncSession):
    # Org 1: Has no active provider configured
    org_no_provider = Organization(name=f"test-org-np-{uuid4()}", slug=f"test-slug-np-{uuid4()}")
    real_db_session.add(org_no_provider)
    await real_db_session.flush()

    repo = ApiKeyRepository(real_db_session)
    api_key_service = ApiKeyService(repo)
    _, raw_key_no_provider = await api_key_service.create_key(
        organization_id=org_no_provider.id,
        name="key-no-provider",
        user_id=None,
    )

    # Org 2: Has an active provider, but the requested model is missing/unregistered
    org_with_provider = Organization(name=f"test-org-wp-{uuid4()}", slug=f"test-slug-wp-{uuid4()}")
    real_db_session.add(org_with_provider)
    await real_db_session.flush()

    provider = Provider(
        organization_id=org_with_provider.id,
        name="OpenAI Provider",
        provider_type=ProviderType.openai,
        api_key="sk-real-mock-key",
        is_active=True,
    )
    real_db_session.add(provider)
    await real_db_session.flush()

    # Register only model "known-model"
    model = ProviderModel(
        provider_id=provider.id,
        name="Known Model",
        model_identifier="known-model",
        is_active=True,
    )
    real_db_session.add(model)
    await real_db_session.flush()

    _, raw_key_with_provider = await api_key_service.create_key(
        organization_id=org_with_provider.id,
        name="key-with-provider",
        user_id=None,
    )
    await real_db_session.commit()

    e_repo = ExecutionLogRepository(real_db_session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Case 1: Organization has no active provider -> HTTP 404
        res1 = await ac.post(
            "/api/v1/chat/completions",
            headers={"X-API-Key": raw_key_no_provider},
            json={"model": "any-model", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert res1.status_code == 404
        assert "no active provider found" in res1.json().get("detail", "").lower()

        # Case 2: Organization has active provider, but requested model is missing -> HTTP 404
        res2 = await ac.post(
            "/api/v1/chat/completions",
            headers={"X-API-Key": raw_key_with_provider},
            json={"model": "missing-unregistered-model", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert res2.status_code == 404
        assert "not configured or active" in res2.json().get("detail", "").lower()

    # Verify execution logging in PostgreSQL executions table
    logs_np = await e_repo.list_by_organization(org_no_provider.id)
    assert len(logs_np) == 1
    assert logs_np[0].status_code == 404
    assert logs_np[0].model_name == "any-model"

    logs_wp = await e_repo.list_by_organization(org_with_provider.id)
    assert len(logs_wp) == 1
    assert logs_wp[0].status_code == 404
    assert logs_wp[0].model_name == "missing-unregistered-model"


@pytest.mark.asyncio
async def test_upstream_failure_and_quota_rollback_and_logging(real_db_session: AsyncSession):
    org = Organization(name=f"test-org-{uuid4()}", slug=f"test-slug-{uuid4()}")
    real_db_session.add(org)
    await real_db_session.flush()

    # Quota with request_limit = 1
    quota = OrganizationQuota(
        organization_id=org.id,
        request_limit=1,
        token_limit=1000,
        requests_used=0,
        tokens_used=0,
        reset_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    real_db_session.add(quota)

    provider = Provider(
        organization_id=org.id,
        name="Mock Failing Provider",
        provider_type=ProviderType.openai,
        api_key="sk-failing",
        is_active=True,
    )
    real_db_session.add(provider)
    await real_db_session.flush()

    model = ProviderModel(
        provider_id=provider.id,
        name="Failing Model",
        model_identifier="failing-model",
        is_active=True,
    )
    real_db_session.add(model)
    await real_db_session.flush()

    repo = ApiKeyRepository(real_db_session)
    api_key_service = ApiKeyService(repo)
    key_record, raw_key = await api_key_service.create_key(
        organization_id=org.id,
        name="test-key",
        user_id=None,
    )
    await real_db_session.commit()

    # Upstream returns 502 Bad Gateway
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Upstream provider down")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    p_repo = ProviderRepository(real_db_session)
    m_repo = ProviderModelRepository(real_db_session)
    e_repo = ExecutionLogRepository(real_db_session)
    gateway_service = LLMGatewayService(p_repo, m_repo, e_repo, http_client=mock_client)

    from app.api.dependencies import get_llm_gateway_service, get_organization_quota_service
    # Provide the real quota service hooked to DB for the API call
    q_service_real = OrganizationQuotaService(OrganizationQuotaRepository(real_db_session))
    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service
    app.dependency_overrides[get_organization_quota_service] = lambda: q_service_real

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": raw_key},
                json={"model": "failing-model", "messages": [{"role": "user", "content": "hi"}]},
            )

        assert res.status_code == 502

        # Verify failed execution logging in DB
        logs = await e_repo.list_by_organization(org.id)
        assert len(logs) >= 1
        assert logs[0].status_code == 502
        assert "Upstream provider down" in (logs[0].error_message or "")

        # Reload OrganizationQuota from PostgreSQL with a fresh session and assert requests_used == 0
        async with AsyncSessionLocal() as verify_session:
            v_repo = OrganizationQuotaRepository(verify_session)
            db_quota = await v_repo.get_by_organization(org.id)
            assert db_quota is not None
            assert db_quota.requests_used == 0

        # Behavioral check: another request is still allowed since quota was rolled back
        allowed = await q_service_real.check_and_increment_request_quota(org.id)
        assert allowed is True
    finally:
        app.dependency_overrides.pop(get_llm_gateway_service, None)
        app.dependency_overrides.pop(get_organization_quota_service, None)
        await mock_client.aclose()


@pytest.mark.asyncio
async def test_rate_limit_and_quota_rejection_e2e(real_db_session: AsyncSession, real_redis_client):
    org = Organization(name=f"test-org-{uuid4()}", slug=f"test-slug-{uuid4()}")
    real_db_session.add(org)
    await real_db_session.flush()

    # Quota with request_limit = 1, token_limit = 10
    quota = OrganizationQuota(
        organization_id=org.id,
        request_limit=1,
        token_limit=10,
        requests_used=0,
        tokens_used=0,
        reset_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    real_db_session.add(quota)

    provider = Provider(
        organization_id=org.id,
        name="Mock Provider",
        provider_type=ProviderType.openai,
        api_key="sk-mock",
        is_active=True,
    )
    real_db_session.add(provider)
    await real_db_session.flush()

    model = ProviderModel(
        provider_id=provider.id,
        name="Mock Model",
        model_identifier="mock-model",
        is_active=True,
    )
    real_db_session.add(model)
    await real_db_session.flush()

    repo = ApiKeyRepository(real_db_session)
    api_key_service = ApiKeyService(repo)
    _, raw_key = await api_key_service.create_key(
        organization_id=org.id,
        name="test-key",
        user_id=None,
    )
    await real_db_session.commit()

    # Mock gateway to return successful responses
    mock_resp = {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": 12345,
        "model": "mock-model",
        "choices": [{"message": {"role": "assistant", "content": "hi"}}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
    }

    mock_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=mock_resp))
    )
    p_repo = ProviderRepository(real_db_session)
    m_repo = ProviderModelRepository(real_db_session)
    e_repo = ExecutionLogRepository(real_db_session)
    gateway_service = LLMGatewayService(p_repo, m_repo, e_repo, http_client=mock_client)

    q_repo = OrganizationQuotaRepository(real_db_session)
    q_service = OrganizationQuotaService(q_repo)
    rl_service = RateLimitService(real_redis_client)

    from app.api.dependencies import (
        get_llm_gateway_service,
        get_organization_quota_service,
        get_rate_limit_service,
    )

    app.dependency_overrides[get_llm_gateway_service] = lambda: gateway_service
    app.dependency_overrides[get_organization_quota_service] = lambda: q_service
    app.dependency_overrides[get_rate_limit_service] = lambda: rl_service

    redis_key = f"rate_limit:org:{org.id}:rpm"
    try:
        # Pre-fill Redis ZSET to simulate rate limit exceeded (limit is settings.RATE_LIMIT_RPM)
        from app.core.config import settings
        now_ms = int(time.time() * 1000)
        pipeline = real_redis_client.pipeline()
        for i in range(settings.RATE_LIMIT_RPM + 1):
            pipeline.zadd(redis_key, {f"{now_ms}:{i}": now_ms})
        await pipeline.execute()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Rate-limit rejection through POST /api/v1/chat/completions
            res_rl = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": raw_key},
                json={"model": "mock-model", "messages": [{"role": "user", "content": "hi"}]},
            )
            assert res_rl.status_code == 429
            rl_data = res_rl.json()
            assert rl_data["error"]["type"] == "rate_limit_error"
            assert "X-RateLimit-Limit" in res_rl.headers
            assert "X-RateLimit-Remaining" in res_rl.headers
            assert res_rl.headers["X-RateLimit-Remaining"] == "0"

            # Verify rate-limit rejection did NOT consume request quota in PostgreSQL
            async with AsyncSessionLocal() as check_session:
                q_check_repo = OrganizationQuotaRepository(check_session)
                q_db = await q_check_repo.get_by_organization(org.id)
                assert q_db is not None
                assert q_db.requests_used == 0

            # Clear Redis rate limit key to allow quota testing
            await real_redis_client.delete(redis_key)

            # 2. First request succeeds and consumes request quota (limit=1, requests_used becomes 1)
            res_ok = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": raw_key},
                json={"model": "mock-model", "messages": [{"role": "user", "content": "hi"}]},
            )
            assert res_ok.status_code == 200

            # 3. Second request fails with Request Quota rejection (limit=1 reached) -> HTTP 429 insufficient_quota
            res_quota = await ac.post(
                "/api/v1/chat/completions",
                headers={"X-API-Key": raw_key},
                json={"model": "mock-model", "messages": [{"role": "user", "content": "hi"}]},
            )
            assert res_quota.status_code == 429
            quota_data = res_quota.json()
            assert quota_data["error"]["type"] == "insufficient_quota"

            # 4. Token quota rejection verification:
            # Current quota: tokens_used is 5 (from first request). token_limit is 10.
            # An increment of 6 tokens will exceed token_limit (5 + 6 > 10)
            token_allowed = await q_service.check_and_increment_token_quota(org.id, tokens=6)
            assert token_allowed is False

    finally:
        app.dependency_overrides.pop(get_llm_gateway_service, None)
        app.dependency_overrides.pop(get_organization_quota_service, None)
        app.dependency_overrides.pop(get_rate_limit_service, None)
        await mock_client.aclose()
        await real_redis_client.delete(redis_key)
