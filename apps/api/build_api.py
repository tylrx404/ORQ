import os

base_dir = r"c:\Users\Lenovo\OneDrive\Desktop\ORQ\apps\api"

directories = [
    "app",
    "app/core",
    "app/db",
    "app/redis",
    "app/api",
    "app/api/v1",
    "app/api/v1/endpoints",
    "alembic"
]

for d in directories:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

files = {}

files["requirements.txt"] = """fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.7.0
pydantic-settings>=2.2.1
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.1
redis>=5.0.0
psycopg2-binary>=2.9.9
"""

files["Dockerfile"] = """FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for asyncpg
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

files[".env.example"] = """PROJECT_NAME="ORQ API"
VERSION="0.1.0"
ENVIRONMENT="development"
DATABASE_URL="postgresql+asyncpg://orq:orq_password@postgres:5432/orq_db"
REDIS_URL="redis://redis:6379/0"
"""

files["app/__init__.py"] = ""
files["app/core/__init__.py"] = ""
files["app/db/__init__.py"] = ""
files["app/redis/__init__.py"] = ""
files["app/api/__init__.py"] = ""
files["app/api/v1/__init__.py"] = ""
files["app/api/v1/endpoints/__init__.py"] = ""

files["app/core/config.py"] = """import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ORQ API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    
    DATABASE_URL: str = "postgresql+asyncpg://orq:orq_password@localhost:5432/orq_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
"""

files["app/core/logging.py"] = """import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging():
    logger = logging.getLogger("orq")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

logger = setup_logging()
"""

files["app/db/engine.py"] = """from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)
"""

files["app/db/base.py"] = """from sqlalchemy.orm import declarative_base

Base = declarative_base()
"""

files["app/db/session.py"] = """from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.engine import AsyncSessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
"""

files["app/redis/client.py"] = """from redis.asyncio import Redis
from app.core.config import settings
import logging

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
"""

files["app/api/v1/endpoints/health.py"] = """from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "healthy", "service": "orq-api"}
"""

files["app/api/v1/endpoints/ready.py"] = """from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.redis.client import redis_manager
import logging

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
"""

files["app/api/v1/endpoints/version.py"] = """from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def get_version():
    return {"name": settings.PROJECT_NAME, "version": settings.VERSION}
"""

files["app/api/v1/router.py"] = """from fastapi import APIRouter
from app.api.v1.endpoints import health, ready, version

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["system"])
api_router.include_router(ready.router, prefix="/ready", tags=["system"])
api_router.include_router(version.router, prefix="/version", tags=["system"])
"""

files["app/api/router.py"] = """from fastapi import APIRouter
from app.api.v1.router import api_router as v1_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/v1")
"""

files["app/main.py"] = """from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import api_router
from app.core.config import settings
from app.redis.client import redis_manager
from app.core.logging import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ORQ API...")
    try:
        await redis_manager.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
    yield
    logger.info("Shutting down ORQ API...")
    try:
        await redis_manager.disconnect()
    except Exception as e:
        logger.error(f"Failed to disconnect Redis: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to ORQ API", "docs": "/docs"}
"""

for path, content in files.items():
    full_path = os.path.join(base_dir, path)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Files generated successfully.")
