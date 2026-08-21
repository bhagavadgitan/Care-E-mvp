"""Live (external URL) M1 identity/authz API tests.

Runs against REACT_APP_BACKEND_URL so cookie transport (HttpOnly/Secure/SameSite=None)
and Kubernetes ingress routing are exercised exactly as the browser sees them.
"""
import os
import time

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api/v1"

ADMIN_EMAIL = "bhagavadgitan.b@gmail.com"
ADMIN_PASSWORD = "Care3-T6q4MN5bpfjw"
PWD = "password123"

RUN = str(int(time.time()))
WORKER = os.environ.get("PYTEST_XDIST_WORKER", "main")


def _email(prefix):
    return f"TEST_{prefix}.{RUN}.{WORKER}@example.com".lower()


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _guard_rate_limit(r):
    """Registration is throttled to 20/hour per client IP. Every external request to
    the preview URL shares one ingress IP, so repeated full-suite runs can exhaust it.
    Skip (not fail) so the throttle isn't misreported as a product defect."""
    if r.status_code == 429:
        pytest.skip("register endpoint throttled (20/hour per IP) — rerun after the window resets")


def _register_hospital(s, email, org):
    return s.post(
        f"{API}/auth/register/hospital",
        json={
            "organisation_name": org,
            "primary_facility_name": f"{org} Main",
            "full_name": "TEST Hospital User",
            "email": email,
            "password": PWD,
        },
    )


def _register_supplier(s, email, org):
    return s.post(
        f"{API}/auth/register/supplier",
        json={"organisation_name": org, "full_name": "TEST Supplier User", "email": email, "password": PWD},
    )


@pytest.fixture(scope="module")
def admin():
    s = _session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.fail(f"Admin login failed {r.status_code}: {r.text[:300]}")
    body = r.json()
    assert body["user"]["role"] == "ADMIN"
    assert body["can_access_app"] is True
    assert body.get("organisation") is None
    return s


@pytest.fixture(scope="module")
def hospital_a():
    """Registered hospital org A (PENDING)."""
    s = _session()
    email = _email("hospa")
    r = _register_hospital(s, email, "TEST Org A Hospital")
    _guard_rate_limit(r)
    assert r.status_code == 201, r.text
    body = r.json()
    return {"session": s, "email": email, "body": body, "org_id": body["organisation"]["id"]}


@pytest.fixture(scope="module")
def supplier_a():
    s = _session()
    email = _email("suppa")
    r = _register_supplier(s, email, "TEST Supplies Co")
    _guard_rate_limit(r)
    assert r.status_code == 201, r.text
    body = r.json()
    return {"session": s, "email": email, "body": body, "org_id": body["organisation"]["id"]}


