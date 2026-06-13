"""
Integration tests for export file download route.

Tests route behavior, streaming, and workflows.
"""

import pytest
import json
import os
from io import BytesIO
from unittest.mock import patch

from scripts.householder.export_download_service import (
    ExportNotFoundError,
    ExportAccessError,
    ExportPathError,
)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content."""
    return "name,email,phone\nJohn,john@example.com,555-1234\nJane,jane@example.com,555-5678\n"


# Route Behavior Tests

def test_download_returns_200_on_valid_record(client, tmp_path, sample_csv_content):
    """Valid download returns 200 with CSV."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    # Create a test CSV file
    csv_path = os.path.join(export_dir, "IMP-TEST-001_export_20260612_143022.csv")
    with open(csv_path, 'w') as f:
        f.write(sample_csv_content)

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        from datetime import datetime
        from scripts.householder.export_download_service import ExportDownloadInfo

        mock_get_info.return_value = ExportDownloadInfo(
            import_id="IMP-TEST-001",
            audit_log_id=12345,
            filename="IMP-TEST-001_export_20260612_143022.csv",
            file_path=csv_path,
            content_type="text/csv",
            generated_at=datetime(2026, 6, 12, 14, 30, 22),
            row_count=100,
            warning_count=0,
        )

        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        assert response.status_code == 200


def test_download_returns_404_on_missing_record(client):
    """Missing audit record returns 404."""
    from scripts.uploader.app import app as flask_app

    flask_app.config['EXPORT_OUTPUT_DIR'] = '/tmp/exports'

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        mock_get_info.side_effect = ExportNotFoundError("Export not found")

        response = client.get('/imports/IMP-TEST-001/exports/download/99999')

        assert response.status_code == 404


def test_download_returns_403_on_wrong_batch(client):
    """Export from different batch returns 403 or 400."""
    from scripts.uploader.app import app as flask_app

    flask_app.config['EXPORT_OUTPUT_DIR'] = '/tmp/exports'

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        mock_get_info.side_effect = ExportAccessError("Wrong batch")

        response = client.get('/imports/IMP-WRONG/exports/download/12345')

        assert response.status_code in (400, 403)


# File Streaming Tests

def test_response_is_csv_attachment(client, tmp_path, sample_csv_content):
    """Response has correct headers for CSV attachment."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write(sample_csv_content)

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        from datetime import datetime
        from scripts.householder.export_download_service import ExportDownloadInfo

        mock_get_info.return_value = ExportDownloadInfo(
            import_id="IMP-TEST-001",
            audit_log_id=12345,
            filename="test_export.csv",
            file_path=csv_path,
            content_type="text/csv",
            generated_at=datetime(2026, 6, 12, 14, 30, 22),
            row_count=2,
            warning_count=0,
        )

        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        assert response.status_code == 200
        assert 'text/csv' in response.content_type


def test_response_has_content_disposition_header(client, tmp_path, sample_csv_content):
    """Response has attachment content disposition."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "test_export.csv")
    with open(csv_path, 'w') as f:
        f.write(sample_csv_content)

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        from datetime import datetime
        from scripts.householder.export_download_service import ExportDownloadInfo

        mock_get_info.return_value = ExportDownloadInfo(
            import_id="IMP-TEST-001",
            audit_log_id=12345,
            filename="test_export.csv",
            file_path=csv_path,
            content_type="text/csv",
            generated_at=datetime(2026, 6, 12, 14, 30, 22),
            row_count=2,
            warning_count=0,
        )

        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        assert response.status_code == 200
        assert 'attachment' in response.headers.get('Content-Disposition', '')


# Path Safety Tests

def test_path_traversal_in_audit_rejected(client):
    """Path traversal in audit details rejected."""
    from scripts.uploader.app import app as flask_app

    flask_app.config['EXPORT_OUTPUT_DIR'] = '/tmp/exports'

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        mock_get_info.side_effect = ExportPathError("Path is unsafe")

        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        assert response.status_code in (400, 404, 500)


def test_missing_file_returns_404(client):
    """Missing file on disk returns 404."""
    from scripts.uploader.app import app as flask_app

    flask_app.config['EXPORT_OUTPUT_DIR'] = '/tmp/exports'

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        mock_get_info.side_effect = ExportPathError("File not found")

        response = client.get('/imports/IMP-TEST-001/exports/download/12345')

        assert response.status_code == 404


# Workflow Tests

def test_exports_from_different_batches_isolated(client, tmp_path, sample_csv_content):
    """Exports from different batches cannot be accessed cross-batch."""
    from scripts.uploader.app import app as flask_app

    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    flask_app.config['EXPORT_OUTPUT_DIR'] = export_dir

    csv_path = os.path.join(export_dir, "export.csv")
    with open(csv_path, 'w') as f:
        f.write(sample_csv_content)

    with patch('scripts.householder.export_download_service.get_export_download_info') as mock_get_info:
        # Trying to access IMP-001 export from IMP-002 route should fail
        mock_get_info.side_effect = ExportAccessError("Wrong batch")

        response = client.get('/imports/IMP-DIFFERENT/exports/download/12345')

        assert response.status_code in (400, 403)
