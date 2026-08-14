"""Derive row validation status from the current issue projection."""

import os
from typing import Any, Dict, List, Optional

from .row_status_policy import derive_row_status as _derive_row_status


def derive_row_status(
    batch_id: str,
    raw_import_row_id: int,
    database_url: Optional[str] = None,
    issues: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Return ``No issues``, ``Warning``, or ``Blocking`` for the current row."""
    if database_url is None:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL', 'sqlite:///./givebutter.db')

    if issues is None:
        from .issue_recalculation_service import recalculate_row_issues
        issues = recalculate_row_issues(batch_id, raw_import_row_id, database_url)

    return _derive_row_status(issues)
