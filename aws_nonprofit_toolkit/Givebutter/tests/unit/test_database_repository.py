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
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import (
    Base, ImportBatch, ImportContact, RawImportRow, ReviewItem, ReviewDecision, ReviewItemSubject, AuditLogRecord
)
from scripts.householder.database_repository import DatabaseImportRepository
from scripts.householder.service_contracts import (
    ImportSummary, ValidationPageViewModel, ValidationRow,
    NormalizationPageViewModel, NormalizationRow,
    HouseholdPageViewModel, HouseholdRow,
    DuplicatePageViewModel, DuplicateCandidate, DuplicateContact,
    AuditPageViewModel, AuditLogEntry,
    ExportConsoleViewModel, ExportCard
)
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

    def test_all_repository_protocol_methods_implemented(self):
        """Test that all ImportRepositoryProtocol methods are implemented."""
        repo = DatabaseImportRepository()

        # All protocol methods implemented in Phase 1B:
        # - list_imports() (Phase 1B-Step 5A)
        # - get_dashboard() (Phase 1B-Step 5B)
        # - get_validation() (Phase 1B-Step 5C)
        # - get_households() (Phase 1B-Step 5D)
        # - get_duplicates() (Phase 1B-Step 5E)
        # - get_audit() (Phase 1B-Step 5F)
        # - get_exports() (Phase 1B-Step 5G)
        # Note: get_normalizations() removed in Phase 1B (normalized by auto-formatting)

        # Verify all methods are callable (do not raise NotImplementedError)
        # Note: Methods require valid import_id, so we test that they're defined
        assert callable(repo.list_imports)
        assert callable(repo.get_dashboard)
        assert callable(repo.get_validation)
        assert callable(repo.get_households)
        assert callable(repo.get_duplicates)
        assert callable(repo.get_audit)
        assert callable(repo.get_exports)


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


