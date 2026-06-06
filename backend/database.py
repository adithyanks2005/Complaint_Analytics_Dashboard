from __future__ import annotations

import sqlite3
import os
from pathlib import Path
from threading import Lock

import pandas as pd

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parents[1]
# Load optional .env file
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# Paths for data and CSV seed file
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "sample_complaints.csv"

# Supabase configuration (optional)
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "complaints")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

# Flag to track if Supabase connection has been verified as working
_supabase_verified: bool = False
_supabase_failed: bool = False

# Database file location - Vercel uses /tmp, otherwise local data folder
if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/complaints.db")
else:
    DB_PATH = DATA_DIR / "complaints.db"

# ---------------------------------------------------------------------------
# Global state to avoid re‑initialising the DB many times in the same process
# ---------------------------------------------------------------------------
_db_initialised: bool = False
_init_lock = Lock()
_supabase_client = None

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Return a fresh SQLite connection to the correct DB file.
    Ensures the data directory exists for local runs.
    """
    if not os.getenv("VERCEL"):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def using_supabase() -> bool:
    """True when Supabase configuration is present AND connection has not failed.
    Falls back to SQLite if credentials are invalid or the package errors out.
    """
    if _supabase_failed:
        return False
    return bool(SUPABASE_URL and SUPABASE_KEY)

def get_supabase_client():
    """Lazily create the Supabase client.
    Sets _supabase_failed=True on any connection error so the app falls back to SQLite.
    """
    global _supabase_client, _supabase_failed
    if _supabase_client is None:
        try:
            from supabase import create_client
        except ImportError as exc:
            _supabase_failed = True
            raise RuntimeError(
                "Supabase is configured but the 'supabase' package is not installed. "
                "Run `pip install -r requirements.txt`."
            ) from exc
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception as exc:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "Supabase connection failed (%s) – falling back to SQLite.", exc
            )
            _supabase_failed = True
            raise
    return _supabase_client


def _mark_supabase_failed(exc: Exception) -> None:
    """Disable Supabase for this process after an API/client failure."""
    global _supabase_failed
    _supabase_failed = True
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "Supabase request failed (%s) - falling back to SQLite.", exc
    )


def _normalise_record(record: dict[str, object]) -> dict[str, object]:
    return {col: record.get(col) for col in COMPLAINT_COLUMNS}

def _is_duplicate_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "23505" in msg or "duplicate key" in msg or "unique constraint" in msg

def _is_duplicate_id(conn: sqlite3.Connection, complaint_id: str) -> bool:
    """Check if a complaint ID already exists in the SQLite DB."""
    row = conn.execute(
        "SELECT 1 FROM complaints WHERE id = ?", (complaint_id,)
    ).fetchone()
    return row is not None

# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------
COMPLAINT_COLUMNS = [
    "id",
    "created_date",
    "closed_date",
    "state",
    "district",
    "municipality",
    "village",
    "area",
    "pincode",
    "category",
    "priority",
    "status",
    "description",
    "user_contact",
    "image_path",
]

class DuplicateComplaintError(Exception):
    """Raised when attempting to insert a complaint with a duplicate ID."""

# ---------------------------------------------------------------------------
# ID generation helpers
# ---------------------------------------------------------------------------

_id_lock = Lock()

def generate_next_id() -> str:
    """Generate the next sequential complaint ID (e.g. CMP-001).

    Uses a process-level lock combined with a SQLite exclusive transaction
    so that concurrent callers in the same process (multiple Streamlit sessions)
    cannot read the same max-ID and produce duplicate complaint IDs.
    """
    with _id_lock:
        with get_connection() as conn:
            # BEGIN EXCLUSIVE prevents any other SQLite writer from interleaving
            conn.execute("BEGIN EXCLUSIVE")
            rows = conn.execute("SELECT id FROM complaints").fetchall()
            highest = 0
            for row in rows:
                id_str = str(row[0]).strip()
                if "-" in id_str:
                    suffix = id_str.split("-")[-1]
                    if suffix.isdigit():
                        highest = max(highest, int(suffix))
            conn.execute("COMMIT")
            return f"CMP-{highest + 1:03d}"

def generate_next_id_supabase() -> str:
    """Generate the next complaint ID from the configured Supabase table."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        return generate_next_id()
    try:
        resp = get_supabase_client().table(SUPABASE_TABLE).select("id").execute()
    except Exception as exc:
        _mark_supabase_failed(exc)
        return generate_next_id()
    ids = [str(record.get("id", "")) for record in (resp.data or [])]
    highest = max(
        (
            int(complaint_id.split("-")[-1])
            for complaint_id in ids
            if complaint_id.split("-")[-1].isdigit()
        ),
        default=0,
    )
    return f"CMP-{highest + 1:03d}"

