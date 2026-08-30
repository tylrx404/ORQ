from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_execution_log_repository, require_member
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.schemas.execution_log import ExecutionLogResponse

router = APIRouter()


@router.get(
    "",
    response_model=Sequence[ExecutionLogResponse],
    dependencies=[Depends(require_member)],
)
async def list_organization_executions(
    organization_id: UUID,
    skip: int = 0,
    limit: int = 100,
    execution_log_repo: ExecutionLogRepository = Depends(get_execution_log_repository),
):
    """List all execution logs for an organization (ordered newest first)."""
    return await execution_log_repo.list_by_organization(
        organization_id=organization_id, skip=skip, limit=limit
    )
