from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from app.main import app
from app.api.dependencies import get_current_api_key, get_llm_gateway_service, get_rate_limit_service
from app.models.api_key import ApiKey
from app.services.rate_limit import RateLimitService


class MockRedisPipeline:
    def __init__(self, db):
        self.db = db
        self.commands = []

    def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(("zremrangebyscore", key, min_score, max_score))

    def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))

    def zcard(self, key):
        self.commands.append(("zcard", key))

    def zrange(self, key, start, end, withscores=False):
        self.commands.append(("zrange", key, start, end, withscores))

    def expire(self, key, time):
        self.commands.append(("expire", key, time))

    async def execute(self):
        results = []
        for cmd in self.commands:
            op = cmd[0]
            key = cmd[1]
            if key not in self.db:
                self.db[key] = {}
            zset = self.db[key]

            if op == "zremrangebyscore":
                min_score, max_score = cmd[2], cmd[3]
                to_remove = [m for m, s in zset.items() if min_score <= s <= max_score]
                for m in to_remove:
                    del zset[m]
                results.append(len(to_remove))
            elif op == "zadd":
                mapping = cmd[2]
                added = 0
                for m, s in mapping.items():
                    if m not in zset:
                        added += 1
                    zset[m] = s
                results.append(added)
            elif op == "zcard":
                results.append(len(zset))
            elif op == "zrange":
                start, end, withscores = cmd[2], cmd[3], cmd[4]
                sorted_items = sorted(zset.items(), key=lambda x: x[1])
                # Note: simple slice implementation assuming start=0, end=0 for now
                if start == 0 and end == 0:
                    sliced = sorted_items[0:1]
                else:
                    sliced = sorted_items[start:end+1 if end != -1 else None]
                if withscores:
                    results.append([(m, s) for m, s in sliced])
                else:
                    results.append([m for m, s in sliced])
            elif op == "expire":
                results.append(1)
        return results

class MockRedis:
    def __init__(self):
        self.db = {}

    def pipeline(self):
        return MockRedisPipeline(self.db)


@pytest.fixture
def mock_redis():
    return MockRedis()


@pytest.fixture
def rate_limit_setup(mock_redis):
    org_id = uuid4()
    api_key = ApiKey(
        id=uuid4(),
        organization_id=org_id,
        name="test",
        key_hash="hash",
        key_prefix="prefix",
        is_active=True,
    )

    class MockLLMGatewayService:
        async def execute_chat_completion(self, *args, **kwargs):
            return {"id": "chatcmpl-123"}, None

    app.dependency_overrides[get_current_api_key] = lambda: api_key
    app.dependency_overrides[get_llm_gateway_service] = lambda: MockLLMGatewayService()
    
    rate_limit_service = RateLimitService(mock_redis)
    app.dependency_overrides[get_rate_limit_service] = lambda: rate_limit_service

    yield {
        "org_id": org_id,
        "api_key": api_key,
        "redis": mock_redis,
    }
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rate_limit_under_limit(rate_limit_setup):
    setup = rate_limit_setup
    
    # Pre-populate 5 recent requests
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    key = f"rate_limit:org:{setup['org_id']}:rpm"
    setup["redis"].db[key] = {f"{now_ms - 10000}:{i}": now_ms - 10000 for i in range(5)}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.headers["x-ratelimit-limit"] == "60"
    assert response.headers["x-ratelimit-remaining"] == "54"  # 60 - 5 - 1 = 54
    assert "x-ratelimit-reset" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_sliding_window_expiry(rate_limit_setup):
    setup = rate_limit_setup
    
    # Pre-populate 60 requests: 59 old (T - 65s), 1 recent (T - 10s)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    key = f"rate_limit:org:{setup['org_id']}:rpm"
    setup["redis"].db[key] = {
        **{f"{now_ms - 65000}:{i}": now_ms - 65000 for i in range(59)},
        f"{now_ms - 10000}:recent": now_ms - 10000
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    # 59 old requests should be cleared, so count should be 1 + 1 (new) = 2
    assert response.status_code == 200
    assert response.headers["x-ratelimit-remaining"] == "58"


@pytest.mark.asyncio
async def test_rate_limit_over_limit_concurrent_behavior(rate_limit_setup):
    setup = rate_limit_setup
    
    # Pre-populate 60 requests (all recent)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    key = f"rate_limit:org:{setup['org_id']}:rpm"
    setup["redis"].db[key] = {f"{now_ms - 10000}:{i}": now_ms - 10000 for i in range(60)}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    # 61st request should be blocked
    assert response.status_code == 429
    assert response.headers["x-ratelimit-limit"] == "60"
    assert response.headers["x-ratelimit-remaining"] == "0"
    
    data = response.json()
    assert data["error"]["type"] == "rate_limit_error"


@pytest.mark.asyncio
async def test_rate_limit_redis_unavailable(rate_limit_setup):
    setup = rate_limit_setup
    
    class FailingRedisPipeline:
        def zremrangebyscore(self, *args): pass
        def zadd(self, *args): pass
        def zcard(self, *args): pass
        def zrange(self, *args, **kwargs): pass
        def expire(self, *args): pass
        async def execute(self):
            raise ConnectionError("Redis is down")

    class FailingRedis:
        def pipeline(self):
            return FailingRedisPipeline()
            
    app.dependency_overrides[get_rate_limit_service] = lambda: RateLimitService(FailingRedis())

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "Rate limit service unavailable"
