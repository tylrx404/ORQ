import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models.execution_log import ExecutionLog


class MockExecutionLogRepository:
    def __init__(self):
        self.logs: dict[UUID, ExecutionLog] = {}

    async def get_by_id(self, execution_id: UUID) -> ExecutionLog | None:
        return self.logs.get(execution_id)

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ExecutionLog]:
        matching = [
            log for log in self.logs.values() if log.organization_id == organization_id
        ]
        matching.sort(key=lambda x: x.created_at, reverse=True)
        return matching[skip : skip + limit]

    async def create(self, execution_log: ExecutionLog) -> ExecutionLog:
        execution_log.id = uuid4()
        execution_log.created_at = datetime.now(timezone.utc)
        self.logs[execution_log.id] = execution_log
        return execution_log


@pytest.mark.asyncio
async def test_create_and_get_execution_log():
    repo = MockExecutionLogRepository()
    org_id = uuid4()

    log = ExecutionLog(
        organization_id=org_id,
        model_name="gpt-4o",
        status_code=200,
        prompt_tokens=15,
        completion_tokens=25,
        total_tokens=40,
        latency_ms=120,
    )

    created = await repo.create(log)
    assert created.id is not None
    assert created.organization_id == org_id
    assert created.model_name == "gpt-4o"
    assert created.status_code == 200

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.total_tokens == 40


@pytest.mark.asyncio
async def test_list_execution_logs_by_organization():
    repo = MockExecutionLogRepository()
    org_id_1 = uuid4()
    org_id_2 = uuid4()

    log1 = ExecutionLog(
        organization_id=org_id_1,
        model_name="gpt-4o",
        status_code=200,
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        latency_ms=100,
    )
    log2 = ExecutionLog(
        organization_id=org_id_1,
        model_name="claude-3-5-sonnet",
        status_code=200,
        prompt_tokens=30,
        completion_tokens=50,
        total_tokens=80,
        latency_ms=250,
    )
    log3 = ExecutionLog(
        organization_id=org_id_2,
        model_name="gpt-4o-mini",
        status_code=500,
        error_message="Provider error",
    )

    await repo.create(log1)
    await repo.create(log2)
    await repo.create(log3)

    org1_logs = await repo.list_by_organization(org_id_1)
    assert len(org1_logs) == 2
    assert {l.model_name for l in org1_logs} == {"gpt-4o", "claude-3-5-sonnet"}

    org2_logs = await repo.list_by_organization(org_id_2)
    assert len(org2_logs) == 1
    assert org2_logs[0].status_code == 500
    assert org2_logs[0].error_message == "Provider error"
