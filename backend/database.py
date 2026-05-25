from __future__ import annotations

import sqlite3
import os
from pathlib import Path
from threading import Lock

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "sample_complaints.csv"
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "complaints")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/complaints.db")
else:
    DB_PATH = DATA_DIR / "complaints.db"

# Guard so init_db only runs its expensive checks once per process
_db_initialised = False
_init_lock       = Lock()
_supabase_client = None


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
    """Raised when a complaint id already exists."""


def using_supabase() -> bool:
    """Return True when the app should use the shared Supabase backend."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_supabase_client():
    """Create the Supabase client lazily so local SQLite runs need no cloud config."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
        except ImportError as exc:
            raise RuntimeError(
                "Supabase is configured but the 'supabase' package is not installed. "
                "Run `pip install -r requirements.txt`."
            ) from exc
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def _normalise_record(record: dict[str, object]) -> dict[str, object]:
    return {column: record.get(column) for column in COMPLAINT_COLUMNS}


def _is_duplicate_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "23505" in message or "duplicate key" in message or "unique constraint" in message


def generate_next_id() -> str:
    """Return the next continuous complaint ID using the highest existing number."""
    with get_connection() as conn:
        rows = conn.execute("SELECT id FROM complaints").fetchall()
        highest = 0
        for row in rows:
            id_str = str(row["id"]).strip()
            if "-" in id_str:
                suffix = id_str.split("-")[-1]
                if suffix.isdigit():
                    highest = max(highest, int(suffix))
    return f"CMP-{highest + 1:03d}"


def generate_next_id_supabase() -> str:
    """Generate next ID using Supabase backend when applicable."""
    client = get_supabase_client()
    response = client.table(SUPABASE_TABLE).select("id").execute()
    ids = [rec["id"] for rec in (response.data or [])]
    highest = max(
        (int(id.split("-")[-1]) for id in ids if str(id).split("-")[-1].isdigit()),
        default=0,
    )
    return f"CMP-{highest + 1:03d}"



def get_connection() -> sqlite3.Connection:
    """Return a thread-safe SQLite connection with WAL mode and Row factory."""
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    return connection


def init_db() -> None:
    """Initialise the database exactly once per process."""
    global _db_initialised
    if using_supabase():
        _db_initialised = True
        return
    if _db_initialised:
        return
    with _init_lock:
        if _db_initialised:          # double-checked locking
            return
        if not os.getenv("VERCEL"):
            DATA_DIR.mkdir(exist_ok=True)
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS complaints (
                    id           TEXT PRIMARY KEY,
                    created_date TEXT NOT NULL,
                    closed_date  TEXT,
                    state        TEXT,
                    district     TEXT,
                    municipality TEXT,
                    village      TEXT,
                    area         TEXT NOT NULL,
                    pincode      TEXT,
                    category     TEXT NOT NULL,
                    priority     TEXT,
                    status       TEXT NOT NULL DEFAULT 'Pending',
                    description  TEXT NOT NULL,
                    user_contact TEXT,
                    image_path   TEXT
                )
                """
            )
            migrate_schema(connection)
            count = connection.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
            if count == 0:
                seed_complaints(connection)
        _db_initialised = True


def migrate_schema(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]: dict(row) for row in connection.execute("PRAGMA table_info(complaints)").fetchall()
    }
    for column_name in [
        "state",
        "district",
        "municipality",
        "village",
        "pincode",
        "user_contact",
        "image_path",
    ]:
        if column_name not in columns:
            connection.execute(f"ALTER TABLE complaints ADD COLUMN {column_name} TEXT")
            columns[column_name] = {"name": column_name, "notnull": 0}
    needs_rebuild = (
        columns.get("closed_date", {}).get("notnull") == 1
        or columns.get("priority", {}).get("notnull") == 1
    )
    if not needs_rebuild:
        return

    connection.execute(
        """
        CREATE TABLE complaints_new (
            id           TEXT PRIMARY KEY,
            created_date TEXT NOT NULL,
            closed_date  TEXT,
            state        TEXT,
            district     TEXT,
            municipality TEXT,
            village      TEXT,
            area         TEXT NOT NULL,
            pincode      TEXT,
            category     TEXT NOT NULL,
            priority     TEXT,
            status       TEXT NOT NULL DEFAULT 'Pending',
            description  TEXT NOT NULL,
            user_contact TEXT,
            image_path   TEXT
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


def seed_complaints(connection: sqlite3.Connection) -> None:
    df = pd.read_csv(CSV_PATH)
    df.to_sql("complaints", connection, if_exists="append", index=False)


def read_complaints_df() -> pd.DataFrame:
    init_db()
    if using_supabase():
        response = (
            get_supabase_client()
            .table(SUPABASE_TABLE)
            .select(",".join(COMPLAINT_COLUMNS))
            .order("created_date", desc=False)
            .execute()
        )
        return pd.DataFrame(response.data or [], columns=COMPLAINT_COLUMNS)
    with get_connection() as connection:
        return pd.read_sql_query("SELECT * FROM complaints", connection)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, object] | None:
    if row is None:
        return None
    return dict(row)


