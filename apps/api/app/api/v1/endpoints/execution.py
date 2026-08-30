from fastapi import APIRouter, Depends

from app.api.dependencies import require_execution_member
from app.models.execution_log import ExecutionLog
from app.schemas.execution_log import ExecutionLogResponse

router = APIRouter()


@router.get(
    "/{execution_id}",
    response_model=ExecutionLogResponse,
)
async def get_execution_log(
    execution_log: ExecutionLog = Depends(require_execution_member),
):
    """Retrieve details for a single execution log."""
    return execution_log