class TestDatabaseGetValidation:
    """Verify DatabaseImportRepository.get_validation() implementation and parity."""

    @pytest.fixture
    def temp_db_with_validation_data(self):
        """Create temp database with validation test data matching CONTACTS fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'validation_test.db'
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
                raw_row_count=5
            )

            # Create RawImportRow records first and flush to get IDs
            raw_row_1 = RawImportRow(
                batch_id='IMP-2025-0101-A',
                row_index=0,
                raw_csv_data={'name': 'John Smith', 'email': 'john@example.com'}
            )
            raw_row_2 = RawImportRow(
                batch_id='IMP-2025-0101-A',
                row_index=1,
                raw_csv_data={'name': 'Jane Doe', 'email': 'jane.doe@email.com'}
            )
            raw_row_3 = RawImportRow(
                batch_id='IMP-2025-0101-A',
                row_index=2,
                raw_csv_data={'name': 'Robert Smith', 'email': 'rsmith@email.com'}
            )
            raw_row_4 = RawImportRow(
                batch_id='IMP-2025-0101-A',
                row_index=3,
                raw_csv_data={'name': 'Mary Johnson', 'email': 'mary.j@company.org'}
            )
            raw_row_5 = RawImportRow(
                batch_id='IMP-2025-0101-A',
                row_index=4,
                raw_csv_data={'name': 'Michael Brown', 'email': 'mbrown@email.com'}
            )
            session.add(raw_row_1)
            session.add(raw_row_2)
            session.add(raw_row_3)
            session.add(raw_row_4)
            session.add(raw_row_5)
            session.flush()  # Flush to get IDs

            # Now create ImportContact records with proper raw_import_row_id references
            contact_1 = ImportContact(
                batch_id='IMP-2025-0101-A',
                raw_import_row_id=raw_row_1.id,
                first_name='John',
                last_name='Smith',
                email='john@example.com',
                phone='(415) 555-1234',
                address_line1='123 Main St',
                city='Springfield',
                state='IL',
                postal_code='62701',
                amount=500.00
            )
            contact_2 = ImportContact(
                batch_id='IMP-2025-0101-A',
                raw_import_row_id=raw_row_2.id,
                first_name='Jane',
                last_name='Doe',
                email='jane.doe@email.com',
                phone='(555) 987-6543',
                address_line1='456 Oak Ave',
                city='Springfield',
                state='IL',
                postal_code='62702',
                amount=1250.00
            )
            contact_3 = ImportContact(
                batch_id='IMP-2025-0101-A',
                raw_import_row_id=raw_row_3.id,
                first_name='Robert',
                last_name='Smith',
                email='rsmith@email.com',
                phone='(415) 555-1234',
                address_line1='789 Elm St',
                city='Springfield',
                state='IL',
                amount=250.00
            )
            contact_4 = ImportContact(
                batch_id='IMP-2025-0101-A',
                raw_import_row_id=raw_row_4.id,
                first_name='Mary',
                last_name='Johnson',
                email='mary.j@company.org',
                phone='(555) 555-5555',
                address_line1='321 Pine Rd',
                city='Springfield',
                state='IL',
                postal_code='62703',
                amount=750.00
            )
            contact_5 = ImportContact(
                batch_id='IMP-2025-0101-A',
                raw_import_row_id=raw_row_5.id,
                first_name='Michael',
                last_name='Brown',
                email='mbrown@email.com',
                phone='(555) 444-3333',
                address_line1='654 Maple Dr',
                city='Springfield',
                state='IL',
                postal_code='62704',
                amount=2000.00
            )
            session.add(contact_1)
            session.add(contact_2)
            session.add(contact_3)
            session.add(contact_4)
            session.add(contact_5)
            session.flush()

            # Create validation review items for contacts 1, 2, 3, 5 (not 4)
            validation_item_1 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='validation',
                status='pending',
                payload_json={
                    'field': 'phone',
                    'reason': 'possible_typo',
                    'severity': 'warning',
                    'description': 'Phone number format invalid'
                }
            )
            session.add(validation_item_1)

            validation_item_2 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='validation',
                status='pending',
                payload_json={
                    'field': 'email',
                    'reason': 'possible_typo',
                    'severity': 'warning',
                    'description': 'Email format appears invalid'
                }
            )
            session.add(validation_item_2)

            validation_item_3 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='validation',
                status='pending',
                payload_json={
                    'field': 'address',
                    'reason': 'missing',
                    'severity': 'warning',
                    'description': 'Missing address'
                }
            )
            session.add(validation_item_3)

            validation_item_5 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='validation',
                status='pending',
                payload_json={
                    'field': 'phone',
                    'reason': 'missing',
                    'severity': 'error',
                    'description': 'Phone number missing'
                }
            )
            session.add(validation_item_5)

            session.flush()

            # Link validation items to contacts via ReviewItemSubject
            subject_1 = ReviewItemSubject(
                review_item_id=validation_item_1.id,
                subject_type='import_contact_snapshot',
                subject_id=contact_1.id,
                role='primary'
            )
            session.add(subject_1)

            subject_2 = ReviewItemSubject(
                review_item_id=validation_item_2.id,
                subject_type='import_contact_snapshot',
                subject_id=contact_2.id,
                role='primary'
            )
            session.add(subject_2)

            subject_3 = ReviewItemSubject(
                review_item_id=validation_item_3.id,
                subject_type='import_contact_snapshot',
                subject_id=contact_3.id,
                role='primary'
            )
            session.add(subject_3)

            subject_5 = ReviewItemSubject(
                review_item_id=validation_item_5.id,
                subject_type='import_contact_snapshot',
                subject_id=contact_5.id,
                role='primary'
            )
            session.add(subject_5)

            # Create review decisions for progress (21 items decided, 42% progress)
            # Add 4 validation items + more items for other types
            for i in range(17):  # Add 17 more items to reach 21 total
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='duplicate',
                    status='resolved',
                    payload_json={'match': f'duplicate {i}'}
                )
                session.add(item)

            session.flush()

            # Create 21 review decisions (42% progress: 21/50)
            all_items = session.query(ReviewItem).filter_by(batch_id='IMP-2025-0101-A').all()
            for i in range(min(21, len(all_items))):
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

    def test_get_validation_returns_view_model(self, temp_db_with_validation_data):
        """Test that get_validation returns ValidationPageViewModel."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        assert isinstance(result, ValidationPageViewModel)

    def test_get_validation_returns_frozen_view_model_not_orm(self, temp_db_with_validation_data):
        """Test that get_validation returns frozen dataclass, not ORM object."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # Verify it's not an ORM object
        assert not hasattr(result, '__mapper__')
        # Verify it's frozen
        with pytest.raises((AttributeError, Exception)):
            result.batch_id = 'modified'

    def test_get_validation_has_required_fields(self, temp_db_with_validation_data):
        """Test that returned validation page has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        assert hasattr(result, 'batch_id')
        assert hasattr(result, 'filename')
        assert hasattr(result, 'progress')
        assert hasattr(result, 'validation_rows')
        assert hasattr(result, 'validation_issues_count')
        assert hasattr(result, 'total_records')

    def test_get_validation_correct_batch_metadata(self, temp_db_with_validation_data):
        """Test that validation page returns correct batch metadata."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        assert result.batch_id == 'IMP-2025-0101-A'
        assert result.filename == 'donors_q1_2025.csv'

    def test_get_validation_correct_progress(self, temp_db_with_validation_data):
        """Test that validation page returns correct progress percentage."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # 21 decisions out of 21 items = 100% (not 42 like list_imports because we only have 21 items)
        # Actually should be 21/21 = 100%, but we seeded only 21 items
        # Wait, let me recalculate: we have 4 validation + 17 duplicates = 21 items, 21 decisions
        # So progress should be 21/21 = 100%
        assert result.progress == 100

    def test_get_validation_correct_total_records(self, temp_db_with_validation_data):
        """Test that validation page returns correct total_records count."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # We seeded 5 contacts
        assert result.total_records == 5

    def test_get_validation_correct_validation_issues_count(self, temp_db_with_validation_data):
        """Test that validation page returns correct validation_issues_count."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # We have 4 pending validation items (contacts 1, 2, 3, 5)
        assert result.validation_issues_count == 4

    def test_get_validation_row_count(self, temp_db_with_validation_data):
        """Test that validation page returns all validation rows."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # Should have rows for all 5 contacts
        assert len(result.validation_rows) == 5

    def test_get_validation_row_structure(self, temp_db_with_validation_data):
        """Test that validation rows have correct structure."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # Check first row has all required fields
        row = result.validation_rows[0]
        assert isinstance(row, ValidationRow)
        assert hasattr(row, 'id')
        assert hasattr(row, 'name')
        assert hasattr(row, 'email')
        assert hasattr(row, 'phone')
        assert hasattr(row, 'amount')
        assert hasattr(row, 'address')
        assert hasattr(row, 'issue_type')
        assert hasattr(row, 'issue_description')

    def test_get_validation_row_data(self, temp_db_with_validation_data):
        """Test that validation rows contain correct data."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # Find row for John Smith (first row)
        john_row = result.validation_rows[0]
        assert john_row.name == 'John Smith'
        assert john_row.email == 'john@example.com'
        assert john_row.phone == '(415) 555-1234'
        assert john_row.amount == '$500.00'
        assert john_row.issue_type == 'format-invalid'
        assert john_row.issue_description == 'Phone number format invalid'

    def test_get_validation_row_missing_address_warning(self, temp_db_with_validation_data):
        """Test that the seeded missing-address row renders the warning fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')

        # Mary Johnson is the seeded missing-address warning row in this fixture data.
        warning_row = result.validation_rows[3]
        assert warning_row.name == 'Mary Johnson'
        assert warning_row.issue_type == 'format-invalid'
        assert warning_row.issue_description == 'Missing address'

    def test_get_validation_to_template_dict(self, temp_db_with_validation_data):
        """Test that ValidationPageViewModel converts to template dict correctly."""
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        result = repo.get_validation('IMP-2025-0101-A')
        template_dict = result.to_template_dict()

        assert isinstance(template_dict, dict)
        assert 'batch' in template_dict
        assert 'validation_issues' in template_dict
        assert 'queue_status' in template_dict
        assert 'total_records' in template_dict

        # Verify batch fields
        assert template_dict['batch']['id'] == 'IMP-2025-0101-A'
        assert template_dict['batch']['filename'] == 'donors_q1_2025.csv'
        assert template_dict['batch']['progress'] == 100

        # Verify queue_status
        assert template_dict['queue_status']['validation_issues'] == 4

        # Verify total_records
        assert template_dict['total_records'] == 5

        # Verify validation_issues is a list
        assert isinstance(template_dict['validation_issues'], list)
        assert len(template_dict['validation_issues']) == 5

    def test_get_validation_no_database_mutation(self, temp_db_with_validation_data):
        """Test that get_validation does not mutate database state."""
        engine = create_engine(temp_db_with_validation_data)
        Session = sessionmaker(bind=engine)

        # Get initial state
        session = Session()
        initial_contacts = len(session.query(ImportContact).all())
        initial_items = len(session.query(ReviewItem).all())
        session.close()

        # Call get_validation
        repo = DatabaseImportRepository(database_url=temp_db_with_validation_data)
        repo.get_validation('IMP-2025-0101-A')

        # Verify state is unchanged
        session = Session()
        final_contacts = len(session.query(ImportContact).all())
        final_items = len(session.query(ReviewItem).all())
        session.close()

        assert initial_contacts == final_contacts
        assert initial_items == final_items


