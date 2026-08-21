"""Security primitives: password hashing, JWT tokens, auth cookies.

Authentication transport is HttpOnly cookies. The frontend never reads a raw
token. Google sign-in (identity) is converted into the *same* JWT session, so
there is a single session mechanism to reason about.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Response

from core.config import settings

ALGORITHM = "HS256"

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
ONBOARDING_COOKIE = "onboarding_token"


# ---- Password hashing ---------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:  # noqa: BLE001
        return False


# ---- JWT ----------------------------------------------------------------
def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return _encode(
        {
            "sub": user_id,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.ACCESS_TTL_MIN),
        }
    )


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return _encode(
        {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=settings.REFRESH_TTL_DAYS),
        }
    )


def create_onboarding_token(email: str, name: str, subject: str) -> str:
    return _encode(
        {
            "email": email,
            "name": name,
            "sub": subject,
            "type": "onboarding",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ONBOARDING_TTL_MIN),
        }
    )


def decode_token(token: str, expected_type: str | None = None) -> dict:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload


# ---- Cookies ------------------------------------------------------------
def _set(response: Response, key: str, value: str, max_age: int) -> None:
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    _set(response, ACCESS_COOKIE, access, settings.ACCESS_TTL_MIN * 60)
    _set(response, REFRESH_COOKIE, refresh, settings.REFRESH_TTL_DAYS * 86400)


def set_onboarding_cookie(response: Response, token: str) -> None:
    _set(response, ONBOARDING_COOKIE, token, settings.ONBOARDING_TTL_MIN * 60)


def clear_auth_cookies(response: Response) -> None:
    # Overwrite with matching attributes + immediate expiry. delete_cookie drops
    # Secure/SameSite, which some clients require to match before removing.
    for key in (ACCESS_COOKIE, REFRESH_COOKIE, ONBOARDING_COOKIE):
        response.set_cookie(
            key=key,
            value="",
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=0,
            path="/",
        )
