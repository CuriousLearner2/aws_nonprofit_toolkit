"""
Database Write Repository - Database implementation of write operations.

Phase 2-Step 2: Implements ValidationDecisionWriter for database backend.
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .database_models import Base, ImportBatch, ReviewItem, ReviewDecision, AuditLogRecord
from .write_repository_contracts import (
    ValidationDecisionResult, ValidationDecisionWriter,
    NormalizationDecisionResult, NormalizationDecisionWriter,
    DuplicateDecisionResult, DuplicateDecisionWriter,
)


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


class DatabaseNormalizationDecisionWriter:
    """Implement NormalizationDecisionWriter for database backend."""

    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        """
        Initialize write repository with database connection string.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url

    def create_normalization_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> NormalizationDecisionResult:
        """
        Create a normalization decision and audit log entry atomically.

        Workflow:
        1. Validate inputs (batch exists, item exists, item type is 'normalization')
        2. Extract field/raw_value/normalized_value from ReviewItem.payload_json
        3. Begin transaction
        4. Insert ReviewDecision
        5. Insert AuditLogRecord
        6. Commit transaction
        7. Derive effective status
        8. Return result

        Args:
            batch_id: Import batch ID
            review_item_id: ReviewItem.id
            decision: One of 'accept_normalization', 'reject_normalization', 'defer'
            notes: Optional notes
            reviewer: Reviewer identifier

        Returns:
            NormalizationDecisionResult

        Raises:
            ValueError: If validation fails
            Exception: If database transaction fails
        """
        import json

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

            # Validation: Item type is 'normalization'
            if item.item_type != 'normalization':
                raise ValueError(
                    f"Review item {review_item_id} is not a normalization item (type: {item.item_type})"
                )

            # Extract field details from payload_json
            payload = item.payload_json
            if not isinstance(payload, dict):
                payload = json.loads(payload) if isinstance(payload, str) else {}

            field_name = payload.get('field')
            raw_value = payload.get('raw_value')
            normalized_value = payload.get('normalized_value')

            if not all([field_name, raw_value is not None, normalized_value is not None]):
                raise ValueError(
                    "Normalization payload missing field/raw_value/normalized_value"
                )

            # Create ReviewDecision with reviewed_values
            reviewed_values = {
                'field': field_name,
                'raw_value': raw_value,
                'normalized_value': normalized_value,
            }
            if notes:
                reviewed_values['notes'] = notes

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
                'accept_normalization': 'accepted',
                'reject_normalization': 'rejected',
                'defer': 'deferred',
            }
            effective_status = status_map.get(decision, 'pending')

            audit_details = {
                'decision_type': 'normalization_decision',
                'decision_value': decision,
                'field': field_name,
                'raw_value': raw_value,
                'normalized_value': normalized_value,
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

            return NormalizationDecisionResult(
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
            raise RuntimeError(f"Error recording normalization decision: {str(e)}") from e
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
            'accept_normalization': 'accepted',
            'reject_normalization': 'rejected',
            'defer': 'deferred',
        }
        return status_map.get(prior.decision, 'pending')


class DatabaseDuplicateDecisionWriter:
    """Implement DuplicateDecisionWriter for database backend."""

    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        """
        Initialize write repository with database connection string.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url

    def create_duplicate_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> DuplicateDecisionResult:
        """
        Create a duplicate decision and audit log entry atomically.

        Workflow:
        1. Validate inputs (batch exists, item exists, item type is 'duplicate')
        2. Extract contact/evidence details from ReviewItem.payload_json
        3. Begin transaction
        4. Insert ReviewDecision
        5. Insert AuditLogRecord
        6. Commit transaction
        7. Derive effective status
        8. Return result

        Args:
            batch_id: Import batch ID
            review_item_id: ReviewItem.id
            decision: One of 'same_person', 'different_people', 'defer'
            notes: Optional notes
            reviewer: Reviewer identifier

        Returns:
            DuplicateDecisionResult

        Raises:
            ValueError: If validation fails
            Exception: If database transaction fails
        """
        import json

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

            # Validation: Item type is 'duplicate'
            if item.item_type != 'duplicate':
                raise ValueError(
                    f"Review item {review_item_id} is not a duplicate item (type: {item.item_type})"
                )

            # Extract candidate and evidence details from payload_json
            payload = item.payload_json
            if not isinstance(payload, dict):
                payload = json.loads(payload) if isinstance(payload, str) else {}

            contact_a_data = payload.get('contact_a', {})
            contact_b_data = payload.get('contact_b', {})
            supporting_evidence = payload.get('supporting_evidence', [])
            conflicting_evidence = payload.get('conflicting_evidence', [])

            # Build reviewed_values from candidate data
            reviewed_values = {
                'primary_contact_id': contact_a_data.get('id'),
                'secondary_contact_ids': [contact_b_data.get('id')] if contact_b_data.get('id') else [],
                'candidate_contact_ids': [
                    contact_a_data.get('id'),
                    contact_b_data.get('id'),
                ] if contact_a_data.get('id') and contact_b_data.get('id') else [],
                'evidence_supporting': supporting_evidence if isinstance(supporting_evidence, list) else [],
                'evidence_conflicting': conflicting_evidence if isinstance(conflicting_evidence, list) else [],
            }
            if notes:
                reviewed_values['notes'] = notes

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
                'same_person': 'same_person',
                'different_people': 'different_people',
                'defer': 'deferred',
            }
            effective_status = status_map.get(decision, 'pending')

            audit_details = {
                'decision_type': 'duplicate_decision',
                'decision_value': decision,
                'primary_contact_id': contact_a_data.get('id'),
                'secondary_contact_ids': [contact_b_data.get('id')] if contact_b_data.get('id') else [],
                'candidate_contact_ids': [
                    contact_a_data.get('id'),
                    contact_b_data.get('id'),
                ] if contact_a_data.get('id') and contact_b_data.get('id') else [],
                'evidence_supporting': supporting_evidence if isinstance(supporting_evidence, list) else [],
                'evidence_conflicting': conflicting_evidence if isinstance(conflicting_evidence, list) else [],
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

            return DuplicateDecisionResult(
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
            raise RuntimeError(f"Error recording duplicate decision: {str(e)}") from e
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
            'same_person': 'same_person',
            'different_people': 'different_people',
            'defer': 'deferred',
        }
        return status_map.get(prior.decision, 'pending')
