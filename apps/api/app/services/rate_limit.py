import time
import uuid
from typing import Any
from uuid import UUID
from redis.asyncio import Redis

class RateLimitService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def check_rate_limit(self, organization_id: UUID, limit: int) -> tuple[bool, dict[str, str], dict[str, Any] | None]:
        """
        Applies a sliding-window rate limit using Redis ZSET.
        Returns:
            allowed (bool): True if the request should be allowed.
            headers (dict): Rate limit headers (Limit, Remaining, Reset).
            error_body (dict | None): OpenAI-compatible error response if not allowed.
        """
        now_ms = int(time.time() * 1000)
        window_size_ms = 60000
        window_start = now_ms - window_size_ms
        key = f"rate_limit:org:{organization_id}:rpm"
        member = f"{now_ms}:{uuid.uuid4()}"

        try:
            pipeline = self.redis.pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zadd(key, {member: now_ms})
            pipeline.zcard(key)
            pipeline.zrange(key, 0, 0, withscores=True)
            pipeline.expire(key, 60)
            
            results = await pipeline.execute()
        except Exception:
            # Fail safely if Redis is unavailable
            raise RuntimeError("Rate limit service unavailable")
            
        current_count = results[2]
        oldest_elements = results[3]
        
        allowed = current_count <= limit
        remaining = max(0, limit - current_count)
        
        reset_time = int(time.time()) + 60
        if oldest_elements:
            oldest_score = oldest_elements[0][1]
            reset_time = int(oldest_score / 1000) + 60
            
        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time)
        }
        
        error_body = None
        if not allowed:
            error_body = {
                "error": {
                    "message": f"Rate limit reached for organization. Limit is {limit} requests per minute.",
                    "type": "rate_limit_error",
                    "code": 429
                }
            }
            
        return allowed, headers, error_body
