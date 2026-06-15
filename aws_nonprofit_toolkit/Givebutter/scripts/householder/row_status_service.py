"""
Row Status Derivation Service for v1.1 Review Screen Refinement

Derives read-only Row Status column from:
- ReviewItem status (issues exist?)
- ReviewDecision state (are issues resolved?)
- Batch approval override state (was file approved with overrides?)
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import (
    ImportBatch, RawImportRow, ReviewItem, ReviewDecision, ReviewItemSubject
)
import os


def derive_row_status(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
) -> str:
    """
    Derive Row Status from review data and approval state.

    Status values:
    - "No issues" = no unresolved blocking/warning issues
    - "Warning" = only non-blocking warning issues remain unresolved
    - "Blocking" = one or more blocking issues remain unresolved
    - "Overridden" = batch was approved with overrides for this row

    Priority: Blocking > Overridden > Warning > No issues

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        database_url: Database connection URL (optional)

    Returns:
        Status string: "No issues" | "Warning" | "Blocking" | "Overridden"

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

        # Get all validation issues for this row
        issues = session.query(ReviewItem).join(
            ReviewItemSubject,
            ReviewItem.id == ReviewItemSubject.review_item_id
        ).filter(
            ReviewItem.batch_id == batch_id,
            ReviewItem.item_type == 'validation',
            ReviewItemSubject.subject_type == 'import_raw_row',
            ReviewItemSubject.subject_id == raw_import_row_id
        ).all()

        if not issues:
            # No issues at all
            return "No issues"

        # Check for blocking issues
        has_blocking = False
        has_warning = False

        for issue in issues:
            # Get latest decision for this issue (by created_at DESC, id DESC)
            latest_decision = session.query(ReviewDecision).filter_by(
                review_item_id=issue.id
            ).order_by(
                ReviewDecision.created_at.desc(),
                ReviewDecision.id.desc()
            ).first()

            # If no decision or decision is 'defer', issue is unresolved
            if not latest_decision or latest_decision.decision == 'defer':
                # Check if blocking or warning
                # For now, assume payload_json contains severity info or we check issue type
                severity = issue.payload_json.get('severity', 'warning') if issue.payload_json else 'warning'
                if severity == 'error':
                    has_blocking = True
                else:
                    has_warning = True

        # Check approval override state FIRST
        # If this row is in override_details, it was explicitly approved with remaining issues
        if batch.approval_status == 'approved_with_overrides':
            if batch.override_details:
                overrides = batch.override_details.get('overrides', [])
                # Check if this row is in the overrides
                for override in overrides:
                    if override.get('raw_import_row_id') == raw_import_row_id:
                        # Row was explicitly approved with overrides
                        return "Overridden"

        # Determine status based on issue types (if not overridden)
        if has_blocking:
            return "Blocking"
        elif has_warning:
            return "Warning"
        else:
            return "No issues"

    finally:
        session.close()


def is_row_overridden(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
) -> bool:
    """
    Check if a row was approved with overrides.

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        database_url: Database connection URL (optional)

    Returns:
        True if row is in override_details, False otherwise
    """
    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch or batch.approval_status != 'approved_with_overrides':
            return False

        if not batch.override_details:
            return False

        overrides = batch.override_details.get('overrides', [])
        for override in overrides:
            if override.get('raw_import_row_id') == raw_import_row_id:
                return True

        return False

    finally:
        session.close()
