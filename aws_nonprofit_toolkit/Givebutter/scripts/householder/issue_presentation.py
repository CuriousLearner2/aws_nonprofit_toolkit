"""Shared presentation shaping for validation issues."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .issue_evaluation_policy import evaluate_effective_values
from .issue_recalculation_service import recalculate_row_issues
from .row_status_policy import derive_row_status as derive_policy_status
from .row_status_service import derive_row_status


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


def project_validation_record(
    record: dict[str, Any],
    import_id: str,
    database_url: str | None = None,
    recalculation=recalculate_row_issues,
    use_database: bool = True,
) -> dict[str, Any]:
    """Apply the single read-only issue/status projection to one page row."""
    raw_import_row_id = record.get("raw_import_row_id")
    if raw_import_row_id and use_database:
        issues = recalculation(
            import_id, raw_import_row_id, database_url=database_url
        )
        record["issues"] = present_validation_issues(issues)
        record["row_status"] = derive_row_status(
            import_id, raw_import_row_id, database_url=database_url, issues=issues
        )
        return record

    if record.get("issue_type") and not record.get("issues"):
        record["issues"] = [{
            "field": record.get("issue_field", "unknown"),
            "reason": record.get("issue_description", "Issue detected"),
            "severity": "error" if record.get("issue_type") == "missing-required" else "warning",
        }]
    elif not record.get("issue_type"):
        fixture_values = {
            "date": record.get("date"),
            "amount": record.get("amount"),
            "email": record.get("email"),
            "phone": record.get("phone"),
            "address": record.get("address"),
        }
        record["issues"] = present_validation_issues(
            evaluate_effective_values(fixture_values)
        )
    else:
        record["issues"] = []
    record["row_status"] = derive_policy_status(record.get("issues", []))
    return record
