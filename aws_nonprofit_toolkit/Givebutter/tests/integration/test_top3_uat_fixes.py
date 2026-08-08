"""Focused regressions for the three Householder UAT defects."""

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
from scripts.householder.issue_recalculation_service import recalculate_row_issues
from scripts.uploader.app import app


@pytest.fixture
def top3_database(monkeypatch):
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_file.close()
    database_url = f'sqlite:///{db_file.name}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    app.config.update(TESTING=True, HOUSEHOLDER_REPOSITORY='database', GIVEBUTTER_DATABASE_URL=database_url)
    yield database_url, sessionmaker(bind=engine)
    Path(db_file.name).unlink(missing_ok=True)


def _seed_row(session, batch_id, value):
    session.add(ImportBatch(
        id=batch_id,
        filename='uat.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=1,
    ))
    session.flush()
    row = RawImportRow(batch_id=batch_id, row_index=1, raw_csv_data=value)
    session.add(row)
    session.flush()
    session.add(ImportContact(
        batch_id=batch_id,
        raw_import_row_id=row.id,
        first_name='Jordan',
        last_name='Lee',
        email=value.get('email', ''),
        phone=value.get('phone', ''),
        address_line1=value.get('address', ''),
    ))
    session.commit()
    return row.id


def test_follow_up_blank_notes_is_rejected_without_persistence(top3_database):
    database_url, Session = top3_database
    session = Session()
    row_id = _seed_row(session, 'follow-up-notes-regression', {
        'name': 'Jordan Lee', 'email': 'jordan@example.com', 'phone': '4155552671',
        'address': '1 Main St',
    })
    prior = ReviewDecision(
        batch_id='follow-up-notes-regression', raw_import_row_id=row_id,
        decision='row_status:defer', reviewed_values={'notes': 'prior state', 'interaction_sequence': 1},
        reviewer='Existing reviewer',
    )
    session.add(prior)
    session.flush()
    session.add(AuditLogRecord(
        batch_id='follow-up-notes-regression', action_type='decision_recorded',
        decision_id=prior.id, actor='Existing reviewer', details={},
    ))
    session.commit()
    before_decisions = session.query(ReviewDecision).count()
    before_audits = session.query(AuditLogRecord).count()
    session.close()

    with app.test_client() as client:
        for notes in ('', '   \n\t'):
            response = client.post('/imports/follow-up-notes-regression/row-decision', json={
                'raw_import_row_id': row_id,
                'decision': 'needs_follow_up',
                'notes': notes,
                'reviewer_name': 'New reviewer',
                'interaction_sequence': 2,
            })
            assert response.status_code == 400
            assert response.get_json()['error'] == 'Notes required for Follow-up decision'

    session = Session()
    assert session.query(ReviewDecision).count() == before_decisions
    assert session.query(AuditLogRecord).count() == before_audits
    saved = session.query(ReviewDecision).filter_by(raw_import_row_id=row_id).one()
    assert saved.decision == 'row_status:defer'
    assert saved.reviewed_values['notes'] == 'prior state'
    session.close()


def test_generic_email_issue_is_suppressed_but_distinct_reason_remains(top3_database):
    database_url, Session = top3_database
    session = Session()
    row_id = _seed_row(session, 'duplicate-issue-regression', {
        'name': 'Jordan Lee', 'email': 'jordan.lee@com', 'phone': '4155552671',
        'address': '1 Main St',
    })
    contact_id = session.query(ImportContact).filter_by(raw_import_row_id=row_id).one().id
    for description, reason in (
        (None, 'format'),
        ('Invalid email format', 'format'),
        ('Email domain is not accepted', 'domain'),
    ):
        payload = {'field': 'email', 'reason': reason, 'severity': 'error'}
        if description:
            payload['description'] = description
        item = ReviewItem(batch_id='duplicate-issue-regression', item_type='validation', status='pending', payload_json=payload)
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(review_item_id=item.id, subject_type='import_contact_snapshot', subject_id=contact_id))
    session.commit()
    session.close()

    issues = recalculate_row_issues('duplicate-issue-regression', row_id, database_url=database_url)
    descriptions = [issue.get('description') for issue in issues if issue.get('field') == 'email']
    assert 'Issue with email' not in descriptions
    assert 'Invalid email format' in descriptions
    assert 'Email domain is not accepted' in descriptions
    assert len(descriptions) == 2


def test_duplicate_specific_email_issue_is_projected_once(top3_database):
    database_url, Session = top3_database
    session = Session()
    row_id = _seed_row(session, 'duplicate-specific-email', {
        'name': 'Jordan Lee', 'email': 'jordan.lee@com', 'phone': '4155552671',
        'address': '1 Main St',
    })
    contact_id = session.query(ImportContact).filter_by(raw_import_row_id=row_id).one().id
    for description, reason in (
        ('Invalid email format', 'format'),
        ('Issue with email', 'format'),
        ('Email domain is not accepted', 'domain'),
    ):
        item = ReviewItem(
            batch_id='duplicate-specific-email',
            item_type='validation',
            status='pending',
            payload_json={
                'field': 'email',
                'reason': reason,
                'description': description,
                'severity': 'error',
            },
        )
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(
            review_item_id=item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_id,
        ))
    session.commit()
    session.close()

    issues = recalculate_row_issues('duplicate-specific-email', row_id, database_url=database_url)
    descriptions = [issue.get('description') for issue in issues if issue.get('field') == 'email']
    assert descriptions.count('Invalid email format') == 1
    assert 'Email domain is not accepted' in descriptions
    assert len(descriptions) == 2
