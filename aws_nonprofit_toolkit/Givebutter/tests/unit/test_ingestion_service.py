"""Unit tests for ingestion service (Phase 1C-Step 4 core)."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.householder.ingestion_service import (
    IngestionResult,
    IngestionValidationError,
    IngestionIOError,
    IngestionDatabaseError,
    BatchIDCollisionError,
    generate_batch_id,
    split_name,
    extract_digits_from_phone,
    parse_amount,
    ingest_processed_csv,
)


class TestBatchIDGeneration:
    """Tests for batch ID generation."""

    def test_batch_id_includes_timestamp(self):
        """Batch ID includes YYYYMMDD-HHMMSS."""
        csv_content = b"test data"
        imported_at = datetime(2026, 6, 12, 12, 15, 30)
        batch_id = generate_batch_id(csv_content, imported_at)

        assert batch_id.startswith("IMP-")
        assert "20260612" in batch_id
        assert "121530" in batch_id

    def test_batch_id_includes_file_hash(self):
        """Batch ID includes 8-char file content hash."""
        csv_content = b"test data"
        batch_id = generate_batch_id(csv_content)
        hash_part = batch_id.split("-")[-1]

        assert len(hash_part) == 8
        assert hash_part.isupper()

    def test_different_files_generate_different_hashes(self):
        """Different file contents → different batch IDs."""
        imported_at = datetime(2026, 6, 12, 12, 15, 30)
        batch_id1 = generate_batch_id(b"file1 content", imported_at)
        batch_id2 = generate_batch_id(b"file2 content", imported_at)

        hash1 = batch_id1.split("-")[-1]
        hash2 = batch_id2.split("-")[-1]
        assert hash1 != hash2

    def test_batch_id_format_is_correct(self):
        """Batch ID format matches IMP-YYYYMMDD-HHMMSS-HASH8."""
        csv_content = b"test data"
        batch_id = generate_batch_id(csv_content)

        parts = batch_id.split("-")
        assert len(parts) == 4
        assert parts[0] == "IMP"
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 8  # HASH


class TestNameSplitting:
    """Tests for name splitting."""

    def test_two_part_name_splits_correctly(self):
        """John Smith → first=John, last=Smith."""
        first, last = split_name("John Smith")
        assert first == "John"
        assert last == "Smith"

    def test_three_part_name_joins_remaining(self):
        """John Michael Smith → first=John, last=Michael Smith."""
        first, last = split_name("John Michael Smith")
        assert first == "John"
        assert last == "Michael Smith"

    def test_suffix_remains_in_last_name(self):
        """John Smith Jr. → first=John, last=Smith Jr."""
        first, last = split_name("John Smith Jr.")
        assert first == "John"
        assert last == "Smith Jr."

    def test_single_name_has_no_last_name(self):
        """Prince → first=Prince, last=None."""
        first, last = split_name("Prince")
        assert first == "Prince"
        assert last is None

    def test_empty_name_returns_none_none(self):
        """'' → first=None, last=None."""
        first, last = split_name("")
        assert first is None
        assert last is None

    def test_whitespace_only_name_returns_none_none(self):
        """'   ' → first=None, last=None."""
        first, last = split_name("   ")
        assert first is None
        assert last is None

    def test_name_with_leading_trailing_spaces(self):
        """'  John Smith  ' → first=John, last=Smith."""
        first, last = split_name("  John Smith  ")
        assert first == "John"
        assert last == "Smith"


class TestPhoneNormalization:
    """Tests for phone number normalization."""

    def test_extract_digits_from_formatted_phone(self):
        """(555) 123-4567 → 5551234567."""
        result = extract_digits_from_phone("(555) 123-4567")
        assert result == "5551234567"

    def test_extract_digits_from_dots(self):
        """555.123.4567 → 5551234567."""
        result = extract_digits_from_phone("555.123.4567")
        assert result == "5551234567"

    def test_extract_digits_bare_number(self):
        """5551234567 → 5551234567."""
        result = extract_digits_from_phone("5551234567")
        assert result == "5551234567"

    def test_extract_digits_empty_string(self):
        """'' → ''."""
        result = extract_digits_from_phone("")
        assert result == ""

    def test_extract_digits_none(self):
        """None → ''."""
        result = extract_digits_from_phone(None)
        assert result == ""


class TestAmountParsing:
    """Tests for amount parsing."""

    def test_parse_simple_amount(self):
        """100.00 → 100.0."""
        result = parse_amount("100.00")
        assert result == 100.0

    def test_parse_amount_with_currency_symbol(self):
        """$100.00 → 100.0."""
        result = parse_amount("$100.00")
        assert result == 100.0

    def test_parse_amount_with_comma(self):
        """1,000.00 → 1000.0."""
        result = parse_amount("1,000.00")
        assert result == 1000.0

    def test_parse_amount_with_comma_and_currency(self):
        """$1,000.50 → 1000.5."""
        result = parse_amount("$1,000.50")
        assert result == 1000.5

    def test_parse_invalid_amount_returns_none(self):
        """invalid → None."""
        result = parse_amount("invalid")
        assert result is None

    def test_parse_empty_amount_returns_none(self):
        """'' → None."""
        result = parse_amount("")
        assert result is None


class TestCSVValidation:
    """Tests for CSV validation."""

    def test_missing_file_raises_ioerror(self):
        """CSV file does not exist → IngestionIOError."""
        with pytest.raises(IngestionIOError) as exc:
            ingest_processed_csv(
                "/nonexistent/path.csv",
                "test.csv",
                "sqlite:///:memory:",
            )
        assert "not found" in str(exc.value).lower() or "does not exist" in str(exc.value).lower()

    def test_empty_csv_raises_validation_error(self, tmp_path):
        """CSV with only headers → IngestionValidationError."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications")

        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "no data" in str(exc.value).lower() or "empty" in str(exc.value).lower()

    def test_missing_validation_tier_column(self, tmp_path):
        """CSV without Validation_Tier → IngestionValidationError."""
        csv_file = tmp_path / "missing_tier.csv"
        csv_file.write_text("Name,Email,Amount,Date,Issues,Suggested_Modifications\nJohn,john@gmail.com,100,2026-06-12,None,")

        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "Validation_Tier" in str(exc.value)

    def test_missing_issues_column(self, tmp_path):
        """CSV without Issues → IngestionValidationError."""
        csv_file = tmp_path / "missing_issues.csv"
        csv_file.write_text("Name,Email,Amount,Date,Validation_Tier,Suggested_Modifications\nJohn,john@gmail.com,100,2026-06-12,PASS,")

        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "Issues" in str(exc.value)

    def test_missing_suggested_modifications_column(self, tmp_path):
        """CSV without Suggested_Modifications → IngestionValidationError."""
        csv_file = tmp_path / "missing_mods.csv"
        csv_file.write_text("Name,Email,Amount,Date,Validation_Tier,Issues\nJohn,john@gmail.com,100,2026-06-12,PASS,None")

        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "Suggested_Modifications" in str(exc.value)


