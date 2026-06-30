"""Normalizations Service - Service layer for normalizations review route.

Thin orchestration layer that returns template-ready data for the
normalizations review screen and handles normalization decision recording.
"""

from typing import Dict, Any, Optional, Mapping
from datetime import datetime

from .write_repository_contracts import NormalizationDecisionResult
from .repository_provider import get_import_repository


def get_normalizations_review(
    import_id: str,
    index: int = 0,
    config: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get normalizations review page data for a specific import.

    Args:
        import_id: Import ID to fetch normalizations data for
        index: Zero-based index of normalization suggestion to display. Defaults to 0.
        config: Optional configuration mapping for repository selection.

    Returns:
        Dictionary with batch and normalizations data, ready for template
    """
    repository = get_import_repository(config)

    try:
        normalizations_vm = repository.get_normalizations(import_id, index=index)
        return normalizations_vm.to_template_dict()
    except (AttributeError, NotImplementedError):
        # Fallback for when repository method isn't fully implemented
        return {
            "batch": {"id": import_id},
            "message": "Normalizations review - coming soon"
        }


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
