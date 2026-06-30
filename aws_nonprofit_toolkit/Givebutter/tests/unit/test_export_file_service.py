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
    ExportUnresolvedValidationWarningError,
    ExportUnresolvedHouseholdWarningError,
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


@patch('scripts.householder.export_file_service.build_export_preview')
@patch('scripts.householder.export_file_service._create_audit_record')
def test_audit_includes_confirmation_flags(mock_audit, mock_preview, temp_export_dir, sample_export_row, monkeypatch):
    """Audit record includes confirmation flags."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    # Mock preview with deferred items
    preview = ExportPreviewResult(
        import_id="IMP-TEST-001",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
        deferred_validation_count=1,
        deferred_household_count=2,
        deferred_duplicate_count=0,
    )
    mock_preview.return_value = preview
    mock_audit.return_value = 999

    generate_export_file(
        "IMP-TEST-001",
        temp_export_dir,
        reviewer="test_reviewer",
        config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
        confirmed_unresolved_validations=True,
        confirmed_unresolved_households=True,
        confirmed_unresolved_duplicates=False,
    )

    # Verify audit called with confirmation flags
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args

    # Extract positional arguments
    assert call_args[0][6] is True, "confirmed_unresolved_validations should be True"
    assert call_args[0][7] is True, "confirmed_unresolved_households should be True"
    assert call_args[0][8] is False, "confirmed_unresolved_duplicates should be False"


@patch('scripts.householder.export_file_service.build_export_preview')
@patch('scripts.householder.export_file_service._create_audit_record')
def test_audit_includes_deferred_counts(mock_audit, mock_preview, temp_export_dir, sample_export_row, monkeypatch):
    """Audit record includes deferred counts from preview."""
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', 'sqlite:///:memory:')

    # Mock preview with deferred items
    preview = ExportPreviewResult(
        import_id="IMP-TEST-002",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
        deferred_validation_count=3,
        deferred_household_count=2,
        deferred_duplicate_count=1,
    )
    mock_preview.return_value = preview
    mock_audit.return_value = 999

    generate_export_file(
        "IMP-TEST-002",
        temp_export_dir,
        reviewer="test_reviewer",
        config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
        confirmed_unresolved_validations=True,
        confirmed_unresolved_households=True,
        confirmed_unresolved_duplicates=True,
    )

    # Verify audit called with preview containing deferred counts
    mock_audit.assert_called_once()
    call_args = mock_audit.call_args
    preview_arg = call_args[0][4]

    # Verify deferred counts are in preview
    assert preview_arg.deferred_validation_count == 3
    assert preview_arg.deferred_household_count == 2
    assert preview_arg.deferred_duplicate_count == 1


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


# Golden-File Tests

def test_csv_golden_file_with_reviewed_normalization():
    """
    Golden-file test: CSV output with reviewed normalization value.

    Tests that reviewed values (applied via decisions) appear in exported CSV.
    This row simulates a contact where email was normalized via accept_normalization
    decision and the reviewed_value was applied.

    Verifies:
    - Column order matches contract
    - Reviewed email value appears in correct position
    - normalized_fields correctly marks the field as normalized
    - All other fields are rendered correctly
    """
    # Create a row where email has been normalized (reviewed value applied)
    # Original email would have been "john.smith@example.com"
    # After normalization decision, it's now "john.smith@example.com" (cleaned)
    row_with_reviewed_email = ExportRow(
        source_row_index=1,
        transaction_id="TXN-001",
        first_name="John",
        last_name="Smith",
        email="john.smith@example.com",  # This is the reviewed/normalized value
        phone="555-1234",
        address_line1="123 Main St",
        address_line2=None,
        city="Springfield",
        state="IL",
        postal_code="62701",
        amount="100.00",
        validation_status="accepted",
        validation_issues=(),
        normalized_fields=("email",),  # Marks email as normalized
        normalization_warnings=(),
        duplicate_group_id=None,
        duplicate_decision=None,
        duplicate_warnings=(),
        household_group_id=None,
        household_group_label=None,
        household_members=(),
        household_decision=None,
        household_warnings=(),
        export_warnings=(),
        export_blocked=False,
        export_derived_at=datetime.utcnow(),
    )

    csv_content = _generate_csv_content((row_with_reviewed_email,))
    lines = csv_content.strip().split('\n')

    # Verify header
    header = lines[0]
    reader = csv.reader([header])
    actual_fields = next(reader)
    expected_fields = [
        'source_row_index', 'transaction_id', 'first_name', 'last_name', 'email', 'phone',
        'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'amount',
        'validation_status', 'validation_issues', 'normalized_fields', 'normalization_warnings',
        'duplicate_group_id', 'duplicate_decision', 'duplicate_warnings',
        'household_group_id', 'household_group_label', 'household_members', 'household_decision', 'household_warnings',
        'export_warnings'
    ]
    assert actual_fields == expected_fields, "CSV header order must match contract"

    # Verify data row has correct values in correct positions
    data_row = lines[1]
    reader = csv.reader([data_row])
    values = next(reader)

    # Verify the reviewed email value appears in the correct position
    assert values[4] == "john.smith@example.com", "Email should be in position 4 (fifth column)"
    assert values[0] == "1", "source_row_index should be 1"
    assert values[1] == "TXN-001", "transaction_id should be TXN-001"
    assert values[2] == "John", "first_name should be John"
    assert values[3] == "Smith", "last_name should be Smith"
    assert values[14] == "email", "normalized_fields should mark email as normalized (position 14)"

    # Verify no blockers/warnings
    assert values[12] == "accepted", "validation_status should be accepted"
    assert values[13] == "", "validation_issues should be empty"
    assert values[15] == "", "normalization_warnings should be empty"

    # Verify row count
    assert len(lines) == 2, "Should have 1 header + 1 data row"


# Phase 3: Extended Golden-File Tests (Multi-Row and Mixed Scenarios)

def test_csv_golden_file_multirow_preserves_order():
    """
    Golden-file test: Multi-row CSV export preserves row ordering and effective values.

    Tests that exported CSV correctly handles multiple rows with different states:
    - Multiple rows are exported in the order they appear
    - Each row's effective/reviewed values are rendered correctly
    - Row ordering matches source_row_index sequence

    Verifies:
    - CSV has correct row count (header + 3 data rows)
    - Rows appear in expected order (source_row_index 1, 2, 3)
    - Each row's values are preserved accurately
    - Column positions are consistent across all rows
    """
    # Create three rows with different reviewed values
    rows = (
        ExportRow(
            source_row_index=1,
            transaction_id="TXN-001",
            first_name="John",
            last_name="Smith",
            email="john@example.com",
            phone="555-0001",
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
            duplicate_group_id="DUP-001",
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
        ),
        ExportRow(
            source_row_index=2,
            transaction_id="TXN-002",
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
            phone="555-0002",
            address_line1="456 Oak Ave",
            address_line2="Apt 200",
            city="Shelbyville",
            state="IL",
            postal_code="62702",
            amount="250.50",
            validation_status="accepted",
            validation_issues=(),
            normalized_fields=("email", "phone"),
            normalization_warnings=(),
            duplicate_group_id=None,
            duplicate_decision=None,
            duplicate_warnings=(),
            household_group_id="HH-002",
            household_group_label="Doe Household",
            household_members=(3,),
            household_decision="confirmed",
            household_warnings=(),
            export_warnings=(),
            export_blocked=False,
            export_derived_at=datetime.utcnow(),
        ),
        ExportRow(
            source_row_index=3,
            transaction_id="TXN-003",
            first_name="Bob",
            last_name="Johnson",
            email="bob.j@example.com",
            phone="555-0003",
            address_line1="789 Pine Rd",
            address_line2=None,
            city="Capital City",
            state="IL",
            postal_code="62703",
            amount="75.25",
            validation_status="accepted",
            validation_issues=(),
            normalized_fields=(),
            normalization_warnings=(),
            duplicate_group_id="DUP-002",
            duplicate_decision="same_person",
            duplicate_warnings=(),
            household_group_id=None,
            household_group_label=None,
            household_members=(),
            household_decision=None,
            household_warnings=(),
            export_warnings=(),
            export_blocked=False,
            export_derived_at=datetime.utcnow(),
        ),
    )

    csv_content = _generate_csv_content(rows)
    lines = csv_content.strip().split('\n')

    # Verify row count: 1 header + 3 data rows
    assert len(lines) == 4, f"Expected 4 lines (1 header + 3 rows), got {len(lines)}"

    # Verify header exists
    header = lines[0]
    reader = csv.reader([header])
    actual_fields = next(reader)
    assert len(actual_fields) == 25, "Header should have 25 fields"

    # Verify each row's values are in correct positions and order is preserved
    for row_idx, expected_row in enumerate(rows, start=1):
        data_row = lines[row_idx]
        reader = csv.reader([data_row])
        values = next(reader)

        # Verify source_row_index matches expected (verifies ordering)
        assert values[0] == str(expected_row.source_row_index), f"Row {row_idx}: source_row_index mismatch"
        assert values[1] == expected_row.transaction_id, f"Row {row_idx}: transaction_id mismatch"
        assert values[2] == expected_row.first_name, f"Row {row_idx}: first_name mismatch"
        assert values[3] == expected_row.last_name, f"Row {row_idx}: last_name mismatch"
        assert values[4] == expected_row.email, f"Row {row_idx}: email mismatch"
        assert values[5] == expected_row.phone, f"Row {row_idx}: phone mismatch"
        assert values[11] == expected_row.amount, f"Row {row_idx}: amount mismatch"


def test_csv_golden_file_mixed_decisions_effective_values():
    """
    Golden-file test: Mixed decision scenario with raw and reviewed values.

    Tests export behavior when batch contains mixed decision states:
    - Row with raw values only (no normalization, default decisions)
    - Row with reviewed/effective values (normalized, approved decisions)
    - Row with deferred decisions (awaiting resolution)

    Verifies:
    - Raw values row exports raw field values
    - Reviewed values row exports effective/reviewed values
    - Deferred status is preserved in validation_status field
    - effective_value behavior is consistent with product semantics

    This test locks down the contract that:
    - Export always uses effective values (reviewed where available, raw otherwise)
    - Raw source data remains immutable
    - Decision state (deferred/accepted) is preserved for audit
    """
    rows = (
        # Row 1: Raw values only (no decisions applied)
        ExportRow(
            source_row_index=1,
            transaction_id="TXN-RAW-001",
            first_name="Alice",
            last_name="Raw",
            email="alice.raw@example.com",
            phone="555-1111",
            address_line1="100 Raw St",
            address_line2=None,
            city="Raw City",
            state="IL",
            postal_code="62000",
            amount="50.00",
            validation_status="accepted",
            validation_issues=(),
            normalized_fields=(),  # No normalization
            normalization_warnings=(),
            duplicate_group_id="DUP-RAW",
            duplicate_decision=None,  # Raw decision state
            duplicate_warnings=(),
            household_group_id=None,
            household_group_label=None,
            household_members=(),
            household_decision=None,
            household_warnings=(),
            export_warnings=(),
            export_blocked=False,
            export_derived_at=datetime.utcnow(),
        ),
        # Row 2: Reviewed/effective values (decisions applied)
        ExportRow(
            source_row_index=2,
            transaction_id="TXN-REV-001",
            first_name="Bob",
            last_name="Reviewed",
            email="bob.reviewed@example.com",  # Effective (reviewed) email
            phone="555-2222",  # Effective (reviewed) phone
            address_line1="200 Reviewed Ave",
            address_line2=None,
            city="Review City",
            state="IL",
            postal_code="62100",
            amount="150.00",
            validation_status="accepted",
            validation_issues=(),
            normalized_fields=("email", "phone"),  # Marked as reviewed
            normalization_warnings=(),
            duplicate_group_id="DUP-REV",
            duplicate_decision="same_person",  # Approved decision
            duplicate_warnings=(),
            household_group_id="HH-REV",
            household_group_label="Reviewed Household",
            household_members=(2, 3),
            household_decision="confirmed",  # Approved decision
            household_warnings=(),
            export_warnings=(),
            export_blocked=False,
            export_derived_at=datetime.utcnow(),
        ),
        # Row 3: Deferred decisions (awaiting resolution)
        ExportRow(
            source_row_index=3,
            transaction_id="TXN-DEF-001",
            first_name="Charlie",
            last_name="Deferred",
            email="charlie.deferred@example.com",
            phone="555-3333",
            address_line1="300 Deferred Ln",
            address_line2=None,
            city="Defer City",
            state="IL",
            postal_code="62200",
            amount="200.00",
            validation_status="deferred",  # Deferred validation status
            validation_issues=(),
            normalized_fields=(),
            normalization_warnings=("Email validation deferred",),
            duplicate_group_id="DUP-DEF",
            duplicate_decision="deferred",  # Deferred decision
            duplicate_warnings=("Duplicate resolution deferred",),
            household_group_id="HH-DEF",
            household_group_label="Deferred Household",
            household_members=(4,),
            household_decision="deferred",  # Deferred decision
            household_warnings=("Household membership deferred",),
            export_warnings=(),
            export_blocked=False,
            export_derived_at=datetime.utcnow(),
        ),
    )

    csv_content = _generate_csv_content(rows)
    lines = csv_content.strip().split('\n')

    # Verify row count
    assert len(lines) == 4, "Expected 4 lines (1 header + 3 rows)"

    # Verify Row 1: Raw values (no decisions)
    reader = csv.reader([lines[1]])
    values = next(reader)
    assert values[0] == "1", "Row 1: source_row_index"
    assert values[1] == "TXN-RAW-001", "Row 1: transaction_id"
    assert values[4] == "alice.raw@example.com", "Row 1: raw email"
    assert values[14] == "", "Row 1: no normalized_fields"
    assert values[17] == "", "Row 1: no duplicate_decision"

    # Verify Row 2: Reviewed values (decisions applied)
    reader = csv.reader([lines[2]])
    values = next(reader)
    assert values[0] == "2", "Row 2: source_row_index"
    assert values[1] == "TXN-REV-001", "Row 2: transaction_id"
    assert values[4] == "bob.reviewed@example.com", "Row 2: effective email"
    assert values[5] == "555-2222", "Row 2: effective phone"
    assert values[14] == "email;phone", "Row 2: normalized_fields marked"
    assert values[17] == "same_person", "Row 2: duplicate decision applied"
    assert values[22] == "confirmed", "Row 2: household decision applied"

    # Verify Row 3: Deferred decisions
    reader = csv.reader([lines[3]])
    values = next(reader)
    assert values[0] == "3", "Row 3: source_row_index"
    assert values[1] == "TXN-DEF-001", "Row 3: transaction_id"
    assert values[12] == "deferred", "Row 3: validation_status is deferred"
    assert values[17] == "deferred", "Row 3: duplicate_decision is deferred"
    assert values[22] == "deferred", "Row 3: household_decision is deferred"
    assert "Email validation deferred" in values[15], "Row 3: normalization_warnings"
    assert "Duplicate resolution deferred" in values[18], "Row 3: duplicate_warnings"


# Filename Tests

def test_generate_safe_filename_format():
    """Filename follows expected format."""
    import_id = "IMP-TEST-001"
    timestamp = datetime(2026, 6, 12, 14, 30, 22)

    filename = _generate_safe_filename(import_id, timestamp)

    assert filename == "IMP-TEST-001_export_20260612_143022.csv"


# Unresolved Households Tests

def test_unresolved_household_warning_error_imported():
    """ExportUnresolvedHouseholdWarningError is properly imported and accessible."""
    from scripts.householder.export_file_service import ExportUnresolvedHouseholdWarningError

    error = ExportUnresolvedHouseholdWarningError(deferred_count=3)
    assert error.deferred_count == 3
    assert "3 unresolved household(s)" in error.message


@patch('scripts.householder.export_file_service.build_export_preview')
def test_export_raises_if_unresolved_and_not_confirmed(mock_preview, temp_export_dir, sample_export_row):
    """Export raises ExportUnresolvedHouseholdWarningError if deferred households exist and not confirmed."""
    from scripts.householder.export_file_service import ExportUnresolvedHouseholdWarningError

    # Mock preview with deferred households
    preview = ExportPreviewResult(
        import_id="IMP-TEST-001",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
        deferred_household_count=2,
    )
    mock_preview.return_value = preview

    with pytest.raises(ExportUnresolvedHouseholdWarningError) as exc_info:
        generate_export_file(
            import_id="IMP-TEST-001",
            output_dir=temp_export_dir,
            reviewer="test@example.com",
            config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
            confirmed_unresolved_households=False,
        )

    assert exc_info.value.deferred_count == 2


# Export Lifecycle Tests

def test_collision_handling_appends_suffixes(temp_export_dir):
    """Filename collision handling appends _01, _02 suffixes when file exists."""
    from scripts.householder.export_file_service import _get_safe_file_path

    # Create first file
    filename = "test_export_20260619_143022.csv"
    filepath1 = _get_safe_file_path(temp_export_dir, filename)

    # Create the first file
    Path(filepath1).touch()
    assert os.path.exists(filepath1)

    # Request same filename again; should get _01 suffix
    filepath2 = _get_safe_file_path(temp_export_dir, filename)

    assert filepath2 != filepath1, "Collision handling should return different path"
    assert "_01.csv" in filepath2, f"Expected _01 suffix, got: {filepath2}"
    assert not os.path.exists(filepath2), "Collision path should not exist yet"

    # Create the _01 file
    Path(filepath2).touch()
    assert os.path.exists(filepath2)

    # Request same filename third time; should get _02 suffix
    filepath3 = _get_safe_file_path(temp_export_dir, filename)

    assert filepath3 != filepath1 and filepath3 != filepath2, "Third path should be different"
    assert "_02.csv" in filepath3, f"Expected _02 suffix, got: {filepath3}"
    assert not os.path.exists(filepath3), "Collision path _02 should not exist yet"


def test_collision_handling_preserves_extension(temp_export_dir):
    """Collision suffix appends before extension, preserving .csv."""
    from scripts.householder.export_file_service import _get_safe_file_path

    filename = "export_data.csv"
    filepath1 = _get_safe_file_path(temp_export_dir, filename)
    Path(filepath1).touch()

    filepath2 = _get_safe_file_path(temp_export_dir, filename)

    # Verify suffix is before .csv, not after
    assert filepath2.endswith(".csv"), f"Expected .csv extension, got: {filepath2}"
    assert "_01.csv" in filepath2, f"Expected _01.csv pattern, got: {filepath2}"


@patch('scripts.householder.export_file_service.build_export_preview')
@patch('scripts.householder.export_file_service._create_audit_record')
def test_export_succeeds_if_unresolved_and_confirmed(mock_audit, mock_preview, temp_export_dir, sample_export_row):
    """Export succeeds if deferred households exist and user confirms."""
    # Mock preview with deferred households
    preview = ExportPreviewResult(
        import_id="IMP-TEST-001",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
        deferred_household_count=2,
    )
    mock_preview.return_value = preview
    mock_audit.return_value = 42

    result = generate_export_file(
        import_id="IMP-TEST-001",
        output_dir=temp_export_dir,
        reviewer="test@example.com",
        config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
        confirmed_unresolved_households=True,
    )

    assert result.import_id == "IMP-TEST-001"
    assert result.row_count == 1
    assert os.path.exists(result.file_path)


@patch('scripts.householder.export_file_service.build_export_preview')
@patch('scripts.householder.export_file_service._create_audit_record')
def test_export_succeeds_if_resolved_regardless_of_confirmation(mock_audit, mock_preview, temp_export_dir, sample_export_row):
    """Export succeeds if all households are resolved, regardless of confirmation param."""
    # Mock preview with NO deferred households
    preview = ExportPreviewResult(
        import_id="IMP-TEST-001",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
        deferred_household_count=0,
    )
    mock_preview.return_value = preview
    mock_audit.return_value = 42

    # Should succeed even with confirmed_unresolved_households=False
    result = generate_export_file(
        import_id="IMP-TEST-001",
        output_dir=temp_export_dir,
        reviewer="test@example.com",
        config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
        confirmed_unresolved_households=False,
    )

    assert result.import_id == "IMP-TEST-001"
    assert result.row_count == 1
    assert os.path.exists(result.file_path)


# Mixed Confirmation Enforcement Tests

@patch('scripts.householder.export_file_service.build_export_preview')
def test_mixed_validation_household_deferred_rejects_without_both_confirmations(mock_preview, temp_export_dir, sample_export_row):
    """Export with both deferred validation and households rejects if confirmations incomplete."""
    # Mock preview with both deferred validation and deferred households
    preview = ExportPreviewResult(
        import_id="IMP-MIXED-001",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
        deferred_validation_count=1,
        deferred_household_count=1,
    )
    mock_preview.return_value = preview

    # Test 1: Only household confirmed (validation not confirmed) → reject
    with pytest.raises(ExportUnresolvedValidationWarningError) as exc_info:
        generate_export_file(
            import_id="IMP-MIXED-001",
            output_dir=temp_export_dir,
            reviewer="test@example.com",
            config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
            confirmed_unresolved_households=True,
            confirmed_unresolved_validations=False,
        )
    assert exc_info.value.deferred_count == 1

    # Test 2: Only validation confirmed (household not confirmed) → reject
    with pytest.raises(ExportUnresolvedHouseholdWarningError) as exc_info:
        generate_export_file(
            import_id="IMP-MIXED-001",
            output_dir=temp_export_dir,
            reviewer="test@example.com",
            config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
            confirmed_unresolved_households=False,
            confirmed_unresolved_validations=True,
        )
    assert exc_info.value.deferred_count == 1


@patch('scripts.householder.export_file_service.build_export_preview')
@patch('scripts.householder.export_file_service._create_audit_record')
def test_mixed_validation_household_deferred_succeeds_with_both_confirmations(mock_audit, mock_preview, temp_export_dir, sample_export_row):
    """Export with both deferred validation and households succeeds when both confirmed."""
    # Mock preview with both deferred validation and deferred households
    preview = ExportPreviewResult(
        import_id="IMP-MIXED-002",
        export_rows=(sample_export_row,),
        blockers=(),
        warnings=(),
        row_count=1,
        blocked_count=0,
        warning_count=0,
        is_export_ready=True,
        derived_at=datetime.utcnow(),
        deferred_validation_count=1,
        deferred_household_count=1,
    )
    mock_preview.return_value = preview
    mock_audit.return_value = 42

    # Export with both confirmations should succeed
    result = generate_export_file(
        import_id="IMP-MIXED-002",
        output_dir=temp_export_dir,
        reviewer="test@example.com",
        config={'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'},
        confirmed_unresolved_households=True,
        confirmed_unresolved_validations=True,
    )

    assert result.import_id == "IMP-MIXED-002"
    assert result.row_count == 1
    assert os.path.exists(result.file_path)
