from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from backend.database import get_connection, init_db, row_to_dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Complaint Analytics Dashboard API",
    description="Analytics API for complaint volume, closure time, and area-wise public service trends.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Complaint Analytics Dashboard API",
        "docs": "/docs",
        "health": "/health",
        "status": "online"
    }

_frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
if _frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")


class ComplaintCreate(BaseModel):
    id:           str  = Field(min_length=3, max_length=20, examples=["CMP-101"])
    created_date: date
    area:         str  = Field(min_length=2, max_length=50)
    category:     str  = Field(min_length=2, max_length=50)
    description:  str  = Field(min_length=10, max_length=300)

    @field_validator("id", "area", "category", mode="before")
    @classmethod
    def strip_strings(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("description", mode="before")
    @classmethod
    def strip_and_validate_description(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if len(v) < 10:
                raise ValueError("description must be at least 10 non-whitespace characters")
        return v


class ComplaintUpdate(BaseModel):
    created_date: date | None = None
    closed_date:  date | None = None
    area:         str  | None = Field(default=None, min_length=2, max_length=50)
    category:     str  | None = Field(default=None, min_length=2, max_length=50)
    priority:     Literal["Low", "Medium", "High"]            | None = None
    status:       Literal["Pending", "In Progress", "Closed"] | None = None
    description:  str  | None = Field(default=None, min_length=10, max_length=300)

    @field_validator("area", "category", mode="before")
    @classmethod
    def strip_strings(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    @field_validator("description", mode="before")
    @classmethod
    def strip_and_validate_description(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            v = v.strip()
            if len(v) < 10:
                raise ValueError("description must be at least 10 non-whitespace characters")
        return v



def filtered_data(
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = None,
    category:   str  | None = None,
    status:     str  | None = None,
):
    return filter_complaints(load_complaints(), start_date, end_date, area, category, status)


@app.get("/")
async def root():
    return {"message": "Complaint Analytics API is running", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/options")
def options() -> dict[str, list[str]]:
    return get_options(load_complaints())


@app.get("/complaints")
def complaints(
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = Query(default=None),
    category:   str  | None = Query(default=None),
    status:     str  | None = Query(default=None),
) -> list[dict[str, object]]:
    return records(filtered_data(start_date, end_date, area, category, status))


@app.get("/complaints/export")
def export_complaints(
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = None,
    category:   str  | None = None,
    status:     str  | None = None,
):
    df = filtered_data(start_date, end_date, area, category, status)
    # Format dates and drop internal columns before export
    export_df = df.copy()
    for col in ["created_date", "closed_date"]:
        export_df[col] = export_df[col].dt.strftime("%Y-%m-%d")
    export_df = export_df.drop(columns=["closure_days"], errors="ignore")
    buffer = StringIO()
    export_df.to_csv(buffer, index=False)
    buffer.seek(0)
    headers = {"Content-Disposition": "attachment; filename=complaints_export.csv"}
    return StreamingResponse(buffer, media_type="text/csv", headers=headers)


@app.get("/complaints/{complaint_id}")
def get_complaint(complaint_id: str) -> dict[str, object]:
    init_db()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
        ).fetchone()
    complaint = row_to_dict(row)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@app.post("/complaints", status_code=status.HTTP_201_CREATED)
def create_complaint(payload: ComplaintCreate) -> dict[str, object]:
    init_db()
    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO complaints
                    (id, created_date, closed_date, area, category, priority, status, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.id,
                    payload.created_date.isoformat(),
                    None,
                    payload.area,
                    payload.category,
                    None,
                    "Pending",
                    payload.description,
                ),
            )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="Complaint ID already exists") from exc
        raise
    return get_complaint(payload.id)


@app.put("/complaints/{complaint_id}")
def update_complaint(complaint_id: str, payload: ComplaintUpdate) -> dict[str, object]:
    existing = get_complaint(complaint_id)
    updated  = {**existing, **payload.model_dump(exclude_unset=True)}

    created = updated["created_date"]
    closed  = updated["closed_date"]

    # Clear closed_date when status is moved away from Closed
    if payload.status is not None and payload.status != "Closed":
        closed = None
        updated["closed_date"] = None

    if isinstance(created, date):
        created = created.isoformat()
    if isinstance(closed, date):
        closed = closed.isoformat()
    if closed and closed < created:
        raise HTTPException(status_code=422, detail="closed_date cannot be before created_date")
    if updated["status"] == "Closed" and not closed:
        raise HTTPException(status_code=422, detail="closed_date is required when status is Closed")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE complaints
            SET created_date = ?, closed_date = ?, area = ?, category = ?,
                priority = ?, status = ?, description = ?
            WHERE id = ?
            """,
            (
                created, closed,
                updated["area"], updated["category"],
                updated["priority"], updated["status"], updated["description"],
                complaint_id,
            ),
        )
    return get_complaint(complaint_id)


@app.delete("/complaints/{complaint_id}")
def delete_complaint(complaint_id: str) -> dict[str, str]:
    get_complaint(complaint_id)
    with get_connection() as connection:
        connection.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
    return {"message": "Complaint deleted successfully"}


@app.get("/analytics/summary")
def analytics_summary(
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = None,
    category:   str  | None = None,
    status:     str  | None = None,
) -> dict[str, float | int]:
    return summary_metrics(filtered_data(start_date, end_date, area, category, status))


@app.get("/analytics/trends")
def analytics_trends(
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = None,
    category:   str  | None = None,
    status:     str  | None = None,
) -> list[dict[str, object]]:
    return monthly_trend(filtered_data(start_date, end_date, area, category, status))


@app.get("/analytics/area")
def analytics_area(
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = None,
    category:   str  | None = None,
    status:     str  | None = None,
) -> list[dict[str, object]]:
    return area_summary(filtered_data(start_date, end_date, area, category, status))


@app.get("/analytics/category")
def analytics_category(
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = None,
    category:   str  | None = None,
    status:     str  | None = None,
) -> list[dict[str, object]]:
    return category_summary(filtered_data(start_date, end_date, area, category, status))
