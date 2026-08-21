"""Health and liveness endpoints."""
from fastapi import APIRouter

from services.health_service import get_health

router = APIRouter(prefix="/health", tags=["system"])


@router.get("")
async def health():
    """Readiness: reports database connectivity + app metadata."""
    return await get_health()


@router.get("/live")
async def liveness():
    """Liveness: process is up (no dependency checks)."""
    return {"status": "ok"}
