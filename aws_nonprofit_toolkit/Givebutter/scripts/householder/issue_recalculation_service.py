"""
Issue Recalculation Service for v1.1 Review Screen Refinement

Recalculates validation issues for a row using effective values (raw + corrections).
Does not mutate raw source data or ReviewItem.payload_json.
Returns updated list of issues for display in Issues column.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import (
    ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject
)
from .autosave_service import get_effective_values
import os


def recalculate_row_issues(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Recalculate validation issues for a row using effective values.

    Workflow:
    1. Get effective values (raw + latest corrections)
    2. Run validation rules on effective values
    3. Compare with existing ReviewItems
    4. Return updated issue list (may be empty if corrections resolved issues)

    Does NOT mutate RawImportRow, ReviewItem, or ReviewDecision.

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        database_url: Database connection URL (optional)

    Returns:
        List of issues: [{"issue_id": int, "issue_type": str, "description": str, "severity": str}, ...]

    Raises:
        ValueError: If batch or row not found
    """
    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Verify batch and row exist
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        raw_row = session.query(RawImportRow).filter_by(id=raw_import_row_id).first()
        if not raw_row:
            raise ValueError(f"Raw import row {raw_import_row_id} not found")

        # Get effective values (raw + corrections)
        effective_values = get_effective_values(batch_id, raw_import_row_id, database_url)

        # Get raw data for comparison
        raw_data = raw_row.raw_csv_data or {}

        # Get all existing validation issues for this row
        # Check both import_raw_row (Phase 1B raw data) and import_contact_snapshot (demo data)
        existing_issues = session.query(ReviewItem).join(
            ReviewItemSubject,
            ReviewItem.id == ReviewItemSubject.review_item_id
        ).filter(
            ReviewItem.batch_id == batch_id,
            ReviewItem.item_type == 'validation',
            ReviewItemSubject.subject_type.in_(['import_raw_row', 'import_contact_snapshot']),
            ReviewItemSubject.subject_id == raw_import_row_id
        ).all()

        # For each existing issue, check if it's still valid given the effective values
        current_issues = []

        for issue in existing_issues:
            payload = issue.payload_json or {}
            issue_field = payload.get('field')  # e.g., 'email'
            issue_reason = payload.get('reason')  # e.g., 'possible_typo'
            severity = payload.get('severity', 'warning')

            # Get the corrected value for this field (if any)
            effective_value = effective_values.get(issue_field)
            raw_value = raw_data.get(issue_field)

            # Check if issue is still valid with the effective value
            # Logic: if a correction was made to the field, we assume the issue is resolved

            if is_issue_resolved(issue_field, effective_value, issue_reason, raw_value):
                # Issue is resolved, don't include it
                continue
            else:
                # Issue remains unresolved
                current_issues.append({
                    'issue_id': issue.id,
                    'issue_type': issue.item_type,
                    'field': issue_field,
                    'description': payload.get('description', f"Issue with {issue_field}"),
                    'severity': severity,
                    'overridden': _is_issue_overridden(batch, raw_import_row_id, issue_field)
                })

        return current_issues

    finally:
        session.close()


def is_issue_resolved(
    field: str,
    effective_value: Any,
    issue_reason: str,
    raw_value: Any = None,
) -> bool:
    """
    Check if an issue is resolved given the effective field value.

    Resolution logic:
    - Missing: resolved if value is now non-empty
    - Typo/format: resolved if value matches raw (no correction) OR appears to have valid format

    Args:
        field: Field name (e.g., 'email', 'phone')
        effective_value: Current effective value for the field
        issue_reason: Issue type (e.g., 'missing', 'typo', 'format')
        raw_value: Original raw value (optional, for comparison)

    Returns:
        True if issue appears resolved, False otherwise
    """
    if not field:
        return False

    # Convert to string for validation
    effective_str = str(effective_value).strip() if effective_value else ''

    if issue_reason == 'missing':
        # Issue resolved if now non-empty
        return bool(effective_str)
    elif issue_reason in ('typo', 'format', 'possible_typo'):
        # For typo/format issues: only resolved if value is actually corrected to valid format
        # Not resolved if just different from raw but still invalid
        if not effective_str:
            return False

        # Basic validation for common issues
        if field == 'email':
            # Email issue resolved only if it contains valid domain patterns
            # (not common typos like gmial, gmal, etc.)
            # Use regex to avoid false positives (e.g., 'gmai' in 'gmail')
            import re
            invalid_typos = [
                r'gmial(?:\.com)?',  # gmail typo: gmial
                r'gmal(?:\.com)?',   # gmail typo: gmal (missing i)
                r'yahooo(?:\.com)?', # yahoo typo: yahooo
                r'hotmial(?:\.com)?',# hotmail typo: hotmial
                r'\bgmai\b',         # gmai standalone (not part of gmail)
            ]
            has_invalid = any(re.search(pattern, effective_str.lower()) for pattern in invalid_typos)
            return not has_invalid and '@' in effective_str
        elif field == 'phone':
            # Phone issue resolved if it has valid format (digits and common separators)
            import re
            # Valid patterns: 555-1234, (555) 555-1234, 5551234, etc.
            valid_phone = bool(re.search(r'\d{3}[-.]?\d{3}[-.]?\d{4}|^\d{10}$', effective_str))
            return valid_phone
        else:
            # For other fields, check if effective differs meaningfully from raw
            if raw_value is not None:
                raw_str = str(raw_value).strip() if raw_value else ''
                # Resolved if effective differs from raw
                return effective_str != raw_str
            return False
    else:
        return False  # Unknown reason, don't auto-resolve


def _is_issue_overridden(
    batch,
    raw_import_row_id: int,
    field: str,
) -> bool:
    """
    Check if an issue was overridden during batch approval.

    Args:
        batch: ImportBatch object
        raw_import_row_id: RawImportRow.id
        field: Field name

    Returns:
        True if batch was approved with overrides for this field on this row
    """
    if batch.approval_status != 'approved_with_overrides':
        return False

    if not batch.override_details:
        return False

    overrides = batch.override_details.get('overrides', [])
    for override in overrides:
        if override.get('raw_import_row_id') == raw_import_row_id:
            # Found override for this row
            # If field matches, mark as overridden
            override_field = override.get('field')
            if override_field == field or not override_field:
                return True

    return False
