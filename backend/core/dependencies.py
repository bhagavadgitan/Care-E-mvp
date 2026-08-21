"""Authorization dependencies enforced server-side.

Authentication (identity) is resolved from the HttpOnly cookie. Authorization
(role + organisation approval + ownership) is enforced here, never on the
frontend.
"""
from fastapi import Request

from core.exceptions import AppError, AuthError, ForbiddenError
from core.security import decode_token
from domain.models import AccountStatus, ApprovalStatus, Role, User
from repositories.mongo.organisation_repository import organisation_repository
from repositories.mongo.user_repository import user_repository


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get("access_token")
    if not token:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:]
    return token


async def get_current_user(request: Request) -> User:
    """Identity only. Works for PENDING/SUSPENDED users (e.g. /auth/me)."""
    token = _extract_token(request)
    if not token:
        raise AuthError()
    try:
        payload = decode_token(token, expected_type="access")
    except Exception:  # noqa: BLE001
        raise AuthError(message="Your session is invalid or has expired.")
    user = await user_repository.get(payload["sub"])
    if not user:
        raise AuthError(message="Your session is no longer valid.")
    sva = user.sessions_valid_after
    if sva and payload.get("iat", 0) < sva:
        raise AuthError(message="Your session has ended. Please sign in again.")
    return user


async def get_current_active_user(request: Request) -> User:
    """Identity + approval gating. Use for all protected operational endpoints."""
    user = await get_current_user(request)
    if user.account_status == AccountStatus.SUSPENDED:
        raise ForbiddenError(code="account_suspended", message="This account has been suspended.")
    if user.role == Role.ADMIN:
        return user

    org = await organisation_repository.get(user.organisation_id) if user.organisation_id else None
    if not org:
        raise ForbiddenError(code="no_organisation", message="No organisation is associated with this account.")
    if org.approval_status == ApprovalStatus.PENDING:
        raise ForbiddenError(code="org_pending", message="Your organisation is awaiting CARE-E approval.")
    if org.approval_status == ApprovalStatus.REJECTED:
        raise ForbiddenError(code="org_rejected", message="Your organisation has not been approved for access.")
    if org.approval_status == ApprovalStatus.SUSPENDED:
        raise ForbiddenError(code="org_suspended", message="Access to this CARE-E account has been suspended.")
    return user


def require_role(*roles: Role):
    async def dependency(request: Request) -> User:
        user = await get_current_active_user(request)
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency


async def get_admin(request: Request) -> User:
    user = await get_current_active_user(request)
    if user.role != Role.ADMIN:
        raise ForbiddenError()
    return user


def assert_org_access(user: User, organisation_id: str) -> None:
    if user.role == Role.ADMIN:
        return
    if user.organisation_id != organisation_id:
        raise ForbiddenError()


def assert_facility_access(user: User, facility) -> None:
    if user.role == Role.ADMIN:
        return
    if not facility or facility.organisation_id != user.organisation_id:
        raise ForbiddenError()
