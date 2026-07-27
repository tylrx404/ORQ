import logging

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("orq")

class RedisManager:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        self.redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Connected to Redis")

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    def get_client(self) -> Redis:
        return self.redis_client

redis_manager = RedisManager()
