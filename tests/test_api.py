import csv
from io import StringIO

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_summary_has_required_kpis():
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_complaints"] >= 30
    assert "average_closure_days" in data
    assert "closure_rate_percent" in data


def test_area_filter_limits_records():
    response = client.get("/complaints", params={"area": "North Zone"})
    assert response.status_code == 200
    complaints = response.json()
    assert complaints
    assert all(item["area"] == "North Zone" for item in complaints)


def test_date_range_filter_returns_matching_records():
    response = client.get(
        "/complaints",
        params={"start_date": "2026-04-01", "end_date": "2026-04-30"},
    )
    assert response.status_code == 200
    complaints = response.json()
    assert complaints
    assert all("2026-04-" in item["created_date"] for item in complaints)


def test_csv_export_uses_short_dates():
    response = client.get(
        "/complaints/export",
        params={"start_date": "2026-04-01", "end_date": "2026-04-30"},
    )
    assert response.status_code == 200
    complaints = list(csv.DictReader(StringIO(response.text)))
    assert complaints
    assert all(len(item["created_date"]) == 8 for item in complaints)
    assert all(len(item["closed_date"]) == 8 for item in complaints if item["closed_date"])
    assert all(item["created_date"][2] == "-" and item["created_date"][5] == "-" for item in complaints)


def test_crud_flow_inserts_updates_reads_and_deletes_sample_record():
    complaint_id = "CMP-TEST-901"
    payload = {
        "id":           complaint_id,
        "created_date": "2026-05-01",
        "area":         "North Zone",
        "category":     "Water Supply",
        "description":  "Testing database insert with sample complaint record",
    }

    create_response = client.post("/complaints", json=payload)
    assert create_response.status_code in {201, 409}
    if create_response.status_code == 201:
        created = create_response.json()
        assert created["status"] == "Pending"
        assert created["priority"] is None
        assert created["closed_date"] is None

    update_response = client.put(
        f"/complaints/{complaint_id}",
        json={
            "priority": "High",
            "status": "Closed",
            "closed_date": "2026-05-03",
            "description": "Testing update flow for sample complaint",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "Closed"

    read_response = client.get(f"/complaints/{complaint_id}")
    assert read_response.status_code == 200
    assert read_response.json()["id"] == complaint_id

    delete_response = client.delete(f"/complaints/{complaint_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Complaint deleted successfully"


def test_admin_validation_rejects_closed_status_without_closure_date():
    complaint_id = "CMP-BAD-901"
    client.post(
        "/complaints",
        json={
            "id":           complaint_id,
            "created_date": "2026-05-05",
            "area":         "East Zone",
            "category":     "Drainage",
            "description":  "Complaint created to test invalid admin update",
        },
    )
    response = client.put(
        f"/complaints/{complaint_id}",
        json={
            "priority": "High",
            "status": "Closed",
            "description": "Invalid admin close without closure date",
        },
    )
    assert response.status_code == 422
    client.delete(f"/complaints/{complaint_id}")


def test_admin_can_close_resolved_complaint():
    complaint_id = "CMP-ADMIN-901"
    payload = {
        "id":           complaint_id,
        "created_date": "2026-05-01",
        "area":         "Central Zone",
        "category":     "Drainage",
        "description":  "Complaint created to test admin closing workflow",
    }

    client.post("/complaints", json=payload)
    response = client.put(
        f"/complaints/{complaint_id}",
        json={
            "priority": "High",
            "closed_date": "2026-05-04",
            "status":      "Closed",
            "description": "Complaint resolved and closed by admin",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Closed"

    client.delete(f"/complaints/{complaint_id}")


def test_auto_generated_id_continues_sequence():
    # Insert first complaint without ID
    payload1 = {
        "created_date": "2026-05-20",
        "area":         "North Zone",
        "category":     "Water Supply",
        "description":  "Test auto ID generation 1",
    }
    resp1 = client.post("/complaints", json=payload1)
    assert resp1.status_code == 201
    created1 = resp1.json()
    id1 = created1["id"]
    assert id1.startswith("CMP-")

    # Insert second complaint without ID
    payload2 = {
        "created_date": "2026-05-21",
        "area":         "South Zone",
        "category":     "Drainage",
        "description":  "Test auto ID generation 2",
    }
    resp2 = client.post("/complaints", json=payload2)
    assert resp2.status_code == 201
    created2 = resp2.json()
    id2 = created2["id"]
    assert id2.startswith("CMP-")
    assert id1 != id2

    # Delete the first complaint
    delete_resp = client.delete(f"/complaints/{id1}")
    assert delete_resp.status_code == 200

    # Insert third complaint, it should continue after the highest existing ID
    payload3 = {
        "created_date": "2026-05-22",
        "area":         "East Zone",
        "category":     "Garbage",
        "description":  "Test continuous auto ID generation",
    }
    resp3 = client.post("/complaints", json=payload3)
    assert resp3.status_code == 201
    created3 = resp3.json()
    id3 = created3["id"]
    assert id3.startswith("CMP-")
    assert int(id3.split("-")[-1]) > int(id2.split("-")[-1])

    # Cleanup
    client.delete(f"/complaints/{id2}")
    client.delete(f"/complaints/{id3}")
