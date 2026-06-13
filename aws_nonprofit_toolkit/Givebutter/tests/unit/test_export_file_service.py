"""
Unit tests for export file service.

Tests CSV generation, file operations, blocking behavior, and audit logging.
"""

import pytest
import os
import csv
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.householder.export_file_service import (
    generate_export_file,
    ExportFileResult,
    ExportError,
    ExportBlockedError,
    ExportIOError,
    _sanitize_filename,
    _generate_safe_filename,
    _encode_csv_field,
    _generate_csv_content,
)
from scripts.householder.service_contracts import ExportRow, ExportPreviewResult


# Fixtures

@pytest.fixture
def temp_export_dir(tmp_path):
    """Temporary export directory for tests."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    return str(export_dir)


@pytest.fixture
def sample_export_row():
    """Sample ExportRow for testing."""
    return ExportRow(
        source_row_index=1,
        transaction_id="TXN-001",
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        phone="555-1234",
        address_line1="123 Main St",
        address_line2=None,
        city="Springfield",
        state="IL",
        postal_code="62701",
        amount="100.00",
        validation_status="accepted",
        validation_issues=(),
        normalized_fields=("email",),
        normalization_warnings=(),
        duplicate_group_id="DUP-GROUP-abc123",
        duplicate_decision="same_person",
        duplicate_warnings=(),
        household_group_id="HH-001",
        household_group_label="Smith Household",
        household_members=(1, 2),
        household_decision="confirmed",
        household_warnings=(),
        export_warnings=(),
        export_blocked=False,
        export_derived_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_preview_ready(sample_export_row):
    """Mock ExportPreviewResult with no blockers."""
    return ExportPreviewResult(
        import_id="IMP-TEST-001",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_preview_blocked(sample_export_row):
    """Mock ExportPreviewResult with blockers."""
    return ExportPreviewResult(
        import_id="IMP-TEST-002",
        export_rows=(sample_export_row,),
        blockers=("Unresolved validation: missing_email",),
        warnings=(),
        row_count=1,
        blocked_count=1,
        warning_count=0,
        is_export_ready=False,
        derived_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_preview_with_warnings(sample_export_row):
    """Mock ExportPreviewResult with warnings but no blockers."""
    row_with_warnings = ExportRow(
        source_row_index=1,
        transaction_id="TXN-001",
        first_name="John",
        last_name="Smith",
        email="john@example.com",
        phone="555-1234",
        address_line1="123 Main St",
        address_line2=None,
        city="Springfield",
        state="IL",
        postal_code="62701",
        amount="100.00",
        validation_status="pending",
        validation_issues=(),
        normalized_fields=("email",),
        normalization_warnings=("Field normalization deferred",),
        duplicate_group_id="DUP-GROUP-abc123",
        duplicate_decision="deferred",
        duplicate_warnings=("Duplicate pair unresolved",),
        household_group_id="HH-001",
        household_group_label="Smith Household",
        household_members=(1, 2),
        household_decision="deferred",
        household_warnings=("Household grouping unresolved",),
        export_warnings=(),
        export_blocked=False,
        export_derived_at=datetime.utcnow(),
    )

    return ExportPreviewResult(
        import_id="IMP-TEST-003",
        export_rows=(row_with_warnings,),
        blockers=(),
        warnings=("Field normalization deferred", "Duplicate pair unresolved"),
        row_count=1,
        blocked_count=0,
        warning_count=2,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
    )


# Configuration Tests

def test_missing_database_config_raises_error(temp_export_dir):
    """Missing database config raises ValueError."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="database configuration"):
            generate_export_file(
                "IMP-TEST-001",
                temp_export_dir,
                config={}
            )


def test_missing_output_dir_raises_error(monkeypatch):
    """Missing output_dir raises ExportIOError."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview'):
        with pytest.raises(ExportIOError, match="output_dir is required"):
            generate_export_file(
                "IMP-TEST-001",
                "",
            )


def test_invalid_import_raises_error(temp_export_dir, monkeypatch):
    """Invalid import ID raises ValueError."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview') as mock:
        mock.side_effect = ValueError("Import batch 'IMP-NOTFOUND' not found")
        with pytest.raises(ValueError, match="Cannot generate export"):
            generate_export_file(
                "IMP-NOTFOUND",
                temp_export_dir,
            )


# Blocker Detection Tests