def get_complaint_by_id(complaint_id: str) -> dict[str, object] | None:
    init_db()
    if using_supabase():
        response = (
            get_supabase_client()
            .table(SUPABASE_TABLE)
            .select(",".join(COMPLAINT_COLUMNS))
            .eq("id", complaint_id)
            .maybe_single()
            .execute()
        )
        return _normalise_record(response.data) if response.data else None
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
        ).fetchone()
    return row_to_dict(row)


def insert_complaint(record: dict[str, object]) -> dict[str, object]:
    init_db()
    # Ensure an ID is always present. Generate using local logic first.
    if not record.get("id"):
        # Prefer supabase ID generation only if supabase is configured; otherwise use local generator.
        record["id"] = generate_next_id_supabase() if using_supabase() else generate_next_id()
    # If supabase is configured but ID generation failed for any reason, fallback to local ID.
    if not record.get("id"):
        record["id"] = generate_next_id()
    record = _normalise_record(record)
    try:
        if using_supabase():
            response = (
                get_supabase_client()
                .table(SUPABASE_TABLE)
                .insert(record)
                .execute()
            )
            return _normalise_record(response.data[0])
        with get_connection() as connection:
            placeholders = ", ".join("?" for _ in COMPLAINT_COLUMNS)
            columns_sql = ", ".join(COMPLAINT_COLUMNS)
            connection.execute(
                f"INSERT INTO complaints ({columns_sql}) VALUES ({placeholders})",
                tuple(record[column] for column in COMPLAINT_COLUMNS),
            )
    except Exception as exc:
        if _is_duplicate_error(exc):
            raise DuplicateComplaintError from exc
        raise
    return get_complaint_by_id(str(record["id"]))


def update_complaint_record(
    complaint_id: str, record: dict[str, object]
) -> dict[str, object] | None:
    init_db()
    existing = get_complaint_by_id(complaint_id) or {}
    record = _normalise_record({**existing, **record, "id": complaint_id})
    updates = {key: value for key, value in record.items() if key != "id"}
    if using_supabase():
        response = (
            get_supabase_client()
            .table(SUPABASE_TABLE)
            .update(updates)
            .eq("id", complaint_id)
            .execute()
        )
        if not response.data:
            return None
        return _normalise_record(response.data[0])
    with get_connection() as connection:
        update_columns = [column for column in COMPLAINT_COLUMNS if column != "id"]
        set_clause = ", ".join(f"{column} = ?" for column in update_columns)
        connection.execute(
            f"UPDATE complaints SET {set_clause} WHERE id = ?",
            tuple(record[column] for column in update_columns) + (complaint_id,),
        )
    return get_complaint_by_id(complaint_id)


def delete_complaint_record(complaint_id: str) -> None:
    init_db()
    if using_supabase():
        (
            get_supabase_client()
            .table(SUPABASE_TABLE)
            .delete()
            .eq("id", complaint_id)
            .execute()
        )
        return
    with get_connection() as connection:
        connection.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
