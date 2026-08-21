"""Pytest environment setup.

The TestClient talks to http://testserver, where browsers/httpx will not store
`Secure` cookies. Disable secure cookies for tests only (production/preview runs
over HTTPS with COOKIE_SECURE=true from .env). Must run before server import.
"""
import os

os.environ["COOKIE_SECURE"] = "false"
os.environ["COOKIE_SAMESITE"] = "lax"

import asyncio  # noqa: E402

import pytest  # noqa: E402
from dotenv import dotenv_values  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def reset_registration_throttle():
    """Registration is throttled to 20/hour per client IP. The whole in-process
    suite shares the identifier `register:testclient`, so consecutive suite runs
    otherwise start failing with 429. Clear only the throttle counters (test-scope,
    no product data touched) so the suite is repeatable.
    """
    env = dotenv_values("/app/backend/.env")

    async def _clear():
        client = AsyncIOMotorClient(env["MONGO_URL"])
        try:
            await client[env["DB_NAME"]]["rate_events"].delete_many(
                {"identifier": {"$regex": "^register:"}}
            )
        finally:
            client.close()

    asyncio.run(_clear())
    yield
