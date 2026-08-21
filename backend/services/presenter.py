"""Presenters: build safe, client-facing response payloads (no password hashes)."""
from domain.models import AccountStatus, ApprovalStatus, Organisation, Role, User
from repositories.mongo.facility_repository import facility_repository
from repositories.mongo.organisation_repository import organisation_repository


def user_public(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "role": u.role,
        "account_status": u.account_status,
        "authentication_provider": u.authentication_provider,
        "organisation_id": u.organisation_id,
        "primary_facility_id": u.primary_facility_id,
        "job_title": u.job_title,
        "last_login_at": u.last_login_at,
    }


def org_public(o: Organisation) -> dict:
    return {
        "id": o.id,
        "name": o.name,
        "organisation_type": o.organisation_type,
        "subtype": o.subtype,
        "approval_status": o.approval_status,
        "created_at": o.created_at,
    }


async def build_me(user: User) -> dict:
    org = None
    if user.organisation_id:
        o = await organisation_repository.get(user.organisation_id)
        org = org_public(o) if o else None

    can_access_app = user.account_status == AccountStatus.ACTIVE and (
        user.role == Role.ADMIN
        or (org is not None and org["approval_status"] == ApprovalStatus.APPROVED)
    )

    facilities = []
    if user.organisation_id and user.role != Role.ADMIN:
        facs = await facility_repository.list_by_org(user.organisation_id)
        facilities = [
            {"id": f.id, "name": f.name, "facility_type": f.facility_type, "status": f.status, "location": f.location}
            for f in facs
        ]

    return {
        "user": user_public(user),
        "organisation": org,
        "facilities": facilities,
        "can_access_app": bool(can_access_app),
    }
