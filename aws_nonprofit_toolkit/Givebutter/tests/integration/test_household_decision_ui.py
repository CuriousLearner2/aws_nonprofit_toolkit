"""Integration tests for household decision UI and form submission."""

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
        raw_csv_data={'Name': 'John Smith'},
    )
    row2 = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=2,
        raw_csv_data={'Name': 'Robert Smith'},
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
    )
    contact2 = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=row2.id,
        first_name='Robert',
        last_name='Smith',
    )
    session.add(contact1)
    session.add(contact2)
    session.flush()

    # Create household review item
    household_payload = {
        'id': 'HH-001',
        'suggested_name': 'Smith Family',
        'address': '123 Main St, Springfield, IL',
        'confidence': '98%',
        'proposed_members': ['John Smith', 'Robert Smith'],
        'evidence': ['Shared address'],
        'conflicts': [],
        'status': 'Pending',
    }

    hh_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='household',
        status='pending',
        payload_json=household_payload,
    )
    session.add(hh_item)
    session.commit()

    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session


class TestHouseholdDecisionUI:
    """Test household decision UI and form behavior."""

    def test_households_page_renders(self, flask_client_with_db):
        """Test that households page renders successfully."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/households')

        assert response.status_code == 200
        assert b'Households' in response.data or b'Smith Family' in response.data

    def test_status_badge_displays_pending(self, flask_client_with_db):
        """Test that status badge displays Pending for new household."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/households')

        assert response.status_code == 200
        assert b'Pending' in response.data

    def test_confirm_household_submission_creates_decision(self, flask_client_with_db):
        """Test that confirming household creates ReviewDecision."""
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
        assert decision is not None
        assert decision.decision == 'confirm_household'
        session.close()

    def test_reject_household_submission_creates_decision(self, flask_client_with_db):
        """Test that rejecting household creates ReviewDecision."""
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
        assert decision is not None
        assert decision.decision == 'reject_household'
        session.close()

    def test_defer_submission_creates_decision(self, flask_client_with_db):
        """Test that deferring household creates ReviewDecision."""
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
        assert decision is not None
        assert decision.decision == 'defer'
        session.close()

    def test_page_has_no_merge_language(self, flask_client_with_db):
        """Test that page uses intent-only language, not mutation language."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/households')

        # Page should NOT contain mutation language
        assert b'Merge' not in response.data.upper() or b'merge' not in response.data
        assert b'Assign' not in response.data
        assert b'Link' not in response.data
        assert b'Consolidate' not in response.data

    def test_form_has_only_household_decisions(self, flask_client_with_db):
        """Test that form only includes household decision types."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/households')

        # Should have household decision values
        assert b'confirm_household' in response.data
        assert b'reject_household' in response.data
        assert b'defer' in response.data

        # Should NOT have validation/normalization/duplicate decision values
        assert b'accept_issue' not in response.data
        assert b'dismiss_issue' not in response.data
        assert b'accept_normalization' not in response.data
        assert b'reject_normalization' not in response.data
        assert b'same_person' not in response.data
        assert b'different_people' not in response.data
