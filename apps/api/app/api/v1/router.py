from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, ready, users, version

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(health.router, prefix="/health", tags=["system"])
api_router.include_router(ready.router, prefix="/ready", tags=["system"])
api_router.include_router(version.router, prefix="/version", tags=["system"])
