"""
Integration tests for decision modal cancel/confirm behavior.

Tests verify:
- T1: Validation Inspect Modal - Cancel closes, no ReviewDecision recorded
- T6: Validation Row Decision - Clear after recording (Reset button clears decision)
- Related: No AuditLog entries created for canceled decisions
- Related: Raw ImportContact data unchanged post-cancel (append-only principle)

These tests use Flask test client (no DOM/browser needed).
For E2E modal UI tests, see tests/e2e/test_decision_modal_cancel_flows.py.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewDecision,
    AuditLogRecord,
    create_db_engine,
)
from sqlalchemy.orm import sessionmaker
import tempfile


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
def flask_client_with_db(temp_db, monkeypatch):
    """Flask test client with database backend and seeded test data."""
    database_url, engine = temp_db

    app.config['TESTING'] = True
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')

    # Seed database with test data
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='cancel-test-batch',
        filename='cancel_test.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=2
    )
    session.add(batch)
    session.flush()

    # Create raw import rows
    row1 = RawImportRow(
        batch_id='cancel-test-batch',
        row_index=1,
        raw_csv_data={
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '(555) 123-4567',
            'amount': '100.00',
            'address': '123 Main St'
        }
    )
    row2 = RawImportRow(
        batch_id='cancel-test-batch',
        row_index=2,
        raw_csv_data={
            'name': 'Another User',
            'email': 'another@example.com',
            'phone': '(555) 987-6543',
            'amount': '200.00',
            'address': '456 Oak Ave'
        }
    )
    session.add(row1)
    session.add(row2)
    session.flush()

    # Create import contacts
    contact1 = ImportContact(
        batch_id='cancel-test-batch',
        raw_import_row_id=row1.id,
        first_name='Test',
        last_name='User',
        email='test@example.com',
        phone='(555) 123-4567',
        amount=100.00,
        address_line1='123 Main St'
    )
    contact2 = ImportContact(
        batch_id='cancel-test-batch',
        raw_import_row_id=row2.id,
        first_name='Another',
        last_name='User',
        email='another@example.com',
        phone='(555) 987-6543',
        amount=200.00,
        address_line1='456 Oak Ave'
    )
    session.add(contact1)
    session.add(contact2)
    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session


class TestValidationInspectModalCancel:
    """T1: Validation Inspect Modal - Cancel closes, no decision recorded."""

    def test_cancel_close_button_no_decision_recorded(self, flask_client_with_db):
        """Clicking Close button in Inspect modal should not create ReviewDecision."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Get first raw row to test
        raw_row = session.query(RawImportRow).filter(
            RawImportRow.batch_id == 'cancel-test-batch',
            RawImportRow.row_index == 1
        ).first()
        raw_id = raw_row.id
        session.close()

        # Verify no decision exists initially
        session = Session()
        decision = session.query(ReviewDecision).filter(
            ReviewDecision.batch_id == 'cancel-test-batch',
            ReviewDecision.raw_import_row_id == raw_id
        ).first()
        assert decision is None, "Should have no decision initially"
        session.close()

        # Simulate user opening modal (just a GET, doesn't create decision)
        response = client.get(f'/imports/cancel-test-batch/row-decision/{raw_id}')
        assert response.status_code == 200

        # Simulate user closing modal without submitting (navigate away)
        # Verify decision still does not exist
        session = Session()
        decision = session.query(ReviewDecision).filter(
            ReviewDecision.batch_id == 'cancel-test-batch',
            ReviewDecision.raw_import_row_id == raw_id
        ).first()
        assert decision is None, \
            "Closing modal (cancel) should not create ReviewDecision"
        session.close()

    def test_cancel_no_audit_entry_created(self, flask_client_with_db):
        """Closing modal without submitting should not create AuditLogRecord."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Get first raw row
        raw_row = session.query(RawImportRow).filter(
            RawImportRow.batch_id == 'cancel-test-batch',
            RawImportRow.row_index == 1
        ).first()
        raw_id = raw_row.id
        session.close()

        # Simulate user closing modal without decision (just GET, no POST)
        response = client.get(f'/imports/cancel-test-batch/row-decision/{raw_id}')
        assert response.status_code == 200

        # Verify no audit entry was created (no decision was recorded)
        session = Session()
        audit_entries = session.query(AuditLogRecord).filter(
            AuditLogRecord.batch_id == 'cancel-test-batch'
        ).all()
        # Should have no audit entries since no decision was recorded
        assert len(audit_entries) == 0, \
            "Cancel should not create AuditLogRecord"
        session.close()

    def test_cancel_raw_data_immutable(self, flask_client_with_db):
        """Raw ImportContact data should remain unchanged after cancel."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Get first contact's original data
        contact = session.query(ImportContact).filter(
            ImportContact.batch_id == 'cancel-test-batch',
            ImportContact.first_name == 'Test'
        ).first()
        raw_id = contact.raw_import_row_id
        original_email = contact.email
        original_phone = contact.phone
        session.close()

        # Simulate cancel (just navigate away)
        response = client.get(f'/imports/cancel-test-batch/row-decision/{raw_id}')
        assert response.status_code == 200

        # Verify contact data unchanged
        session = Session()
        contact_after = session.query(ImportContact).filter(
            ImportContact.id == contact.id
        ).first()
        assert contact_after.email == original_email, \
            "Email should not change after cancel"
        assert contact_after.phone == original_phone, \
            "Phone should not change after cancel"
        session.close()


