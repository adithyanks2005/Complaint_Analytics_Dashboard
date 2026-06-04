"""
backfill_locations.py
Backfills state, district, municipality, village, pincode for existing
complaint records that are missing these fields, using the sample CSV as
the reference source.

Run from the repo root:
    python scripts/backfill_locations.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

import pandas as pd
from backend.database import (
    init_db,
    using_supabase,
    get_connection,
    get_supabase_client,
    SUPABASE_TABLE,
    read_complaints_df,
    update_complaint_record,
)

CSV_PATH = ROOT / "data" / "sample_complaints.csv"

LOCATION_COLS = ["state", "district", "municipality", "village", "pincode"]


def backfill_sqlite() -> None:
    print("Backfilling SQLite database...")
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT id, state, district, municipality, village, pincode FROM complaints"
        ).fetchall()
        updated = 0
        for row in rows:
            row_dict = dict(row)
            missing = [c for c in LOCATION_COLS if not row_dict.get(c)]
            if not missing:
                continue
            # Try to match by ID in CSV
            csv_match = ref_df[ref_df["id"] == row_dict["id"]]
            if not csv_match.empty:
                set_parts = ", ".join(f"{c} = ?" for c in missing)
                vals = [str(csv_match.iloc[0][c]) if pd.notna(csv_match.iloc[0].get(c)) else None for c in missing]
                vals.append(row_dict["id"])
                conn.execute(f"UPDATE complaints SET {set_parts} WHERE id = ?", vals)
                updated += 1
        print(f"  Updated {updated} rows in SQLite.")


def backfill_supabase() -> None:
    print("Backfilling Supabase table...")
    client = get_supabase_client()
    resp = client.table(SUPABASE_TABLE).select("id,state,district,municipality,village,pincode").execute()
    rows = resp.data or []
    updated = 0
    for row in rows:
        missing = [c for c in LOCATION_COLS if not row.get(c)]
        if not missing:
            continue
        csv_match = ref_df[ref_df["id"] == row["id"]]
        if not csv_match.empty:
            updates = {}
            for c in missing:
                val = csv_match.iloc[0].get(c)
                if pd.notna(val) and str(val).strip():
                    updates[c] = str(val).strip()
            if updates:
                client.table(SUPABASE_TABLE).update(updates).eq("id", row["id"]).execute()
                updated += 1
    print(f"  Updated {updated} rows in Supabase.")


def report_missing() -> None:
    print("\nChecking for remaining missing location data...")
    df = read_complaints_df()
    for col in LOCATION_COLS:
        if col in df.columns:
            missing = df[df[col].isna() | (df[col].astype(str).str.strip() == "")]["id"].tolist()
            print(f"  {col}: {len(missing)} rows missing")
    print()


if __name__ == "__main__":
    init_db()
    ref_df = pd.read_csv(CSV_PATH) if CSV_PATH.exists() else pd.DataFrame()

    if using_supabase():
        backfill_supabase()
    else:
        backfill_sqlite()

    report_missing()
    print("Done.")
