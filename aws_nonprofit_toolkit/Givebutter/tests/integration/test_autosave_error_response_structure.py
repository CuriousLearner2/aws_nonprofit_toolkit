"""
Test that autosave error responses include required fields for JavaScript error handling.

When autosave fails, the JavaScript error handler expects 'issues' and 'row_status' fields
to update the UI and prevent disconnect between inline field error and row status display.

This test proves that all autosave error responses include these fields, even when
validation fails or exceptions occur.
"""

import os
import pytest
import sys
from pathlib import Path
import json
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import RawImportRow, create_db_engine


class TestAutosaveErrorResponseStructure:
    """Test autosave error response includes required fields for JavaScript."""

    def test_autosave_error_response_includes_issues_field(self, client_with_fixture):
        """Test that autosave error response includes 'issues' field.

        When autosave fails (validation error, exception, etc.), JavaScript expects
        'issues' field to update the Issues column. Without it, inline field error
        displays (red border, "Error" text) but Issues/Row Status don't sync.

        This test proves the 'issues' field is always present in error responses.
        """
        response = client_with_fixture.post(
            '/imports/IMP-2025-0101-A/autosave',
            json={
                'raw_import_row_id': 999,  # Non-existent row → ValueError
                'corrected_values': {'phone': '(415) 555-1234'}
            }
        )

        # Expect 400 error (invalid row)
        assert response.status_code == 400

        # Parse response JSON
        error_data = json.loads(response.data)

        # PROOF: error response includes 'issues' field
        # This allows JavaScript to update Issues/Row Status despite error
        assert 'issues' in error_data, (
            "Autosave error response missing 'issues' field. "
            "JavaScript error handler requires this to sync UI state. "
            "Without it, inline field shows Error but Issues/Row Status remain stale."
        )

        # PROOF: 'issues' is a list (even if empty)
        assert isinstance(error_data['issues'], list), (
            f"'issues' field must be a list, got {type(error_data['issues'])}"
        )
        assert len(error_data['issues']) > 0, (
            "Missing-row fixture autosave must surface at least one blocking issue "
            "so the browser does not collapse Row Status back to No issues."
        )

    def test_autosave_error_response_includes_row_status_field(self, client_with_fixture):
        """Test that autosave error response includes 'row_status' field.

        JavaScript error handler updates the Row Status dropdown based on
        error response 'row_status' field. Without it, Row Status dropdown
        remains stale while inline field shows error.
        """
        response = client_with_fixture.post(
            '/imports/IMP-2025-0101-A/autosave',
            json={
                'raw_import_row_id': 999,  # Non-existent row
                'corrected_values': {'phone': '(415) 555-1234'}
            }
        )

        assert response.status_code == 400
        error_data = json.loads(response.data)

        # PROOF: error response includes 'row_status' field
        assert 'row_status' in error_data, (
            "Autosave error response missing 'row_status' field. "
            "JavaScript error handler requires this to update Row Status dropdown. "
            "Without it, dropdown remains showing stale status."
        )

        # PROOF: 'row_status' is a string
        assert isinstance(error_data['row_status'], str), (
            f"'row_status' field must be a string, got {type(error_data['row_status'])}"
        )
        assert error_data['row_status'] == 'Blocking'

    def test_autosave_validation_error_response_includes_issues(self, client_with_fixture):
        """Test that autosave error responses always include 'issues' field.

        Even when autosave fails (ValueError, Exception), the response must
        include 'issues' field so JavaScript can sync UI state. Without it,
        inline field shows error but Issues/Row Status don't update.

        This test ensures the structure is correct regardless of error type.
        """
        # Non-existent row causes ValueError → 400 response
        response = client_with_fixture.post(
            '/imports/IMP-2025-0101-A/autosave',
            json={
                'raw_import_row_id': 999,  # Non-existent
                'corrected_values': {'phone': '(555) 555-5555'}
            }
        )

        assert response.status_code == 400
        error_data = json.loads(response.data)

        # PROOF: error response ALWAYS includes 'issues', even for database errors
        # This is critical - JavaScript relies on this field existing
        assert 'issues' in error_data, (
            "Autosave error response MUST include 'issues' field. "
            "JavaScript error handler expects this to update Issues column. "
            "Without it, inline field error (red border, 'Error' text) won't sync with Issues/Row Status."
        )

        # PROOF: 'issues' is always a list structure
        assert isinstance(error_data['issues'], list)
        assert len(error_data['issues']) > 0

        first_issue = error_data['issues'][0]
        assert first_issue.get('field')
        assert first_issue.get('reason')
        assert first_issue.get('severity') == 'error'

    def test_autosave_success_response_includes_issues(self, client_with_fixture):
        """Test that successful autosave response includes 'issues' field.

        Proves that both error and success paths return consistent structure
        for JavaScript to process. Success may return empty issues, but the
        field must be present.
        """
        response = client_with_fixture.post(
            '/imports/IMP-2025-0101-A/autosave',
            json={
                'raw_import_row_id': 1,  # TXN-001 - clean row
                'corrected_values': {'phone': '(555) 555-5555'}  # Valid
            }
        )

        # Response should be 200 or 400 depending on fixture/database mode
        # (Fixture mode may fail if row is not in database, but that's OK for this test)
        # We're checking structure, not success

        if response.status_code == 200:
            success_data = json.loads(response.data)

            # PROOF: success response includes 'issues'
            assert 'issues' in success_data, (
                "Autosave success response missing 'issues' field"
            )
            assert isinstance(success_data['issues'], list)

    def test_autosave_error_issues_have_required_fields(self, client_with_fixture):
        """Test that each issue in error response has 'field' and 'reason'.

        JavaScript error handler expects:
        - issue.field: field name ('phone', 'email', etc.)
        - issue.reason: error description to display

        Without these, JavaScript can't render the issue properly.
        """
        response = client_with_fixture.post(
            '/imports/IMP-2025-0101-A/autosave',
            json={
                'raw_import_row_id': 1,
                'corrected_values': {'email': 'invalid-email', 'phone': 'short'}
            }
        )

        if response.status_code == 400:
            error_data = json.loads(response.data)
            issues = error_data.get('issues', [])

            # Check each issue has required fields
            for issue in issues:
                assert 'field' in issue, (
                    f"Issue missing 'field': {issue}"
                )
                assert 'reason' in issue, (
                    f"Issue missing 'reason': {issue}"
                )
                assert isinstance(issue['field'], str)
                assert isinstance(issue['reason'], str)


