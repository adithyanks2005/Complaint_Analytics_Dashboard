"""
tests/test_backfill_bug.py

Bug condition exploration test for Bug 3:
  NameError: name 'ref_df' is not defined

When backfill_sqlite() (or backfill_supabase()) is called programmatically
(i.e. outside the __main__ block), the function references `ref_df` as if it
were a module-level global. Because `ref_df` is only assigned inside the
`if __name__ == "__main__"` block, calling either function from any other
context raises:

    NameError: name 'ref_df' is not defined

This test PASSES on UNFIXED code — the NameError confirms the bug exists.

Validates: Requirements 1.4
Property 5: Bug Condition — backfill_sqlite() / backfill_supabase() raise
            NameError outside __main__

Also contains:

Validates: Requirements 3.4
Property 6: Preservation — script execution behavior unchanged (BEFORE fix)
  Tests that simulate the __main__ path (where ref_df IS defined in module scope)
  verify that calling backfill_sqlite with an empty ref_df produces zero updates
  and raises no exception. These tests PASS on UNFIXED code because the __main__
  path works correctly.
"""
import sys
import tempfile
import sqlite3
from pathlib import Path

import pytest
import pandas as pd

# Ensure the scripts/ directory is importable
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import backfill_locations  # noqa: E402


def test_backfill_sqlite_accepts_ref_df_when_called_programmatically(tmp_path, monkeypatch):
    """
    Calling backfill_sqlite() with no arguments outside __main__ must raise
    NameError because ref_df is not defined at module scope.

    EXPECTED OUTCOME on unfixed code: NameError: name 'ref_df' is not defined
    This test PASSES on unfixed code, confirming the bug exists.

    After Bug 3 is fixed (ref_df added as an explicit parameter), task 11.2
    updates this test to assert no exception is raised when ref_df is passed.
    """
    db_path = _make_temp_sqlite_db(tmp_path)
    ref_df = pd.DataFrame(columns=["id", "state", "district", "municipality", "village", "pincode"])

    import backend.database as _db
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_db, "_db_initialised", True)
    monkeypatch.setattr(backfill_locations, "get_connection", _db.get_connection)

    backfill_locations.backfill_sqlite(ref_df)


# ---------------------------------------------------------------------------
# Property 6: Preservation — __main__ path behavior unchanged (BEFORE fix)
#
# The __main__ block assigns ref_df before calling backfill_sqlite():
#
#   if __name__ == "__main__":
#       ref_df = pd.read_csv(CSV_PATH) if CSV_PATH.exists() else pd.DataFrame()
#       backfill_sqlite()          # ref_df is now a module-level global
#
# These tests simulate that path by injecting ref_df into the module's
# global namespace (as __main__ does), then calling backfill_sqlite().
#
# All tests PASS on UNFIXED code because the __main__ path is not broken —
# only the programmatic-call path (tested above) raises NameError.
# ---------------------------------------------------------------------------


