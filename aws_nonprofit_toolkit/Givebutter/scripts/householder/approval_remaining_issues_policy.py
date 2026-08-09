"""Shared per-row gating projection for approval and export."""

from dataclasses import dataclass
from collections.abc import Iterable, Mapping, Set
from typing import Any, Optional


@dataclass(frozen=True)
class RowGatingProjection:
    """The shared disposition/gating result for one row."""

    raw_import_row_id: int
    row_index: int
    row_status: str
    export_included: bool
    export_blocked: bool
    blockers: tuple[str, ...]
    decision_warning: Optional[str] = None


def project_row_gating(
    *,
    raw_import_row_id: int,
    row_index: int,
    row_status: str,
    has_unresolved_validation: bool,
    human_disposition: Optional[str],
    base_blockers: Iterable[str] = (),
) -> RowGatingProjection:
    """Project one row's shared approval/export gating outcome."""
    if human_disposition == 'needs_follow_up':
        return RowGatingProjection(
            raw_import_row_id, row_index, row_status,
            export_included=False,
            export_blocked=False,
            blockers=(),
            decision_warning='needs_follow_up',
        )
    if human_disposition == 'reject_row':
        return RowGatingProjection(
            raw_import_row_id, row_index, row_status,
            export_included=False,
            export_blocked=False,
            blockers=(),
        )

    blockers = list(base_blockers)
    if has_unresolved_validation and not human_disposition:
        if 'Reviewer disposition required' not in blockers:
            blockers.append('Reviewer disposition required')
    elif human_disposition:
        blockers = [
            blocker for blocker in blockers
            if not blocker.startswith('Unresolved validation:')
        ]

    return RowGatingProjection(
        raw_import_row_id, row_index, row_status,
        export_included=True,
        export_blocked=bool(blockers),
        blockers=tuple(dict.fromkeys(blockers)),
    )


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
        human_disposition = (
            'needs_follow_up' if row.id in follow_up_rows
            else 'defer' if row.id in defer_rows
            else None
        )
        projection = project_row_gating(
            raw_import_row_id=row.id,
            row_index=row.row_index,
            row_status=status_by_row[row.id],
            has_unresolved_validation=bool(issues),
            human_disposition=human_disposition,
        )
        if projection.export_blocked:
            projected.append({
                'raw_import_row_id': row.id,
                'row_index': row.row_index,
                'issues': issues,
                'row_status': status_by_row[row.id],
                'decision_warning': 'disposition_required',
            })
        elif projection.decision_warning == 'needs_follow_up':
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
