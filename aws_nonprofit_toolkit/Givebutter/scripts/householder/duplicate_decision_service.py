"""
Duplicate Decision Service - Service layer for recording duplicate decisions.

Phase 2-Step 7: Orchestrates duplicate decision workflow.
Calls write repository to persist decisions.
"""

from typing import Optional, Mapping, Any
from datetime import datetime

from .write_repository_contracts import DuplicateDecisionResult
from .repository_provider import get_import_repository
from .decision_policy import create_decision_writer, latest_decision_status, validate_decision_value


def record_duplicate_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> DuplicateDecisionResult:
    """
    Record a duplicate decision for a review item.

    Appends ReviewDecision and AuditLogRecord atomically.
    Does not mutate ReviewItem, RawImportRow, or ImportContact.
    Effective status is derived from latest decision.

    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'same_person', 'different_people', 'defer'
        notes: Optional context or explanation
        reviewer: Reviewer identifier (name or email); defaults to None for anonymous
        config: Optional configuration mapping for database selection.
               If None, uses environment variables.
               Expected keys: 'HOUSEHOLDER_REPOSITORY', 'GIVEBUTTER_DATABASE_URL'

    Returns:
        DuplicateDecisionResult with decision_id, effective_status, etc.

    Raises:
        ValueError: If validation fails
        DatabaseError: If write transaction fails
    """
    # Validate decision value
    validate_decision_value(decision, {'same_person', 'different_people', 'defer'})

    # Validate notes required when conflicting evidence exists
    _validate_notes_if_conflicting_evidence(review_item_id, notes, config)

    # Get write repository (database only; fixture mode must not accept writes)
    write_repo = _get_duplicate_decision_writer(config)

    # Delegate to write repository
    return write_repo.create_duplicate_decision(
        batch_id=import_id,
        review_item_id=review_item_id,
        decision=decision,
        notes=notes,
        reviewer=reviewer,
    )


def _validate_notes_if_conflicting_evidence(
    review_item_id: int,
    notes: Optional[str],
    config: Optional[Mapping[str, Any]],
) -> None:
    """
    Validate that notes are provided when conflicting evidence exists.

    Args:
        review_item_id: ReviewItem.id to check
        notes: Notes provided by reviewer (may be None or empty string)
        config: Optional configuration mapping for database selection

    Raises:
        ValueError: If conflicting evidence exists but notes are missing or empty
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .database_models import ReviewItem
    import os

    # Check if in explicit fixture mode (should skip validation)
    repository_mode = os.environ.get('HOUSEHOLDER_REPOSITORY', 'database')
    if config:
        repository_mode = config.get('HOUSEHOLDER_REPOSITORY', repository_mode)

    if repository_mode == 'fixture':
        # Skip validation in explicit fixture mode
        return

    # Determine database URL
    if config:
        database_url = config.get('GIVEBUTTER_DATABASE_URL')
    else:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        # Fail-safe: database URL is required for validation in production mode
        raise ValueError(
            "Duplicate decision validation requires database configuration. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or pass config."
        )

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        review_item = session.query(ReviewItem).filter_by(id=review_item_id).first()
        if not review_item:
            raise ValueError(f"ReviewItem {review_item_id} not found")

        # Check if conflicting evidence exists in payload
        conflicting_evidence = review_item.payload_json.get('conflicting_evidence', [])
        has_conflicting_evidence = bool(conflicting_evidence and len(conflicting_evidence) > 0)

        # If conflicting evidence exists, notes are required
        if has_conflicting_evidence:
            notes_present = notes and notes.strip()
            if not notes_present:
                raise ValueError(
                    "Notes are required when conflicting evidence exists. "
                    "Please provide an explanation for your decision."
                )
    finally:
        session.close()


def _get_duplicate_decision_writer(config: Optional[Mapping[str, Any]]):
    """
    Get the appropriate write repository based on configuration.

    Args:
        config: Configuration mapping

    Returns:
        DuplicateDecisionWriter implementation

    Raises:
        ValueError: If database configuration is missing
    """
    from .database_write_repository import DatabaseDuplicateDecisionWriter
    try:
        return create_decision_writer(config, DatabaseDuplicateDecisionWriter)
    except ValueError as exc:
        if str(exc).startswith("Decision recording"):
            raise ValueError(str(exc).replace("Decision recording", "Duplicate decision recording", 1)) from exc
        raise


def get_effective_status(review_item_id: int, database_url: str = 'sqlite:///./givebutter.db') -> str:
    """
    Derive effective status from latest ReviewDecision.

    Args:
        review_item_id: ReviewItem.id
        database_url: Database connection URL

    Returns:
        Effective status: 'pending', 'same_person', 'different_people', or 'deferred'
    """
    return latest_decision_status(review_item_id, database_url, {
        'same_person': 'same_person', 'different_people': 'different_people', 'defer': 'deferred'
    })
