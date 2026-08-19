from __future__ import annotations

import re
from datetime import date

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s-]{7,14}[0-9]$")
PIN_RE = re.compile(r"^[1-9][0-9]{5}$")
VALID_STATUSES = {"Pending", "In Progress", "Closed"}
VALID_PRIORITIES = {"Low", "Medium", "High"}


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
    if closed_date:
        created = str(created_date)[:10]
        closed = str(closed_date)[:10]
        if closed < created:
            raise ValueError("closed_date cannot be before created_date")


def validate_priority(priority: str | None) -> str | None:
    if priority in (None, ""):
        return None
    if priority not in VALID_PRIORITIES:
        raise ValueError("priority must be Low, Medium, or High")
    return priority
