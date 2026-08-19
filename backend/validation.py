from __future__ import annotations

import re
from datetime import date

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s-]{7,14}[0-9]$")
PIN_RE = re.compile(r"^[1-9][0-9]{5}$")
VALID_STATUSES = {"Pending", "In Progress", "Closed"}
VALID_PRIORITIES = {"Low", "Medium", "High"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def clean_string(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


def validate_contact(value: str | None) -> str | None:
    value = clean_string(value)
    if value is None or value == "":
        return value
    if not (EMAIL_RE.fullmatch(value) or PHONE_RE.fullmatch(value)):
        raise ValueError("user_contact must be a valid email address or mobile number")
    return value


def validate_pincode(value: str | None) -> str | None:
    value = clean_string(value)
    if value is None or value == "":
        return value
    if not PIN_RE.fullmatch(value):
        raise ValueError("pincode must be a valid 6-digit Indian PIN code")
    return value


def validate_description(value: str | None, minimum: int = 10, maximum: int = 300) -> str:
    if not isinstance(value, str):
        raise ValueError("description is required")
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise ValueError(f"description must contain {minimum}-{maximum} characters")
    return value


def validate_state(status: str, created_date: date | str, closed_date: date | str | None) -> None:
    if status not in VALID_STATUSES:
        raise ValueError("status must be Pending, In Progress, or Closed")
    if status == "Closed" and not closed_date:
        raise ValueError("closed_date is required when status is Closed")
    if status != "Closed" and closed_date:
        raise ValueError("closed_date must be empty unless status is Closed")
    if closed_date and str(closed_date)[:10] < str(created_date)[:10]:
        raise ValueError("closed_date cannot be before created_date")


def validate_priority(priority: str | None) -> str | None:
    if priority in (None, ""):
        return None
    if priority not in VALID_PRIORITIES:
        raise ValueError("priority must be Low, Medium, or High")
    return priority


def validate_coordinates(latitude: float | None, longitude: float | None) -> tuple[float, float] | None:
    if latitude is None and longitude is None:
        return None
    if latitude is None or longitude is None:
        raise ValueError("latitude and longitude must be supplied together")
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    return float(latitude), float(longitude)


def validate_image_bytes(content: bytes, content_type: str | None) -> None:
    if not content:
        raise ValueError("uploaded image is empty")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValueError("image exceeds the 5 MB upload limit")
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("only JPEG, PNG, and WebP images are supported")
