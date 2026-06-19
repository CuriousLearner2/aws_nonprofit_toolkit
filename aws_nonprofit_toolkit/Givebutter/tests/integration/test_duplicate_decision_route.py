"""Integration tests for duplicate decision route."""

import pytest
import sys
from pathlib import Path
from datetime import datetime

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
def flask_client_with_db(temp_db, monkeypatch):
    """Flask client with database backend and seeded test data."""
    database_url, engine = temp_db

    app.config['TESTING'] = True

    # IMPORTANT: Configure environment for database mode
    # This ensures all services use the test database
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Monkeypatch the duplicate_decision_service to use test database
    from scripts.householder import duplicate_decision_service
    from scripts.householder.database_write_repository import DatabaseDuplicateDecisionWriter

    def patched_get_writer(config):
        return DatabaseDuplicateDecisionWriter(database_url=database_url)

    monkeypatch.setattr(duplicate_decision_service, '_get_duplicate_decision_writer', patched_get_writer)

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

    # Create raw import rows
    row1 = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=1,
        raw_csv_data={'Name': 'John Smith', 'Email': 'john@example.com'},
    )
    row2 = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=2,
        raw_csv_data={'Name': 'Jon Smith', 'Email': 'jon@example.com'},
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
    )
    contact2 = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=row2.id,
        first_name='Jon',
        last_name='Smith',
        email='jon@example.com',
        phone='555-1234',
    )
    session.add(contact1)
    session.add(contact2)
    session.flush()

    # Create duplicate review item WITH conflicting evidence
    duplicate_payload = {
        'contact_a': {'id': str(contact1.id), 'name': 'John Smith'},
        'contact_b': {'id': str(contact2.id), 'name': 'Jon Smith'},
        'supporting_evidence': ['Same phone'],
        'conflicting_evidence': ['Different name'],
    }

    dup_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='duplicate',
        status='pending',
        payload_json=duplicate_payload,
    )
    session.add(dup_item)

    # Create duplicate review item WITHOUT conflicting evidence
    duplicate_payload_clean = {
        'contact_a': {'id': str(contact1.id), 'name': 'John Smith'},
        'contact_b': {'id': str(contact2.id), 'name': 'John Smith'},
        'supporting_evidence': ['Same phone', 'Same name'],
        'conflicting_evidence': [],
    }

    dup_item_clean = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='duplicate',
        status='pending',
        payload_json=duplicate_payload_clean,
    )
    session.add(dup_item_clean)

    # Create validation item for error testing
    val_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='validation',
        status='pending',
        payload_json={'issue': 'test'},
    )
    session.add(val_item)
    session.commit()

    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session


