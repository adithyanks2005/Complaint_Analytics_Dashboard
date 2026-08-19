from __future__ import annotations

import logging
import os
from datetime import date, datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .database import (
    DatabaseConfigurationError,
    DatabaseUnavailableError,
    DuplicateComplaintError,
    check_database_health,
    delete_complaint_record,
    get_complaint_by_id,
    init_db,
    insert_complaint,
    read_complaints_df,
    update_complaint_record,
)
from .validation import validate_state

logger = logging.getLogger(__name__)

app = FastAPI(title="Complaint Analytics API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = None
    created_date: date = Field(default_factory=date.today)
    closed_date: Optional[date] = None
    state: Optional[str] = None
    district: Optional[str] = None
    municipality: Optional[str] = None
    village: Optional[str] = None
    area: str
    pincode: Optional[str] = None
    category: str
    priority: Optional[str] = None
    status: str = "Pending"
    description: str
    user_contact: Optional[str] = None
    image_path: Optional[str] = None


class ComplaintUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_date: Optional[date] = None
    closed_date: Optional[date] = None
    state: Optional[str] = None
    district: Optional[str] = None
    municipality: Optional[str] = None
    village: Optional[str] = None
    area: Optional[str] = None
    pincode: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    user_contact: Optional[str] = None
    image_path: Optional[str] = None


# Notification function is resolved lazily so tests and deployments without
# notification credentials remain functional.
try:
    from .notifier import notify as _notify_real
except Exception:  # pragma: no cover
    _notify_real = None


def _json_safe_record(record: dict) -> dict:
    """Convert Python date/datetime values to JSON-safe ISO strings."""
    safe = {}
    for key, value in record.items():
        if isinstance(value, (date, datetime)):
            safe[key] = value.isoformat()
        else:
            safe[key] = value
    return safe


@app.on_event("startup")
def startup() -> None:
    try:
        init_db()
        logger.info("database.startup.ok")
    except Exception:
        logger.exception("database.startup.failed")
        raise


@app.get("/")
def read_root():
    return {"message": "Complaint Analytics API", "status": "ok"}


@app.get("/health")
def health():
    db_health = check_database_health()
    return {
        "status": "ok" if db_health["status"] == "ok" else "degraded",
        "database": db_health,
    }


@app.get("/health/database")
def database_health():
    result = check_database_health()
    if result["status"] != "ok":
        return result
    return result


@app.get("/complaints")
def list_complaints():
    try:
        df = read_complaints_df()
    except (DatabaseUnavailableError, DatabaseConfigurationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if df.empty:
        return []
    return df.where(pd.notna(df), None).to_dict(orient="records")


@app.get("/complaints/{complaint_id}")
def get_complaint(complaint_id: str):
    try:
        result = get_complaint_by_id(complaint_id)
    except (DatabaseUnavailableError, DatabaseConfigurationError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not result:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return result


@app.post("/complaints")
def create_complaint(payload: ComplaintCreate):
    complaint_data = _json_safe_record(payload.model_dump(exclude_unset=True))
    if complaint_data.get("status") != "Closed":
        complaint_data["closed_date"] = None
    try:
        validate_state(
            complaint_data.get("status", "Pending"),
            complaint_data.get("created_date"),
            complaint_data.get("closed_date"),
        )
        result = insert_complaint(complaint_data)
    except DuplicateComplaintError as exc:
        raise HTTPException(status_code=409, detail="Complaint ID already exists") from exc
    except (ValueError, DatabaseConfigurationError, DatabaseUnavailableError) as exc:
        status = 422 if isinstance(exc, ValueError) else 503
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    logger.info(
        "complaint.created id=%s status=%s priority=%s",
        result["id"],
        result["status"],
        result["priority"],
    )

    if _notify_real and payload.user_contact:
        try:
            _notify_real(
                payload.user_contact,
                "New Complaint Received",
                f"Complaint ID {result['id']} has been logged.",
            )
        except Exception:
            logger.exception("notification.failed complaint_id=%s", result["id"])
    return result


@app.put("/complaints/{complaint_id}")
def update_complaint(complaint_id: str, payload: ComplaintUpdate):
    try:
        existing = get_complaint_by_id(complaint_id)
    except (DatabaseConfigurationError, DatabaseUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not existing:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # JSON-mode dumping guarantees dates are serialized before the record reaches
    # Supabase/PostgREST. This avoids Python date objects leaking into JSON payloads.
    incoming = payload.model_dump(exclude_unset=True, mode="json")
    updated = {**existing, **incoming}
    if payload.status is not None and payload.status != "Closed":
        updated["closed_date"] = None

    try:
        validate_state(updated["status"], updated["created_date"], updated.get("closed_date"))
        result = update_complaint_record(complaint_id, _json_safe_record(updated))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (DatabaseConfigurationError, DatabaseUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    logger.info(
        "complaint.updated id=%s status=%s",
        complaint_id,
        result["status"] if result else "unknown",
    )
    return result


@app.delete("/complaints/{complaint_id}")
def delete_complaint(complaint_id: str):
    try:
        if not get_complaint_by_id(complaint_id):
            raise HTTPException(status_code=404, detail="Complaint not found")
        delete_complaint_record(complaint_id)
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found") from exc
    except (DatabaseConfigurationError, DatabaseUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    logger.info("complaint.deleted id=%s", complaint_id)
    return {"message": "Complaint deleted successfully", "id": complaint_id}
