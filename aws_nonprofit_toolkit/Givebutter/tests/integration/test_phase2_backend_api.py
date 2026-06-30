"""
Phase 2 Backend API Tests for v1.1 Review Screen Refinement

Tests for:
1. Autosave append-only pattern
2. Deterministic latest decision (created_at DESC, id DESC)
3. Effective values derivation
4. Row status derivation
5. Issue recalculation
6. Approval flows (approved, approved_with_overrides)
7. Audit logging
"""

import pytest
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add scripts to path
scripts_path = Path(__file__).resolve().parents[3] / 'scripts'
sys.path.insert(0, str(scripts_path))

from householder.database_models import (
    init_db, ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject,
    ReviewDecision, AuditLogRecord, Base
)
from householder.autosave_service import autosave_row_corrections, get_effective_values
from householder.row_status_service import derive_row_status, is_row_overridden
from householder.issue_recalculation_service import recalculate_row_issues, is_issue_resolved
from householder.approval_service import approve_batch, get_batch_approval_status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def test_db():
    """Create isolated test database for Phase 2 tests."""
    db_path = 'test_phase2_backend.db'
    db_url = f'sqlite:///{db_path}'

    # Create and initialize database
    engine = create_engine(db_url, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield db_url

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def sample_batch(test_db):
    """Create sample batch with rows and validation issues."""
    engine = create_engine(test_db)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='BATCH-001',
            filename='test_batch.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='processing',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        row1 = RawImportRow(
            batch_id='BATCH-001',
            row_index=1,
            raw_csv_data={'name': 'John Doe', 'email': 'john@example.com', 'phone': '555-1234'}
        )
        row2 = RawImportRow(
            batch_id='BATCH-001',
            row_index=2,
            raw_csv_data={'name': 'Jane Smith', 'email': 'jane.smith@test.com', 'phone': ''}
        )
        session.add(row1)
        session.add(row2)
        session.flush()

        # Create validation issues
        issue1 = ReviewItem(
            batch_id='BATCH-001',
            item_type='validation',
            payload_json={'field': 'email', 'reason': 'possible_typo', 'description': 'Email may have typo', 'severity': 'warning'}
        )
        issue2 = ReviewItem(
            batch_id='BATCH-001',
            item_type='validation',
            payload_json={'field': 'phone', 'reason': 'missing', 'description': 'Phone number missing', 'severity': 'error'}
        )
        session.add(issue1)
        session.add(issue2)
        session.flush()

        # Link issues to rows
        subject1 = ReviewItemSubject(
            review_item_id=issue1.id,
            subject_type='import_raw_row',
            subject_id=row1.id
        )
        subject2 = ReviewItemSubject(
            review_item_id=issue2.id,
            subject_type='import_raw_row',
            subject_id=row2.id
        )
        session.add(subject1)
        session.add(subject2)

        session.commit()

        return {
            'batch_id': batch.id,
            'row1_id': row1.id,
            'row2_id': row2.id,
            'issue1_id': issue1.id,
            'issue2_id': issue2.id,
            'db_url': test_db
        }
    finally:
        session.close()


class TestAutosaveAppendOnly:
    """Test autosave creates append-only ReviewDecision records."""

    def test_autosave_creates_new_decision(self, sample_batch):
        """Autosave creates new ReviewDecision (not update)."""
        result = autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'john.doe@example.com'},
            database_url=sample_batch['db_url']
        )

        # Verify decision created
        assert result.decision_id > 0
        assert result.decision == 'accept_issue'
        assert result.effective_status == 'accepted'

    def test_autosave_multiple_decisions_per_row(self, sample_batch):
        """Multiple autosaves create multiple ReviewDecision records."""
        # First autosave
        result1 = autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'john.doe@example.com'},
            database_url=sample_batch['db_url']
        )

        # Second autosave (different field)
        result2 = autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'john.doe@example.com', 'phone': '555-9999'},
            database_url=sample_batch['db_url']
        )

        # Verify both decisions exist
        assert result1.decision_id != result2.decision_id

        # Verify both decisions are in database
        engine = create_engine(sample_batch['db_url'])
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            decisions = session.query(ReviewDecision).filter_by(
                batch_id=sample_batch['batch_id']
            ).all()
            assert len(decisions) >= 2
        finally:
            session.close()


