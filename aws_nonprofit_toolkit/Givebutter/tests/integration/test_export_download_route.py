"""
Integration tests for export file download route.

Tests route behavior, streaming, and workflows.
"""

import pytest
import json
import os
import sys
import csv
import tempfile
from pathlib import Path
from io import BytesIO, StringIO
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.export_download_service import (
    ExportNotFoundError,
    ExportAccessError,
    ExportPathError,
)
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, create_db_engine
)
from scripts.uploader.app import app
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sample_csv_content():
    """Sample CSV content."""
    return "name,email,phone\nJohn,john@example.com,555-1234\nJane,jane@example.com,555-5678\n"


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
def flask_client_with_db_for_export(temp_db, monkeypatch, tmp_path):
    """Flask client with database backend for export testing."""
    database_url, engine = temp_db

    app.config['TESTING'] = True
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    app.config['EXPORT_OUTPUT_DIR'] = export_dir

    # Configure environment for database mode
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    yield app.test_client(), database_url, engine, export_dir

    # Cleanup
    app.config['EXPORT_OUTPUT_DIR'] = '/tmp/givebutter/exports'


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


# Content Equivalence Tests

def test_downloaded_csv_matches_generated_content(flask_client_with_db_for_export):
    """Downloaded CSV content matches generated file byte-for-byte."""
    client, database_url, engine, export_dir = flask_client_with_db_for_export

    # Seed database with test data
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-EQUIV-001',
        filename='test_upload.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create raw import rows with deterministic data
    row1 = RawImportRow(
        batch_id='IMP-EQUIV-001',
        row_index=1,
        raw_csv_data={
            'transaction_id': 'TXN-001',
            'first_name': 'John',
            'last_name': 'Smith',
            'email': 'john@example.com',
            'phone': '555-1234',
            'amount': '100.00'
        },
    )
    row2 = RawImportRow(
        batch_id='IMP-EQUIV-001',
        row_index=2,
        raw_csv_data={
            'transaction_id': 'TXN-002',
            'first_name': 'Jané',
            'last_name': 'Döé',
            'email': 'jane@example.com',
            'phone': '555-5678',
            'amount': '250.50'
        },
    )
    session.add(row1)
    session.add(row2)
    session.flush()

    # Create import contacts
    contact1 = ImportContact(
        batch_id='IMP-EQUIV-001',
        raw_import_row_id=row1.id,
        first_name='John',
        last_name='Smith',
        email='john@example.com',
        phone='555-1234',
        amount=100.00,
    )
    contact2 = ImportContact(
        batch_id='IMP-EQUIV-001',
        raw_import_row_id=row2.id,
        first_name='Jané',
        last_name='Döé',
        email='jane@example.com',
        phone='555-5678',
        amount=250.50,
    )
    session.add(contact1)
    session.add(contact2)
    session.commit()

    # Generate export using the service
    from scripts.householder.export_file_service import generate_export_file

    result = generate_export_file(
        import_id='IMP-EQUIV-001',
        output_dir=export_dir,
        reviewer='test_user',
        config={'GIVEBUTTER_DATABASE_URL': database_url},
        confirmed_unresolved_households=False,
        confirmed_unresolved_duplicates=False,
        confirmed_unresolved_validations=False,
    )

    # Read generated file from disk
    with open(result.file_path, 'r', encoding='utf-8') as f:
        generated_content = f.read()

    # Download via Flask route
    response = client.get(f'/imports/IMP-EQUIV-001/exports/download/{result.audit_log_id}')

    # Verify response status
    assert response.status_code == 200
    assert 'text/csv' in response.content_type

    # Decode response content
    downloaded_content = response.data.decode('utf-8')

    # Verify CSV structure via row comparison (handles platform-specific line endings)
    generated_rows = list(csv.reader(StringIO(generated_content)))
    downloaded_rows = list(csv.reader(StringIO(downloaded_content)))

    assert len(generated_rows) == len(downloaded_rows), (
        f"Row count mismatch: {len(generated_rows)} vs {len(downloaded_rows)}"
    )

    # Verify headers match
    assert generated_rows[0] == downloaded_rows[0], (
        "CSV headers do not match"
    )

    # Verify headers are non-empty and include transaction_id
    assert 'transaction_id' in generated_rows[0], (
        "Expected transaction_id in header"
    )

    # Verify all data rows match exactly (byte-for-byte after line ending normalization)
    for idx in range(1, len(generated_rows)):
        assert generated_rows[idx] == downloaded_rows[idx], (
            f"Row {idx} mismatch:\n  Generated: {generated_rows[idx]}\n  Downloaded: {downloaded_rows[idx]}"
        )

    # Verify UTF-8 names are preserved (non-ASCII test)
    assert 'Jané' in downloaded_content, (
        "UTF-8 character 'é' not preserved in downloaded content"
    )
    assert 'Döé' in downloaded_content, (
        "UTF-8 character 'ö' not preserved in downloaded content"
    )

    # Verify data integrity: amount values preserved
    assert '100.0' in downloaded_content, (
        "Amount 100.0 not found in downloaded content"
    )
    assert '250.5' in downloaded_content, (
        "Amount 250.5 not found in downloaded content"
    )

    # Cleanup
    session.close()
