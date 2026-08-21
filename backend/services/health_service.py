"""Health/readiness service. Reports database connectivity and app metadata."""
from core.config import settings
from core.database import ping


async def get_health() -> dict:
    db_connected = False
    try:
        db_connected = await ping()
    except Exception:  # noqa: BLE001 - health must never raise
        db_connected = False

    return {
        "status": "ok" if db_connected else "degraded",
        "service": "care-e-api",
        "version": settings.API_VERSION,
        "environment": settings.ENV,
        "data_mode": settings.DATA_MODE,
        "database": "connected" if db_connected else "disconnected",
    }
