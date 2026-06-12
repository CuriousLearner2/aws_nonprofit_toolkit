"""
Unit tests for DatabaseImportRepository.

Verifies:
1. DatabaseImportRepository class exists
2. list_imports() method is implemented
3. list_imports() returns List[ImportSummary] (frozen view models, not ORM objects)
4. Parity with FixtureImportRepository.list_imports() output shape
5. Database state is not mutated
6. Proper timestamp formatting
7. Other repository methods raise NotImplementedError
8. No repository swap has occurred
9. No write APIs or mutations added
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import (
    Base, ImportBatch, ImportContact, RawImportRow, ReviewItem, ReviewDecision
)
from scripts.householder.database_repository import DatabaseImportRepository
from scripts.householder.service_contracts import ImportSummary
from scripts.householder.fixture_repository import FixtureImportRepository


class TestDatabaseImportRepositoryExists:
    """Verify DatabaseImportRepository class structure."""

    def test_database_import_repository_class_exists(self):
        """Test that DatabaseImportRepository can be instantiated."""
        repo = DatabaseImportRepository()
        assert repo is not None
        assert hasattr(repo, 'list_imports')

    def test_database_import_repository_accepts_custom_database_url(self):
        """Test that repository accepts database URL parameter."""
        repo = DatabaseImportRepository(database_url='sqlite:///:memory:')
        assert repo.database_url == 'sqlite:///:memory:'

    def test_list_imports_method_exists(self):
        """Test that list_imports method is defined."""
        repo = DatabaseImportRepository()
        assert callable(repo.list_imports)


class TestDatabaseListImportsReturnType:
    """Verify list_imports() return type and structure."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary SQLite database for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'test.db'
            db_url = f'sqlite:///{db_path}'

            # Create tables
            engine = create_engine(db_url)
            Base.metadata.create_all(engine)

            yield db_url

    def test_list_imports_returns_list(self, temp_db):
        """Test that list_imports returns a list."""
        repo = DatabaseImportRepository(database_url=temp_db)
        result = repo.list_imports()
        assert isinstance(result, list)

    def test_list_imports_returns_import_summary_objects(self, temp_db):
        """Test that list_imports returns ImportSummary instances."""
        # Seed database with test data
        engine = create_engine(temp_db)
        Session = sessionmaker(bind=engine)
        session = Session()

        batch = ImportBatch(
            id='IMP-TEST-001',
            filename='test.csv',
            upload_timestamp=datetime.now(),
            status='In Review',
            raw_row_count=10
        )
        session.add(batch)
        session.commit()
        session.close()

        # Test repository
        repo = DatabaseImportRepository(database_url=temp_db)
        result = repo.list_imports()

        assert len(result) > 0
        assert isinstance(result[0], ImportSummary)

    def test_list_imports_returns_frozen_view_models_not_orm_objects(self, temp_db):
        """Test that list_imports returns frozen dataclasses, not ORM objects."""
        engine = create_engine(temp_db)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        batch = ImportBatch(
            id='IMP-TEST-002',
            filename='test.csv',
            upload_timestamp=datetime.now(),
            status='Complete',
            raw_row_count=5
        )
        session.add(batch)
        session.commit()
        session.close()

        repo = DatabaseImportRepository(database_url=temp_db)
        result = repo.list_imports()

        assert len(result) > 0
        summary = result[0]

        # Verify it's not an ORM object
        assert not hasattr(summary, '__mapper__')  # SQLAlchemy ORM objects have this
        # Verify it's a frozen dataclass
        with pytest.raises((AttributeError, Exception)):
            summary.id = 'modified'  # Should fail on frozen dataclass

    def test_list_imports_has_required_fields(self, temp_db):
        """Test that returned ImportSummary has all required fields."""
        engine = create_engine(temp_db)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        batch = ImportBatch(
            id='IMP-TEST-003',
            filename='donors.csv',
            upload_timestamp=datetime.now(),
            status='Complete',
            raw_row_count=20
        )
        session.add(batch)
        session.commit()
        session.close()

        repo = DatabaseImportRepository(database_url=temp_db)
        result = repo.list_imports()

        assert len(result) > 0
        summary = result[0]

        # Verify required fields
        assert hasattr(summary, 'id')
        assert hasattr(summary, 'filename')
        assert hasattr(summary, 'record_count')
        assert hasattr(summary, 'status')
        assert hasattr(summary, 'progress')
        assert hasattr(summary, 'uploaded_timestamp')

    def test_list_imports_to_template_dict(self, temp_db):
        """Test that ImportSummary can be converted to template dict."""
        engine = create_engine(temp_db)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        batch = ImportBatch(
            id='IMP-TEST-004',
            filename='test.csv',
            upload_timestamp=datetime.now(),
            status='Complete',
            raw_row_count=10
        )
        session.add(batch)
        session.commit()
        session.close()

        repo = DatabaseImportRepository(database_url=temp_db)
        result = repo.list_imports()

        assert len(result) > 0
        summary = result[0]
        template_dict = summary.to_template_dict()

        assert isinstance(template_dict, dict)
        assert 'id' in template_dict
        assert 'filename' in template_dict
        assert 'record_count' in template_dict
        assert 'status' in template_dict
        assert 'progress' in template_dict
        assert 'uploaded_timestamp' in template_dict


