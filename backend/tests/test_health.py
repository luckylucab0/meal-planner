"""Smoke-Test für den Health-Endpoint — stellt sicher, dass der Skeleton-Build hochkommt."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
