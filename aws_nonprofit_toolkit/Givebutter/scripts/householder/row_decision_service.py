"""
Row-Level Review Status Decision Service

Handles reviewer decisions on row status (Accept, Follow-up, Reject, Clear).
These are stored as ReviewDecision records with decision type tracking the reviewer's choice.

Decision types:
- 'accept_as_is': Row acceptable without changes
- 'needs_follow_up': Requires follow-up, notes mandatory
- 'reject_row': Reject this row entirely
- 'clear_decision': Remove reviewer decision, return to system-derived status
"""

from typing import Optional, Mapping, Any
from datetime import datetime, timezone
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import ReviewDecision, ImportBatch, RawImportRow, AuditLogRecord


_ROW_DECISION_LOCKS = {}
_ROW_DECISION_LOCKS_MUTEX = threading.Lock()

ROW_HUMAN_DISPOSITIONS = frozenset({
    'accept_as_is',
    'needs_follow_up',
    'reject_row',
})


def requires_reason_for_row_decision(
    decision: str,
    *,
    has_active_issues: bool,
) -> bool:
    """Return whether a human row disposition needs an auditable reason."""
    return decision in {'needs_follow_up', 'reject_row'} or (
        decision == 'accept_as_is' and has_active_issues
    )


def project_effective_disposition(
    *,
    row_status: str,
    human_disposition: Optional[str],
) -> Optional[str]:
    """Project the effective disposition without creating persistence state."""
    if human_disposition in ROW_HUMAN_DISPOSITIONS:
        return human_disposition
    return 'accept_as_is' if row_status == 'No issues' else None


def _normalize_row_decision_notes(notes: Optional[str]) -> Optional[str]:
    if notes is None:
        return None

    normalized = notes.strip()
    return normalized or None


def _normalize_interaction_sequence(interaction_sequence: Optional[Any]) -> Optional[int]:
    if interaction_sequence is None:
        return None

    try:
        normalized = int(interaction_sequence)
    except (TypeError, ValueError):
        raise ValueError("Row decision requires a valid interaction_sequence")

    if normalized < 1:
        raise ValueError("Row decision requires interaction_sequence >= 1")

    return normalized


def _row_decision_lock_key(batch_id: str, raw_import_row_id: int) -> str:
    return f"{batch_id}:{raw_import_row_id}"


def _get_row_decision_lock(batch_id: str, raw_import_row_id: int) -> threading.Lock:
    key = _row_decision_lock_key(batch_id, raw_import_row_id)
    with _ROW_DECISION_LOCKS_MUTEX:
        lock = _ROW_DECISION_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _ROW_DECISION_LOCKS[key] = lock
        return lock


def _get_latest_row_status_decision(session, batch_id: str, raw_import_row_id: int):
    return (
        session.query(ReviewDecision)
        .filter_by(
            batch_id=batch_id,
            raw_import_row_id=raw_import_row_id
        )
        .filter(ReviewDecision.decision.like('row_status:%'))
        .order_by(ReviewDecision.created_at.desc(), ReviewDecision.id.desc())
        .first()
    )


def invalidate_human_disposition_after_edit(session, batch_id: str, raw_import_row_id: int) -> bool:
    """Append a clear marker when a persisted edit supersedes a human decision."""
    latest = _get_latest_row_status_decision(session, batch_id, raw_import_row_id)
    decision_type, _, sequence = _extract_row_status_decision_state(latest)
    if decision_type not in ROW_HUMAN_DISPOSITIONS:
        return False

    reviewed_values = {'invalidation_reason': 'persisted_edit'}
    if sequence is not None:
        reviewed_values['interaction_sequence'] = sequence
    session.add(ReviewDecision(
        batch_id=batch_id,
        review_item_id=None,
        raw_import_row_id=raw_import_row_id,
        decision='row_status:clear_decision',
        reviewed_values=reviewed_values,
        reviewer=None,
    ))
    return True


def _extract_row_status_decision_state(review_decision):
    if not review_decision:
        return None, None, None

    decision_type = review_decision.decision.replace('row_status:', '', 1)
    reviewed_values = review_decision.reviewed_values or {}
    interaction_sequence = reviewed_values.get('interaction_sequence')

    if decision_type == 'clear_decision':
        return 'clear_decision', None, interaction_sequence

    return (
        decision_type,
        _normalize_row_decision_notes(reviewed_values.get('notes')),
        interaction_sequence,
    )


def _serialize_row_decision_history(decisions):
    history = []
    for decision in decisions:
        decision_type, notes, sequence = _extract_row_status_decision_state(decision)
        history.append({
            'decision_id': decision.id,
            'decision': decision_type,
            'notes': notes,
            'reviewer': decision.reviewer,
            'timestamp': decision.created_at.isoformat(),
            'interaction_sequence': sequence or 0,
        })
    return history


