from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from threading import Lock

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "sample_complaints.csv"
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "complaints")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_KEY", "").strip()
    or os.getenv("SUPABASE_ANON_KEY", "").strip()
)
DB_PATH = Path(os.getenv("TEST_DB_PATH", str(DATA_DIR / "complaints.db")))

COMPLAINT_COLUMNS = [
    "id", "created_date", "closed_date", "state", "district", "municipality",
    "village", "area", "pincode", "category", "priority", "status", "description",
    "user_contact", "image_path",
]

_db_initialised = False
_init_lock = Lock()
_write_lock = Lock()
_supabase_client = None
# Kept for backwards compatibility with older tests; it is deliberately NOT used
# to route requests, so one failed request can never silently change the data store.
_supabase_failed = False


class DatabaseUnavailableError(RuntimeError):
    """Raised when the configured authoritative database cannot be reached."""


class DatabaseConfigurationError(RuntimeError):
    """Raised when database configuration is incomplete."""


class DuplicateComplaintError(Exception):
    """Raised when a complaint ID already exists."""


def _supabase_configured() -> bool:
    return bool(SUPABASE_URL or SUPABASE_KEY)


def using_supabase() -> bool:
    """Return whether Supabase is the authoritative configured store.

    SQLite is used only when Supabase is completely unconfigured. A configured
    but unhealthy Supabase instance never falls back to SQLite.
    """
    if _supabase_configured() and not (SUPABASE_URL and SUPABASE_KEY):
        raise DatabaseConfigurationError(
            "SUPABASE_URL and a Supabase key must both be configured."
        )
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
        except ImportError as exc:  # pragma: no cover
            raise DatabaseConfigurationError(
                "Supabase is configured but the supabase package is not installed."
            ) from exc
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def _is_duplicate_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "23505" in message or "duplicate key" in message or "unique constraint" in message


def _normalise_record(record: dict[str, object] | None) -> dict[str, object] | None:
    if record is None:
        return None
    return {column: record.get(column) for column in COMPLAINT_COLUMNS}


def _validate_state(record: dict[str, object]) -> None:
    status = record.get("status") or "Pending"
    closed_date = record.get("closed_date")
    if status not in {"Pending", "In Progress", "Closed"}:
        raise ValueError("status must be Pending, In Progress, or Closed")
    if record.get("priority") not in {None, "", "Low", "Medium", "High"}:
        raise ValueError("priority must be Low, Medium, or High")
    if status == "Closed" and not closed_date:
        raise ValueError("closed_date is required when status is Closed")
    if status != "Closed" and closed_date:
        raise ValueError("closed_date must be empty unless status is Closed")
    created = str(record.get("created_date") or "")[:10]
    closed = str(closed_date or "")[:10]
    if created and closed and closed < created:
        raise ValueError("closed_date cannot be before created_date")


def _mark_supabase_failure(exc: Exception) -> None:
    # No failover is performed. The next request is allowed to retry Supabase.
    global _supabase_failed
    _supabase_failed = True
    logger.exception("database.supabase_request_failed", exc_info=exc)


def check_database_health() -> dict[str, object]:
    """Actively verify the configured authoritative store."""
    if using_supabase():
        try:
            query = get_supabase_client().table(SUPABASE_TABLE).select("id")
            limit = getattr(query, "limit", None)
            if callable(limit):
                query = limit(1)
            query.execute()
            return {"status": "ok", "backend": "supabase"}
        except Exception as exc:
            _mark_supabase_failure(exc)
            return {"status": "unavailable", "backend": "supabase", "error": str(exc)}
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return {"status": "ok", "backend": "sqlite"}
    except Exception as exc:
        logger.exception("database.sqlite_health_failed")
        return {"status": "unavailable", "backend": "sqlite", "error": str(exc)}

