"""Derive row validation status from the current issue projection."""

import os
from typing import Any, Dict, List, Optional

from .row_status_policy import derive_row_status as _derive_row_status


def derive_row_status(
    batch_id: Optional[str] = None,
    raw_import_row_id: Optional[int] = None,
    database_url: Optional[str] = None,
    issues: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Return the canonical status for a row or an already-built issue list."""
    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    if issues is None:
        if batch_id is None or raw_import_row_id is None:
            raise ValueError("batch_id and raw_import_row_id are required when issues are omitted")
        from .issue_recalculation_service import recalculate_row_issues
        issues = recalculate_row_issues(batch_id, raw_import_row_id, database_url)

    return _derive_row_status(issues)