def test_generation_blocked_if_blockers_exist(mock_preview_blocked, temp_export_dir, monkeypatch):
    """File generation raises ExportBlockedError if blockers exist."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_blocked):
        with pytest.raises(ExportBlockedError):
            generate_export_file(
                "IMP-TEST-002",
                temp_export_dir,
            )


def test_blocker_error_includes_summary(mock_preview_blocked, temp_export_dir, monkeypatch):
    """ExportBlockedError includes blocker summary and count."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_blocked):
        with pytest.raises(ExportBlockedError) as exc_info:
            generate_export_file(
                "IMP-TEST-002",
                temp_export_dir,
            )

        error = exc_info.value
        assert error.blocked_count == 1
        assert len(error.blockers) == 1
        assert "Unresolved validation: missing_email" in error.blockers


def test_blocker_error_does_not_generate_file(mock_preview_blocked, temp_export_dir, monkeypatch):
    """No file created when blockers prevent export."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_blocked):
        try:
            generate_export_file(
                "IMP-TEST-002",
                temp_export_dir,
            )
        except ExportBlockedError:
            pass

        # Verify no CSV files created
        files = list(Path(temp_export_dir).glob("*.csv"))
        assert len(files) == 0


def test_blocker_error_does_not_create_audit_record(mock_preview_blocked, temp_export_dir, monkeypatch):
    """No audit record created when blockers prevent export."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_blocked):
        with patch('scripts.householder.export_file_service._create_audit_record') as mock_audit:
            try:
                generate_export_file(
                    "IMP-TEST-002",
                    temp_export_dir,
                )
            except ExportBlockedError:
                pass

            # Verify audit record not called
            mock_audit.assert_not_called()


# Warning Handling Tests

def test_generation_succeeds_with_warnings(mock_preview_with_warnings, temp_export_dir, monkeypatch):
    """File generation succeeds with warnings but no blockers."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_with_warnings):
        with patch('scripts.householder.export_file_service._create_audit_record', return_value=123):
            result = generate_export_file(
                "IMP-TEST-003",
                temp_export_dir,
            )

            assert result.warning_count == 2
            assert result.blocked_count == 0
            assert result.row_count == 1


def test_warning_count_in_result(mock_preview_with_warnings, temp_export_dir, monkeypatch):
    """ExportFileResult includes warning count."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_with_warnings):
        with patch('scripts.householder.export_file_service._create_audit_record', return_value=123):
            result = generate_export_file(
                "IMP-TEST-003",
                temp_export_dir,
            )

            assert result.warning_count == 2


def test_warnings_in_audit_details(mock_preview_with_warnings, temp_export_dir, monkeypatch):
    """Warnings included in audit log details."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_with_warnings):
        with patch('scripts.householder.export_file_service._create_audit_record') as mock_audit:
            mock_audit.return_value = 123
            generate_export_file(
                "IMP-TEST-003",
                temp_export_dir,
            )

            # Verify audit called with preview
            mock_audit.assert_called_once()
            call_args = mock_audit.call_args
            preview_arg = call_args[0][4]  # preview is 5th arg
            assert len(preview_arg.warnings) == 2


# CSV Generation Tests

def test_csv_header_matches_contract(mock_preview_ready, sample_export_row):
    """CSV header matches the defined contract."""
    csv_content = _generate_csv_content((sample_export_row,))
    lines = csv_content.strip().split('\n')
    header = lines[0]

    expected_fields = [
        'source_row_index', 'transaction_id', 'first_name', 'last_name', 'email', 'phone',
        'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'amount',
        'validation_status', 'validation_issues', 'normalized_fields', 'normalization_warnings',
        'duplicate_group_id', 'duplicate_decision', 'duplicate_warnings',
        'household_group_id', 'household_group_label', 'household_members', 'household_decision', 'household_warnings',
        'export_warnings'
    ]

    # Parse header with csv reader to handle quoted fields
    reader = csv.reader([header])
    actual_fields = next(reader)
    assert actual_fields == expected_fields


def test_csv_row_count_matches_preview(sample_export_row):
    """CSV row count (excluding header) matches preview row count."""
    rows = (sample_export_row, sample_export_row, sample_export_row)
    csv_content = _generate_csv_content(rows)
    lines = csv_content.strip().split('\n')

    # 1 header + 3 data rows
    assert len(lines) == 4


def test_csv_normalized_fields_applied(sample_export_row):
    """CSV correctly encodes normalized fields."""
    csv_content = _generate_csv_content((sample_export_row,))
    lines = csv_content.strip().split('\n')
    data_row = lines[1]

    reader = csv.reader([data_row])
    values = next(reader)

    # normalized_fields is at index 14
    assert values[14] == "email"


def test_csv_none_values_rendered_as_empty_string(sample_export_row):
    """None values rendered as empty strings in CSV."""
    csv_content = _generate_csv_content((sample_export_row,))
    lines = csv_content.strip().split('\n')
    data_row = lines[1]

    reader = csv.reader([data_row])
    values = next(reader)

    # address_line2 is None, should be empty (index 7)
    assert values[7] == ""


# File Operation Tests

def test_file_created_in_output_dir(mock_preview_ready, temp_export_dir, monkeypatch):
    """File created in specified output directory."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_ready):
        with patch('scripts.householder.export_file_service._create_audit_record', return_value=123):
            result = generate_export_file(
                "IMP-TEST-001",
                temp_export_dir,
            )

            # Verify file exists
            assert os.path.exists(result.file_path)
            assert result.file_path.startswith(temp_export_dir)


