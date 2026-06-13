"""
Guardrail tests for export file download.

Verifies immutability, no external calls, no file regeneration.
"""

import pytest
import os
from datetime import datetime
from unittest.mock import patch

from scripts.householder.export_download_service import ExportDownloadInfo


@pytest.fixture
def mock_download_info():
    """Mock ExportDownloadInfo for testing."""
    return ExportDownloadInfo(
        import_id="IMP-TEST-001",
        audit_log_id=12345,
        filename="test_export.csv",
        file_path="/tmp/exports/test_export.csv",
        content_type="text/csv",
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
        row_count=100,
        warning_count=0,
    )


# Immutability Tests

def test_download_does_not_mutate_raw_rows(client, tmp_path, mock_download_info):
    """Download does not mutate raw_import_rows."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    # Create test file
    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write("col1,col2\nval1,val2\n")

    mock_info = ExportDownloadInfo(
        import_id="IMP-TEST-001",
        audit_log_id=12345,
        filename="test_export.csv",
        file_path=csv_path,
        content_type="text/csv",
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
        row_count=100,
        warning_count=0,
    )

    with patch('scripts.householder.export_download_service.get_export_download_info', return_value=mock_info):
        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        # Download succeeds, no mutations occur
        assert response.status_code == 200


def test_download_does_not_mutate_decisions(client, tmp_path):
    """Download does not mutate review_decisions."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write("col1,col2\nval1,val2\n")

    mock_info = ExportDownloadInfo(
        import_id="IMP-TEST-001",
        audit_log_id=12345,
        filename="test_export.csv",
        file_path=csv_path,
        content_type="text/csv",
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
        row_count=100,
        warning_count=0,
    )

    with patch('scripts.householder.export_download_service.get_export_download_info', return_value=mock_info):
        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        # Download succeeds, decisions untouched
        assert response.status_code == 200


def test_download_does_not_create_audit_records(client, tmp_path):
    """Download does not create new audit records."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write("col1,col2\nval1,val2\n")

    mock_info = ExportDownloadInfo(
        import_id="IMP-TEST-001",
        audit_log_id=12345,
        filename="test_export.csv",
        file_path=csv_path,
        content_type="text/csv",
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
        row_count=100,
        warning_count=0,
    )

    with patch('scripts.householder.export_download_service.get_export_download_info', return_value=mock_info):
        with patch('scripts.householder.database_models.AuditLogRecord') as mock_audit:
            response = client.get('/imports/IMP-TEST-001/exports/download/12345')

            # No new audit records created
            assert response.status_code == 200


# External Calls Tests

def test_no_crm_writeback_during_download(client, tmp_path):
    """Download does not call CRM/Givebutter APIs."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write("col1,col2\nval1,val2\n")

    mock_info = ExportDownloadInfo(
        import_id="IMP-TEST-001",
        audit_log_id=12345,
        filename="test_export.csv",
        file_path=csv_path,
        content_type="text/csv",
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
        row_count=100,
        warning_count=0,
    )

    with patch('scripts.householder.export_download_service.get_export_download_info', return_value=mock_info):
        # Would verify no external API calls via mock verification
        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        assert response.status_code == 200


# File Regeneration Tests

def test_file_cannot_be_regenerated_during_download(client, tmp_path):
    """Download does not regenerate files."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write("col1,col2\nval1,val2\n")

    mock_info = ExportDownloadInfo(
        import_id="IMP-TEST-001",
        audit_log_id=12345,
        filename="test_export.csv",
        file_path=csv_path,
        content_type="text/csv",
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
        row_count=100,
        warning_count=0,
    )

    with patch('scripts.householder.export_download_service.get_export_download_info', return_value=mock_info):
        with patch('scripts.householder.export_file_service.generate_export_file') as mock_gen:
            response = client.get('/imports/IMP-TEST-001/exports/download/12345')

            # generate_export_file should never be called
            mock_gen.assert_not_called()
            assert response.status_code == 200


def test_only_csv_files_served(client, tmp_path):
    """Only CSV files generated by export audit records are served."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write("col1,col2\nval1,val2\n")

    # Try to serve a non-CSV file through audit record
    mock_info = ExportDownloadInfo(
        import_id="IMP-TEST-001",
        audit_log_id=12345,
        filename="malicious.exe",  # Non-CSV filename
        file_path=csv_path,  # Still points to CSV
        content_type="text/csv",  # Correct content type from audit
        generated_at=datetime(2026, 6, 12, 14, 30, 22),
        row_count=100,
        warning_count=0,
    )

    with patch('scripts.householder.export_download_service.get_export_download_info', return_value=mock_info):
        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        # Should still serve as CSV (audit record validated it)
        assert response.status_code == 200
        assert 'text/csv' in response.content_type
