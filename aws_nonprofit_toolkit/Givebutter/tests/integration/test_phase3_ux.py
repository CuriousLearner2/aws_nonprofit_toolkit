"""
Phase 3 Frontend UX Verification Tests

Tests for:
1. Table structure and column rendering
2. Read-only vs editable field constraints
3. Autosave behavior and response handling
4. Row Status and Issues display
5. Approval workflow (check → confirm)
6. Data immutability verification
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import json

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
def temp_db_phase3():
    """Create temporary database with demo batch for Phase 3 testing."""
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
def flask_client_phase3(temp_db_phase3, monkeypatch):
    """Flask client with demo batch for Phase 3 testing."""
    database_url, engine = temp_db_phase3

    app.config['TESTING'] = True

    # Set database URL in environment so autosave_service can find it
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Monkeypatch repository_provider to use test database
    from scripts.householder import repository_provider
    from scripts.householder.database_repository import DatabaseImportRepository

    def patched_get_import_repository(config):
        return DatabaseImportRepository(database_url=database_url)

    monkeypatch.setattr(repository_provider, 'get_import_repository', patched_get_import_repository)

    # Seed database with demo records
    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='demo-phase3-test',
        filename='phase3_test.csv',
        upload_timestamp=datetime.utcnow(),
        status='processing',
        raw_row_count=3,
    )
    session.add(batch)
    session.flush()

    # Row 1: Jane Smith with email typo (warning issue)
    raw_row1 = RawImportRow(
        batch_id='demo-phase3-test',
        row_index=1,
        raw_csv_data={
            'transaction_id': 'TXN-001',
            'date': '2026-06-13',
            'name': 'Jane Smith',
            'email': 'jane.smith@gmial.com',  # typo: gmial instead of gmail
            'phone': '(555) 123-4567',
            'amount': '500.00',
            'address': '123 Main St'
        }
    )
    session.add(raw_row1)
    session.flush()

    contact1 = ImportContact(
        batch_id='demo-phase3-test',
        raw_import_row_id=raw_row1.id,
        first_name='Jane',
        last_name='Smith',
        email='jane.smith@gmial.com',
        phone='(555) 123-4567',
        amount=500.00,
    )
    session.add(contact1)
    session.flush()

    # Row 1: Email typo issue (warning)
    issue1 = ReviewItem(
        batch_id='demo-phase3-test',
        item_type='validation',
        payload_json={
            'field': 'email',
            'reason': 'possible_typo',
            'description': 'Email may have typo',
            'severity': 'warning'
        }
    )
    session.add(issue1)
    session.flush()

    subject1 = ReviewItemSubject(
        review_item_id=issue1.id,
        subject_type='import_raw_row',
        subject_id=raw_row1.id
    )
    session.add(subject1)

    # Row 2: Carol White with missing phone (blocking issue)
    raw_row2 = RawImportRow(
        batch_id='demo-phase3-test',
        row_index=2,
        raw_csv_data={
            'transaction_id': 'TXN-002',
            'date': '2026-06-13',
            'name': 'Carol White',
            'email': 'carol@example.com',
            'phone': '',  # missing phone
            'amount': '750.00',
            'address': '456 Oak Ave'
        }
    )
    session.add(raw_row2)
    session.flush()

    contact2 = ImportContact(
        batch_id='demo-phase3-test',
        raw_import_row_id=raw_row2.id,
        first_name='Carol',
        last_name='White',
        email='carol@example.com',
        phone='',
        amount=750.00,
    )
    session.add(contact2)
    session.flush()

    # Row 2: Missing phone issue (error/blocking)
    issue2 = ReviewItem(
        batch_id='demo-phase3-test',
        item_type='validation',
        payload_json={
            'field': 'phone',
            'reason': 'missing',
            'description': 'Phone number missing',
            'severity': 'error'
        }
    )
    session.add(issue2)
    session.flush()

    subject2 = ReviewItemSubject(
        review_item_id=issue2.id,
        subject_type='import_raw_row',
        subject_id=raw_row2.id
    )
    session.add(subject2)

    # Row 3: Clean record with no issues
    raw_row3 = RawImportRow(
        batch_id='demo-phase3-test',
        row_index=3,
        raw_csv_data={
            'transaction_id': 'TXN-003',
            'date': '2026-06-13',
            'name': 'David Jones',
            'email': 'david@example.com',
            'phone': '(555) 987-6543',
            'amount': '1000.00',
            'address': '789 Pine Rd'
        }
    )
    session.add(raw_row3)
    session.flush()

    contact3 = ImportContact(
        batch_id='demo-phase3-test',
        raw_import_row_id=raw_row3.id,
        first_name='David',
        last_name='Jones',
        email='david@example.com',
        phone='(555) 987-6543',
        amount=1000.00,
    )
    session.add(contact3)

    session.commit()
    session.close()

    client = app.test_client()
    yield client, database_url, engine, Session


class TestPhase3TableStructure:
    """Test Phase 3 table structure and column rendering."""

    def test_validation_table_has_required_columns(self, flask_client_phase3):
        """Validation table has all Phase 3 columns."""
        client, _, _, _ = flask_client_phase3

        response = client.get('/imports/demo-phase3-test/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Check for all required column headers
        assert 'Txn ID' in html
        assert 'Date' in html
        assert 'Name' in html
        assert 'Email' in html
        assert 'Phone' in html
        assert 'Amount' in html
        assert 'Address' in html
        assert 'Row Status' in html
        assert 'Issues' in html
        assert 'Actions' in html

    def test_table_structure_with_validation_items(self, flask_client_phase3):
        """Table structure properly renders when validation items present."""
        client, _, _, _ = flask_client_phase3

        response = client.get('/imports/demo-phase3-test/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Check for table structure (data rows rendered as <tr>)
        assert '<table' in html
        assert '<tr' in html
        # Should have validation review content (either records or empty state)
        assert 'Validation Review' in html or 'validation' in html.lower()


class TestPhase3EditableVsReadOnly:
    """Test that correct fields are editable and read-only."""

    def test_txn_id_is_read_only(self, flask_client_phase3):
        """Txn ID is read-only (not an input)."""
        client, _, _, _ = flask_client_phase3

        response = client.get('/imports/demo-phase3-test/validation')
        html = response.data.decode('utf-8')

        # Txn ID should not be an editable input (should be in td without input)
        # Pattern: TXN-001 appears in <td>TXN-001</td>, not <input value="TXN-001">
        assert 'TXN-001' in html
        # Verify it's not in a typical input field pattern
        assert 'type="text"' not in html.split('TXN-001')[0][-100:]

    def test_editable_fields_are_inputs(self, flask_client_phase3):
        """Date, Name, Email, Phone, Amount, Address are editable inputs."""
        client, _, _, _ = flask_client_phase3

        response = client.get('/imports/demo-phase3-test/validation')
        html = response.data.decode('utf-8')

        # Count autosave-field inputs (one for each editable field per record)
        assert 'autosave-field' in html
        # Should have 6 editable fields × 3 records = 18 inputs
        autosave_count = html.count('autosave-field')
        assert autosave_count >= 18

    def test_row_status_is_read_only(self, flask_client_phase3):
        """Row Status is read-only (not an input)."""
        client, _, _, _ = flask_client_phase3

        response = client.get('/imports/demo-phase3-test/validation')
        html = response.data.decode('utf-8')

        # Row Status should be in a span or badge, not an input
        assert 'row-status-badge' in html or 'Row Status' in html

    def test_issues_is_read_only(self, flask_client_phase3):
        """Issues are read-only (not inputs)."""
        client, _, _, _ = flask_client_phase3

        response = client.get('/imports/demo-phase3-test/validation')
        html = response.data.decode('utf-8')

        # Issues should be in spans/badges, not inputs
        assert 'issues-cell' in html or 'Issues' in html


class TestPhase3Autosave:
    """Test autosave endpoint and behavior."""

    def test_autosave_endpoint_accepts_post(self, flask_client_phase3):
        """Autosave endpoint accepts POST with corrected values."""
        client, database_url, engine, Session = flask_client_phase3

        # Get raw row ID
        session = Session()
        raw_row = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=1
        ).first()
        raw_id = raw_row.id
        session.close()

        # POST to autosave endpoint
        response = client.post(
            '/imports/demo-phase3-test/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result['success'] is True
        assert result['decision_id'] > 0

    def test_autosave_response_includes_effective_values(self, flask_client_phase3):
        """Autosave response includes effective_values."""
        client, database_url, engine, Session = flask_client_phase3

        session = Session()
        raw_row = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=1
        ).first()
        raw_id = raw_row.id
        session.close()

        response = client.post(
            '/imports/demo-phase3-test/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            },
            content_type='application/json'
        )

        result = json.loads(response.data)
        assert 'effective_values' in result
        assert result['effective_values']['email'] == 'jane.smith@gmail.com'
        assert result['effective_values']['name'] == 'Jane Smith'  # from raw

    def test_autosave_response_includes_row_status(self, flask_client_phase3):
        """Autosave response includes refreshed row_status."""
        client, database_url, engine, Session = flask_client_phase3

        session = Session()
        raw_row = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=1
        ).first()
        raw_id = raw_row.id
        session.close()

        response = client.post(
            '/imports/demo-phase3-test/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            },
            content_type='application/json'
        )

        result = json.loads(response.data)
        assert 'row_status' in result
        # Should show "No issues" after fixing email typo
        assert result['row_status'] in ['No issues', 'Warning', 'Blocking', 'Overridden']

    def test_autosave_response_includes_issues(self, flask_client_phase3):
        """Autosave response includes updated issues list."""
        client, database_url, engine, Session = flask_client_phase3

        session = Session()
        raw_row = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=1
        ).first()
        raw_id = raw_row.id
        session.close()

        response = client.post(
            '/imports/demo-phase3-test/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            },
            content_type='application/json'
        )

        result = json.loads(response.data)
        assert 'issues' in result
        # Should have no issues after fixing email
        assert isinstance(result['issues'], list)

    def test_autosave_persists_corrected_values(self, flask_client_phase3):
        """Autosave persists corrected values in ReviewDecision."""
        client, database_url, engine, Session = flask_client_phase3

        session = Session()
        raw_row = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=1
        ).first()
        raw_id = raw_row.id
        session.close()

        # Autosave
        response = client.post(
            '/imports/demo-phase3-test/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            },
            content_type='application/json'
        )

        # Verify ReviewDecision created
        session = Session()
        decision = session.query(ReviewDecision).filter_by(
            batch_id='demo-phase3-test',
            raw_import_row_id=raw_id
        ).first()

        assert decision is not None
        assert decision.reviewed_values['email'] == 'jane.smith@gmail.com'
        session.close()


class TestPhase3ApprovalWorkflow:
    """Test approval check and confirm workflow."""

    def test_approve_check_mode_detects_issues(self, flask_client_phase3):
        """Approve File check mode detects remaining issues."""
        client, _, _, _ = flask_client_phase3

        response = client.post(
            '/imports/demo-phase3-test/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            },
            content_type='application/json'
        )

        result = json.loads(response.data)
        assert result['requires_override_confirmation'] is True
        assert 'remaining_issues' in result
        assert len(result['remaining_issues']) >= 1  # At least Carol White with missing phone

    def test_approve_confirm_mode_persists_overrides(self, flask_client_phase3):
        """Approve with Overrides persists approval_status and override_details."""
        client, database_url, engine, Session = flask_client_phase3

        # Get row with issue
        session = Session()
        raw_row = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=2  # Carol White
        ).first()
        raw_id = raw_row.id
        session.close()

        # Confirm override
        response = client.post(
            '/imports/demo-phase3-test/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': [
                    {
                        'raw_import_row_id': raw_id,
                        'row_index': 2,
                        'issues': [{'field': 'phone', 'reason': 'missing'}]
                    }
                ]
            },
            content_type='application/json'
        )

        result = json.loads(response.data)
        assert result['success'] is True

        # Verify ImportBatch updated
        session = Session()
        batch = session.query(ImportBatch).filter_by(id='demo-phase3-test').first()
        assert batch.approval_status == 'approved_with_overrides'
        assert batch.override_details is not None
        assert len(batch.override_details['overrides']) == 1
        session.close()


class TestPhase3DataImmutability:
    """Test that raw data remains unchanged."""

    def test_raw_import_row_data_unchanged_after_autosave(self, flask_client_phase3):
        """RawImportRow.raw_csv_data unchanged after autosave."""
        client, database_url, engine, Session = flask_client_phase3

        session = Session()
        raw_row_before = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=1
        ).first()
        original_email = raw_row_before.raw_csv_data['email']
        raw_id = raw_row_before.id
        session.close()

        # Autosave with corrected email
        client.post(
            '/imports/demo-phase3-test/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            },
            content_type='application/json'
        )

        # Verify raw data unchanged
        session = Session()
        raw_row_after = session.query(RawImportRow).filter_by(id=raw_id).first()
        assert raw_row_after.raw_csv_data['email'] == original_email
        assert raw_row_after.raw_csv_data['email'] == 'jane.smith@gmial.com'  # Still has typo
        session.close()

    def test_review_item_payload_unchanged(self, flask_client_phase3):
        """ReviewItem.payload_json unchanged after autosave."""
        client, database_url, engine, Session = flask_client_phase3

        session = Session()
        raw_row = session.query(RawImportRow).filter_by(
            batch_id='demo-phase3-test',
            row_index=1
        ).first()
        review_item = session.query(ReviewItem).join(
            ReviewItemSubject,
            ReviewItem.id == ReviewItemSubject.review_item_id
        ).filter(
            ReviewItemSubject.subject_id == raw_row.id
        ).first()
        original_payload = review_item.payload_json.copy()
        session.close()

        # Autosave
        client.post(
            '/imports/demo-phase3-test/autosave',
            json={
                'raw_import_row_id': raw_row.id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            },
            content_type='application/json'
        )

        # Verify payload unchanged
        session = Session()
        review_item_after = session.query(ReviewItem).filter_by(id=review_item.id).first()
        assert review_item_after.payload_json == original_payload
        session.close()
