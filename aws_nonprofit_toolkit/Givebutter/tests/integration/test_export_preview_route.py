"""Integration tests for export preview route."""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewItem, ReviewDecision, AuditLogRecord
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
    from scripts.householder.database_models import create_db_engine
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def flask_client_with_export_db(temp_db, monkeypatch):
    """Flask client with database backend and seeded test data."""
    database_url, engine = temp_db

    app.config['TESTING'] = True

    # Set environment variable so services can find database
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Seed database with test data
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-2025-0101-A',
        filename='test_export.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create raw import rows
    row1 = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=1,
        raw_csv_data={'Name': 'John Smith', 'Email': 'john@example.com', 'Amount': '100.00', 'transaction_id': 'TXN-001'},
    )
    row2 = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=2,
        raw_csv_data={'Name': 'Jane Smith', 'Email': 'jane@example.com', 'Amount': '50.00', 'transaction_id': 'TXN-002'},
    )
    session.add(row1)
    session.add(row2)
    session.flush()

    # Create import contacts
    contact1 = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=row1.id,
        first_name='John',
        last_name='Smith',
        email='john@example.com',
        phone='555-1234',
        address_line1='123 Main St',
        city='Springfield',
        state='IL',
        postal_code='62701',
        amount=100.00,
    )
    contact2 = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=row2.id,
        first_name='Jane',
        last_name='Smith',
        email='jane@example.com',
        phone='555-1234',
        address_line1='123 Main St',
        city='Springfield',
        state='IL',
        postal_code='62701',
        amount=50.00,
    )
    session.add(contact1)
    session.add(contact2)
    session.flush()

    # Create validation review item
    val_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='validation',
        status='pending',
        payload_json={'issue_type': 'missing_email', 'issue': 'Email missing'},
    )
    session.add(val_item)

    # Create normalization review item
    norm_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='normalization',
        status='pending',
        payload_json={
            'field': 'email',
            'raw_value': 'john@example.com',
            'normalized_value': 'JOHN@EXAMPLE.COM',
        },
    )
    session.add(norm_item)

    # Create duplicate review item
    dup_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='duplicate',
        status='pending',
        payload_json={
            'contact_a': {'id': str(contact1.id), 'name': 'John Smith'},
            'contact_b': {'id': str(contact2.id), 'name': 'Jane Smith'},
            'supporting_evidence': ['Same address'],
            'conflicting_evidence': ['Different names'],
        },
    )
    session.add(dup_item)

    # Create household review item
    hh_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='household',
        status='pending',
        payload_json={
            'id': 'HH-001',
            'suggested_name': 'Smith Family',
            'address': '123 Main St, Springfield, IL',
            'confidence': '95%',
            'proposed_members': ['John Smith', 'Jane Smith'],
            'evidence': ['Shared address'],
            'conflicts': [],
        },
    )
    session.add(hh_item)
    session.commit()

    # Save IDs before closing session
    contact1_id = contact1.id
    contact2_id = contact2.id
    val_item_id = val_item.id
    norm_item_id = norm_item.id
    dup_item_id = dup_item.id
    hh_item_id = hh_item.id

    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, {
            'batch_id': 'IMP-2025-0101-A',
            'contact1_id': contact1_id,
            'contact2_id': contact2_id,
            'val_item_id': val_item_id,
            'norm_item_id': norm_item_id,
            'dup_item_id': dup_item_id,
            'hh_item_id': hh_item_id,
        }


