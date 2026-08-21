"""Facility service with server-enforced organisation/facility scoping."""
from typing import List, Optional

from core.dependencies import assert_facility_access
from core.exceptions import NotFoundError, ValidationAppError
from domain.models import Facility, Role, User
from repositories.mongo.facility_repository import facility_repository
from services import audit_service


async def list_for_user(user: User, organisation_id: Optional[str] = None) -> List[Facility]:
    if user.role == Role.ADMIN:
        if organisation_id:
            return await facility_repository.list_by_org(organisation_id)
        return await facility_repository.list({}, limit=200)
    return await facility_repository.list_by_org(user.organisation_id)


async def get_for_user(user: User, facility_id: str) -> Facility:
    facility = await facility_repository.get(facility_id)
    if not facility:
        raise NotFoundError(message="Facility not found.")
    assert_facility_access(user, facility)
    return facility


async def create_for_user(
    user: User,
    *,
    name: str,
    facility_type: str = "HOSPITAL",
    location: Optional[str] = None,
    organisation_id: Optional[str] = None,
) -> Facility:
    if user.role == Role.ADMIN:
        if not organisation_id:
            raise ValidationAppError(message="organisation_id is required.")
        org_id = organisation_id
    else:
        org_id = user.organisation_id

    facility = await facility_repository.create(
        Facility(organisation_id=org_id, name=name, facility_type=facility_type, location=location)
    )
    await audit_service.record_event(
        "facility.created", actor=user, target_type="facility", target_id=facility.id, organisation_id=org_id
    )
    return facility


async def update_for_user(user: User, facility_id: str, changes: dict) -> Facility:
    await get_for_user(user, facility_id)  # enforces ownership
    return await facility_repository.update(facility_id, changes)
