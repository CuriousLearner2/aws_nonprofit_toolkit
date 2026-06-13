"""
Database Write Repository - Database implementation of write operations.

Phase 2-Step 2: Implements ValidationDecisionWriter for database backend.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .database_models import Base, ImportBatch, ReviewItem, ReviewDecision, AuditLogRecord
from .write_repository_contracts import ValidationDecisionResult, ValidationDecisionWriter


def get_db_session(database_url: str = 'sqlite:///./givebutter.db') -> Session:
    """
    Create a new database session.

    Args:
        database_url: Database connection string

    Returns:
        SQLAlchemy Session instance
    """
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


class DatabaseValidationDecisionWriter:
    """Implement ValidationDecisionWriter for database backend."""

    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        """
        Initialize write repository with database connection string.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url

    def create_validation_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> ValidationDecisionResult:
        """
        Create a validation decision and audit log entry atomically.

        Workflow:
        1. Validate inputs (batch exists, item exists, item type is 'validation')
        2. Begin transaction
        3. Insert ReviewDecision
        4. Insert AuditLogRecord
        5. Commit transaction
        6. Derive effective status
        7. Return result

        Args:
            batch_id: Import batch ID
            review_item_id: ReviewItem.id
            decision: One of 'accept_issue', 'dismiss_issue', 'defer'
            notes: Optional notes
            reviewer: Reviewer identifier

        Returns:
            ValidationDecisionResult

        Raises:
            ValueError: If validation fails
            Exception: If database transaction fails
        """
        session = get_db_session(self.database_url)
        try:
            # Validation: Import batch exists
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()
            if not batch:
                raise ValueError(f"Import batch '{batch_id}' not found")

            # Validation: Review item exists
            item = session.query(ReviewItem).filter_by(id=review_item_id).first()
            if not item:
                raise ValueError(f"Review item {review_item_id} not found")

            # Validation: Item belongs to this batch
            if item.batch_id != batch_id:
                raise ValueError(
                    f"Review item {review_item_id} does not belong to batch '{batch_id}'"
                )

            # Validation: Item type is 'validation'
            if item.item_type != 'validation':
                raise ValueError(
                    f"Review item {review_item_id} is not a validation item (type: {item.item_type})"
                )

            # Create ReviewDecision
            reviewed_values = None
            if notes:
                reviewed_values = {'notes': notes}

            decision_record = ReviewDecision(
                batch_id=batch_id,
                review_item_id=review_item_id,
                decision=decision,
                reviewed_values=reviewed_values,
                reviewer=reviewer,
                created_at=datetime.utcnow(),
            )
            session.add(decision_record)
            session.flush()  # Flush to get the ID

            decision_id = decision_record.id
            now = datetime.utcnow()

            # Create AuditLogRecord
            # Determine prior status (from latest previous decision)
            prior_status = self._get_prior_status(session, review_item_id, decision_id)

            # Determine effective status (what it is now after this decision)
            status_map = {
                'accept_issue': 'accepted',
                'dismiss_issue': 'dismissed',
                'defer': 'deferred',
            }
            effective_status = status_map.get(decision, 'pending')

            audit_details = {
                'decision_type': 'validation_decision',
                'decision_value': decision,
                'notes': notes,
                'prior_status': prior_status,
                'effective_status': effective_status,
            }

            audit_record = AuditLogRecord(
                batch_id=batch_id,
                action_type='decision_recorded',
                action_timestamp=now,
                actor=reviewer,
                item_id=review_item_id,
                decision_id=decision_id,
                details=audit_details,
                created_at=now,
            )
            session.add(audit_record)
            session.flush()  # Flush to get the ID

            audit_id = audit_record.id

            # Commit transaction
            session.commit()

            return ValidationDecisionResult(
                decision_id=decision_id,
                review_item_id=review_item_id,
                decision=decision,
                effective_status=effective_status,
                audit_log_id=audit_id,
                timestamp=now,
            )

        except ValueError:
            # Validation errors: rollback and re-raise
            session.rollback()
            raise
        except Exception as e:
            # Unexpected errors: rollback and wrap
            session.rollback()
            raise RuntimeError(f"Error recording validation decision: {str(e)}") from e
        finally:
            session.close()

    def _get_prior_status(self, session: Session, review_item_id: int, exclude_decision_id: int) -> str:
        """
        Get the effective status before the most recent decision.

        Args:
            session: Active database session
            review_item_id: ReviewItem.id
            exclude_decision_id: Decision ID to exclude (current decision)

        Returns:
            Prior effective status, or 'pending' if no prior decisions
        """
        prior = (
            session.query(ReviewDecision)
            .filter_by(review_item_id=review_item_id)
            .filter(ReviewDecision.id != exclude_decision_id)
            .order_by(ReviewDecision.created_at.desc())
            .first()
        )

        if not prior:
            return 'pending'

        status_map = {
            'accept_issue': 'accepted',
            'dismiss_issue': 'dismissed',
            'defer': 'deferred',
        }
        return status_map.get(prior.decision, 'pending')