def record_row_decision(
    batch_id: str,
    raw_import_row_id: int,
    decision: str,
    notes: Optional[str] = None,
    interaction_sequence: Optional[Any] = None,
    reviewer_name: Optional[str] = None,
    database_url: Optional[str] = None,
    reviewer: Optional[str] = None,
) -> dict:
    """
    Record a reviewer's row-level status decision.

    Creates a new ReviewDecision with reviewed_status and optional notes.
    Each decision is append-only; clearing a decision creates a new 'clear_decision' record.

    Args:
        batch_id: Import batch ID
        raw_import_row_id: RawImportRow.id
        decision: One of: 'accept_as_is', 'needs_follow_up', 'reject_row', 'clear_decision'
        notes: Optional reviewer notes (required for 'needs_follow_up')
        interaction_sequence: Monotonic per-row interaction order number
        reviewer_name: Required manually entered reviewer name
        database_url: Optional database connection URL

    Returns:
        Dict with decision_id, decision type, timestamp, and validation status

    Raises:
        ValueError: If batch/row not found, invalid decision type, or required notes are missing
    """
    import os

    # Determine database URL
    if not database_url:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError("Row decision requires database configuration")

    # ``reviewer`` remains an internal compatibility alias for existing direct
    # service callers; the row-decision HTTP flow supplies reviewer_name.
    normalized_reviewer_name = (reviewer_name if reviewer_name is not None else reviewer or '').strip() or None

    # Validate decision type
    valid_decisions = {
        'accept_as_is',
        'needs_follow_up',
        'reject_row',
        'clear_decision'
    }
    if decision not in valid_decisions:
        raise ValueError(
            f"Invalid decision '{decision}'. Must be one of: {', '.join(valid_decisions)}"
        )

    # Reject and follow-up are explicit human dispositions and both require
    # an auditable reason. Accept-as-is has its issue-specific requirement
    # checked below after the row is loaded.
    if requires_reason_for_row_decision(decision, has_active_issues=False) and not (notes and notes.strip()):
        if decision == 'needs_follow_up':
            raise ValueError('Notes required for Follow-up decision')
        raise ValueError('Reason / notes required for Reject row decision')

    normalized_sequence = _normalize_interaction_sequence(interaction_sequence)
    use_sequence_guard = normalized_sequence is not None

    lock = _get_row_decision_lock(batch_id, raw_import_row_id) if use_sequence_guard else None

    if lock is not None:
        lock.acquire()

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

        # A human Accept as-is on a row that still has validation issues must
        # carry an explanation.  Clean rows are system-accepted in the UI and
        # never reach this persistence path.
        if decision == 'accept_as_is' and not (notes and notes.strip()):
            from .issue_recalculation_service import recalculate_row_issues
            has_active_issues = bool(recalculate_row_issues(
                batch_id=batch_id,
                raw_import_row_id=raw_import_row_id,
                database_url=database_url,
            ))
            if requires_reason_for_row_decision(decision, has_active_issues=has_active_issues):
                raise ValueError(
                    'Reason / notes required for Accept as-is when validation issues exist'
                )

        normalized_notes = _normalize_row_decision_notes(notes)
        latest_row_decision = _get_latest_row_status_decision(session, batch_id, raw_import_row_id)
        latest_decision_type, latest_notes, latest_sequence = _extract_row_status_decision_state(latest_row_decision)

        if use_sequence_guard and latest_sequence is not None:
            if normalized_sequence < latest_sequence:
                from .row_status_service import derive_row_status
                row_status = derive_row_status(batch_id, raw_import_row_id, database_url)
                return {
                    'decision_id': latest_row_decision.id if latest_row_decision else None,
                    'decision': latest_decision_type,
                    'timestamp': latest_row_decision.created_at.isoformat() if latest_row_decision else datetime.now(timezone.utc).isoformat(),
                    'success': True,
                    'message': 'Stale row decision ignored',
                    'row_status': row_status,
                    'stale_ignored': True,
                    'interaction_sequence': latest_sequence,
                }

            if normalized_sequence == latest_sequence:
                if latest_decision_type == decision and latest_notes == normalized_notes:
                    from .row_status_service import derive_row_status
                    row_status = derive_row_status(batch_id, raw_import_row_id, database_url)
                    return {
                        'decision_id': latest_row_decision.id if latest_row_decision else None,
                        'decision': decision,
                        'timestamp': latest_row_decision.created_at.isoformat() if latest_row_decision else datetime.now(timezone.utc).isoformat(),
                        'success': True,
                        'message': f'Row decision already recorded: {decision}',
                        'row_status': row_status,
                        'idempotent': True,
                        'interaction_sequence': latest_sequence,
                    }
                raise ValueError("Row decision interaction_sequence already recorded for this row")

        if latest_decision_type == decision and latest_notes == normalized_notes:
            from .row_status_service import derive_row_status
            row_status = derive_row_status(batch_id, raw_import_row_id, database_url)
            return {
                'decision_id': latest_row_decision.id if latest_row_decision else None,
                'decision': decision,
                'timestamp': latest_row_decision.created_at.isoformat() if latest_row_decision else datetime.now(timezone.utc).isoformat(),
                'success': True,
                'message': f'Row decision already recorded: {decision}',
                'row_status': row_status,
                'idempotent': True,
                'interaction_sequence': latest_sequence,
            }

        # Build reviewed_values with decision, notes, and ordering metadata
        reviewed_values = {
            'reviewed_status': decision,
            'interaction_sequence': normalized_sequence if normalized_sequence is not None else None,
        }
        if normalized_notes:
            reviewed_values['notes'] = normalized_notes

        # Remove null ordering metadata from stored payload
        reviewed_values = {key: value for key, value in reviewed_values.items() if value is not None}

        # Create new ReviewDecision record
        # Use decision as the decision type for row-level status decisions
        row_decision = ReviewDecision(
            batch_id=batch_id,
            review_item_id=None,  # Row-level decision, not item-specific
            raw_import_row_id=raw_import_row_id,
            decision=f'row_status:{decision}',  # Prefix to distinguish from item decisions
            reviewed_values=reviewed_values,
            reviewer=normalized_reviewer_name
        )
        session.add(row_decision)
        session.flush()

        # Create audit log record for this decision
        now = datetime.now(timezone.utc)
        audit_details = {
            'decision_value': decision,
            'interaction_sequence': normalized_sequence,
        }
        if normalized_notes:
            audit_details['notes'] = normalized_notes

        audit_record = AuditLogRecord(
            batch_id=batch_id,
            action_type='decision_recorded',
            action_timestamp=now,
            actor=normalized_reviewer_name,
            decision_id=row_decision.id,
            details=audit_details,
            created_at=now,
        )
        session.add(audit_record)
        session.commit()

        # Calculate current row status for frontend dropdown update
        from .row_status_service import derive_row_status
        row_status = derive_row_status(batch_id, raw_import_row_id, database_url)

        return {
            'decision_id': row_decision.id,
            'decision': decision,
            'timestamp': row_decision.created_at.isoformat(),
            'success': True,
            'message': f'Row decision recorded: {decision}',
            'row_status': row_status,  # For frontend dropdown display
            'interaction_sequence': normalized_sequence,
        }

    finally:
        session.close()
        if lock is not None and lock.locked():
            lock.release()


