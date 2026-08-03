"""
Validation Decision Service - Service layer for recording validation decisions.

Phase 2-Step 2: Orchestrates validation decision workflow.
Calls write repository to persist decisions.
"""

from typing import Optional, Mapping, Any
from datetime import datetime

from .write_repository_contracts import ValidationDecisionResult
from .repository_provider import get_import_repository
from .decision_policy import create_decision_writer, latest_decision_status, validate_decision_value


def record_validation_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewed_values: Optional[Mapping[str, Any]] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> ValidationDecisionResult:
    """
    Record a validation decision for a review item.

    Appends ReviewDecision and AuditLogRecord atomically.
    Does not mutate ReviewItem, RawImportRow, or ImportContact.
    Effective status is derived from latest decision.

    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'accept_issue', 'dismiss_issue', 'defer'
        notes: Optional context or explanation
        reviewed_values: Optional dict of field corrections (e.g., {'name': 'John Doe', 'email': 'john@example.com'})
                        Stored as metadata without mutating raw data.
        reviewer: Reviewer identifier (name or email); defaults to None for anonymous
        config: Optional configuration mapping for database selection.
               If None, uses environment variables.
               Expected keys: 'HOUSEHOLDER_REPOSITORY', 'GIVEBUTTER_DATABASE_URL'

    Returns:
        ValidationDecisionResult with decision_id, effective_status, etc.

    Raises:
        ValueError: If validation fails
        DatabaseError: If write transaction fails
    """
    # Validate decision value
    validate_decision_value(decision, {'accept_issue', 'dismiss_issue', 'defer'})

    # Get write repository (database only; fixture mode must not accept writes)
    write_repo = _get_validation_decision_writer(config)

    # Delegate to write repository
    return write_repo.create_validation_decision(
        batch_id=import_id,
        review_item_id=review_item_id,
        decision=decision,
        notes=notes,
        reviewed_values=reviewed_values,
        reviewer=reviewer,
    )


def _get_validation_decision_writer(config: Optional[Mapping[str, Any]]):
    """
    Get the appropriate write repository based on configuration.

    Args:
        config: Configuration mapping

    Returns:
        ValidationDecisionWriter implementation

    Raises:
        ValueError: If database configuration is missing
    """
    from .database_write_repository import DatabaseValidationDecisionWriter
    try:
        return create_decision_writer(config, DatabaseValidationDecisionWriter)
    except ValueError as exc:
        if str(exc).startswith("Decision recording"):
            raise ValueError(str(exc).replace("Decision recording", "Validation decision recording", 1)) from exc
        raise


def get_effective_status(review_item_id: int, database_url: str = 'sqlite:///./givebutter.db') -> str:
    """
    Derive effective status from latest ReviewDecision.

    Args:
        review_item_id: ReviewItem.id
        database_url: Database connection URL

    Returns:
        Effective status: 'pending', 'accepted', 'dismissed', or 'deferred'
    """
    return latest_decision_status(review_item_id, database_url, {
        'accept_issue': 'accepted', 'dismiss_issue': 'dismissed', 'defer': 'deferred'
    })