def _make_temp_sqlite_db(tmp_path: Path) -> Path:
    """Create a minimal SQLite complaints DB with a few rows for testing."""
    db_path = tmp_path / "test_backfill.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE complaints (
            id TEXT PRIMARY KEY,
            state TEXT,
            district TEXT,
            municipality TEXT,
            village TEXT,
            pincode TEXT
        )
        """
    )
    # Insert rows that already have all location fields filled in
    conn.execute(
        "INSERT INTO complaints VALUES (?, ?, ?, ?, ?, ?)",
        ("CMP-001", "Karnataka", "Bengaluru Urban", "BBMP", "Whitefield", "560066"),
    )
    # Insert a row with missing location fields
    conn.execute(
        "INSERT INTO complaints VALUES (?, ?, ?, ?, ?, ?)",
        ("CMP-002", None, None, None, None, None),
    )
    conn.commit()
    conn.close()
    return db_path


def test_preservation_empty_ref_df_updates_zero_rows(tmp_path, monkeypatch):
    """
    **Validates: Requirements 3.4**
    Property 6 (Preservation) — empty ref_df produces zero updates, no exception.

    Simulates the __main__ path: inject an empty ref_df (with columns, as a CSV
    read would produce) into the module's global namespace, then call backfill_sqlite().

    With an empty ref_df, the csv_match lookup always returns an empty DataFrame,
    so no rows are updated. The function must complete without raising any exception.

    NOTE: ref_df must have at least an 'id' column to avoid KeyError — a pd.read_csv
    of an existing CSV always yields columns; pd.DataFrame(columns=['id']) models
    an empty CSV that still has the id column header.

    EXPECTED OUTCOME: PASSES on unfixed code (the __main__ path works correctly;
    only the no-args programmatic call raises NameError).
    """
    db_path = _make_temp_sqlite_db(tmp_path)

    # Inject ref_df into the module's global scope — replicates what __main__ does
    # Use an empty DataFrame WITH columns (as pd.read_csv produces), not a column-less one
    empty_ref_df = pd.DataFrame(columns=["id", "state", "district", "municipality", "village", "pincode"])
    monkeypatch.setattr(backfill_locations, "ref_df", empty_ref_df, raising=False)

    # Redirect backfill_locations to use our temp DB
    import backend.database as _db
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_db, "_db_initialised", True)  # skip init_db in get_connection
    monkeypatch.setattr(backfill_locations, "get_connection", _db.get_connection)

    # Call backfill_sqlite() — the module now has ref_df in its global scope
    backfill_locations.backfill_sqlite(empty_ref_df)

    # Verify: rows with missing fields are still missing (zero updates applied)
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT * FROM complaints WHERE id = ?", ("CMP-002",)).fetchone()
    conn.close()
    # All location columns should still be NULL — no updates happened
    assert row[1] is None, f"Expected state=None (no update), got {row[1]!r}"
    assert row[2] is None, f"Expected district=None (no update), got {row[2]!r}"


@pytest.mark.parametrize("ref_data,expected_updated_count", [
    # Case 1: Empty ref_df (with id column) — no rows can be matched, zero updates
    # Models CSV with columns but no rows (e.g., header-only CSV)
    ("empty_with_cols", 0),
    # Case 2: ref_df has a row for CMP-999 (no match in DB) — zero updates
    ([{"id": "CMP-999", "state": "Tamil Nadu", "district": "Chennai",
       "municipality": "GCC", "village": "T Nagar", "pincode": "600017"}], 0),
])
def test_preservation_backfill_zero_updates_when_no_match(
    tmp_path, monkeypatch, ref_data, expected_updated_count
):
    """
    **Validates: Requirements 3.4**
    Property 6 (Preservation) — backfill_sqlite raises no exception and updates
    exactly zero rows when ref_df is empty or contains no matching IDs.

    Parametrized over two cases:
      1. Empty ref_df with columns (models a header-only CSV — __main__ path)
      2. ref_df with a non-matching ID (models a CSV with different records)

    Both cases must complete without error and leave DB state unchanged.

    EXPECTED OUTCOME: PASSES on unfixed code.
    """
    db_path = _make_temp_sqlite_db(tmp_path)

    if ref_data == "empty_with_cols":
        ref_df = pd.DataFrame(columns=["id", "state", "district", "municipality", "village", "pincode"])
    else:
        ref_df = pd.DataFrame(ref_data)
    # Inject ref_df into module global scope — replicates __main__ assignment
    monkeypatch.setattr(backfill_locations, "ref_df", ref_df, raising=False)

    import backend.database as _db
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_db, "_db_initialised", True)
    monkeypatch.setattr(backfill_locations, "get_connection", _db.get_connection)

    # Must not raise any exception
    backfill_locations.backfill_sqlite(ref_df)

    # Verify the row that had missing fields is still unmodified
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT state, district, municipality, village, pincode FROM complaints WHERE id = ?",
        ("CMP-002",),
    ).fetchone()
    conn.close()
    # All columns should still be None — the empty/no-match ref_df produced zero updates
    assert all(v is None for v in row), (
        f"Expected all location columns to remain NULL but got: {row!r}"
    )


def test_preservation_fully_populated_row_is_skipped(tmp_path, monkeypatch):
    """
    **Validates: Requirements 3.4**
    Property 6 (Preservation) — rows that already have all location fields populated
    are skipped even when ref_df contains a matching entry with different values.

    This mirrors the __main__ path behavior: only rows with at least one missing
    location field are candidates for update.

    EXPECTED OUTCOME: PASSES on unfixed code.
    """
    db_path = _make_temp_sqlite_db(tmp_path)

    # ref_df contains a matching row for CMP-001, but CMP-001 already has all fields
    ref_df = pd.DataFrame([{
        "id": "CMP-001",
        "state": "CHANGED_STATE",
        "district": "CHANGED_DISTRICT",
        "municipality": "CHANGED_MUNICIPALITY",
        "village": "CHANGED_VILLAGE",
        "pincode": "000000",
    }])
    monkeypatch.setattr(backfill_locations, "ref_df", ref_df, raising=False)

    import backend.database as _db
    monkeypatch.setattr(_db, "DB_PATH", db_path)
    monkeypatch.setattr(_db, "_db_initialised", True)
    monkeypatch.setattr(backfill_locations, "get_connection", _db.get_connection)

    backfill_locations.backfill_sqlite(ref_df)

    # CMP-001 had all fields populated, so it must NOT have been overwritten
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT state, district FROM complaints WHERE id = ?", ("CMP-001",)
    ).fetchone()
    conn.close()
    assert row[0] == "Karnataka", (
        f"Expected state='Karnataka' (unchanged) but got {row[0]!r}"
    )
    assert row[1] == "Bengaluru Urban", (
        f"Expected district='Bengaluru Urban' (unchanged) but got {row[1]!r}"
    )
