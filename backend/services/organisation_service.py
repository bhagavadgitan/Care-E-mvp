"""Organisation service: retrieval, creation, and guarded approval transitions."""
from typing import List, Optional

from core.exceptions import ConflictError, NotFoundError
from domain.models import ApprovalStatus, Organisation, OrganisationType, User
from repositories.mongo.organisation_repository import organisation_repository
from services import audit_service

# Allowed approval state transitions.
_VALID_TRANSITIONS = {
    ApprovalStatus.PENDING: {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED},
    ApprovalStatus.APPROVED: {ApprovalStatus.SUSPENDED},
    ApprovalStatus.SUSPENDED: {ApprovalStatus.APPROVED},
    ApprovalStatus.REJECTED: set(),
}


def validate_transition(current: ApprovalStatus, new: ApprovalStatus) -> bool:
    return new in _VALID_TRANSITIONS.get(current, set())


async def get_org(org_id: str) -> Organisation:
    org = await organisation_repository.get(org_id)
    if not org:
        raise NotFoundError(message="Organisation not found.")
    return org


async def list_orgs(status: Optional[str] = None) -> List[Organisation]:
    return await organisation_repository.list_by_status(status)


async def create_org(admin: User, name: str, organisation_type: str, subtype: Optional[str] = None) -> Organisation:
    org = await organisation_repository.create(
        Organisation(name=name, organisation_type=OrganisationType(organisation_type), subtype=subtype)
    )
    await audit_service.record_event(
        "organisation.created", actor=admin, target_type="organisation", target_id=org.id, organisation_id=org.id
    )
    return org


async def update_approval(admin: User, org_id: str, new_status: ApprovalStatus) -> Organisation:
    org = await get_org(org_id)
    if org.approval_status == new_status:
        return org
    if not validate_transition(org.approval_status, new_status):
        raise ConflictError(
            code="invalid_transition",
            message=f"Cannot change status from {org.approval_status.value} to {new_status.value}.",
        )
    updated = await organisation_repository.update(org_id, {"approval_status": new_status.value})
    await audit_service.record_event(
        "organisation.approval_changed",
        actor=admin,
        target_type="organisation",
        target_id=org_id,
        organisation_id=org_id,
        meta={"previous": org.approval_status.value, "new": new_status.value},
    )
    return updated
