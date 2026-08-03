"""Pure projection policy for rows that remain before batch approval."""

from collections.abc import Iterable, Mapping, Set
from typing import Any


def project_remaining_issues(
    rows: Iterable[Any],
    issues_by_row: Mapping[int, list[dict[str, Any]]],
    status_by_row: Mapping[int, str],
    follow_up_rows: Set[int],
    defer_rows: Set[int],
) -> list[dict[str, Any]]:
    """Project blocking issues and pending row decisions in source row order."""
    projected = []
    for row in rows:
        issues = issues_by_row[row.id]
        blocking_issues = [
            issue for issue in issues
            if issue.get('severity', 'warning') == 'error'
        ]
        if blocking_issues:
            projected.append({
                'raw_import_row_id': row.id,
                'row_index': row.row_index,
                'issues': blocking_issues,
                'row_status': status_by_row[row.id],
            })
        elif row.id in follow_up_rows:
            projected.append({
                'raw_import_row_id': row.id,
                'row_index': row.row_index,
                'issues': [{'field': 'row_decision', 'reason': 'Marked as Needs follow-up'}],
                'row_status': status_by_row[row.id],
                'decision_warning': 'needs_follow_up',
            })
        elif row.id in defer_rows:
            projected.append({
                'raw_import_row_id': row.id,
                'row_index': row.row_index,
                'issues': [{'field': 'row_decision', 'reason': 'Deferred for later review'}],
                'row_status': status_by_row[row.id],
                'decision_warning': 'defer',
            })
    return projected
