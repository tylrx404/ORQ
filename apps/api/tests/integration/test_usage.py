from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.dependencies import get_current_user, get_usage_service, require_member
from app.models.user import User
from app.services.usage import UsageService
from app.repositories.execution_log_repository import ExecutionLogRepository


class MockExecutionLogRepo:
    """In-memory repo that supports get_usage_summary for testing."""

    def __init__(self, logs=None):
        self.logs = logs or []

    async def get_usage_summary(self, organization_id, start, end):
        scoped = [
            l for l in self.logs
            if l["organization_id"] == organization_id
            and start <= l["created_at"] <= end
        ]
        total = len(scoped)
        successful = sum(1 for l in scoped if l["status_code"] < 400)
        failed = total - successful
        prompt_tokens = sum(l.get("prompt_tokens") or 0 for l in scoped)
        completion_tokens = sum(l.get("completion_tokens") or 0 for l in scoped)
        total_tokens = sum(l.get("total_tokens") or 0 for l in scoped)
        latencies = [l["latency_ms"] for l in scoped if l.get("latency_ms") is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
        return {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": failed,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "average_latency_ms": avg_latency,
        }


@pytest.fixture
def usage_setup():
    org_id_1 = uuid4()
    org_id_2 = uuid4()
    user = User(id=uuid4(), email="member@example.com", is_active=True)
    now = datetime.now(timezone.utc)

    logs = [
        {
            "organization_id": org_id_1,
            "status_code": 200,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "latency_ms": 120,
            "created_at": now - timedelta(days=1),
        },
        {
            "organization_id": org_id_1,
            "status_code": 200,
            "prompt_tokens": 5,
            "completion_tokens": 8,
            "total_tokens": 13,
            "latency_ms": 80,
            "created_at": now - timedelta(days=2),
        },
        {
            "organization_id": org_id_1,
            "status_code": 500,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "latency_ms": 200,
            "created_at": now - timedelta(days=3),
        },
        # Log belonging to a different org — must not appear in org_id_1's usage
        {
            "organization_id": org_id_2,
            "status_code": 200,
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
            "latency_ms": 500,
            "created_at": now - timedelta(days=1),
        },
    ]

    repo = MockExecutionLogRepo(logs)
    usage_service = UsageService(repo)

    yield {
        "org_id_1": org_id_1,
        "org_id_2": org_id_2,
        "user": user,
        "usage_service": usage_service,
        "now": now,
    }


@pytest.mark.asyncio
async def test_usage_default_range(usage_setup):
    setup = usage_setup
    app.dependency_overrides[get_current_user] = lambda: setup["user"]
    app.dependency_overrides[require_member] = lambda: None
    app.dependency_overrides[get_usage_service] = lambda: setup["usage_service"]

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                f"/api/v1/organizations/{setup['org_id_1']}/usage"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 3
        assert data["successful_requests"] == 2
        assert data["failed_requests"] == 1
        assert data["prompt_tokens"] == 15
        assert data["completion_tokens"] == 28
        assert data["total_tokens"] == 43
        assert data["average_latency_ms"] == pytest.approx((120 + 80 + 200) / 3)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_usage_custom_time_range(usage_setup):
    setup = usage_setup
    now = setup["now"]

    # Only include logs from the last 1.5 days — should pick up only 1 successful log
    start = (now - timedelta(days=1, hours=12)).isoformat()
    end = now.isoformat()

    app.dependency_overrides[get_current_user] = lambda: setup["user"]
    app.dependency_overrides[require_member] = lambda: None
    app.dependency_overrides[get_usage_service] = lambda: setup["usage_service"]

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                f"/api/v1/organizations/{setup['org_id_1']}/usage",
                params={"start": start, "end": end},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 1
        assert data["successful_requests"] == 1
        assert data["failed_requests"] == 0
        assert data["total_tokens"] == 30
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_usage_empty_range(usage_setup):
    setup = usage_setup
    now = setup["now"]

    # Time range in the distant past — no logs
    start = (now - timedelta(days=365)).isoformat()
    end = (now - timedelta(days=364)).isoformat()

    app.dependency_overrides[get_current_user] = lambda: setup["user"]
    app.dependency_overrides[require_member] = lambda: None
    app.dependency_overrides[get_usage_service] = lambda: setup["usage_service"]

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                f"/api/v1/organizations/{setup['org_id_1']}/usage",
                params={"start": start, "end": end},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 0
        assert data["prompt_tokens"] == 0
        assert data["average_latency_ms"] is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_usage_cross_organization_blocked(usage_setup):
    """A user without membership in the target org receives 403/404 from require_member."""
    setup = usage_setup

    async def mock_require_member():
        from fastapi import HTTPException, status
        # Simulate RBAC blocking access to an org the user is not a member of
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found."
        )

    app.dependency_overrides[get_current_user] = lambda: setup["user"]
    app.dependency_overrides[require_member] = mock_require_member

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                f"/api/v1/organizations/{setup['org_id_2']}/usage"
            )

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_usage_unauthenticated():
    """Requests without a JWT are rejected by get_current_user."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/organizations/{uuid4()}/usage")
    assert response.status_code == 401
