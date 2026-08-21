"""Aggregate all /api/v1 routers here."""
from fastapi import APIRouter

from api.v1 import health

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router)
