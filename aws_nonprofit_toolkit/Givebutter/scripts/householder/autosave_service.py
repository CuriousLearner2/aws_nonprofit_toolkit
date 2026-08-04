"""
Autosave Service for v1.1 Review Screen Refinement

Handles append-only ReviewDecision creation for row-level corrections.
Each autosave creates a new ReviewDecision record (never updates).
Audit trail preserves full correction history.
"""

from dataclasses import dataclass
from typing import Optional, Mapping, Any
from datetime import datetime, timezone

from .write_repository_contracts import ValidationDecisionResult
from .repository_provider import get_import_repository
from .editable_field_validation import validate_editable_field_values as _validate_editable_field_values
from .effective_value_resolution import get_effective_values as _get_effective_values


@dataclass(frozen=True)
class AutosaveResult:
    """Internal result shared by fixture and database autosave modes."""

    status_code: int
    payload: dict


def run_autosave(batch_id, raw_import_row_id, corrected_values, reviewer=None,
                 repository_mode="", database_url=None) -> AutosaveResult:
    """Own autosave validation, persistence, reload, issues, and row status."""
    if not database_url and repository_mode != "database":
        payload = build_fixture_autosave_response(
            batch_id, raw_import_row_id, corrected_values
        )
        return AutosaveResult(payload.pop("status_code", 200), payload)

    try:
        is_valid, errors = validate_corrected_values(corrected_values)
        if not is_valid:
            existing = _recalculate_and_status(batch_id, raw_import_row_id, database_url)[0]
            validation_issues = [
                {"field": field, "description": message, "severity": "error",
                 "is_validation_error": True}
                for field, message in errors.items()
            ]
            issues = validation_issues + existing
            return AutosaveResult(400, {
                "success": False, "error": "Validation failed",
                "validation_errors": errors,
                "message": "Corrections not saved - please fix validation errors",
                "row_status": _derive_database_row_status(
                    batch_id, raw_import_row_id, issues, database_url
                ),
                "issues": _format_issues(issues),
            })

        result = autosave_row_corrections(
            batch_id, raw_import_row_id, corrected_values,
            reviewer=reviewer, database_url=database_url
        )
        effective_values = get_effective_values(
            batch_id, raw_import_row_id, database_url
        )
        issues = _recalculate_and_status(
            batch_id, raw_import_row_id, database_url, corrected_values
        )[0]
        return AutosaveResult(200, {
            "success": True, "decision_id": result.decision_id,
            "effective_values": effective_values,
            "row_status": _derive_database_row_status(
                batch_id, raw_import_row_id, issues, database_url
            ),
            "issues": _format_issues(issues),
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "message": "Autosave completed successfully",
        })
    except ValueError as exc:
        return _error_result(400, str(exc), batch_id, raw_import_row_id, database_url)
    except Exception as exc:
        return _error_result(500, "Autosave failed", batch_id, raw_import_row_id, database_url, exc)


def _recalculate_and_status(batch_id, raw_import_row_id, database_url, proposed_values=None):
    from .issue_recalculation_service import recalculate_row_issues
    issues = recalculate_row_issues(
        batch_id=batch_id, raw_import_row_id=raw_import_row_id,
        proposed_values=proposed_values, database_url=database_url
    )
    return issues, _derive_database_row_status(batch_id, raw_import_row_id, issues, database_url)


def _derive_database_row_status(batch_id, raw_import_row_id, issues, database_url):
    from .row_status_service import derive_row_status
    return derive_row_status(
        batch_id=batch_id, raw_import_row_id=raw_import_row_id,
        issues=issues, database_url=database_url
    )


def _error_result(status_code, error, batch_id, raw_import_row_id, database_url, cause=None):
    try:
        issues, row_status = _recalculate_and_status(batch_id, raw_import_row_id, database_url)
    except Exception:
        issues, row_status = [], "Blocking"
    if row_status == "Blocking" and not issues:
        issues = [{"field": "raw_import_row_id", "description":
                   f"Autosave failed: {cause or error}", "severity": "error"}]
    return AutosaveResult(status_code, {
        "error": error, "issues": _format_issues(issues), "row_status": row_status
    })


