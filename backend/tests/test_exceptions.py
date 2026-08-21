"""Unit tests for the application error hierarchy."""
from core.exceptions import (
    AppError,
    AuthError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationAppError,
)


def test_default_app_error():
    err = AppError()
    assert err.status_code == 500
    assert err.code == "internal_error"


def test_specific_errors_have_expected_codes():
    assert NotFoundError().status_code == 404
    assert ValidationAppError().status_code == 400
    assert AuthError().status_code == 401
    assert ForbiddenError().status_code == 403
    assert ConflictError().status_code == 409


def test_app_error_overrides():
    err = AppError("boom", code="custom", status_code=418, details={"x": 1})
    assert err.message == "boom"
    assert err.code == "custom"
    assert err.status_code == 418
    assert err.details == {"x": 1}
