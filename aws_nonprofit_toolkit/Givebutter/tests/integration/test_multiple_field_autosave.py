"""
Integration tests for multiple field autosave and issue display.

Critical use cases that should NOT regress:
1. Autosaving multiple fields sequentially preserves all corrections
2. Records with multiple issues display all issues
3. Effective values accumulate corrections from all ReviewDecisions
4. Issue recalculation works with multiple issues per record
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject,
    ReviewDecision, create_db_engine
)
from scripts.householder.autosave_service import get_effective_values
from scripts.householder.issue_recalculation_service import recalculate_row_issues
from sqlalchemy.orm import sessionmaker


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
def client_with_db(temp_db, monkeypatch):
    """Flask test client configured with temporary database."""
    database_url, engine = temp_db

    # Monkeypatch environment variable
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Configure Flask app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client, database_url


def setup_multi_issue_batch(database_url):
    """Set up a batch with a record that has BOTH email and phone issues."""
    SessionLocal = sessionmaker(bind=create_db_engine(database_url))
    session = SessionLocal()

    try:
        batch = ImportBatch(
            id='test-multi-field',
            filename='test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        # Raw import row with BOTH email typo and phone too short
        raw_row = RawImportRow(
            batch_id='test-multi-field',
            row_index=0,
            raw_csv_data={
                'transaction_id': 'TX001',
                'date': '2024-01-01',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@gmial.com',  # Email typo
                'phone': '555-0001',              # Too short (7 digits)
                'amount': '100.00',
                'address': '123 Main St',
            }
        )
        session.add(raw_row)
        session.flush()

        # Issue 1: Email validation (typo)
        email_issue = ReviewItem(
            batch_id='test-multi-field',
            item_type='validation',
            status=None,
            confidence=0.95,
            payload_json={
                'field': 'email',
                'reason': 'possible_typo',
                'severity': 'warning',
                'description': 'Invalid email format (gmial.com typo)'
            },
        )
        session.add(email_issue)
        session.flush()

        # Issue 2: Phone validation (format - too short)
        phone_issue = ReviewItem(
            batch_id='test-multi-field',
            item_type='validation',
            status=None,
            confidence=0.95,
            payload_json={
                'field': 'phone',
                'reason': 'format',
                'severity': 'warning',
                'description': 'Phone number too short (7 digits, need 10)'
            },
        )
        session.add(phone_issue)
        session.flush()

        # Link both issues to the same row
        email_subject = ReviewItemSubject(
            review_item_id=email_issue.id,
            subject_type='import_raw_row',
            subject_id=raw_row.id,
            role='primary',
        )
        session.add(email_subject)

        phone_subject = ReviewItemSubject(
            review_item_id=phone_issue.id,
            subject_type='import_raw_row',
            subject_id=raw_row.id,
            role='primary',
        )
        session.add(phone_subject)
        session.commit()

        return batch.id, raw_row.id
    finally:
        session.close()


@pytest.mark.integration
class TestMultipleFieldAutosave:
    """Test suite for multiple field autosave and issue handling."""

    def test_sequential_autosave_preserves_all_corrections(self, client_with_db):
        """CRITICAL: Autosaving email then phone should preserve BOTH corrections."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_multi_issue_batch(database_url)

        # Step 1: Autosave email correction
        response1 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'email': 'jane.smith@gmail.com'  # Corrected
                }
            }
        )
        assert response1.status_code == 200, f"Autosave failed: {response1.data}"
        result1 = response1.get_json()
        assert result1['success'] is True
        assert result1['effective_values']['email'] == 'jane.smith@gmail.com'
        assert result1['effective_values']['phone'] == '555-0001'  # Original

        # Step 2: Autosave phone correction (should NOT lose email correction)
        response2 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'phone': '(415) 555-1234'  # Corrected
                }
            }
        )
        assert response2.status_code == 200, f"Autosave failed: {response2.data}"
        result2 = response2.get_json()
        assert result2['success'] is True

        # CRITICAL: Both corrections should be present
        assert result2['effective_values']['email'] == 'jane.smith@gmail.com', \
            "Email correction lost after phone autosave!"
        assert result2['effective_values']['phone'] == '(415) 555-1234', \
            "Phone correction not applied!"

    def test_get_effective_values_accumulates_corrections(self, client_with_db):
        """Verify get_effective_values merges ALL ReviewDecisions, not just latest."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_multi_issue_batch(database_url)

        # Create two sequential ReviewDecisions (simulating autosave)
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()

        try:
            # Decision 1: Email correction
            decision1 = ReviewDecision(
                batch_id=batch_id,
                review_item_id=None,
                raw_import_row_id=raw_row_id,
                decision='accept_issue',
                reviewed_values={'email': 'jane.smith@gmail.com'}
            )
            session.add(decision1)
            session.commit()

            # Decision 2: Phone correction
            decision2 = ReviewDecision(
                batch_id=batch_id,
                review_item_id=None,
                raw_import_row_id=raw_row_id,
                decision='accept_issue',
                reviewed_values={'phone': '(415) 555-1234'}
            )
            session.add(decision2)
            session.commit()

            # Get effective values - should have BOTH corrections
            effective_values = get_effective_values(batch_id, raw_row_id, database_url)

            assert effective_values['email'] == 'jane.smith@gmail.com', \
                "Email correction lost in accumulation"
            assert effective_values['phone'] == '(415) 555-1234', \
                "Phone correction lost in accumulation"
            assert effective_values['first_name'] == 'Jane', \
                "Raw values should be included"

        finally:
            session.close()

    def test_multiple_issues_all_display_in_recalculation(self, client_with_db):
        """Verify recalculate_row_issues returns ALL issues, not just first."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_multi_issue_batch(database_url)

        # Get issues for the record
        issues = recalculate_row_issues(batch_id, raw_row_id, database_url)

        # Should have 2 issues: email and phone
        assert len(issues) == 2, f"Expected 2 issues, got {len(issues)}"

        issue_fields = {issue['field'] for issue in issues}
        assert 'email' in issue_fields, "Email issue missing"
        assert 'phone' in issue_fields, "Phone issue missing"

    def test_multiple_issues_resolved_by_corrections(self, client_with_db):
        """Verify both issues resolve when respective fields are corrected."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_multi_issue_batch(database_url)

        # Verify both issues exist initially
        issues_before = recalculate_row_issues(batch_id, raw_row_id, database_url)
        assert len(issues_before) == 2, "Should have 2 issues initially"

        # Autosave both corrections
        response1 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'email': 'jane.smith@gmail.com'
                }
            }
        )
        assert response1.status_code == 200

        response2 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'phone': '(415) 555-1234'
                }
            }
        )
        assert response2.status_code == 200

        # Verify both issues are now resolved
        issues_after = recalculate_row_issues(batch_id, raw_row_id, database_url)
        assert len(issues_after) == 0, \
            f"Expected 0 issues after correction, got {len(issues_after)}: {issues_after}"

    def test_third_field_autosave_preserves_previous_two(self, client_with_db):
        """Stress test: Autosaving 3 fields sequentially preserves all."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_multi_issue_batch(database_url)

        # Autosave field 1
        response1 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'jane.smith@gmail.com'}
            }
        )
        assert response1.status_code == 200

        # Autosave field 2
        response2 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'phone': '(415) 555-1234'}
            }
        )
        assert response2.status_code == 200

        # Autosave field 3
        response3 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '250.00'}
            }
        )
        assert response3.status_code == 200

        result3 = response3.get_json()
        # All 3 should be present
        assert result3['effective_values']['email'] == 'jane.smith@gmail.com'
        assert result3['effective_values']['phone'] == '(415) 555-1234'
        assert result3['effective_values']['amount'] == '250.00'