def seed_complaints(connection: sqlite3.Connection) -> None:
    if not CSV_PATH.exists():
        return
    df = pd.read_csv(CSV_PATH)
    missing = [column for column in COMPLAINT_COLUMNS if column not in df.columns]
    for column in missing:
        df[column] = None
    df = df[COMPLAINT_COLUMNS]
    # Keep seed data compatible with the state invariants.
    for index, row in df.iterrows():
        if row["status"] != "Closed":
            df.at[index, "closed_date"] = None
        if pd.isna(df.at[index, "priority"]):
            df.at[index, "priority"] = None
    df.to_sql("complaints", connection, if_exists="append", index=False)


def _create_sqlite_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
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
            image_path TEXT,
            CHECK (status IN ('Pending', 'In Progress', 'Closed')),
            CHECK (priority IS NULL OR priority IN ('Low', 'Medium', 'High')),
            CHECK ((status = 'Closed' AND closed_date IS NOT NULL) OR
                   (status <> 'Closed' AND closed_date IS NULL)),
            CHECK (closed_date IS NULL OR substr(closed_date, 1, 10) >= substr(created_date, 1, 10))
        )
        """
    )


def migrate_schema(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(complaints)").fetchall()}
    for column in ["state", "district", "municipality", "village", "pincode", "user_contact", "image_path"]:
        if column not in columns:
            connection.execute(f"ALTER TABLE complaints ADD COLUMN {column} TEXT")


def init_db() -> None:
    global _db_initialised
    if using_supabase():
        # Supabase migrations own the production schema. Fail startup if it is unavailable.
        health = check_database_health()
        if health["status"] != "ok":
            raise DatabaseUnavailableError(
                f"Authoritative Supabase database unavailable: {health.get('error', 'unknown error')}"
            )
        _db_initialised = True
        return

    if _db_initialised:
        return
    with _init_lock:
        if _db_initialised:
            return
        with get_connection() as conn:
            _create_sqlite_schema(conn)
            migrate_schema(conn)
            if conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0] == 0:
                try:
                    seed_complaints(conn)
                except Exception:
                    logger.exception("database.seed_failed")
                    raise
        _db_initialised = True


def _sqlite_next_id(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        """
        SELECT COALESCE(MAX(CAST(substr(id, 5) AS INTEGER)), 0) + 1
        FROM complaints WHERE id GLOB 'CMP-[0-9]*'
        """
    ).fetchone()
    return f"CMP-{int(row[0]):03d}"


def generate_next_id() -> str:
    """Compatibility helper; inserts themselves own ID allocation."""
    init_db()
    if using_supabase():
        # Do not use this for inserts; production IDs are generated by the DB trigger.
        resp = get_supabase_client().table(SUPABASE_TABLE).select("id").execute()
        numbers = [
            int(str(item.get("id", "")).split("-")[-1])
            for item in (resp.data or [])
            if str(item.get("id", "")).split("-")[-1].isdigit()
        ]
        return f"CMP-{max(numbers, default=0) + 1:03d}"
    with get_connection() as conn:
        return _sqlite_next_id(conn)


def generate_next_id_supabase() -> str:
    """Generate an ID from the authoritative Supabase table without routing through SQLite."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        return generate_next_id()
    try:
        response = get_supabase_client().table(SUPABASE_TABLE).select("id").execute()
    except Exception as exc:
        _mark_supabase_failure(exc)
        raise DatabaseUnavailableError(
            "Authoritative Supabase database unavailable; complaint ID allocation cannot proceed."
        ) from exc
    numbers = [
        int(str(item.get("id", "")).split("-")[-1])
        for item in (response.data or [])
        if str(item.get("id", "")).split("-")[-1].isdigit()
    ]
    return f"CMP-{max(numbers, default=0) + 1:03d}"

def read_complaints_df() -> pd.DataFrame:
    init_db()
    if using_supabase():
        try:
            response = (
                get_supabase_client().table(SUPABASE_TABLE)
                .select(",".join(COMPLAINT_COLUMNS))
                .order("created_date", desc=False)
                .execute()
            )
            return pd.DataFrame(response.data or [], columns=COMPLAINT_COLUMNS)
        except Exception as exc:
            _mark_supabase_failure(exc)
            raise DatabaseUnavailableError("Supabase read failed; no SQLite fallback is permitted") from exc
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM complaints ORDER BY created_date ASC", conn)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, object] | None:
    return dict(row) if row is not None else None