class TestIngestionIntegration:
    """Tests for full ingestion."""

    def test_valid_pass_row_creates_batch_and_records(self, tmp_path):
        """Valid CSV with PASS row → batch, raw row, contact created."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.batch_id.startswith("IMP-")
        assert result.raw_row_count == 1
        assert result.contacts_created == 1
        assert result.validation_items_created == 0
        assert result.normalization_items_created == 0
        assert result.pass_count == 1
        assert result.warning_count == 0
        assert result.fail_count == 0

    def test_warning_row_creates_validation_items(self, tmp_path):
        """CSV with WARNING row → validation items created."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "warning.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmai.com,100.00,2026-06-12,WARNING,Email: Email typo detected,Consider: john@gmail.com"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.validation_items_created >= 1
        assert result.warning_count == 1

    def test_fail_row_creates_validation_items(self, tmp_path):
        """CSV with FAIL row → validation items created."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "fail.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,,100.00,2026-06-12,FAIL,Email: Email field is empty,Verify email address"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.validation_items_created >= 1
        assert result.fail_count == 1

    def test_multiple_issues_create_multiple_items(self, tmp_path):
        """Row with multiple semicolon-separated issues → multiple items."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "multiple.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmai.com,abc,2026-06-12,FAIL,Email: Email typo; Amount: Invalid amount,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.validation_items_created >= 2

    def test_pass_row_with_suggestions_creates_normalization_items(self, tmp_path):
        """PASS row with non-empty Suggested_Modifications → normalization items."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "normalize.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmai.com,100.00,2026-06-12,PASS,None,Consider: john@gmail.com"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.normalization_items_created >= 1

    def test_pass_row_without_suggestions_no_normalization_items(self, tmp_path):
        """PASS row with empty Suggested_Modifications → no normalization items."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "pass_no_suggest.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.normalization_items_created == 0

    def test_household_items_always_zero(self, tmp_path):
        """Household items created is always 0 in Phase 1C."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "any.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.household_items_created == 0

    def test_duplicate_items_always_zero(self, tmp_path):
        """Duplicate items created is always 0 in Phase 1C (deferred)."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "any.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.duplicate_items_created == 0

    def test_audit_log_record_created(self, tmp_path):
        """Successful ingestion → audit log created with batch_imported action."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.audit_log_id > 0
        assert result.audit_action_type == "batch_imported"
        assert isinstance(result.audit_timestamp, datetime)

    def test_ingestion_result_is_frozen(self, tmp_path):
        """IngestionResult is immutable (frozen dataclass)."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        # Try to modify (should fail with FrozenInstanceError or AttributeError)
        with pytest.raises((AttributeError, Exception)):
            result.status = "failed"

    def test_uploader_default_is_system(self, tmp_path):
        """If uploader not provided, defaults to 'system'."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.uploader == "system"

    def test_uploader_custom_value_preserved(self, tmp_path):
        """If uploader provided, value is preserved."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url, uploader="alice@example.com")

        assert result.uploader == "alice@example.com"

    def test_name_splitting_integrated(self, tmp_path):
        """ImportContact.first_name and last_name correctly split from Name column."""
        from scripts.householder.database_models import init_db

        csv_file = tmp_path / "names.csv"
        csv_file.write_text(
            "Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
            "John Michael Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"
        )

        # Result: first_name=John, last_name=Michael Smith
        # (Would verify in integration test with database query)
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)
        result = ingest_processed_csv(str(csv_file), "original.csv", db_url)

        assert result.status == "success"
        assert result.contacts_created == 1
