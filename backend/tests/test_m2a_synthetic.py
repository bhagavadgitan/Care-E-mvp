"""M2A targeted tests: synthetic network counts, integrity, canonical scenario."""
import pytest
from fastapi.testclient import TestClient

from core.config import settings
from server import app

API = "/api/v1"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # triggers lifespan (Mongo connect + migrations + seed)
        r = c.post(f"{API}/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
        assert r.status_code == 200, r.text
        yield c


def test_five_facilities(client):
    assert client.get(f"{API}/network/facilities").json()["count"] == 5


def test_hundred_products(client):
    assert client.get(f"{API}/catalog/products").json()["count"] == 100


def test_five_hundred_inventory(client):
    assert client.get(f"{API}/network/inventory").json()["count"] == 500


def test_twenty_suppliers(client):
    assert client.get(f"{API}/network/suppliers").json()["count"] == 20


def test_no_impossible_reserved(client):
    items = client.get(f"{API}/network/inventory").json()["inventory"]
    assert all(i["reserved_quantity"] <= i["quantity_on_hand"] for i in items)
    assert all(i["available_quantity"] >= 0 for i in items)


def test_canonical_scenario(client):
    canon = client.get(f"{API}/synthetic/status").json()["canonical_scenario"]
    assert canon["required_quantity"] == 800
    assert canon["required_within_hours"] == 12
    cands = canon["candidates"]
    a = cands["HOSP-A"]
    assert a["available_quantity"] >= 1200
    assert a["safety_stock"] <= 300
    assert a["transfer_permitted"] is True
    assert (a["available_quantity"] - 800) >= a["safety_stock"]
    assert cands["HOSP-B"]["available_quantity"] < 800
    d = cands["HOSP-D"]
    assert d["available_quantity"] >= 800
    assert (d["available_quantity"] - 800) < d["safety_stock"]
    assert cands["HOSP-E"]["transfer_permitted"] is False
    assert any(o["available_quantity"] >= 800 and o["lead_time_hours"] <= 12 for o in canon["supplier_options"])


def test_seed_idempotent(client):
    first = client.post(f"{API}/synthetic/reset").json()["counts"]
    second = client.post(f"{API}/synthetic/reset").json()["counts"]
    assert first == second
    assert second["products"] == 100
    assert second["inventory"] == 500
    assert second["facilities"] == 5
    assert second["suppliers"] == 20
