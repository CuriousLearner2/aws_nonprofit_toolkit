"""
Unit tests for normalizations review service.

Tests verify that the service boundary correctly transforms fixture data
into view models and dictionaries suitable for template rendering.
"""

import pytest
from scripts.householder.service_contracts import (
    NormalizationRow,
    NormalizationPageViewModel,
)
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.normalizations_service import get_normalizations_review


class TestNormalizationRow:
    """Test NormalizationRow view model."""

    def test_normalization_row_creation(self):
        """Test that NormalizationRow can be created with required fields."""
        row = NormalizationRow(
            id="NORM-001",
            contact_name="John Smith",
            field_name="Name",
            original_value="john smith",
            suggested_value="John Smith",
            normalization_type="Capitalization Fix",
            status="Pending",
        )
        assert row.id == "NORM-001"
        assert row.contact_name == "John Smith"
        assert row.field_name == "Name"

    def test_normalization_row_frozen(self):
        """Test that NormalizationRow is immutable."""
        row = NormalizationRow(
            id="NORM-001",
            contact_name="John Smith",
            field_name="Name",
            original_value="john smith",
            suggested_value="John Smith",
            normalization_type="Capitalization Fix",
            status="Pending",
        )
        with pytest.raises(AttributeError):
            row.contact_name = "Changed"

    def test_normalization_row_to_dict(self):
        """Test conversion to dictionary."""
        row = NormalizationRow(
            id="NORM-001",
            contact_name="John Smith",
            field_name="Name",
            original_value="john smith",
            suggested_value="John Smith",
            normalization_type="Capitalization Fix",
            status="Pending",
        )
        row_dict = row.to_dict()
        assert isinstance(row_dict, dict)
        assert row_dict["id"] == "NORM-001"
        assert row_dict["contact_name"] == "John Smith"
        assert row_dict["original_value"] == "john smith"
        assert row_dict["suggested_value"] == "John Smith"

    def test_normalization_row_default_status(self):
        """Test that status defaults to Pending."""
        row = NormalizationRow(
            id="NORM-001",
            contact_name="John Smith",
            field_name="Name",
            original_value="john smith",
            suggested_value="John Smith",
            normalization_type="Capitalization Fix",
        )
        assert row.status == "Pending"


class TestNormalizationPageViewModel:
    """Test NormalizationPageViewModel."""

    def test_normalization_page_view_model_creation(self):
        """Test that NormalizationPageViewModel can be created."""
        suggestion = NormalizationRow(
            id="NORM-001",
            contact_name="John Smith",
            field_name="Name",
            original_value="john smith",
            suggested_value="John Smith",
            normalization_type="Capitalization Fix",
            status="Pending",
        )
        vm = NormalizationPageViewModel(
            batch_id="IMP-TEST-001",
            filename="test.csv",
            progress=50,
            current_suggestion=suggestion,
            current_suggestion_index=1,
            total_suggestions=6,
        )
        assert vm.batch_id == "IMP-TEST-001"
        assert vm.progress == 50
        assert vm.current_suggestion_index == 1
        assert vm.total_suggestions == 6

    def test_normalization_page_view_model_to_template_dict(self):
        """Test conversion to template-compatible dict."""
        suggestion = NormalizationRow(
            id="NORM-001",
            contact_name="John Smith",
            field_name="Name",
            original_value="john smith",
            suggested_value="John Smith",
            normalization_type="Capitalization Fix",
            status="Pending",
        )
        vm = NormalizationPageViewModel(
            batch_id="IMP-TEST-002",
            filename="test2.csv",
            progress=75,
            current_suggestion=suggestion,
            current_suggestion_index=2,
            total_suggestions=6,
        )
        template_dict = vm.to_template_dict()
        assert isinstance(template_dict, dict)
        assert template_dict["batch"]["id"] == "IMP-TEST-002"
        assert template_dict["batch"]["filename"] == "test2.csv"
        assert template_dict["batch"]["progress"] == 75
        assert template_dict["current_suggestion"]["id"] == "NORM-001"
        assert template_dict["current_suggestion"]["contact_name"] == "John Smith"
        assert template_dict["current_suggestion_index"] == 2
        assert template_dict["total_suggestions"] == 6

    def test_normalization_page_view_model_frozen(self):
        """Test that NormalizationPageViewModel is immutable."""
        suggestion = NormalizationRow(
            id="NORM-001",
            contact_name="John Smith",
            field_name="Name",
            original_value="john smith",
            suggested_value="John Smith",
            normalization_type="Capitalization Fix",
            status="Pending",
        )
        vm = NormalizationPageViewModel(
            batch_id="IMP-TEST-003",
            filename="test.csv",
            progress=25,
            current_suggestion=suggestion,
            current_suggestion_index=1,
            total_suggestions=6,
        )
        with pytest.raises(AttributeError):
            vm.batch_id = "CHANGED"