def get_row_decision_state(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
) -> dict:
    """
    Get the latest row-level decision state for a row, including ordering metadata.

    Returns the latest decision record, whether or not it is currently active.
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
        row_decisions = (
            session.query(ReviewDecision)
            .filter_by(
                batch_id=batch_id,
                raw_import_row_id=raw_import_row_id,
            )
            .filter(ReviewDecision.decision.like('row_status:%'))
            .order_by(ReviewDecision.created_at.desc(), ReviewDecision.id.desc())
            .all()
        )
        latest = row_decisions[0] if row_decisions else None
        if not latest:
            return {
                'has_decision': False,
                'decision': None,
                'notes': None,
                'timestamp': None,
                'reviewer': None,
                'interaction_sequence': 0,
                'last_event': None,
                'history': [],
            }

        decision_type, notes, sequence = _extract_row_status_decision_state(latest)
        has_decision = decision_type in ROW_HUMAN_DISPOSITIONS
        last_event = (
            _serialize_row_decision_history([latest])[0]
            if decision_type == 'clear_decision'
            else None
        )

        return {
            'has_decision': has_decision,
            'decision': decision_type if has_decision else None,
            'notes': notes if has_decision else None,
            'timestamp': latest.created_at.isoformat(),
            'reviewer': latest.reviewer,
            'interaction_sequence': sequence or 0,
            'last_event': last_event,
            'history': _serialize_row_decision_history(row_decisions[1:]),
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

    decision_state = get_row_decision_state(batch_id, raw_import_row_id, database_url)
    if not decision_state['has_decision']:
        return None

    return {
        'decision': decision_state['decision'],
        'notes': decision_state['notes'],
        'timestamp': decision_state['timestamp'],
        'reviewer': decision_state['reviewer'],
        'interaction_sequence': decision_state['interaction_sequence'],
    }


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