# ---- Unauthenticated ----------------------------------------------------
class TestUnauthenticated:
    def test_me_401(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401
        assert "error" in r.json()

    def test_facilities_401(self):
        assert requests.get(f"{API}/facilities").status_code == 401

    def test_organisations_401(self):
        assert requests.get(f"{API}/organisations").status_code == 401

    def test_users_me_401(self):
        assert requests.get(f"{API}/users/me").status_code == 401

    def test_bad_token_401(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer not.a.token"})
        assert r.status_code == 401


# ---- Registration & pending gating -------------------------------------
class TestRegistrationPending:
    def test_hospital_registration_pending(self, hospital_a):
        body = hospital_a["body"]
        assert body["can_access_app"] is False
        assert body["organisation"]["approval_status"] == "PENDING"
        assert body["user"]["role"] == "HOSPITAL"
        assert "password_hash" not in str(body)

    def test_supplier_registration_pending(self, supplier_a):
        body = supplier_a["body"]
        assert body["can_access_app"] is False
        assert body["organisation"]["approval_status"] == "PENDING"
        assert body["user"]["role"] == "SUPPLIER"
        assert body["organisation"]["organisation_type"] == "SUPPLIER"

    def test_me_works_while_pending(self, hospital_a):
        r = hospital_a["session"].get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["user"]["email"] == hospital_a["email"]
        assert r.json()["can_access_app"] is False

    def test_facilities_403_org_pending(self, hospital_a):
        r = hospital_a["session"].get(f"{API}/facilities")
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "org_pending"

    def test_create_facility_403_while_pending(self, hospital_a):
        r = hospital_a["session"].post(f"{API}/facilities", json={"name": "TEST New Wing"})
        assert r.status_code == 403

    def test_duplicate_email_rejected(self, hospital_a):
        r = _register_hospital(_session(), hospital_a["email"], "TEST Dup Org")
        _guard_rate_limit(r)
        assert r.status_code == 409, r.text

    def test_short_password_rejected(self):
        r = _session().post(
            f"{API}/auth/register/supplier",
            json={"organisation_name": "TEST X", "full_name": "N", "email": _email("shortpw2"), "password": "123"},
        )
        assert r.status_code in (400, 422)


# ---- Authorization / isolation -----------------------------------------
class TestAuthorization:
    def test_cross_org_denied(self, hospital_a, supplier_a):
        # supplier requesting hospital org id
        assert supplier_a["session"].get(f"{API}/organisations/{hospital_a['org_id']}").status_code == 403
        # hospital requesting supplier org id
        assert hospital_a["session"].get(f"{API}/organisations/{supplier_a['org_id']}").status_code == 403

    def test_own_org_allowed(self, hospital_a):
        r = hospital_a["session"].get(f"{API}/organisations/{hospital_a['org_id']}")
        assert r.status_code == 200
        assert r.json()["organisation"]["id"] == hospital_a["org_id"]

    def test_non_admin_cannot_list_orgs(self, hospital_a):
        assert hospital_a["session"].get(f"{API}/organisations").status_code == 403

    def test_non_admin_cannot_approve(self, hospital_a):
        r = hospital_a["session"].patch(
            f"{API}/organisations/{hospital_a['org_id']}", json={"approval_status": "APPROVED"}
        )
        assert r.status_code == 403


# ---- Admin approval lifecycle ------------------------------------------
class TestApprovalLifecycle:
    def test_admin_can_list_pending(self, admin):
        r = admin.get(f"{API}/organisations", params={"status": "PENDING"})
        assert r.status_code == 200
        assert all(o["approval_status"] == "PENDING" for o in r.json()["organisations"])

    def test_approve_then_invalid_transition(self, admin, hospital_a):
        r = admin.patch(f"{API}/organisations/{hospital_a['org_id']}", json={"approval_status": "APPROVED"})
        assert r.status_code == 200, r.text
        assert r.json()["organisation"]["approval_status"] == "APPROVED"
        # persistence
        g = admin.get(f"{API}/organisations/{hospital_a['org_id']}")
        assert g.json()["organisation"]["approval_status"] == "APPROVED"
        # invalid APPROVED -> PENDING
        bad = admin.patch(f"{API}/organisations/{hospital_a['org_id']}", json={"approval_status": "PENDING"})
        assert bad.status_code == 409, bad.text

    def test_approved_user_gains_access(self, hospital_a):
        s = _session()
        r = s.post(f"{API}/auth/login", json={"email": hospital_a["email"], "password": PWD})
        assert r.status_code == 200, r.text
        assert r.json()["can_access_app"] is True
        f = s.get(f"{API}/facilities")
        assert f.status_code == 200, f.text
        assert isinstance(f.json()["facilities"], list)
        assert len(f.json()["facilities"]) >= 1

    def test_suspend_blocks_operational_access(self, admin, hospital_a):
        r = admin.patch(f"{API}/organisations/{hospital_a['org_id']}", json={"approval_status": "SUSPENDED"})
        assert r.status_code == 200, r.text
        s = _session()
        lr = s.post(f"{API}/auth/login", json={"email": hospital_a["email"], "password": PWD})
        assert lr.status_code == 200  # identity still works
        assert lr.json()["can_access_app"] is False
        f = s.get(f"{API}/facilities")
        assert f.status_code == 403
        assert f.json()["error"]["code"] == "org_suspended"
        # restore for later tests
        admin.patch(f"{API}/organisations/{hospital_a['org_id']}", json={"approval_status": "APPROVED"})

    def test_supplier_approval(self, admin, supplier_a):
        r = admin.patch(f"{API}/organisations/{supplier_a['org_id']}", json={"approval_status": "APPROVED"})
        assert r.status_code == 200, r.text
        s = _session()
        lr = s.post(f"{API}/auth/login", json={"email": supplier_a["email"], "password": PWD})
        assert lr.json()["can_access_app"] is True

    def test_admin_get_any_org(self, admin, supplier_a):
        assert admin.get(f"{API}/organisations/{supplier_a['org_id']}").status_code == 200


# ---- Profile ------------------------------------------------------------
class TestProfile:
    def test_update_full_name_persists(self, supplier_a):
        s = supplier_a["session"]
        r = s.patch(f"{API}/users/me", json={"full_name": "TEST Renamed User"})
        assert r.status_code == 200, r.text
        assert r.json()["user"]["full_name"] == "TEST Renamed User"
        g = s.get(f"{API}/users/me")
        assert g.json()["user"]["full_name"] == "TEST Renamed User"
        assert "password_hash" not in str(g.json())


# ---- Session / logout / refresh ----------------------------------------
class TestSession:
    def test_logout_clears_session(self, hospital_a):
        s = _session()
        assert s.post(f"{API}/auth/login", json={"email": hospital_a["email"], "password": PWD}).status_code == 200
        assert s.get(f"{API}/auth/me").status_code == 200
        assert s.post(f"{API}/auth/logout").status_code == 200
        assert s.get(f"{API}/auth/me").status_code == 401

    def test_refresh_issues_new_access(self, hospital_a):
        s = _session()
        s.post(f"{API}/auth/login", json={"email": hospital_a["email"], "password": PWD})
        assert s.post(f"{API}/auth/refresh").status_code == 200
        assert s.get(f"{API}/auth/me").status_code == 200

    def test_refresh_without_cookie_401(self):
        assert requests.post(f"{API}/auth/refresh").status_code == 401

    def test_httponly_secure_cookies(self, hospital_a):
        r = requests.post(f"{API}/auth/login", json={"email": hospital_a["email"], "password": PWD})
        assert r.status_code == 200
        raw = r.headers.get("set-cookie", "")
        assert "access_token" in raw
        assert "HttpOnly" in raw
        assert "Secure" in raw


# ---- Brute force --------------------------------------------------------
class TestBruteForce:
    def test_lockout_after_failures(self):
        email = _email("brute")
        _guard_rate_limit(_register_supplier(_session(), email, "TEST Brute Co"))
        codes = []
        for _ in range(8):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrongpassword"})
            codes.append(r.status_code)
            if r.status_code == 429:
                break
        assert 429 in codes, f"No 429 lockout observed: {codes}"
        # correct password also locked out while window active
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": PWD})
        assert r.status_code == 429


# ---- Password storage ---------------------------------------------------
class TestPasswordStorage:
    def test_hash_is_bcrypt_in_db(self, hospital_a):
        import asyncio

        from motor.motor_asyncio import AsyncIOMotorClient

        mongo_url = dotenv_values("/app/backend/.env").get("MONGO_URL")
        db_name = dotenv_values("/app/backend/.env").get("DB_NAME")
        assert mongo_url and db_name

        async def _fetch():
            client = AsyncIOMotorClient(mongo_url)
            try:
                return await client[db_name]["users"].find_one({"email": hospital_a["email"]})
            finally:
                client.close()

        doc = asyncio.run(_fetch())
        assert doc is not None
        assert doc["password_hash"].startswith("$2b$")
