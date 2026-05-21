from __future__ import annotations

from datetime import date

import pandas as pd

from backend.database import read_complaints_df


def load_complaints() -> pd.DataFrame:
    df = read_complaints_df().copy()
    created_date = pd.to_datetime(df["created_date"], errors="coerce", utc=True).dt.tz_localize(None)
    closed_date = pd.to_datetime(df["closed_date"], errors="coerce", utc=True).dt.tz_localize(None)
    return df.assign(
        created_date=created_date,
        closed_date=closed_date,
        closure_days=(closed_date - created_date).dt.days,
    )


def filter_complaints(
    df: pd.DataFrame,
    start_date: date | None = None,
    end_date:   date | None = None,
    area:       str  | None = None,
    category:   str  | None = None,
    status:     str  | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    if start_date:
        filtered = filtered[filtered["created_date"].dt.date >= start_date]
    if end_date:
        filtered = filtered[filtered["created_date"].dt.date <= end_date]
    if area and area != "All":
        filtered = filtered[filtered["area"] == area]
    if category and category != "All":
        filtered = filtered[filtered["category"] == category]
    if status and status != "All":
        filtered = filtered[filtered["status"] == status]
    return filtered.sort_values("created_date", ascending=False)


def get_options(df: pd.DataFrame) -> dict[str, list[str]]:
    return {
        "areas":      sorted(df["area"].dropna().unique().tolist()),
        "categories": sorted(df["category"].dropna().unique().tolist()),
        "statuses":   sorted(df["status"].dropna().unique().tolist()),
    }


def summary_metrics(df: pd.DataFrame) -> dict[str, float | int]:
    total     = int(len(df))
    closed_df = df[df["status"] == "Closed"]
    open_df   = df[df["status"] != "Closed"]
    # nanmean returns nan when all values are NaN; guard with explicit check
    raw_avg      = closed_df["closure_days"].mean() if not closed_df.empty else 0.0
    avg_closure  = float(raw_avg) if raw_avg == raw_avg else 0.0   # nan != nan
    closure_rate = round((len(closed_df) / total) * 100, 2) if total else 0.0
    return {
        "total_complaints":     total,
        "closed_complaints":    int(len(closed_df)),
        "open_or_pending":      int(len(open_df)),
        "average_closure_days": round(avg_closure, 2),
        "closure_rate_percent": closure_rate,
    }


def monthly_trend(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []
    trend = (
        df.assign(month=df["created_date"].dt.to_period("M").astype(str))
        .groupby("month")
        .size()
        .reset_index(name="complaints")
        .sort_values("month")
    )
    return trend.to_dict(orient="records")


def area_summary(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []
    summary = (
        df.groupby("area")
        .agg(
            complaints=("id", "count"),
            avg_closure_days=("closure_days", "mean"),
            closed=("status", lambda v: int((v == "Closed").sum())),
        )
        .reset_index()
        .sort_values("complaints", ascending=False)
    )
    summary["avg_closure_days"] = summary["avg_closure_days"].round(2)
    # Replace NaN (areas with no closed complaints) with None so JSON stays valid
    summary["avg_closure_days"] = summary["avg_closure_days"].where(
        summary["avg_closure_days"].notna(), other=None
    )
    return summary.to_dict(orient="records")


def category_summary(df: pd.DataFrame) -> list[dict[str, object]]:
    if df.empty:
        return []
    summary = (
        df.groupby("category")
        .size()
        .reset_index(name="complaints")
        .sort_values("complaints", ascending=False)
    )
    return summary.to_dict(orient="records")


def records(df: pd.DataFrame) -> list[dict[str, object]]:
    output = df.copy()
    # Format date columns as ISO strings; NaT → None
    for col in ["created_date", "closed_date"]:
        output[col] = output[col].dt.strftime("%Y-%m-%d")
        output[col] = output[col].where(output[col].notna(), None)
    # Drop internal computed column — not part of the public API contract
    output = output.drop(columns=["closure_days"], errors="ignore")
    return output.to_dict(orient="records")
