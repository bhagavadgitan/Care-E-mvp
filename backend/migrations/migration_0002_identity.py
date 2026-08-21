"""M1 identity: indexes + TTL for rate limiting / brute-force collections.

Integrity for MongoDB is enforced via: unique indexes (below), Pydantic schema
validation (models), and service-layer ownership/reference checks.
"""

VERSION = 2
NAME = "identity_indexes"


async def upgrade(db) -> None:
    await db["users"].create_index("email", unique=True)
    await db["users"].create_index([("authentication_provider", 1), ("provider_subject", 1)])
    await db["users"].create_index("organisation_id")

    await db["organisations"].create_index("approval_status")
    await db["organisations"].create_index("organisation_type")

    await db["facilities"].create_index("organisation_id")

    await db["audit_events"].create_index([("target_type", 1), ("target_id", 1)])
    await db["audit_events"].create_index("created_at")

    # Brute-force / rate-limit stores with TTL cleanup.
    await db["login_attempts"].create_index("identifier")
    await db["login_attempts"].create_index("ts", expireAfterSeconds=3600)
    await db["rate_events"].create_index("identifier")
    await db["rate_events"].create_index("ts", expireAfterSeconds=3600)
