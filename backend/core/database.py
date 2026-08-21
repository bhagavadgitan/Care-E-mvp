"""MongoDB connection lifecycle and accessors (async, motor)."""
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import settings
from core.logging_config import get_logger

logger = get_logger("care_e.db")


class _DBState:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


_state = _DBState()


async def connect_to_mongo() -> None:
    _state.client = AsyncIOMotorClient(settings.MONGO_URL, uuidRepresentation="standard")
    _state.db = _state.client[settings.DB_NAME]
    await _state.client.admin.command("ping")
    logger.info("Connected to MongoDB (db=%s)", settings.DB_NAME)


async def close_mongo_connection() -> None:
    if _state.client is not None:
        _state.client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    if _state.db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return _state.db


async def ping() -> bool:
    await get_database().command("ping")
    return True