def get_complaint_by_id(complaint_id: str) -> dict[str, object] | None:
    init_db()
    if using_supabase():
        try:
            response = (
                get_supabase_client().table(SUPABASE_TABLE)
                .select(",".join(COMPLAINT_COLUMNS))
                .eq("id", complaint_id).maybe_single().execute()
            )
            return _normalise_record(response.data)
        except Exception as exc:
            _mark_supabase_failure(exc)
            raise DatabaseUnavailableError("Supabase read failed; no SQLite fallback is permitted") from exc
    with get_connection() as conn:
        return row_to_dict(conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone())


def insert_complaint(record: dict[str, object]) -> dict[str, object]:
    init_db()
    data = _normalise_record(record) or {}
    if not data.get("status"):
        data["status"] = "Pending"
    _validate_state(data)

    if using_supabase():
        try:
            # Do not manufacture an ID here. The Postgres trigger allocates it atomically.
            if not data.get("id"):
                data.pop("id", None)
            response = get_supabase_client().table(SUPABASE_TABLE).insert(data).execute()
            if not response.data:
                raise DatabaseUnavailableError("Supabase insert returned no row")
            return _normalise_record(response.data[0]) or {}
        except Exception as exc:
            if _is_duplicate_error(exc):
                raise DuplicateComplaintError from exc
            _mark_supabase_failure(exc)
            raise DatabaseUnavailableError("Supabase insert failed; no SQLite fallback is permitted") from exc

    with _write_lock:
        with get_connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                if not data.get("id"):
                    data["id"] = _sqlite_next_id(conn)
                placeholders = ",".join("?" for _ in COMPLAINT_COLUMNS)
                conn.execute(
                    f"INSERT INTO complaints ({','.join(COMPLAINT_COLUMNS)}) VALUES ({placeholders})",
                    tuple(data.get(column) for column in COMPLAINT_COLUMNS),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                if _is_duplicate_error(exc) or "UNIQUE" in str(exc).upper():
                    raise DuplicateComplaintError from exc
                raise
    return get_complaint_by_id(str(data["id"])) or data


def update_complaint_record(complaint_id: str, record: dict[str, object]) -> dict[str, object] | None:
    init_db()
    existing = get_complaint_by_id(complaint_id)
    if existing is None:
        return None
    data = _normalise_record({**existing, **record, "id": complaint_id}) or {}
    _validate_state(data)
    updates = {key: value for key, value in data.items() if key != "id"}

    if using_supabase():
        try:
            response = get_supabase_client().table(SUPABASE_TABLE).update(updates).eq("id", complaint_id).execute()
            return _normalise_record(response.data[0]) if response.data else None
        except Exception as exc:
            _mark_supabase_failure(exc)
            raise DatabaseUnavailableError("Supabase update failed; no SQLite fallback is permitted") from exc

    with get_connection() as conn:
        set_clause = ",".join(f"{column} = ?" for column in updates)
        conn.execute(
            f"UPDATE complaints SET {set_clause} WHERE id = ?",
            tuple(updates.values()) + (complaint_id,),
        )
    return get_complaint_by_id(complaint_id)


def delete_complaint_record(complaint_id: str) -> None:
    init_db()
    if using_supabase():
        try:
            response = get_supabase_client().table(SUPABASE_TABLE).delete().eq("id", complaint_id).execute()
            if not response.data:
                raise KeyError(complaint_id)
            return
        except KeyError:
            raise
        except Exception as exc:
            _mark_supabase_failure(exc)
            raise DatabaseUnavailableError("Supabase delete failed; no SQLite fallback is permitted") from exc
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
        if cursor.rowcount == 0:
            raise KeyError(complaint_id)


def reset_database_state_for_tests() -> None:
    global _db_initialised, _supabase_client, _supabase_failed
    _db_initialised = False
    _supabase_client = None
    _supabase_failed = False
