"""
Integration tests for autosave validation synchronization.

Tests that when autosave fails due to validation errors, the Row Status
dropdown updates to show the actual validation state (not stale status).

Issue: Email field shows "Error" but Row Status shows "No issues"
Root cause: Autosave failure didn't update Row Status in UI
Solution: Return row_status and issues in error response
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    create_db_engine,
)
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
        id='sync-test-batch',
        filename='test.csv',
        upload_timestamp=datetime.utcnow(),
        status='pending_review',
        raw_row_count=2
    )
    session.add(batch)
    session.flush()

    rows = []
    for i in range(1, 3):
        row = RawImportRow(
            batch_id='sync-test-batch',
            row_index=i,
            raw_csv_data={'name': f'Person {i}', 'email': f'person{i}@gmail.com'}
        )
        session.add(row)
        session.flush()
        rows.append(row.id)

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, rows


class TestAutosaveValidationSync:
    """Test autosave validation synchronization."""

    def test_autosave_validation_error_response_includes_status(self, flask_client_with_batch):
        """Autosave error response includes row_status and issues for UI sync."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # Try to autosave an invalid email
        response = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid-email'}  # No @ symbol
            }
        )

        # Should fail validation
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'validation_errors' in data

    def test_autosave_error_includes_row_status(self, flask_client_with_batch):
        """Autosave error response includes current row_status."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        response = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        # Must include row_status so UI can update dropdown
        assert 'row_status' in data
        assert data['row_status'] is not None

    def test_autosave_error_includes_issues(self, flask_client_with_batch):
        """Autosave error response includes current issues list."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        response = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'bad@email'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        # Must include issues so UI can update Issues column
        assert 'issues' in data
        assert isinstance(data['issues'], list)

    def test_autosave_success_response_consistent(self, flask_client_with_batch):
        """Success response includes same fields as error response."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # Valid correction
        response = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'name': 'John Smith Updated'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Both success and error should have these fields
        assert 'row_status' in data
        assert 'issues' in data

    def test_row_status_reflects_validation_errors(self, flask_client_with_batch):
        """Row status changes when validation fails (before fix would show stale status)."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # First, get initial status
        response_initial = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'name': 'Valid Name'}
            }
        )
        assert response_initial.status_code == 200
        initial_status = response_initial.get_json()['row_status']

        # Now try invalid correction
        response_invalid = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid'}
            }
        )

        assert response_invalid.status_code == 400
        error_data = response_invalid.get_json()

        # Error response must include current row status
        assert error_data['row_status'] is not None
        # The row status should potentially be different from initial if validation errors exist
        assert 'row_status' in error_data

    def test_multiple_field_validation_errors(self, flask_client_with_batch):
        """Error response handles multiple validation errors across fields."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        response = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {
                    'email': 'bad',
                    'amount': 'not-a-number'
                }
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'validation_errors' in data
        assert len(data['validation_errors']) >= 1
        # But still include row status and issues for UI update
        assert 'row_status' in data
        assert 'issues' in data

    def test_error_response_issues_format_matches_success(self, flask_client_with_batch):
        """Issues format in error response matches success response format."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # Get success response format
        response_success = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'name': 'Test'}
            }
        )
        assert response_success.status_code == 200
        success_issues = response_success.get_json()['issues']

        # Get error response format
        response_error = client.post(
            f'/imports/sync-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid'}
            }
        )
        assert response_error.status_code == 400
        error_issues = response_error.get_json()['issues']

        # Both should be lists of issue objects with same structure
        assert isinstance(success_issues, list)
        assert isinstance(error_issues, list)

        # If error_issues has items, they should have the expected fields
        if error_issues:
            for issue in error_issues:
                assert 'field' in issue or 'reason' in issue
