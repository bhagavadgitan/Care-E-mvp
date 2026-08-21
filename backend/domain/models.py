"""Identity & organisation domain models (M1)."""
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field

from domain.base import BaseDocument


class Role(str, Enum):
    HOSPITAL = "HOSPITAL"
    SUPPLIER = "SUPPLIER"
    ADMIN = "ADMIN"


class OrganisationType(str, Enum):
    HOSPITAL = "HOSPITAL"
    SUPPLIER = "SUPPLIER"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class AuthProvider(str, Enum):
    PASSWORD = "PASSWORD"
    GOOGLE = "GOOGLE"


class Organisation(BaseDocument):
    name: str
    organisation_type: OrganisationType
    subtype: Optional[str] = None
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    is_synthetic: bool = False


class Facility(BaseDocument):
    organisation_id: str
    name: str
    facility_type: str = "HOSPITAL"
    code: Optional[str] = None
    location: Optional[str] = None
    status: str = "ACTIVE"
    is_synthetic: bool = False


class User(BaseDocument):
    organisation_id: Optional[str] = None
    email: str
    full_name: str
    role: Role
    account_status: AccountStatus = AccountStatus.ACTIVE
    authentication_provider: AuthProvider = AuthProvider.PASSWORD
    provider_subject: Optional[str] = None
    primary_facility_id: Optional[str] = None
    job_title: Optional[str] = None
    password_hash: Optional[str] = None
    last_login_at: Optional[str] = None
    # Tokens issued before this epoch are rejected (enables real logout).
    sessions_valid_after: Optional[int] = None


class AuditEvent(BaseDocument):
    actor_user_id: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    organisation_id: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
