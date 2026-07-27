import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.redis.client import redis_manager

router = APIRouter()
logger = logging.getLogger("orq")

@router.get("/")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    status = {"database": "ok", "redis": "ok"}
    ready = True

    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        status["database"] = "unhealthy"
        ready = False

    try:
        redis_client = redis_manager.get_client()
        if not redis_client:
            raise Exception("Redis client not initialized")
        await redis_client.ping()
    except Exception as e:
        logger.error(f"Redis readiness check failed: {e}")
        status["redis"] = "unhealthy"
        ready = False

    if not ready:
        raise HTTPException(status_code=503, detail=status)

    return status
