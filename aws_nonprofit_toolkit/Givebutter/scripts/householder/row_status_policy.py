"""Canonical row-status policy for issue lists."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def derive_row_status(issues: Iterable[dict[str, Any]] | None) -> str:
    """Map an issue list to Blocking, Warning, or No issues."""
    issue_list = list(issues or [])
    if any(issue.get("severity") == "error" for issue in issue_list):
        return "Blocking"
    if issue_list:
        return "Warning"
    return "No issues"
