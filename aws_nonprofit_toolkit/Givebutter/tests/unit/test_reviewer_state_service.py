"""Focused contract tests for the shared reviewer-state projection."""

import pytest

from scripts.householder.reviewer_state_service import project_reviewer_row_state


@pytest.mark.parametrize(
    ("name", "status", "issues", "has_unresolved_validation", "decision", "expected_disposition", "export_eligible"),
    [
        ("clean system", "No issues", [], False, None, "accept_as_is", True),
        ("warning-only phone", "Warning", [{"field": "phone", "severity": "warning"}], False, None, "", True),
        ("unresolved issue", "Blocking", [{"field": "email", "severity": "error"}], True, None, "", False),
        ("human accept", "Blocking", [{"field": "email", "severity": "error"}], True, "accept_as_is", "accept_as_is", True),
        ("follow up", "Warning", [{"field": "phone", "severity": "warning"}], False, "needs_follow_up", "needs_follow_up", False),
        ("reject", "Blocking", [{"field": "email", "severity": "error"}], True, "reject_row", "reject_row", False),
    ],
)
def test_shared_projection_agrees_for_reviewer_states(
    name, status, issues, has_unresolved_validation, decision, expected_disposition, export_eligible
):
    state = project_reviewer_row_state(
        batch_id=None,
        raw_import_row_id=7,
        issues=issues,
        row_status=status,
        has_unresolved_validation=has_unresolved_validation,
        decision_state={
            "has_decision": decision is not None,
            "decision": decision,
            "notes": "review reason" if decision else None,
            "reviewer": "Reviewer 1" if decision else None,
            "timestamp": "2026-08-25T12:00:00+00:00" if decision else None,
            "history": [],
        },
    )

    assert state.effective_disposition == expected_disposition, name
    assert state.export_eligible is export_eligible, name
    assert state.approval_blocked is (not export_eligible and decision is None), name


def test_shared_projection_serializes_current_review_and_history_once():
    state = project_reviewer_row_state(
        batch_id=None,
        raw_import_row_id=7,
        issues=[{"field": "email", "severity": "error"}],
        row_status="Blocking",
        has_unresolved_validation=True,
        decision_state={
            "has_decision": True,
            "decision": "accept_as_is",
            "notes": "Accepted after review",
            "reviewer": "Reviewer 1",
            "timestamp": "2026-08-25T12:00:00+00:00",
            "history": [{
                "decision": "accept_as_is",
                "notes": "Accepted after review",
                "reviewer": "Reviewer 1",
                "timestamp": "2026-08-25T12:00:00+00:00",
            }],
        },
    )

    payload = state.to_dict()
    assert payload["effective_disposition"] == payload["decision"] == "accept_as_is"
    assert payload["current_reviewer"] == payload["reviewer"] == "Reviewer 1"
    assert payload["current_notes"] == payload["notes"] == "Accepted after review"
    assert payload["history"] == [{
        "decision": "accept_as_is",
        "notes": "Accepted after review",
        "reviewer": "Reviewer 1",
        "timestamp": "2026-08-25T12:00:00+00:00",
    }]