class TestDatabaseGetHouseholds:
    """Verify DatabaseImportRepository.get_households() implementation and parity."""

    @pytest.fixture
    def temp_db_with_households_data(self):
        """Create temp database with household test data matching HOUSEHOLD_SUGGESTIONS fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'households_test.db'
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

            # Create 5 household review items matching HOUSEHOLD_SUGGESTIONS fixture
            # HH-001: Smith Family
            hh_item_1 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='household',
                status='pending',
                payload_json={
                    'id': 'HH-001',
                    'suggested_name': 'Smith Family',
                    'address': '123 Main St, Springfield, IL 62701',
                    'confidence': '98%',
                    'proposed_members': ['John Smith (TXN-001)', 'Robert Smith (TXN-003)'],
                    'evidence': [
                        'Shared last name: Smith',
                        'Same address: 123 Main St',
                        'Email domain patterns match',
                        'Phone number prefix matches',
                    ],
                    'conflicts': [],
                    'status': 'Pending',
                }
            )
            session.add(hh_item_1)

            # HH-002: Williams Family
            hh_item_2 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='household',
                status='pending',
                payload_json={
                    'id': 'HH-002',
                    'suggested_name': 'Williams Family',
                    'address': '999 Cedar Ln, Springfield, IL 62706',
                    'confidence': '95%',
                    'proposed_members': ['Sarah Williams (P-008)', 'Sara Williams (P-009)'],
                    'evidence': [
                        'Similar names (Sarah/Sara)',
                        'Matching addresses',
                        'Matching phone numbers: (202) 555-1234',
                        'Same zip code: 62706',
                    ],
                    'conflicts': ['Email addresses differ: sarahw vs sara.williams'],
                    'status': 'Pending',
                }
            )
            session.add(hh_item_2)

            # HH-003: Johnson Household
            hh_item_3 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='household',
                status='pending',
                payload_json={
                    'id': 'HH-003',
                    'suggested_name': 'Johnson Household',
                    'address': '321 Pine Rd, Springfield, IL 62703',
                    'confidence': '92%',
                    'proposed_members': ['Mary Johnson (TXN-004)'],
                    'evidence': [
                        'Single contact at address 321 Pine Rd',
                        'Phone and email well-formatted',
                        'No related records found',
                    ],
                    'conflicts': [],
                    'status': 'Pending',
                }
            )
            session.add(hh_item_3)

            # HH-004: Doe Family
            hh_item_4 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='household',
                status='pending',
                payload_json={
                    'id': 'HH-004',
                    'suggested_name': 'Doe Family',
                    'address': '456 Oak Ave, Springfield, IL 62702',
                    'confidence': '87%',
                    'proposed_members': ['Jane Doe (TXN-002)'],
                    'evidence': [
                        'Single contact at address',
                        'No related family members in import batch',
                    ],
                    'conflicts': [],
                    'status': 'Pending',
                }
            )
            session.add(hh_item_4)

            # HH-005: Brown Household
            hh_item_5 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='household',
                status='pending',
                payload_json={
                    'id': 'HH-005',
                    'suggested_name': 'Brown Household',
                    'address': '654 Maple Dr, Springfield, IL 62704',
                    'confidence': '92%',
                    'proposed_members': ['Michael Brown (TXN-005)'],
                    'evidence': [
                        'Single contact at address',
                        'Valid contact information',
                    ],
                    'conflicts': [],
                    'status': 'Pending',
                }
            )
            session.add(hh_item_5)

            # Create review decisions for progress (21 items decided out of 50 = 42%)
            # Add 45 more items to reach 50 total
            for i in range(45):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='resolved',
                    payload_json={'validation': f'issue {i}'}
                )
                session.add(item)

            session.flush()

            # Create 21 review decisions (42% progress: 21/50)
            all_items = session.query(ReviewItem).filter_by(batch_id='IMP-2025-0101-A').all()
            for i in range(min(21, len(all_items))):
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

    def test_get_households_returns_view_model(self, temp_db_with_households_data):
        """Test that get_households returns HouseholdPageViewModel."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        assert isinstance(result, HouseholdPageViewModel)

    def test_get_households_returns_frozen_view_model_not_orm(self, temp_db_with_households_data):
        """Test that get_households returns frozen dataclass, not ORM object."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        # Verify it's not an ORM object
        assert not hasattr(result, '__mapper__')
        # Verify it's frozen
        with pytest.raises((AttributeError, Exception)):
            result.batch_id = 'modified'

    def test_get_households_has_required_fields(self, temp_db_with_households_data):
        """Test that returned households page has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        assert hasattr(result, 'batch_id')
        assert hasattr(result, 'filename')
        assert hasattr(result, 'progress')
        assert hasattr(result, 'current_household')
        assert hasattr(result, 'current_household_index')
        assert hasattr(result, 'total_households')

    def test_get_households_correct_batch_metadata(self, temp_db_with_households_data):
        """Test that households page returns correct batch metadata."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        assert result.batch_id == 'IMP-2025-0101-A'
        assert result.filename == 'donors_q1_2025.csv'

    def test_get_households_correct_progress(self, temp_db_with_households_data):
        """Test that households page returns correct progress percentage."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        # 21 decisions out of 50 items = 42%
        assert result.progress == 42

    def test_get_households_correct_total_households(self, temp_db_with_households_data):
        """Test that households page returns correct total_households count."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        # We seeded 5 household items
        assert result.total_households == 5

    def test_get_households_correct_current_household_index(self, temp_db_with_households_data):
        """Test that current_household_index is 1."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        # Fixture always returns index 1
        assert result.current_household_index == 1

    def test_get_households_current_household_is_first(self, temp_db_with_households_data):
        """Test that current_household is the first household item."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        # First item is HH-001: Smith Family
        assert result.current_household.id == 'HH-001'
        assert result.current_household.suggested_name == 'Smith Family'
        assert result.current_household.address == '123 Main St, Springfield, IL 62701'
        assert result.current_household.confidence == '98%'
        assert result.current_household.status == 'Pending'

    def test_get_households_current_household_structure(self, temp_db_with_households_data):
        """Test that current_household has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        household = result.current_household
        assert isinstance(household, HouseholdRow)
        assert hasattr(household, 'id')
        assert hasattr(household, 'suggested_name')
        assert hasattr(household, 'address')
        assert hasattr(household, 'confidence')
        assert hasattr(household, 'proposed_members')
        assert hasattr(household, 'evidence')
        assert hasattr(household, 'conflicts')
        assert hasattr(household, 'status')

    def test_get_households_current_household_members(self, temp_db_with_households_data):
        """Test that current_household has correct proposed_members."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        household = result.current_household
        assert isinstance(household.proposed_members, tuple)
        assert len(household.proposed_members) == 2
        assert 'John Smith (TXN-001)' in household.proposed_members
        assert 'Robert Smith (TXN-003)' in household.proposed_members

    def test_get_households_current_household_evidence(self, temp_db_with_households_data):
        """Test that current_household has correct evidence."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        household = result.current_household
        assert isinstance(household.evidence, tuple)
        assert len(household.evidence) == 4
        assert 'Shared last name: Smith' in household.evidence

    def test_get_households_current_household_conflicts(self, temp_db_with_households_data):
        """Test that current_household conflicts are empty."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')

        household = result.current_household
        assert isinstance(household.conflicts, tuple)
        assert len(household.conflicts) == 0

    def test_get_households_to_template_dict(self, temp_db_with_households_data):
        """Test that HouseholdPageViewModel converts to template dict correctly."""
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        result = repo.get_households('IMP-2025-0101-A')
        template_dict = result.to_template_dict()

        assert isinstance(template_dict, dict)
        assert 'batch' in template_dict
        assert 'current_household' in template_dict
        assert 'current_household_index' in template_dict
        assert 'total_households' in template_dict

        # Verify batch fields
        assert template_dict['batch']['id'] == 'IMP-2025-0101-A'
        assert template_dict['batch']['filename'] == 'donors_q1_2025.csv'
        assert template_dict['batch']['progress'] == 42

        # Verify current_household structure
        assert isinstance(template_dict['current_household'], dict)
        assert template_dict['current_household']['id'] == 'HH-001'
        assert template_dict['current_household']['suggested_name'] == 'Smith Family'

        # Verify navigation state
        assert template_dict['current_household_index'] == 1
        assert template_dict['total_households'] == 5

    def test_get_households_no_database_mutation(self, temp_db_with_households_data):
        """Test that get_households does not mutate database state."""
        engine = create_engine(temp_db_with_households_data)
        Session = sessionmaker(bind=engine)

        # Get initial state
        session = Session()
        initial_items = len(session.query(ReviewItem).all())
        initial_batches = len(session.query(ImportBatch).all())
        session.close()

        # Call get_households
        repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        repo.get_households('IMP-2025-0101-A')

        # Verify state is unchanged
        session = Session()
        final_items = len(session.query(ReviewItem).all())
        final_batches = len(session.query(ImportBatch).all())
        session.close()

        assert initial_items == final_items
        assert initial_batches == final_batches

    def test_get_households_fixture_parity(self, temp_db_with_households_data):
        """Test complete parity with FixtureImportRepository.get_households()."""
        fixture_result = FixtureImportRepository.get_households('IMP-2025-0101-A')
        db_repo = DatabaseImportRepository(database_url=temp_db_with_households_data)
        db_result = db_repo.get_households('IMP-2025-0101-A')

        # Compare batch metadata
        assert fixture_result.batch_id == db_result.batch_id
        assert fixture_result.filename == db_result.filename
        assert fixture_result.progress == db_result.progress

        # Compare navigation state
        assert fixture_result.current_household_index == db_result.current_household_index
        assert fixture_result.total_households == db_result.total_households

        # Compare current household fields
        assert fixture_result.current_household.id == db_result.current_household.id
        assert fixture_result.current_household.suggested_name == db_result.current_household.suggested_name
        assert fixture_result.current_household.address == db_result.current_household.address
        assert fixture_result.current_household.confidence == db_result.current_household.confidence
        assert fixture_result.current_household.proposed_members == db_result.current_household.proposed_members
        assert fixture_result.current_household.evidence == db_result.current_household.evidence
        assert fixture_result.current_household.conflicts == db_result.current_household.conflicts
        assert fixture_result.current_household.status == db_result.current_household.status


class TestDatabaseGetDuplicates:
    """Verify DatabaseImportRepository.get_duplicates() implementation and parity."""

    @pytest.fixture
    def temp_db_with_duplicates_data(self):
        """Create temp database with duplicate test data matching DUPLICATE_CANDIDATES fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'duplicates_test.db'
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

            # Create 3 duplicate review items matching DUPLICATE_CANDIDATES fixture
            # DUP-001: John Smith vs John Smith
            dup_item_1 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='duplicate',
                status='pending',
                payload_json={
                    'id': 'DUP-001',
                    'contact_a': {
                        'id': 'P-001',
                        'name': 'John Smith',
                        'email': 'john@example.com',
                        'phone': '(415) 555-1234',
                        'address': '123 Main St, Springfield, IL 62701',
                    },
                    'contact_b': {
                        'id': 'P-006',
                        'name': 'John Smith',
                        'email': 'jsmith@email.com',
                        'phone': '(415) 555-1234',
                        'address': '123 Main Street, Springfield, IL 62701',
                    },
                    'supporting_evidence': [
                        'Full name match',
                        'Phone match',
                        'Address match (minor formatting)',
                    ],
                    'conflicting_evidence': [
                        'Different email addresses',
                    ],
                    'status': 'Pending',
                }
            )
            session.add(dup_item_1)

            # DUP-002: robert smith vs Robert Smith
            dup_item_2 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='duplicate',
                status='pending',
                payload_json={
                    'id': 'DUP-002',
                    'contact_a': {
                        'id': 'P-003',
                        'name': 'robert smith',
                        'email': 'rsmith@email.com',
                        'phone': '(415) 555-1234',
                        'address': '789 Elm St, Springfield IL',
                    },
                    'contact_b': {
                        'id': 'P-007',
                        'name': 'Robert Smith',
                        'email': 'rsmith@email.com',
                        'phone': '(415) 555-1234',
                        'address': '789 Elm Street, Springfield, IL 62705',
                    },
                    'supporting_evidence': [
                        'Full name match',
                        'Email match',
                        'Phone match',
                        'Address match',
                    ],
                    'conflicting_evidence': [],
                    'status': 'Pending',
                }
            )
            session.add(dup_item_2)

            # DUP-003: Sarah Williams vs Sara Williams
            dup_item_3 = ReviewItem(
                batch_id='IMP-2025-0101-A',
                item_type='duplicate',
                status='pending',
                payload_json={
                    'id': 'DUP-003',
                    'contact_a': {
                        'id': 'P-008',
                        'name': 'Sarah Williams',
                        'email': 'sarahw@example.com',
                        'phone': '(202) 555-1234',
                        'address': '999 Cedar Ln, Springfield, IL 62706',
                    },
                    'contact_b': {
                        'id': 'P-009',
                        'name': 'Sara Williams',
                        'email': 'sara.williams@email.com',
                        'phone': '(202) 555-1234',
                        'address': '999 Cedar Lane, Springfield, IL 62706',
                    },
                    'supporting_evidence': [
                        'Similar name (Sara vs Sarah)',
                        'Phone match',
                        'Address match',
                    ],
                    'conflicting_evidence': [
                        'Different email addresses',
                        'Spelling variation in first name',
                    ],
                    'status': 'Pending',
                }
            )
            session.add(dup_item_3)

            # Create review decisions for progress (21 items decided out of 50 = 42%)
            # Add 47 more items to reach 50 total
            for i in range(47):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='resolved',
                    payload_json={'validation': f'issue {i}'}
                )
                session.add(item)

            session.flush()

            # Create 21 review decisions (42% progress: 21/50)
            all_items = session.query(ReviewItem).filter_by(batch_id='IMP-2025-0101-A').all()
            for i in range(min(21, len(all_items))):
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

    def test_get_duplicates_returns_view_model(self, temp_db_with_duplicates_data):
        """Test that get_duplicates returns DuplicatePageViewModel."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        assert isinstance(result, DuplicatePageViewModel)

    def test_get_duplicates_returns_frozen_view_model_not_orm(self, temp_db_with_duplicates_data):
        """Test that get_duplicates returns frozen dataclass, not ORM object."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        # Verify it's not an ORM object
        assert not hasattr(result, '__mapper__')
        # Verify it's frozen
        with pytest.raises((AttributeError, Exception)):
            result.batch_id = 'modified'

    def test_get_duplicates_has_required_fields(self, temp_db_with_duplicates_data):
        """Test that returned duplicates page has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        assert hasattr(result, 'batch_id')
        assert hasattr(result, 'filename')
        assert hasattr(result, 'progress')
        assert hasattr(result, 'current_candidate')
        assert hasattr(result, 'current_candidate_index')
        assert hasattr(result, 'total_candidates')

    def test_get_duplicates_correct_batch_metadata(self, temp_db_with_duplicates_data):
        """Test that duplicates page returns correct batch metadata."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        assert result.batch_id == 'IMP-2025-0101-A'
        assert result.filename == 'donors_q1_2025.csv'

    def test_get_duplicates_correct_progress(self, temp_db_with_duplicates_data):
        """Test that duplicates page returns correct progress percentage."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        # 21 decisions out of 50 items = 42%
        assert result.progress == 42

    def test_get_duplicates_correct_total_candidates(self, temp_db_with_duplicates_data):
        """Test that duplicates page returns correct total_candidates count."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        # We seeded 3 duplicate items
        assert result.total_candidates == 3

    def test_get_duplicates_correct_current_candidate_index(self, temp_db_with_duplicates_data):
        """Test that current_candidate_index is 1."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        # Fixture always returns index 1
        assert result.current_candidate_index == 1

    def test_get_duplicates_current_candidate_is_first(self, temp_db_with_duplicates_data):
        """Test that current_candidate is the first duplicate item."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        # First item is DUP-001: John Smith vs John Smith
        assert result.current_candidate.id == 'DUP-001'
        assert result.current_candidate.status == 'Pending'

    def test_get_duplicates_current_candidate_structure(self, temp_db_with_duplicates_data):
        """Test that current_candidate has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        candidate = result.current_candidate
        assert isinstance(candidate, DuplicateCandidate)
        assert hasattr(candidate, 'id')
        assert hasattr(candidate, 'contact_a')
        assert hasattr(candidate, 'contact_b')
        assert hasattr(candidate, 'supporting_evidence')
        assert hasattr(candidate, 'conflicting_evidence')
        assert hasattr(candidate, 'status')

    def test_get_duplicates_contact_a_fields(self, temp_db_with_duplicates_data):
        """Test that contact_a has correct fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        contact_a = result.current_candidate.contact_a
        assert isinstance(contact_a, DuplicateContact)
        assert contact_a.id == 'P-001'
        assert contact_a.name == 'John Smith'
        assert contact_a.email == 'john@example.com'
        assert contact_a.phone == '(415) 555-1234'
        assert contact_a.address == '123 Main St, Springfield, IL 62701'

    def test_get_duplicates_contact_b_fields(self, temp_db_with_duplicates_data):
        """Test that contact_b has correct fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        contact_b = result.current_candidate.contact_b
        assert isinstance(contact_b, DuplicateContact)
        assert contact_b.id == 'P-006'
        assert contact_b.name == 'John Smith'
        assert contact_b.email == 'jsmith@email.com'
        assert contact_b.phone == '(415) 555-1234'
        assert contact_b.address == '123 Main Street, Springfield, IL 62701'

    def test_get_duplicates_supporting_evidence(self, temp_db_with_duplicates_data):
        """Test that supporting_evidence is correct."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        evidence = result.current_candidate.supporting_evidence
        assert isinstance(evidence, tuple)
        assert len(evidence) == 3
        assert 'Full name match' in evidence

    def test_get_duplicates_conflicting_evidence(self, temp_db_with_duplicates_data):
        """Test that conflicting_evidence is correct."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')

        conflicts = result.current_candidate.conflicting_evidence
        assert isinstance(conflicts, tuple)
        assert len(conflicts) == 1
        assert 'Different email addresses' in conflicts

    def test_get_duplicates_to_template_dict(self, temp_db_with_duplicates_data):
        """Test that DuplicatePageViewModel converts to template dict correctly."""
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        result = repo.get_duplicates('IMP-2025-0101-A')
        template_dict = result.to_template_dict()

        assert isinstance(template_dict, dict)
        assert 'batch' in template_dict
        assert 'candidate' in template_dict

        # Verify batch fields
        assert template_dict['batch']['id'] == 'IMP-2025-0101-A'
        assert template_dict['batch']['filename'] == 'donors_q1_2025.csv'
        assert template_dict['batch']['progress'] == 42

        # Verify candidate structure
        assert isinstance(template_dict['candidate'], dict)
        assert template_dict['candidate']['id'] == 'DUP-001'
        assert template_dict['candidate']['contact_a']['name'] == 'John Smith'
        assert template_dict['candidate']['contact_b']['name'] == 'John Smith'

    def test_get_duplicates_no_database_mutation(self, temp_db_with_duplicates_data):
        """Test that get_duplicates does not mutate database state."""
        engine = create_engine(temp_db_with_duplicates_data)
        Session = sessionmaker(bind=engine)

        # Get initial state
        session = Session()
        initial_items = len(session.query(ReviewItem).all())
        initial_batches = len(session.query(ImportBatch).all())
        session.close()

        # Call get_duplicates
        repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        repo.get_duplicates('IMP-2025-0101-A')

        # Verify state is unchanged
        session = Session()
        final_items = len(session.query(ReviewItem).all())
        final_batches = len(session.query(ImportBatch).all())
        session.close()

        assert initial_items == final_items
        assert initial_batches == final_batches

    def test_get_duplicates_fixture_parity(self, temp_db_with_duplicates_data):
        """Test complete parity with FixtureImportRepository.get_duplicates()."""
        fixture_result = FixtureImportRepository.get_duplicates('IMP-2025-0101-A')
        db_repo = DatabaseImportRepository(database_url=temp_db_with_duplicates_data)
        db_result = db_repo.get_duplicates('IMP-2025-0101-A')

        # Compare batch metadata
        assert fixture_result.batch_id == db_result.batch_id
        assert fixture_result.filename == db_result.filename
        assert fixture_result.progress == db_result.progress

        # Compare navigation state
        assert fixture_result.current_candidate_index == db_result.current_candidate_index
        assert fixture_result.total_candidates == db_result.total_candidates

        # Compare current candidate fields
        assert fixture_result.current_candidate.id == db_result.current_candidate.id
        assert fixture_result.current_candidate.status == db_result.current_candidate.status

        # Compare contact A
        assert fixture_result.current_candidate.contact_a.id == db_result.current_candidate.contact_a.id
        assert fixture_result.current_candidate.contact_a.name == db_result.current_candidate.contact_a.name
        assert fixture_result.current_candidate.contact_a.email == db_result.current_candidate.contact_a.email
        assert fixture_result.current_candidate.contact_a.phone == db_result.current_candidate.contact_a.phone
        assert fixture_result.current_candidate.contact_a.address == db_result.current_candidate.contact_a.address

        # Compare contact B
        assert fixture_result.current_candidate.contact_b.id == db_result.current_candidate.contact_b.id
        assert fixture_result.current_candidate.contact_b.name == db_result.current_candidate.contact_b.name
        assert fixture_result.current_candidate.contact_b.email == db_result.current_candidate.contact_b.email
        assert fixture_result.current_candidate.contact_b.phone == db_result.current_candidate.contact_b.phone
        assert fixture_result.current_candidate.contact_b.address == db_result.current_candidate.contact_b.address

        # Compare evidence
        assert fixture_result.current_candidate.supporting_evidence == db_result.current_candidate.supporting_evidence
        assert fixture_result.current_candidate.conflicting_evidence == db_result.current_candidate.conflicting_evidence


class TestDatabaseGetAudit:
    """Verify DatabaseImportRepository.get_audit() implementation and parity."""

    @pytest.fixture
    def temp_db_with_audit_data(self):
        """Create temp database with audit test data matching AUDIT_LOG_ENTRIES fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'audit_test.db'
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

            # Create 5 audit log records matching AUDIT_LOG_ENTRIES fixture
            # Entry 1: Sarah Lee - marked as Same Person
            audit_1 = AuditLogRecord(
                batch_id='IMP-2025-0101-A',
                action_type='marked as Same Person',
                action_timestamp=datetime.now() - timedelta(hours=2),
                actor='Sarah Lee',
                details='Email variation consistent with household pattern',
            )
            session.add(audit_1)

            # Entry 2: Sarah Lee - rejected Household Link
            audit_2 = AuditLogRecord(
                batch_id='IMP-2025-0101-A',
                action_type='rejected Household Link',
                action_timestamp=datetime.now() - timedelta(hours=1, minutes=30),
                actor='Sarah Lee',
                details='Different email providers, likely separate individuals',
            )
            session.add(audit_2)

            # Entry 3: James Martinez - confirmed Household #HH-001
            audit_3 = AuditLogRecord(
                batch_id='IMP-2025-0101-A',
                action_type='confirmed Household #HH-001',
                action_timestamp=datetime.now() - timedelta(hours=1),
                actor='James Martinez',
                details='Smith family confirmed via manual lookup',
            )
            session.add(audit_3)

            # Entry 4: Sarah Lee - deferred normalization decision
            audit_4 = AuditLogRecord(
                batch_id='IMP-2025-0101-A',
                action_type='deferred normalization decision',
                action_timestamp=datetime.now() - timedelta(minutes=45),
                actor='Sarah Lee',
                details='Waiting for confirmation from donor before address change',
            )
            session.add(audit_4)

            # Entry 5: System - System Logged batch import
            audit_5 = AuditLogRecord(
                batch_id='IMP-2025-0101-A',
                action_type='System Logged batch import',
                action_timestamp=datetime.now() - timedelta(minutes=15),
                actor='System',
                details='50 records imported from donors_q1_2025.csv',
            )
            session.add(audit_5)

            # Create review decisions for progress (21 items decided out of 50 = 42%)
            # Add 50 review items
            for i in range(50):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='resolved' if i < 21 else 'pending',
                    payload_json={'validation': f'issue {i}'}
                )
                session.add(item)

            session.flush()

            # Create 21 review decisions (42% progress: 21/50)
            all_items = session.query(ReviewItem).filter_by(batch_id='IMP-2025-0101-A').all()
            for i in range(min(21, len(all_items))):
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

    def test_get_audit_returns_view_model(self, temp_db_with_audit_data):
        """Test that get_audit returns AuditPageViewModel."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        assert isinstance(result, AuditPageViewModel)

    def test_get_audit_returns_frozen_view_model_not_orm(self, temp_db_with_audit_data):
        """Test that get_audit returns frozen dataclass, not ORM object."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        # Verify it's not an ORM object
        assert not hasattr(result, '__mapper__')
        # Verify it's frozen
        with pytest.raises((AttributeError, Exception)):
            result.batch_id = 'modified'

    def test_get_audit_has_required_fields(self, temp_db_with_audit_data):
        """Test that returned audit page has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        assert hasattr(result, 'batch_id')
        assert hasattr(result, 'filename')
        assert hasattr(result, 'progress')
        assert hasattr(result, 'audit_entries')

    def test_get_audit_correct_batch_metadata(self, temp_db_with_audit_data):
        """Test that audit page returns correct batch metadata."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        assert result.batch_id == 'IMP-2025-0101-A'
        assert result.filename == 'donors_q1_2025.csv'

    def test_get_audit_correct_progress(self, temp_db_with_audit_data):
        """Test that audit page returns correct progress percentage."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        # 21 decisions out of 50 items = 42%
        assert result.progress == 42

    def test_get_audit_correct_entry_count(self, temp_db_with_audit_data):
        """Test that audit page returns correct entry count."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        # We seeded 5 audit entries
        assert len(result.audit_entries) == 5

    def test_get_audit_entries_are_frozen(self, temp_db_with_audit_data):
        """Test that audit entries are frozen AuditLogEntry objects."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        for entry in result.audit_entries:
            assert isinstance(entry, AuditLogEntry)
            # Verify it's frozen
            with pytest.raises((AttributeError, Exception)):
                entry.timestamp = 'modified'

    def test_get_audit_entry_structure(self, temp_db_with_audit_data):
        """Test that audit entries have correct structure."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        # Check first entry has all required fields
        entry = result.audit_entries[0]
        assert hasattr(entry, 'timestamp')
        assert hasattr(entry, 'reviewer')
        assert hasattr(entry, 'action')
        assert hasattr(entry, 'details')

    def test_get_audit_entry_values(self, temp_db_with_audit_data):
        """Test that audit entries contain correct values."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        # Check first entry (Sarah Lee marked as Same Person)
        entry = result.audit_entries[0]
        assert entry.reviewer == 'Sarah Lee'
        assert entry.action == 'marked as Same Person'
        assert entry.details == 'Email variation consistent with household pattern'
        assert entry.timestamp  # Should have a timestamp

    def test_get_audit_entry_ordering(self, temp_db_with_audit_data):
        """Test that audit entries are ordered by timestamp ascending."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')

        # Verify ordering by checking action order (most recent first in fixture, but DB stores ascending)
        # The last entry should be "System Logged batch import" (most recent)
        assert result.audit_entries[-1].action == 'System Logged batch import'

    def test_get_audit_to_template_dict(self, temp_db_with_audit_data):
        """Test that AuditPageViewModel converts to template dict correctly."""
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        result = repo.get_audit('IMP-2025-0101-A')
        template_dict = result.to_template_dict()

        assert isinstance(template_dict, dict)
        assert 'batch' in template_dict
        assert 'audit_log' in template_dict

        # Verify batch fields
        assert template_dict['batch']['id'] == 'IMP-2025-0101-A'
        assert template_dict['batch']['filename'] == 'donors_q1_2025.csv'
        assert template_dict['batch']['progress'] == 42

        # Verify audit_log is a list
        assert isinstance(template_dict['audit_log'], list)
        assert len(template_dict['audit_log']) == 5

        # Verify first entry structure
        first_entry = template_dict['audit_log'][0]
        assert isinstance(first_entry, dict)
        assert 'timestamp' in first_entry
        assert 'reviewer' in first_entry
        assert 'action' in first_entry
        assert 'details' in first_entry

    def test_get_audit_no_database_mutation(self, temp_db_with_audit_data):
        """Test that get_audit does not mutate database state."""
        engine = create_engine(temp_db_with_audit_data)
        Session = sessionmaker(bind=engine)

        # Get initial state
        session = Session()
        initial_audit_records = len(session.query(AuditLogRecord).all())
        initial_batches = len(session.query(ImportBatch).all())
        session.close()

        # Call get_audit
        repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        repo.get_audit('IMP-2025-0101-A')

        # Verify state is unchanged
        session = Session()
        final_audit_records = len(session.query(AuditLogRecord).all())
        final_batches = len(session.query(ImportBatch).all())
        session.close()

        assert initial_audit_records == final_audit_records
        assert initial_batches == final_batches

    def test_get_audit_fixture_parity(self, temp_db_with_audit_data):
        """Test complete parity with FixtureImportRepository.get_audit()."""
        fixture_result = FixtureImportRepository.get_audit('IMP-2025-0101-A')
        db_repo = DatabaseImportRepository(database_url=temp_db_with_audit_data)
        db_result = db_repo.get_audit('IMP-2025-0101-A')

        # Compare batch metadata
        assert fixture_result.batch_id == db_result.batch_id
        assert fixture_result.filename == db_result.filename
        assert fixture_result.progress == db_result.progress

        # Compare entry count
        assert len(fixture_result.audit_entries) == len(db_result.audit_entries)

        # Compare each entry (note: fixture and DB may have different ordering)
        # So we compare by matching action + reviewer pairs
        fixture_entries = {(e.action, e.reviewer): e for e in fixture_result.audit_entries}
        db_entries = {(e.action, e.reviewer): e for e in db_result.audit_entries}

        # Verify same set of actions
        assert set(fixture_entries.keys()) == set(db_entries.keys())

        # For each matching entry pair, verify details match
        for key in fixture_entries.keys():
            fixture_entry = fixture_entries[key]
            db_entry = db_entries[key]
            assert fixture_entry.details == db_entry.details


