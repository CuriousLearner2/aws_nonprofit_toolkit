"""
Unit tests for validation review service.

Tests verify that the service boundary correctly transforms fixture data
into view models and dictionaries suitable for template rendering.
"""

import pytest
from scripts.householder.service_contracts import (
    ValidationRow,
    ValidationPageViewModel,
)
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.validation_service import get_validation_review


class TestValidationRow:
    """Test ValidationRow view model."""

    def test_validation_row_creation(self):
        """Test that ValidationRow can be created with required fields."""
        row = ValidationRow(
            id="TXN-001",
            date="2026-05-15",
            name="John Smith",
            email="john@example.com",
            phone="(212) 555-1234",
            amount="$500.00",
            address="123 Main St, Springfield, IL 62701",
            issue_type="format-invalid",
            issue_description="Phone number format invalid",
        )
        assert row.id == "TXN-001"
        assert row.name == "John Smith"
        assert row.issue_type == "format-invalid"

    def test_validation_row_frozen(self):
        """Test that ValidationRow is immutable."""
        row = ValidationRow(
            id="TXN-001",
            date="2026-05-15",
            name="John Smith",
            email="john@example.com",
            phone="(212) 555-1234",
            amount="$500.00",
            address="123 Main St, Springfield, IL 62701",
            issue_type="format-invalid",
            issue_description="Phone number format invalid",
        )
        with pytest.raises(AttributeError):
            row.name = "Changed"

    def test_validation_row_to_dict(self):
        """Test conversion to dictionary."""
        row = ValidationRow(
            id="TXN-001",
            date="2026-05-15",
            name="John Smith",
            email="john@example.com",
            phone="(212) 555-1234",
            amount="$500.00",
            address="123 Main St, Springfield, IL 62701",
            issue_type="format-invalid",
            issue_description="Phone number format invalid",
        )
        row_dict = row.to_dict()
        assert isinstance(row_dict, dict)
        assert row_dict["id"] == "TXN-001"
        assert row_dict["name"] == "John Smith"
        assert row_dict["issue_type"] == "format-invalid"

    def test_validation_row_optional_issue_fields(self):
        """Test that issue_type and issue_description are optional."""
        row = ValidationRow(
            id="TXN-004",
            date="2026-05-18",
            name="Mary Johnson",
            email="mary.j@company.org",
            phone="(212) 555-9999",
            amount="$750.00",
            address="321 Pine Rd, Springfield, IL 62703",
        )
        assert row.issue_type is None
        assert row.issue_description is None
        row_dict = row.to_dict()
        assert row_dict["issue_type"] is None