class TestDuplicateDecisionRoute:
    """Test duplicate decision POST route."""

    def test_valid_decision_creates_review_decision(self, flask_client_with_db):
        """Test that valid decision creates ReviewDecision record."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        dup_item = session.query(ReviewItem).filter(
            ReviewItem.item_type == 'duplicate'
        ).first()
        item_id = dup_item.id
        session.close()

        response = client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'same_person',
                'notes': 'Test decision',  # Required due to conflicting evidence
            },
        )

        assert response.status_code == 302

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'same_person'
        session.close()

    def test_valid_decision_creates_audit_log(self, flask_client_with_db):
        """Test that valid decision creates AuditLogRecord."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        dup_item = session.query(ReviewItem).filter(
            ReviewItem.item_type == 'duplicate'
        ).first()
        item_id = dup_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'different_people',
                'notes': 'Test decision',  # Required due to conflicting evidence
            },
        )

        session = Session()
        audit = session.query(AuditLogRecord).filter_by(item_id=item_id).first()
        assert audit is not None
        assert audit.action_type == 'decision_recorded'
        session.close()

    def test_same_person_decision_recorded(self, flask_client_with_db):
        """Test that same_person decision is recorded."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'same_person',
                'notes': 'Test decision',  # Required due to conflicting evidence
            },
        )

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision.decision == 'same_person'
        session.close()

    def test_different_people_decision_recorded(self, flask_client_with_db):
        """Test that different_people decision is recorded."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'different_people',
                'notes': 'Test decision',  # Required due to conflicting evidence
            },
        )

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision.decision == 'different_people'
        session.close()

    def test_defer_decision_recorded(self, flask_client_with_db):
        """Test that defer decision is recorded."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'defer',
                'notes': 'Test decision',  # Required due to conflicting evidence
            },
        )

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision.decision == 'defer'
        session.close()

    def test_invalid_decision_returns_400(self, flask_client_with_db):
        """Test that invalid decision returns 400."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        session.close()

        response = client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={'decision': 'invalid'},
        )

        assert response.status_code == 400

    def test_wrong_item_type_returns_400(self, flask_client_with_db):
        """Test that wrong item type returns 400."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        val_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'validation').first()
        item_id = val_item.id
        session.close()

        response = client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={'decision': 'same_person'},
        )

        assert response.status_code == 400

    def test_raw_import_rows_unchanged(self, flask_client_with_db):
        """Test that raw import rows are not modified."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        before = session.query(RawImportRow).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={'decision': 'same_person'},
        )

        session = Session()
        after = session.query(RawImportRow).count()
        assert before == after
        session.close()

    def test_import_contacts_unchanged(self, flask_client_with_db):
        """Test that import contacts are not modified."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        before = session.query(ImportContact).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={'decision': 'same_person'},
        )

        session = Session()
        after = session.query(ImportContact).count()
        assert before == after
        session.close()

    def test_no_contacts_created_deleted_mutated(self, flask_client_with_db):
        """Test that no contacts are created or deleted."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        before_count = session.query(ImportContact).count()
        before_names = [(c.first_name, c.last_name) for c in session.query(ImportContact).all()]
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={'decision': 'same_person'},
        )

        session = Session()
        after_count = session.query(ImportContact).count()
        after_names = [(c.first_name, c.last_name) for c in session.query(ImportContact).all()]
        assert before_count == after_count
        assert before_names == after_names
        session.close()

    def test_notes_required_when_conflicting_evidence_present(self, flask_client_with_db):
        """Test that notes are required when conflicting evidence exists (Bug #1)."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Get duplicate item which has conflicting_evidence
        dup_item = session.query(ReviewItem).filter(
            ReviewItem.item_type == 'duplicate'
        ).first()
        item_id = dup_item.id

        # Verify the item has conflicting evidence
        assert len(dup_item.payload_json.get('conflicting_evidence', [])) > 0
        session.close()

        # Submit decision WITHOUT notes - should be rejected (400)
        response = client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'same_person',
                'notes': '',  # Empty notes
            },
        )

        # Should return 400 error
        assert response.status_code == 400, f"Expected 400 but got {response.status_code}"

        # Verify no decision was recorded
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is None, "Decision should not be recorded when notes are missing"
        session.close()

    def test_notes_persisted_in_decision_when_required(self, flask_client_with_db):
        """Test that notes are persisted in ReviewDecision when conflicting evidence exists."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        dup_item = session.query(ReviewItem).filter(
            ReviewItem.item_type == 'duplicate'
        ).first()
        item_id = dup_item.id
        session.close()

        # Submit decision WITH notes
        response = client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'same_person',
                'notes': 'These are same person despite different names',
            },
        )

        # Should succeed
        assert response.status_code == 302

        # Verify notes are persisted in reviewed_values
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.reviewed_values is not None
        assert decision.reviewed_values.get('notes') == 'These are same person despite different names'
        session.close()

    def test_notes_optional_when_no_conflicting_evidence(self, flask_client_with_db):
        """Test that notes are NOT required when no conflicting evidence exists."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Get duplicate item WITHOUT conflicting evidence
        all_dups = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').all()
        dup_item_clean = None
        for item in all_dups:
            conflicting = item.payload_json.get('conflicting_evidence', [])
            if not conflicting or len(conflicting) == 0:
                dup_item_clean = item
                break

        assert dup_item_clean is not None, "Could not find duplicate item without conflicting evidence"
        item_id = dup_item_clean.id
        session.close()

        # Submit decision WITHOUT notes - should succeed
        response = client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'same_person',
                'notes': '',  # Empty notes
            },
        )

        # Should succeed (302) because no conflicting evidence
        assert response.status_code == 302

        # Verify decision was recorded
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'same_person'
        session.close()

    def test_review_item_status_updated_to_decided(self, flask_client_with_db):
        """Test that ReviewItem status is updated to 'decided' after decision recorded."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        dup_item = session.query(ReviewItem).filter(
            ReviewItem.item_type == 'duplicate'
        ).first()
        item_id = dup_item.id

        # Verify initial status is 'pending'
        assert dup_item.status == 'pending'
        session.close()

        # Submit decision
        client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'same_person',
                'notes': 'Test decision',
            },
        )

        # Verify status was updated to 'decided'
        session = Session()
        dup_item_after = session.query(ReviewItem).filter_by(id=item_id).first()
        assert dup_item_after.status == 'decided', f"Expected 'decided' but got '{dup_item_after.status}'"
        session.close()