class TestEffectiveValues:
    """Test effective values derivation (raw + corrections)."""

    def test_effective_values_without_corrections(self, sample_batch):
        """Effective values = raw values when no corrections."""
        effective = get_effective_values(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            database_url=sample_batch['db_url']
        )

        # Should return raw values
        assert effective['name'] == 'John Doe'
        assert effective['email'] == 'john@example.com'
        assert effective['phone'] == '555-1234'

    def test_effective_values_with_corrections(self, sample_batch):
        """Effective values merge raw + latest corrections."""
        # Create autosave with corrections
        autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'john.doe@example.com'},
            database_url=sample_batch['db_url']
        )

        effective = get_effective_values(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            database_url=sample_batch['db_url']
        )

        # Should have corrected email + raw name/phone
        assert effective['email'] == 'john.doe@example.com'
        assert effective['name'] == 'John Doe'  # raw
        assert effective['phone'] == '555-1234'  # raw

    def test_effective_values_deterministic_latest(self, sample_batch):
        """Effective values use deterministic 'latest' (created_at DESC, id DESC)."""
        # Create first autosave
        result1 = autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'v1@example.com'},
            database_url=sample_batch['db_url']
        )

        # Create second autosave
        result2 = autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'v2@example.com'},
            database_url=sample_batch['db_url']
        )

        # Effective values should use result2 (latest)
        effective = get_effective_values(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            database_url=sample_batch['db_url']
        )

        # Should have latest correction
        assert effective['email'] == 'v2@example.com'


class TestRowStatusDerivation:
    """Test row status derivation from review state."""

    def test_row_status_no_issues(self, sample_batch):
        """Row status = 'No issues' when no unresolved issues."""
        # Create a batch with no issues
        engine = create_engine(sample_batch['db_url'])
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            batch = ImportBatch(
                id='CLEAN-BATCH',
                filename='clean.csv',
                upload_timestamp=datetime.now(timezone.utc),
                status='processing',
                raw_row_count=1
            )
            session.add(batch)
            session.flush()

            row = RawImportRow(
                batch_id='CLEAN-BATCH',
                row_index=1,
                raw_csv_data={'name': 'Clean Row'}
            )
            session.add(row)
            session.commit()

            # Query status for row with no issues
            status = derive_row_status(
                batch_id='CLEAN-BATCH',
                raw_import_row_id=row.id,
                database_url=sample_batch['db_url']
            )

            assert status == 'No issues'
        finally:
            session.close()

    def test_row_status_warning(self, sample_batch):
        """Row status = 'Warning' when only warning issues unresolved."""
        status = derive_row_status(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            database_url=sample_batch['db_url']
        )

        # Row 1 has warning (email typo)
        assert status == 'Warning'

    def test_row_status_blocking(self, sample_batch):
        """Row status = 'Blocking' when error/blocking issues unresolved."""
        status = derive_row_status(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row2_id'],
            database_url=sample_batch['db_url']
        )

        # Row 2 has error (missing phone)
        assert status == 'Blocking'


