"""M1 identity/authz tests: unit + integration + cross-organisation security."""
import time

from fastapi.testclient import TestClient

from core.config import settings
from server import app

API = "/api/v1"


def _uniq(prefix: str) -> str:
    return f"{prefix}.{int(time.time() * 1000000)}@example.com"


def _register_hospital(client, email, org="Synthetic Health"):
    return client.post(
        f"{API}/auth/register/hospital",
        json={
            "organisation_name": org,
            "primary_facility_name": f"{org} Main",
            "full_name": "Test User",
            "email": email,
            "password": "password123",
        },
    )


# ---- Unit ---------------------------------------------------------------
def test_password_hashing_roundtrip():
    from core.security import hash_password, verify_password

    h = hash_password("password123")
    assert h.startswith("$2b$")
    assert verify_password("password123", h)
    assert not verify_password("wrong", h)


def test_approval_transitions():
    from domain.models import ApprovalStatus as A
    from services.organisation_service import validate_transition

    assert validate_transition(A.PENDING, A.APPROVED)
    assert validate_transition(A.PENDING, A.REJECTED)
    assert validate_transition(A.APPROVED, A.SUSPENDED)
    assert validate_transition(A.SUSPENDED, A.APPROVED)
    assert not validate_transition(A.PENDING, A.SUSPENDED)
    assert not validate_transition(A.REJECTED, A.APPROVED)


# ---- Integration --------------------------------------------------------
def test_unauthenticated_blocked():
    with TestClient(app) as c:
        assert c.get(f"{API}/auth/me").status_code == 401
        assert c.get(f"{API}/facilities").status_code == 401


def test_hospital_registration_is_pending_and_blocked():
    with TestClient(app) as c:
        r = _register_hospital(c, _uniq("hosp"))
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["can_access_app"] is False
        assert body["organisation"]["approval_status"] == "PENDING"
        # session established (pending) -> /me works
        assert c.get(f"{API}/auth/me").status_code == 200
        # protected operational endpoint blocked while pending
        assert c.post(f"{API}/facilities", json={"name": "New Wing"}).status_code == 403


def test_admin_login_and_approval_flow():
    email = _uniq("supp")
    with TestClient(app) as c:
        r = c.post(
            f"{API}/auth/register/supplier",
            json={"organisation_name": "Synthetic Supplies", "full_name": "Sup User", "email": email, "password": "password123"},
        )
        assert r.status_code == 201
        org_id = r.json()["organisation"]["id"]

    with TestClient(app) as admin:
        lr = admin.post(f"{API}/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
        assert lr.status_code == 200, lr.text
        assert lr.json()["user"]["role"] == "ADMIN"
        pr = admin.patch(f"{API}/organisations/{org_id}", json={"approval_status": "APPROVED"})
        assert pr.status_code == 200, pr.text
        assert pr.json()["organisation"]["approval_status"] == "APPROVED"
        # invalid transition APPROVED -> PENDING
        assert admin.patch(f"{API}/organisations/{org_id}", json={"approval_status": "PENDING"}).status_code == 409


def test_cross_org_access_denied():
    with TestClient(app) as ca:
        ra = _register_hospital(ca, _uniq("orgA"), org="Org A")
        org_a = ra.json()["organisation"]["id"]

    with TestClient(app) as cb:
        _register_hospital(cb, _uniq("orgB"), org="Org B")
        # user B (authenticated) requests Org A -> 403
        assert cb.get(f"{API}/organisations/{org_a}").status_code == 403


def test_non_admin_cannot_approve():
    with TestClient(app) as c:
        r = _register_hospital(c, _uniq("noadmin"))
        org_id = r.json()["organisation"]["id"]
        # a normal user attempting to approve its own org
        assert c.patch(f"{API}/organisations/{org_id}", json={"approval_status": "APPROVED"}).status_code == 403


def test_suspended_org_blocks_access():
    email = _uniq("susp")
    with TestClient(app) as c:
        r = _register_hospital(c, email, org="Suspend Co")
        org_id = r.json()["organisation"]["id"]

    with TestClient(app) as admin:
        admin.post(f"{API}/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
        assert admin.patch(f"{API}/organisations/{org_id}", json={"approval_status": "APPROVED"}).status_code == 200
        assert admin.patch(f"{API}/organisations/{org_id}", json={"approval_status": "SUSPENDED"}).status_code == 200

    with TestClient(app) as c2:
        lr = c2.post(f"{API}/auth/login", json={"email": email, "password": "password123"})
        assert lr.status_code == 200  # login (identity) succeeds
        resp = c2.get(f"{API}/facilities")  # protected -> blocked
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "org_suspended"


def test_logout_invalidates_session():
    with TestClient(app) as c:
        _register_hospital(c, _uniq("logout"))
        assert c.get(f"{API}/auth/me").status_code == 200
        assert c.post(f"{API}/auth/logout").status_code == 200
        assert c.get(f"{API}/auth/me").status_code == 401
