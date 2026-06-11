"""
Unit tests for exports console service.

Tests verify that the service boundary correctly transforms fixture data
into view models and dictionaries suitable for template rendering.
"""

import pytest
from scripts.householder.service_contracts import (
    ExportCard,
    ExportConsoleViewModel,
)
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.exports_service import get_export_console


class TestExportCard:
    """Test ExportCard view model."""

    def test_export_card_creation(self):
        """Test that ExportCard can be created with required fields."""
        card = ExportCard(
            id="EXPORT-REVIEWED",
            title="Reviewed Export",
            description="CSV reflecting reviewer-confirmed duplicate decisions",
            status="Generated",
            files_ready=1,
        )
        assert card.id == "EXPORT-REVIEWED"
        assert card.title == "Reviewed Export"
        assert card.status == "Generated"

    def test_export_card_frozen(self):
        """Test that ExportCard is immutable."""
        card = ExportCard(
            id="EXPORT-REVIEWED",
            title="Reviewed Export",
            description="CSV reflecting reviewer-confirmed duplicate decisions",
            status="Generated",
            files_ready=1,
        )
        with pytest.raises(AttributeError):
            card.title = "Changed"

    def test_export_card_to_dict(self):
        """Test conversion to dictionary."""
        card = ExportCard(
            id="EXPORT-REVIEWED",
            title="Reviewed Export",
            description="CSV reflecting reviewer-confirmed duplicate decisions",
            status="Generated",
            files_ready=1,
        )
        card_dict = card.to_dict()
        assert isinstance(card_dict, dict)
        assert card_dict["id"] == "EXPORT-REVIEWED"
        assert card_dict["title"] == "Reviewed Export"


class TestExportConsoleViewModel:
    """Test ExportConsoleViewModel."""

    def test_export_console_view_model_creation(self):
        """Test that ExportConsoleViewModel can be created."""
        card = ExportCard("EXPORT-1", "Export 1", "Description", "Ready", 1)
        vm = ExportConsoleViewModel(
            batch_id="IMP-TEST-001",
            filename="test.csv",
            progress=50,
            export_cards=(card,),
            staged_record_count=25,
            total_decisions=10,
            household_count=5,
            recent_exports=(),
        )
        assert vm.batch_id == "IMP-TEST-001"
        assert vm.progress == 50
        assert vm.staged_record_count == 25

    def test_export_console_view_model_to_template_dict(self):
        """Test conversion to template-compatible dict."""
        card = ExportCard("EXPORT-1", "Export 1", "Description", "Ready", 1)
        vm = ExportConsoleViewModel(
            batch_id="IMP-TEST-002",
            filename="test2.csv",
            progress=75,
            export_cards=(card,),
            staged_record_count=30,
            total_decisions=12,
            household_count=6,
            recent_exports=(),
        )
        template_dict = vm.to_template_dict()
        assert isinstance(template_dict, dict)
        assert template_dict["batch"]["id"] == "IMP-TEST-002"
        assert template_dict["batch"]["filename"] == "test2.csv"
        assert template_dict["batch"]["progress"] == 75
        assert template_dict["staged_record_count"] == 30
        assert template_dict["total_decisions"] == 12
        assert template_dict["household_count"] == 6
        assert len(template_dict["export_options"]) == 1

    def test_export_console_view_model_frozen(self):
        """Test that ExportConsoleViewModel is immutable."""
        card = ExportCard("EXPORT-1", "Export 1", "Description", "Ready", 1)
        vm = ExportConsoleViewModel(
            "IMP-TEST-003", "test.csv", 25, (card,), 20, 8, 4, ()
        )
        with pytest.raises(AttributeError):
            vm.batch_id = "CHANGED"


