"""Focused UAT-024 regressions for persisted edits superseding human decisions."""

from scripts.householder.autosave_service import autosave_row_corrections
from scripts.householder.database_models import RawImportRow, ReviewDecision
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.issue_recalculation_service import recalculate_row_issues
from scripts.householder.row_decision_service import get_row_decision_state, record_row_decision
from scripts.uploader.app import app

from tests.integration.test_final_reviewer_disposition_rules import disposition_db


def _save_human(database_url, batch_id, raw_id, decision, sequence):
    return record_row_decision(
        batch_id=batch_id,
        raw_import_row_id=raw_id,
        decision=decision,
        notes=f"UAT-024 {decision} reason",
        interaction_sequence=sequence,
        reviewer_name="UAT-024 Reviewer",
        database_url=database_url,
    )


def test_each_human_disposition_is_invalidated_after_successful_edit(disposition_db):
    database_url, Session, batch_id, _, issue_raw_id = disposition_db

    for sequence, decision in enumerate(("accept_as_is", "needs_follow_up", "reject_row"), 1):
        _save_human(database_url, batch_id, issue_raw_id, decision, sequence)
        result = autosave_row_corrections(
            batch_id=batch_id,
            raw_import_row_id=issue_raw_id,
            corrected_values={"name": f"Edited {decision}"},
            database_url=database_url,
        )

        assert result.disposition_invalidated is True
        state = get_row_decision_state(batch_id, issue_raw_id, database_url)
        assert state["has_decision"] is False
        assert any(entry["decision"] == decision for entry in state["history"])
        assert recalculate_row_issues(batch_id, issue_raw_id, database_url)
        assert build_export_preview(
            batch_id, {"GIVEBUTTER_DATABASE_URL": database_url}
        ).blocked_count == 1

        session = Session()
        try:
            assert session.query(ReviewDecision).filter_by(
                batch_id=batch_id,
                raw_import_row_id=issue_raw_id,
                decision=f"row_status:{decision}",
            ).count() == 1
        finally:
            session.close()


def test_successful_edit_resolving_issues_returns_to_system_accept(disposition_db):
    database_url, _, batch_id, _, issue_raw_id = disposition_db
    _save_human(database_url, batch_id, issue_raw_id, "accept_as_is", 1)

    result = autosave_row_corrections(
        batch_id=batch_id,
        raw_import_row_id=issue_raw_id,
        corrected_values={"email": "fixed@example.com"},
        database_url=database_url,
    )

    assert result.disposition_invalidated is True
    assert recalculate_row_issues(batch_id, issue_raw_id, database_url) == []
    state = get_row_decision_state(batch_id, issue_raw_id, database_url)
    assert state["has_decision"] is False
    assert build_export_preview(
        batch_id, {"GIVEBUTTER_DATABASE_URL": database_url}
    ).blocked_count == 0


def test_system_accept_edit_creating_issue_has_no_human_disposition(disposition_db):
    database_url, _, batch_id, clean_raw_id, _ = disposition_db

    result = autosave_row_corrections(
        batch_id=batch_id,
        raw_import_row_id=clean_raw_id,
        corrected_values={"address": ""},
        database_url=database_url,
    )

    assert result.disposition_invalidated is False
    assert recalculate_row_issues(batch_id, clean_raw_id, database_url)
    assert get_row_decision_state(batch_id, clean_raw_id, database_url)["has_decision"] is False


def test_failed_edit_preserves_current_human_disposition(disposition_db, monkeypatch):
    database_url, Session, batch_id, _, issue_raw_id = disposition_db
    _save_human(database_url, batch_id, issue_raw_id, "reject_row", 1)
    monkeypatch.setenv("GIVEBUTTER_DATABASE_URL", database_url)
    app.config.update(TESTING=True, GIVEBUTTER_DATABASE_URL=database_url)

    with app.test_client() as client:
        response = client.post(
            f"/imports/{batch_id}/autosave",
            json={
                "raw_import_row_id": issue_raw_id,
                "corrected_values": {"email": "not-an-email"},
            },
        )
    assert response.status_code == 400
    state = get_row_decision_state(batch_id, issue_raw_id, database_url)
    assert state["has_decision"] is True
    assert state["decision"] == "reject_row"
    assert state["reviewer"] == "UAT-024 Reviewer"

    session = Session()
    try:
        assert session.query(RawImportRow).filter_by(id=issue_raw_id).one().raw_csv_data["email"] == "invalid-email"
    finally:
        session.close()