class TestFixtureImportRepository:
    """Test FixtureImportRepository normalizations method."""

    def test_get_normalizations_returns_view_model(self):
        """Test that get_normalizations returns NormalizationPageViewModel."""
        normalizations = FixtureImportRepository.get_normalizations(
            "IMP-2025-0101-A"
        )
        assert isinstance(normalizations, NormalizationPageViewModel)

    def test_get_normalizations_batch_data(self):
        """Test that normalizations page contains correct batch data."""
        normalizations = FixtureImportRepository.get_normalizations(
            "IMP-2025-0101-A"
        )
        assert normalizations.batch_id == "IMP-2025-0101-A"
        assert normalizations.filename == "donors_q1_2025.csv"
        assert normalizations.progress == 42

    def test_get_normalizations_current_suggestion_index(self):
        """Test that normalizations page has correct current suggestion index."""
        normalizations = FixtureImportRepository.get_normalizations(
            "IMP-2025-0101-A"
        )
        assert normalizations.current_suggestion_index == 1

    def test_get_normalizations_total_suggestions(self):
        """Test that normalizations page contains correct total count."""
        normalizations = FixtureImportRepository.get_normalizations(
            "IMP-2025-0101-A"
        )
        assert normalizations.total_suggestions == 6

    def test_get_normalizations_current_suggestion(self):
        """Test that normalizations page has correct current suggestion."""
        normalizations = FixtureImportRepository.get_normalizations(
            "IMP-2025-0101-A"
        )
        suggestion = normalizations.current_suggestion
        assert suggestion.id == "NORM-001"
        assert suggestion.contact_name == "John Smith"
        assert suggestion.field_name == "Name"
        assert suggestion.original_value == "john smith"
        assert suggestion.suggested_value == "John Smith"
        assert suggestion.normalization_type == "Capitalization Fix"

    def test_get_normalizations_data_not_mutated(self):
        """Test that fixture data is not mutated by multiple calls."""
        normalizations1 = FixtureImportRepository.get_normalizations(
            "IMP-2025-0101-A"
        )
        normalizations2 = FixtureImportRepository.get_normalizations(
            "IMP-2025-0101-A"
        )
        assert normalizations1.batch_id == normalizations2.batch_id
        assert normalizations1.current_suggestion_index == normalizations2.current_suggestion_index
        assert normalizations1.total_suggestions == normalizations2.total_suggestions


class TestNormalizationsService:
    """Test normalizations_service module."""

    def test_get_normalizations_review_returns_dict(self):
        """Test that get_normalizations_review returns a dictionary."""
        result = get_normalizations_review("IMP-2025-0101-A")
        assert isinstance(result, dict)

    def test_get_normalizations_review_has_required_keys(self):
        """Test that returned dict has all required keys."""
        result = get_normalizations_review("IMP-2025-0101-A")
        assert "batch" in result
        assert "current_suggestion" in result
        assert "current_suggestion_index" in result
        assert "total_suggestions" in result

    def test_get_normalizations_review_batch_data(self):
        """Test that normalizations dict contains correct batch data."""
        result = get_normalizations_review("IMP-2025-0101-A")
        batch = result["batch"]
        assert batch["id"] == "IMP-2025-0101-A"
        assert batch["filename"] == "donors_q1_2025.csv"
        assert batch["progress"] == 42

    def test_get_normalizations_review_current_suggestion(self):
        """Test that normalizations dict contains current suggestion."""
        result = get_normalizations_review("IMP-2025-0101-A")
        suggestion = result["current_suggestion"]
        assert isinstance(suggestion, dict)
        assert suggestion["id"] == "NORM-001"
        assert suggestion["contact_name"] == "John Smith"
        assert suggestion["field_name"] == "Name"
        assert suggestion["original_value"] == "john smith"
        assert suggestion["suggested_value"] == "John Smith"

    def test_get_normalizations_review_current_suggestion_index(self):
        """Test that normalizations dict contains correct index."""
        result = get_normalizations_review("IMP-2025-0101-A")
        assert result["current_suggestion_index"] == 1

    def test_get_normalizations_review_total_suggestions(self):
        """Test that normalizations dict contains correct total."""
        result = get_normalizations_review("IMP-2025-0101-A")
        assert result["total_suggestions"] == 6

    def test_get_normalizations_review_template_ready(self):
        """Test that returned data is ready for Jinja2 template rendering."""
        result = get_normalizations_review("IMP-2025-0101-A")
        batch = result["batch"]
        suggestion = result["current_suggestion"]

        # Verify template can access all needed attributes
        assert batch["id"]
        assert batch["filename"]
        assert isinstance(batch["progress"], int)
        assert suggestion["id"]
        assert suggestion["contact_name"]
        assert suggestion["field_name"]
        assert suggestion["original_value"]
        assert suggestion["suggested_value"]
        assert suggestion["normalization_type"]
        assert isinstance(result["current_suggestion_index"], int)
        assert isinstance(result["total_suggestions"], int)
