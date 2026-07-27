from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()

@router.get("/")
async def get_version():
    return {"name": settings.PROJECT_NAME, "version": settings.VERSION}
