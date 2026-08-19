from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from backend.analytics import (
    area_summary,
    category_summary,
    filter_complaints,
    get_options,
    load_complaints,
    monthly_trend,
    records,
    summary_metrics,
)
from backend.ai_prioritizer import compute_priority
from backend.database import (
    DatabaseConfigurationError,
    DatabaseUnavailableError,
    DuplicateComplaintError,
    check_database_health,
    delete_complaint_record,
    get_complaint_by_id,
    init_db,
    insert_complaint,
    update_complaint_record,
)
from backend.validation import (
    clean_string,
    validate_contact,
    validate_description,
    validate_pincode,
    validate_priority,
    validate_state,
)

logger = logging.getLogger(__name__)

try:
    from frontend.notifier import notify as _notify_real
except Exception:  # pragma: no cover
    _notify_real = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("api.startup database_initialization_begin")
    init_db()
    logger.info("api.startup database_initialization_complete")
    yield


app = FastAPI(
    title="Complaint Analytics Dashboard API",
    description="Production complaint management and analytics API.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

_frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


@app.exception_handler(DatabaseUnavailableError)
async def database_unavailable_handler(_: Request, exc: DatabaseUnavailableError):
    logger.exception("api.database_unavailable", exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": str(exc), "code": "DATABASE_UNAVAILABLE"})


@app.exception_handler(DatabaseConfigurationError)
async def database_configuration_handler(_: Request, exc: DatabaseConfigurationError):
    logger.exception("api.database_configuration_error", exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": str(exc), "code": "DATABASE_CONFIGURATION_ERROR"})


class ComplaintCreateInput(BaseModel):
    id: str | None = Field(default=None, min_length=3, max_length=20)
    created_date: date
    state: str | None = Field(default=None, min_length=2, max_length=50)
    district: str | None = Field(default=None, min_length=2, max_length=50)
    municipality: str | None = Field(default=None, min_length=2, max_length=80)
    village: str | None = Field(default=None, min_length=2, max_length=80)
    area: str = Field(min_length=2, max_length=50)
    pincode: str | None = Field(default=None, min_length=6, max_length=6)
    category: str = Field(min_length=2, max_length=50)
    priority: Literal["Low", "Medium", "High"] | None = None
    user_contact: str | None = Field(default=None, min_length=5, max_length=100)
    image_path: str | None = Field(default=None, max_length=300)
    description: str = Field(min_length=10, max_length=300)

    @field_validator("id", "state", "district", "municipality", "village", "area", "pincode", "category", "user_contact", "image_path", mode="before")
    @classmethod
    def strip_strings(cls, value):
        return clean_string(value)

    @field_validator("pincode")
    @classmethod
    def pincode_validator(cls, value):
        return validate_pincode(value)

    @field_validator("user_contact")
    @classmethod
    def contact_validator(cls, value):
        return validate_contact(value)

    @field_validator("description")
    @classmethod
    def description_validator(cls, value):
        return validate_description(value)


class ComplaintUpdate(BaseModel):
    created_date: date | None = None
    closed_date: date | None = None
    state: str | None = Field(default=None, min_length=2, max_length=50)
    district: str | None = Field(default=None, min_length=2, max_length=50)
    municipality: str | None = Field(default=None, min_length=2, max_length=80)
    village: str | None = Field(default=None, min_length=2, max_length=80)
    area: str | None = Field(default=None, min_length=2, max_length=50)
    pincode: str | None = Field(default=None, min_length=6, max_length=6)
    category: str | None = Field(default=None, min_length=2, max_length=50)
    priority: Literal["Low", "Medium", "High"] | None = None
    status: Literal["Pending", "In Progress", "Closed"] | None = None
    user_contact: str | None = Field(default=None, min_length=5, max_length=100)
    image_path: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, min_length=10, max_length=300)

    @field_validator("state", "district", "municipality", "village", "area", "pincode", "category", "user_contact", "image_path", mode="before")
    @classmethod
    def strip_strings(cls, value):
        return clean_string(value)

    @field_validator("pincode")
    @classmethod
    def pincode_validator(cls, value):
        return validate_pincode(value)

    @field_validator("user_contact")
    @classmethod
    def contact_validator(cls, value):
        return validate_contact(value)

    @field_validator("description")
    @classmethod
    def description_validator(cls, value):
        return validate_description(value) if value is not None else value

    @field_validator("priority")
    @classmethod
    def priority_validator(cls, value):
        return validate_priority(value)


def filtered_data(start_date=None, end_date=None, state=None, district=None, area=None, pincode=None, category=None, status=None):
    return filter_complaints(load_complaints(), start_date, end_date, state, district, area, pincode, category, status)


@app.get("/")
async def root():
    return {"message": "Complaint Analytics Dashboard API", "docs": "/docs", "health": "/health", "status": "online"}


@app.get("/health")
def health():
    database = check_database_health()
    payload = {"status": "ok" if database["status"] == "ok" else "degraded", "database": database}
    if database["status"] != "ok":
        raise HTTPException(status_code=503, detail=payload)
    return payload


@app.get("/health/database")
def database_health():
    database = check_database_health()
    if database["status"] != "ok":
        raise HTTPException(status_code=503, detail=database)
    return database


@app.get("/options")
def options():
    return get_options(load_complaints())


@app.get("/complaints")
def complaints(
    start_date: date | None = None, end_date: date | None = None,
    state: str | None = Query(default=None), district: str | None = Query(default=None),
    area: str | None = Query(default=None), pincode: str | None = Query(default=None),
    category: str | None = Query(default=None), status: str | None = Query(default=None),
):
    return records(filtered_data(start_date, end_date, state, district, area, pincode, category, status))


@app.get("/complaints/export")
def export_complaints(
    start_date: date | None = None, end_date: date | None = None,
    state: str | None = None, district: str | None = None, area: str | None = None,
    pincode: str | None = None, category: str | None = None, status: str | None = None,
):
    df = filtered_data(start_date, end_date, state, district, area, pincode, category, status).copy()
    for column in ["created_date", "closed_date"]:
        if column in df.columns:
            df[column] = df[column].dt.strftime("%Y-%m-%d")
            df[column] = df[column].where(df[column].notna(), None)
    df = df.drop(columns=["closure_days"], errors="ignore")
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=complaints_export.csv"})


@app.get("/complaints/{complaint_id}")
def get_complaint(complaint_id: str):
    complaint = get_complaint_by_id(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@app.post("/complaints", status_code=status.HTTP_201_CREATED)
def create_complaint(payload: ComplaintCreateInput):
    priority = payload.priority or compute_priority(payload.description)
    complaint_data = {
        "id": payload.id,
        "created_date": payload.created_date.isoformat(),
        "closed_date": None,
        "state": payload.state,
        "district": payload.district,
        "municipality": payload.municipality,
        "village": payload.village,
        "area": payload.area,
        "pincode": payload.pincode,
        "category": payload.category,
        "priority": priority,
        "status": "Pending",
        "description": payload.description,
        "user_contact": payload.user_contact,
        "image_path": payload.image_path,
    }
    try:
        result = insert_complaint(complaint_data)
    except DuplicateComplaintError as exc:
        raise HTTPException(status_code=409, detail="Complaint ID already exists") from exc
    logger.info("complaint.created id=%s status=%s priority=%s", result["id"], result["status"], result["priority"])

    if _notify_real and payload.user_contact:
        try:
            _notify_real(
                payload.user_contact,
                "New Complaint Received",
                f"Complaint ID {result['id']} has been logged.",
            )
        except Exception:
            # Notification is non-transactional: the complaint remains committed,
            # but the failure is visible in structured logs instead of being swallowed.
            logger.exception("notification.failed complaint_id=%s", result["id"])
    return result


@app.put("/complaints/{complaint_id}")
def update_complaint(complaint_id: str, payload: ComplaintUpdate):
    existing = get_complaint_by_id(complaint_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Complaint not found")
    updated = {**existing, **payload.model_dump(exclude_unset=True)}
    if payload.status is not None and payload.status != "Closed":
        updated["closed_date"] = None
    validate_state(updated["status"], updated["created_date"], updated.get("closed_date"))
    try:
        result = update_complaint_record(complaint_id, updated)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    logger.info("complaint.updated id=%s status=%s", complaint_id, result["status"] if result else "unknown")
    return result


@app.delete("/complaints/{complaint_id}")
def delete_complaint(complaint_id: str):
    if not get_complaint_by_id(complaint_id):
        raise HTTPException(status_code=404, detail="Complaint not found")
    try:
        delete_complaint_record(complaint_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found") from exc
    logger.info("complaint.deleted id=%s", complaint_id)
    return {"message": "Complaint deleted successfully", "id": complaint_id}


@app.get("/analytics/summary")
def analytics_summary(start_date: date | None = None, end_date: date | None = None, state: str | None = None, district: str | None = None, area: str | None = None, pincode: str | None = None, category: str | None = None, status: str | None = None):
    return summary_metrics(filtered_data(start_date, end_date, state, district, area, pincode, category, status))


@app.get("/analytics/trends")
def analytics_trends(start_date: date | None = None, end_date: date | None = None, state: str | None = None, district: str | None = None, area: str | None = None, pincode: str | None = None, category: str | None = None, status: str | None = None):
    return monthly_trend(filtered_data(start_date, end_date, state, district, area, pincode, category, status))


@app.get("/analytics/area")
def analytics_area(start_date: date | None = None, end_date: date | None = None, state: str | None = None, district: str | None = None, area: str | None = None, pincode: str | None = None, category: str | None = None, status: str | None = None):
    return area_summary(filtered_data(start_date, end_date, state, district, area, pincode, category, status))


@app.get("/analytics/category")
def analytics_category(start_date: date | None = None, end_date: date | None = None, state: str | None = None, district: str | None = None, area: str | None = None, pincode: str | None = None, category: str | None = None, status: str | None = None):
    return category_summary(filtered_data(start_date, end_date, state, district, area, pincode, category, status))
