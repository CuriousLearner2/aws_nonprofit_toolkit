"""Shared policy helpers for review decision services."""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional, Type

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import ReviewDecision


def validate_decision_value(decision: str, valid_decisions: set[str]) -> None:
    if decision not in valid_decisions:
        raise ValueError(
            f"Invalid decision '{decision}'. Must be one of: {', '.join(sorted(valid_decisions))}"
        )


def database_url_for_decision(config: Optional[Mapping[str, Any]]) -> str:
    database_url = config.get('GIVEBUTTER_DATABASE_URL') if config else os.environ.get('GIVEBUTTER_DATABASE_URL')
    if not database_url:
        raise ValueError(
            "Decision recording requires database configuration. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or pass config."
        )
    return database_url


def create_decision_writer(config: Optional[Mapping[str, Any]], writer_type: Type[Any]) -> Any:
    return writer_type(database_url=database_url_for_decision(config))


def latest_decision_status(review_item_id: int, database_url: str, status_map: Mapping[str, str]) -> str:
    engine = create_engine(database_url, echo=False)
    session = sessionmaker(bind=engine)()
    try:
        latest = (
            session.query(ReviewDecision)
            .filter_by(review_item_id=review_item_id)
            .order_by(ReviewDecision.created_at.desc(), ReviewDecision.id.desc())
            .first()
        )
        return 'pending' if not latest else status_map.get(latest.decision, 'pending')
    finally:
        session.close()