class TestValidationPageViewModel:
    """Test ValidationPageViewModel."""

    def test_validation_page_view_model_creation(self):
        """Test that ValidationPageViewModel can be created."""
        rows = (
            ValidationRow(
                id="TXN-001",
                date="2026-05-15",
                name="John Smith",
                email="john@example.com",
                phone="(212) 555-1234",
                amount="$500.00",
                address="123 Main St, Springfield, IL 62701",
                issue_type="format-invalid",
                issue_description="Phone number format invalid",
            ),
        )
        vm = ValidationPageViewModel(
            batch_id="IMP-TEST-001",
            filename="test.csv",
            progress=50,
            validation_rows=rows,
            validation_issues_count=8,
            total_records=50,
        )
        assert vm.batch_id == "IMP-TEST-001"
        assert vm.progress == 50
        assert vm.validation_issues_count == 8
        assert len(vm.validation_rows) == 1

    def test_validation_page_view_model_to_template_dict(self):
        """Test conversion to template-compatible dict."""
        rows = (
            ValidationRow(
                id="TXN-001",
                date="2026-05-15",
                name="John Smith",
                email="john@example.com",
                phone="(212) 555-1234",
                amount="$500.00",
                address="123 Main St, Springfield, IL 62701",
                issue_type="format-invalid",
                issue_description="Phone number format invalid",
            ),
            ValidationRow(
                id="TXN-002",
                date="2026-05-16",
                name="Jane Doe",
                email="jane.doe@email.com",
                phone="(555) 987-6543",
                amount="$1,250.00",
                address="456 Oak Ave, Springfield, IL 62702",
                issue_type="missing-required",
                issue_description="Missing campaign field",
            ),
        )
        vm = ValidationPageViewModel(
            batch_id="IMP-TEST-002",
            filename="test2.csv",
            progress=75,
            validation_rows=rows,
            validation_issues_count=8,
            total_records=50,
        )
        template_dict = vm.to_template_dict()
        assert isinstance(template_dict, dict)
        assert template_dict["batch"]["id"] == "IMP-TEST-002"
        assert template_dict["batch"]["filename"] == "test2.csv"
        assert template_dict["batch"]["progress"] == 75
        assert len(template_dict["validation_issues"]) == 2
        assert template_dict["queue_status"]["validation_issues"] == 8
        assert template_dict["total_records"] == 50

    def test_validation_page_view_model_frozen(self):
        """Test that ValidationPageViewModel is immutable."""
        rows = (
            ValidationRow(
                id="TXN-001",
                date="2026-05-15",
                name="John Smith",
                email="john@example.com",
                phone="(212) 555-1234",
                amount="$500.00",
                address="123 Main St, Springfield, IL 62701",
            ),
        )
        vm = ValidationPageViewModel(
            batch_id="IMP-TEST-003",
            filename="test.csv",
            progress=25,
            validation_rows=rows,
            validation_issues_count=8,
            total_records=50,
        )
        with pytest.raises(AttributeError):
            vm.batch_id = "CHANGED"


class TestFixtureImportRepository:
    """Test FixtureImportRepository validation method."""

    def test_get_validation_returns_view_model(self):
        """Test that get_validation returns ValidationPageViewModel."""
        validation = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        assert isinstance(validation, ValidationPageViewModel)

    def test_get_validation_batch_data(self):
        """Test that validation page contains correct batch data."""
        validation = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        assert validation.batch_id == "IMP-2025-0101-A"
        assert validation.filename == "donors_q1_2025.csv"
        assert validation.progress == 42

    def test_get_validation_queue_count(self):
        """Test that validation page contains correct queue status."""
        validation = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        assert validation.validation_issues_count == 8

    def test_get_validation_total_records(self):
        """Test that validation page contains correct total records count."""
        validation = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        assert validation.total_records == 50

    def test_get_validation_rows_count(self):
        """Test that validation page contains correct number of validation rows."""
        validation = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        assert len(validation.validation_rows) == 5

    def test_get_validation_rows_structure(self):
        """Test that validation rows have correct structure."""
        validation = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        first_row = validation.validation_rows[0]
        assert first_row.id == "TXN-001"
        assert first_row.name == "John Smith"
        assert first_row.email == "john@example.com"
        assert first_row.issue_type is None  # TXN-001 is now a clean fixture row

    def test_get_validation_rows_with_no_issues(self):
        """Test that rows can have null issue fields."""
        validation = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        # TXN-004 has no issues
        row_004 = validation.validation_rows[3]
        assert row_004.id == "TXN-004"
        assert row_004.issue_type is None
        assert row_004.issue_description is None

    def test_get_validation_data_not_mutated(self):
        """Test that fixture data is not mutated by multiple calls."""
        validation1 = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        validation2 = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        assert validation1.batch_id == validation2.batch_id
        assert validation1.filename == validation2.filename
        assert len(validation1.validation_rows) == len(validation2.validation_rows)


