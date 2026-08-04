"""Read-only aggregation for an import's immutable decision history report."""

import json
import os
from typing import Any, Mapping, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import ImportBatch, ReviewDecision


def get_decision_history_report(
    import_id: str,
    config: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Return stored decisions for one import, without deriving any meaning."""
    config = config or {}
    database_url = config.get("GIVEBUTTER_DATABASE_URL") or os.environ.get(
        "GIVEBUTTER_DATABASE_URL"
    )
    if not database_url:
        raise ValueError("Database configuration is required")

    session = sessionmaker(bind=create_engine(database_url, echo=False))()
    try:
        if session.query(ImportBatch.id).filter_by(id=import_id).first() is None:
            raise LookupError("Import not found")
        records = (
            session.query(ReviewDecision)
            .filter_by(batch_id=import_id)
            .order_by(ReviewDecision.created_at.asc(), ReviewDecision.id.asc())
            .all()
        )
        return {"import_id": import_id, "decisions": [_decision_record(record) for record in records]}
    finally:
        session.close()


def _decision_record(record: ReviewDecision) -> dict[str, Any]:
    """Project only immutable columns stored on a ReviewDecision."""
    return {
        "id": record.id,
        "review_item_id": record.review_item_id,
        "raw_import_row_id": record.raw_import_row_id,
        "decision": record.decision,
        "reviewed_values": record.reviewed_values,
        "reviewer": record.reviewer,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def to_deterministic_json(report: Mapping[str, Any]) -> str:
    """Serialize the report with stable key and array ordering."""
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
