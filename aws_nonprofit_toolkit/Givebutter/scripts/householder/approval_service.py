"""
Approval Service for v1.1 Review Screen Refinement

Handles batch approval after all blocking rows have been resolved.
Creates AuditLogRecord for approval action.
Ensures raw data and review items remain unchanged.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import (
    ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject, AuditLogRecord
)
import os


def approve_batch(
    batch_id: str,
    approval_status: str,
    rows_with_overrides: Optional[list] = None,
    reviewer: Optional[str] = None,
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Approve a batch only after all blocking rows have been resolved.

    Workflow:
    1. Validate batch exists and is not already approved
    2. Validate approval_status is 'approved'
    3. Reject any file-level override payload
    4. Update ImportBatch.approval_status
    5. Create AuditLogRecord for approval action
    6. Return approval result with audit log id

    Does NOT mutate RawImportRow or ReviewItem.

    Args:
        batch_id: Import batch ID
        approval_status: 'approved'
        rows_with_overrides: legacy input, rejected when supplied
        reviewer: Optional reviewer identifier
        database_url: Database connection URL (optional)

    Returns:
        Dict with approval result:
        {
            'success': bool,
            'approval_status': str,
            'batch_id': str,
            'audit_log_id': int,
            'timestamp': datetime
        }

    Raises:
        ValueError: If batch not found, invalid approval_status, or unresolved issues remain
    """
    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Verify batch exists
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        # Validate approval_status
        if approval_status != 'approved':
            raise ValueError('File-level approval overrides are not supported; resolve rows individually')
        if rows_with_overrides:
            raise ValueError('File-level approval overrides are not supported; resolve rows individually')

        # If already approved, don't re-approve
        if batch.approval_status == 'approved':
            raise ValueError(f"Batch '{batch_id}' is already {batch.approval_status}")

        remaining_issues = check_batch_remaining_issues(
            batch_id=batch_id,
            database_url=database_url,
        )
        if remaining_issues:
            raise ValueError('Batch has unresolved issues; resolve each row before approving')

        # Update batch approval status
        batch.approval_status = approval_status
        batch.updated_at = datetime.now(timezone.utc)

        session.add(batch)

        # Create AuditLogRecord for approval
        audit_record = AuditLogRecord(
            batch_id=batch_id,
            action_type='batch_approved',
            action_timestamp=datetime.now(timezone.utc),
            actor=reviewer,
            details={
                'approval_status': approval_status,
            }
        )
        session.add(audit_record)

        # Commit transaction
        session.commit()

        return {
            'success': True,
            'approval_status': approval_status,
            'batch_id': batch_id,
            'audit_log_id': audit_record.id,
            'timestamp': datetime.now(timezone.utc)
        }

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_batch_approval_status(
    batch_id: str,
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get current approval status for a batch.

    Args:
        batch_id: Import batch ID
        database_url: Database connection URL (optional)

    Returns:
        Dict with approval status:
        {
            'batch_id': str,
            'approval_status': str or None,
            'approval_status': str or None
        }

    Raises:
        ValueError: If batch not found
    """
    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        return {
            'batch_id': batch_id,
            'approval_status': batch.approval_status,
        }

    finally:
        session.close()


def check_batch_remaining_issues(
    batch_id: str,
    database_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Check for remaining unresolved issues in batch.

    Returns rows whose effective gating still blocks finalization.

    Args:
        batch_id: Import batch ID
        database_url: Database connection URL (optional)

    Returns:
        List of rows with remaining issues:
        [
            {
                'raw_import_row_id': int,
                'row_index': int,
                'issues': [{...}, ...],
                'row_status': str,
                'decision_warning': str
            }
        ]

    Raises:
        ValueError: If batch not found
    """
    from .row_status_service import derive_row_status
    from .issue_recalculation_service import recalculate_row_issues
    from .row_decision_service import (
        get_row_decision_state,
        project_effective_disposition,
    )
    from .approval_remaining_issues_policy import project_row_gating

    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        # Get all raw rows in batch
        rows = session.query(RawImportRow).filter_by(batch_id=batch_id).all()

        remaining_issues_by_row = []
        for row in rows:
            issues = recalculate_row_issues(
                batch_id=batch_id,
                raw_import_row_id=row.id,
                database_url=database_url
            )
            row_status = derive_row_status(
                batch_id=batch_id,
                raw_import_row_id=row.id,
                database_url=database_url
            )

            decision_state = get_row_decision_state(
                batch_id=batch_id,
                raw_import_row_id=row.id,
                database_url=database_url,
            )
            human_disposition = decision_state.get('decision') if decision_state.get('has_decision') else None
            effective_disposition = project_effective_disposition(
                row_status=row_status,
                human_disposition=human_disposition,
            )
            projection = project_row_gating(
                raw_import_row_id=row.id,
                row_index=row.row_index,
                row_status=row_status,
                has_unresolved_validation=bool(issues),
                human_disposition=effective_disposition,
            )
            if projection.export_blocked:
                remaining_issues_by_row.append({
                    'raw_import_row_id': row.id,
                    'row_index': row.row_index,
                    'issues': issues,
                    'row_status': row_status,
                    'decision_warning': 'disposition_required',
                })
                continue
        return remaining_issues_by_row

    finally:
        session.close()
