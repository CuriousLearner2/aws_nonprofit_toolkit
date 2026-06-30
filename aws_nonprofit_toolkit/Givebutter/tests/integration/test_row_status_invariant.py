"""
Test for Row Status Invariant Violation.

Issue: Review Status shows "No issues" while a field shows an Error.

Invariant: No visible field-level Error may coexist with Review Status = "No issues"

This test suite verifies:
1. If a field has a validation error, row_status must NOT be "No issues"
2. If autosave fails due to validation error, error response includes non-"No issues" row_status
3. The derive_row_status function correctly accounts for all issues
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from scripts.householder.row_status_service import derive_row_status
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
def flask_client_with_batch(temp_db, monkeypatch):
    """Flask client with batch and rows seeded in database."""
    database_url, engine = temp_db

    app.config['TESTING'] = True
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Seed database
    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='invariant-test-batch',
        filename='test.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=1
    )
    session.add(batch)
    session.flush()

    row = RawImportRow(
        batch_id='invariant-test-batch',
        row_index=1,
        raw_csv_data={'name': 'John Doe', 'email': 'john@example.com'}
    )
    session.add(row)
    session.flush()
    raw_id = row.id

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, raw_id


class TestRowStatusInvariant:
    """Test the invariant: no field error can coexist with row_status='No issues'."""

    def test_autosave_invalid_email_error_response_has_blocking_status(
        self, flask_client_with_batch
    ):
        """
        When autosave fails with email validation error, error response
        must include row_status that is NOT "No issues".

        This directly tests the reported bug: Review Status showing "No issues"
        while Email field shows Error.
        """
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        response = client.post(
            f'/imports/invariant-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid-no-at-symbol'}
            }
        )

        # Should fail validation
        assert response.status_code == 400
        data = response.get_json()

        # INVARIANT: If email field has error, row_status must NOT be "No issues"
        assert data['row_status'] != 'No issues', \
            f"BUG: Email field has validation error but row_status is 'No issues'. Got: {data['row_status']}"

        # INVARIANT: Issues list must be non-empty if row_status is not "No issues"
        if data['row_status'] != 'No issues':
            assert len(data['issues']) > 0, \
                f"BUG: row_status is '{data['row_status']}' but issues list is empty"

    def test_autosave_invalid_email_error_has_email_in_issues(
        self, flask_client_with_batch
    ):
        """Error response issues list contains the email field issue."""
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        response = client.post(
            f'/imports/invariant-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()

        # Email issue must be present
        email_issues = [i for i in data['issues'] if i.get('field') == 'email']
        assert len(email_issues) > 0, \
            f"Email field has error but not in issues list. Issues: {data['issues']}"

    def test_derive_row_status_with_email_error_issue(self, flask_client_with_batch):
        """
        derive_row_status correctly returns non-"No issues" when given
        an issue list with email error.
        """
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        # Construct an issue list with email error
        issues = [
            {
                'issue_id': 1,
                'issue_type': 'validation',
                'field': 'email',
                'description': 'Invalid email format',
                'severity': 'error',
            }
        ]

        status = derive_row_status(
            batch_id='invariant-test-batch',
            raw_import_row_id=raw_id,
            database_url='sqlite:///:memory:',  # Dummy, we're passing issues directly
            issues=issues
        )

        # INVARIANT: if issues contain error-level issue, status must not be "No issues"
        assert status != 'No issues', \
            f"BUG: Issues with error severity gave status '{status}' (expected 'Blocking')"
        assert status == 'Blocking', \
            f"Status should be 'Blocking' when error issues exist, got '{status}'"

    def test_derive_row_status_with_warning_issue(self, flask_client_with_batch):
        """
        derive_row_status correctly returns 'Warning' when given
        an issue list with warning (not error) issues.
        """
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        issues = [
            {
                'issue_id': 1,
                'issue_type': 'validation',
                'field': 'email',
                'description': 'Possible typo',
                'severity': 'warning',
            }
        ]

        status = derive_row_status(
            batch_id='invariant-test-batch',
            raw_import_row_id=raw_id,
            database_url='sqlite:///:memory:',
            issues=issues
        )

        # INVARIANT: if issues contain warning-level issues, status must be "Warning"
        assert status == 'Warning', \
            f"Status should be 'Warning' when warning issues exist, got '{status}'"

    def test_derive_row_status_empty_issues_no_issues(self, flask_client_with_batch):
        """
        derive_row_status returns "No issues" ONLY when issues list is empty.
        """
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        issues = []

        status = derive_row_status(
            batch_id='invariant-test-batch',
            raw_import_row_id=raw_id,
            database_url='sqlite:///:memory:',
            issues=issues
        )

        # INVARIANT: if issues list is empty, status MUST be "No issues"
        assert status == 'No issues', \
            f"Status should be 'No issues' when issues list is empty, got '{status}'"

    def test_recalculate_row_issues_with_invalid_email_proposed(
        self, flask_client_with_batch
    ):
        """
        recalculate_row_issues detects validation errors in proposed_values
        and returns issues list containing the invalid email.
        """
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        issues = recalculate_row_issues(
            batch_id='invariant-test-batch',
            raw_import_row_id=raw_id,
            database_url=database_url,  # Use the actual test database
            proposed_values={'email': 'invalid-email'}  # No @ symbol
        )

        # Must detect email validation error
        email_issues = [i for i in issues if i.get('field') == 'email']
        assert len(email_issues) > 0, \
            f"recalculate_row_issues didn't detect invalid email. Issues: {issues}"

        # The detected issue should have error severity
        error_issues = [i for i in email_issues if i.get('severity') == 'error']
        assert len(error_issues) > 0, \
            f"Email issue should be severity='error', got: {email_issues}"

    def test_autosave_with_proposed_values_validates_new_issues(
        self, flask_client_with_batch
    ):
        """
        Autosave with proposed_values that introduces validation errors
        returns non-empty issues list and non-"No issues" row_status.
        """
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        # Propose an invalid email correction
        response = client.post(
            f'/imports/invariant-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'john@example'}  # Missing TLD
            }
        )

        # Should fail validation
        assert response.status_code == 400
        data = response.get_json()

        # INVARIANT: error response must have non-empty issues and non-"No issues" status
        assert len(data['issues']) > 0, \
            f"Error response must have non-empty issues list"
        assert data['row_status'] != 'No issues', \
            f"Error response must have row_status != 'No issues', got '{data['row_status']}'"

    def test_error_response_consistency(self, flask_client_with_batch):
        """
        Verify consistency: if row_status is "No issues", issues list must be empty.
        If issues list is non-empty, row_status must NOT be "No issues".
        """
        client, database_url, engine, Session, raw_id = flask_client_with_batch

        response = client.post(
            f'/imports/invariant-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'bad-email-format'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()

        # INVARIANT check
        issues_empty = len(data['issues']) == 0
        status_no_issues = data['row_status'] == 'No issues'

        assert issues_empty == status_no_issues, \
            f"INVARIANT VIOLATION: issues_empty={issues_empty} but status_no_issues={status_no_issues}. " \
            f"Issues: {data['issues']}, Status: {data['row_status']}"
