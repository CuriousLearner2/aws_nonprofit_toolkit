"""Canonical address source-capability and review-warning policy."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Optional


# Ordered to preserve the existing preference for the specific Address 1
# column when a source contains both Address and Address 1.
ADDRESS_SOURCE_ALIASES = (
    "Address 1",
    "Street Address",
    "Address Line 1",
    "Address",
    "address_1",
    "address_line_1",
    "street_address",
)


def find_address_source_column(columns: Iterable[Any]) -> Optional[Any]:
    """Return the recognized source column for an address, if present."""
    available = {str(column).strip().casefold(): column for column in columns}
    for alias in ADDRESS_SOURCE_ALIASES:
        column = available.get(alias.casefold())
        if column is not None:
            return column
    return None


def has_address_source(raw_data: Mapping[Any, Any] | None) -> bool:
    """Return whether raw imported data contains a recognized address field."""
    if not isinstance(raw_data, Mapping):
        return False
    return find_address_source_column(raw_data.keys()) is not None


def get_address_source_value(raw_data: Mapping[Any, Any] | None) -> Any:
    """Return the raw value from the canonical recognized address column."""
    if not isinstance(raw_data, Mapping):
        return None
    data = raw_data
    column = find_address_source_column(data.keys())
    return data.get(column) if column is not None else None


def evaluate_address_issue(address: Any) -> Optional[dict[str, Any]]:
    """Return the single canonical non-blocking address issue, if any."""
    if address is None or str(address).strip().casefold() in {"", "nan", "none", "null"}:
        return {
            "field": "address",
            "reason": "missing",
            "description": "Missing address",
            "severity": "warning",
            "is_new": True,
        }

    normalized = " ".join(str(address).strip().split())
    if normalized.count(",") == 1:
        suffix = normalized.split(",", 1)[1].strip()
        if re.fullmatch(r"[A-Za-z .'-]+\s+[A-Z]{2}(?:\s+\d{5}(?:-\d{4})?)?", suffix):
            return {
                "field": "address",
                "reason": "malformed",
                "description": "Malformed address",
                "severity": "warning",
                "is_new": True,
            }

    return None
