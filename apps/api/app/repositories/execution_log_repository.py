from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
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

    async def get_usage_summary(
        self,
        organization_id: UUID,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        """Return aggregated usage statistics for an organization over a time range."""
        result = await self.db.execute(
            select(
                func.count(ExecutionLog.id).label("total_requests"),
                func.count(ExecutionLog.id).filter(
                    ExecutionLog.status_code < 400
                ).label("successful_requests"),
                func.count(ExecutionLog.id).filter(
                    ExecutionLog.status_code >= 400
                ).label("failed_requests"),
                func.coalesce(
                    func.sum(ExecutionLog.prompt_tokens), 0
                ).label("prompt_tokens"),
                func.coalesce(
                    func.sum(ExecutionLog.completion_tokens), 0
                ).label("completion_tokens"),
                func.coalesce(
                    func.sum(ExecutionLog.total_tokens), 0
                ).label("total_tokens"),
                func.avg(ExecutionLog.latency_ms).label("average_latency_ms"),
            )
            .where(ExecutionLog.organization_id == organization_id)
            .where(ExecutionLog.created_at >= start)
            .where(ExecutionLog.created_at <= end)
        )
        row = result.one()
        return {
            "total_requests": row.total_requests or 0,
            "successful_requests": row.successful_requests or 0,
            "failed_requests": row.failed_requests or 0,
            "prompt_tokens": row.prompt_tokens or 0,
            "completion_tokens": row.completion_tokens or 0,
            "total_tokens": row.total_tokens or 0,
            "average_latency_ms": (
                float(row.average_latency_ms) if row.average_latency_ms is not None else None
            ),
        }