class TestValidationService:
    """Test validation_service module."""

    def test_get_validation_review_returns_dict(self):
        """Test that get_validation_review returns a dictionary."""
        result = get_validation_review("IMP-2025-0101-A")
        assert isinstance(result, dict)

    def test_get_validation_review_has_required_keys(self):
        """Test that returned dict has all required keys."""
        result = get_validation_review("IMP-2025-0101-A")
        assert "batch" in result
        assert "validation_issues" in result
        assert "queue_status" in result
        assert "total_records" in result

    def test_get_validation_review_batch_data(self):
        """Test that validation dict contains correct batch data."""
        result = get_validation_review("IMP-2025-0101-A")
        batch = result["batch"]
        assert batch["id"] == "IMP-2025-0101-A"
        assert batch["filename"] == "donors_q1_2025.csv"
        assert batch["progress"] == 42

    def test_get_validation_review_validation_issues(self):
        """Test that validation dict contains correct validation issues."""
        result = get_validation_review("IMP-2025-0101-A")
        validation_issues = result["validation_issues"]
        assert isinstance(validation_issues, list)
        assert len(validation_issues) == 5
        assert validation_issues[0]["id"] == "TXN-001"
        assert validation_issues[0]["name"] == "John Smith"

    def test_get_validation_review_queue_status(self):
        """Test that validation dict contains correct queue status."""
        result = get_validation_review("IMP-2025-0101-A")
        queue_status = result["queue_status"]
        assert queue_status["validation_issues"] == 8

    def test_get_validation_review_total_records(self):
        """Test that validation dict contains correct total records."""
        result = get_validation_review("IMP-2025-0101-A")
        assert result["total_records"] == 50

    def test_get_validation_review_template_ready(self):
        """Test that returned data is ready for Jinja2 template rendering."""
        result = get_validation_review("IMP-2025-0101-A")
        batch = result["batch"]
        validation_issues = result["validation_issues"]
        queue_status = result["queue_status"]

        # Verify template can access all needed attributes
        assert batch["id"]
        assert batch["filename"]
        assert isinstance(batch["progress"], int)
        assert isinstance(validation_issues, list)
        for issue in validation_issues:
            assert issue["id"]
            assert issue["name"]
            assert issue["email"]
            assert issue["phone"]
            assert issue["amount"]
            assert "address" in issue
        assert isinstance(queue_status["validation_issues"], int)


