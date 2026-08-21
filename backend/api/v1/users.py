"""Current-user profile endpoints."""
from fastapi import APIRouter, Depends

from core.dependencies import get_current_user
from repositories.mongo.user_repository import user_repository
from schemas.resources import UserUpdateRequest
from services.presenter import build_me

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    return await build_me(user)


@router.patch("/me")
async def update_me(payload: UserUpdateRequest, user=Depends(get_current_user)):
    changes = payload.model_dump(exclude_none=True)
    if changes:
        await user_repository.update(user.id, changes)
        user = await user_repository.get(user.id)
    return await build_me(user)