def _format_issues(issues):
    return [{
        "field": issue.get("field", "unknown"),
        "reason": issue.get("description", issue.get("reason", "Issue detected")),
        "severity": issue.get("severity", "warning"),
    } for issue in issues]


def autosave_row_corrections(
    batch_id: str,
    raw_import_row_id: int,
    corrected_values: Mapping[str, Any],
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
    database_url: Optional[str] = None,
) -> ValidationDecisionResult:
    """
    Autosave corrected/export values for a row.

    Creates a new ReviewDecision with decision='accept_issue' and reviewed_values
    containing the corrected field values. Never updates existing decisions (append-only).

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        corrected_values: Dict of corrected field values (e.g., {'email': 'corrected@example.com'})
        reviewer: Optional reviewer identifier
        config: Optional configuration mapping for database selection
        database_url: Optional database connection URL (overrides config and env)

    Returns:
        ValidationDecisionResult with decision_id, effective_status, etc.

    Raises:
        ValueError: If batch or row not found
        DatabaseError: If write transaction fails
    """
    from .database_models import ReviewDecision, get_session, create_db_engine
    from .amount_validation_service import validate_review_amount
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os

    # Determine database URL (prioritize: database_url > config > env)
    if not database_url:
        if config:
            database_url = config.get('GIVEBUTTER_DATABASE_URL')
        else:
            database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError(
            "Autosave requires database configuration. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or pass config."
        )

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Validate batch exists
        from .database_models import ImportBatch, RawImportRow
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        # Validate row exists
        row = session.query(RawImportRow).filter_by(id=raw_import_row_id).first()
        if not row:
            raise ValueError(f"Raw import row {raw_import_row_id} not found")

        if row.batch_id != batch_id:
            raise ValueError(
                f"Raw import row {raw_import_row_id} does not belong to batch '{batch_id}'"
            )

        # Create autosave ReviewDecision (append-only)
        # Row-level autosave doesn't link to a specific ReviewItem
        # Instead, creates a row-level decision with reviewed_values
        reviewed_values = dict(corrected_values)
        amount_value = reviewed_values.get('amount')
        if amount_value is not None:
            from decimal import Decimal
            amount_result = validate_review_amount(amount_value, allow_blank=False)
            if amount_result.valid and amount_result.normalized_value:
                reviewed_values['amount'] = f"{Decimal(amount_result.normalized_value):.2f}"

        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=None,  # Not applicable for row-level autosave
            raw_import_row_id=raw_import_row_id,
            decision='accept_issue',
            reviewed_values=reviewed_values,
            reviewer=reviewer
        )
        session.add(decision)
        session.commit()

        return ValidationDecisionResult(
            decision_id=decision.id,
            review_item_id=0,  # Not applicable for row-level autosave
            decision='accept_issue',
            effective_status='accepted',
            audit_log_id=0,  # Placeholder
            timestamp=datetime.now(timezone.utc)
        )

    finally:
        session.close()


def get_effective_values(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
) -> dict:
    """
    Derive effective row values from raw data + latest corrections.

    Workflow:
    1. Get RawImportRow.raw_csv_data
    2. Find latest ReviewDecision.reviewed_values (by created_at DESC, id DESC)
    3. Merge: corrected values override raw values
    4. Return effective_values dict

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        database_url: Database connection URL (optional)

    Returns:
        Dict of effective values: {field: corrected_or_raw_value, ...}

    Raises:
        ValueError: If batch or row not found
    """
    return _get_effective_values(batch_id, raw_import_row_id, database_url)


def validate_corrected_values(
    corrected_values: Mapping[str, Any],
) -> tuple[bool, Optional[dict]]:
    """
    Validate corrected field values before autosave.

    Ensures that corrections are valid before saving to ReviewDecision.
    Invalid values are rejected with specific error messages.

    Args:
        corrected_values: Dict of field values to validate (e.g., {'email': 'user@example.com'})

    Returns:
        Tuple of (is_valid: bool, errors: dict or None)
        - If valid: (True, None)
        - If invalid: (False, {'field': 'error message', ...})
    """
    return _validate_editable_field_values(corrected_values)


