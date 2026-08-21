"""Integration test: health endpoints via the full app (lifespan + Mongo)."""
from fastapi.testclient import TestClient

from server import app


def test_health_endpoint():
    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ok", "degraded")
        assert body["data_mode"] == "SYNTHETIC"
        assert body["service"] == "care-e-api"


def test_liveness_endpoint():
    with TestClient(app) as client:
        resp = client.get("/api/v1/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_unknown_route_returns_structured_error():
    with TestClient(app) as client:
        resp = client.get("/api/v1/does-not-exist")
        assert resp.status_code == 404
        assert "error" in resp.json()
