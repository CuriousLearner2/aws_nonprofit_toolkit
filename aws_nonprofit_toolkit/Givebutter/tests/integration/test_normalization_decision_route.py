"""
Integration tests for normalization decision workflow.

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

    # Monkeypatch the normalization_decision_service to use test database
    from scripts.householder import normalization_decision_service
    from scripts.householder.database_write_repository import DatabaseNormalizationDecisionWriter

    def patched_get_writer(config):
        if config and 'GIVEBUTTER_DATABASE_URL' in config:
            return DatabaseNormalizationDecisionWriter(database_url=config['GIVEBUTTER_DATABASE_URL'])
        return DatabaseNormalizationDecisionWriter(database_url=database_url)

    monkeypatch.setattr(normalization_decision_service, '_get_normalization_decision_writer', patched_get_writer)

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

    # Create normalization review item
    normalization_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='normalization',
        status='pending',
        payload_json={
            'field': 'email',
            'raw_value': 'john@example.com',
            'normalized_value': 'john@example.com',
            'basis': 'processor suggestion',
            'confidence': 0.85,
        },
    )
    session.add(normalization_item)
    session.flush()

    # Create subject reference
    subject = ReviewItemSubject(
        review_item_id=normalization_item.id,
        subject_type='import_contact_snapshot',
        subject_id=contact.id,
        role='primary',
    )
    session.add(subject)
    session.flush()

    # Create non-normalization item for error testing
    validation_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='validation',
        status='pending',
        payload_json={'issue_type': 'format-invalid', 'issue_description': 'Invalid email'},
    )
    session.add(validation_item)
    session.commit()

    session.close()

    # Create Flask test client
    with app.test_client() as client:
        yield client, database_url, engine, Session


class TestNormalizationDecisionRoute:
    """Test normalization decision recording via Flask route."""

    def test_valid_decision_creates_review_decision(self, flask_client_with_database):
        """POST decision creates exactly one ReviewDecision."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={
                    'decision': 'accept_normalization',
                    'notes': 'Confirmed typo fix',
                },
            )

            assert response.status_code == 302  # Redirect
            assert '/imports/IMP-2025-0101-A/normalizations' in response.location

            # Verify ReviewDecision created
            decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
            assert decision is not None
            assert decision.decision == 'accept_normalization'
            assert decision.batch_id == 'IMP-2025-0101-A'
            assert decision.review_item_id == item_id

        finally:
            session.close()

    def test_valid_decision_creates_audit_log(self, flask_client_with_database):
        """POST decision creates exactly one AuditLogRecord."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={
                    'decision': 'reject_normalization',
                    'notes': 'Original is correct',
                },
            )

            assert response.status_code == 302

            # Verify AuditLogRecord created
            audit = session.query(AuditLogRecord).filter_by(item_id=item_id).first()
            assert audit is not None
            assert audit.action_type == 'decision_recorded'
            assert audit.batch_id == 'IMP-2025-0101-A'
            assert audit.item_id == item_id
            assert audit.details['decision_value'] == 'reject_normalization'
            assert audit.details['notes'] == 'Original is correct'
            assert audit.details['field'] == 'email'

        finally:
            session.close()

    def test_accept_normalization_decision_recorded(self, flask_client_with_database):
        """accept_normalization decision is recorded with correct value."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
            )

            assert response.status_code == 302

            decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
            assert decision.decision == 'accept_normalization'

        finally:
            session.close()

    def test_reject_normalization_decision_recorded(self, flask_client_with_database):
        """reject_normalization decision is recorded with correct value."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'reject_normalization'},
            )

            assert response.status_code == 302

            decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
            assert decision.decision == 'reject_normalization'

        finally:
            session.close()

    def test_defer_decision_recorded(self, flask_client_with_database):
        """defer decision is recorded with correct value."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'defer'},
            )

            assert response.status_code == 302

            decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
            assert decision.decision == 'defer'

        finally:
            session.close()

    def test_invalid_decision_returns_400(self, flask_client_with_database):
        """Invalid decision value returns HTTP 400."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'invalid_decision'},
            )

            assert response.status_code == 400

        finally:
            session.close()

    def test_wrong_item_type_returns_400(self, flask_client_with_database):
        """Submitting decision for non-normalization item returns 400."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            validation_item = session.query(ReviewItem).filter_by(item_type='validation').first()
            item_id = validation_item.id

            response = client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
            )

            assert response.status_code == 400

        finally:
            session.close()

    def test_unknown_item_returns_400(self, flask_client_with_database):
        """Submitting decision for non-existent item returns 400."""
        client, database_url, engine, Session = flask_client_with_database

        response = client.post(
            f'/imports/IMP-2025-0101-A/normalizations/99999/decision',
            data={'decision': 'accept_normalization'},
        )

        assert response.status_code == 400

    def test_raw_import_rows_unchanged(self, flask_client_with_database):
        """RawImportRow records not mutated by decision."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            # Count before
            count_before = session.query(RawImportRow).count()

            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
            )

            # Count after
            count_after = session.query(RawImportRow).count()
            assert count_before == count_after

        finally:
            session.close()

    def test_import_contacts_unchanged(self, flask_client_with_database):
        """ImportContact records not mutated by decision."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            # Count before
            count_before = session.query(ImportContact).count()

            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
            )

            # Count after
            count_after = session.query(ImportContact).count()
            assert count_before == count_after

        finally:
            session.close()

    def test_review_items_status_unchanged(self, flask_client_with_database):
        """ReviewItem.status not mutated by decision."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id
            original_status = normalization_item.status

            client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
            )

            # Refresh
            updated_item = session.query(ReviewItem).filter_by(id=item_id).first()
            assert updated_item.status == original_status

        finally:
            session.close()

    def test_field_values_stored_in_audit(self, flask_client_with_database):
        """Field/raw/normalized values from payload stored in audit."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
            )

            audit = session.query(AuditLogRecord).filter_by(item_id=item_id).first()
            assert audit.details['field'] == 'email'
            assert audit.details['raw_value'] == 'john@example.com'
            assert audit.details['normalized_value'] == 'john@example.com'

        finally:
            session.close()

    def test_multiple_decisions_allowed(self, flask_client_with_database):
        """Multiple decisions on same item allowed; latest wins."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            # First decision: defer
            client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'defer'},
            )

            # Second decision: accept
            client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
            )

            # Both decisions exist
            decisions = session.query(ReviewDecision).filter_by(review_item_id=item_id).all()
            assert len(decisions) == 2

            # Latest is accept
            latest = session.query(ReviewDecision).filter_by(
                review_item_id=item_id
            ).order_by(ReviewDecision.created_at.desc()).first()
            assert latest.decision == 'accept_normalization'

        finally:
            session.close()

    def test_reviewer_identity_from_header(self, flask_client_with_database):
        """Reviewer identity extracted from X-Reviewer-ID header."""
        client, database_url, engine, Session = flask_client_with_database
        session = Session()

        try:
            normalization_item = session.query(ReviewItem).filter_by(item_type='normalization').first()
            item_id = normalization_item.id

            client.post(
                f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
                data={'decision': 'accept_normalization'},
                headers={'X-Reviewer-ID': 'reviewer@example.com'},
            )

            decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
            assert decision.reviewer == 'reviewer@example.com'

        finally:
            session.close()
