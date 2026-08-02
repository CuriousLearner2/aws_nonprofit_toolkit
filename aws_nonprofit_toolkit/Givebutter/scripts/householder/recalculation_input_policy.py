"""Canonical recalculation-input preparation for autosave and issue recalculation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .issue_identity import normalize_validation_issue_field


def prepare_recalculation_input(
    effective_values: Mapping[str, Any] | None,
    proposed_values: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a non-mutating merge of effective values with proposed values."""
    prepared = dict(effective_values or {})
    for source in (effective_values or {}, proposed_values or {}):
        for field, value in source.items():
            prepared[field] = value
            canonical_field = normalize_validation_issue_field(field)
            if canonical_field:
                prepared[canonical_field] = value
    return prepared


def value_for_validation_field(values: Mapping[str, Any] | None, field_name: Any) -> Any:
    """Resolve the value used by validation and issue comparison for a field."""
    if not values:
        return None

    canonical_field = normalize_validation_issue_field(field_name)
    if canonical_field:
        blank_match = None
        for key, value in values.items():
            if normalize_validation_issue_field(key) == canonical_field:
                if value is not None and str(value).strip():
                    return value
                if blank_match is None:
                    blank_match = value
        if blank_match is not None:
            return blank_match
    return values.get(field_name)
