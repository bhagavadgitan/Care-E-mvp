"""Authentication & registration endpoints."""
from fastapi import APIRouter, Depends, Request, Response

from core.config import settings
from core.dependencies import get_current_user
from core.exceptions import AppError, AuthError
from core.rate_limit import check_and_hit
from core.security import (
    ACCESS_COOKIE,
    ONBOARDING_COOKIE,
    REFRESH_COOKIE,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    set_auth_cookies,
    set_onboarding_cookie,
)
from schemas.auth import (
    GoogleCallbackRequest,
    GoogleCompleteRequest,
    HospitalRegisterRequest,
    LoginRequest,
    SupplierRegisterRequest,
)
from services import auth_service
from services.presenter import build_me

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _throttle_register(email: str) -> None:
    # Key on the target email — the client IP is shared behind the ingress and
    # X-Forwarded-For is caller-supplied (spoofable), so it is not trustworthy.
    if not await check_and_hit(f"register:{email.lower()}", 5, 3600):
        raise AppError(
            "Too many registration attempts for this email. Please try again later.",
            code="rate_limited",
            status_code=429,
        )


@router.post("/register/hospital", status_code=201)
async def register_hospital(payload: HospitalRegisterRequest, request: Request, response: Response):
    await _throttle_register(payload.email)
    user = await auth_service.register_hospital(**payload.model_dump())
    set_auth_cookies(response, create_access_token(user.id), create_refresh_token(user.id))
    return await build_me(user)


@router.post("/register/supplier", status_code=201)
async def register_supplier(payload: SupplierRegisterRequest, request: Request, response: Response):
    await _throttle_register(payload.email)
    user = await auth_service.register_supplier(**payload.model_dump())
    set_auth_cookies(response, create_access_token(user.id), create_refresh_token(user.id))
    return await build_me(user)


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response):
    user, access, refresh = await auth_service.authenticate(payload.email, payload.password, _client_ip(request))
    set_auth_cookies(response, access, refresh)
    return await build_me(user)


@router.post("/logout")
async def logout(request: Request, response: Response):
    # Server-side invalidation so previously issued tokens stop working even if
    # a proxy-mangled cookie lingers on the client.
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        try:
            payload = decode_token(token, expected_type="access")
            await auth_service.invalidate_sessions(payload["sub"])
        except Exception:  # noqa: BLE001
            pass
    clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return await build_me(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise AuthError()
    access = await auth_service.refresh_access(token)
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TTL_MIN * 60,
        path="/",
    )
    return {"status": "ok"}


@router.post("/google/callback")
async def google_callback(payload: GoogleCallbackRequest, response: Response):
    result = await auth_service.google_login_or_onboard(payload.session_id)
    if result["status"] == "authenticated":
        set_auth_cookies(response, result["access"], result["refresh"])
        return {"status": "authenticated", "me": await build_me(result["user"])}
    set_onboarding_cookie(response, result["onboarding"])
    return {"status": "onboarding_required", "email": result["email"], "name": result["name"]}


@router.post("/google/complete", status_code=201)
async def google_complete(payload: GoogleCompleteRequest, request: Request, response: Response):
    token = request.cookies.get(ONBOARDING_COOKIE)
    if not token:
        raise AuthError(message="Your sign-in session expired. Please try again.")
    user, access, refresh = await auth_service.google_complete(
        onboarding_token=token,
        role=payload.role.value,
        organisation_name=payload.organisation_name,
        full_name=payload.full_name,
        primary_facility_name=payload.primary_facility_name,
        organisation_subtype=payload.organisation_subtype,
    )
    set_auth_cookies(response, access, refresh)
    response.delete_cookie(ONBOARDING_COOKIE, path="/")
    return await build_me(user)
