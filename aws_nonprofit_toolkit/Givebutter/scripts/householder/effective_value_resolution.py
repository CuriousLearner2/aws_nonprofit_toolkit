"""Canonical effective-value resolution for autosave and issue recalculation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import RawImportRow, ReviewDecision
from .issue_identity import normalize_validation_issue_field


def _effective_key(field: Any) -> str:
    return normalize_validation_issue_field(field)


def decision_order_key(decision: Any) -> tuple[Any, Any]:
    """Return the canonical chronological ordering for persisted decisions."""
    return decision.created_at, decision.id


def fold_row_reviewed_values(decisions: list[Any]) -> dict[Any, dict[str, Any]]:
    """Fold row-level reviewed values in canonical decision order."""
    folded: dict[Any, dict[str, Any]] = {}
    for decision in sorted(decisions, key=decision_order_key):
        if decision.review_item_id is not None:
            continue
        if decision.reviewed_values:
            folded.setdefault(decision.raw_import_row_id, {}).update(decision.reviewed_values)
    return folded


def merge_effective_values(
    raw_values: Mapping[str, Any] | None,
    reviewed_values: Mapping[str, Any] | None,
) -> dict[str, Any]:
    effective = dict(raw_values or {})
    for source in (raw_values or {}, reviewed_values or {}):
        for field, value in source.items():
            effective[field] = value
            canonical_field = _effective_key(field)
            if canonical_field:
                effective[canonical_field] = value
    return effective


def effective_value_for_field(
    field: Any,
    raw_values: Mapping[str, Any] | None,
    reviewed_values: Mapping[str, Any] | None,
) -> Any:
    canonical_field = _effective_key(field)
    effective = merge_effective_values(raw_values, reviewed_values)
    if canonical_field:
        return effective.get(canonical_field)
    return effective.get(field)


def get_effective_values(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
) -> dict[str, Any]:
    if database_url is None:
        database_url = "sqlite:///./givebutter.db"

    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        raw_row = session.query(RawImportRow).filter_by(id=raw_import_row_id).first()
        if not raw_row:
            raise ValueError(f"Raw import row {raw_import_row_id} not found")

        decisions = session.query(ReviewDecision).filter_by(
            batch_id=batch_id,
            raw_import_row_id=raw_import_row_id,
        ).all()
        reviewed_values: dict[str, Any] = {}
        for decision in sorted(decisions, key=decision_order_key):
            if decision.reviewed_values:
                reviewed_values.update(decision.reviewed_values)

        return merge_effective_values(raw_row.raw_csv_data or {}, reviewed_values)
    finally:
        session.close()