class TestIssueRecalculation:
    """Test issue recalculation with effective values."""

    def test_issues_resolved_by_correction(self, sample_batch):
        """Issue resolved when corrected."""
        # Before correction: issue should exist
        issues_before = recalculate_row_issues(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            database_url=sample_batch['db_url']
        )

        assert len(issues_before) > 0  # Email typo issue exists

        # Apply correction
        autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'john.doe@example.com'},
            database_url=sample_batch['db_url']
        )

        # After correction: issue should be resolved (not in list)
        issues_after = recalculate_row_issues(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            database_url=sample_batch['db_url']
        )

        # Issue should be resolved
        assert len(issues_after) == 0 or issues_after[0]['field'] != 'email'

    def test_is_issue_resolved_logic(self):
        """is_issue_resolved returns correct boolean with two-tier validation and typo detection."""
        # Missing issue resolved when value present
        assert is_issue_resolved('phone', '555-1234', 'missing') is True

        # Missing issue not resolved when empty
        assert is_issue_resolved('phone', '', 'missing') is False

        # === Common typo domains (detected for all emails) ===
        # Common typo not resolved (no correction made)
        assert is_issue_resolved('email', 'user@gamil.com', 'possible_typo', raw_value='user@gamil.com') is False

        # Common typo resolved when corrected
        assert is_issue_resolved('email', 'user@gmail.com', 'possible_typo', raw_value='user@gamil.com') is True

        # Other typo domains detected
        assert is_issue_resolved('email', 'user@yahooo.com', 'possible_typo', raw_value='user@yahooo.com') is False
        assert is_issue_resolved('email', 'user@yahoo.com', 'possible_typo', raw_value='user@yahooo.com') is True

        # === TIER 1: Recognized domains (strict validation) ===
        # Gmail typo not resolved (no correction made)
        assert is_issue_resolved('email', 'user@gmial.com', 'possible_typo', raw_value='user@gmial.com') is False

        # Gmail typo resolved when corrected to valid format
        assert is_issue_resolved('email', 'user@gmail.com', 'possible_typo', raw_value='user@gmial.com') is True

        # Hotmail typo resolved when corrected
        assert is_issue_resolved('email', 'user@hotmail.com', 'possible_typo', raw_value='user@hotmial.com') is True

        # === TIER 2: Unrecognized domains (lenient validation) ===
        # Corporate domain accepted (format valid)
        assert is_issue_resolved('email', 'user@mycompany.com', 'possible_typo', raw_value='user@test.com') is True

        # Czech domain accepted (format valid)
        assert is_issue_resolved('email', 'user@mail.cz', 'possible_typo', raw_value='user@test.com') is True

        # Multi-part unrecognized domain accepted
        assert is_issue_resolved('email', 'user@company.co.uk', 'possible_typo', raw_value='user@test.com') is True

        # === Invalid formats (all domains) ===
        # Format validation: double @ rejected
        assert is_issue_resolved('email', 'user@@gmail.com', 'possible_typo', raw_value='user@gmial.com') is False

        # Format validation: missing local part rejected
        assert is_issue_resolved('email', '@gmail.com', 'possible_typo', raw_value='user@gmial.com') is False

        # Format validation: missing TLD rejected
        assert is_issue_resolved('email', 'user@gmail', 'possible_typo', raw_value='user@gmial.com') is False

        # Typo without raw_value cannot be determined as resolved
        assert is_issue_resolved('email', 'corrected@example.com', 'typo') is False

        # Unknown reason not auto-resolved
        assert is_issue_resolved('field', 'value', 'unknown') is False


