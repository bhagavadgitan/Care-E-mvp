"""Iteration-2 live regression suite (external preview URL).

Covers the fixes reported by the developer agent:
  * logout performs server-side session invalidation (token replay -> 401)
  * registration throttle keyed per-email (distinct emails all succeed)
  * login brute-force lockout keyed on email only (other email unaffected)
  * PENDING org access blocks + cross-org isolation
  * Cache-Control: no-store on /api responses
  * admin approvals API (list + PATCH status)
"""
import os
import time
import uuid

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

RUN = f"{int(time.time())}.{uuid.uuid4().hex[:6]}"


def _email(prefix):
    return f"test_{prefix}.{RUN}@example.com"


def _session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _cb():
    return f"?_={uuid.uuid4().hex}"


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
        json={
            "organisation_name": org,
            "full_name": "TEST Supplier User",
            "email": email,
            "password": PWD,
        },
    )


# ---------------------------------------------------------------- logout / session invalidation
class TestLogoutInvalidation:
    def test_logout_invalidates_token_replay(self):
        s = _session()
        email = _email("logout")
        r = _register_hospital(s, email, f"TEST Logout Org {RUN}")
        assert r.status_code == 201, r.text
        token = s.cookies.get("access_token")
        assert token, f"access_token cookie not set: {s.cookies.get_dict()}"

        # authenticated read works with the raw token
        bearer = {"Authorization": f"Bearer {token}"}
        r = requests.get(f"{API}/auth/me{_cb()}", headers=bearer)
        assert r.status_code == 200, r.text
        assert r.json()["user"]["email"] == email

        # logout (immediately after issuance — exposes the 1s iat/sessions_valid_after
        # truncation race: sessions_valid_after == iat and the check uses `<`)
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200, r.text

        time.sleep(1.5)
        r = requests.get(f"{API}/auth/me{_cb()}", headers=bearer)
        assert r.status_code == 401, f"replayed token still valid: {r.status_code} {r.text[:200]}"

    def test_logout_invalidates_token_replay_after_delay(self):
        """Same flow but with >1s between token issuance and logout (passes today)."""
        s = _session()
        email = _email("logoutdelay")
        r = _register_hospital(s, email, f"TEST Logout Delay Org {RUN}")
        assert r.status_code == 201, r.text
        token = s.cookies.get("access_token")
        time.sleep(2.5)
        assert s.post(f"{API}/auth/logout").status_code == 200
        time.sleep(1)
        r = requests.get(f"{API}/auth/me{_cb()}", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, f"replayed token still valid: {r.status_code} {r.text[:200]}"


    def test_no_store_cache_header_on_api(self):
        r = requests.get(f"{API}/auth/me{_cb()}")
        assert r.status_code == 401
        assert "no-store" in (r.headers.get("cache-control") or "").lower(), r.headers


# ---------------------------------------------------------------- registration throttle keyed per email
class TestRegisterThrottlePerEmail:
    def test_distinct_emails_all_succeed(self):
        for i in range(6):
            s = _session()
            email = _email(f"throttle{i}")
            r = _register_hospital(s, email, f"TEST Throttle Org {RUN}-{i}")
            assert r.status_code == 201, f"distinct email #{i} rejected: {r.status_code} {r.text[:200]}"
            body = r.json()
            assert body["user"]["email"] == email
            assert body["organisation"]["approval_status"] == "PENDING"

    def test_same_email_throttled_after_five(self):
        email = _email("samemail")
        codes = []
        for i in range(6):
            s = _session()
            codes.append(_register_hospital(s, email, f"TEST Same Org {RUN}-{i}").status_code)
        assert codes[0] == 201, codes
        assert codes[-1] == 429, f"expected 429 on 6th attempt for same email, got {codes}"


# ---------------------------------------------------------------- login lockout keyed on email
class TestLoginLockoutPerEmail:
    def test_lockout_is_email_scoped(self):
        s = _session()
        victim = _email("lockvictim")
        other = _email("lockother")
        assert _register_hospital(s, victim, f"TEST Lock Org {RUN}").status_code == 201
        s2 = _session()
        assert _register_hospital(s2, other, f"TEST Lock Other Org {RUN}").status_code == 201

        codes = []
        for _ in range(5):
            codes.append(
                requests.post(f"{API}/auth/login", json={"email": victim, "password": "wrong-pass"}).status_code
            )
        assert all(c in (401, 429) for c in codes), codes

        r = requests.post(f"{API}/auth/login", json={"email": victim, "password": PWD})
        assert r.status_code == 429, f"victim email not locked out: {r.status_code} {r.text[:200]}"

        r = requests.post(f"{API}/auth/login", json={"email": other, "password": PWD})
        assert r.status_code == 200, f"different email affected by lockout: {r.status_code} {r.text[:200]}"


# ---------------------------------------------------------------- pending gating + cross-org isolation
class TestPendingAndIsolation:
    def test_pending_blocked_and_cross_org_403(self):
        s1 = _session()
        e1 = _email("pend1")
        r = _register_hospital(s1, e1, f"TEST Pend Org A {RUN}")
        assert r.status_code == 201, r.text
        org1 = r.json()["organisation"]["id"]

        r = s1.get(f"{API}/facilities{_cb()}")
        assert r.status_code == 403, r.text
        assert r.json()["error"]["code"] == "org_pending", r.text

        s2 = _session()
        e2 = _email("pend2")
        r = _register_supplier(s2, e2, f"TEST Pend Org B {RUN}")
        assert r.status_code == 201, r.text

        r = s2.get(f"{API}/organisations/{org1}{_cb()}")
        assert r.status_code == 403, f"cross-org read allowed: {r.status_code} {r.text[:200]}"

        # own org readable
        r = s2.get(f"{API}/organisations/me{_cb()}")
        assert r.status_code == 200, r.text
        assert r.json()["organisation"]["approval_status"] == "PENDING"


# ---------------------------------------------------------------- admin approvals API
class TestAdminApprovals:
    def test_admin_can_list_and_approve(self):
        h = _session()
        hemail = _email("approve")
        r = _register_hospital(h, hemail, f"TEST Approve Org {RUN}")
        assert r.status_code == 201, r.text
        org_id = r.json()["organisation"]["id"]

        a = _session()
        r = a.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:300]}"
        assert r.json()["user"]["role"] == "ADMIN"

        r = a.get(f"{API}/organisations{_cb()}")
        assert r.status_code == 200, r.text
        orgs = r.json()["organisations"]
        row = next((o for o in orgs if o["id"] == org_id), None)
        assert row is not None, "new org missing from admin list"
        assert row["approval_status"] == "PENDING"
        assert all("_id" not in o for o in orgs), "mongo _id leaked"

        r = a.patch(f"{API}/organisations/{org_id}", json={"approval_status": "APPROVED"})
        assert r.status_code == 200, r.text
        assert r.json()["organisation"]["approval_status"] == "APPROVED"

        # persistence
        r = a.get(f"{API}/organisations/{org_id}{_cb()}")
        assert r.status_code == 200
        assert r.json()["organisation"]["approval_status"] == "APPROVED"

        # approved hospital user now gains operational access
        r = h.get(f"{API}/facilities{_cb()}")
        assert r.status_code == 200, f"approved org still blocked: {r.status_code} {r.text[:200]}"

    def test_non_admin_cannot_list_organisations(self):
        s = _session()
        r = _register_supplier(s, _email("nonadmin"), f"TEST NonAdmin Org {RUN}")
        assert r.status_code == 201, r.text
        r = s.get(f"{API}/organisations{_cb()}")
        assert r.status_code == 403, r.text
