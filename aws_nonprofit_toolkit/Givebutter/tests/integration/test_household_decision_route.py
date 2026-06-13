"""Integration tests for household decision route."""

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

    # Monkeypatch the household_decision_service to use test database
    from scripts.householder import household_decision_service
    from scripts.householder.database_write_repository import DatabaseHouseholdDecisionWriter

    def patched_get_writer(config):
        return DatabaseHouseholdDecisionWriter(database_url=database_url)

    monkeypatch.setattr(household_decision_service, '_get_household_decision_writer', patched_get_writer)

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
        raw_csv_data={'Name': 'Robert Smith', 'Email': 'robert@example.com'},
    )
    row3 = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=3,
        raw_csv_data={'Name': 'Mary Smith', 'Email': 'mary@example.com'},
    )
    session.add(row1)
    session.add(row2)
    session.add(row3)
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
        first_name='Robert',
        last_name='Smith',
        email='robert@example.com',
        phone='555-1234',
    )
    contact3 = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=row3.id,
        first_name='Mary',
        last_name='Smith',
        email='mary@example.com',
        phone='555-1234',
    )
    session.add(contact1)
    session.add(contact2)
    session.add(contact3)
    session.flush()

    # Create household review item
    household_payload = {
        'id': 'HH-001',
        'suggested_name': 'Smith Family',
        'address': '123 Main St, Springfield, IL 62701',
        'confidence': '98%',
        'proposed_members': [
            f'John Smith (TXN-{contact1.id})',
            f'Robert Smith (TXN-{contact2.id})',
            f'Mary Smith (TXN-{contact3.id})',
        ],
        'evidence': ['Shared last name: Smith', 'Same address'],
        'conflicts': [],
    }

    hh_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='household',
        status='pending',
        payload_json=household_payload,
    )
    session.add(hh_item)

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


class TestHouseholdDecisionRoute:
    """Test household decision POST route."""

    def test_valid_decision_creates_review_decision(self, flask_client_with_db):
        """Test that valid decision creates ReviewDecision record."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        hh_item = session.query(ReviewItem).filter(
            ReviewItem.item_type == 'household'
        ).first()
        item_id = hh_item.id
        session.close()

        response = client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        assert response.status_code == 302

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'confirm_household'
        session.close()

    def test_valid_decision_creates_audit_log(self, flask_client_with_db):
        """Test that valid decision creates AuditLogRecord."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        hh_item = session.query(ReviewItem).filter(
            ReviewItem.item_type == 'household'
        ).first()
        item_id = hh_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'reject_household'},
        )

        session = Session()
        audit = session.query(AuditLogRecord).filter_by(item_id=item_id).first()
        assert audit is not None
        assert audit.action_type == 'decision_recorded'
        session.close()

    def test_confirm_household_decision_recorded(self, flask_client_with_db):
        """Test that confirm_household decision is recorded."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision.decision == 'confirm_household'
        session.close()

    def test_reject_household_decision_recorded(self, flask_client_with_db):
        """Test that reject_household decision is recorded."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'reject_household'},
        )

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision.decision == 'reject_household'
        session.close()

    def test_defer_decision_recorded(self, flask_client_with_db):
        """Test that defer decision is recorded."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'defer'},
        )

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision.decision == 'defer'
        session.close()

    def test_invalid_decision_returns_400(self, flask_client_with_db):
        """Test that invalid decision returns 400."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        session.close()

        response = client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
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
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        assert response.status_code == 400

    def test_raw_import_rows_unchanged(self, flask_client_with_db):
        """Test that raw import rows are not modified."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        before = session.query(RawImportRow).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        session = Session()
        after = session.query(RawImportRow).count()
        assert before == after
        session.close()

    def test_import_contacts_unchanged(self, flask_client_with_db):
        """Test that import contacts are not modified."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        before = session.query(ImportContact).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        session = Session()
        after = session.query(ImportContact).count()
        assert before == after
        session.close()

    def test_no_contacts_created_deleted_mutated(self, flask_client_with_db):
        """Test that no contacts are created or deleted."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        before_count = session.query(ImportContact).count()
        before_names = [(c.first_name, c.last_name) for c in session.query(ImportContact).all()]
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        session = Session()
        after_count = session.query(ImportContact).count()
        after_names = [(c.first_name, c.last_name) for c in session.query(ImportContact).all()]
        assert before_count == after_count
        assert before_names == after_names
        session.close()

    def test_household_item_not_mutated(self, flask_client_with_db):
        """Test that the household ReviewItem itself is not mutated."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        before_status = hh_item.status
        before_payload = hh_item.payload_json
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        session = Session()
        hh_item = session.query(ReviewItem).filter_by(id=item_id).first()
        assert hh_item.status == before_status
        assert hh_item.payload_json == before_payload
        session.close()

    def test_multiple_decisions_allowed(self, flask_client_with_db):
        """Test that same item can have multiple decisions (latest wins)."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        hh_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'household').first()
        item_id = hh_item.id
        session.close()

        # First decision
        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'confirm_household'},
        )

        # Second decision (override)
        client.post(
            f'/imports/IMP-2025-0101-A/households/{item_id}/decision',
            data={'decision': 'reject_household'},
        )

        session = Session()
        decisions = session.query(ReviewDecision).filter_by(review_item_id=item_id).all()
        assert len(decisions) == 2
        assert decisions[-1].decision == 'reject_household'
        session.close()
