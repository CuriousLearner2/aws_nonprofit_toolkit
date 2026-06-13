"""
Normalization Decision Service - Service layer for recording normalization decisions.

Phase 2-Step 5: Orchestrates normalization decision workflow.
Calls write repository to persist decisions.
"""

from typing import Optional, Mapping, Any
from datetime import datetime

from .write_repository_contracts import NormalizationDecisionResult
from .repository_provider import get_import_repository


def record_normalization_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> NormalizationDecisionResult:
    """
    Record a normalization decision for a review item.

    Appends ReviewDecision and AuditLogRecord atomically.
    Does not mutate ReviewItem, RawImportRow, or ImportContact.
    Effective status is derived from latest decision.

    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'accept_normalization', 'reject_normalization', 'defer'
        notes: Optional context or explanation
        reviewer: Reviewer identifier (name or email); defaults to None for anonymous
        config: Optional configuration mapping for database selection.
               If None, uses environment variables.
               Expected keys: 'HOUSEHOLDER_REPOSITORY', 'GIVEBUTTER_DATABASE_URL'

    Returns:
        NormalizationDecisionResult with decision_id, effective_status, etc.

    Raises:
        ValueError: If validation fails
        DatabaseError: If write transaction fails
    """
    # Validate decision value
    valid_decisions = {'accept_normalization', 'reject_normalization', 'defer'}
    if decision not in valid_decisions:
        raise ValueError(
            f"Invalid decision '{decision}'. Must be one of: {', '.join(sorted(valid_decisions))}"
        )

    # Get write repository (database only; fixture mode must not accept writes)
    write_repo = _get_normalization_decision_writer(config)

    # Delegate to write repository
    return write_repo.create_normalization_decision(
        batch_id=import_id,
        review_item_id=review_item_id,
        decision=decision,
        notes=notes,
        reviewer=reviewer,
    )


def _get_normalization_decision_writer(config: Optional[Mapping[str, Any]]):
    """
    Get the appropriate write repository based on configuration.

    Args:
        config: Configuration mapping

    Returns:
        NormalizationDecisionWriter implementation

    Raises:
        ValueError: If database configuration is missing
    """
    from .database_write_repository import DatabaseNormalizationDecisionWriter
    import os

    # Determine database URL
    if config:
        database_url = config.get('GIVEBUTTER_DATABASE_URL')
    else:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError(
            "Normalization decision recording requires database configuration. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or pass config."
        )

    return DatabaseNormalizationDecisionWriter(database_url=database_url)


def get_effective_status(review_item_id: int, database_url: str = 'sqlite:///./givebutter.db') -> str:
    """
    Derive effective status from latest ReviewDecision.

    Args:
        review_item_id: ReviewItem.id
        database_url: Database connection URL

    Returns:
        Effective status: 'pending', 'accepted', 'rejected', or 'deferred'
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
            'accept_normalization': 'accepted',
            'reject_normalization': 'rejected',
            'defer': 'deferred',
        }
        return status_map.get(latest.decision, 'pending')
    finally:
        session.close()
