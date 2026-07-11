"""Canonical strict ISO date validation helpers for review-time parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any, Optional, Tuple


ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_BLOCKING_ERROR = "Date must use YYYY-MM-DD and be a real calendar date."
DATE_BLANK_ERROR = "Date field is empty"


@dataclass(frozen=True)
class DateValidationResult:
    """Structured validation result for review-time date parsing."""

    valid: bool
    normalized_value: Optional[str] = None
    blocking_error: Optional[str] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)


def validate_review_date(value: Any, *, allow_blank: bool = False) -> DateValidationResult:
    """
    Validate a reviewed date using strict ISO YYYY-MM-DD syntax.

    Uses datetime.date.fromisoformat() for calendar validation, but only after a
    strict dashed ISO pre-check so basic format YYYYMMDD is not accepted.
    """
    text = "" if value is None else str(value).strip()

    if not text:
        if allow_blank:
            return DateValidationResult(valid=True, normalized_value="")
        return DateValidationResult(valid=False, blocking_error=DATE_BLANK_ERROR)

    if not ISO_DATE_PATTERN.match(text):
        return DateValidationResult(valid=False, blocking_error=DATE_BLOCKING_ERROR)

    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return DateValidationResult(valid=False, blocking_error=DATE_BLOCKING_ERROR)

    return DateValidationResult(
        valid=True,
        normalized_value=parsed.isoformat(),
    )
