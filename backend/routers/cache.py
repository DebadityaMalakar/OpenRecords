"""
Cache management router for OpenRecords.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/status")
async def cache_status():
    """Return cache system status."""
    return {"status": "ok"}
