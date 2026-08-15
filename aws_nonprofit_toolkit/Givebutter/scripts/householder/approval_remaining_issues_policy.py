"""Shared per-row gating projection for approval and export."""

from dataclasses import dataclass
from collections.abc import Iterable
from typing import Optional


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
