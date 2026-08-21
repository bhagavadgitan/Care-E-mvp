"""Facility endpoints (server-enforced organisation/facility scoping)."""
from typing import Optional

from fastapi import APIRouter, Depends

from core.dependencies import get_current_active_user, require_role
from domain.models import Role
from schemas.resources import FacilityCreateRequest, FacilityUpdateRequest
from services import facility_service

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.get("")
async def list_facilities(organisation_id: Optional[str] = None, user=Depends(get_current_active_user)):
    facilities = await facility_service.list_for_user(user, organisation_id)
    return {"facilities": facilities}


@router.post("", status_code=201)
async def create_facility(payload: FacilityCreateRequest, user=Depends(require_role(Role.HOSPITAL, Role.ADMIN))):
    facility = await facility_service.create_for_user(
        user,
        name=payload.name,
        facility_type=payload.facility_type,
        location=payload.location,
        organisation_id=payload.organisation_id,
    )
    return {"facility": facility}


@router.get("/{facility_id}")
async def get_facility(facility_id: str, user=Depends(get_current_active_user)):
    facility = await facility_service.get_for_user(user, facility_id)
    return {"facility": facility}


@router.patch("/{facility_id}")
async def update_facility(
    facility_id: str, payload: FacilityUpdateRequest, user=Depends(require_role(Role.HOSPITAL, Role.ADMIN))
):
    changes = payload.model_dump(exclude_none=True)
    facility = await facility_service.update_for_user(user, facility_id, changes)
    return {"facility": facility}
