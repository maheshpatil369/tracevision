"""Small, reusable input-validation helpers used by the service layer."""
from __future__ import annotations

import re

from app.utils.errors import ValidationAppError

CASE_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,50}$")
CASE_STATUSES = ("open", "in_progress", "closed", "archived")


def validate_case_number(value: str) -> str:
    value = (value or "").strip()
    if not CASE_NUMBER_PATTERN.match(value):
        raise ValidationAppError(
            "INVALID_CASE_NUMBER",
            "Case number must be 3-50 characters and contain only letters, numbers, '.', '_' or '-'.",
        )
    return value


def validate_case_status(value: str) -> str:
    if value not in CASE_STATUSES:
        raise ValidationAppError("INVALID_CASE_STATUS", f"Status must be one of {CASE_STATUSES}.")
    return value


def validate_pagination(page: int, page_size: int) -> tuple[int, int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    return page, page_size
