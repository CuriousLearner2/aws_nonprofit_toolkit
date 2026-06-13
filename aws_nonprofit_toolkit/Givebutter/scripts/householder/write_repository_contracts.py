"""
Write Repository Contracts - Protocol definitions for write operations.

Separate from read repository to keep concerns clean.
Phase 2-Step 2: Validation decision writer protocol.
"""

from typing import Protocol, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ValidationDecisionResult:
    """Result of recording a validation decision."""
    decision_id: int
    review_item_id: int
    decision: str
    effective_status: str
    audit_log_id: int
    timestamp: datetime


class ValidationDecisionWriter(Protocol):
    """Protocol for writing validation decisions."""

    def create_validation_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> ValidationDecisionResult:
        """
        Create a validation decision and audit log entry.

        Args:
            batch_id: Import batch ID
            review_item_id: ReviewItem.id to decide on
            decision: One of 'accept_issue', 'dismiss_issue', 'defer'
            notes: Optional context for the decision
            reviewer: Reviewer identifier (name or email)

        Returns:
            ValidationDecisionResult with decision details

        Raises:
            ValueError: If validation fails (unknown import, unknown item, invalid decision, wrong type)
            DatabaseError: If transaction fails
        """
        ...


@dataclass(frozen=True)
class NormalizationDecisionResult:
    """Result of recording a normalization decision."""
    decision_id: int
    review_item_id: int
    decision: str
    effective_status: str
    audit_log_id: int
    timestamp: datetime


class NormalizationDecisionWriter(Protocol):
    """Protocol for writing normalization decisions."""

    def create_normalization_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> NormalizationDecisionResult:
        """
        Create a normalization decision and audit log entry.

        Args:
            batch_id: Import batch ID
            review_item_id: ReviewItem.id to decide on
            decision: One of 'accept_normalization', 'reject_normalization', 'defer'
            notes: Optional context for the decision
            reviewer: Reviewer identifier (name or email)

        Returns:
            NormalizationDecisionResult with decision details

        Raises:
            ValueError: If validation fails (unknown import, unknown item, invalid decision, wrong type)
            DatabaseError: If transaction fails
        """
        ...
