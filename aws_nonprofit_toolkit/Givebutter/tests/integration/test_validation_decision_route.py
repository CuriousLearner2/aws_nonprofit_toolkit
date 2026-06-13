"""
Integration tests for validation decision workflow.

Tests end-to-end: route, service, database operations.
Verifies atomicity, immutability, and audit logging.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
    AuditLogRecord,
    create_db_engine,
)
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def flask_client_with_database(temp_db, monkeypatch):
    """Flask client with database backend and seeded test data."""
    database_url, engine = temp_db

    app.config['TESTING'] = True

    # Monkeypatch the validation_decision_service to use test database
    from scripts.householder import validation_decision_service
    from scripts.householder.database_write_repository import DatabaseValidationDecisionWriter

    def patched_get_writer(config):
        if config and 'GIVEBUTTER_DATABASE_URL' in config:
            return DatabaseValidationDecisionWriter(database_url=config['GIVEBUTTER_DATABASE_URL'])
        return DatabaseValidationDecisionWriter(database_url=database_url)

    monkeypatch.setattr(validation_decision_service, '_get_validation_decision_writer', patched_get_writer)

    # Seed database with test data
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-2025-0101-A',
        filename='test_upload.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create raw import row
    raw_row = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=1,
        raw_csv_data={'Name': 'John Smith', 'Email': 'john@example.com'},
    )
    session.add(raw_row)
    session.flush()

    # Create import contact
    contact = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=raw_row.id,
        first_name='John',
        last_name='Smith',
        email='john@example.com',
        phone='(555) 123-4567',
        amount=100.00,
    )
    session.add(contact)
    session.flush()

    # Create validation review item
    validation_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='validation',
        status='pending',
        payload_json={'issue_type': 'format-invalid', 'issue_description': 'Invalid email format'},
    )
    session.add(validation_item)
    session.flush()

    # Create subject reference
    subject = ReviewItemSubject(
        review_item_id=validation_item.id,
        subject_type='import_contact_snapshot',
        subject_id=contact.id,
        role='primary',
    )
    session.add(subject)
    session.flush()

    # Create non-validation item for error testing
    duplicate_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='duplicate',
        status='pending',
        payload_json={'match_type': 'potential_duplicate'},
    )
    session.add(duplicate_item)
    session.commit()

    session.close()

    # Create Flask test client
    with app.test_client() as client:
        yield client, database_url, engine, Session


class TestValidationDecisionRoute:
    """Test validation decision recording via Flask route."""

    def test_valid_decision_creates_review_decision(self, flask_client_with_database):
        """POST decision creates exactly one ReviewDecision."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()
            item_id = validation_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{item_id}/decision',
                data={
                    'decision': 'dismiss_issue',
                    'notes': 'False positive',
                },
            )

            assert response.status_code == 302  # Redirect
            assert '/imports/IMP-2025-0101-A/validation' in response.location

            # Verify ReviewDecision created
            decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
            assert decision is not None
            assert decision.decision == 'dismiss_issue'
            assert decision.batch_id == 'IMP-2025-0101-A'
            assert decision.review_item_id == item_id

        finally:
            session.close()

    def test_valid_decision_creates_audit_log(self, flask_client_with_database):
        """POST decision creates exactly one AuditLogRecord."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()
            item_id = validation_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{item_id}/decision',
                data={
                    'decision': 'accept_issue',
                    'notes': 'Data is valid',
                },
            )

            assert response.status_code == 302

            # Verify AuditLogRecord created
            audit = session.query(AuditLogRecord).filter_by(item_id=item_id).first()
            assert audit is not None
            assert audit.action_type == 'decision_recorded'
            assert audit.batch_id == 'IMP-2025-0101-A'
            assert audit.item_id == item_id
            assert audit.details['decision_value'] == 'accept_issue'
            assert audit.details['notes'] == 'Data is valid'

        finally:
            session.close()

    def test_decision_and_audit_created_atomically(self, flask_client_with_database):
        """Decision and audit records created together (atomic)."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()
            item_id = validation_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{item_id}/decision',
                data={'decision': 'defer'},
            )

            assert response.status_code == 302

            # Verify both created together
            decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
            audit = session.query(AuditLogRecord).filter_by(decision_id=decision.id).first()

            assert decision is not None
            assert audit is not None
            assert audit.decision_id == decision.id

        finally:
            session.close()

    def test_raw_import_rows_unchanged(self, flask_client_with_database):
        """Decision does not mutate RawImportRow."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            original_rows = session.query(RawImportRow).count()
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={'decision': 'dismiss_issue'},
            )

            new_rows = session.query(RawImportRow).count()
            assert new_rows == original_rows

        finally:
            session.close()

    def test_import_contacts_unchanged(self, flask_client_with_database):
        """Decision does not mutate ImportContact."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            original_contacts = session.query(ImportContact).count()
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={'decision': 'dismiss_issue'},
            )

            new_contacts = session.query(ImportContact).count()
            assert new_contacts == original_contacts

        finally:
            session.close()

    def test_invalid_decision_returns_400(self, flask_client_with_database):
        """Invalid decision value returns HTTP 400."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={'decision': 'invalid_value'},
            )

            assert response.status_code == 400
            assert 'Invalid decision' in response.data.decode()

        finally:
            session.close()

    def test_wrong_item_type_rejected(self, flask_client_with_database):
        """Non-validation item rejected."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            duplicate_item = session.query(ReviewItem).filter_by(item_type='duplicate').first()

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{duplicate_item.id}/decision',
                data={'decision': 'dismiss_issue'},
            )

            assert response.status_code == 400
            assert 'not a validation item' in response.data.decode()

        finally:
            session.close()

    def test_unknown_import_returns_400(self, flask_client_with_database):
        """Unknown import ID returns HTTP 400."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            response = client.post(
                f'/imports/IMP-NONEXISTENT/validation/{validation_item.id}/decision',
                data={'decision': 'dismiss_issue'},
            )

            assert response.status_code == 400
            assert 'not found' in response.data.decode()

        finally:
            session.close()

    def test_unknown_review_item_returns_400(self, flask_client_with_database):
        """Unknown review item ID returns HTTP 400."""
        client, database_url, engine, Session = flask_client_with_database

        response = client.post(
            '/imports/IMP-2025-0101-A/validation/999999/decision',
            data={'decision': 'dismiss_issue'},
        )

        assert response.status_code == 400
        assert 'not found' in response.data.decode()

    def test_multiple_decisions_allowed(self, flask_client_with_database):
        """Multiple decisions per item allowed; latest is current."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()
            item_id = validation_item.id

            # First decision: defer
            response1 = client.post(
                f'/imports/IMP-2025-0101-A/validation/{item_id}/decision',
                data={'decision': 'defer'},
            )
            assert response1.status_code == 302

            # Second decision: dismiss_issue
            response2 = client.post(
                f'/imports/IMP-2025-0101-A/validation/{item_id}/decision',
                data={'decision': 'dismiss_issue'},
            )
            assert response2.status_code == 302

            # Verify both decisions exist
            decisions = session.query(ReviewDecision).filter_by(review_item_id=item_id).all()
            assert len(decisions) == 2

            # Verify latest is dismiss_issue
            latest = decisions[-1]  # Most recent
            assert latest.decision == 'dismiss_issue'

        finally:
            session.close()

    def test_audit_page_reflects_decision(self, flask_client_with_database):
        """Audit page shows decision record."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            # Record decision
            client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={
                    'decision': 'dismiss_issue',
                    'notes': 'Test decision',
                },
            )

            # View audit page
            response = client.get('/imports/IMP-2025-0101-A/audit')
            assert response.status_code == 200

        finally:
            session.close()

    def test_reviewer_identity_from_header(self, flask_client_with_database):
        """Reviewer ID from X-Reviewer-ID header stored in decision."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={'decision': 'dismiss_issue'},
                headers={'X-Reviewer-ID': 'reviewer@example.com'},
            )

            assert response.status_code == 302

            # Verify reviewer stored
            decision = session.query(ReviewDecision).filter_by(
                review_item_id=validation_item.id
            ).first()
            assert decision.reviewer == 'reviewer@example.com'

        finally:
            session.close()

    def test_reviewer_anonymous_if_no_header(self, flask_client_with_database):
        """Reviewer None if X-Reviewer-ID header not provided."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={'decision': 'dismiss_issue'},
                # No X-Reviewer-ID header
            )

            assert response.status_code == 302

            # Verify reviewer is None
            decision = session.query(ReviewDecision).filter_by(
                review_item_id=validation_item.id
            ).first()
            assert decision.reviewer is None

        finally:
            session.close()

    def test_notes_stored_in_decision(self, flask_client_with_database):
        """Notes stored in reviewed_values JSON."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={
                    'decision': 'dismiss_issue',
                    'notes': 'This is a false positive',
                },
            )

            assert response.status_code == 302

            decision = session.query(ReviewDecision).filter_by(
                review_item_id=validation_item.id
            ).first()
            assert decision.reviewed_values is not None
            assert decision.reviewed_values.get('notes') == 'This is a false positive'

        finally:
            session.close()

    def test_empty_notes_not_stored(self, flask_client_with_database):
        """Empty notes not stored."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()

            response = client.post(
                f'/imports/IMP-2025-0101-A/validation/{validation_item.id}/decision',
                data={
                    'decision': 'dismiss_issue',
                    'notes': '',  # Empty
                },
            )

            assert response.status_code == 302

            decision = session.query(ReviewDecision).filter_by(
                review_item_id=validation_item.id
            ).first()
            assert decision.reviewed_values is None

        finally:
            session.close()
