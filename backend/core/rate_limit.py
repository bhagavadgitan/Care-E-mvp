"""Lightweight MongoDB-backed rate limiting & brute-force protection.

Simplest reliable mechanism for the MVP — no distributed infrastructure. TTL
indexes (created in migration 0002) expire old records automatically.
"""
from datetime import datetime, timedelta, timezone

from core.database import get_database


async def check_and_hit(identifier: str, limit: int, window_seconds: int) -> bool:
    """Generic throttle. Returns True if allowed, False if over the limit."""
    coll = get_database()["rate_events"]
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    count = await coll.count_documents({"identifier": identifier, "ts": {"$gte": window_start}})
    if count >= limit:
        return False
    await coll.insert_one({"identifier": identifier, "ts": now})
    return True


async def record_login_failure(identifier: str) -> None:
    await get_database()["login_attempts"].insert_one(
        {"identifier": identifier, "ts": datetime.now(timezone.utc)}
    )


async def login_locked(identifier: str, limit: int = 5, window_seconds: int = 900) -> bool:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    count = await get_database()["login_attempts"].count_documents(
        {"identifier": identifier, "ts": {"$gte": window_start}}
    )
    return count >= limit


async def clear_login_failures(identifier: str) -> None:
    await get_database()["login_attempts"].delete_many({"identifier": identifier})
