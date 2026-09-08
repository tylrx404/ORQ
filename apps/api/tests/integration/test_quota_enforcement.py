"tests/integration/test_quota_enforcement.py"""
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    get_current_api_key,
    get_llm_gateway_service,
    get_organization_quota_service,
)
from app.main import app
from app.models.api_key import ApiKey
from app.models.organization_quota import OrganizationQuota
from app.services.organization_quota import OrganizationQuotaService

def _future(days: int = 30) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)

def _past(days: int = 5) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


class InMemoryQuotaRepo:
    def __init__(self, quota: OrganizationQuota | None = None):
        self.quota = quota
        self.lock = asyncio.Lock()

    async def get_by_organization(self, organization_id):
        return self.quota

    async def try_increment_request(self, organization_id, cycle_days: int = 30) -> bool:
        async with self.lock:
            await asyncio.sleep(0.001)
            if self.quota is None:
                return True

            now = datetime.now(timezone.utc)
            reset_at = self.quota.reset_at
            if reset_at.tzinfo is None:
                reset_at = reset_at.replace(tzinfo=timezone.utc)

            if now >= reset_at:
                while now >= reset_at:
                    reset_at = reset_at + timedelta(days=cycle_days)
                self.quota.reset_at = reset_at
                self.quota.requests_used = 0
                self.quota.tokens_used = 0

            if self.quota.request_limit is not None and self.quota.requests_used >= self.quota.request_limit:
                return False

            self.quota.requests_used += 1
            return True


@pytest.fixture
def quota_enforcement_setup():
    org_id = uuid4()
    api_key = ApiKey(
        id=uuid4(),
        organization_id=org_id,
        name="test-key",
        key_prefix="orq_sk_test",
        key_hash="hash",
        is_active=True,
    )

    class MockGateway:
        async def execute_chat_completion(self, *args, **kwargs):
            return {"id": "chatcmpl-test", "choices": [{"message": {"content": "ok"}}]}, None

    app.dependency_overrides[get_current_api_key] = lambda: api_key
    app.dependency_overrides[get_llm_gateway_service] = lambda: MockGateway()

    yield {"org_id": org_id, "api_key": api_key}

    app.dependency_overrides.pop(get_current_api_key, None)
    app.dependency_overrides.pop(get_llm_gateway_service, None)
    app.dependency_overrides.pop(get_organization_quota_service, None)


@pytest.mark.asyncio
async def test_quota_under_limit(quota_enforcement_setup):
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=10,
        requests_used=3,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200
    assert quota.requests_used == 4


@pytest.mark.asyncio
async def test_quota_exact_limit(quota_enforcement_setup):
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=5,
        requests_used=4,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp1 = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp1.status_code == 200
        assert quota.requests_used == 5

        resp2 = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp2.status_code == 429
        assert resp2.json() == {
            "error": {
                "message": "You have exceeded your organization's monthly usage quota. Please check your plan details.",
                "type": "insufficient_quota",
                "code": 429,
            }
        }
        assert quota.requests_used == 5


@pytest.mark.asyncio
async def test_quota_over_limit_error_format(quota_enforcement_setup):
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=10,
        requests_used=10,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 429
    data = resp.json()
    assert data["error"]["type"] == "insufficient_quota"
    assert data["error"]["code"] == 429
    assert "You have exceeded your organization's monthly usage quota" in data["error"]["message"]


@pytest.mark.asyncio
async def test_quota_unlimited_null_limit(quota_enforcement_setup):
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=None,
        requests_used=9999,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200
    assert quota.requests_used == 10000


@pytest.mark.asyncio
async def test_quota_unlimited_no_quota_configured(quota_enforcement_setup):
    repo = InMemoryQuotaRepo(None)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_quota_reset_expired_billing_cycle(quota_enforcement_setup):
    org_id = quota_enforcement_setup["org_id"]
    past_reset = _past(days=2)
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=5,
        requests_used=5,
        reset_at=past_reset,
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200
    assert quota.requests_used == 1
    assert quota.reset_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_quota_concurrent_requests(quota_enforcement_setup):
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=5,
        requests_used=0,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async def send_req():
            return await ac.post(
                "/api/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )

        responses = await asyncio.gather(*[send_req() for _ in range(10)])


    status_codes = [r.status_code for r in responses]
    success_count = status_codes.count(200)
    blocked_count = status_codes.count(429)


    assert success_count == 5
    assert blocked_count == 5
    assert quota.requests_used == 5
