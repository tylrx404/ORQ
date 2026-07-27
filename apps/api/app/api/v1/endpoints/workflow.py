from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def workflow_placeholder():
    """Placeholder endpoint – will be implemented in a future phase."""
    return {"status": "not_implemented", "endpoint": "workflow"}
