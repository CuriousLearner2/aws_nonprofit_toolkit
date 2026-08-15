"""Parity tests for the shared approval/export row-gating projection."""

import pytest

from scripts.householder.approval_remaining_issues_policy import project_row_gating


@pytest.mark.parametrize(
    ("name", "has_issue", "disposition", "included", "blocked", "warning"),
    [
        ("clean", False, None, True, False, None),
        ("unresolved issue", True, None, True, True, None),
        ("human accept", True, "accept_as_is", True, False, None),
        ("needs follow-up", True, "needs_follow_up", False, False, "needs_follow_up"),
        ("reject", True, "reject_row", False, False, None),
        ("warning-only issue", True, None, True, True, None),
    ],
)
def test_shared_projection_matches_authoritative_row_gating(
    name, has_issue, disposition, included, blocked, warning
):
    projection = project_row_gating(
        raw_import_row_id=1,
        row_index=1,
        row_status="Blocking" if has_issue else "No issues",
        has_unresolved_validation=has_issue,
        human_disposition=disposition,
    )

    assert projection.export_included is included, name
    assert projection.export_blocked is blocked, name
    assert projection.decision_warning == warning, name


def test_shared_projection_matches_mixed_batch_aggregate():
    projections = [
        project_row_gating(
            raw_import_row_id=index,
            row_index=index,
            row_status="No issues" if index == 1 else "Blocking",
            has_unresolved_validation=index != 1,
            human_disposition=disposition,
        )
        for index, disposition in (
            (1, None),
            (2, None),
            (3, "needs_follow_up"),
            (4, "reject_row"),
        )
    ]

    assert sum(projection.export_blocked for projection in projections) == 1
    assert [
        projection.raw_import_row_id
        for projection in projections
        if projection.export_included and not projection.export_blocked
    ] == [1]
