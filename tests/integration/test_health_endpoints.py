from fastapi.testclient import TestClient

from src.app.main import create_app


def test_health_live_ok() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_ready_structure() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data

