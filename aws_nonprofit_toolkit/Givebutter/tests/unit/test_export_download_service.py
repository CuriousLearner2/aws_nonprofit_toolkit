"""
Unit tests for export download service.

Tests path validation, audit record retrieval, and metadata extraction.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.householder.export_download_service import (
    get_export_download_info,
    ExportDownloadInfo,
    ExportNotFoundError,
    ExportAccessError,
    ExportPathError,
)


@pytest.fixture
def valid_audit_record():
    """Valid export audit record."""
    return MagicMock(
        id=12345,
        batch_id="IMP-TEST-001",
        action_type="export_generated",
        action_timestamp=datetime(2026, 6, 12, 14, 30, 22),
        details={
            "export_type": "csv",
            "filename": "IMP-TEST-001_export_20260612_143022.csv",
            "file_path": "/tmp/exports/IMP-TEST-001_export_20260612_143022.csv",
            "row_count": 100,
            "warning_count": 3,
            "blocked_count": 0,
            "is_export_ready": True,
            "generated_by": "reviewer@example.com",
            "generated_at": "2026-06-12T14:30:22Z",
        }
    )


@pytest.fixture
def temp_export_dir(tmp_path):
    """Temporary export directory with test CSV file."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()

    # Create a test CSV file
    csv_file = export_dir / "IMP-TEST-001_export_20260612_143022.csv"
    csv_file.write_text("col1,col2\nval1,val2\n")

    return str(export_dir)


# Happy Path Tests

def test_valid_audit_record_returns_download_info(valid_audit_record, temp_export_dir, monkeypatch):
    """Valid audit record returns ExportDownloadInfo."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            # Update file path to use temp directory
            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / "IMP-TEST-001_export_20260612_143022.csv")

            info = get_export_download_info(
                "IMP-TEST-001",
                12345,
                temp_export_dir,
            )

            assert isinstance(info, ExportDownloadInfo)
            assert info.import_id == "IMP-TEST-001"
            assert info.audit_log_id == 12345


def test_filename_preserved_from_audit_details(valid_audit_record, temp_export_dir, monkeypatch):
    """Filename from audit details is preserved."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / valid_audit_record.details['filename'])

            info = get_export_download_info(
                "IMP-TEST-001",
                12345,
                temp_export_dir,
            )

            assert info.filename == "IMP-TEST-001_export_20260612_143022.csv"


def test_content_type_is_csv(valid_audit_record, temp_export_dir, monkeypatch):
    """Content type is text/csv."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / valid_audit_record.details['filename'])

            info = get_export_download_info(
                "IMP-TEST-001",
                12345,
                temp_export_dir,
            )

            assert info.content_type == "text/csv"


# Error Cases

def test_missing_audit_record_raises_error(monkeypatch):
    """Missing audit record raises ExportNotFoundError."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal
            mock_session.query.return_value.filter_by.return_value.first.return_value = None

            with pytest.raises(ExportNotFoundError):
                get_export_download_info(
                    "IMP-TEST-001",
                    99999,
                    "/tmp/exports",
                )


def test_wrong_batch_raises_error(valid_audit_record, monkeypatch):
    """Audit record from different batch raises ExportAccessError."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            # Try to access with different import_id
            with pytest.raises(ExportAccessError):
                get_export_download_info(
                    "IMP-DIFFERENT",  # Different batch
                    12345,
                    "/tmp/exports",
                )


def test_non_export_record_raises_error(valid_audit_record, monkeypatch):
    """Non-export audit record raises ExportAccessError."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            # Set wrong action_type
            valid_audit_record.action_type = "batch_imported"
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            with pytest.raises(ExportAccessError):
                get_export_download_info(
                    "IMP-TEST-001",
                    12345,
                    "/tmp/exports",
                )


def test_missing_file_path_in_details_raises_error(valid_audit_record, monkeypatch):
    """Missing file_path in details raises ExportPathError."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            # Remove file_path
            valid_audit_record.details = {"filename": "test.csv"}
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            with pytest.raises(ExportPathError):
                get_export_download_info(
                    "IMP-TEST-001",
                    12345,
                    "/tmp/exports",
                )


# Path Safety Tests

def test_path_traversal_rejected(valid_audit_record, temp_export_dir, monkeypatch):
    """Paths with .. are rejected."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            # File path with .. traversal
            valid_audit_record.details['file_path'] = f"{temp_export_dir}/../../../etc/passwd"
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            with pytest.raises(ExportPathError):
                get_export_download_info(
                    "IMP-TEST-001",
                    12345,
                    temp_export_dir,
                )


def test_absolute_path_outside_dir_rejected(valid_audit_record, temp_export_dir, monkeypatch):
    """Absolute path outside export directory rejected."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            # File path outside export directory
            valid_audit_record.details['file_path'] = "/etc/passwd"
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            with pytest.raises(ExportPathError):
                get_export_download_info(
                    "IMP-TEST-001",
                    12345,
                    temp_export_dir,
                )


def test_missing_file_raises_error(valid_audit_record, temp_export_dir, monkeypatch):
    """Missing file on disk raises ExportPathError."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            # File doesn't exist
            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / "nonexistent.csv")
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            with pytest.raises(ExportPathError):
                get_export_download_info(
                    "IMP-TEST-001",
                    12345,
                    temp_export_dir,
                )


def test_valid_path_within_directory_accepted(valid_audit_record, temp_export_dir, monkeypatch):
    """Valid path within directory is accepted."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / "IMP-TEST-001_export_20260612_143022.csv")
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            info = get_export_download_info(
                "IMP-TEST-001",
                12345,
                temp_export_dir,
            )

            assert info is not None


# Metadata Tests

def test_row_count_from_audit_details(valid_audit_record, temp_export_dir, monkeypatch):
    """Row count from audit details is preserved."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / "IMP-TEST-001_export_20260612_143022.csv")
            valid_audit_record.details['row_count'] = 250
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            info = get_export_download_info(
                "IMP-TEST-001",
                12345,
                temp_export_dir,
            )

            assert info.row_count == 250


def test_warning_count_from_audit_details(valid_audit_record, temp_export_dir, monkeypatch):
    """Warning count from audit details is preserved."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / "IMP-TEST-001_export_20260612_143022.csv")
            valid_audit_record.details['warning_count'] = 5
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            info = get_export_download_info(
                "IMP-TEST-001",
                12345,
                temp_export_dir,
            )

            assert info.warning_count == 5


def test_generated_at_from_audit_timestamp(valid_audit_record, temp_export_dir, monkeypatch):
    """Generated_at comes from audit timestamp."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_download_service.create_engine'):
        with patch('scripts.householder.export_download_service.sessionmaker') as mock_sessionmaker:
            mock_session = MagicMock()
            mock_SessionLocal = MagicMock(return_value=mock_session)
            mock_sessionmaker.return_value = mock_SessionLocal

            valid_audit_record.details['file_path'] = str(Path(temp_export_dir) / "IMP-TEST-001_export_20260612_143022.csv")
            expected_timestamp = datetime(2026, 6, 12, 15, 45, 30)
            valid_audit_record.action_timestamp = expected_timestamp
            mock_session.query.return_value.filter_by.return_value.first.return_value = valid_audit_record

            info = get_export_download_info(
                "IMP-TEST-001",
                12345,
                temp_export_dir,
            )

            assert info.generated_at == expected_timestamp
