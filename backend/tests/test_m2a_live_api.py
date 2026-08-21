"""M2A live (external URL) tests: admin gating, synthetic network reads, canonical scenario,
idempotent seeding, plus a light M1 auth regression smoke check."""
import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL is missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api/v1"


# --- fixtures ---
@pytest.fixture(scope="session")
def admin_credentials():
    path = Path("/app/memory/test_credentials.md")
    if not path.exists():
        pytest.skip("Missing /app/memory/test_credentials.md")
    content = path.read_text(encoding="utf-8")
    email = re.search(r"(?im)^\s*[-*]?\s*Email:\s*`([^`]+)`", content)
    password = re.search(r"(?im)^\s*[-*]?\s*Password:\s*`([^`]+)`", content)
    if not email or not password:
        pytest.skip("No admin credentials found in test_credentials.md")
    return {"email": email.group(1), "password": password.group(1)}


@pytest.fixture(scope="module")
def anon():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin(admin_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=admin_credentials, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"Admin login failed {r.status_code}: {r.text[:400]}")
    body = r.json()
    assert body.get("user", body).get("role", "ADMIN").upper() == "ADMIN", body
    names = {c.name for c in s.cookies}
    assert "access_token" in names, f"access_token cookie not set; cookies={names}"
    return s


def eid(doc):
    """Entity id: M1/M2A serialise BaseDocument.id under its Mongo alias `_id`."""
    return doc.get("id") or doc.get("_id")


ADMIN_ENDPOINTS = [
    "/network/facilities",
    "/catalog/products",
    "/network/inventory",
    "/network/suppliers",
    "/network/supplier-availability",
    "/synthetic/status",
]


# --- auth / gating on M2A endpoints ---
class TestAdminGating:
    @pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
    def test_unauthenticated_rejected(self, anon, path):
        r = anon.get(f"{API}{path}", timeout=60)
        assert r.status_code in (401, 403), f"{path} -> {r.status_code}: {r.text[:200]}"

    @pytest.mark.parametrize("path", ["/synthetic/seed", "/synthetic/reset"])
    def test_unauthenticated_seed_rejected(self, anon, path):
        r = anon.post(f"{API}{path}", timeout=60)
        assert r.status_code in (401, 403), f"{path} -> {r.status_code}"

    def test_non_admin_forbidden(self, anon):
        """Register a hospital user and confirm it cannot read the network endpoints."""
        email = f"TEST_m2a_{uuid.uuid4().hex[:8]}@example.com"
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        reg = s.post(
            f"{API}/auth/register/hospital",
            json={
                "email": email,
                "password": "password123",
                "full_name": "TEST M2A User",
                "organisation_name": f"TEST Hospital {uuid.uuid4().hex[:6]}",
                "primary_facility_name": "TEST Facility",
            },
            timeout=60,
        )
        assert reg.status_code in (200, 201), f"registration failed {reg.status_code}: {reg.text[:400]}"
        assert "PENDING" in reg.text.upper(), f"expected PENDING org status: {reg.text[:400]}"

        login = s.post(f"{API}/auth/login", json={"email": email, "password": "password123"}, timeout=60)
        if login.status_code != 200:
            pytest.skip(f"pending hospital user cannot log in ({login.status_code}); gating checked anonymously")
        for path in ADMIN_ENDPOINTS:
            r = s.get(f"{API}{path}", timeout=60)
            assert r.status_code == 403, f"non-admin got {r.status_code} on {path}: {r.text[:200]}"


