"""
Integration tests for the OrganizationQuota CRUD endpoint and service layer.

All tests use MockOrganizationQuotaRepository — no real DB needed for this file.
A separate DB integration test covers the repository SQL.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import (
    get_organization_quota_service,
    require_admin,
    require_member,
)
from app.main import app
from app.models.organization_quota import OrganizationQuota
from app.services.organization_quota import (
    OrganizationQuotaService,
    QuotaAlreadyExistsError,
    QuotaNotFoundError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future(days: int = 30) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def _quota(
    org_id=None,
    request_limit=100,
    token_limit=50000,
    requests_used=0,
    tokens_used=0,
    reset_at=None,
) -> OrganizationQuota:
    q = OrganizationQuota(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        request_limit=request_limit,
        token_limit=token_limit,
        requests_used=requests_used,
        tokens_used=tokens_used,
        reset_at=reset_at or _future(),
    )
    q.created_at = datetime.now(timezone.utc)
    q.updated_at = datetime.now(timezone.utc)
    return q


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def quota_setup(org_id):
    """Fixture that wires a mock OrganizationQuotaService and bypasses auth."""
    mock_service = AsyncMock(spec=OrganizationQuotaService)

    app.dependency_overrides[get_organization_quota_service] = lambda: mock_service
    app.dependency_overrides[require_admin] = lambda: None
    app.dependency_overrides[require_member] = lambda: None

    yield {"org_id": org_id, "service": mock_service}

    app.dependency_overrides.pop(get_organization_quota_service, None)
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(require_member, None)


# ---------------------------------------------------------------------------
# GET /quota
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_quota_success(quota_setup):
    org_id = quota_setup["org_id"]
    q = _quota(org_id=org_id)
    quota_setup["service"].get_quota.return_value = q

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/organizations/{org_id}/quota")

    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org_id)
    assert data["request_limit"] == 100
    assert data["token_limit"] == 50000
    assert data["requests_used"] == 0
    assert data["tokens_used"] == 0


@pytest.mark.asyncio
async def test_get_quota_not_found(quota_setup):
    org_id = quota_setup["org_id"]
    quota_setup["service"].get_quota.side_effect = QuotaNotFoundError("not found")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/organizations/{org_id}/quota")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /quota
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_quota_success(quota_setup):
    org_id = quota_setup["org_id"]
    q = _quota(org_id=org_id, request_limit=200, token_limit=100000)
    quota_setup["service"].create_quota.return_value = q

    payload = {
        "request_limit": 200,
        "token_limit": 100000,
        "reset_at": _future().isoformat(),
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/organizations/{org_id}/quota", json=payload)

    assert resp.status_code == 201
    assert resp.json()["request_limit"] == 200


@pytest.mark.asyncio
async def test_create_quota_conflict(quota_setup):
    org_id = quota_setup["org_id"]
    quota_setup["service"].create_quota.side_effect = QuotaAlreadyExistsError("exists")

    payload = {
        "request_limit": 200,
        "reset_at": _future().isoformat(),
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/organizations/{org_id}/quota", json=payload)

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_quota_unlimited(quota_setup):
    """Omitting limits should create an unlimited quota (NULL limits accepted)."""
    org_id = quota_setup["org_id"]
    q = _quota(org_id=org_id, request_limit=None, token_limit=None)
    quota_setup["service"].create_quota.return_value = q

    payload = {"reset_at": _future().isoformat()}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(f"/api/v1/organizations/{org_id}/quota", json=payload)

    assert resp.status_code == 201
    assert resp.json()["request_limit"] is None
    assert resp.json()["token_limit"] is None


# ---------------------------------------------------------------------------
# PATCH /quota
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_quota_success(quota_setup):
    org_id = quota_setup["org_id"]
    q = _quota(org_id=org_id, request_limit=500)
    quota_setup["service"].update_quota.return_value = q

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/organizations/{org_id}/quota",
            json={"request_limit": 500},
        )

    assert resp.status_code == 200
    assert resp.json()["request_limit"] == 500


@pytest.mark.asyncio
async def test_update_quota_not_found(quota_setup):
    org_id = quota_setup["org_id"]
    quota_setup["service"].update_quota.side_effect = QuotaNotFoundError("not found")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.patch(
            f"/api/v1/organizations/{org_id}/quota",
            json={"request_limit": 500},
        )

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /quota
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_quota_success(quota_setup):
    org_id = quota_setup["org_id"]
    quota_setup["service"].delete_quota.return_value = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.delete(f"/api/v1/organizations/{org_id}/quota")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_quota_not_found(quota_setup):
    org_id = quota_setup["org_id"]
    quota_setup["service"].delete_quota.side_effect = QuotaNotFoundError("not found")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.delete(f"/api/v1/organizations/{org_id}/quota")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Service-level unit tests (no HTTP, no DB)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_cycle_reset():
    """_maybe_reset_cycle should reset counters and advance reset_at when past."""
    org_id = uuid4()
    past = datetime.now(timezone.utc) - timedelta(days=5)

    q = _quota(org_id=org_id, requests_used=50, tokens_used=12000, reset_at=past)

    mock_repo = AsyncMock()
    mock_repo.get_by_organization.return_value = q
    mock_repo.update = AsyncMock(return_value=q)

    service = OrganizationQuotaService(mock_repo)
    reset_q = await service._maybe_reset_cycle(q)

    assert reset_q.requests_used == 0
    assert reset_q.tokens_used == 0
    assert reset_q.reset_at > datetime.now(timezone.utc)
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_service_no_reset_when_cycle_not_expired():
    """_maybe_reset_cycle should not touch the record if reset_at is in the future."""
    org_id = uuid4()
    future = datetime.now(timezone.utc) + timedelta(days=25)

    q = _quota(org_id=org_id, requests_used=10, tokens_used=5000, reset_at=future)

    mock_repo = AsyncMock()
    mock_repo.update = AsyncMock()

    service = OrganizationQuotaService(mock_repo)
    result = await service._maybe_reset_cycle(q)

    assert result.requests_used == 10
    mock_repo.update.assert_not_called()


@pytest.mark.asyncio
async def test_service_create_raises_if_exists():
    from app.schemas.organization_quota import OrganizationQuotaCreate

    org_id = uuid4()
    mock_repo = AsyncMock()
    mock_repo.get_by_organization.return_value = _quota(org_id=org_id)

    service = OrganizationQuotaService(mock_repo)
    data = OrganizationQuotaCreate(request_limit=100, reset_at=_future())

    with pytest.raises(QuotaAlreadyExistsError):
        await service.create_quota(org_id, data)
