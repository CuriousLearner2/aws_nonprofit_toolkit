"""Focused contract tests for row-only file approval."""

import pytest

from scripts.householder.approval_service import approve_batch
from scripts.householder.row_decision_service import record_row_decision
from scripts.uploader.app import app

from tests.integration.test_final_reviewer_disposition_rules import disposition_db


def _save_row_decision(database_url, batch_id, raw_id, decision):
    return record_row_decision(
        batch_id=batch_id,
        raw_import_row_id=raw_id,
        decision=decision,
        notes=f"UAT approval reason for {decision}",
        interaction_sequence=1,
        reviewer_name="Approval Reviewer",
        database_url=database_url,
    )


def test_unresolved_no_disposition_blocks_approval(disposition_db):
    database_url, _, batch_id, _, _ = disposition_db

    try:
        approve_batch(batch_id, "approved", database_url=database_url)
    except ValueError as error:
        assert str(error) == 'Batch has unresolved issues; resolve each row before approving'
    else:
        raise AssertionError('Unresolved issue-bearing No disposition must block approval')


def test_approval_api_rejects_file_level_override_and_ui_offers_none(disposition_db):
    database_url, _, batch_id, _, _ = disposition_db
    app.config.update(TESTING=True, GIVEBUTTER_DATABASE_URL=database_url)

    with app.test_client() as client:
        response = client.post(
            f"/imports/{batch_id}/approve-batch",
            json={
                "approval_status": "approved",
                "rows_with_overrides": [{"raw_import_row_id": 1}],
            },
        )
        assert response.status_code == 400
        assert 'File-level approval overrides are not supported' in response.get_json()['error']

        page = client.get(f"/imports/{batch_id}/validation")
        html = page.get_data(as_text=True)
        assert 'Approve with Overrides' not in html
        assert 'approval-modal' not in html
        assert 'confirm-override-btn' not in html


@pytest.mark.parametrize('decision', ('accept_as_is', 'needs_follow_up', 'reject_row'))
def test_row_level_dispositions_allow_approval_without_file_override(disposition_db, decision):
    database_url, _, batch_id, _, issue_raw_id = disposition_db

    _save_row_decision(database_url, batch_id, issue_raw_id, decision)
    result = approve_batch(batch_id, 'approved', database_url=database_url)
    assert result['success'] is True