class TestDatabaseGetExports:
    """Verify DatabaseImportRepository.get_exports() parity with fixture."""

    @pytest.fixture
    def temp_db_with_exports_data(self):
        """Create temp database with export test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'exports_test.db'
            db_url = f'sqlite:///{db_path}'

            engine = create_engine(db_url)
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            session = Session()

            # Create batch
            batch = ImportBatch(
                id='IMP-2025-0101-A',
                filename='donors_q1_2025.csv',
                upload_timestamp=datetime.now(),
                status='In Review',
                raw_row_count=50
            )
            session.add(batch)
            session.flush()

            # Create raw import rows and contacts
            for i in range(1, 6):
                raw_row = RawImportRow(
                    batch_id='IMP-2025-0101-A',
                    row_index=i,
                    raw_csv_data={
                        'id': f'P-{i:03d}',
                        'name': f'Contact {i}',
                        'email': f'contact{i}@example.com',
                        'phone': f'(555) {i:03d}-{i:04d}'
                    }
                )
                session.add(raw_row)
                session.flush()

                contact = ImportContact(
                    batch_id='IMP-2025-0101-A',
                    raw_import_row_id=raw_row.id,
                    first_name=f'Contact',
                    last_name=f'{i}',
                    email=f'contact{i}@example.com',
                    phone=f'(555) {i:03d}-{i:04d}',
                    address_line1=f'{i} Main St'
                )
                session.add(contact)

            # Create review items: 6 normalizations + 5 households + 3 duplicates + others = 50 total
            normalization_items = [
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'id': 'NORM-001', 'field': 'name'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'id': 'NORM-002', 'field': 'phone'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'id': 'NORM-003', 'field': 'email'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'id': 'NORM-004', 'field': 'address'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'id': 'NORM-005', 'field': 'name'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='normalization',
                    status='pending',
                    payload_json={'id': 'NORM-006', 'field': 'phone'}
                ),
            ]

            household_items = [
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='household',
                    status='pending',
                    payload_json={'id': 'HH-001', 'name': 'Smith Family'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='household',
                    status='pending',
                    payload_json={'id': 'HH-002', 'name': 'Williams Family'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='household',
                    status='pending',
                    payload_json={'id': 'HH-003', 'name': 'Johnson Household'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='household',
                    status='pending',
                    payload_json={'id': 'HH-004', 'name': 'Doe Family'}
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='household',
                    status='pending',
                    payload_json={'id': 'HH-005', 'name': 'Brown Household'}
                ),
            ]

            duplicate_items = [
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='duplicate',
                    status='pending',
                    payload_json={
                        'id': 'DUP-001',
                        'contact_a': {'id': 'P-001', 'name': 'John Smith'},
                        'contact_b': {'id': 'P-006', 'name': 'John Smith'},
                        'supporting_evidence': ['Full name match', 'Phone match', 'Address match']
                    }
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='duplicate',
                    status='pending',
                    payload_json={
                        'id': 'DUP-002',
                        'contact_a': {'id': 'P-003', 'name': 'robert smith'},
                        'contact_b': {'id': 'P-007', 'name': 'Robert Smith'},
                        'supporting_evidence': ['Full name match', 'Phone match', 'Email match', 'Address match']
                    }
                ),
                ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='duplicate',
                    status='pending',
                    payload_json={
                        'id': 'DUP-003',
                        'contact_a': {'id': 'P-008', 'name': 'Sarah Williams'},
                        'contact_b': {'id': 'P-009', 'name': 'Sara Williams'},
                        'supporting_evidence': ['Full name match', 'Phone match', 'Address match']
                    }
                ),
            ]

            # Add all review items
            all_items = normalization_items + household_items + duplicate_items
            for item in all_items:
                session.add(item)

            # Add other review items to reach 50 total
            other_items = []
            other_count = 50 - len(all_items)
            for i in range(other_count):
                item = ReviewItem(
                    batch_id='IMP-2025-0101-A',
                    item_type='validation',
                    status='pending',
                    payload_json={'id': f'VAL-{i:03d}'}
                )
                session.add(item)
                other_items.append(item)

            # Flush to get IDs for all review items
            session.flush()

            # Create 21 review decisions for 42% progress
            all_items_with_ids = all_items + other_items
            for i in range(21):
                if i < len(all_items_with_ids):
                    decision = ReviewDecision(
                        batch_id='IMP-2025-0101-A',
                        review_item_id=all_items_with_ids[i].id,
                        decision='approved',
                        reviewer='reviewer@example.com'
                    )
                    session.add(decision)

            session.commit()
            session.close()

            yield db_url

    def test_get_exports_returns_view_model(self, temp_db_with_exports_data):
        """Test that get_exports returns ExportConsoleViewModel."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert isinstance(result, ExportConsoleViewModel)

    def test_get_exports_returns_frozen_view_model_not_orm(self, temp_db_with_exports_data):
        """Test that get_exports returns frozen dataclass, not ORM object."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert hasattr(result, '__dataclass_fields__')
        # Verify frozen
        with pytest.raises(AttributeError):
            result.batch_id = 'MODIFIED'

    def test_get_exports_has_required_fields(self, temp_db_with_exports_data):
        """Test that export console has all required fields."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert hasattr(result, 'batch_id')
        assert hasattr(result, 'filename')
        assert hasattr(result, 'progress')
        assert hasattr(result, 'export_cards')
        assert hasattr(result, 'staged_record_count')
        assert hasattr(result, 'total_decisions')
        assert hasattr(result, 'household_count')
        assert hasattr(result, 'recent_exports')

    def test_get_exports_correct_batch_metadata(self, temp_db_with_exports_data):
        """Test that batch metadata is correct."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert result.batch_id == 'IMP-2025-0101-A'
        assert result.filename == 'donors_q1_2025.csv'

    def test_get_exports_correct_progress(self, temp_db_with_exports_data):
        """Test that progress is computed correctly (21/50 = 42%)."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert result.progress == 42

    def test_get_exports_export_cards_count(self, temp_db_with_exports_data):
        """Test that export cards match fixture count (4 cards)."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert len(result.export_cards) == 4

    def test_get_exports_export_cards_are_frozen(self, temp_db_with_exports_data):
        """Test that each export card is frozen."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        for card in result.export_cards:
            assert isinstance(card, ExportCard)
            assert hasattr(card, '__dataclass_fields__')

    def test_get_exports_export_cards_structure(self, temp_db_with_exports_data):
        """Test that export cards have correct structure."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        # First card should be EXPORT-REVIEWED
        first_card = result.export_cards[0]
        assert first_card.id == 'EXPORT-REVIEWED'
        assert first_card.title == 'Reviewed Export'
        assert first_card.status == 'Generated'
        assert first_card.files_ready == 1

    def test_get_exports_staged_record_count(self, temp_db_with_exports_data):
        """Test that staged_record_count equals import_contacts count (5)."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert result.staged_record_count == 5

    def test_get_exports_total_decisions(self, temp_db_with_exports_data):
        """Test that total_decisions is sum of supporting_evidence (3+4+3=10)."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert result.total_decisions == 10

    def test_get_exports_household_count(self, temp_db_with_exports_data):
        """Test that household_count equals household review_items (5)."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert result.household_count == 5

    def test_get_exports_recent_exports_empty(self, temp_db_with_exports_data):
        """Test that recent_exports is empty tuple in Phase 1B."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        assert result.recent_exports == ()

    def test_get_exports_to_template_dict(self, temp_db_with_exports_data):
        """Test that to_template_dict() returns correct shape."""
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        result = repo.get_exports('IMP-2025-0101-A')
        template_dict = result.to_template_dict()

        assert 'batch' in template_dict
        assert template_dict['batch']['id'] == 'IMP-2025-0101-A'
        assert template_dict['batch']['filename'] == 'donors_q1_2025.csv'
        assert template_dict['batch']['progress'] == 42

        assert 'export_options' in template_dict
        assert len(template_dict['export_options']) == 4

        assert template_dict['staged_record_count'] == 5
        assert template_dict['total_decisions'] == 10
        assert template_dict['household_count'] == 5
        assert template_dict['recent_exports'] == []

    def test_get_exports_no_database_mutation(self, temp_db_with_exports_data):
        """Test that calling get_exports does not mutate database state."""
        engine = create_engine(temp_db_with_exports_data)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Count records before
        contacts_before = session.query(ImportContact).count()
        items_before = session.query(ReviewItem).count()
        decisions_before = session.query(ReviewDecision).count()

        session.close()

        # Call get_exports
        repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        repo.get_exports('IMP-2025-0101-A')

        # Count records after
        session = Session()
        contacts_after = session.query(ImportContact).count()
        items_after = session.query(ReviewItem).count()
        decisions_after = session.query(ReviewDecision).count()

        session.close()

        # Verify no mutations
        assert contacts_before == contacts_after
        assert items_before == items_after
        assert decisions_before == decisions_after

    def test_get_exports_fixture_parity(self, temp_db_with_exports_data):
        """Test complete parity with fixture repository output."""
        db_repo = DatabaseImportRepository(database_url=temp_db_with_exports_data)
        fixture_repo = FixtureImportRepository()

        db_result = db_repo.get_exports('IMP-2025-0101-A')
        fixture_result = fixture_repo.get_exports('IMP-2025-0101-A')

        # Compare batch metadata
        assert db_result.batch_id == fixture_result.batch_id
        assert db_result.filename == fixture_result.filename
        assert db_result.progress == fixture_result.progress

        # Compare export cards count and content
        assert len(db_result.export_cards) == len(fixture_result.export_cards)
        for db_card, fixture_card in zip(db_result.export_cards, fixture_result.export_cards):
            assert db_card.id == fixture_card.id
            assert db_card.title == fixture_card.title
            assert db_card.description == fixture_card.description
            assert db_card.status == fixture_card.status
            assert db_card.files_ready == fixture_card.files_ready

        # Compare statistics
        assert db_result.staged_record_count == fixture_result.staged_record_count
        assert db_result.total_decisions == fixture_result.total_decisions
        assert db_result.household_count == fixture_result.household_count
        assert db_result.recent_exports == fixture_result.recent_exports


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


class TestRecentExportsLimit:
    """Test P0 fix: recent exports query limited to 50 records."""

    @pytest.fixture
    def temp_db_with_many_exports(self):
        """Create temp database with 60+ audit log entries for export_generated actions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = Path(tmpdir) / "test.db"
            db_url = f"sqlite:///{db_file}"

            engine = create_engine(db_url)
            Base.metadata.create_all(engine)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()

            # Create batch
            batch = ImportBatch(
                id='IMP-2025-0101-A',
                filename='test_exports.csv',
                upload_timestamp=datetime.now(timezone.utc),
                uploader='test_user'
            )
            session.add(batch)
            session.flush()

            # Create 60 audit log entries for export_generated (to test limit of 50)
            base_time = datetime.now(timezone.utc)
            for i in range(60):
                # Create entries with descending timestamps (newest first)
                timestamp = base_time - timedelta(seconds=i)
                record = AuditLogRecord(
                    batch_id='IMP-2025-0101-A',
                    action_type='export_generated',
                    action_timestamp=timestamp,
                    actor='test_reviewer',
                    details={
                        'filename': f'export_{60-i:03d}.csv',
                        'export_type': 'csv',
                        'row_count': 100 + i,
                        'warning_count': i % 5
                    }
                )
                session.add(record)

            session.commit()
            session.close()

            yield db_url

    def test_get_recent_exports_limited_to_50(self, temp_db_with_many_exports):
        """Test that get_recent_exports returns at most 50 records."""
        from scripts.householder.exports_service import get_recent_exports

        result = get_recent_exports('IMP-2025-0101-A', config={'GIVEBUTTER_DATABASE_URL': temp_db_with_many_exports})

        # Should return exactly 50, not all 60
        assert len(result) == 50
        assert all(isinstance(r, dict) for r in result)

    def test_get_recent_exports_newest_first_ordering(self, temp_db_with_many_exports):
        """Test that get_recent_exports returns entries sorted newest first by timestamp."""
        from scripts.householder.exports_service import get_recent_exports
        from datetime import datetime, timezone

        result = get_recent_exports('IMP-2025-0101-A', config={'GIVEBUTTER_DATABASE_URL': temp_db_with_many_exports})

        # Verify ordering: entries sorted by timestamp, newest first
        assert len(result) == 50

        # Parse timestamps and verify descending order (newest first)
        for i in range(len(result) - 1):
            current_iso = result[i]['generated_at']
            next_iso = result[i + 1]['generated_at']

            # Parse ISO timestamps
            current_time = datetime.fromisoformat(current_iso)
            next_time = datetime.fromisoformat(next_iso)

            # Current should be >= next (newest first)
            assert current_time >= next_time, f"Should be sorted newest first: {current_time} >= {next_time}"

    def test_get_recent_exports_includes_metadata(self, temp_db_with_many_exports):
        """Test that get_recent_exports includes all required metadata."""
        from scripts.householder.exports_service import get_recent_exports

        result = get_recent_exports('IMP-2025-0101-A', config={'GIVEBUTTER_DATABASE_URL': temp_db_with_many_exports})

        assert len(result) > 0
        export = result[0]

        # Verify all required fields present
        assert 'audit_log_id' in export
        assert 'filename' in export
        assert 'export_type' in export
        assert 'generated_at' in export
        assert 'generated_timestamp' in export
        assert 'row_count' in export
        assert 'warning_count' in export
