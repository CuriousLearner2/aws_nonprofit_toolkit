"""Shared transaction and audit ownership for item-level decisions."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Type

from .database_models import ImportBatch, ReviewItem, ReviewDecision, AuditLogRecord


@dataclass
class DecisionPreparation:
    reviewed_values: Optional[dict]
    audit_details: dict
    effective_status: str
    mutate_item: Optional[Callable[[ReviewItem], None]] = None


def record_item_decision(
    session_factory: Callable[[], Any],
    *,
    batch_id: str,
    review_item_id: int,
    decision: str,
    reviewer: Optional[str],
    item_type: str,
    decision_type: str,
    status_map: dict,
    result_type: Type,
    error_label: str,
    prepare: Callable[[ReviewItem], DecisionPreparation],
):
    """Coordinate validation, append-only decision/audit persistence, and rollback."""
    session = session_factory()
    try:
        batch = session.query(ImportBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Import batch '{batch_id}' not found")

        item = session.query(ReviewItem).filter_by(id=review_item_id).first()
        if not item:
            raise ValueError(f"Review item {review_item_id} not found")
        if item.batch_id != batch_id:
            raise ValueError(
                f"Review item {review_item_id} does not belong to batch '{batch_id}'"
            )
        if item.item_type != item_type:
            raise ValueError(
                f"Review item {review_item_id} is not a {item_type} item "
                f"(type: {item.item_type})"
            )

        prepared = prepare(item)
        decision_record = ReviewDecision(
            batch_id=batch_id,
            review_item_id=review_item_id,
            decision=decision,
            reviewed_values=prepared.reviewed_values,
            reviewer=reviewer,
            created_at=datetime.now(timezone.utc),
        )
        session.add(decision_record)
        session.flush()

        if prepared.mutate_item is not None:
            prepared.mutate_item(item)
            session.add(item)

        prior = (
            session.query(ReviewDecision)
            .filter_by(review_item_id=review_item_id)
            .filter(ReviewDecision.id != decision_record.id)
            .order_by(ReviewDecision.created_at.desc())
            .first()
        )
        prior_status = status_map.get(prior.decision, 'pending') if prior else 'pending'
        now = datetime.now(timezone.utc)
        details = dict(prepared.audit_details)
        details.update({'prior_status': prior_status, 'effective_status': prepared.effective_status})
        audit_record = AuditLogRecord(
            batch_id=batch_id,
            action_type='decision_recorded',
            action_timestamp=now,
            actor=reviewer,
            item_id=review_item_id,
            decision_id=decision_record.id,
            details=details,
            created_at=now,
        )
        session.add(audit_record)
        session.flush()
        session.commit()
        return result_type(
            decision_id=decision_record.id,
            review_item_id=review_item_id,
            decision=decision,
            effective_status=prepared.effective_status,
            audit_log_id=audit_record.id,
            timestamp=now,
        )
    except ValueError:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise RuntimeError(f"Error recording {error_label} decision: {str(exc)}") from exc
    finally:
        session.close()