# ---------------------------------------------------------------------------
# Database initialisation and migration
# ---------------------------------------------------------------------------

def seed_complaints(connection: sqlite3.Connection) -> None:
    """Insert sample data from the CSV seed file into the fresh database.
    This function is used only when the table is newly created.
    """
    df = pd.read_csv(CSV_PATH)
    df.to_sql("complaints", connection, if_exists="append", index=False)

def init_db() -> None:
    """Create the complaints table if it does not exist and run migrations.
    The function is guarded so it runs only once per process.
    If Supabase is configured but fails, falls back to SQLite.
    """
    global _db_initialised
    if using_supabase():
        # Verify the Supabase connection works; if not, fall back to SQLite
        try:
            get_supabase_client()
            _db_initialised = True
            return
        except Exception as exc:
            _mark_supabase_failed(exc)
            # _supabase_failed is now True; continue to SQLite init below
            pass
    if _db_initialised:
        return
    with _init_lock:
        if _db_initialised:
            return
        if not os.getenv("VERCEL"):
            DATA_DIR.mkdir(exist_ok=True)
        with get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS complaints (
                    id TEXT PRIMARY KEY,
                    created_date TEXT NOT NULL,
                    closed_date TEXT,
                    state TEXT,
                    district TEXT,
                    municipality TEXT,
                    village TEXT,
                    area TEXT NOT NULL,
                    pincode TEXT,
                    category TEXT NOT NULL,
                    priority TEXT,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    description TEXT NOT NULL,
                    user_contact TEXT,
                    image_path TEXT
                )
                """
            )
            migrate_schema(conn)
            count = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
            if count == 0:
                seed_complaints(conn)
        _db_initialised = True

def migrate_schema(connection: sqlite3.Connection) -> None:
    """Add missing optional columns and rebuild the table if critical columns changed.
    PRAGMA table_info returns rows as tuples; column name is at index 1.
    """
    columns = {
        row[1]: {
            "cid": row[0], "name": row[1], "type": row[2], "notnull": row[3], "dflt_value": row[4], "pk": row[5]
        }
        for row in connection.execute("PRAGMA table_info(complaints)").fetchall()
    }
    # Ensure all optional columns exist (they may be missing in older DB versions)
    for col in ["state", "district", "municipality", "village", "pincode", "user_contact", "image_path"]:
        if col not in columns:
            connection.execute(f"ALTER TABLE complaints ADD COLUMN {col} TEXT")
            columns[col] = {"name": col, "notnull": 0}
    # Rebuild if previously the column definitions were stricter (e.g., NOT NULL)
    needs_rebuild = (
        columns.get("closed_date", {}).get("notnull") == 1
        or columns.get("priority", {}).get("notnull") == 1
    )
    if not needs_rebuild:
        return
    # Create a new table with the proper schema
    connection.execute(
        """
        CREATE TABLE complaints_new (
            id TEXT PRIMARY KEY,
            created_date TEXT NOT NULL,
            closed_date TEXT,
            state TEXT,
            district TEXT,
            municipality TEXT,
            village TEXT,
            area TEXT NOT NULL,
            pincode TEXT,
            category TEXT NOT NULL,
            priority TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            description TEXT NOT NULL,
            user_contact TEXT,
            image_path TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO complaints_new (
            id, created_date, closed_date, state, district, municipality, village, area,
            pincode, category, priority, status, description, user_contact, image_path
        )
        SELECT
            id,
            created_date,
            NULLIF(closed_date, ''),
            state,
            district,
            municipality,
            village,
            area,
            pincode,
            category,
            NULLIF(priority, ''),
            status,
            description,
            user_contact,
            image_path
        FROM complaints
        """
    )
    connection.execute("DROP TABLE complaints")
    connection.execute("ALTER TABLE complaints_new RENAME TO complaints")

# ---------------------------------------------------------------------------
# CRUD operations used by the rest of the application
# ---------------------------------------------------------------------------

def read_complaints_df() -> pd.DataFrame:
    init_db()
    if using_supabase():
        try:
            resp = (
                get_supabase_client()
                .table(SUPABASE_TABLE)
                .select(",".join(COMPLAINT_COLUMNS))
                .order("created_date", desc=False)
                .execute()
            )
            return pd.DataFrame(resp.data or [], columns=COMPLAINT_COLUMNS)
        except Exception as exc:
            _mark_supabase_failed(exc)
            # _supabase_failed is now True; fall through to SQLite
            pass
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM complaints", conn)

def row_to_dict(row: sqlite3.Row | None) -> dict[str, object] | None:
    if row is None:
        return None
    return dict(row)

def get_complaint_by_id(complaint_id: str) -> dict[str, object] | None:
    init_db()
    if using_supabase():
        try:
            resp = (
                get_supabase_client()
                .table(SUPABASE_TABLE)
                .select(",".join(COMPLAINT_COLUMNS))
                .eq("id", complaint_id)
                .maybe_single()
                .execute()
            )
            return _normalise_record(resp.data) if resp.data else None
        except Exception as exc:
            _mark_supabase_failed(exc)
            pass
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
    return row_to_dict(row)

def insert_complaint(record: dict[str, object]) -> dict[str, object]:
    init_db()
    id_was_generated = not bool(record.get("id"))
    if id_was_generated:
        record["id"] = generate_next_id_supabase() if using_supabase() else generate_next_id()
    record = _normalise_record(record)
    try:
        if using_supabase():
            try:
                resp = (
                    get_supabase_client()
                    .table(SUPABASE_TABLE)
                    .insert(record)
                    .execute()
                )
                return _normalise_record(resp.data[0])
            except Exception as exc:
                if _is_duplicate_error(exc):
                    raise DuplicateComplaintError from exc
                _mark_supabase_failed(exc)
                # Supabase failed – fall through to SQLite
        with _id_lock:
            with get_connection() as conn:
                if _is_duplicate_id(conn, str(record["id"])):
                    if not id_was_generated:
                        raise DuplicateComplaintError
                    # Regenerate generated IDs inside the lock to avoid races.
                    rows = conn.execute("SELECT id FROM complaints").fetchall()
                    highest = max(
                        (int(r[0].split("-")[-1]) for r in rows
                         if "-" in str(r[0]) and str(r[0]).split("-")[-1].isdigit()),
                        default=0,
                    )
                    record["id"] = f"CMP-{highest + 1:03d}"
                placeholders = ", ".join("?" for _ in COMPLAINT_COLUMNS)
                cols_sql = ", ".join(COMPLAINT_COLUMNS)
                conn.execute(
                    f"INSERT INTO complaints ({cols_sql}) VALUES ({placeholders})",
                    tuple(record[col] for col in COMPLAINT_COLUMNS),
                )
    except DuplicateComplaintError:
        raise
    except Exception as exc:
        if _is_duplicate_error(exc):
            raise DuplicateComplaintError from exc
        raise
    return get_complaint_by_id(str(record["id"]))

def update_complaint_record(complaint_id: str, record: dict[str, object]) -> dict[str, object] | None:
    init_db()
    existing = get_complaint_by_id(complaint_id) or {}
    record = _normalise_record({**existing, **record, "id": complaint_id})
    updates = {k: v for k, v in record.items() if k != "id"}
    if using_supabase():
        try:
            resp = (
                get_supabase_client()
                .table(SUPABASE_TABLE)
                .update(updates)
                .eq("id", complaint_id)
                .execute()
            )
            if resp.data:
                return _normalise_record(resp.data[0])
        except Exception as exc:
            _mark_supabase_failed(exc)
            pass  # fall through to SQLite
    with get_connection() as conn:
        set_clause = ", ".join(f"{col} = ?" for col in COMPLAINT_COLUMNS if col != "id")
        conn.execute(
            f"UPDATE complaints SET {set_clause} WHERE id = ?",
            tuple(record[col] for col in COMPLAINT_COLUMNS if col != "id") + (complaint_id,),
        )
    return get_complaint_by_id(complaint_id)

def delete_complaint_record(complaint_id: str) -> None:
    init_db()
    if using_supabase():
        try:
            (
                get_supabase_client()
                .table(SUPABASE_TABLE)
                .delete()
                .eq("id", complaint_id)
                .execute()
            )
            return
        except Exception as exc:
            _mark_supabase_failed(exc)
            pass  # fall through to SQLite
    with get_connection() as conn:
        conn.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
