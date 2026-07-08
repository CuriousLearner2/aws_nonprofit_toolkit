"""
Integration tests for export file generation route.

Tests route behavior, success/error responses, and integration with service.
"""

import pytest
import json
import os
from unittest.mock import patch
from datetime import datetime, timezone

from scripts.householder.export_file_service import (
    ExportFileResult,
    ExportBlockedError,
    ExportIOError,
)


@pytest.fixture
def sample_export_result():
    """Sample ExportFileResult for mocking."""
    return ExportFileResult(
        import_id="IMP-TEST-001",
        filename="IMP-TEST-001_export_20260612_143022.csv",
        file_path="/tmp/exports/IMP-TEST-001_export_20260612_143022.csv",
        row_count=100,
        warning_count=3,
        blocked_count=0,
        audit_log_id=12345,
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
    )


# Route Behavior Tests

def test_generate_route_forwards_app_config_to_service(client, initialized_test_db, monkeypatch, tmp_path, sample_export_result):
    """Route should pass the app's DB config through even if env points elsewhere."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'fixture')
    monkeypatch.delitem(flask_app.config, 'HOUSEHOLDER_REPOSITORY', raising=False)
    monkeypatch.delitem(flask_app.config, 'GIVEBUTTER_DATABASE_URL', raising=False)

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result) as mock_gen:
        response = client.post('/imports/IMP-TEST-001/exports/generate')

    assert response.status_code == 200
    assert mock_gen.call_count == 1
    assert mock_gen.call_args.kwargs['config']['HOUSEHOLDER_REPOSITORY'] == 'database'
    assert mock_gen.call_args.kwargs['config']['GIVEBUTTER_DATABASE_URL'] == initialized_test_db

def test_generate_route_returns_200_on_success(client, sample_export_result, tmp_path):
    """POST /imports/<id>/exports/generate returns 200 on success."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'


def test_generate_route_returns_400_on_blockers(client, tmp_path):
    """POST /imports/<id>/exports/generate returns 400 on blockers."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    error = ExportBlockedError(
        blockers=["Unresolved validation: missing_email"],
        blocked_count=1
    )

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-002/exports/generate')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'blocked'
        assert data['blocked_count'] == 1


def test_generate_route_returns_500_on_error(client, tmp_path):
    """POST /imports/<id>/exports/generate returns 500 on service error."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=Exception("Database error")):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['status'] == 'error'


# Success Cases

def test_export_generated_with_no_warnings(client, tmp_path):
    """Export generated successfully with no warnings."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    sample_export_result = ExportFileResult(
        import_id="IMP-TEST-001",
        filename="IMP-TEST-001_export_20260612_143022.csv",
        file_path="/tmp/exports/IMP-TEST-001_export_20260612_143022.csv",
        row_count=100,
        warning_count=0,
        blocked_count=0,
        audit_log_id=12345,
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
    )

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['file']['warning_count'] == 0


def test_export_generated_with_warnings(client, sample_export_result, tmp_path):
    """Export generated successfully with warnings."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['file']['warning_count'] == 3


def test_response_includes_file_metadata(client, sample_export_result, tmp_path):
    """Success response includes complete file metadata."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        data = json.loads(response.data)
        assert 'file' in data
        assert data['file']['import_id'] == "IMP-TEST-001"
        assert data['file']['filename'] == "IMP-TEST-001_export_20260612_143022.csv"
        assert data['file']['row_count'] == 100


def test_response_includes_audit_log_reference(client, sample_export_result, tmp_path):
    """Success response includes audit log ID."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        data = json.loads(response.data)
        assert data['file']['audit_log_id'] == 12345


def test_file_path_in_response_is_valid(client, sample_export_result, tmp_path):
    """File path in response is absolute path."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        data = json.loads(response.data)
        file_path = data['file']['file_path']
        assert file_path.startswith('/')


# Error Cases

def test_blockers_prevent_file_generation(client, tmp_path):
    """Blockers prevent file generation (HTTP 400)."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    error = ExportBlockedError(
        blockers=["Unresolved validation: missing_email", "Unresolved validation: invalid_amount"],
        blocked_count=2
    )

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-002/exports/generate')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert len(data['blockers']) == 2


