from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "HackRadar"


def test_stats_endpoint():
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "active_sources" in data


def test_sources_endpoint():
    resp = client.get("/api/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert isinstance(sources, list)
    names = [s["name"] for s in sources]
    assert "devfolio" in names
    assert "unstop" in names
    assert "tathva" in names


def test_events_endpoint():
    resp = client.get("/api/events?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_dashboard_ui():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "HackRadar" in resp.text