def test_filename_follows_convention(mock_preview_ready, temp_export_dir, monkeypatch):
    """Filename follows {import_id}_export_{YYYYMMDD_HHMMSS}.csv convention."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_ready):
        with patch('scripts.householder.export_file_service._create_audit_record', return_value=123):
            result = generate_export_file(
                "IMP-TEST-001",
                temp_export_dir,
            )

            # Check filename pattern
            assert result.filename.startswith("IMP-TEST-001_export_")
            assert result.filename.endswith(".csv")


def test_filename_sanitization_prevents_traversal(mock_preview_ready, temp_export_dir, monkeypatch):
    """Filename sanitization prevents directory traversal."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    # Test sanitization directly
    sanitized = _sanitize_filename("../../../etc/passwd")
    assert "/" not in sanitized
    assert "\\" not in sanitized
    assert ".." not in sanitized


def test_file_not_created_on_blockers(mock_preview_blocked, temp_export_dir, monkeypatch):
    """No file created when blockers exist."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_blocked):
        try:
            generate_export_file(
                "IMP-TEST-002",
                temp_export_dir,
            )
        except ExportBlockedError:
            pass

        # Verify no files created
        files = list(Path(temp_export_dir).glob("*.csv"))
        assert len(files) == 0


# Audit Logging Tests

def test_audit_log_record_created_on_success(mock_preview_ready, temp_export_dir, monkeypatch):
    """Audit log record created on successful generation."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_ready):
        with patch('scripts.householder.export_file_service._create_audit_record', return_value=999) as mock_audit:
            result = generate_export_file(
                "IMP-TEST-001",
                temp_export_dir,
            )

            # Verify audit record created and ID returned
            mock_audit.assert_called_once()
            assert result.audit_log_id == 999


def test_audit_log_includes_decision_summary(mock_preview_ready, temp_export_dir, monkeypatch):
    """Audit log includes decision summary."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    with patch('scripts.householder.export_file_service.build_export_preview', return_value=mock_preview_ready):
        with patch('scripts.householder.export_file_service._create_audit_record') as mock_audit:
            mock_audit.return_value = 123
            generate_export_file(
                "IMP-TEST-001",
                temp_export_dir,
                reviewer="test_reviewer",
            )

            # Verify audit called with correct parameters
            mock_audit.assert_called_once()
            call_args = mock_audit.call_args
            preview_arg = call_args[0][4]
            assert preview_arg.import_id == "IMP-TEST-001"


# Encoding Tests

def test_encode_csv_field_none():
    """None encoded as empty string."""
    assert _encode_csv_field(None) == ""


def test_encode_csv_field_boolean():
    """Booleans encoded as true/false."""
    assert _encode_csv_field(True) == "true"
    assert _encode_csv_field(False) == "false"


def test_encode_csv_field_tuple():
    """Tuples encoded as semicolon-separated."""
    result = _encode_csv_field(("a", "b", "c"))
    assert result == "a;b;c"


def test_encode_csv_field_list():
    """Lists encoded as semicolon-separated."""
    result = _encode_csv_field(["a", "b", "c"])
    assert result == "a;b;c"


def test_encode_csv_field_string():
    """Strings passed through."""
    assert _encode_csv_field("hello") == "hello"


# Filename Tests

def test_generate_safe_filename_format():
    """Filename follows expected format."""
    import_id = "IMP-TEST-001"
    timestamp = datetime(2026, 6, 12, 14, 30, 22)

    filename = _generate_safe_filename(import_id, timestamp)

    assert filename == "IMP-TEST-001_export_20260612_143022.csv"