def build_fixture_autosave_response(
    batch_id: str,
    raw_import_row_id: int,
    corrected_values: Mapping[str, Any],
    config: Optional[Mapping[str, Any]] = None,
) -> dict:
    """
    Build a fixture-mode autosave response without requiring a database.

    Fixture mode remains read-only, so autosave behaves as an in-memory
    validation and UI sync path: valid corrections return clean row state,
    invalid corrections return the same error shape as the database-backed
    autosave endpoint.
    """
    from .issue_recalculation_service import _validate_effective_values
    from .validation_service import get_validation_review
    from .amount_validation_service import validate_review_amount

    fixture_config = dict(config or {})
    fixture_config["HOUSEHOLDER_REPOSITORY"] = "fixture"

    review = get_validation_review(batch_id, config=fixture_config)
    record = next(
        (
            row for row in review.get("validation_issues", [])
            if row.get("raw_import_row_id") == raw_import_row_id
        ),
        None,
    )

    if not record:
        return {
            "status_code": 400,
            "success": False,
            "error": f"Raw import row {raw_import_row_id} not found",
            "issues": [
                {
                    "field": "raw_import_row_id",
                    "reason": f"Raw import row {raw_import_row_id} not found",
                    "severity": "error",
                }
            ],
            "row_status": "Blocking",
            "message": "Corrections not saved - please fix validation errors",
        }

    current_values = {
        field: record.get(field)
        for field in ("date", "name", "email", "phone", "amount", "address")
    }
    effective_values = dict(current_values)
    effective_values.update(corrected_values)
    amount_value = effective_values.get("amount")
    if amount_value is not None:
        from decimal import Decimal
        amount_result = validate_review_amount(amount_value, allow_blank=False)
        if amount_result.valid and amount_result.normalized_value:
            effective_values["amount"] = f"{Decimal(amount_result.normalized_value):.2f}"

    current_issues = list(record.get("issues") or [])
    is_valid, errors = validate_corrected_values(corrected_values)

    if not is_valid:
        validation_issues = [
            {
                "field": field,
                "reason": error_msg,
                "severity": "error",
            }
            for field, error_msg in errors.items()
        ]
        issues = _merge_issues(validation_issues + current_issues)
        row_status = _derive_row_status_from_issues(issues)

        return {
            "status_code": 400,
            "success": False,
            "error": "Validation failed",
            "validation_errors": errors,
            "message": "Corrections not saved - please fix validation errors",
            "row_status": row_status,
            "issues": issues,
        }

    resolved_fields = {
        field for field in corrected_values.keys()
        if field
    }
    remaining_current_issues = [
        issue for issue in current_issues
        if issue.get("field") not in resolved_fields
    ]
    new_validation_issues = _validate_effective_values(effective_values)
    issues = _merge_issues(remaining_current_issues + new_validation_issues)
    row_status = _derive_row_status_from_issues(issues)

    return {
        "status_code": 200,
        "success": True,
        "decision_id": 0,
        "effective_values": effective_values,
        "row_status": row_status,
        "issues": issues,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "message": "Autosave completed successfully",
    }


def _merge_issues(issues: list[dict]) -> list[dict]:
    """Deduplicate issues by field while preserving the last occurrence."""
    merged: dict[str, dict] = {}
    fallback_index = 0

    for issue in issues:
        field = issue.get("field")
        if field:
            merged[field] = issue
        else:
            merged[f"__issue_{fallback_index}"] = issue
            fallback_index += 1

    return list(merged.values())


def _derive_row_status_from_issues(issues: list[dict]) -> str:
    """Derive row status from issue severities without requiring a database."""
    has_error = any(issue.get("severity") == "error" for issue in issues)
    if has_error:
        return "Blocking"
    if issues:
        return "Warning"
    return "No issues"
