"""Fast state-transition matrix for the shared row projections."""

import pytest

from scripts.householder.approval_remaining_issues_policy import project_row_gating
from scripts.householder.row_decision_service import project_effective_disposition
from scripts.householder.row_status_policy import derive_row_status


STATE_ISSUES = {
    "clean": [],
    "warning": [{"field": "email", "severity": "warning"}],
    "blocking": [{"field": "email", "severity": "error"}],
}


def project(state, disposition):
    issues = STATE_ISSUES[state]
    row_status = derive_row_status(issues)
    effective = project_effective_disposition(
        row_status=row_status,
        human_disposition=disposition,
    )
    gating = project_row_gating(
        raw_import_row_id=1,
        row_index=1,
        row_status=row_status,
        has_unresolved_validation=bool(issues),
        human_disposition=effective,
        base_blockers=("Unresolved validation: email",) if issues else (),
    )
    return row_status, effective, gating


@pytest.mark.parametrize(
    ("state", "disposition", "expected_effective", "blocks", "eligible", "retained"),
    [
        ("clean", None, "accept_as_is", False, True, True),
        ("warning", None, None, True, False, True),
        ("blocking", None, None, True, False, True),
        ("clean", "accept_as_is", "accept_as_is", False, True, True),
        ("warning", "accept_as_is", "accept_as_is", False, True, True),
        ("blocking", "accept_as_is", "accept_as_is", False, True, True),
        ("clean", "needs_follow_up", "needs_follow_up", False, False, True),
        ("warning", "needs_follow_up", "needs_follow_up", False, False, True),
        ("blocking", "needs_follow_up", "needs_follow_up", False, False, True),
        ("clean", "reject_row", "reject_row", False, False, True),
        ("warning", "reject_row", "reject_row", False, False, True),
        ("blocking", "reject_row", "reject_row", False, False, True),
    ],
)
def test_row_state_matrix(
    state, disposition, expected_effective, blocks, eligible, retained
):
    row_status, effective, gating = project(state, disposition)

    assert row_status == {"clean": "No issues", "warning": "Warning", "blocking": "Blocking"}[state]
    assert effective == expected_effective
    assert gating.export_blocked is blocks
    assert (gating.export_included and not gating.export_blocked) is eligible
    assert retained is True


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [
        ([('clean', None), ('blocking', None), ('clean', None)],
         [('accept_as_is', False, True), (None, True, False), ('accept_as_is', False, True)]),
        ([('blocking', None), ('clean', 'accept_as_is'), ('blocking', 'accept_as_is')],
         [(None, True, False), ('accept_as_is', False, True), ('accept_as_is', False, True)]),
        ([('blocking', 'needs_follow_up'), ('blocking', None)],
         [('needs_follow_up', False, False), (None, True, False)]),
        ([('blocking', 'reject_row'), ('blocking', None)],
         [('reject_row', False, False), (None, True, False)]),
        ([('blocking', None), ('clean', None)],
         [(None, True, False), ('accept_as_is', False, True)]),
    ],
)
def test_row_state_transition_sequences(sequence, expected):
    actual = []
    for state, disposition in sequence:
        _, effective, gating = project(state, disposition)
        actual.append((effective, gating.export_blocked, gating.export_included and not gating.export_blocked))

    assert actual == expected
