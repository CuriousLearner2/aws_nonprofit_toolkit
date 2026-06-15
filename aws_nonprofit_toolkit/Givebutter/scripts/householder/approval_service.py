"""
Approval Service for v1.1 Review Screen Refinement

Handles batch approval with and without overrides.
Persists approval_status and override_details to ImportBatch.
Creates AuditLogRecord for approval action.
Ensures raw data and review items remain unchanged.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import (
    ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject, AuditLogRecord
)
import os


def approve_batch(
    batch_id: str,
    approval_status: str,
    rows_with_overrides: Optional[List[Dict[str, Any]]] = None,
    reviewer: Optional[str] = None,
    database_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Approve a batch with or without overrides.

    Workflow:
    1. Validate batch exists and is not already approved
    2. Validate approval_status is 'approved' or 'approved_with_overrides'
    3. If approved_with_overrides, validate rows_with_overrides list
    4. Update ImportBatch.approval_status
    5. If approved_with_overrides, populate ImportBatch.override_details
    6. Create AuditLogRecord for approval action
    7. Return approval result with audit log id

    Does NOT mutate RawImportRow or ReviewItem.

    Args:
        batch_id: Import batch ID
        approval_status: 'approved' or 'approved_with_overrides'
        rows_with_overrides: List of rows with unresolved issues (for approved_with_overrides)
                           Each item: {'raw_import_row_id': int, 'row_index': int, 'issues': [{'field': str, 'reason': str}, ...]}
        reviewer: Optional reviewer identifier
        database_url: Database connection URL (optional)

    Returns:
        Dict with approval result:
        {
            'success': bool,
            'approval_status': str,
            'batch_id': str,
            'override_count': int,
            'audit_log_id': int,
            'timestamp': datetime
        }

    Raises:
        ValueError: If batch not found, invalid approval_status, or invalid override list
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
        if approval_status not in ('approved', 'approved_with_overrides'):
            raise ValueError(f"Invalid approval_status: {approval_status}")

        # If already approved, don't re-approve
        if batch.approval_status in ('approved', 'approved_with_overrides'):
            raise ValueError(f"Batch '{batch_id}' is already {batch.approval_status}")

        # Build override_details if needed
        override_details = None
        override_count = 0

        if approval_status == 'approved_with_overrides':
            if not rows_with_overrides:
                raise ValueError("approved_with_overrides requires rows_with_overrides list")

            # Validate each override entry
            overrides = []
            for row_override in rows_with_overrides:
                row_id = row_override.get('raw_import_row_id')
                row_index = row_override.get('row_index')
                issues = row_override.get('issues', [])

                # Verify row exists
                row = session.query(RawImportRow).filter_by(id=row_id).first()
                if not row:
                    raise ValueError(f"Raw import row {row_id} not found")

                # Build override detail entry
                override_entry = {
                    'raw_import_row_id': row_id,
                    'row_index': row_index,
                    'issues': issues  # List of {field, reason} dicts
                }
                overrides.append(override_entry)
                override_count += 1

            # Persist override_details
            override_details = {'overrides': overrides}

        # Update batch approval status
        batch.approval_status = approval_status
        if override_details:
            batch.override_details = override_details
        batch.updated_at = datetime.utcnow()

        session.add(batch)

        # Create AuditLogRecord for approval
        audit_record = AuditLogRecord(
            batch_id=batch_id,
            action_type='batch_approved',
            action_timestamp=datetime.utcnow(),
            actor=reviewer,
            details={
                'approval_status': approval_status,
                'override_count': override_count,
                'override_details': override_details
            }
        )
        session.add(audit_record)

        # Commit transaction
        session.commit()

        return {
            'success': True,
            'approval_status': approval_status,
            'batch_id': batch_id,
            'override_count': override_count,
            'audit_log_id': audit_record.id,
            'timestamp': datetime.utcnow()
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
            'override_count': int,
            'override_details': dict or None
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

        override_count = 0
        if batch.override_details:
            override_count = len(batch.override_details.get('overrides', []))

        return {
            'batch_id': batch_id,
            'approval_status': batch.approval_status,
            'override_count': override_count,
            'override_details': batch.override_details
        }

    finally:
        session.close()


def check_batch_remaining_issues(
    batch_id: str,
    database_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Check for remaining unresolved issues in batch.

    Returns list of rows with remaining issues for approval override modal.

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
                'row_status': str
            }
        ]

    Raises:
        ValueError: If batch not found
    """
    from .row_status_service import derive_row_status
    from .issue_recalculation_service import recalculate_row_issues

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

            if issues:  # Only return rows with remaining issues
                remaining_issues_by_row.append({
                    'raw_import_row_id': row.id,
                    'row_index': row.row_index,
                    'issues': issues,
                    'row_status': row_status
                })

        return remaining_issues_by_row

    finally:
        session.close()
