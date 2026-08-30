from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., max_length=50)
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., max_length=255)
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    stream: bool = False
    stream_options: Optional[dict[str, Any]] = None
