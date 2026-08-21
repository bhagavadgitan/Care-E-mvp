"""Auth request schemas."""
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from domain.models import Role


class HospitalRegisterRequest(BaseModel):
    organisation_name: str = Field(min_length=2, max_length=200)
    primary_facility_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    job_title: Optional[str] = Field(default=None, max_length=120)
    organisation_subtype: Optional[str] = Field(default=None, max_length=120)


class SupplierRegisterRequest(BaseModel):
    organisation_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    organisation_subtype: Optional[str] = Field(default=None, max_length=120)
    job_title: Optional[str] = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class GoogleCallbackRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=512)


class GoogleCompleteRequest(BaseModel):
    role: Role
    organisation_name: str = Field(min_length=2, max_length=200)
    full_name: str = Field(min_length=2, max_length=120)
    primary_facility_name: Optional[str] = Field(default=None, max_length=200)
    organisation_subtype: Optional[str] = Field(default=None, max_length=120)