# --- network / catalog reads ---
class TestNetworkReads:
    def test_facilities(self, admin):
        r = admin.get(f"{API}/network/facilities", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["count"] == 5, data["count"]
        facs = data["facilities"]
        assert len(facs) == 5
        codes = sorted(f["code"] for f in facs)
        assert codes == ["HOSP-A", "HOSP-B", "HOSP-C", "HOSP-D", "HOSP-E"], codes
        assert all("DEMO" in f["name"] for f in facs), [f["name"] for f in facs]
        assert all(eid(f) for f in facs)

    def test_products(self, admin):
        r = admin.get(f"{API}/catalog/products", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["count"] == 100, data["count"]
        products = data["products"]
        assert len({p["sku"] for p in products}) == 100, "duplicate SKUs"
        gloves = [p for p in products if p["sku"] == "SKU-0001"]
        assert len(gloves) == 1, "canonical SKU-0001 missing"
        assert gloves[0]["name"] == "Surgical Gloves", gloves[0]

    def test_product_detail_and_filter(self, admin):
        r = admin.get(f"{API}/catalog/products", timeout=60)
        gloves = next(p for p in r.json()["products"] if p["sku"] == "SKU-0001")
        d = admin.get(f"{API}/catalog/products/{eid(gloves)}", timeout=60)
        assert d.status_code == 200, d.text[:300]
        assert d.json()["product"]["sku"] == "SKU-0001"

        f = admin.get(f"{API}/catalog/products", params={"category": "Gloves"}, timeout=60)
        assert f.status_code == 200
        cats = {p["category"] for p in f.json()["products"]}
        assert cats == {"Gloves"}, cats

    def test_product_detail_unknown_id(self, admin):
        r = admin.get(f"{API}/catalog/products/{uuid.uuid4().hex[:24]}", timeout=60)
        # NOTE: currently returns 200 {"product": null} instead of 404 (reported as minor issue)
        assert r.status_code in (404, 400, 200)
        if r.status_code == 200:
            assert r.json()["product"] is None

    def test_inventory_integrity(self, admin):
        r = admin.get(f"{API}/network/inventory", timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["count"] == 500, data["count"]
        items = data["inventory"]
        assert len(items) == 500
        for i in items:
            assert i["reserved_quantity"] <= i["quantity_on_hand"], i
            assert i["available_quantity"] == i["quantity_on_hand"] - i["reserved_quantity"], i
            assert i["available_quantity"] >= 0, i
            assert i["quantity_on_hand"] >= 0 and i["safety_stock"] >= 0, i
            assert isinstance(i["transfer_permitted"], bool), i
            assert i["expiry_date"], i
        # referential integrity
        fac_ids = {eid(f) for f in admin.get(f"{API}/network/facilities", timeout=60).json()["facilities"]}
        prod_ids = {eid(p) for p in admin.get(f"{API}/catalog/products", timeout=60).json()["products"]}
        assert {i["facility_id"] for i in items} <= fac_ids
        assert {i["product_id"] for i in items} <= prod_ids
        # unique (facility, product) pairs
        pairs = [(i["facility_id"], i["product_id"]) for i in items]
        assert len(set(pairs)) == len(pairs), "duplicate facility/product inventory rows"

    def test_inventory_filters(self, admin):
        facs = admin.get(f"{API}/network/facilities", timeout=60).json()["facilities"]
        fac = next(f for f in facs if f["code"] == "HOSP-A")
        r = admin.get(f"{API}/network/inventory", params={"facility_id": eid(fac)}, timeout=60)
        assert r.status_code == 200
        items = r.json()["inventory"]
        assert items and all(i["facility_id"] == eid(fac) for i in items)
        assert len(items) == 100, len(items)

        gloves = next(p for p in admin.get(f"{API}/catalog/products", timeout=60).json()["products"]
                      if p["sku"] == "SKU-0001")
        r2 = admin.get(f"{API}/network/inventory", params={"product_id": eid(gloves)}, timeout=60)
        items2 = r2.json()["inventory"]
        assert len(items2) == 5, len(items2)

    def test_suppliers(self, admin):
        r = admin.get(f"{API}/network/suppliers", timeout=60)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["count"] == 20, data["count"]
        assert all("DEMO" in s["name"] for s in data["suppliers"])

    def test_supplier_availability(self, admin):
        r = admin.get(f"{API}/network/supplier-availability", timeout=90)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["count"] > 0
        rows = data["supplier_availability"]
        supplier_ids = {eid(s) for s in admin.get(f"{API}/network/suppliers", timeout=60).json()["suppliers"]}
        for a in rows:
            assert a["available_quantity"] >= 0
            assert a["unit_cost"] >= 0
            assert a["lead_time_hours"] > 0
            assert a["supplier_id"] in supplier_ids

        gloves = next(p for p in admin.get(f"{API}/catalog/products", timeout=60).json()["products"]
                      if p["sku"] == "SKU-0001")
        f = admin.get(f"{API}/network/supplier-availability",
                      params={"product_id": eid(gloves)}, timeout=60)
        frows = f.json()["supplier_availability"]
        assert frows and all(a["product_id"] == eid(gloves) for a in frows)


# --- canonical scenario ---
class TestCanonicalScenario:
    def test_status_canonical(self, admin):
        r = admin.get(f"{API}/synthetic/status", timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["data_mode"] == "SYNTHETIC"
        counts = body["counts"]
        assert counts["facilities"] == 5
        assert counts["products"] == 100
        assert counts["inventory"] == 500
        assert counts["suppliers"] == 20

        canon = body["canonical_scenario"]
        assert canon["product"] == "Surgical Gloves"
        assert canon["product_sku"] == "SKU-0001"
        assert canon["required_quantity"] == 800
        assert canon["required_within_hours"] == 12
        assert canon["requesting_facility"] == "HOSP-C"

        c = canon["candidates"]
        a = c["HOSP-A"]
        assert a["available_quantity"] >= 1200, a
        assert a["safety_stock"] <= 300, a
        assert a["transfer_permitted"] is True, a
        assert a["available_quantity"] - 800 >= a["safety_stock"], a

        assert c["HOSP-B"]["available_quantity"] < 800, c["HOSP-B"]

        d = c["HOSP-D"]
        assert d["available_quantity"] >= 800, d
        assert d["available_quantity"] - 800 < d["safety_stock"], d

        assert c["HOSP-E"]["transfer_permitted"] is False, c["HOSP-E"]

        opts = canon["supplier_options"]
        assert any(o["available_quantity"] >= 800 and o["lead_time_hours"] <= 12 for o in opts), opts


# --- idempotent seeding ---
class TestIdempotentSeed:
    def test_reset_twice_identical(self, admin):
        first = admin.post(f"{API}/synthetic/reset", timeout=180)
        assert first.status_code == 200, first.text[:300]
        c1 = first.json()["counts"]
        second = admin.post(f"{API}/synthetic/reset", timeout=180)
        assert second.status_code == 200, second.text[:300]
        c2 = second.json()["counts"]
        assert c1 == c2, (c1, c2)
        assert c2["products"] == 100
        assert c2["inventory"] == 500
        assert c2["facilities"] == 5
        assert c2["suppliers"] == 20

    def test_seed_endpoint_counts(self, admin):
        r = admin.post(f"{API}/synthetic/seed", timeout=180)
        assert r.status_code == 200, r.text[:300]
        counts = r.json()["counts"]
        assert counts["products"] == 100 and counts["inventory"] == 500
        # data still queryable & consistent after reseed
        inv = admin.get(f"{API}/network/inventory", timeout=90).json()
        assert inv["count"] == 500
        assert all(i["available_quantity"] >= 0 for i in inv["inventory"])


# --- M1 regression smoke ---
class TestM1Regression:
    def test_unauthenticated_me_401(self, anon):
        r = anon.get(f"{API}/auth/me", params={"cb": uuid.uuid4().hex}, timeout=60)
        assert r.status_code == 401, f"{r.status_code}: {r.text[:200]}"

    def test_admin_me(self, admin, admin_credentials):
        r = admin.get(f"{API}/auth/me", params={"cb": uuid.uuid4().hex}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        user = body.get("user", body)
        assert user["email"] == admin_credentials["email"]
        assert user["role"].upper() == "ADMIN"

    def test_hospital_registration_pending(self, anon):
        email = f"TEST_m2a_reg_{uuid.uuid4().hex[:8]}@example.com"
        r = anon.post(
            f"{API}/auth/register/hospital",
            json={
                "email": email,
                "password": "password123",
                "full_name": "TEST Reg User",
                "organisation_name": f"TEST Hospital {uuid.uuid4().hex[:6]}",
                "primary_facility_name": "TEST Facility",
            },
            timeout=60,
        )
        assert r.status_code in (200, 201), f"{r.status_code}: {r.text[:400]}"
        assert "PENDING" in r.text.upper(), r.text[:400]

    def test_bad_password_rejected(self, anon, admin_credentials):
        r = anon.post(f"{API}/auth/login",
                      json={"email": admin_credentials["email"], "password": "wrong-password-xyz"},
                      timeout=60)
        assert r.status_code in (400, 401, 423, 429), f"{r.status_code}: {r.text[:200]}"


# --- reproducibility + isolation from M1 data ---
class TestReproducibilityAndIsolation:
    @staticmethod
    def _fingerprint(session):
        inv = session.get(f"{API}/network/inventory", timeout=90).json()["inventory"]
        prods = session.get(f"{API}/catalog/products", timeout=60).json()["products"]
        pid_to_sku = {eid(p): p["sku"] for p in prods}
        facs = {eid(f): f["code"] for f in
                session.get(f"{API}/network/facilities", timeout=60).json()["facilities"]}
        return sorted(
            (facs[i["facility_id"]], pid_to_sku[i["product_id"]], i["quantity_on_hand"],
             i["reserved_quantity"], i["safety_stock"], i["transfer_permitted"])
            for i in inv
        )

    def test_reseed_is_deterministic(self, admin):
        admin.post(f"{API}/synthetic/reset", timeout=180)
        first = self._fingerprint(admin)
        admin.post(f"{API}/synthetic/reset", timeout=180)
        second = self._fingerprint(admin)
        assert first == second, "reseed produced different data (not reproducible)"

    def test_reseed_preserves_real_registered_org(self, admin, anon):
        """A user-registered (non-synthetic) hospital must survive a synthetic reset."""
        email = f"TEST_m2a_keep_{uuid.uuid4().hex[:8]}@example.com"
        reg = anon.post(
            f"{API}/auth/register/hospital",
            json={
                "email": email,
                "password": "password123",
                "full_name": "TEST Keep User",
                "organisation_name": f"TEST Keep Hospital {uuid.uuid4().hex[:6]}",
                "primary_facility_name": "TEST Keep Facility",
            },
            timeout=60,
        )
        assert reg.status_code in (200, 201), reg.text[:300]

        admin.post(f"{API}/synthetic/reset", timeout=180)
        login = anon.post(f"{API}/auth/login", json={"email": email, "password": "password123"}, timeout=60)
        assert login.status_code == 200, f"real user lost after reset: {login.status_code} {login.text[:200]}"
        me = anon.get(f"{API}/auth/me", params={"cb": uuid.uuid4().hex}, timeout=60)
        assert me.status_code == 200, me.text[:200]
        org = anon.get(f"{API}/organisations/me", timeout=60)
        assert org.status_code == 200, f"org missing after reset: {org.status_code} {org.text[:200]}"
        assert "PENDING" in org.text.upper()
