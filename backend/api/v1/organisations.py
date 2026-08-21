"""Organisation endpoints (org-scoped reads + admin approval management)."""
from typing import Optional

from fastapi import APIRouter, Depends

from core.dependencies import assert_org_access, get_admin, get_current_user
from schemas.resources import ApprovalUpdateRequest, OrgCreateRequest
from services import organisation_service
from services.presenter import org_public

router = APIRouter(prefix="/organisations", tags=["organisations"])


@router.get("/me")
async def my_organisation(user=Depends(get_current_user)):
    if not user.organisation_id:
        return {"organisation": None}
    org = await organisation_service.get_org(user.organisation_id)
    return {"organisation": org_public(org)}


@router.get("")
async def list_organisations(status: Optional[str] = None, admin=Depends(get_admin)):
    orgs = await organisation_service.list_orgs(status)
    return {"organisations": [org_public(o) for o in orgs]}


@router.post("", status_code=201)
async def create_organisation(payload: OrgCreateRequest, admin=Depends(get_admin)):
    org = await organisation_service.create_org(admin, payload.name, payload.organisation_type.value, payload.subtype)
    return {"organisation": org_public(org)}


@router.get("/{org_id}")
async def get_organisation(org_id: str, user=Depends(get_current_user)):
    assert_org_access(user, org_id)
    org = await organisation_service.get_org(org_id)
    return {"organisation": org_public(org)}


@router.patch("/{org_id}")
async def update_organisation(org_id: str, payload: ApprovalUpdateRequest, admin=Depends(get_admin)):
    org = await organisation_service.update_approval(admin, org_id, payload.approval_status)
    return {"organisation": org_public(org)}
