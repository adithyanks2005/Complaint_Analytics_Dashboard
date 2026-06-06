"""
Pytest-based unit tests for the backend database module.
Uses a temporary SQLite database to keep tests isolated.
"""
from __future__ import annotations

import os
import tempfile
import pytest

# Point the DB at a temp file before importing the module
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ.setdefault("TEST_DB_PATH", _tmp.name)

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import backend.database as db

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Run every test with a fresh, isolated SQLite database."""
    tmp_db = tmp_path / "test_complaints.db"
    monkeypatch.setattr(db, "DB_PATH", tmp_db)
    monkeypatch.setattr(db, "_db_initialised", False)
    db.init_db()
    yield
    monkeypatch.setattr(db, "_db_initialised", False)


def _sample_record(**overrides):
    base = {
        "created_date": "2024-01-01",
        "area": "Test Area",
        "category": "Water",
        "status": "Pending",
        "description": "A test complaint.",
    }
    base.update(overrides)
    return base


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_init_db_creates_table():
    """Database should initialise without errors."""
    df = db.read_complaints_df()
    assert df is not None


def test_insert_and_read():
    """Inserting a complaint should make it readable."""
    before = len(db.read_complaints_df())
    rec = db.insert_complaint(_sample_record())
    assert rec["id"].startswith("CMP-")
    after = len(db.read_complaints_df())
    assert after == before + 1


def test_get_by_id():
    """Fetching by ID should return the correct record."""
    rec = db.insert_complaint(_sample_record(description="Unique desc"))
    fetched = db.get_complaint_by_id(rec["id"])
    assert fetched is not None
    assert fetched["description"] == "Unique desc"


def test_update():
    """Updating a record should persist the new values."""
    rec = db.insert_complaint(_sample_record())
    updated = db.update_complaint_record(rec["id"], {"status": "Closed", "closed_date": "2024-06-01"})
    assert updated["status"] == "Closed"
    assert updated["closed_date"] == "2024-06-01"


def test_delete():
    """Deleting a record should remove it from the database."""
    rec = db.insert_complaint(_sample_record())
    db.delete_complaint_record(rec["id"])
    assert db.get_complaint_by_id(rec["id"]) is None


def test_duplicate_id_raises():
    """Inserting a duplicate ID should raise DuplicateComplaintError."""
    rec = db.insert_complaint(_sample_record())
    with pytest.raises(db.DuplicateComplaintError):
        db.insert_complaint(_sample_record(id=rec["id"]))


def test_generate_next_id_increments():
    """Each new complaint ID should be higher than the last."""
    r1 = db.insert_complaint(_sample_record())
    r2 = db.insert_complaint(_sample_record())
    n1 = int(r1["id"].split("-")[-1])
    n2 = int(r2["id"].split("-")[-1])
    assert n2 > n1


def test_generate_next_id_supabase_reads_remote_ids(monkeypatch):
    """Supabase ID generation should use the highest remote complaint suffix."""

    class _FakeResponse:
        data = [{"id": "CMP-002"}, {"id": "CMP-120"}, {"id": "legacy"}]

    class _FakeTable:
        def select(self, _columns):
            return self

        def execute(self):
            return _FakeResponse()

    class _FakeClient:
        def table(self, _table_name):
            return _FakeTable()

    monkeypatch.setattr(db, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(db, "SUPABASE_KEY", "test-key")
    monkeypatch.setattr(db, "_supabase_failed", False)
    monkeypatch.setattr(db, "get_supabase_client", lambda: _FakeClient())

    assert db.generate_next_id_supabase() == "CMP-121"


def test_preservation_supabase_fallback_reads_sqlite(monkeypatch):
    """Preservation property test — Supabase fallback unaffected (Property 2).

    **Validates: Requirements 3.1, 3.2**

    When SUPABASE_URL="" and SUPABASE_KEY="" (no credentials), using_supabase() returns
    False and generate_next_id_supabase() MUST delegate to generate_next_id(), returning
    a string matching r"CMP-\\d{3,}" from SQLite.

    This test also verifies that get_supabase_client is NOT called when credentials are absent.

    EXPECTED TO PASS on unfixed code (confirms the SQLite fallback baseline is intact).
    """
    import re

    # Track whether get_supabase_client is called
    supabase_client_called = []

    def _fake_get_supabase_client():
        supabase_client_called.append(True)
        raise RuntimeError("Should not be called when credentials are absent")

    # Patch out credentials so using_supabase() returns False
    monkeypatch.setattr(db, "SUPABASE_URL", "")
    monkeypatch.setattr(db, "SUPABASE_KEY", "")
    # Ensure _supabase_failed is False so the fallback is purely credential-based
    monkeypatch.setattr(db, "_supabase_failed", False)
    # Instrument get_supabase_client to detect if it's called
    monkeypatch.setattr(db, "get_supabase_client", _fake_get_supabase_client)

    result = db.generate_next_id_supabase()

    # Property: result must match CMP-NNN (3 or more digits)
    assert re.match(r"CMP-\d{3,}", result), (
        f"Expected result matching r'CMP-\\d{{3,}}' but got {result!r}"
    )

    # Property: get_supabase_client must NOT have been called
    assert not supabase_client_called, (
        "get_supabase_client was called even though credentials were absent"
    )


def test_bug1_supabase_id_state_leak(monkeypatch):
    """Bug condition exploration test — Supabase ID state leak.

    **Validates: Requirements 1.1, 1.2**

    This test simulates the cross-test _supabase_failed state leak that causes
    generate_next_id_supabase() to return CMP-101 (from SQLite) instead of CMP-121
    (from the mocked Supabase client).

    EXPECTED TO FAIL on unfixed code:
        AssertionError: assert 'CMP-101' == 'CMP-121'

    Counterexample:
        _supabase_failed=True → using_supabase() returns False →
        SQLite fallback used → CMP-101 returned instead of CMP-121.
    """

    class _FakeResponse:
        data = [{"id": "CMP-002"}, {"id": "CMP-120"}, {"id": "legacy"}]

    class _FakeTable:
        def select(self, _columns):
            return self

        def execute(self):
            return _FakeResponse()

    class _FakeClient:
        def table(self, _table_name):
            return _FakeTable()

    # Step 1 — Contaminate state: simulate a prior test having set _supabase_failed = True
    monkeypatch.setattr(db, "_supabase_failed", True)

    # Step 2 — Apply the same patches as the original test
    monkeypatch.setattr(db, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(db, "SUPABASE_KEY", "test-key")
    monkeypatch.setattr(db, "get_supabase_client", lambda: _FakeClient())

    # Step 3 — Assert expected behavior (WILL FAIL on unfixed code — returns CMP-101)
    assert db.generate_next_id_supabase() == "CMP-121"
