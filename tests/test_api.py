from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_options():
    response = client.get("/options")
    assert response.status_code == 200
    data = response.json()
    assert "states" in data
    assert "categories" in data

def test_complaints():
    response = client.get("/complaints")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
