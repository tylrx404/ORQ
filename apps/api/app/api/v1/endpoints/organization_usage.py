from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_usage_service, require_member
from app.schemas.usage import UsageSummaryResponse
from app.services.usage import UsageService

router = APIRouter()

_DEFAULT_WINDOW_DAYS = 30


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    dependencies=[Depends(require_member)],
)
async def get_organization_usage(
    organization_id: UUID,
    start: datetime | None = None,
    end: datetime | None = None,
    usage_service: UsageService = Depends(get_usage_service),
):
    """
    Return aggregated usage statistics for an organization.

    Defaults to the last 30 days if `start` / `end` are omitted.
    Both parameters are inclusive and timezone-aware (UTC assumed when naive).
    """
    now = datetime.now(timezone.utc)

    if end is None:
        end = now
    elif end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    if start is None:
        start = end - timedelta(days=_DEFAULT_WINDOW_DAYS)
    elif start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    return await usage_service.get_organization_usage(
        organization_id=organization_id,
        start=start,
        end=end,
    )
