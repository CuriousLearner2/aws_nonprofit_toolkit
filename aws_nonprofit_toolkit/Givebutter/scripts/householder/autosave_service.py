"""
Autosave Service for v1.1 Review Screen Refinement

Handles append-only ReviewDecision creation for row-level corrections.
Each autosave creates a new ReviewDecision record (never updates).
Audit trail preserves full correction history.
"""

from typing import Optional, Mapping, Any
from datetime import datetime

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
            timestamp=datetime.utcnow()
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
    import re

    errors = {}

    for field, value in corrected_values.items():
        if not value or not isinstance(value, str):
            # Empty values are allowed (might be clearing a field)
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

        # Add more field validations as needed

    if errors:
        return False, errors
    else:
        return True, None