class TestApprovalFlows:
    """Test batch approval workflows."""

    def test_approve_batch_no_issues(self, sample_batch):
        """Approve batch without overrides (no remaining issues)."""
        result = approve_batch(
            batch_id=sample_batch['batch_id'],
            approval_status='approved',
            database_url=sample_batch['db_url']
        )

        assert result['success'] is True
        assert result['approval_status'] == 'approved'
        assert result['override_count'] == 0
        assert result['audit_log_id'] > 0

    def test_approve_batch_with_overrides(self, sample_batch):
        """Approve batch with overrides (remaining issues)."""
        rows_with_overrides = [
            {
                'raw_import_row_id': sample_batch['row2_id'],
                'row_index': 2,
                'issues': [{'field': 'phone', 'reason': 'missing'}]
            }
        ]

        result = approve_batch(
            batch_id=sample_batch['batch_id'],
            approval_status='approved_with_overrides',
            rows_with_overrides=rows_with_overrides,
            database_url=sample_batch['db_url']
        )

        assert result['success'] is True
        assert result['approval_status'] == 'approved_with_overrides'
        assert result['override_count'] == 1
        assert result['audit_log_id'] > 0

        # Verify override_details persisted
        status = get_batch_approval_status(
            batch_id=sample_batch['batch_id'],
            database_url=sample_batch['db_url']
        )

        assert status['approval_status'] == 'approved_with_overrides'
        assert status['override_count'] == 1
        assert status['override_details'] is not None

    def test_cannot_re_approve_batch(self, sample_batch):
        """Cannot re-approve already approved batch."""
        # First approval
        approve_batch(
            batch_id=sample_batch['batch_id'],
            approval_status='approved',
            database_url=sample_batch['db_url']
        )

        # Second approval should fail
        with pytest.raises(ValueError, match="already approved"):
            approve_batch(
                batch_id=sample_batch['batch_id'],
                approval_status='approved',
                database_url=sample_batch['db_url']
            )

    def test_is_row_overridden(self, sample_batch):
        """Check if row is in override_details."""
        # Before approval: not overridden
        assert is_row_overridden(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row2_id'],
            database_url=sample_batch['db_url']
        ) is False

        # Approve with overrides
        approve_batch(
            batch_id=sample_batch['batch_id'],
            approval_status='approved_with_overrides',
            rows_with_overrides=[{
                'raw_import_row_id': sample_batch['row2_id'],
                'row_index': 2,
                'issues': [{'field': 'phone', 'reason': 'missing'}]
            }],
            database_url=sample_batch['db_url']
        )

        # After approval: overridden
        assert is_row_overridden(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row2_id'],
            database_url=sample_batch['db_url']
        ) is True


class TestAuditLogging:
    """Test audit log records for Phase 2 actions."""

    def test_approval_creates_audit_record(self, sample_batch):
        """Approval action creates AuditLogRecord."""
        result = approve_batch(
            batch_id=sample_batch['batch_id'],
            approval_status='approved',
            reviewer='test-reviewer',
            database_url=sample_batch['db_url']
        )

        # Verify audit record exists
        engine = create_engine(sample_batch['db_url'])
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            audit = session.query(AuditLogRecord).filter_by(
                id=result['audit_log_id']
            ).first()

            assert audit is not None
            assert audit.action_type == 'batch_approved'
            assert audit.actor == 'test-reviewer'
            assert audit.details['approval_status'] == 'approved'
        finally:
            session.close()


class TestDataImmutability:
    """Test that raw data remains unchanged."""

    def test_raw_data_unchanged_after_autosave(self, sample_batch):
        """RawImportRow.raw_csv_data unchanged after autosave."""
        # Get original raw data
        engine = create_engine(sample_batch['db_url'])
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            row_before = session.query(RawImportRow).filter_by(
                id=sample_batch['row1_id']
            ).first()
            original_raw = dict(row_before.raw_csv_data)
        finally:
            session.close()

        # Apply autosave
        autosave_row_corrections(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            corrected_values={'email': 'corrected@example.com'},
            database_url=sample_batch['db_url']
        )

        # Verify raw data unchanged
        engine = create_engine(sample_batch['db_url'])
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            row_after = session.query(RawImportRow).filter_by(
                id=sample_batch['row1_id']
            ).first()

            assert row_after.raw_csv_data == original_raw
        finally:
            session.close()

    def test_review_item_unchanged_after_recalculation(self, sample_batch):
        """ReviewItem.payload_json unchanged after issue recalculation."""
        # Get original issue payload
        engine = create_engine(sample_batch['db_url'])
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            issue_before = session.query(ReviewItem).filter_by(
                id=sample_batch['issue1_id']
            ).first()
            original_payload = dict(issue_before.payload_json)
        finally:
            session.close()

        # Recalculate issues
        recalculate_row_issues(
            batch_id=sample_batch['batch_id'],
            raw_import_row_id=sample_batch['row1_id'],
            database_url=sample_batch['db_url']
        )

        # Verify payload unchanged
        engine = create_engine(sample_batch['db_url'])
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            issue_after = session.query(ReviewItem).filter_by(
                id=sample_batch['issue1_id']
            ).first()

            assert issue_after.payload_json == original_payload
        finally:
            session.close()
