"""
Audit Service - Service layer for audit log route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5P: Wired to use repository provider for flexible repository selection.
"""

import csv
import io
import math
import os
from typing import Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository


def get_audit_log(import_id: str, config: Optional[Mapping[str, Any]] = None,
                  action: Optional[str] = None, page: int = 1,
                  per_page: int = 50) -> Dict[str, Any]:
    """
    Get audit log page data for a specific import.

    Service orchestration: calls repository to fetch audit data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch audit data for
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed audit.

    Returns:
        Dictionary with 'batch' and 'audit_log' keys, ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    audit_vm = repository.get_audit(import_id)
    data = audit_vm.to_template_dict()
    entries = list(data.get('audit_log', []))
    action = (action or '').strip()
    if action:
        entries = [entry for entry in entries if _action_key(entry) == action]
    per_page = max(1, min(int(per_page), 200))
    page = max(1, int(page))
    total = len(entries)
    pages = max(1, math.ceil(total / per_page))
    page = min(page, pages)
    start = (page - 1) * per_page
    data['audit_log'] = entries[start:start + per_page]
    data.update({'audit_log_total': total, 'audit_page': page,
                 'audit_per_page': per_page, 'audit_total_pages': pages,
                 'audit_action': action})
    return data


def _action_key(entry: Any) -> str:
    action_value = getattr(entry, 'action', None)
    if action_value is None and isinstance(entry, dict):
        action_value = entry.get('action', '')
    action = str(action_value or '').lower()
    if 'duplicate' in action or 'same person' in action:
        return 'marked-duplicate'
    if 'different' in action and 'household' not in action:
        return 'marked-different'
    if 'normalization' in action and 'accept' in action:
        return 'normalization-accepted'
    if 'normalization' in action and 'reject' in action:
        return 'normalization-rejected'
    if 'household' in action and 'confirm' in action:
        return 'household-confirmed'
    if 'defer' in action:
        return 'record-deferred'
    return 'other'


def get_audit_log_csv(import_id: str, config: Optional[Mapping[str, Any]] = None,
                      action: Optional[str] = None) -> str:
    data = get_audit_log(import_id, config=config, action=action, page=1, per_page=200)
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(('Timestamp', 'Action', 'Details', 'Reviewer'))
    for entry in data.get('audit_log', []):
        values = []
        for name in ('timestamp', 'action', 'details', 'reviewer'):
            value = getattr(entry, name, None)
            if value is None and isinstance(entry, dict):
                value = entry.get(name, '')
            values.append(str(value or ''))
        writer.writerow(values)
    return output.getvalue()


def get_decision_history(import_id: str, review_item_id: int,
                         config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .database_models import ReviewItem, ReviewDecision
    config = config or {}
    database_url = config.get('GIVEBUTTER_DATABASE_URL') or os.environ.get('GIVEBUTTER_DATABASE_URL')
    if not database_url:
        raise ValueError('Database configuration is required')
    session = sessionmaker(bind=create_engine(database_url, echo=False))()
    try:
        item = session.query(ReviewItem).filter_by(id=review_item_id, batch_id=import_id).first()
        if item is None:
            raise LookupError('Review item not found')
        decisions = session.query(ReviewDecision).filter_by(
            batch_id=import_id, review_item_id=review_item_id
        ).order_by(ReviewDecision.created_at.asc(), ReviewDecision.id.asc()).all()
        return {'import_id': import_id, 'review_item_id': review_item_id, 'decisions': [{
            'id': decision.id, 'decision': decision.decision,
            'reviewed_values': decision.reviewed_values, 'reviewer': decision.reviewer,
            'created_at': decision.created_at.isoformat() if decision.created_at else None,
        } for decision in decisions]}
    finally:
        session.close()
