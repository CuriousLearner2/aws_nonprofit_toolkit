"""
Row-Level Review Status Decision Service

Handles reviewer decisions on row status (Accept, Follow-up, Defer, Reject, Clear).
These are stored as ReviewDecision records with decision type tracking the reviewer's choice.

Decision types:
- 'accept_as_is': Row acceptable without changes
- 'needs_follow_up': Requires follow-up, notes mandatory
- 'defer': Defer review to later, optional notes
- 'reject_row': Reject this row entirely
- 'clear_decision': Remove reviewer decision, return to system-derived status
"""

from typing import Optional, Mapping, Any
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import ReviewDecision, ImportBatch, RawImportRow


def record_row_decision(
    batch_id: str,
    raw_import_row_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    database_url: Optional[str] = None,
) -> dict:
    """
    Record a reviewer's row-level status decision.

    Creates a new ReviewDecision with reviewed_status and optional notes.
    Each decision is append-only; clearing a decision creates a new 'clear_decision' record.

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        decision: One of: 'accept_as_is', 'needs_follow_up', 'defer', 'reject_row', 'clear_decision'
        notes: Optional reviewer notes (required for 'needs_follow_up')
        reviewer: Optional reviewer identifier
        database_url: Optional database connection URL

    Returns:
        Dict with decision_id, decision type, timestamp, and validation status

    Raises:
        ValueError: If batch/row not found, invalid decision type, or notes missing for follow-up
    """
    import os

    # Determine database URL
    if not database_url:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError("Row decision requires database configuration")

    # Validate decision type
    valid_decisions = {
        'accept_as_is',
        'needs_follow_up',
        'defer',
        'reject_row',
        'clear_decision'
    }
    if decision not in valid_decisions:
        raise ValueError(
            f"Invalid decision '{decision}'. Must be one of: {', '.join(valid_decisions)}"
        )

    # Validate notes for follow-up
    if decision == 'needs_follow_up' and not (notes and notes.strip()):
        raise ValueError("Notes are required when 'Needs follow-up' is selected")

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Verify batch exists
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        # Verify row exists
        row = session.query(RawImportRow).filter_by(id=raw_import_row_id).first()
        if not row:
            raise ValueError(f"Raw import row {raw_import_row_id} not found")

        if row.batch_id != batch_id:
            raise ValueError(
                f"Raw import row {raw_import_row_id} does not belong to batch '{batch_id}'"
            )

        # Build reviewed_values with decision and notes
        reviewed_values = {
            'reviewed_status': decision,
        }
        if notes:
            reviewed_values['notes'] = notes.strip()

        # Create new ReviewDecision record
        # Use decision as the decision type for row-level status decisions
        row_decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=None,  # Row-level decision, not item-specific
            raw_import_row_id=raw_import_row_id,
            decision=f'row_status:{decision}',  # Prefix to distinguish from item decisions
            reviewed_values=reviewed_values,
            reviewer=reviewer
        )
        session.add(row_decision)
        session.commit()

        return {
            'decision_id': row_decision.id,
            'decision': decision,
            'timestamp': row_decision.created_at.isoformat(),
            'success': True,
            'message': f'Row decision recorded: {decision}',
        }

    finally:
        session.close()


def get_row_decision(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
) -> Optional[dict]:
    """
    Get the latest row-level reviewer decision for a row.

    Returns the most recent decision (by created_at, then id).
    If the latest decision is 'clear_decision', returns None (no active decision).

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        database_url: Optional database connection URL

    Returns:
        Dict with decision, notes, timestamp, or None if no active decision
    """
    import os

    if not database_url:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError("Row decision query requires database configuration")

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get latest decision for this row
        latest = (
            session.query(ReviewDecision)
            .filter_by(
                batch_id=batch_id,
                raw_import_row_id=raw_import_row_id
            )
            .filter(ReviewDecision.decision.like('row_status:%'))
            .order_by(ReviewDecision.created_at.desc(), ReviewDecision.id.desc())
            .first()
        )

        if not latest:
            return None

        # Extract decision type from 'row_status:decision_type' format
        decision_type = latest.decision.replace('row_status:', '', 1)

        # If cleared, return None (system status applies)
        if decision_type == 'clear_decision':
            return None

        # Extract notes from reviewed_values
        reviewed_values = latest.reviewed_values or {}
        notes = reviewed_values.get('notes')

        return {
            'decision': decision_type,
            'notes': notes,
            'timestamp': latest.created_at.isoformat(),
            'reviewer': latest.reviewer,
        }

    finally:
        session.close()


def get_rows_with_follow_up(
    batch_id: str,
    database_url: Optional[str] = None,
) -> list:
    """
    Get all rows in batch with active 'needs_follow_up' decision.

    Returns list of raw_import_row_id with current follow-up decisions (not cleared).
    Checks latest decision for each row to exclude cleared decisions.
    """
    import os

    if not database_url:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError("Row decision query requires database configuration")

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get all rows with decisions in this batch
        all_decisions = (
            session.query(ReviewDecision)
            .filter_by(batch_id=batch_id)
            .filter(ReviewDecision.decision.like('row_status:%'))
            .order_by(
                ReviewDecision.raw_import_row_id,
                ReviewDecision.created_at.desc(),
                ReviewDecision.id.desc()
            )
            .all()
        )

        # Build dict of latest decision per row
        latest_per_row = {}
        for decision in all_decisions:
            if decision.raw_import_row_id not in latest_per_row:
                latest_per_row[decision.raw_import_row_id] = decision

        # Return only rows with active follow-up (not cleared)
        follow_up_rows = []
        for row_id, decision in latest_per_row.items():
            decision_type = decision.decision.replace('row_status:', '', 1)
            if decision_type == 'needs_follow_up':
                follow_up_rows.append(row_id)

        return follow_up_rows

    finally:
        session.close()


def get_rows_with_defer(
    batch_id: str,
    database_url: Optional[str] = None,
) -> list:
    """
    Get all rows in batch with active 'defer' decision.

    Returns list of raw_import_row_id with current defer decisions (not cleared).
    Checks latest decision for each row to exclude cleared decisions.
    """
    import os

    if not database_url:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError("Row decision query requires database configuration")

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get all rows with decisions in this batch
        all_decisions = (
            session.query(ReviewDecision)
            .filter_by(batch_id=batch_id)
            .filter(ReviewDecision.decision.like('row_status:%'))
            .order_by(
                ReviewDecision.raw_import_row_id,
                ReviewDecision.created_at.desc(),
                ReviewDecision.id.desc()
            )
            .all()
        )

        # Build dict of latest decision per row
        latest_per_row = {}
        for decision in all_decisions:
            if decision.raw_import_row_id not in latest_per_row:
                latest_per_row[decision.raw_import_row_id] = decision

        # Return only rows with active defer (not cleared)
        defer_rows = []
        for row_id, decision in latest_per_row.items():
            decision_type = decision.decision.replace('row_status:', '', 1)
            if decision_type == 'defer':
                defer_rows.append(row_id)

        return defer_rows

    finally:
        session.close()