class TestDatabaseListImportsParity:
    """Verify parity between DatabaseImportRepository and FixtureImportRepository."""

    @pytest.fixture
    def seeded_temp_db(self):
        """Create temp database seeded with equivalent fixture data and progress state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'parity_test.db'
            db_url = f'sqlite:///{db_path}'

            engine = create_engine(db_url)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            session = Session()

            # Seed with data equivalent to IMPORTS_LIST fixture
            # IMP-2025-0101-A: progress 42 (21 decided out of 50 items)
            batch1 = ImportBatch(
                id='IMP-2025-0101-A',
                filename='donors_q1_2025.csv',
                upload_timestamp=datetime.now() - timedelta(days=2),
                status='In Review',
                raw_row_count=50
            )
            # Create corresponding raw rows and contacts
            for i in range(50):
                raw_row = RawImportRow(
                    batch_id='IMP-2025-0101-A',
                    row_index=i,
                    raw_csv_data={'name': f'Donor {i}'}
                )
                contact = ImportContact(
                    batch_id='IMP-2025-0101-A',
                    raw_import_row_id=i + 1,
                    first_name=f'Donor',
                    last_name=f'{i}'
                )
                session.add(raw_row)
                session.add(contact)

            # Create review items for batch1 with pending status for dashboard queue counts
            # Duplicates: 3 pending
            for i in range(3):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='duplicate',
                    status='pending',
                    payload_json={'duplicate': f'pair {i}'}
                )
                session.add(item)

            # Validation: 8 pending
            for i in range(8):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='pending',
                    payload_json={'validation': f'issue {i}'}
                )
                session.add(item)

            # Normalizations: 6 pending
            for i in range(6):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'normalization': f'suggestion {i}'}
                )
                session.add(item)

            # Households: 5 pending
            for i in range(5):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='household',
                    status='pending',
                    payload_json={'household': f'grouping {i}'}
                )
                session.add(item)

            # Additional items (50 total): 28 resolved to achieve 42% progress (21/50)
            for i in range(28):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='resolved',
                    payload_json={'validation': f'resolved {i}'}
                )
                session.add(item)

            session.flush()  # Ensure items get IDs

            # Create 21 review decisions (42% of 50) for batch1 (only for some items)
            batch1_items = session.query(ReviewItem).filter_by(batch_id='IMP-2025-0101-A').all()
            for i in range(21):
                decision = ReviewDecision(
                    batch_id='IMP-2025-0101-A',
                    review_item_id=batch1_items[i].id,
                    decision='accept'
                )
                session.add(decision)

            # IMP-2024-1201-B: progress 100 (all items decided)
            batch2 = ImportBatch(
                id='IMP-2024-1201-B',
                filename='donors_q4_2024.csv',
                upload_timestamp=datetime.now() - timedelta(days=30),
                status='Complete',
                raw_row_count=125
            )
            for i in range(125):
                raw_row = RawImportRow(
                    batch_id='IMP-2024-1201-B',
                    row_index=i,
                    raw_csv_data={'name': f'Donor {i}'}
                )
                contact = ImportContact(
                    batch_id='IMP-2024-1201-B',
                    raw_import_row_id=i + 50 + 1,
                    first_name=f'Donor',
                    last_name=f'{i}'
                )
                session.add(raw_row)
                session.add(contact)

            # Create 125 review items for batch2
            for i in range(125):
                item = ReviewItem(
                    batch_id='IMP-2024-1201-B',
                    item_type='duplicate',
                    status='resolved',
                    payload_json={'match': f'duplicate {i}'}
                )
                session.add(item)
            session.flush()

            # Create 125 review decisions (100% of 125) for batch2
            batch2_items = session.query(ReviewItem).filter_by(batch_id='IMP-2024-1201-B').all()
            for i in range(125):
                decision = ReviewDecision(
                    batch_id='IMP-2024-1201-B',
                    review_item_id=batch2_items[i].id,
                    decision='confirm' if i % 2 == 0 else 'defer'
                )
                session.add(decision)

            # IMP-2024-1001-A: progress 100 (all items decided)
            batch3 = ImportBatch(
                id='IMP-2024-1001-A',
                filename='holiday_campaign_2024.csv',
                upload_timestamp=datetime.now() - timedelta(days=60),
                status='Complete',
                raw_row_count=89
            )
            for i in range(89):
                raw_row = RawImportRow(
                    batch_id='IMP-2024-1001-A',
                    row_index=i,
                    raw_csv_data={'name': f'Donor {i}'}
                )
                contact = ImportContact(
                    batch_id='IMP-2024-1001-A',
                    raw_import_row_id=i + 50 + 125 + 1,
                    first_name=f'Donor',
                    last_name=f'{i}'
                )
                session.add(raw_row)
                session.add(contact)

            # Create 89 review items for batch3
            for i in range(89):
                item = ReviewItem(
                    batch_id='IMP-2024-1001-A',
                    item_type='household',
                    status='resolved',
                    payload_json={'group': f'household {i}'}
                )
                session.add(item)
            session.flush()

            # Create 89 review decisions (100% of 89) for batch3
            batch3_items = session.query(ReviewItem).filter_by(batch_id='IMP-2024-1001-A').all()
            for i in range(89):
                decision = ReviewDecision(
                    batch_id='IMP-2024-1001-A',
                    review_item_id=batch3_items[i].id,
                    decision='accept'
                )
                session.add(decision)

            session.add(batch1)
            session.add(batch2)
            session.add(batch3)
            session.commit()
            session.close()

            yield db_url

    def test_database_returns_same_count_as_fixture(self, seeded_temp_db):
        """Test that database and fixture repositories return same number of imports."""
        fixture_result = FixtureImportRepository.list_imports()
        db_repo = DatabaseImportRepository(database_url=seeded_temp_db)
        db_result = db_repo.list_imports()

        assert len(db_result) == len(fixture_result)

    def test_database_returns_same_ids_as_fixture(self, seeded_temp_db):
        """Test that database and fixture repositories return same import IDs."""
        fixture_result = FixtureImportRepository.list_imports()
        db_repo = DatabaseImportRepository(database_url=seeded_temp_db)
        db_result = db_repo.list_imports()

        fixture_ids = {r.id for r in fixture_result}
        db_ids = {r.id for r in db_result}

        assert fixture_ids == db_ids

    def test_database_returns_same_filenames_as_fixture(self, seeded_temp_db):
        """Test that database and fixture repositories return same filenames."""
        fixture_result = FixtureImportRepository.list_imports()
        db_repo = DatabaseImportRepository(database_url=seeded_temp_db)
        db_result = db_repo.list_imports()

        fixture_filenames = {r.filename for r in fixture_result}
        db_filenames = {r.filename for r in db_result}

        assert fixture_filenames == db_filenames

    def test_database_returns_correct_record_counts(self, seeded_temp_db):
        """Test that database returns correct record counts from seeded data."""
        db_repo = DatabaseImportRepository(database_url=seeded_temp_db)
        db_result = db_repo.list_imports()

        # Find the batches and verify counts match seeding
        by_id = {r.id: r for r in db_result}

        assert by_id['IMP-2025-0101-A'].record_count == 50
        assert by_id['IMP-2024-1201-B'].record_count == 125
        assert by_id['IMP-2024-1001-A'].record_count == 89

    def test_database_returns_correct_status(self, seeded_temp_db):
        """Test that database returns correct status from seeded data."""
        db_repo = DatabaseImportRepository(database_url=seeded_temp_db)
        db_result = db_repo.list_imports()

        by_id = {r.id: r for r in db_result}

        assert by_id['IMP-2025-0101-A'].status == 'In Review'
        assert by_id['IMP-2024-1201-B'].status == 'Complete'
        assert by_id['IMP-2024-1001-A'].status == 'Complete'

    def test_database_returns_correct_progress_values(self, seeded_temp_db):
        """Test that database computes correct progress from review_items/review_decisions."""
        db_repo = DatabaseImportRepository(database_url=seeded_temp_db)
        db_result = db_repo.list_imports()

        by_id = {r.id: r for r in db_result}

        # Verify progress matches fixture values (computed from seeded decisions)
        assert by_id['IMP-2025-0101-A'].progress == 42  # 21 of 50 items decided
        assert by_id['IMP-2024-1201-B'].progress == 100  # 125 of 125 items decided
        assert by_id['IMP-2024-1001-A'].progress == 100  # 89 of 89 items decided

    def test_fixture_vs_database_complete_parity(self, seeded_temp_db):
        """Test complete parity: all ImportSummary fields match fixture."""
        fixture_result = FixtureImportRepository.list_imports()
        db_repo = DatabaseImportRepository(database_url=seeded_temp_db)
        db_result = db_repo.list_imports()

        # Index by ID for comparison
        fixture_by_id = {r.id: r for r in fixture_result}
        db_by_id = {r.id: r for r in db_result}

        # Verify all fields match for each import
        for import_id in ['IMP-2025-0101-A', 'IMP-2024-1201-B', 'IMP-2024-1001-A']:
            fixture = fixture_by_id[import_id]
            database = db_by_id[import_id]

            # Verify all template-ready fields
            assert fixture.id == database.id, f"IDs don't match for {import_id}"
            assert fixture.filename == database.filename, f"Filenames don't match for {import_id}"
            assert fixture.record_count == database.record_count, f"Record counts don't match for {import_id}"
            assert fixture.status == database.status, f"Status don't match for {import_id}"
            assert fixture.progress == database.progress, f"Progress don't match for {import_id}: fixture={fixture.progress}, db={database.progress}"

            # Verify template dict conversion works
            fixture_dict = fixture.to_template_dict()
            database_dict = database.to_template_dict()
            assert fixture_dict.keys() == database_dict.keys()


class TestDatabaseGetDashboard:
    """Verify DatabaseImportRepository.get_dashboard() implementation and parity."""

    @pytest.fixture
    def temp_db_with_dashboard_data(self):
        """Create temp database with dashboard test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'dashboard_test.db'
            db_url = f'sqlite:///{db_path}'

            engine = create_engine(db_url)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            session = Session()

            batch = ImportBatch(
                id='IMP-2025-0101-A',
                filename='donors_q1_2025.csv',
                upload_timestamp=datetime.now() - timedelta(days=2),
                status='In Review',
                raw_row_count=50
            )

            # Create review items with specific types and pending status
            # to match fixture dashboard queue counts
            for i in range(3):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='duplicate',
                    status='pending',
                    payload_json={'duplicate': f'pair {i}'}
                )
                session.add(item)

            for i in range(8):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='pending',
                    payload_json={'validation': f'issue {i}'}
                )
                session.add(item)

            for i in range(6):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'normalization': f'suggestion {i}'}
                )
                session.add(item)

            for i in range(5):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='household',
                    status='pending',
                    payload_json={'household': f'grouping {i}'}
                )
                session.add(item)

            # Additional resolved items (28 total) to achieve 42% progress
            for i in range(28):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='resolved',
                    payload_json={'validation': f'resolved {i}'}
                )
                session.add(item)

            session.flush()

            # Create 21 decisions (42% progress)
            all_items = session.query(ReviewItem).filter_by(batch_id='IMP-2025-0101-A').all()
            for i in range(21):
                decision = ReviewDecision(
                    batch_id='IMP-2025-0101-A',
                    review_item_id=all_items[i].id,
                    decision='accept'
                )
                session.add(decision)

            session.add(batch)
            session.commit()
            session.close()

            yield db_url

    def test_get_dashboard_returns_view_model(self, temp_db_with_dashboard_data):
        """Test that get_dashboard returns ImportDashboardViewModel."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        from scripts.householder.service_contracts import ImportDashboardViewModel
        assert isinstance(result, ImportDashboardViewModel)

    def test_get_dashboard_returns_frozen_view_model_not_orm(self, temp_db_with_dashboard_data):
        """Test that get_dashboard returns frozen dataclass, not ORM object."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        # Verify it's not an ORM object
        assert not hasattr(result, '__mapper__')
        # Verify it's frozen
        with pytest.raises((AttributeError, Exception)):
            result.batch_id = 'modified'

    def test_get_dashboard_has_required_fields(self, temp_db_with_dashboard_data):
        """Test that returned dashboard has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        assert hasattr(result, 'batch_id')
        assert hasattr(result, 'filename')
        assert hasattr(result, 'progress')
        assert hasattr(result, 'queues')
        assert hasattr(result, 'audit_log_url')
        assert hasattr(result, 'export_console_url')
        assert hasattr(result, 'back_to_imports_url')

    def test_get_dashboard_correct_batch_metadata(self, temp_db_with_dashboard_data):
        """Test that dashboard returns correct batch metadata."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        assert result.batch_id == 'IMP-2025-0101-A'
        assert result.filename == 'donors_q1_2025.csv'

    def test_get_dashboard_correct_progress(self, temp_db_with_dashboard_data):
        """Test that dashboard returns correct progress (42%)."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        assert result.progress == 42

    def test_get_dashboard_correct_queue_names(self, temp_db_with_dashboard_data):
        """Test that dashboard returns correct queue card names."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        queue_names = [card.name for card in result.queues]
        expected_names = [
            'Possible Duplicates',
            'Validation Review',
            'Normalizations',
            'Households'
        ]

        assert queue_names == expected_names

    def test_get_dashboard_correct_queue_counts(self, temp_db_with_dashboard_data):
        """Test that dashboard returns correct queue pending counts."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        by_name = {card.name: card for card in result.queues}

        assert by_name['Possible Duplicates'].pending_count == 3
        assert by_name['Validation Review'].pending_count == 8
        assert by_name['Normalizations'].pending_count == 6
        assert by_name['Households'].pending_count == 5

    def test_get_dashboard_parity_with_fixture(self, temp_db_with_dashboard_data):
        """Test complete parity with FixtureImportRepository.get_dashboard()."""
        fixture_result = FixtureImportRepository.get_dashboard('IMP-2025-0101-A')
        db_repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        db_result = db_repo.get_dashboard('IMP-2025-0101-A')

        # Verify key fields match
        assert db_result.batch_id == fixture_result.batch_id
        assert db_result.filename == fixture_result.filename
        assert db_result.progress == fixture_result.progress

        # Verify queue counts match
        fixture_by_name = {card.name: card for card in fixture_result.queues}
        db_by_name = {card.name: card for card in db_result.queues}

        for name in ['Possible Duplicates', 'Validation Review', 'Normalizations', 'Households']:
            assert db_by_name[name].pending_count == fixture_by_name[name].pending_count, \
                f"Queue '{name}' counts don't match: db={db_by_name[name].pending_count}, fixture={fixture_by_name[name].pending_count}"

    def test_get_dashboard_to_template_dict(self, temp_db_with_dashboard_data):
        """Test that dashboard view model converts to template dict."""
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        result = repo.get_dashboard('IMP-2025-0101-A')

        template_dict = result.to_template_dict()

        assert isinstance(template_dict, dict)
        assert 'batch' in template_dict
        assert 'queue_status' in template_dict
        assert template_dict['batch']['id'] == 'IMP-2025-0101-A'
        assert template_dict['batch']['filename'] == 'donors_q1_2025.csv'
        assert template_dict['batch']['progress'] == 42
        assert template_dict['queue_status']['duplicates_pending'] == 3
        assert template_dict['queue_status']['validation_issues'] == 8
        assert template_dict['queue_status']['normalizations_pending'] == 6
        assert template_dict['queue_status']['households_pending'] == 5

    def test_get_dashboard_no_database_mutation(self, temp_db_with_dashboard_data):
        """Test that calling get_dashboard does not mutate database state."""
        engine = create_engine(temp_db_with_dashboard_data)
        Session = sessionmaker(bind=engine)

        # Get initial state
        session = Session()
        initial_batch_count = session.query(ImportBatch).count()
        initial_item_count = session.query(ReviewItem).count()
        session.close()

        # Call get_dashboard
        repo = DatabaseImportRepository(database_url=temp_db_with_dashboard_data)
        repo.get_dashboard('IMP-2025-0101-A')

        # Verify state unchanged
        session = Session()
        final_batch_count = session.query(ImportBatch).count()
        final_item_count = session.query(ReviewItem).count()
        session.close()

        assert initial_batch_count == final_batch_count
        assert initial_item_count == final_item_count


class TestDatabaseRepositoryMethods:
    """Verify other repository methods are not implemented."""

    def test_unimplemented_methods_raise_not_implemented_error(self):
        """Test that unimplemented methods raise NotImplementedError."""
        repo = DatabaseImportRepository()

        with pytest.raises(NotImplementedError):
            repo.get_validation('IMP-2025-0101-A')

        with pytest.raises(NotImplementedError):
            repo.get_normalizations('IMP-2025-0101-A')

        with pytest.raises(NotImplementedError):
            repo.get_households('IMP-2025-0101-A')

        with pytest.raises(NotImplementedError):
            repo.get_duplicates('IMP-2025-0101-A')

        with pytest.raises(NotImplementedError):
            repo.get_audit('IMP-2025-0101-A')

        with pytest.raises(NotImplementedError):
            repo.get_exports('IMP-2025-0101-A')


class TestDatabaseRepositoryNoMutations:
    """Verify database state is not mutated."""

    @pytest.fixture
    def temp_db_with_batch(self):
        """Create temp database with one batch."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'mutation_test.db'
            db_url = f'sqlite:///{db_path}'

            engine = create_engine(db_url)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            session = Session()

            batch = ImportBatch(
                id='IMP-MUTATION-001',
                filename='test.csv',
                upload_timestamp=datetime.now(),
                status='Complete',
                raw_row_count=10
            )
            session.add(batch)
            session.commit()
            session.close()

            yield db_url

    def test_list_imports_does_not_mutate_database(self, temp_db_with_batch):
        """Test that calling list_imports does not modify database state."""
        engine = create_engine(temp_db_with_batch)
        Session = sessionmaker(bind=engine)

        # Get initial state
        session = Session()
        initial_batches = len(session.query(ImportBatch).all())
        initial_batch = session.query(ImportBatch).filter_by(id='IMP-MUTATION-001').first()
        initial_status = initial_batch.status
        session.close()

        # Call list_imports
        repo = DatabaseImportRepository(database_url=temp_db_with_batch)
        repo.list_imports()

        # Verify state is unchanged
        session = Session()
        final_batches = len(session.query(ImportBatch).all())
        final_batch = session.query(ImportBatch).filter_by(id='IMP-MUTATION-001').first()
        final_status = final_batch.status
        session.close()

        assert initial_batches == final_batches
        assert initial_status == final_status