class TestValidationServiceProviderWiring:
    """Test that validation_service uses repository provider (Phase 1B-Step 5L)."""

    def test_get_validation_review_default_uses_fixture_repository(self):
        """Test that default config returns fixture-backed validation."""
        result = get_validation_review("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"
        assert result["batch"]["progress"] == 42

    def test_get_validation_review_with_none_config_uses_fixture(self):
        """Test that None config explicitly uses fixture repository."""
        result = get_validation_review("IMP-2025-0101-A", config=None)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_validation_review_with_empty_config_uses_fixture(self):
        """Test that empty dict config uses fixture repository."""
        result = get_validation_review("IMP-2025-0101-A", config={})
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_validation_review_with_explicit_fixture_config(self):
        """Test that explicit fixture config returns fixture-backed validation."""
        config = {"HOUSEHOLDER_REPOSITORY": "fixture"}
        result = get_validation_review("IMP-2025-0101-A", config=config)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"

    def test_get_validation_review_database_mode_without_url_raises_error(self):
        """Test that database mode without GIVEBUTTER_DATABASE_URL raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "database"}
        with pytest.raises(ValueError) as exc_info:
            get_validation_review("IMP-2025-0101-A", config=config)
        assert "Database mode requested but no database URL configured" in str(exc_info.value)

    def test_get_validation_review_invalid_repository_mode_raises_error(self):
        """Test that invalid repository mode raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "invalid_mode"}
        with pytest.raises(ValueError) as exc_info:
            get_validation_review("IMP-2025-0101-A", config=config)
        assert "Invalid HOUSEHOLDER_REPOSITORY mode" in str(exc_info.value)

    def test_get_validation_review_template_dict_shape_unchanged(self):
        """Test that template dict shape is identical after provider wiring."""
        # Get validation with default (fixture)
        fixture_result = get_validation_review("IMP-2025-0101-A")
        # Get validation with explicit fixture config
        config_result = get_validation_review("IMP-2025-0101-A", config={"HOUSEHOLDER_REPOSITORY": "fixture"})

        # Both should have same shape and data
        assert fixture_result["batch"]["id"] == config_result["batch"]["id"]
        assert fixture_result["batch"]["filename"] == config_result["batch"]["filename"]
        assert fixture_result["batch"]["progress"] == config_result["batch"]["progress"]
        assert fixture_result["queue_status"] == config_result["queue_status"]
        assert fixture_result["total_records"] == config_result["total_records"]

    def test_get_validation_review_returns_dicts_not_orm_objects(self):
        """Test that result contains dicts, not ORM objects."""
        result = get_validation_review("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert isinstance(result["batch"], dict)
        assert isinstance(result["queue_status"], dict)
        assert isinstance(result["validation_issues"], list)
        # Verify no ORM objects
        assert not hasattr(result, '__table__')
        assert not hasattr(result["batch"], '__table__')




class TestValidationServiceFixtureFallbackValidation:
    """Test fixture-mode fallback validation when issue_type is None."""

    def test_fixture_fallback_catches_negative_amount(self):
        """Test that negative amount is caught even when fixture issue_type is None."""
        from scripts.householder.service_contracts import ValidationRow, ValidationPageViewModel
        from scripts.householder.validation_service import get_validation_review
        from unittest.mock import patch, MagicMock
        
        # Create a test row with negative amount and no fixture issue_type
        test_row = ValidationRow(
            id="TXN-NEG-AMT",
            raw_import_row_id=999,  # Trigger the database path (will fail and fall back)
            date="2026-05-20",
            name="Negative Amount Test",
            email="valid@example.com",
            phone="(212) 555-1234",
            amount="-100.00",
            address="123 Test St, Springfield, IL 62701",
            issue_type=None,
            issue_description=None,
        )
        
        test_vm = ValidationPageViewModel(
            batch_id="IMP-TEST-NEG",
            filename="test_negative.csv",
            progress=50,
            validation_rows=(test_row,),
            validation_issues_count=1,
            total_records=1,
        )
        
        # Mock the repository to return our test data
        with patch('scripts.householder.validation_service.get_import_repository') as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_validation.return_value = test_vm
            mock_get_repo.return_value = mock_repo
            
            # Call get_validation_review
            result = get_validation_review("IMP-TEST-NEG")
            
            # Verify the negative amount was caught
            issues = result['validation_issues'][0]['issues']
            assert len(issues) > 0, "Expected issues to be detected for negative amount"
            assert any('amount' in issue['field'].lower() for issue in issues), \
                f"Expected amount issue but got: {issues}"
            
            # Verify row status is Blocking (not "No issues")
            row_status = result['validation_issues'][0]['row_status']
            assert row_status == 'Blocking', f"Expected 'Blocking' but got '{row_status}'"

    def test_fixture_fallback_catches_invalid_email(self):
        """Test that invalid email is caught even when fixture issue_type is None."""
        from scripts.householder.service_contracts import ValidationRow, ValidationPageViewModel
        from scripts.householder.validation_service import get_validation_review
        from unittest.mock import patch, MagicMock
        
        # Create a test row with invalid email and no fixture issue_type
        test_row = ValidationRow(
            id="TXN-BAD-EMAIL",
            raw_import_row_id=998,
            date="2026-05-21",
            name="Bad Email Test",
            email="not-an-email",  # Missing @domain
            phone="(212) 555-1234",
            amount="$500.00",
            address="123 Test St, Springfield, IL 62701",
            issue_type=None,
            issue_description=None,
        )
        
        test_vm = ValidationPageViewModel(
            batch_id="IMP-TEST-BAD-EMAIL",
            filename="test_bad_email.csv",
            progress=50,
            validation_rows=(test_row,),
            validation_issues_count=1,
            total_records=1,
        )
        
        # Mock the repository to return our test data
        with patch('scripts.householder.validation_service.get_import_repository') as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_validation.return_value = test_vm
            mock_get_repo.return_value = mock_repo
            
            # Call get_validation_review
            result = get_validation_review("IMP-TEST-BAD-EMAIL")
            
            # Verify the invalid email was caught
            issues = result['validation_issues'][0]['issues']
            assert len(issues) > 0, "Expected issues to be detected for invalid email"
            assert any('email' in issue['field'].lower() for issue in issues), \
                f"Expected email issue but got: {issues}"
            
            # Verify row status is Blocking
            row_status = result['validation_issues'][0]['row_status']
            assert row_status == 'Blocking', f"Expected 'Blocking' but got '{row_status}'"

    def test_fixture_fallback_catches_missing_amount(self):
        """Test that missing amount is caught even when fixture issue_type is None."""
        from scripts.householder.service_contracts import ValidationRow, ValidationPageViewModel
        from scripts.householder.validation_service import get_validation_review
        from unittest.mock import patch, MagicMock
        
        # Create a test row with missing amount and no fixture issue_type
        test_row = ValidationRow(
            id="TXN-NO-AMT",
            raw_import_row_id=997,
            date="2026-05-22",
            name="Missing Amount Test",
            email="valid@example.com",
            phone="(212) 555-1234",
            amount="",  # Empty amount
            address="123 Test St, Springfield, IL 62701",
            issue_type=None,
            issue_description=None,
        )
        
        test_vm = ValidationPageViewModel(
            batch_id="IMP-TEST-NO-AMT",
            filename="test_no_amount.csv",
            progress=50,
            validation_rows=(test_row,),
            validation_issues_count=1,
            total_records=1,
        )
        
        # Mock the repository to return our test data
        with patch('scripts.householder.validation_service.get_import_repository') as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_validation.return_value = test_vm
            mock_get_repo.return_value = mock_repo
            
            # Call get_validation_review
            result = get_validation_review("IMP-TEST-NO-AMT")
            
            # Verify the missing amount was caught
            issues = result['validation_issues'][0]['issues']
            assert len(issues) > 0, "Expected issues to be detected for missing amount"
            assert any('amount' in issue['field'].lower() for issue in issues), \
                f"Expected amount issue but got: {issues}"
            
            # Verify row status is Blocking
            row_status = result['validation_issues'][0]['row_status']
            assert row_status == 'Blocking', f"Expected 'Blocking' but got '{row_status}'"

    def test_fixture_fallback_date_is_currently_unsupported_in_validation_review(self):
        """Test that Validation Review fallback currently does not validate date-only issues."""
        from scripts.householder.service_contracts import ValidationRow, ValidationPageViewModel
        from scripts.householder.validation_service import get_validation_review
        from unittest.mock import patch, MagicMock

        test_row = ValidationRow(
            id="TXN-UNSUPPORTED-DATE",
            raw_import_row_id=995,
            date="not-a-real-date",
            name="Date Unsupported Test",
            email="valid@example.com",
            phone="(212) 555-1234",
            amount="$250.00",
            address="123 Test St, Springfield, IL 62701",
            issue_type=None,
            issue_description=None,
        )

        test_vm = ValidationPageViewModel(
            batch_id="IMP-TEST-UNSUPPORTED-DATE",
            filename="test_date_unsupported.csv",
            progress=50,
            validation_rows=(test_row,),
            validation_issues_count=0,
            total_records=1,
        )

        with patch('scripts.householder.validation_service.get_import_repository') as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_validation.return_value = test_vm
            mock_get_repo.return_value = mock_repo

            result = get_validation_review("IMP-TEST-UNSUPPORTED-DATE")

            row = result['validation_issues'][0]
            assert row['issues'] == [], (
                "Validation Review fallback currently ignores date-only issues, "
                f"but got: {row['issues']}"
            )
            assert row['row_status'] == 'No issues', (
                "Validation Review fallback currently treats invalid-looking dates as clean, "
                f"but got row_status={row['row_status']}"
            )

    def test_fixture_fallback_address_is_currently_unsupported_in_validation_review(self):
        """Test that Validation Review fallback currently does not validate address-only issues."""
        from scripts.householder.service_contracts import ValidationRow, ValidationPageViewModel
        from scripts.householder.validation_service import get_validation_review
        from unittest.mock import patch, MagicMock

        test_row = ValidationRow(
            id="TXN-UNSUPPORTED-ADDRESS",
            raw_import_row_id=994,
            date="2026-05-24",
            name="Address Unsupported Test",
            email="valid@example.com",
            phone="(212) 555-1234",
            amount="$250.00",
            address="789 Elm St, Springfield IL",
            issue_type=None,
            issue_description=None,
        )

        test_vm = ValidationPageViewModel(
            batch_id="IMP-TEST-UNSUPPORTED-ADDRESS",
            filename="test_address_unsupported.csv",
            progress=50,
            validation_rows=(test_row,),
            validation_issues_count=0,
            total_records=1,
        )

        with patch('scripts.householder.validation_service.get_import_repository') as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_validation.return_value = test_vm
            mock_get_repo.return_value = mock_repo

            result = get_validation_review("IMP-TEST-UNSUPPORTED-ADDRESS")

            row = result['validation_issues'][0]
            assert row['issues'] == [], (
                "Validation Review fallback currently ignores address-only issues, "
                f"but got: {row['issues']}"
            )
            assert row['row_status'] == 'No issues', (
                "Validation Review fallback currently treats malformed addresses as clean, "
                f"but got row_status={row['row_status']}"
            )

    def test_fixture_fallback_valid_row_still_no_issues(self):
        """Test that valid fixture rows with issue_type=None still render as 'No issues'."""
        from scripts.householder.service_contracts import ValidationRow, ValidationPageViewModel
        from scripts.householder.validation_service import get_validation_review
        from unittest.mock import patch, MagicMock
        
        # Create a test row with valid data and no fixture issue_type
        test_row = ValidationRow(
            id="TXN-VALID",
            raw_import_row_id=996,
            date="2026-05-23",
            name="Valid Row Test",
            email="valid@example.com",
            phone="(212) 555-1234",
            amount="$250.00",
            address="123 Test St, Springfield, IL 62701",
            issue_type=None,
            issue_description=None,
        )
        
        test_vm = ValidationPageViewModel(
            batch_id="IMP-TEST-VALID",
            filename="test_valid.csv",
            progress=50,
            validation_rows=(test_row,),
            validation_issues_count=0,
            total_records=1,
        )
        
        # Mock the repository to return our test data
        with patch('scripts.householder.validation_service.get_import_repository') as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.get_validation.return_value = test_vm
            mock_get_repo.return_value = mock_repo
            
            # Call get_validation_review
            result = get_validation_review("IMP-TEST-VALID")
            
            # Verify no issues were detected
            issues = result['validation_issues'][0]['issues']
            assert len(issues) == 0, f"Expected no issues for valid row but got: {issues}"
            
            # Verify row status is "No issues"
            row_status = result['validation_issues'][0]['row_status']
            assert row_status == 'No issues', f"Expected 'No issues' but got '{row_status}'"

    def test_fixture_fallback_existing_row_txn004_still_valid(self):
        """Test that existing TXN-004 (Mary Johnson) still renders as 'No issues'."""
        # This verifies that the fallback validation doesn't break existing behavior
        result = get_validation_review("IMP-2025-0101-A")
        
        # Find TXN-004
        row_004 = None
        for issue in result['validation_issues']:
            if issue['id'] == 'TXN-004':
                row_004 = issue
                break
        
        assert row_004 is not None, "TXN-004 not found in validation results"
        
        # Verify it still has no issues (valid data, issue_type=None)
        assert len(row_004['issues']) == 0, \
            f"TXN-004 should have no issues but got: {row_004['issues']}"
        
        # Verify row status is "No issues"
        assert row_004['row_status'] == 'No issues', \
            f"TXN-004 should have 'No issues' status but got '{row_004['row_status']}'"
