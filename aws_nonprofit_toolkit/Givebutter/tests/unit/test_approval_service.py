"""
Unit tests for approval_service - batch approval workflow.

Tests:
- Batch approval with and without overrides
- Checking for remaining issues including follow-up and defer decisions
- Audit log creation
- Batch approval status queries
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject,
    ReviewDecision, AuditLogRecord
)
from scripts.householder.approval_service import (
    approve_batch,
    check_batch_remaining_issues,
    get_batch_approval_status,
)
from scripts.householder.row_decision_service import (
    record_row_decision,
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


class TestApproveBatch:
    """Test batch approval workflow."""

    def test_approve_batch_simple(self, temp_db):
        """Test simple batch approval without overrides."""
        db_url, row_ids = temp_db

        result = approve_batch(
            batch_id='test-batch-001',
            approval_status='approved',
            database_url=db_url
        )

        assert result['success'] is True
        assert result['approval_status'] == 'approved'
        assert result['override_count'] == 0
        assert 'audit_log_id' in result

    def test_approve_batch_with_overrides(self, temp_db):
        """Test batch approval with overrides."""
        db_url, row_ids = temp_db

        overrides = [
            {
                'raw_import_row_id': row_ids[0],
                'row_index': 1,
                'issues': [{'field': 'email', 'reason': 'Invalid format'}]
            }
        ]

        result = approve_batch(
            batch_id='test-batch-001',
            approval_status='approved_with_overrides',
            rows_with_overrides=overrides,
            database_url=db_url
        )

        assert result['success'] is True
        assert result['approval_status'] == 'approved_with_overrides'
        assert result['override_count'] == 1

    def test_invalid_approval_status_raises_error(self, temp_db):
        """Test that invalid approval_status raises error."""
        db_url, row_ids = temp_db

        with pytest.raises(ValueError) as exc_info:
            approve_batch(
                batch_id='test-batch-001',
                approval_status='invalid_status',
                database_url=db_url
            )

        assert 'Invalid approval_status' in str(exc_info.value)

    def test_nonexistent_batch_raises_error(self, temp_db):
        """Test that nonexistent batch raises error."""
        db_url, row_ids = temp_db

        with pytest.raises(ValueError) as exc_info:
            approve_batch(
                batch_id='nonexistent-batch',
                approval_status='approved',
                database_url=db_url
            )

        assert 'not found' in str(exc_info.value)

    def test_cannot_re_approve_batch(self, temp_db):
        """Test that already approved batch cannot be re-approved."""
        db_url, row_ids = temp_db

        # First approval
        approve_batch(
            batch_id='test-batch-001',
            approval_status='approved',
            database_url=db_url
        )

        # Try to re-approve
        with pytest.raises(ValueError) as exc_info:
            approve_batch(
                batch_id='test-batch-001',
                approval_status='approved',
                database_url=db_url
            )

        assert 'already' in str(exc_info.value)

    def test_approval_creates_audit_log(self, temp_db):
        """Test that batch approval creates AuditLogRecord."""
        db_url, row_ids = temp_db

        result = approve_batch(
            batch_id='test-batch-001',
            approval_status='approved',
            reviewer='test-reviewer',
            database_url=db_url
        )

        # Verify audit log was created
        Session = sessionmaker(bind=create_engine(db_url))
        session = Session()
        audit = session.query(AuditLogRecord).filter_by(
            id=result['audit_log_id']
        ).first()
        assert audit is not None
        assert audit.action_type == 'batch_approved'
        assert audit.actor == 'test-reviewer'
        session.close()


class TestCheckBatchRemainingIssues:
    """Test checking for remaining issues before approval."""

    def test_no_issues_returns_empty_list(self, temp_db):
        """Test that batch with no issues returns empty list."""
        db_url, row_ids = temp_db

        issues = check_batch_remaining_issues(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert issues == []

    def test_includes_rows_with_follow_up_decisions(self, temp_db):
        """Test that rows with follow-up decisions are included in remaining issues."""
        db_url, row_ids = temp_db

        # Record a follow-up decision on first row
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[0],
            decision='needs_follow_up',
            notes='Verify phone number',
            database_url=db_url
        )

        issues = check_batch_remaining_issues(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert len(issues) == 1
        assert issues[0]['raw_import_row_id'] == row_ids[0]
        assert issues[0]['row_index'] == 1
        assert issues[0]['decision_warning'] == 'needs_follow_up'
        assert 'Needs follow-up' in issues[0]['issues'][0]['reason']

    def test_includes_rows_with_defer_decisions(self, temp_db):
        """Test that rows with defer decisions are included in remaining issues."""
        db_url, row_ids = temp_db

        # Record a defer decision on first row
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[0],
            decision='defer',
            database_url=db_url
        )

        issues = check_batch_remaining_issues(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert len(issues) == 1
        assert issues[0]['raw_import_row_id'] == row_ids[0]
        assert issues[0]['row_index'] == 1
        assert issues[0]['decision_warning'] == 'defer'
        assert 'Deferred' in issues[0]['issues'][0]['reason']

    def test_includes_multiple_rows_with_decisions(self, temp_db):
        """Test that multiple rows with different decisions are all included."""
        db_url, row_ids = temp_db

        # Record follow-up for row 0
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[0],
            decision='needs_follow_up',
            notes='Check data',
            database_url=db_url
        )

        # Record defer for row 1
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[1],
            decision='defer',
            database_url=db_url
        )

        issues = check_batch_remaining_issues(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert len(issues) == 2

        # Check follow-up row
        follow_up_row = [i for i in issues if i['raw_import_row_id'] == row_ids[0]][0]
        assert follow_up_row['decision_warning'] == 'needs_follow_up'

        # Check defer row
        defer_row = [i for i in issues if i['raw_import_row_id'] == row_ids[1]][0]
        assert defer_row['decision_warning'] == 'defer'

    def test_cleared_decisions_not_included(self, temp_db):
        """Test that rows with cleared decisions are not included."""
        db_url, row_ids = temp_db

        # Record and clear a decision
        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[0],
            decision='needs_follow_up',
            notes='Check',
            database_url=db_url
        )

        record_row_decision(
            batch_id='test-batch-001',
            raw_import_row_id=row_ids[0],
            decision='clear_decision',
            database_url=db_url
        )

        issues = check_batch_remaining_issues(
            batch_id='test-batch-001',
            database_url=db_url
        )

        # No issues should be returned for cleared decision
        assert issues == []

    def test_nonexistent_batch_raises_error(self, temp_db):
        """Test that nonexistent batch raises error."""
        db_url, row_ids = temp_db

        with pytest.raises(ValueError) as exc_info:
            check_batch_remaining_issues(
                batch_id='nonexistent-batch',
                database_url=db_url
            )

        assert 'not found' in str(exc_info.value)


class TestGetBatchApprovalStatus:
    """Test retrieving batch approval status."""

    def test_get_approval_status_not_approved(self, temp_db):
        """Test getting approval status of unapproved batch."""
        db_url, row_ids = temp_db

        status = get_batch_approval_status(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert status['batch_id'] == 'test-batch-001'
        assert status['approval_status'] is None
        assert status['override_count'] == 0
        assert status['override_details'] is None

    def test_get_approval_status_approved(self, temp_db):
        """Test getting approval status of approved batch."""
        db_url, row_ids = temp_db

        approve_batch(
            batch_id='test-batch-001',
            approval_status='approved',
            database_url=db_url
        )

        status = get_batch_approval_status(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert status['approval_status'] == 'approved'
        assert status['override_count'] == 0

    def test_get_approval_status_with_overrides(self, temp_db):
        """Test getting approval status of batch with overrides."""
        db_url, row_ids = temp_db

        overrides = [
            {'raw_import_row_id': row_ids[0], 'row_index': 1, 'issues': []},
            {'raw_import_row_id': row_ids[1], 'row_index': 2, 'issues': []},
        ]

        approve_batch(
            batch_id='test-batch-001',
            approval_status='approved_with_overrides',
            rows_with_overrides=overrides,
            database_url=db_url
        )

        status = get_batch_approval_status(
            batch_id='test-batch-001',
            database_url=db_url
        )

        assert status['approval_status'] == 'approved_with_overrides'
        assert status['override_count'] == 2

    def test_nonexistent_batch_raises_error(self, temp_db):
        """Test that nonexistent batch raises error."""
        db_url, row_ids = temp_db

        with pytest.raises(ValueError) as exc_info:
            get_batch_approval_status(
                batch_id='nonexistent-batch',
                database_url=db_url
            )

        assert 'not found' in str(exc_info.value)
