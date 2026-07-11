"""
Autosave Service for v1.1 Review Screen Refinement

Handles append-only ReviewDecision creation for row-level corrections.
Each autosave creates a new ReviewDecision record (never updates).
Audit trail preserves full correction history.
"""

from typing import Optional, Mapping, Any
from datetime import datetime, timezone

from .write_repository_contracts import ValidationDecisionResult
from .repository_provider import get_import_repository


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
        decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=None,  # Not applicable for row-level autosave
            raw_import_row_id=raw_import_row_id,
            decision='accept_issue',
            reviewed_values=corrected_values,
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
    from .database_models import (
        RawImportRow, ReviewDecision, get_session, create_db_engine
    )
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os

    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get raw row
        raw_row = session.query(RawImportRow).filter_by(
            id=raw_import_row_id
        ).first()
        if not raw_row:
            raise ValueError(f"Raw import row {raw_import_row_id} not found")

        # Start with raw values
        effective_values = dict(raw_row.raw_csv_data) if raw_row.raw_csv_data else {}

        # Accumulate corrections from ALL ReviewDecisions for this row
        # Each autosave creates a new decision with reviewed_values for one or more fields
        # We need to merge them all in chronological order (later decisions override earlier)
        decisions = session.query(ReviewDecision).filter_by(
            batch_id=batch_id,
            raw_import_row_id=raw_import_row_id
        ).order_by(
            ReviewDecision.created_at.asc(),  # Earliest first
            ReviewDecision.id.asc()
        ).all()

        # Merge corrections: iterate in chronological order, later overrides earlier
        for decision in decisions:
            if decision.reviewed_values:
                effective_values.update(decision.reviewed_values)

        return effective_values

    finally:
        session.close()


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
    from .phone_validation_service import is_valid_phone
    from .date_validation_service import validate_review_date
    import re

    errors = {}

    for field, value in corrected_values.items():
        # Amount must be validated even if 0 (falsy) or empty string
        if field == 'amount':
            amount_str = '' if value is None else str(value).strip()
            # Empty amount is invalid
            if not amount_str:
                errors['amount'] = 'Amount is required'
            else:
                try:
                    normalized_amount = amount_str.replace('$', '').replace(',', '').strip()
                    if normalized_amount.startswith('-'):
                        errors['amount'] = 'Amount must be greater than 0'
                        continue

                    if '.' in normalized_amount:
                        whole_part, decimal_part = normalized_amount.split('.', 1)
                        if not whole_part.isdigit() or not decimal_part.isdigit():
                            errors['amount'] = 'Invalid amount format'
                            continue
                        if len(decimal_part) > 2:
                            errors['amount'] = 'Amount must have at most 2 decimal places'
                            continue
                    elif not normalized_amount.isdigit():
                        errors['amount'] = 'Invalid amount format'
                        continue

                    amount_val = float(normalized_amount)
                    if amount_val <= 0:
                        errors['amount'] = 'Amount must be greater than 0'
                except ValueError:
                    errors['amount'] = 'Invalid amount format'
            continue

        if field == 'date':
            date_result = validate_review_date(value, allow_blank=True)
            if not date_result.valid:
                errors['date'] = date_result.blocking_error or 'Invalid date format'
            continue

        # For other fields, skip if empty/falsy (might be clearing a field)
        if not value or not isinstance(value, str):
            continue

        value_str = value.strip()
        if not value_str:
            continue

        # Validate email field
        if field == 'email':
            # Canonical format: something@something.something
            email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
            if not re.match(email_pattern, value_str.lower()):
                errors['email'] = 'Invalid email format (require: localpart@domain.tld)'

        # Validate phone field
        elif field == 'phone':
            # Use phonenumbers library for validation
            if not is_valid_phone(value_str, 'US'):
                errors['phone'] = 'Invalid phone format (require: 10+ digit US number)'

    if errors:
        return False, errors
    else:
        return True, None


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
