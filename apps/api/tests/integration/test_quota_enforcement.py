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

    async def try_increment_tokens(
        self, organization_id, tokens: int, cycle_days: int = 30
    ) -> bool:
        async with self.lock:
            await asyncio.sleep(0.001)
            if tokens <= 0:
                return True
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

            if self.quota.token_limit is not None and (self.quota.tokens_used + tokens) > self.quota.token_limit:
                return False

            self.quota.tokens_used += tokens
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


# ===========================================================================
# Step 3: Token Quota Enforcement Tests
# ===========================================================================

def _make_gateway_with_tokens(total_tokens: int):
    class MockTokenGateway:
        async def execute_chat_completion(self, *args, **kwargs):
            return {
                "id": "chatcmpl-token-test",
                "choices": [{"message": {"content": "response"}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": total_tokens - 10 if total_tokens >= 10 else 0,
                    "total_tokens": total_tokens,
                },
            }, None
    return MockTokenGateway()


@pytest.mark.asyncio
async def test_token_quota_under_limit(quota_enforcement_setup):
    """Tokens are successfully counted and added to tokens_used when under token_limit."""
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=10,
        token_limit=1000,
        requests_used=0,
        tokens_used=100,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service
    app.dependency_overrides[get_llm_gateway_service] = lambda: _make_gateway_with_tokens(50)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200
    assert quota.tokens_used == 150
    assert quota.requests_used == 1


@pytest.mark.asyncio
async def test_token_quota_exact_boundary(quota_enforcement_setup):
    """Adding tokens up to exactly token_limit succeeds; subsequent tokens exceeding limit return 429."""
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=10,
        token_limit=100,
        requests_used=0,
        tokens_used=80,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service

    # 1. Request uses exactly 20 tokens -> 80 + 20 = 100 (exact boundary)
    app.dependency_overrides[get_llm_gateway_service] = lambda: _make_gateway_with_tokens(20)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp1 = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp1.status_code == 200
    assert quota.tokens_used == 100

    # 2. Next request uses 1 token -> 100 + 1 > 100 -> fails with 429
    app.dependency_overrides[get_llm_gateway_service] = lambda: _make_gateway_with_tokens(1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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
    # Tokens must not be counted beyond limit
    assert quota.tokens_used == 100


@pytest.mark.asyncio
async def test_token_quota_exceeding_limit(quota_enforcement_setup):
    """When adding tokens would exceed token_limit, returns 429 and does not increment tokens_used."""
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=10,
        token_limit=100,
        requests_used=0,
        tokens_used=90,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service
    # Completion generates 15 tokens -> 90 + 15 = 105 > 100
    app.dependency_overrides[get_llm_gateway_service] = lambda: _make_gateway_with_tokens(15)

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
    # Token usage must not have incremented past the limit
    assert quota.tokens_used == 90


@pytest.mark.asyncio
async def test_token_quota_null_unlimited(quota_enforcement_setup):
    """When token_limit is NULL (None), tokens are always allowed and counted."""
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=10,
        token_limit=None,
        requests_used=0,
        tokens_used=500000,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service
    app.dependency_overrides[get_llm_gateway_service] = lambda: _make_gateway_with_tokens(5000)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200
    assert quota.tokens_used == 505000


@pytest.mark.asyncio
async def test_token_quota_concurrent_updates(quota_enforcement_setup):
    """Concurrent completions safely lock and update token usage without racing past token_limit.

    If limit is 100 and initial tokens_used is 0, sending 5 concurrent completions each consuming
    30 tokens will allow 3 (90 tokens) and block 2 (which would push it to 120 and 150).
    """
    org_id = quota_enforcement_setup["org_id"]
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=20,
        token_limit=100,
        requests_used=0,
        tokens_used=0,
        reset_at=_future(),
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service
    app.dependency_overrides[get_llm_gateway_service] = lambda: _make_gateway_with_tokens(30)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async def send_req():
            return await ac.post(
                "/api/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )

        responses = await asyncio.gather(*[send_req() for _ in range(5)])

    status_codes = [r.status_code for r in responses]
    success_count = status_codes.count(200)
    blocked_count = status_codes.count(429)

    assert success_count == 3
    assert blocked_count == 2
    assert quota.tokens_used == 90


@pytest.mark.asyncio
async def test_token_quota_reset_expired_billing_cycle(quota_enforcement_setup):
    """Expired billing cycle resets tokens_used to 0 and advances reset_at before checking tokens."""
    org_id = quota_enforcement_setup["org_id"]
    past_reset = _past(days=3)
    quota = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id,
        request_limit=10,
        token_limit=500,
        requests_used=10,
        tokens_used=500,  # fully exhausted in previous cycle
        reset_at=past_reset,
    )
    repo = InMemoryQuotaRepo(quota)
    service = OrganizationQuotaService(repo)
    app.dependency_overrides[get_organization_quota_service] = lambda: service
    app.dependency_overrides[get_llm_gateway_service] = lambda: _make_gateway_with_tokens(150)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
        )

    assert resp.status_code == 200
    # tokens_used was reset to 0 in cycle reset, then 150 added
    assert quota.tokens_used == 150
    assert quota.reset_at > datetime.now(timezone.utc)
