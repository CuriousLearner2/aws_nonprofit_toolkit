"""
Household Decision Service - Service layer for recording household decisions.

Phase 2-Step 9: Orchestrates household decision workflow.
Calls write repository to persist decisions.
"""

from typing import Optional, Mapping, Any
from datetime import datetime

from .write_repository_contracts import HouseholdDecisionResult
from .repository_provider import get_import_repository


def record_household_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> HouseholdDecisionResult:
    """
    Record a household decision for a review item.

    Appends ReviewDecision and AuditLogRecord atomically.
    Does not mutate ReviewItem, RawImportRow, or ImportContact.
    Effective status is derived from latest decision.

    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'confirm_household', 'reject_household', 'defer'
        notes: Optional context or explanation
        reviewer: Reviewer identifier (name or email); defaults to None for anonymous
        config: Optional configuration mapping for database selection.
               If None, uses environment variables.
               Expected keys: 'HOUSEHOLDER_REPOSITORY', 'GIVEBUTTER_DATABASE_URL'

    Returns:
        HouseholdDecisionResult with decision_id, effective_status, etc.

    Raises:
        ValueError: If validation fails
        DatabaseError: If write transaction fails
    """
    # Validate decision value
    valid_decisions = {'confirm_household', 'reject_household', 'defer'}
    if decision not in valid_decisions:
        raise ValueError(
            f"Invalid decision '{decision}'. Must be one of: {', '.join(sorted(valid_decisions))}"
        )

    # Get write repository (database only; fixture mode must not accept writes)
    write_repo = _get_household_decision_writer(config)

    # Delegate to write repository
    return write_repo.create_household_decision(
        batch_id=import_id,
        review_item_id=review_item_id,
        decision=decision,
        notes=notes,
        reviewer=reviewer,
    )


def _get_household_decision_writer(config: Optional[Mapping[str, Any]]):
    """
    Get the appropriate write repository based on configuration.

    Args:
        config: Configuration mapping

    Returns:
        HouseholdDecisionWriter implementation

    Raises:
        ValueError: If database configuration is missing
    """
    from .database_write_repository import DatabaseHouseholdDecisionWriter
    import os

    # Determine database URL
    if config:
        database_url = config.get('GIVEBUTTER_DATABASE_URL')
    else:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError(
            "Household decision recording requires database configuration. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or pass config."
        )

    return DatabaseHouseholdDecisionWriter(database_url=database_url)


def get_effective_status(review_item_id: int, database_url: str = 'sqlite:///./givebutter.db') -> str:
    """
    Derive effective status from latest ReviewDecision.

    Args:
        review_item_id: ReviewItem.id
        database_url: Database connection URL

    Returns:
        Effective status: 'pending', 'confirmed', 'rejected', or 'deferred'
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .database_models import ReviewDecision

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        latest = (
            session.query(ReviewDecision)
            .filter_by(review_item_id=review_item_id)
            .order_by(ReviewDecision.created_at.desc())
            .first()
        )

        if not latest:
            return 'pending'

        status_map = {
            'confirm_household': 'confirmed',
            'reject_household': 'rejected',
            'defer': 'deferred',
        }
        return status_map.get(latest.decision, 'pending')
    finally:
        session.close()


def get_next_unresolved_household_index(
    import_id: str,
    current_review_item_id: int,
    database_url: str = 'sqlite:///./givebutter.db'
) -> Optional[int]:
    """
    Find the index of the next unresolved (pending) household after current_review_item_id.

    Used for post-decision redirect. After user decides a household, we find the next
    one that has no decision (effective status is 'pending').

    Args:
        import_id: Import batch ID
        current_review_item_id: ReviewItem.id of household just decided
        database_url: Database connection URL

    Returns:
        Zero-based index of next unresolved household, or None if all are resolved.
    """
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .database_models import ReviewItem, ReviewDecision

    # Use environment variable if not explicitly provided
    if database_url == 'sqlite:///./givebutter.db':
        env_url = os.environ.get('GIVEBUTTER_DATABASE_URL')
        if env_url:
            database_url = env_url

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Get all household items ordered by creation
        household_items = (
            session.query(ReviewItem)
            .filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'household'
            )
            .order_by(ReviewItem.created_at.asc())
            .all()
        )

        # Find index of current item
        current_index = None
        for i, item in enumerate(household_items):
            if item.id == current_review_item_id:
                current_index = i
                break

        if current_index is None:
            # Current item not found, return None
            return None

        # Search for next unresolved (pending) household after current_index
        for i in range(current_index + 1, len(household_items)):
            item = household_items[i]
            # Check if this item has any decision
            latest_decision = (
                session.query(ReviewDecision)
                .filter_by(review_item_id=item.id)
                .order_by(ReviewDecision.created_at.desc())
                .first()
            )
            # If no decision, this is unresolved (pending)
            if not latest_decision:
                return i

        # No unresolved household found after current
        return None

    finally:
        session.close()