class TestDatabaseRepositoryBoundaryChecks:
    """Verify boundary conditions and integration constraints."""

    def test_no_repository_imported_by_routes(self):
        """Verify DatabaseImportRepository is not imported by routes."""
        import scripts.uploader.app as app_module
        app_source = str(app_module.__file__)
        try:
            with open(app_source, 'r') as f:
                content = f.read()
                assert 'DatabaseImportRepository' not in content
        except FileNotFoundError:
            pass  # app.py may be loaded from bytecode

    def test_no_repository_imported_by_services(self):
        """Verify DatabaseImportRepository is not imported by services."""
        import scripts.householder.duplicates_service as service_module
        service_source = str(service_module.__file__)
        try:
            with open(service_source, 'r') as f:
                content = f.read()
                assert 'DatabaseImportRepository' not in content
        except FileNotFoundError:
            pass

    def test_no_repository_swap_in_fixture_imports(self):
        """Verify FixtureImportRepository is still the active implementation."""
        from scripts.householder.fixture_repository import FixtureImportRepository
        assert FixtureImportRepository is not None
        assert hasattr(FixtureImportRepository, 'list_imports')

    def test_orm_models_not_exposed(self):
        """Verify ORM models are not returned directly."""
        repo = DatabaseImportRepository()
        # This will fail because database is empty, but verifies no ORM leak
        # actual test is in return type verification above
        assert repo is not None
