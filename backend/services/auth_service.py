"""Authentication & registration service (email/password + Google identity)."""
from typing import Optional

import httpx

from datetime import datetime, timezone

from core.config import settings
from core.exceptions import AppError, AuthError, ConflictError, ValidationAppError
from core.rate_limit import (
    clear_login_failures,
    login_locked,
    record_login_failure,
)
from core.security import (
    create_access_token,
    create_onboarding_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from domain.base import utcnow_iso
from domain.models import (
    AccountStatus,
    ApprovalStatus,
    AuthProvider,
    Facility,
    Organisation,
    OrganisationType,
    Role,
    User,
)
from repositories.mongo.facility_repository import facility_repository
from repositories.mongo.organisation_repository import organisation_repository
from repositories.mongo.user_repository import user_repository
from services import audit_service

GENERIC_CREATE_ERROR = "We couldn't create the account with those details."


async def _ensure_email_free(email: str) -> None:
    if await user_repository.find_by_email(email):
        raise ConflictError(code="email_unavailable", message=GENERIC_CREATE_ERROR)


async def register_hospital(
    *,
    organisation_name: str,
    primary_facility_name: str,
    full_name: str,
    email: str,
    password: Optional[str] = None,
    job_title: Optional[str] = None,
    organisation_subtype: Optional[str] = None,
    authentication_provider: AuthProvider = AuthProvider.PASSWORD,
    provider_subject: Optional[str] = None,
) -> User:
    email = email.lower()
    await _ensure_email_free(email)

    org = await organisation_repository.create(
        Organisation(
            name=organisation_name,
            organisation_type=OrganisationType.HOSPITAL,
            subtype=organisation_subtype,
            approval_status=ApprovalStatus.PENDING,
        )
    )
    try:
        facility = await facility_repository.create(
            Facility(organisation_id=org.id, name=primary_facility_name, facility_type="HOSPITAL")
        )
        # The unique index on users.email (migration 0002) is the authoritative
        # guard; a DuplicateKeyError here triggers the compensating cleanup below.
        user = await user_repository.create(
            User(
                organisation_id=org.id,
                email=email,
                full_name=full_name,
                role=Role.HOSPITAL,
                job_title=job_title,
                authentication_provider=authentication_provider,
                provider_subject=provider_subject,
                password_hash=hash_password(password) if password else None,
                primary_facility_id=facility.id,
            )
        )
    except Exception:
        # Compensating cleanup (standalone MongoDB has no multi-doc transactions).
        await organisation_repository.delete(org.id)
        await facility_repository.collection.delete_many({"organisation_id": org.id})
        raise ConflictError(code="email_unavailable", message=GENERIC_CREATE_ERROR)

    await audit_service.record_event(
        "organisation.created", actor=user, target_type="organisation", target_id=org.id,
        organisation_id=org.id, meta={"type": "HOSPITAL"},
    )
    await audit_service.record_event("account.created", actor=user, target_type="user", target_id=user.id)
    return user


async def register_supplier(
    *,
    organisation_name: str,
    full_name: str,
    email: str,
    password: Optional[str] = None,
    organisation_subtype: Optional[str] = None,
    job_title: Optional[str] = None,
    authentication_provider: AuthProvider = AuthProvider.PASSWORD,
    provider_subject: Optional[str] = None,
) -> User:
    email = email.lower()
    await _ensure_email_free(email)

    org = await organisation_repository.create(
        Organisation(
            name=organisation_name,
            organisation_type=OrganisationType.SUPPLIER,
            subtype=organisation_subtype,
            approval_status=ApprovalStatus.PENDING,
        )
    )
    try:
        user = await user_repository.create(
            User(
                organisation_id=org.id,
                email=email,
                full_name=full_name,
                role=Role.SUPPLIER,
                job_title=job_title,
                authentication_provider=authentication_provider,
                provider_subject=provider_subject,
                password_hash=hash_password(password) if password else None,
            )
        )
    except Exception:
        await organisation_repository.delete(org.id)
        raise ConflictError(code="email_unavailable", message=GENERIC_CREATE_ERROR)

    await audit_service.record_event(
        "organisation.created", actor=user, target_type="organisation", target_id=org.id,
        organisation_id=org.id, meta={"type": "SUPPLIER"},
    )
    await audit_service.record_event("account.created", actor=user, target_type="user", target_id=user.id)
    return user


async def authenticate(email: str, password: str, ip: str):
    email = email.lower()
    # Key brute-force lockout on the account (email), not the spoofable client IP.
    identifier = f"login:{email}"
    if await login_locked(identifier):
        raise AppError(
            "Too many attempts. Please wait a few minutes and try again.",
            code="rate_limited",
            status_code=429,
        )
    user = await user_repository.find_by_email(email)
    if (
        not user
        or user.authentication_provider != AuthProvider.PASSWORD
        or not user.password_hash
        or not verify_password(password, user.password_hash)
    ):
        await record_login_failure(identifier)
        raise AuthError(code="invalid_credentials", message="Invalid email or password.")

    await clear_login_failures(identifier)
    await user_repository.update(user.id, {"last_login_at": utcnow_iso()})
    await audit_service.record_event("user.login", actor=user, meta={"provider": "password"})
    return user, create_access_token(user.id), create_refresh_token(user.id)


# ---- Google identity ----------------------------------------------------
async def _google_session_data(session_id: str) -> dict:
    url = f"{settings.EMERGENT_AUTH_BASE}/auth/v1/env/oauth/session-data"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers={"X-Session-ID": session_id})
    except Exception:  # noqa: BLE001
        raise AuthError(code="google_failed", message="Google sign-in could not be completed.")
    if resp.status_code != 200:
        raise AuthError(code="google_failed", message="Google sign-in could not be completed.")
    data = resp.json()
    return {
        "email": (data.get("email") or "").lower(),
        "name": data.get("name") or data.get("email"),
        "sub": data.get("id"),
    }


