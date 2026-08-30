import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from uuid import UUID, uuid4

from app.main import app
from app.api.dependencies import (
    get_current_user,
    require_member,
    require_execution_member,
    get_execution_log_repository,
)
from app.models.user import User
from app.models.execution_log import ExecutionLog


class MockExecutionLogRepo:
    def __init__(self):
        self.logs: dict[UUID, ExecutionLog] = {}

    async def get_by_id(self, execution_id: UUID) -> ExecutionLog | None:
        return self.logs.get(execution_id)

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ExecutionLog]:
        return [
            l for l in self.logs.values() if l.organization_id == organization_id
        ][skip : skip + limit]


@pytest.fixture
def execution_setup():
    org_id_1 = uuid4()
    org_id_2 = uuid4()
    user_1 = User(id=uuid4(), email="user1@example.com", is_active=True)
    user_2 = User(id=uuid4(), email="user2@example.com", is_active=True)

    log_1 = ExecutionLog(
        id=uuid4(),
        organization_id=org_id_1,
        model_name="gpt-4o",
        status_code=200,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        latency_ms=150,
        created_at=datetime.now(timezone.utc),
    )
    log_2 = ExecutionLog(
        id=uuid4(),
        organization_id=org_id_2,
        model_name="claude-3-5-sonnet",
        status_code=200,
        prompt_tokens=50,
        completion_tokens=50,
        total_tokens=100,
        latency_ms=300,
        created_at=datetime.now(timezone.utc),
    )

    repo = MockExecutionLogRepo()
    repo.logs[log_1.id] = log_1
    repo.logs[log_2.id] = log_2

    yield {
        "org_id_1": org_id_1,
        "org_id_2": org_id_2,
        "user_1": user_1,
        "user_2": user_2,
        "log_1": log_1,
        "log_2": log_2,
        "repo": repo,
    }


@pytest.mark.asyncio
async def test_list_organization_executions(execution_setup):
    setup = execution_setup
    app.dependency_overrides[get_execution_log_repository] = lambda: setup["repo"]
    app.dependency_overrides[get_current_user] = lambda: setup["user_1"]
    app.dependency_overrides[require_member] = lambda: None

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(
                f"/api/v1/organizations/{setup['org_id_1']}/executions"
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_name"] == "gpt-4o"
        assert data[0]["total_tokens"] == 30
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_execution_log_success(execution_setup):
    setup = execution_setup
    app.dependency_overrides[get_execution_log_repository] = lambda: setup["repo"]
    app.dependency_overrides[get_current_user] = lambda: setup["user_1"]

    async def mock_require_execution_member(execution_id: UUID):
        log = await setup["repo"].get_by_id(execution_id)
        if not log:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution log not found."
            )
        return log

    app.dependency_overrides[require_execution_member] = mock_require_execution_member

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(f"/api/v1/executions/{setup['log_1'].id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(setup["log_1"].id)
        assert data["model_name"] == "gpt-4o"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_execution_log_not_found(execution_setup):
    setup = execution_setup
    app.dependency_overrides[get_execution_log_repository] = lambda: setup["repo"]
    app.dependency_overrides[get_current_user] = lambda: setup["user_1"]

    async def mock_require_execution_member(execution_id: UUID):
        log = await setup["repo"].get_by_id(execution_id)
        if not log:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution log not found."
            )
        return log

    app.dependency_overrides[require_execution_member] = mock_require_execution_member

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(f"/api/v1/executions/{uuid4()}")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_cross_organization_access_prevented(execution_setup):
    setup = execution_setup
    app.dependency_overrides[get_execution_log_repository] = lambda: setup["repo"]
    app.dependency_overrides[get_current_user] = lambda: setup["user_2"]

    async def mock_require_execution_member(execution_id: UUID):
        log = await setup["repo"].get_by_id(execution_id)
        if not log or log.organization_id != setup["org_id_2"]:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Execution log not found."
            )
        return log

    app.dependency_overrides[require_execution_member] = mock_require_execution_member

    try:
        # user_2 (in org_id_2) tries to access log_1 (belonging to org_id_1)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get(f"/api/v1/executions/{setup['log_1'].id}")

        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()
