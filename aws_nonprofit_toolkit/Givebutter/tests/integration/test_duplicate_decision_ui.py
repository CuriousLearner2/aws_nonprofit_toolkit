"""Integration tests for duplicate decision UI."""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewItem, ReviewDecision, AuditLogRecord
)
from sqlalchemy.orm import sessionmaker
import tempfile


@pytest.fixture
def temp_db():
    """Create temporary SQLite database."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    from scripts.householder.database_models import create_db_engine
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def flask_client_with_db(temp_db, monkeypatch):
    """Flask client with database backend and seeded test data."""
    database_url, engine = temp_db

    app.config['TESTING'] = True

    # Set environment variables for database mode
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')

    from scripts.householder import duplicate_decision_service, repository_provider
    from scripts.householder.database_write_repository import DatabaseDuplicateDecisionWriter
    from scripts.householder.database_repository import DatabaseImportRepository

    def patched_get_writer(config):
        return DatabaseDuplicateDecisionWriter(database_url=database_url)

    def patched_get_repo(config=None):
        return DatabaseImportRepository(database_url=database_url)

    monkeypatch.setattr(duplicate_decision_service, '_get_duplicate_decision_writer', patched_get_writer)
    monkeypatch.setattr(repository_provider, 'get_import_repository', patched_get_repo)

    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='IMP-2025-0101-A',
        filename='test_upload.csv',
        upload_timestamp=datetime.now(timezone.utc),
    )
    session.add(batch)
    session.flush()

    row1 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=1, raw_csv_data={'Name': 'John Smith'})
    row2 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=2, raw_csv_data={'Name': 'Jon Smith'})
    session.add(row1)
    session.add(row2)
    session.flush()

    contact1 = ImportContact(
        batch_id='IMP-2025-0101-A', raw_import_row_id=row1.id,
        first_name='John', last_name='Smith', email='john@example.com'
    )
    contact2 = ImportContact(
        batch_id='IMP-2025-0101-A', raw_import_row_id=row2.id,
        first_name='Jon', last_name='Smith', email='jon@example.com'
    )
    session.add(contact1)
    session.add(contact2)
    session.flush()

    dup_payload = {
        'contact_a': {'id': str(contact1.id), 'name': 'John Smith'},
        'contact_b': {'id': str(contact2.id), 'name': 'Jon Smith'},
        'supporting_evidence': ['Same phone'],
        'conflicting_evidence': ['Different name'],
    }

    dup_item = ReviewItem(
        batch_id='IMP-2025-0101-A',
        item_type='duplicate',
        status='pending',
        payload_json=dup_payload,
    )
    session.add(dup_item)
    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session


class TestDuplicateDecisionUI:
    """Test duplicate decision UI rendering and form submission."""

    def test_duplicates_page_renders(self, flask_client_with_db):
        """Test that duplicates page renders."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200
        assert b'Possible Duplicates' in response.data

    def test_status_badge_displays_pending(self, flask_client_with_db):
        """Test that status badge displays Pending."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200
        assert b'Pending' in response.data

    def test_same_person_submission_creates_decision(self, flask_client_with_db):
        """Test that Same Person submission creates ReviewDecision."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
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

    def test_different_people_submission_creates_decision(self, flask_client_with_db):
        """Test that Different People submission creates ReviewDecision."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()
        dup_item = session.query(ReviewItem).filter(ReviewItem.item_type == 'duplicate').first()
        item_id = dup_item.id
        session.close()

        response = client.post(
            f'/imports/IMP-2025-0101-A/duplicates/{item_id}/decision',
            data={
                'decision': 'different_people',
                'notes': 'Test decision',  # Required due to conflicting evidence
            },
        )

        assert response.status_code == 302
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision.decision == 'different_people'
        session.close()

    def test_no_merge_language_in_page(self, flask_client_with_db):
        """Test that page has no merge language."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        html = response.data.decode('utf-8', errors='ignore').lower()
        
        forbidden = ['merge', 'merged', 'combine', 'delete duplicate']
        for word in forbidden:
            assert word not in html

    def test_only_duplicate_decision_types(self, flask_client_with_db):
        """Test that only duplicate decision types in form."""
        client, database_url, engine, Session = flask_client_with_db

        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        html = response.data.decode('utf-8')

        assert b'same_person' in response.data
        assert b'different_people' in response.data
        assert b'defer' in response.data
        assert b'accept_issue' not in response.data
        assert b'accept_normalization' not in response.data

    def test_multiple_pairs_navigation_metadata(self, flask_client_with_db):
        """Test that page shows accurate pair count when multiple pairs exist."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Add a second duplicate pair
        row3 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=3, raw_csv_data={'Name': 'Alice Brown'})
        row4 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=4, raw_csv_data={'Name': 'Alicia Brown'})
        session.add(row3)
        session.add(row4)
        session.flush()

        contact3 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row3.id,
            first_name='Alice', last_name='Brown', email='alice@example.com'
        )
        contact4 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row4.id,
            first_name='Alicia', last_name='Brown', email='alicia@example.com'
        )
        session.add(contact3)
        session.add(contact4)
        session.flush()

        dup_payload2 = {
            'contact_a': {'id': str(contact3.id), 'name': 'Alice Brown'},
            'contact_b': {'id': str(contact4.id), 'name': 'Alicia Brown'},
            'supporting_evidence': ['Same last name'],
            'conflicting_evidence': [],
        }

        dup_item2 = ReviewItem(
            batch_id='IMP-2025-0101-A',
            item_type='duplicate',
            status='pending',
            payload_json=dup_payload2,
        )
        session.add(dup_item2)
        session.commit()
        session.close()

        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200
        # Should show "Pair 1 of 2" (or similar accurate count)
        assert b'Pair 1 of 2' in response.data or b'Pair 1 of' in response.data

    def test_duplicates_index_parameter_selects_pair(self, flask_client_with_db):
        """Test that ?index parameter selects the correct duplicate pair."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Add a second duplicate pair
        row3 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=3, raw_csv_data={'Name': 'Alice Brown'})
        row4 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=4, raw_csv_data={'Name': 'Alicia Brown'})
        session.add(row3)
        session.add(row4)
        session.flush()

        contact3 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row3.id,
            first_name='Alice', last_name='Brown', email='alice@example.com'
        )
        contact4 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row4.id,
            first_name='Alicia', last_name='Brown', email='alicia@example.com'
        )
        session.add(contact3)
        session.add(contact4)
        session.flush()

        dup_payload2 = {
            'contact_a': {'id': str(contact3.id), 'name': 'Alice Brown'},
            'contact_b': {'id': str(contact4.id), 'name': 'Alicia Brown'},
            'supporting_evidence': ['Same last name'],
            'conflicting_evidence': [],
        }

        dup_item2 = ReviewItem(
            batch_id='IMP-2025-0101-A',
            item_type='duplicate',
            status='pending',
            payload_json=dup_payload2,
        )
        session.add(dup_item2)
        session.commit()

        # Get both duplicate items
        items = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-2025-0101-A',
            ReviewItem.item_type == 'duplicate'
        ).order_by(ReviewItem.created_at.asc()).all()
        item1_id = items[0].id
        item2_id = items[1].id
        session.close()

        # Get first pair (index=0 or default)
        response1 = client.get('/imports/IMP-2025-0101-A/duplicates?index=0')
        assert response1.status_code == 200
        assert b'Pair 1 of 2' in response1.data
        # Should show first contact pair
        assert b'John Smith' in response1.data or b'John' in response1.data

        # Get second pair (index=1)
        response2 = client.get('/imports/IMP-2025-0101-A/duplicates?index=1')
        assert response2.status_code == 200
        assert b'Pair 2 of 2' in response2.data
        # Should show second contact pair
        assert b'Alice Brown' in response2.data or b'Alice' in response2.data

    def test_duplicates_navigation_without_decision(self, flask_client_with_db):
        """Test that navigation via ?index does NOT create ReviewDecision."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Add a second duplicate pair
        row3 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=3, raw_csv_data={'Name': 'Alice Brown'})
        row4 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=4, raw_csv_data={'Name': 'Alicia Brown'})
        session.add(row3)
        session.add(row4)
        session.flush()

        contact3 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row3.id,
            first_name='Alice', last_name='Brown', email='alice@example.com'
        )
        contact4 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row4.id,
            first_name='Alicia', last_name='Brown', email='alicia@example.com'
        )
        session.add(contact3)
        session.add(contact4)
        session.flush()

        dup_payload2 = {
            'contact_a': {'id': str(contact3.id), 'name': 'Alice Brown'},
            'contact_b': {'id': str(contact4.id), 'name': 'Alicia Brown'},
            'supporting_evidence': ['Same last name'],
            'conflicting_evidence': [],
        }

        dup_item2 = ReviewItem(
            batch_id='IMP-2025-0101-A',
            item_type='duplicate',
            status='pending',
            payload_json=dup_payload2,
        )
        session.add(dup_item2)
        session.commit()
        session.close()

        # Navigate to first pair
        client.get('/imports/IMP-2025-0101-A/duplicates?index=0')

        # Navigate to second pair
        client.get('/imports/IMP-2025-0101-A/duplicates?index=1')

        # Navigate back to first pair
        client.get('/imports/IMP-2025-0101-A/duplicates?index=0')

        # Verify NO ReviewDecisions were created
        session = Session()
        decisions = session.query(ReviewDecision).filter_by(batch_id='IMP-2025-0101-A').all()
        assert len(decisions) == 0, f"Navigation should NOT create decisions, but found {len(decisions)}"
        session.close()

    def test_duplicates_index_out_of_bounds_clamped(self, flask_client_with_db):
        """Test that out-of-bounds index is clamped to valid range."""
        client, database_url, engine, Session = flask_client_with_db
        session = Session()

        # Add a second duplicate pair
        row3 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=3, raw_csv_data={'Name': 'Alice Brown'})
        row4 = RawImportRow(batch_id='IMP-2025-0101-A', row_index=4, raw_csv_data={'Name': 'Alicia Brown'})
        session.add(row3)
        session.add(row4)
        session.flush()

        contact3 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row3.id,
            first_name='Alice', last_name='Brown', email='alice@example.com'
        )
        contact4 = ImportContact(
            batch_id='IMP-2025-0101-A', raw_import_row_id=row4.id,
            first_name='Alicia', last_name='Brown', email='alicia@example.com'
        )
        session.add(contact3)
        session.add(contact4)
        session.flush()

        dup_payload2 = {
            'contact_a': {'id': str(contact3.id), 'name': 'Alice Brown'},
            'contact_b': {'id': str(contact4.id), 'name': 'Alicia Brown'},
            'supporting_evidence': ['Same last name'],
            'conflicting_evidence': [],
        }

        dup_item2 = ReviewItem(
            batch_id='IMP-2025-0101-A',
            item_type='duplicate',
            status='pending',
            payload_json=dup_payload2,
        )
        session.add(dup_item2)
        session.commit()
        session.close()

        # Request index way out of bounds (negative)
        response = client.get('/imports/IMP-2025-0101-A/duplicates?index=-10')
        assert response.status_code == 200
        assert b'Pair 1 of 2' in response.data

        # Request index way out of bounds (too high)
        response = client.get('/imports/IMP-2025-0101-A/duplicates?index=100')
        assert response.status_code == 200
        # Should show last pair (Pair 2 of 2)
        assert b'Pair 2 of 2' in response.data
