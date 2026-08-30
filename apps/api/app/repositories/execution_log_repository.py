from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution_log import ExecutionLog


class ExecutionLogRepository:
    """Repository for execution log database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, execution_id: UUID) -> ExecutionLog | None:
        """Fetch an execution log by ID."""
        result = await self.db.execute(
            select(ExecutionLog).where(ExecutionLog.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def list_by_organization(
        self, organization_id: UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[ExecutionLog]:
        """List execution logs for an organization, ordered by newest first."""
        result = await self.db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.organization_id == organization_id)
            .order_by(ExecutionLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create(self, execution_log: ExecutionLog) -> ExecutionLog:
        """Create a new execution log."""
        self.db.add(execution_log)
        await self.db.commit()
        await self.db.refresh(execution_log)
        return execution_log
