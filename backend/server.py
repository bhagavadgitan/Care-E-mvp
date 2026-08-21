"""CARE-E backend application entrypoint (modular monolith).

Layering: API -> (AuthN/AuthZ, added later) -> Services -> Domain -> Repositories -> MongoDB.
This M0 foundation wires configuration, database lifecycle, migrations, logging,
centralized error handling, versioned API routing, and a health check.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.v1.router import api_v1_router
from core.config import settings
from core.database import close_mongo_connection, connect_to_mongo
from core.exceptions import register_exception_handlers
from core.logging_config import configure_logging, get_logger
from migrations.runner import run_migrations

configure_logging()
logger = get_logger("care_e.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    await run_migrations()
    logger.info("CARE-E backend started (env=%s, data_mode=%s)", settings.ENV, settings.DATA_MODE)
    yield
    await close_mongo_connection()


app = FastAPI(
    title="CARE-E API",
    description="Healthcare Supply Resolution Network — synthetic demonstration data.",
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All backend routes are mounted under /api (Kubernetes ingress requirement),
# and versioned under /v1 -> effective prefix /api/v1.
app.include_router(api_v1_router, prefix="/api")