async def google_login_or_onboard(session_id: str):
    info = await _google_session_data(session_id)
    if not info["email"]:
        raise AuthError(code="google_failed", message="Google sign-in could not be completed.")

    user = await user_repository.find_by_email(info["email"])
    if user:
        changes = {"last_login_at": utcnow_iso()}
        if not user.provider_subject:
            changes["provider_subject"] = info["sub"]
        await user_repository.update(user.id, changes)
        await audit_service.record_event("user.login", actor=user, meta={"provider": "google"})
        return {
            "status": "authenticated",
            "user": user,
            "access": create_access_token(user.id),
            "refresh": create_refresh_token(user.id),
        }

    return {
        "status": "onboarding_required",
        "email": info["email"],
        "name": info["name"],
        "onboarding": create_onboarding_token(info["email"], info["name"], info["sub"] or ""),
    }


async def google_complete(
    *,
    onboarding_token: str,
    role: str,
    organisation_name: str,
    full_name: str,
    primary_facility_name: Optional[str] = None,
    organisation_subtype: Optional[str] = None,
):
    try:
        payload = decode_token(onboarding_token, expected_type="onboarding")
    except Exception:  # noqa: BLE001
        raise AuthError(code="onboarding_expired", message="Your sign-in session expired. Please try again.")

    if role not in (Role.HOSPITAL.value, Role.SUPPLIER.value):
        raise ValidationAppError(message="Invalid organisation role.")

    email = payload["email"]
    subject = payload.get("sub")
    await _ensure_email_free(email)

    if role == Role.HOSPITAL.value:
        user = await register_hospital(
            organisation_name=organisation_name,
            primary_facility_name=primary_facility_name or f"{organisation_name} — Main",
            full_name=full_name,
            email=email,
            organisation_subtype=organisation_subtype,
            authentication_provider=AuthProvider.GOOGLE,
            provider_subject=subject,
        )
    else:
        user = await register_supplier(
            organisation_name=organisation_name,
            full_name=full_name,
            email=email,
            organisation_subtype=organisation_subtype,
            authentication_provider=AuthProvider.GOOGLE,
            provider_subject=subject,
        )

    return user, create_access_token(user.id), create_refresh_token(user.id)


async def refresh_access(refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token, expected_type="refresh")
    except Exception:  # noqa: BLE001
        raise AuthError(message="Your session has expired. Please sign in again.")
    user = await user_repository.get(payload["sub"])
    if not user:
        raise AuthError(message="Your session is no longer valid.")
    if user.sessions_valid_after and payload.get("iat", 0) < user.sessions_valid_after:
        raise AuthError(message="Your session has ended. Please sign in again.")
    return create_access_token(user.id)


async def invalidate_sessions(user_id: str) -> None:
    """Server-side logout: reject all tokens issued before now."""
    await user_repository.update(
        user_id, {"sessions_valid_after": int(datetime.now(timezone.utc).timestamp())}
    )


async def seed_admin() -> None:
    email = settings.ADMIN_EMAIL.lower()
    existing = await user_repository.find_by_email(email)
    if not existing:
        await user_repository.create(
            User(
                organisation_id=None,
                email=email,
                full_name="CARE-E Administrator",
                role=Role.ADMIN,
                account_status=AccountStatus.ACTIVE,
                authentication_provider=AuthProvider.PASSWORD,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
            )
        )
        await audit_service.record_event("admin.seeded", meta={"email": email})
        return

    changes = {}
    if existing.role != Role.ADMIN:
        changes["role"] = Role.ADMIN.value
    if (
        existing.authentication_provider == AuthProvider.PASSWORD
        and existing.password_hash
        and not verify_password(settings.ADMIN_PASSWORD, existing.password_hash)
    ):
        changes["password_hash"] = hash_password(settings.ADMIN_PASSWORD)
    if changes:
        await user_repository.update(existing.id, changes)