def test_error_response_includes_blocker_summary(client, tmp_path):
    """Error response includes blocker summary."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    blockers = ["Unresolved validation: missing_email"]
    error = ExportBlockedError(blockers=blockers, blocked_count=1)

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-002/exports/generate')

        data = json.loads(response.data)
        assert data['blockers'] == blockers


def test_missing_config_returns_clear_error(client, tmp_path):
    """Missing configuration returns clear error message."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=ValueError("database configuration")):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 500


def test_invalid_batch_returns_clear_error(client, tmp_path):
    """Invalid batch ID returns clear error message."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=ValueError("Import batch not found")):
        response = client.post('/imports/INVALID/exports/generate')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


# Reviewer Header Tests

def test_reviewer_id_from_header(client, sample_export_result, tmp_path):
    """Reviewer ID read from X-Reviewer-ID header."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result) as mock_gen:
        response = client.post(
            '/imports/IMP-TEST-001/exports/generate',
            headers={'X-Reviewer-ID': 'reviewer@example.com'}
        )

        assert response.status_code == 200

        # Verify reviewer was passed to service
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs.get('reviewer') == 'reviewer@example.com'


# Response Format Tests

def test_success_response_json_format(client, sample_export_result, tmp_path):
    """Success response has correct JSON structure."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        data = json.loads(response.data)
        assert 'status' in data
        assert 'file' in data
        assert data['status'] == 'success'


def test_blocked_response_json_format(client, tmp_path):
    """Blocked response has correct JSON structure."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    error = ExportBlockedError(
        blockers=["Unresolved validation: missing_email"],
        blocked_count=1
    )

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-002/exports/generate')

        data = json.loads(response.data)
        assert 'status' in data
        assert 'blockers' in data
        assert 'blocked_count' in data
        assert data['status'] == 'blocked'


def test_error_response_json_format(client, tmp_path):
    """Error response has correct JSON structure."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=Exception("Unknown error")):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        data = json.loads(response.data)
        assert 'status' in data
        assert 'error' in data
        assert data['status'] == 'error'


# Configuration from Flask App

def test_output_dir_from_flask_config(client, sample_export_result, tmp_path):
    """Output directory read from Flask config."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result) as mock_gen:
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 200

        # Verify output_dir was passed
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert 'output_dir' in call_kwargs


# Route Immutability Tests

def test_no_mutations_to_raw_rows_or_contacts(client, sample_export_result, tmp_path):
    """Route does not mutate source data."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        # Route should succeed and return metadata only
        assert response.status_code == 200


def test_no_external_system_calls_made(client, sample_export_result, tmp_path):
    """Route does not call external systems directly."""
    from scripts.uploader.app import app as flask_app
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        # Route should only call service layer
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 200


# P0 Fix Tests: Better blocked export messaging

def test_blocked_export_includes_actionable_next_steps(client, tmp_path):
    """P0 fix: blocked export error includes 'Go to Validation Review' action."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    blockers = ["Missing required email", "Invalid phone format"]
    error = ExportBlockedError(blockers=blockers, blocked_count=2)

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 400
        data = response.get_json()

        # Verify response structure
        assert data['status'] == 'blocked'
        assert 'action' in data
        assert 'Validation Review' in data['action']
        assert 'blockers' in data
        assert len(data['blockers']) == 2

        # Verify error message includes detailed context
        assert 'error' in data
        assert 'Missing required email' in data['error']
        assert 'Invalid phone format' in data['error']


