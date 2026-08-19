from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import backend.database as db
from backend.main import app
from backend.validation import validate_coordinates, validate_image_bytes


def sample(**overrides):
    value = {
        "created_date": "2026-08-19",
        "area": "Test Area",
        "category": "Water Supply",
        "status": "Pending",
        "description": "Water supply failure in the test area.",
    }
    value.update(overrides)
    return value


@pytest.fixture(autouse=True)
def isolated_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "SUPABASE_URL", "")
    monkeypatch.setattr(db, "SUPABASE_KEY", "")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "complaints.db")
    db.reset_database_state_for_tests()
    yield
    db.reset_database_state_for_tests()


def test_concurrent_submissions_have_unique_atomic_ids():
    existing = db.read_complaints_df()["id"].astype(str).tolist()
    existing_numbers = [
        int(value.split("-")[-1])
        for value in existing
        if value.startswith("CMP-") and value.split("-")[-1].isdigit()
    ]
    baseline = max(existing_numbers, default=0)

    def submit(index):
        return db.insert_complaint(sample(description=f"Concurrent complaint number {index}."))["id"]

    with ThreadPoolExecutor(max_workers=12) as executor:
        ids = list(executor.map(submit, range(40)))

    assert len(ids) == 40
    assert len(set(ids)) == 40
    numbers = sorted(int(value.split("-")[-1]) for value in ids)
    assert numbers == list(range(baseline + 1, baseline + 41))


def test_state_invariants_are_enforced_by_backend():
    with pytest.raises(ValueError, match="closed_date"):
        db.insert_complaint(sample(status="Closed", closed_date=None))
    with pytest.raises(ValueError, match="closed_date"):
        db.insert_complaint(sample(status="Pending", closed_date="2026-08-20"))
    with pytest.raises(ValueError, match="before"):
        db.insert_complaint(sample(status="Closed", closed_date="2026-08-18"))


def test_supabase_failure_never_falls_back_to_sqlite(monkeypatch):
    monkeypatch.setattr(db, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(db, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(db, "get_supabase_client", lambda: (_ for _ in ()).throw(RuntimeError("outage")))

    with pytest.raises(db.DatabaseUnavailableError):
        db.init_db()

    assert not (db.DB_PATH.exists() and db.DB_PATH.stat().st_size > 0)


def test_supabase_health_recovers_without_process_state_reset(monkeypatch):
    class FakeTable:
        def __init__(self, failing):
            self.failing = failing
        def select(self, *_):
            return self
        def limit(self, *_):
            return self
        def execute(self):
            if self.failing:
                raise RuntimeError("temporary outage")
            return type("Response", (), {"data": []})()

    class FakeClient:
        def __init__(self):
            self.failing = True
        def table(self, _):
            return FakeTable(self.failing)

    client = FakeClient()
    monkeypatch.setattr(db, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(db, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(db, "get_supabase_client", lambda: client)

    assert db.check_database_health()["status"] == "unavailable"
    client.failing = False
    assert db.check_database_health()["status"] == "ok"


def test_api_post_put_delete_workflow():
    with TestClient(app) as client:
        payload = {
            "created_date": "2026-08-19",
            "area": "Test Area",
            "category": "Water Supply",
            "description": "Water supply failure requiring attention.",
        }
        created = client.post("/complaints", json=payload)
        assert created.status_code == 201
        complaint_id = created.json()["id"]
        assert complaint_id.startswith("CMP-")

        fetched = client.get(f"/complaints/{complaint_id}")
        assert fetched.status_code == 200

        updated = client.put(
            f"/complaints/{complaint_id}",
            json={"status": "Closed", "closed_date": "2026-08-20"},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "Closed"

        deleted = client.delete(f"/complaints/{complaint_id}")
        assert deleted.status_code == 200
        assert client.get(f"/complaints/{complaint_id}").status_code == 404


def test_api_rejects_invalid_state_transition():
    with TestClient(app) as client:
        payload = {
            "created_date": "2026-08-19",
            "area": "Test Area",
            "category": "Water Supply",
            "description": "Water supply failure requiring attention.",
        }
        created = client.post("/complaints", json=payload)
        complaint_id = created.json()["id"]
        response = client.put(f"/complaints/{complaint_id}", json={"status": "Closed"})
        assert response.status_code == 422


def test_notification_receives_database_generated_id(monkeypatch):
    observed = []
    monkeypatch.setattr("backend.main._notify_real", lambda contact, subject, message: observed.append(message))
    with TestClient(app) as client:
        response = client.post(
            "/complaints",
            json={
                "created_date": "2026-08-19",
                "area": "Test Area",
                "category": "Water Supply",
                "description": "Notification should contain the generated complaint ID.",
                "user_contact": "test@example.com",
            },
        )
    assert response.status_code == 201
    generated_id = response.json()["id"]
    assert observed and generated_id in observed[0]


def test_export_and_empty_analytics():
    with TestClient(app) as client:
        export_response = client.get("/complaints/export", params={"state": "No Such State"})
        assert export_response.status_code == 200
        assert "Content-Disposition" in export_response.headers
        assert client.get("/analytics/trends", params={"state": "No Such State"}).json() == []
        summary = client.get("/analytics/summary", params={"state": "No Such State"}).json()
        assert summary["total_complaints"] == 0
        assert summary["closure_rate_percent"] == 0.0


def test_image_upload_failures_are_explicit():
    with pytest.raises(ValueError, match="empty"):
        validate_image_bytes(b"", "image/png")
    with pytest.raises(ValueError, match="5 MB"):
        validate_image_bytes(b"x" * (5 * 1024 * 1024 + 1), "image/png")
    with pytest.raises(ValueError, match="JPEG"):
        validate_image_bytes(b"not-an-image", "text/plain")


def test_gps_validation_handles_provider_failure_inputs():
    assert validate_coordinates(None, None) is None
    assert validate_coordinates(13.0827, 80.2707) == (13.0827, 80.2707)
    with pytest.raises(ValueError):
        validate_coordinates(91, 80)
    with pytest.raises(ValueError):
        validate_coordinates(13, None)
