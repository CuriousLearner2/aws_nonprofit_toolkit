"""Shared presentation shaping for validation issues."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def present_validation_issues(issues: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Convert canonical issue records into the validation UI contract."""
    return [
        {
            "field": issue.get("field", "unknown"),
            "reason": issue.get("description", issue.get("reason", "Issue detected")),
            "severity": issue.get("severity", "warning"),
        }
        for issue in issues
    ]