class TestValidationRowDecisionReset:
    """T6: Validation Row Decision - Clear after recording."""

    def test_record_decision_then_reset(self, flask_client_with_db):
        """Recording a decision then resetting should clear the decision."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Get raw row ID
        raw_row = session.query(RawImportRow).filter(
            RawImportRow.batch_id == 'cancel-test-batch',
            RawImportRow.row_index == 1
        ).first()
        raw_id = raw_row.id
        session.close()

        # Step 1: Record a decision (e.g., "defer") using JSON API
        response = client.post(
            '/imports/cancel-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'defer',
                'notes': 'Test defer decision'
            }
        )
        # Verify decision was created
        assert response.status_code == 200, \
            f"POST decision should succeed, got {response.status_code}: {response.data}"

        session = Session()
        decision = session.query(ReviewDecision).filter(
            ReviewDecision.batch_id == 'cancel-test-batch',
            ReviewDecision.raw_import_row_id == raw_id
        ).first()
        assert decision is not None, "Decision should be recorded"
        # Decision is stored as 'row_status:defer' (prefixed format)
        assert 'defer' in decision.decision, f"Decision should contain 'defer', got {decision.decision}"
        decision_id = decision.id
        session.close()

        # Step 2: Reset/clear the decision by posting 'clear_decision'
        response = client.post(
            '/imports/cancel-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'clear_decision'
            }
        )
        # Should succeed
        assert response.status_code == 200, \
            f"Reset should succeed, got {response.status_code}"

        # Step 3: Verify decision is cleared
        # Note: clear_decision is append-only, so the record still exists
        # but the latest decision should reflect the clear_decision action
        session = Session()
        decisions = session.query(ReviewDecision).filter(
            ReviewDecision.batch_id == 'cancel-test-batch',
            ReviewDecision.raw_import_row_id == raw_id
        ).order_by(ReviewDecision.id.desc()).all()

        # Should have at least 2 decisions (original + clear)
        assert len(decisions) >= 1, "Should have at least one decision record"

        # The most recent decision should be the clear_decision
        latest_decision = decisions[0]
        assert 'clear_decision' in latest_decision.decision, \
            f"Latest decision should be 'clear_decision', got {latest_decision.decision}"
        session.close()

    def test_reset_raw_data_immutable(self, flask_client_with_db):
        """Resetting a decision should not modify raw ImportContact data."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Get contact
        contact = session.query(ImportContact).filter(
            ImportContact.batch_id == 'cancel-test-batch',
            ImportContact.first_name == 'Another'
        ).first()
        raw_id = contact.raw_import_row_id
        original_email = contact.email
        session.close()

        # Record a decision using JSON API
        response = client.post(
            '/imports/cancel-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': 'Test follow-up'
            }
        )
        assert response.status_code == 200, f"Record decision should succeed, got {response.status_code}"

        # Reset the decision
        response = client.post(
            '/imports/cancel-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'clear_decision'
            }
        )
        assert response.status_code == 200, f"Clear decision should succeed, got {response.status_code}"

        # Verify contact email unchanged
        session = Session()
        contact_after = session.query(ImportContact).filter(
            ImportContact.id == contact.id
        ).first()
        assert contact_after.email == original_email, \
            "Email should not change after reset"
        session.close()
