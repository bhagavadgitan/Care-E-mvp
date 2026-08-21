"""Organisation & facility & user request schemas."""
from typing import Optional

from pydantic import BaseModel, Field

from domain.models import ApprovalStatus, OrganisationType


class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    organisation_type: OrganisationType
    subtype: Optional[str] = Field(default=None, max_length=120)


class ApprovalUpdateRequest(BaseModel):
    approval_status: ApprovalStatus


class FacilityCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    facility_type: str = Field(default="HOSPITAL", max_length=60)
    location: Optional[str] = Field(default=None, max_length=300)
    organisation_id: Optional[str] = Field(default=None, max_length=64)


class FacilityUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    location: Optional[str] = Field(default=None, max_length=300)
    status: Optional[str] = Field(default=None, max_length=60)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    job_title: Optional[str] = Field(default=None, max_length=120)
