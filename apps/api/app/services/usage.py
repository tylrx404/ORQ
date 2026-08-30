from datetime import datetime
from typing import Any
from uuid import UUID

from app.repositories.execution_log_repository import ExecutionLogRepository


class UsageService:
    """Service for computing usage analytics from execution logs."""

    def __init__(self, execution_log_repo: ExecutionLogRepository):
        self._repo = execution_log_repo

    async def get_organization_usage(
        self,
        organization_id: UUID,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        """Return aggregated usage metrics for an organization within a time range."""
        summary = await self._repo.get_usage_summary(
            organization_id=organization_id,
            start=start,
            end=end,
        )
        return {
            "organization_id": str(organization_id),
            "start": start,
            "end": end,
            **summary,
        }
