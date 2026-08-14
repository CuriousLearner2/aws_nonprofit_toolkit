"""Focused database regressions for final reviewer-disposition rules."""

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import (
    AuditLogRecord,
    Base,
    ImportBatch,
    ImportContact,
    RawImportRow,
    ReviewDecision,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.row_decision_service import get_row_decision_state
from scripts.householder.row_decision_service import record_row_decision
from scripts.householder.issue_recalculation_service import recalculate_row_issues


@pytest.fixture
def disposition_db():
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()
    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='final-disposition-batch',
        filename='disposition.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
    )
    session.add(batch)
    session.flush()

    clean_raw = RawImportRow(
        batch_id=batch.id,
        row_index=1,
        raw_csv_data={
            'name': 'Clean Row', 'email': 'clean@example.com',
            'amount': '10.00', 'address': '123 Main St',
        },
    )
    issue_raw = RawImportRow(
        batch_id=batch.id,
        row_index=2,
        raw_csv_data={
            'name': 'Issue Row', 'email': 'invalid-email',
            'amount': '20.00', 'address': '456 Oak Ave',
        },
    )
    session.add_all([clean_raw, issue_raw])
    session.flush()
    session.add_all([
        ImportContact(
            batch_id=batch.id,
            raw_import_row_id=clean_raw.id,
            first_name='Clean',
            last_name='Row',
            email='clean@example.com',
            amount=10.0,
            address_line1='123 Main St',
        ),
        ImportContact(
            batch_id=batch.id,
            raw_import_row_id=issue_raw.id,
            first_name='Issue',
            last_name='Row',
            email='invalid-email',
            amount=20.0,
            address_line1='456 Oak Ave',
        ),
    ])
    session.flush()
    issue_item = ReviewItem(
        batch_id=batch.id,
        item_type='validation',
        status='pending',
        payload_json={
            'field': 'email',
            'issue': 'invalid_email_format',
            'reason': 'invalid_email_format',
            'description': 'Invalid email format',
            'severity': 'error',
        },
    )
    session.add(issue_item)
    session.flush()
    issue_contact = session.query(ImportContact).filter_by(raw_import_row_id=issue_raw.id).one()
    session.add(ReviewItemSubject(
        review_item_id=issue_item.id,
        subject_type='import_contact_snapshot',
        subject_id=issue_contact.id,
    ))
    session.commit()

    yield database_url, Session, batch.id, clean_raw.id, issue_raw.id

    session.close()
    Path(db_path).unlink(missing_ok=True)


def _post_row_decision(client, batch_id, raw_id, decision, notes=None, sequence=1):
    return client.post(
        f'/imports/{batch_id}/row-decision',
        json={
            'raw_import_row_id': raw_id,
            'decision': decision,
            'notes': notes,
            'reviewer_name': 'Disposition Reviewer',
            'interaction_sequence': sequence,
        },
    )


def test_clean_row_is_system_accepted_without_review_records(disposition_db, monkeypatch):
    database_url, Session, batch_id, clean_raw_id, _ = disposition_db
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    state = get_row_decision_state(batch_id, clean_raw_id, database_url)
    preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

    assert state['has_decision'] is False
    assert preview.is_export_ready is False  # issue row still lacks a disposition
    clean_preview_row = next(row for row in preview.export_rows if row.source_row_index == 1)
    assert clean_preview_row.export_blocked is False
    session = Session()
    try:
        assert session.query(ReviewDecision).count() == 0
        assert session.query(AuditLogRecord).count() == 0
    finally:
        session.close()


def test_issue_row_requires_human_accept_notes_and_preserves_issue(
    disposition_db, monkeypatch
):
    database_url, Session, batch_id, _, issue_raw_id = disposition_db
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    from scripts.uploader.app import app

    app.config['TESTING'] = True
    app.config['GIVEBUTTER_DATABASE_URL'] = database_url
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    with app.test_client() as client:
        approval_check = client.post(
            f'/imports/{batch_id}/approve-batch',
            json={'approval_status': 'approved'},
        )
        assert approval_check.status_code == 400
        assert 'unresolved issues' in approval_check.get_json()['error']

        before = _post_row_decision(client, batch_id, issue_raw_id, 'accept_as_is')
        assert before.status_code == 400
        assert 'Reason / notes required' in before.get_json()['error']

        preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        assert preview.is_export_ready is False

        saved = _post_row_decision(
            client, batch_id, issue_raw_id, 'accept_as_is', 'Reviewed invalid value', 1
        )
        assert saved.status_code == 200

    preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
    assert preview.is_export_ready is True
    issue_row = next(row for row in preview.export_rows if row.source_row_index == 2)
    assert issue_row.validation_issues
    assert issue_row.export_blocked is False
    session = Session()
    try:
        assert session.query(ReviewDecision).filter_by(raw_import_row_id=issue_raw_id).count() == 1
        assert session.query(AuditLogRecord).count() == 1
    finally:
        session.close()


