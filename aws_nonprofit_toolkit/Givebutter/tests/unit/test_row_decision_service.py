"""
Unit tests for row_decision_service - reviewer status decisions.

Tests:
- Recording accept, follow-up, defer, reject decisions
- Notes required for follow-up
- Notes optional for defer
- Clear decision
- Querying decisions
- Getting rows with follow-up/defer
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import Base, ImportBatch, RawImportRow, ReviewDecision
from scripts.householder.row_decision_service import (
    record_row_decision,
    get_row_decision,
    get_rows_with_follow_up,
    get_rows_with_defer,
)


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    # Create test batch and rows
    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='test-batch-001',
        filename='test.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=3
    )
    session.add(batch)
    session.flush()

    rows = []
    for i in range(1, 4):
        row = RawImportRow(
            batch_id='test-batch-001',
            row_index=i,
            raw_csv_data={'name': f'Person {i}', 'email': f'person{i}@example.com'}
        )
        session.add(row)
        rows.append(row)

    session.commit()
    row_ids = [r.id for r in rows]
    session.close()

    yield database_url, row_ids

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestRecordRowDecision:
    """Test recording row-level status decisions."""

    def test_record_accept_as_is_decision(self, temp_db):
        """Test recording 'accept_as_is' decision."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        result = record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='accept_as_is',
            database_url=db_url
        )

        assert result['success'] is True
        assert result['decision'] == 'accept_as_is'
        assert 'decision_id' in result
        assert 'timestamp' in result

    def test_record_needs_follow_up_with_notes(self, temp_db):
        """Test recording 'needs_follow_up' decision with notes."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        result = record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Verify phone number with contact',
            database_url=db_url
        )

        assert result['success'] is True
        assert result['decision'] == 'needs_follow_up'

    def test_follow_up_requires_notes(self, temp_db):
        """Test that 'needs_follow_up' decision requires notes."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        with pytest.raises(ValueError) as exc_info:
            record_row_decision(
                batch_id='test-batch-001',
                raw_import_row_id=raw_id,
                decision='needs_follow_up',
                notes=None,
                database_url=db_url
            )

        assert 'Notes are required' in str(exc_info.value)

    def test_record_defer_without_notes(self, temp_db):
        """Test that 'defer' decision doesn't require notes."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        result = record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='defer',
            database_url=db_url
        )

        assert result['success'] is True
        assert result['decision'] == 'defer'

    def test_record_reject_row_decision(self, temp_db):
        """Test recording 'reject_row' decision."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        result = record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='reject_row',
            notes='Data quality issues',
            database_url=db_url
        )

        assert result['success'] is True
        assert result['decision'] == 'reject_row'

    def test_record_clear_decision(self, temp_db):
        """Test recording 'clear_decision' to reset to system status."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        # First record a decision
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Check address',
            database_url=db_url
        )

        # Then clear it
        result = record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=db_url
        )

        assert result['success'] is True
        assert result['decision'] == 'clear_decision'

    def test_invalid_decision_raises_error(self, temp_db):
        """Test that invalid decision type raises error."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        with pytest.raises(ValueError) as exc_info:
            record_row_decision(
                batch_id='test-batch-001',
                raw_import_row_id=raw_id,
                decision='invalid_decision',
                database_url=db_url
            )

        assert 'Invalid decision' in str(exc_info.value)

    def test_nonexistent_batch_raises_error(self, temp_db):
        """Test that nonexistent batch raises error."""
        db_url, row_ids = temp_db

        with pytest.raises(ValueError) as exc_info:
            record_row_decision(
                batch_id='nonexistent-batch',
                raw_import_row_id=row_ids[0],
                decision='accept_as_is',
                database_url=db_url
            )

        assert 'not found' in str(exc_info.value)

    def test_nonexistent_row_raises_error(self, temp_db):
        """Test that nonexistent row raises error."""
        db_url, row_ids = temp_db

        with pytest.raises(ValueError) as exc_info:
            record_row_decision(
                batch_id='test-batch-001',
                raw_import_row_id=99999,
                decision='accept_as_is',
                database_url=db_url
            )

        assert 'not found' in str(exc_info.value)


class TestGetRowDecision:
    """Test retrieving row decisions."""

    def test_get_latest_decision(self, temp_db):
        """Test getting the latest decision for a row."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        # Record a decision
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Verify phone',
            database_url=db_url
        )

        # Get the decision
        decision = get_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            database_url=db_url
        )

        assert decision is not None
        assert decision['decision'] == 'needs_follow_up'
        assert decision['notes'] == 'Verify phone'
        assert 'timestamp' in decision

    def test_get_no_decision_returns_none(self, temp_db):
        """Test that no decision returns None."""
        db_url, row_ids = temp_db

        decision = get_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[0],
            database_url=db_url
        )

        assert decision is None

    def test_clear_decision_returns_none(self, temp_db):
        """Test that cleared decision returns None (system status applies)."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        # Record and then clear
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Check data',
            database_url=db_url
        )

        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=db_url
        )

        # Get decision should return None (cleared)
        decision = get_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            database_url=db_url
        )

        assert decision is None

    def test_multiple_decisions_returns_latest(self, temp_db):
        """Test that multiple decisions return the latest one."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        # Record first decision
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='defer',
            database_url=db_url
        )

        # Record second decision
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='accept_as_is',
            database_url=db_url
        )

        # Get should return latest
        decision = get_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            database_url=db_url
        )

        assert decision is not None
        assert decision['decision'] == 'accept_as_is'


class TestGetRowsWithFollowUp:
    """Test querying rows with follow-up decisions."""

    def test_get_rows_with_follow_up(self, temp_db):
        """Test getting all rows with follow-up decisions."""
        db_url, row_ids = temp_db

        # Record follow-up for rows 0 and 1
        for i in range(2):
            record_row_decision(
                batch_id='test-batch-001',
                raw_import_row_id=row_ids[i],
                decision='needs_follow_up',
                notes='Check data',
                database_url=db_url
            )

        # Record different decision for row 2
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[2],
            decision='defer',
            database_url=db_url
        )

        # Get follow-up rows
        follow_up_rows = get_rows_with_follow_up(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert len(follow_up_rows) == 2
        assert row_ids[0] in follow_up_rows
        assert row_ids[1] in follow_up_rows
        assert row_ids[2] not in follow_up_rows

    def test_follow_up_not_in_list_after_clear(self, temp_db):
        """Test that cleared follow-up is not in list."""
        db_url, row_ids = temp_db
        raw_id = row_ids[0]

        # Record follow-up
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Check',
            database_url=db_url
        )

        # Clear it
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=db_url
        )

        # Should not be in follow-up list
        follow_up_rows = get_rows_with_follow_up(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert raw_id not in follow_up_rows


class TestGetRowsWithDefer:
    """Test querying rows with defer decisions."""

    def test_get_rows_with_defer(self, temp_db):
        """Test getting all rows with defer decisions."""
        db_url, row_ids = temp_db

        # Record defer for rows 0 and 1
        for i in range(2):
            record_row_decision(
                batch_id='test-batch-001',
                raw_import_row_id=row_ids[i],
                decision='defer',
                database_url=db_url
            )

        # Record different decision for row 2
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[2],
            decision='accept_as_is',
            database_url=db_url
        )

        # Get defer rows
        defer_rows = get_rows_with_defer(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert len(defer_rows) == 2
        assert row_ids[0] in defer_rows
        assert row_ids[1] in defer_rows
        assert row_ids[2] not in defer_rows
