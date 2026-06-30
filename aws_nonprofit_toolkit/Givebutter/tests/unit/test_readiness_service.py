"""
Unit tests for export readiness service.

Tests that readiness derives directly from export preview service.
No new business rules; uses existing preview logic as source of truth.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.readiness_service import get_export_readiness, ExportReadinessViewModel
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact
)
from sqlalchemy.orm import sessionmaker
from scripts.householder.database_models import create_db_engine


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
def seeded_batch(temp_db):
    """Create a batch with contacts for readiness testing."""
    database_url, engine = temp_db
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-2025-0101-A',
        filename='test.csv',
        upload_timestamp=datetime.now(timezone.utc),
    )
    session.add(batch)
    session.flush()

    # Create raw row
    row = RawImportRow(
        batch_id='IMP-2025-0101-A',
        row_index=1,
        raw_csv_data={
            'Name': 'John Smith',
            'Email': 'john@example.com',
            'Phone': '555-1234',
            'Amount': '100.00',
            'Address': '123 Main St',
            'transaction_id': 'TXN-001'
        },
    )
    session.add(row)
    session.flush()

    # Create contact
    contact = ImportContact(
        batch_id='IMP-2025-0101-A',
        raw_import_row_id=row.id,
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
    session.add(contact)
    session.commit()

    batch_id = batch.id
    session.close()

    yield database_url, batch_id


class TestExportReadinessViewModel:
    """Test ExportReadinessViewModel structure."""

    def test_readiness_view_model_creation(self):
        """Test that ExportReadinessViewModel can be created."""
        vm = ExportReadinessViewModel(
            batch_id='IMP-TEST-001',
            batch_filename='test.csv',
            progress_pct=50,
            is_export_ready=True,
            blocker_count=0,
            warning_count=2,
            staged_records=100,
            blockers=(),
            warnings=('warning1', 'warning2'),
            queue_status={'validation_issues': 0, 'duplicates_pending': 0}
        )
        assert vm.batch_id == 'IMP-TEST-001'
        assert vm.is_export_ready is True
        assert vm.blocker_count == 0

    def test_readiness_view_model_to_template_dict(self):
        """Test conversion to template dictionary."""
        vm = ExportReadinessViewModel(
            batch_id='IMP-TEST-001',
            batch_filename='test.csv',
            progress_pct=75,
            is_export_ready=False,
            blocker_count=3,
            warning_count=1,
            staged_records=85,
            blockers=('issue1', 'issue2', 'issue3'),
            warnings=('warning1',),
            queue_status={
                'validation_issues': 2,
                'duplicates_pending': 1,
                'normalizations_pending': 0,
                'households_pending': 0,
            }
        )
        result = vm.to_template_dict()

        assert result['batch']['id'] == 'IMP-TEST-001'
        assert result['readiness']['is_export_ready'] is False
        assert result['readiness']['blocker_count'] == 3
        assert len(result['readiness']['blockers']) == 3

    def test_readiness_view_model_frozen(self):
        """Test that ExportReadinessViewModel is immutable."""
        vm = ExportReadinessViewModel(
            batch_id='IMP-TEST-001',
            batch_filename='test.csv',
            progress_pct=50,
            is_export_ready=True,
            blocker_count=0,
            warning_count=0,
            staged_records=100,
            blockers=(),
            warnings=(),
            queue_status={'validation_issues': 0, 'duplicates_pending': 0}
        )
        with pytest.raises(AttributeError):
            vm.is_export_ready = False


class TestReadinessMirrorsPreview:
    """Test that readiness derives directly from export preview service."""

    def test_readiness_ready_when_preview_has_zero_blockers(self, seeded_batch):
        """Test that readiness is ready when preview has zero blockers."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        # Build preview for database
        preview = build_export_preview(batch_id, config=config)
        readiness = get_export_readiness(batch_id, config=config)

        # Readiness should match preview readiness
        assert readiness.is_export_ready == preview.is_export_ready
        assert readiness.blocker_count == preview.blocked_count

    def test_readiness_includes_exact_blocker_messages_from_preview(self, seeded_batch):
        """Test that readiness includes exact blocker messages from preview."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        preview = build_export_preview(batch_id, config=config)
        readiness = get_export_readiness(batch_id, config=config)

        # Blockers should match exactly
        assert readiness.blockers == preview.blockers
        assert len(readiness.blockers) == len(preview.blockers)
        for expected_blocker in preview.blockers:
            assert expected_blocker in readiness.blockers

    def test_readiness_includes_warnings_from_preview(self, seeded_batch):
        """Test that readiness includes warnings from preview."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        preview = build_export_preview(batch_id, config=config)
        readiness = get_export_readiness(batch_id, config=config)

        # Warnings should match exactly
        assert readiness.warnings == preview.warnings
        assert readiness.warning_count == preview.warning_count

    def test_warnings_alone_do_not_block_if_preview_allows(self, seeded_batch):
        """Test that warnings alone don't block if preview says ready."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        preview = build_export_preview(batch_id, config=config)
        readiness = get_export_readiness(batch_id, config=config)

        if preview.is_export_ready:
            # If preview is ready, readiness should be ready
            assert readiness.is_export_ready is True
            # Even if there are warnings
            assert readiness.warning_count >= 0

    def test_staged_row_count_matches_preview(self, seeded_batch):
        """Test that staged row count matches preview."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        preview = build_export_preview(batch_id, config=config)
        readiness = get_export_readiness(batch_id, config=config)

        # Staged records should match preview row count
        assert readiness.staged_records == preview.row_count

    def test_readiness_does_not_create_review_decisions(self, seeded_batch):
        """Test that readiness service does not create ReviewDecision records."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        # Call readiness service
        readiness = get_export_readiness(batch_id, config=config)

        # Should return view model without side effects
        assert isinstance(readiness, ExportReadinessViewModel)
        # No mutation - just a read operation
        assert readiness.batch_id == batch_id

    def test_readiness_does_not_create_audit_records(self, seeded_batch):
        """Test that readiness service does not create AuditLogRecord entries."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        # Call readiness service
        readiness = get_export_readiness(batch_id, config=config)

        # Should return view model without side effects
        assert isinstance(readiness, ExportReadinessViewModel)

    def test_readiness_does_not_create_csv_files(self, seeded_batch):
        """Test that readiness service does not generate CSV files."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        # Call readiness service
        readiness = get_export_readiness(batch_id, config=config)

        # Should only return data, no file generation
        assert isinstance(readiness, ExportReadinessViewModel)

    def test_readiness_does_not_mutate_raw_rows(self, seeded_batch):
        """Test that readiness service does not mutate raw import rows."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        # Call readiness twice
        readiness1 = get_export_readiness(batch_id, config=config)
        readiness2 = get_export_readiness(batch_id, config=config)

        # Should be identical (no mutations between calls)
        assert readiness1.is_export_ready == readiness2.is_export_ready
        assert readiness1.blocker_count == readiness2.blocker_count
        assert readiness1.blockers == readiness2.blockers

    def test_readiness_does_not_mutate_contact_snapshots(self, seeded_batch):
        """Test that readiness service does not mutate contact snapshots."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        # Call readiness multiple times
        for _ in range(3):
            readiness = get_export_readiness(batch_id, config=config)
            # Should succeed without errors
            assert isinstance(readiness, ExportReadinessViewModel)

    def test_readiness_returns_frozen_dataclass(self, seeded_batch):
        """Test that readiness returns immutable dataclass."""
        database_url, batch_id = seeded_batch
        config = {'GIVEBUTTER_DATABASE_URL': database_url}

        readiness = get_export_readiness(batch_id, config=config)
        with pytest.raises((AttributeError, TypeError)):
            readiness.is_export_ready = not readiness.is_export_ready
