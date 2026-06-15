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

    # Use issue_recalculation_service to get current issues
    from .issue_recalculation_service import recalculate_row_issues

    try:
        # Get current issues using issue_recalculation_service
        current_issues = recalculate_row_issues(batch_id, raw_import_row_id, database_url)

        if not current_issues:
            # No unresolved issues
            return "No issues"

        # Check for blocking issues
        has_blocking = False
        has_warning = False

        for issue in current_issues:
            severity = issue.get('severity', 'warning')
            if severity == 'error':
                has_blocking = True
            else:
                has_warning = True

        # Check approval override state FIRST
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()

            if batch and batch.approval_status == 'approved_with_overrides':
                if batch.override_details:
                    overrides = batch.override_details.get('overrides', [])
                    # Check if this row is in the overrides
                    for override in overrides:
                        if override.get('raw_import_row_id') == raw_import_row_id:
                            # Row was explicitly approved with overrides
                            return "Overridden"
        finally:
            session.close()

        # Determine status based on issue types (if not overridden)
        if has_blocking:
            return "Blocking"
        elif has_warning:
            return "Warning"
        else:
            return "No issues"

    except Exception as e:
        # If issue recalculation fails, default to "No issues"
        return "No issues"


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
