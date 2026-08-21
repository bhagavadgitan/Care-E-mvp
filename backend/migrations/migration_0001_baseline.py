"""Baseline foundation migration (M0).

Establishes the migration mechanism and a system metadata document. No business
collections/validators are created in M0 — later milestones add JSON-Schema
validators and indexes for domain collections.
"""

VERSION = 1
NAME = "baseline_foundation"


async def upgrade(db) -> None:
    await db["system_info"].update_one(
        {"_id": "meta"},
        {
            "$set": {
                "app": "CARE-E",
                "data_mode": "SYNTHETIC",
                "schema_version": VERSION,
            }
        },
        upsert=True,
    )
