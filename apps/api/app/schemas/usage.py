from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UsageSummaryResponse(BaseModel):
    """Aggregated usage statistics for an organization over a time range."""

    organization_id: str
    start: datetime
    end: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    average_latency_ms: Optional[float]

    model_config = {"from_attributes": True}