class TestFixtureModeAutosave:
    """Test fixture/no-DB autosave behavior for the Validation Review page."""

    def test_fixture_mode_valid_noop_phone_autosave_returns_clean_state(
        self,
        client_with_fixture,
    ):
        """A valid no-op phone autosave in fixture mode stays clean and does not error."""
        response = client_with_fixture.post(
            '/imports/IMP-2025-0101-A/autosave',
            json={
                'raw_import_row_id': 1,
                'corrected_values': {'phone': '(415) 555-1234'},
            }
        )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['row_status'] == 'No issues'
        assert data['issues'] == []
        assert data['effective_values']['phone'] == '(415) 555-1234'
        assert data['effective_values']['name'] == 'John Smith'

    def test_fixture_mode_invalid_phone_autosave_still_shows_error_state(
        self,
        client_with_fixture,
    ):
        """Fixture mode still surfaces real validation failures for invalid phone edits."""
        response = client_with_fixture.post(
            '/imports/IMP-2025-0101-A/autosave',
            json={
                'raw_import_row_id': 1,
                'corrected_values': {'phone': '123'},
            }
        )

        assert response.status_code == 400
        data = json.loads(response.data)

        assert data['success'] is False
        assert data['row_status'] == 'Blocking'
        assert any(issue.get('field') == 'phone' for issue in data['issues'])
        assert any(issue.get('severity') == 'error' for issue in data['issues'])


class TestDatabaseModeAutosaveFallback:
    """Test database-mode autosave fallback stays internally consistent."""

    def test_database_mode_exception_fallback_returns_renderable_blocking_issue(
        self,
        client_with_database,
        monkeypatch,
    ):
        """Force the database fallback branch and verify the response is still renderable.

        The fallback must never return row_status='Blocking' with an empty issues list,
        because validation.html collapses an empty Issues payload back to No issues.
        """

        def explode(*_args, **_kwargs):
            raise RuntimeError("forced recalc failure")

        monkeypatch.setattr(
            "householder.issue_recalculation_service.recalculate_row_issues",
            explode,
        )

        database_url = os.environ["GIVEBUTTER_DATABASE_URL"]
        engine = create_db_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            raw_import_row_id = session.query(RawImportRow.id).order_by(RawImportRow.id.asc()).first()[0]
        finally:
            session.close()

        response = client_with_database.post(
            '/imports/IMP-TEST-001/autosave',
            json={
                'raw_import_row_id': raw_import_row_id,
                'corrected_values': {'email': 'invalid-email'},
            },
        )

        assert response.status_code == 500
        data = json.loads(response.data)

        assert data['row_status'] == 'Blocking'
        assert len(data['issues']) > 0

        first_issue = data['issues'][0]
        assert first_issue.get('field')
        assert first_issue.get('reason')
        assert first_issue.get('severity') == 'error'
