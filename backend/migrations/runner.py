"""Idempotent migration runner.

Applies any migrations not yet recorded in the `_migrations` collection. Safe to
run repeatedly (on startup or via CLI). Version-controlled analog to SQL
migrations.
"""
from datetime import datetime, timezone

from core.database import get_database
from core.logging_config import get_logger
from migrations import migration_0001_baseline as m0001

logger = get_logger("care_e.migrations")

MIGRATIONS = [m0001]


async def run_migrations() -> None:
    db = get_database()
    coll = db["_migrations"]
    await coll.create_index("version", unique=True)

    applied = {doc["version"] async for doc in coll.find({}, {"version": 1})}

    for migration in MIGRATIONS:
        if migration.VERSION in applied:
            continue
        await migration.upgrade(db)
        await coll.insert_one(
            {
                "version": migration.VERSION,
                "name": migration.NAME,
                "applied_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("Applied migration %s - %s", migration.VERSION, migration.NAME)