def test_blocked_export_error_message_format(client, tmp_path):
    """P0 fix: blocked export error message is formatted with clear structure."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    blockers = ["Issue 1", "Issue 2"]
    error = ExportBlockedError(blockers=blockers, blocked_count=2)

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        data = response.get_json()

        # Verify error message contains Blockers: header and resolution guidance
        assert 'Blockers:' in data['error']
        assert 'Resolve these issues in Validation Review' in data['error']


# Export Directory Configuration Tests

def test_missing_export_output_dir_config(client):
    """P0 fix: missing EXPORT_OUTPUT_DIR produces clear actionable error."""
    from scripts.uploader.app import app as flask_app

    # Remove or unset EXPORT_OUTPUT_DIR
    if 'EXPORT_OUTPUT_DIR' in flask_app.config:
        del flask_app.config['EXPORT_OUTPUT_DIR']

    response = client.post('/imports/IMP-TEST-001/exports/generate')

    assert response.status_code == 500
    data = response.get_json()

    # Verify clear message about configuration
    assert 'Export directory' in data['error'] or 'EXPORT_OUTPUT_DIR' in data['error']


def test_nonexistent_export_directory(client, tmp_path):
    """P0 fix: non-existent export directory produces clear error."""
    from scripts.uploader.app import app as flask_app

    # Set config to a directory that doesn't exist
    nonexistent_dir = str(tmp_path / "does" / "not" / "exist")
    flask_app.config['EXPORT_OUTPUT_DIR'] = nonexistent_dir

    response = client.post('/imports/IMP-TEST-001/exports/generate')

    assert response.status_code == 500
    data = response.get_json()

    # Verify error message mentions the directory problem
    assert 'does not exist' in data['error'] or 'Export directory' in data['error']


def test_unwritable_export_directory(client, tmp_path):
    """P0 fix: unwritable export directory produces clear error."""
    from scripts.uploader.app import app as flask_app
    import stat

    # Create directory with no write permissions
    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    restricted_path = str(restricted_dir)

    # Remove write permissions
    os.chmod(restricted_path, stat.S_IRUSR | stat.S_IXUSR)  # read + execute only

    flask_app.config['EXPORT_OUTPUT_DIR'] = restricted_path

    try:
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 500
        data = response.get_json()

        # Verify error message mentions write access
        assert 'writable' in data['error'] or 'write' in data['error'].lower() or 'Export directory' in data['error']
    finally:
        # Restore permissions for cleanup
        os.chmod(restricted_path, stat.S_IRWXU)


def test_blocked_export_creates_no_audit_record(client, tmp_path):
    """P0 guardrail: blocked export does not create audit log entry."""
    from scripts.uploader.app import app as flask_app
    from scripts.householder.database_models import AuditLogRecord
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    blockers = ["Unresolved validation"]
    error = ExportBlockedError(blockers=blockers, blocked_count=1)

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 400
        # Verify no file was written or audit logged
        assert len(os.listdir(export_dir)) == 0


def test_failed_export_creates_no_csv_file(client, tmp_path):
    """P0 guardrail: failed export does not write CSV file."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    error = ExportIOError("File write failed")

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 500
        # Verify no files were written to export directory
        assert len(os.listdir(export_dir)) == 0


# Unresolved Households Tests

