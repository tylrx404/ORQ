from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.core.middleware import RequestLoggingMiddleware
from app.redis.client import redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up ORQ API...")
    try:
        await redis_manager.connect()
    except Exception as e:
        logger.error(f"Failed to connect to Redis on startup: {e}")
    yield
    logger.info("Shutting down ORQ API...")
    try:
        await redis_manager.disconnect()
    except Exception as e:
        logger.error(f"Failed to disconnect Redis: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["root"])
async def root():
    return {"message": "Welcome to ORQ API", "docs": "/docs"}
