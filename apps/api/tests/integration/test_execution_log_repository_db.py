from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.organization import Organization
from app.models.execution_log import ExecutionLog
from app.repositories.execution_log_repository import ExecutionLogRepository


@pytest.fixture
async def db_session():
    """Provides a real database session and cleans up after the test."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_get_usage_summary_real_db(db_session: AsyncSession):
    """Integration test against a real PostgreSQL database to verify the usage summary aggregation query."""
    repo = ExecutionLogRepository(db_session)
    now = datetime.now(timezone.utc)

    # 1. Create a real Organization to satisfy the foreign key
    org = Organization(
        name=f"test-org-{uuid4()}",
        slug=f"test-slug-{uuid4()}",
    )
    db_session.add(org)
    await db_session.flush()

    # 2. Insert test ExecutionLogs
    logs = [
        ExecutionLog(
            id=uuid4(),
            organization_id=org.id,
            model_name="test-model",
            status_code=200,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            latency_ms=100,
            created_at=now - timedelta(hours=1),
        ),
        ExecutionLog(
            id=uuid4(),
            organization_id=org.id,
            model_name="test-model",
            status_code=200,
            prompt_tokens=5,
            completion_tokens=15,
            total_tokens=20,
            latency_ms=200,
            created_at=now - timedelta(hours=2),
        ),
        ExecutionLog(
            id=uuid4(),
            organization_id=org.id,
            model_name="test-model",
            status_code=500,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            latency_ms=300,
            created_at=now - timedelta(hours=3),
        ),
    ]
    for log in logs:
        db_session.add(log)
    await db_session.flush()

    # 3. Test the get_usage_summary query
    start_time = now - timedelta(days=1)
    end_time = now + timedelta(hours=1)

    summary = await repo.get_usage_summary(org.id, start_time, end_time)

    assert summary["total_requests"] == 3
    assert summary["successful_requests"] == 2
    assert summary["failed_requests"] == 1
    assert summary["prompt_tokens"] == 15
    assert summary["completion_tokens"] == 35
    assert summary["total_tokens"] == 50
    assert summary["average_latency_ms"] == pytest.approx((100 + 200 + 300) / 3)

    # Clean up (Optional, since the fixture rolls back)
    await db_session.delete(org)
    await db_session.flush()