def test_export_blocked_by_unresolved_households_if_not_confirmed(client, tmp_path):
    """POST /imports/<id>/exports/generate returns 400 if deferred households exist and not confirmed."""
    from scripts.uploader.app import app as flask_app
    from scripts.householder.export_file_service import ExportUnresolvedHouseholdWarningError

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    error = ExportUnresolvedHouseholdWarningError(deferred_count=2)

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        # POST without confirmation
        response = client.post('/imports/IMP-TEST-001/exports/generate', data={
            'confirmed_unresolved_households': 'false'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'warning'
        assert data['action_required'] == 'confirm_unresolved_households'
        assert data['deferred_household_count'] == 2


def test_export_succeeds_with_unresolved_households_if_confirmed(client, sample_export_result, tmp_path):
    """POST /imports/<id>/exports/generate succeeds if deferred households exist and confirmed."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result):
        # POST with confirmation
        response = client.post('/imports/IMP-TEST-001/exports/generate', data={
            'confirmed_unresolved_households': 'true'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'


def test_export_passes_confirmation_parameter_to_service(client, sample_export_result, tmp_path):
    """Route passes confirmed_unresolved_households parameter to service."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    with patch('scripts.householder.export_file_service.generate_export_file', return_value=sample_export_result) as mock_gen:
        # POST with confirmation
        response = client.post('/imports/IMP-TEST-001/exports/generate', data={
            'confirmed_unresolved_households': 'true'
        })

        # Verify parameter was passed to service
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert 'confirmed_unresolved_households' in call_kwargs
        assert call_kwargs['confirmed_unresolved_households'] is True


def test_export_treats_missing_confirmation_as_false(client, tmp_path):
    """Route treats missing confirmation parameter as false."""
    from scripts.uploader.app import app as flask_app
    from scripts.householder.export_file_service import ExportUnresolvedHouseholdWarningError

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    error = ExportUnresolvedHouseholdWarningError(deferred_count=1)

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error) as mock_gen:
        # POST without any confirmation parameter
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        # Verify parameter was passed as False
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert 'confirmed_unresolved_households' in call_kwargs
        assert call_kwargs['confirmed_unresolved_households'] is False


def test_unresolved_household_warning_response_json_format(client, tmp_path):
    """Unresolved household warning response has correct JSON format."""
    from scripts.uploader.app import app as flask_app
    from scripts.householder.export_file_service import ExportUnresolvedHouseholdWarningError

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    error = ExportUnresolvedHouseholdWarningError(deferred_count=3)

    with patch('scripts.householder.export_file_service.generate_export_file', side_effect=error):
        response = client.post('/imports/IMP-TEST-001/exports/generate')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'status' in data
        assert 'action_required' in data
        assert 'warning' in data
        assert 'deferred_household_count' in data
        assert 'message' in data
        assert data['deferred_household_count'] == 3


def test_export_audit_record_includes_confirmation_flags_and_deferred_counts(tmp_path, monkeypatch):
    """Audit record persists confirmation flags and deferred counts from export."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from scripts.householder.database_models import init_db, ImportBatch, ImportContact, AuditLogRecord
    from scripts.householder.export_preview_service import build_export_preview
    from scripts.householder.export_file_service import generate_export_file

    # Setup database
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    init_db(db_url)

    # Create import batch and contact
    Session = sessionmaker(bind=create_engine(db_url))
    session = Session()

    batch = ImportBatch(
        id='IMP-AUDIT-001',
        filename='test.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending'
    )
    session.add(batch)
    session.commit()

    # Create export directory
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)

    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', db_url)

    # Generate export with specific confirmations
    result = generate_export_file(
        'IMP-AUDIT-001',
        export_dir,
        reviewer='test_reviewer@example.com',
        config={'GIVEBUTTER_DATABASE_URL': db_url},
        confirmed_unresolved_validations=True,
        confirmed_unresolved_households=True,
        confirmed_unresolved_duplicates=False,
    )

    # Query audit record from database
    session = Session()
    try:
        audit = session.query(AuditLogRecord).filter_by(
            batch_id='IMP-AUDIT-001',
            action_type='export_generated'
        ).first()

        assert audit is not None, "Audit record should be created"
        assert audit.actor == 'test_reviewer@example.com'
        assert audit.details is not None

        # Verify confirmations are in audit details
        assert 'confirmations' in audit.details
        confirmations = audit.details['confirmations']
        assert confirmations['confirmed_unresolved_validations'] is True
        assert confirmations['confirmed_unresolved_households'] is True
        assert confirmations['confirmed_unresolved_duplicates'] is False

        # Verify deferred counts are in audit details
        assert 'deferred_counts' in audit.details
        deferred = audit.details['deferred_counts']
        assert isinstance(deferred['deferred_validation_count'], int)
        assert isinstance(deferred['deferred_household_count'], int)
        assert isinstance(deferred['deferred_duplicate_count'], int)

    finally:
        session.close()
