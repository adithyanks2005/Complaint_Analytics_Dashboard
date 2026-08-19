from fastapi.testclient import TestClient

from backend.main import app


def test_read_root():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["status"] == "ok"


def test_database_health():
    with TestClient(app) as client:
        response = client.get("/health/database")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_options():
    with TestClient(app) as client:
        response = client.get("/options")
    assert response.status_code == 200
    data = response.json()
    assert "states" in data
    assert "categories" in data


def test_complaints():
    with TestClient(app) as client:
        response = client.get("/complaints")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
