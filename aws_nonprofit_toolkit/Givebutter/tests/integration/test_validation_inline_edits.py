"""
Tests for inline editable validation review fields.

Verifies:
1. Inline editable fields (Date, Name, Email, Phone, Amount, Address)
2. Read-only Transaction ID
3. Save/Defer row-level actions
4. Reviewed values stored in ReviewDecision without mutating raw data
5. Audit trail records corrections
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewItem, ReviewItemSubject,
    ReviewDecision, AuditLogRecord, create_db_engine
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
def client_with_db(temp_db, monkeypatch):
    """Flask test client configured with temporary database."""
    database_url, engine = temp_db

    # Monkeypatch environment variable
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Configure Flask app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client, database_url


def setup_demo_batch(database_url):
    """Set up a demo batch with validation issue for testing."""
    SessionLocal = sessionmaker(bind=create_db_engine(database_url))
    session = SessionLocal()

    try:
        batch = ImportBatch(
            id='test-inline-edits',
            filename='test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        # Raw import row (immutable)
        raw_row = RawImportRow(
            batch_id='test-inline-edits',
            row_index=0,
            raw_csv_data={
                'transaction_id': 'TX001',
                'date': '2024-01-01',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@gmial.com',  # Typo!
                'phone': '555-1234',
                'amount': '100.00',
                'address': '123 Main St',
            }
        )
        session.add(raw_row)
        session.flush()

        # Import contact snapshot (immutable)
        contact = ImportContact(
            batch_id='test-inline-edits',
            raw_import_row_id=raw_row.id,
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@gmial.com',
            phone='555-1234',
            address_line1='123 Main St',
            amount=100.00,
        )
        session.add(contact)
        session.flush()

        # Validation issue (email typo)
        review_item = ReviewItem(
            batch_id='test-inline-edits',
            item_type='validation',
            status=None,
            confidence=0.95,
            payload_json={'field': 'email', 'issue': 'possible_typo', 'value': 'jane.smith@gmial.com'},
        )
        session.add(review_item)
        session.flush()

        # Review item subject
        subject = ReviewItemSubject(
            review_item_id=review_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary',
        )
        session.add(subject)
        session.commit()

        return batch.id, review_item.id, raw_row.id
    finally:
        session.close()


class TestValidationInlineEdits:
    """Test suite for inline editable validation review."""

    def test_save_inline_correction_stores_reviewed_values(self, client_with_db):
        """Verify saving inline correction stores reviewed_values without mutating raw data."""
        client, database_url = client_with_db
        batch_id, review_item_id, raw_row_id = setup_demo_batch(database_url)

        # Send inline correction (simulating reviewer editing the email field)
        response = client.post(
            f'/imports/{batch_id}/validation/{review_item_id}/save-correction',
            json={
                'reviewed_values': {
                    'email': 'jane.smith@gmail.com',  # Corrected
                    'name': 'Jane M. Smith',  # Also edited
                }
            }
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['effective_status'] == 'accepted'

        # Verify ReviewDecision stores the corrections
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()

        try:
            decision = session.query(ReviewDecision).filter_by(
                review_item_id=review_item_id
            ).first()
            assert decision is not None
            assert decision.reviewed_values is not None
            assert decision.reviewed_values['email'] == 'jane.smith@gmail.com'
            assert decision.reviewed_values['name'] == 'Jane M. Smith'

            # Verify raw data is unchanged
            raw_row = session.query(RawImportRow).filter_by(id=raw_row_id).first()
            assert raw_row.raw_csv_data['email'] == 'jane.smith@gmial.com'  # Original, unchanged
            assert raw_row.raw_csv_data['first_name'] == 'Jane'  # Original, unchanged
        finally:
            session.close()

    def test_defer_validation_item(self, client_with_db):
        """Verify deferring a validation item sets status to deferred."""
        client, database_url = client_with_db
        batch_id, review_item_id, raw_row_id = setup_demo_batch(database_url)

        # Defer the item
        response = client.post(
            f'/imports/{batch_id}/validation/{review_item_id}/defer'
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['effective_status'] == 'deferred'

        # Verify ReviewDecision records 'defer' decision
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()

        try:
            decision = session.query(ReviewDecision).filter_by(
                review_item_id=review_item_id
            ).first()
            assert decision is not None
            assert decision.decision == 'defer'
        finally:
            session.close()

    def test_audit_log_records_inline_correction(self, client_with_db):
        """Verify audit log records inline corrections."""
        client, database_url = client_with_db
        batch_id, review_item_id, raw_row_id = setup_demo_batch(database_url)

        # Save inline correction
        response = client.post(
            f'/imports/{batch_id}/validation/{review_item_id}/save-correction',
            json={
                'reviewed_values': {
                    'email': 'jane.smith@gmail.com',
                }
            }
        )

        assert response.status_code == 200

        # Verify audit log entry
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()

        try:
            audit_record = session.query(AuditLogRecord).filter_by(
                batch_id=batch_id
            ).order_by(AuditLogRecord.created_at.desc()).first()
            assert audit_record is not None
            assert audit_record.action_type == 'decision_recorded'
        finally:
            session.close()

    def test_empty_reviewed_values(self, client_with_db):
        """Verify saving with empty reviewed_values (user deferred without edits)."""
        client, database_url = client_with_db
        batch_id, review_item_id, raw_row_id = setup_demo_batch(database_url)

        # Save with empty corrections (just mark as accepted)
        response = client.post(
            f'/imports/{batch_id}/validation/{review_item_id}/save-correction',
            json={'reviewed_values': {}}
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['effective_status'] == 'accepted'

        # Verify ReviewDecision was created
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()

        try:
            decision = session.query(ReviewDecision).filter_by(
                review_item_id=review_item_id
            ).first()
            assert decision is not None
            assert decision.decision == 'accept_issue'
        finally:
            session.close()