class TestFixtureImportRepository:
    """Test FixtureImportRepository exports method."""

    def test_get_exports_returns_view_model(self):
        """Test that get_exports returns ExportConsoleViewModel."""
        exports = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        assert isinstance(exports, ExportConsoleViewModel)

    def test_get_exports_batch_data(self):
        """Test that exports page contains correct batch data."""
        exports = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        assert exports.batch_id == "IMP-2025-0101-A"
        assert exports.filename == "donors_q1_2025.csv"
        assert exports.progress == 42

    def test_get_exports_has_export_cards(self):
        """Test that exports page contains export cards."""
        exports = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        assert len(exports.export_cards) > 0

    def test_get_exports_export_card_fields(self):
        """Test that export cards have required fields."""
        exports = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        first_card = exports.export_cards[0]
        assert hasattr(first_card, 'id')
        assert hasattr(first_card, 'title')
        assert hasattr(first_card, 'description')
        assert hasattr(first_card, 'status')
        assert hasattr(first_card, 'files_ready')

    def test_get_exports_first_card_has_data(self):
        """Test that first export card has expected data."""
        exports = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        first_card = exports.export_cards[0]
        assert first_card.id == "EXPORT-REVIEWED"
        assert "Reviewed" in first_card.title or "Export" in first_card.title

    def test_get_exports_staging_statistics(self):
        """Test that exports page contains staging statistics."""
        exports = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        assert exports.staged_record_count > 0
        assert isinstance(exports.total_decisions, int)
        assert isinstance(exports.household_count, int)

    def test_get_exports_recent_exports_empty(self):
        """Test that recent_exports is empty for fixture-backed phase 1a."""
        exports = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        assert len(exports.recent_exports) == 0

    def test_get_exports_data_not_mutated(self):
        """Test that fixture data is not mutated by multiple calls."""
        exports1 = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        exports2 = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        assert exports1.batch_id == exports2.batch_id
        assert len(exports1.export_cards) == len(exports2.export_cards)
        assert exports1.staged_record_count == exports2.staged_record_count


class TestExportsService:
    """Test exports_service module."""

    def test_get_export_console_returns_dict(self):
        """Test that get_export_console returns a dictionary."""
        result = get_export_console("IMP-2025-0101-A")
        assert isinstance(result, dict)

    def test_get_export_console_has_required_keys(self):
        """Test that returned dict has all required keys."""
        result = get_export_console("IMP-2025-0101-A")
        assert "batch" in result
        assert "export_options" in result
        assert "staged_record_count" in result
        assert "total_decisions" in result
        assert "household_count" in result
        assert "recent_exports" in result

    def test_get_export_console_batch_data(self):
        """Test that exports dict contains correct batch data."""
        result = get_export_console("IMP-2025-0101-A")
        batch = result["batch"]
        assert batch["id"] == "IMP-2025-0101-A"
        assert batch["filename"] == "donors_q1_2025.csv"
        assert batch["progress"] == 42

    def test_get_export_console_export_options(self):
        """Test that exports dict contains export options."""
        result = get_export_console("IMP-2025-0101-A")
        export_options = result["export_options"]
        assert isinstance(export_options, list)
        assert len(export_options) > 0

    def test_get_export_console_option_structure(self):
        """Test that export options have expected structure."""
        result = get_export_console("IMP-2025-0101-A")
        export_options = result["export_options"]
        first_option = export_options[0]
        assert "id" in first_option
        assert "title" in first_option
        assert "description" in first_option
        assert "status" in first_option
        assert "files_ready" in first_option

    def test_get_export_console_statistics(self):
        """Test that exports dict contains staging statistics."""
        result = get_export_console("IMP-2025-0101-A")
        assert isinstance(result["staged_record_count"], int)
        assert isinstance(result["total_decisions"], int)
        assert isinstance(result["household_count"], int)
        assert result["staged_record_count"] > 0

    def test_get_export_console_template_ready(self):
        """Test that returned data is ready for Jinja2 template rendering."""
        result = get_export_console("IMP-2025-0101-A")
        batch = result["batch"]
        export_options = result["export_options"]

        # Verify template can access all needed attributes
        assert batch["id"]
        assert batch["filename"]
        assert isinstance(batch["progress"], int)
        assert len(export_options) > 0
        first_option = export_options[0]
        assert first_option["title"]
        assert first_option["description"]

    def test_get_export_console_no_file_generation(self):
        """Test that service does not generate real export files."""
        result = get_export_console("IMP-2025-0101-A")
        # Verify no file writing side effects by checking recent_exports is empty
        assert len(result["recent_exports"]) == 0
