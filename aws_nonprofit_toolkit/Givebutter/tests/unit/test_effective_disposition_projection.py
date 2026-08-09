"""Focused parity tests for effective row disposition projection."""

import pytest

from scripts.householder.row_decision_service import project_effective_disposition


@pytest.mark.parametrize(
    ("row_status", "human_disposition", "expected"),
    [
        ("No issues", None, "accept_as_is"),
        ("Blocking", None, None),
        ("Warning", None, None),
        ("Blocking", "accept_as_is", "accept_as_is"),
        ("No issues", "accept_as_is", "accept_as_is"),
        ("Blocking", "needs_follow_up", "needs_follow_up"),
        ("No issues", "reject_row", "reject_row"),
        ("Blocking", "reject_row", "reject_row"),
        ("No issues", "clear_decision", "accept_as_is"),
        ("Blocking", "clear_decision", None),
    ],
)
def test_effective_disposition_projection_preserves_human_or_derives_system(
    row_status, human_disposition, expected
):
    assert project_effective_disposition(
        row_status=row_status,
        human_disposition=human_disposition,
    ) == expected


def test_saved_human_accept_persists_across_validation_changes():
    assert project_effective_disposition(
        row_status="No issues",
        human_disposition="accept_as_is",
    ) == "accept_as_is"
    assert project_effective_disposition(
        row_status="Blocking",
        human_disposition="accept_as_is",
    ) == "accept_as_is"