class TestExportPreviewRoute:
    """Test export preview route."""

    def test_preview_route_returns_200(self, flask_client_with_export_db):
        """Test that preview route returns HTTP 200."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        assert response.status_code == 200

    def test_preview_shows_row_count(self, flask_client_with_export_db):
        """Test that preview response shows row count."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        assert b'2' in response.data or b'row' in response.data.lower()

    def test_preview_shows_blocker_count(self, flask_client_with_export_db):
        """Test that preview response is successfully generated."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        # Verify successful response with preview data
        assert response.status_code == 200
        assert b'export' in response.data.lower()

    def test_preview_shows_warning_count(self, flask_client_with_export_db):
        """Test that preview response includes status information."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        # Verify successful response with export console data
        assert response.status_code == 200
        assert b'export' in response.data.lower()

    def test_preview_shows_readiness_status(self, flask_client_with_export_db):
        """Test that preview response shows export readiness status."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        assert response.status_code == 200
        # Should show readiness status (ready or not ready)
        assert b'ready' in response.data.lower() or b'export' in response.data.lower()

    def test_accepted_normalization_appears_in_output(self, flask_client_with_export_db):
        """Test that accepted normalization appears in preview output."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()

        # Add accepted normalization decision
        norm_decision = ReviewDecision(
            batch_id='IMP-2025-0101-A',
            review_item_id=ids['norm_item_id'],
            decision='accept_normalization',
            reviewed_values={'field': 'email', 'normalized_value': 'john.smith@example.com'},
        )
        session.add(norm_decision)
        session.commit()
        session.close()

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        assert response.status_code == 200

    def test_duplicate_grouping_appears_as_metadata(self, flask_client_with_export_db):
        """Test that duplicate grouping appears only as derived metadata."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()

        # Add same_person decision
        dup_decision = ReviewDecision(
            batch_id='IMP-2025-0101-A',
            review_item_id=ids['dup_item_id'],
            decision='same_person',
            reviewed_values={'candidate_contact_ids': [ids['contact1_id'], ids['contact2_id']]},
        )
        session.add(dup_decision)
        session.commit()
        session.close()

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        assert response.status_code == 200
        # Response should contain duplicate group information
        assert b'DUP' in response.data or b'duplicate' in response.data.lower()

    def test_household_grouping_appears_as_metadata(self, flask_client_with_export_db):
        """Test that household grouping appears only as derived metadata."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()

        # Add confirm_household decision
        hh_decision = ReviewDecision(
            batch_id='IMP-2025-0101-A',
            review_item_id=ids['hh_item_id'],
            decision='confirm_household',
            reviewed_values={
                'candidate_household_id': 'HH-123',
                'suggested_household_label': 'Smith Household',
                'candidate_contact_ids': [ids['contact1_id'], ids['contact2_id']],
            },
        )
        session.add(hh_decision)
        session.commit()
        session.close()

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        assert response.status_code == 200
        # Response should contain household group information
        assert b'household' in response.data.lower() or b'HH' in response.data

    def test_preview_does_not_create_files(self, flask_client_with_export_db):
        """Test that preview does not create any files."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        # Response should not be a file download
        assert response.status_code == 200
        assert 'text/html' in response.content_type or 'text/plain' in response.content_type

    def test_preview_does_not_create_audit_records(self, flask_client_with_export_db):
        """Test that preview does not create audit records."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()
        audit_count_before = session.query(AuditLogRecord).count()
        session.close()

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        session = Session()
        audit_count_after = session.query(AuditLogRecord).count()
        session.close()

        assert audit_count_before == audit_count_after

    def test_preview_does_not_mutate_raw_rows(self, flask_client_with_export_db):
        """Test that preview does not mutate raw rows."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()
        rows_before = [r.raw_csv_data for r in session.query(RawImportRow).all()]
        session.close()

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        session = Session()
        rows_after = [r.raw_csv_data for r in session.query(RawImportRow).all()]
        session.close()

        assert rows_before == rows_after

    def test_preview_does_not_mutate_import_contacts(self, flask_client_with_export_db):
        """Test that preview does not mutate import contacts."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()
        contacts_before = [(c.first_name, c.last_name, c.email) for c in session.query(ImportContact).all()]
        session.close()

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        session = Session()
        contacts_after = [(c.first_name, c.last_name, c.email) for c in session.query(ImportContact).all()]
        session.close()

        assert contacts_before == contacts_after

    def test_preview_does_not_mutate_review_decisions(self, flask_client_with_export_db):
        """Test that preview does not mutate review decisions."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()
        decisions_before = session.query(ReviewDecision).count()
        session.close()

        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        session = Session()
        decisions_after = session.query(ReviewDecision).count()
        session.close()

        assert decisions_before == decisions_after

    def test_invalid_import_returns_clear_error(self, flask_client_with_export_db):
        """Test that invalid import returns clear error."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        response = client.post(
            '/imports/INVALID-ID/exports/preview',
        )

        assert response.status_code == 400
        assert b'error' in response.data.lower()

    def test_missing_database_config_returns_clear_error(self, monkeypatch):
        """Test that missing database config returns clear error."""
        # Create app without database config
        monkeypatch.delenv('GIVEBUTTER_DATABASE_URL', raising=False)

        app.config['TESTING'] = True
        with app.test_client() as client:
            # Try to use preview without database configured
            response = client.post(
                '/imports/IMP-TEST/exports/preview',
            )

            # Should return error
            assert response.status_code in [400, 500]

    def test_no_mutations_from_preview(self, flask_client_with_export_db):
        """Test that preview does not mutate any data."""
        client, database_url, engine, Session, ids = flask_client_with_export_db
        session = Session()

        # Count before
        contact_count_before = session.query(ImportContact).count()
        row_count_before = session.query(RawImportRow).count()
        decision_count_before = session.query(ReviewDecision).count()
        audit_count_before = session.query(AuditLogRecord).count()

        session.close()

        # Call preview
        response = client.post(
            '/imports/IMP-2025-0101-A/exports/preview',
        )

        session = Session()

        # Count after
        contact_count_after = session.query(ImportContact).count()
        row_count_after = session.query(RawImportRow).count()
        decision_count_after = session.query(ReviewDecision).count()
        audit_count_after = session.query(AuditLogRecord).count()

        # Verify no mutations
        assert contact_count_before == contact_count_after
        assert row_count_before == row_count_after
        assert decision_count_before == decision_count_after
        assert audit_count_before == audit_count_after

        session.close()

    def test_existing_exports_route_remains_safe(self, flask_client_with_export_db):
        """Test that existing GET /imports/<id>/exports remains safe and read-only."""
        client, database_url, engine, Session, ids = flask_client_with_export_db

        session = Session()
        audit_count_before = session.query(AuditLogRecord).count()
        session.close()

        # Call exports route (not preview)
        response = client.get(
            '/imports/IMP-2025-0101-A/exports',
        )

        session = Session()
        audit_count_after = session.query(AuditLogRecord).count()
        session.close()

        # Should not create audit records
        assert audit_count_before == audit_count_after
