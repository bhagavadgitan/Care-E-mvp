"""Aggregate all /api/v1 routers here."""
from fastapi import APIRouter

from api.v1 import auth, facilities, health, network, organisations, users

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(organisations.router)
api_v1_router.include_router(facilities.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(network.router)