def test_reject_row_requires_reason_and_does_not_persist_without_it(disposition_db, monkeypatch):
    database_url, Session, batch_id, clean_raw_id, _ = disposition_db
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    from scripts.uploader.app import app

    app.config['TESTING'] = True
    app.config['GIVEBUTTER_DATABASE_URL'] = database_url
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    with app.test_client() as client:
        rejected = _post_row_decision(client, batch_id, clean_raw_id, 'reject_row')
        assert rejected.status_code == 400
        assert 'Reason / notes required for Reject row' in rejected.get_json()['error']

    session = Session()
    try:
        assert session.query(ReviewDecision).filter_by(raw_import_row_id=clean_raw_id).count() == 0
        assert session.query(AuditLogRecord).filter_by(batch_id=batch_id).count() == 0
    finally:
        session.close()


def test_clear_is_only_saved_human_revision_and_restores_issue_default(
    disposition_db, monkeypatch
):
    database_url, Session, batch_id, _, issue_raw_id = disposition_db
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    from scripts.uploader.app import app

    app.config['TESTING'] = True
    app.config['GIVEBUTTER_DATABASE_URL'] = database_url
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    with app.test_client() as client:
        saved = _post_row_decision(
            client, batch_id, issue_raw_id, 'needs_follow_up', 'Need confirmation', 1
        )
        assert saved.status_code == 200
        cleared = _post_row_decision(client, batch_id, issue_raw_id, 'clear_decision', None, 2)
        assert cleared.status_code == 200

    state = get_row_decision_state(batch_id, issue_raw_id, database_url)
    preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
    issue_row = next(row for row in preview.export_rows if row.source_row_index == 2)
    assert state['has_decision'] is False
    assert state['history'][0]['decision'] == 'needs_follow_up'
    assert issue_row.validation_issues
    assert issue_row.export_blocked is True
    session = Session()
    try:
        assert session.query(ReviewDecision).filter_by(raw_import_row_id=issue_raw_id).count() == 2
        assert session.query(AuditLogRecord).filter_by(batch_id=batch_id).count() == 2
    finally:
        session.close()


def test_follow_up_and_reject_are_excluded_and_dashboard_recovers_them(
    disposition_db, monkeypatch
):
    database_url, _, batch_id, clean_raw_id, issue_raw_id = disposition_db
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    from scripts.uploader.app import app

    app.config['TESTING'] = True
    app.config['GIVEBUTTER_DATABASE_URL'] = database_url
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    record_row_decision(
        batch_id, issue_raw_id, 'needs_follow_up', 'Need donor confirmation',
        interaction_sequence=1, reviewer_name='Reviewer', database_url=database_url,
    )
    record_row_decision(
        batch_id, clean_raw_id, 'reject_row', 'Duplicate source row',
        interaction_sequence=1, reviewer_name='Reviewer', database_url=database_url,
    )

    preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
    assert preview.is_export_ready is True
    assert preview.exported_count == 0
    assert preview.needs_follow_up_count == 1
    assert preview.rejected_count == 1
    assert preview.export_rows == ()

    with app.test_client() as client:
        dashboard = client.get(f'/imports/{batch_id}/dashboard')
        assert dashboard.status_code == 200
        body = dashboard.get_data(as_text=True)
        assert 'Needs follow-up: 1' in body
        assert f'/imports/{batch_id}/validation?disposition=needs_follow_up' in body

        filtered = client.get(f'/imports/{batch_id}/validation?disposition=needs_follow_up')
        assert filtered.status_code == 200
        filtered_body = filtered.get_data(as_text=True)
        assert 'Issue Row' in filtered_body
        assert 'Clean Row' not in filtered_body


def test_defer_is_not_a_row_disposition_and_new_notes_are_blank(monkeypatch):
    from scripts.householder.row_decision_service import record_row_decision

    with pytest.raises(ValueError, match="Invalid decision 'defer'"):
        record_row_decision(
            'missing-batch', 1, 'defer', database_url='sqlite:///:memory:',
            reviewer_name='Reviewer', interaction_sequence=1,
        )

    template = Path(__file__).resolve().parents[2] / 'scripts/uploader/templates/imports/validation.html'
    html = template.read_text()
    assert 'value="defer"' not in html
    assert "['defer', 'Defer']" not in html
    assert 'class="edit-row-review"' not in html
    assert 'box-sizing: border-box;">${escapeHtml(currentNotes)}</textarea>' not in html


def test_missing_address_source_does_not_synthesize_warning(disposition_db):
    database_url, Session, batch_id, _, _ = disposition_db
    session = Session()
    raw = RawImportRow(
        batch_id=batch_id,
        row_index=3,
        raw_csv_data={'name': 'No Address Source', 'email': 'source@example.com'},
    )
    session.add(raw)
    session.flush()
    session.add(ImportContact(
        batch_id=batch_id,
        raw_import_row_id=raw.id,
        first_name='No',
        last_name='Address Source',
        email='source@example.com',
        amount=30.0,
        address_line1=None,
    ))
    session.commit()
    raw_id = raw.id
    session.close()

    issues = recalculate_row_issues(batch_id, raw_id, database_url)
    assert not any(issue.get('field') == 'address' for issue in issues)
