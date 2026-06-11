"""
Unit tests for DonorTrust v1 dashboard service.

Tests verify that the service boundary correctly transforms fixture data
into view models and dictionaries suitable for template rendering.
"""

import pytest
from scripts.householder.service_contracts import (
    ImportDashboardViewModel,
    DashboardQueueCard,
)
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.dashboard_service import get_import_dashboard


class TestDashboardQueueCard:
    """Test DashboardQueueCard view model."""

    def test_queue_card_creation(self):
        """Test that DashboardQueueCard can be created with required fields."""
        card = DashboardQueueCard(
            name="Test Queue",
            description="Test description",
            pending_count=5,
            badge_color="badge-blue",
            action_label="Test Action",
            action_url="/test/path",
        )
        assert card.name == "Test Queue"
        assert card.pending_count == 5
        assert card.action_url == "/test/path"

    def test_queue_card_frozen(self):
        """Test that DashboardQueueCard is immutable."""
        card = DashboardQueueCard(
            name="Test Queue",
            description="Test description",
            pending_count=5,
            badge_color="badge-blue",
            action_label="Test Action",
            action_url="/test/path",
        )
        with pytest.raises(AttributeError):
            card.name = "Changed"


class TestImportDashboardViewModel:
    """Test ImportDashboardViewModel."""

    def test_dashboard_view_model_creation(self):
        """Test that ImportDashboardViewModel can be created."""
        queues = (
            DashboardQueueCard(
                name="Duplicates",
                description="Duplicates",
                pending_count=3,
                badge_color="badge-amber",
                action_label="Review",
                action_url="/test/duplicates",
            ),
            DashboardQueueCard(
                name="Validation",
                description="Validation",
                pending_count=8,
                badge_color="badge-red",
                action_label="Review",
                action_url="/test/validation",
            ),
        )
        vm = ImportDashboardViewModel(
            batch_id="TEST-001",
            filename="test.csv",
            progress=50,
            queues=queues,
            audit_log_url="/test/audit",
            export_console_url="/test/exports",
            back_to_imports_url="/imports",
        )
        assert vm.batch_id == "TEST-001"
        assert vm.progress == 50
        assert len(vm.queues) == 2

    def test_dashboard_view_model_to_template_dict(self):
        """Test conversion to template-compatible dict."""
        queues = (
            DashboardQueueCard(
                name="Duplicates",
                description="Duplicates",
                pending_count=3,
                badge_color="badge-amber",
                action_label="Review",
                action_url="/test/duplicates",
            ),
            DashboardQueueCard(
                name="Validation",
                description="Validation",
                pending_count=8,
                badge_color="badge-red",
                action_label="Review",
                action_url="/test/validation",
            ),
            DashboardQueueCard(
                name="Normalizations",
                description="Normalizations",
                pending_count=6,
                badge_color="badge-blue",
                action_label="Review",
                action_url="/test/normalizations",
            ),
            DashboardQueueCard(
                name="Households",
                description="Households",
                pending_count=5,
                badge_color="badge-green",
                action_label="Review",
                action_url="/test/households",
            ),
        )
        vm = ImportDashboardViewModel(
            batch_id="TEST-002",
            filename="test2.csv",
            progress=75,
            queues=queues,
            audit_log_url="/test/audit",
            export_console_url="/test/exports",
            back_to_imports_url="/imports",
        )
        template_dict = vm.to_template_dict()
        assert isinstance(template_dict, dict)
        assert template_dict["batch"]["id"] == "TEST-002"
        assert template_dict["batch"]["filename"] == "test2.csv"
        assert template_dict["batch"]["progress"] == 75
        assert template_dict["queue_status"]["duplicates_pending"] == 3
        assert template_dict["queue_status"]["validation_issues"] == 8
        assert template_dict["queue_status"]["normalizations_pending"] == 6
        assert template_dict["queue_status"]["households_pending"] == 5

    def test_dashboard_view_model_frozen(self):
        """Test that ImportDashboardViewModel is immutable."""
        queues = (
            DashboardQueueCard(
                name="Test",
                description="Test",
                pending_count=1,
                badge_color="badge-blue",
                action_label="Test",
                action_url="/test",
            ),
        )
        vm = ImportDashboardViewModel(
            batch_id="TEST-003",
            filename="test.csv",
            progress=25,
            queues=queues,
            audit_log_url="/test/audit",
            export_console_url="/test/exports",
            back_to_imports_url="/imports",
        )
        with pytest.raises(AttributeError):
            vm.batch_id = "CHANGED"


class TestFixtureImportRepository:
    """Test FixtureImportRepository dashboard method."""

    def test_get_dashboard_returns_view_model(self):
        """Test that get_dashboard returns ImportDashboardViewModel."""
        dashboard = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert isinstance(dashboard, ImportDashboardViewModel)

    def test_get_dashboard_batch_data(self):
        """Test that dashboard contains correct batch data."""
        dashboard = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert dashboard.batch_id == "IMP-2025-0101-A"
        assert dashboard.filename == "donors_q1_2025.csv"
        assert dashboard.progress == 42

    def test_get_dashboard_queue_counts(self):
        """Test that dashboard contains correct queue counts from fixture."""
        dashboard = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert len(dashboard.queues) == 4
        assert dashboard.queues[0].pending_count == 3  # duplicates
        assert dashboard.queues[1].pending_count == 8  # validation
        assert dashboard.queues[2].pending_count == 6  # normalizations
        assert dashboard.queues[3].pending_count == 5  # households

    def test_get_dashboard_queue_cards(self):
        """Test that dashboard queues have correct names and colors."""
        dashboard = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert dashboard.queues[0].name == "Possible Duplicates"
        assert dashboard.queues[0].badge_color == "badge-amber"
        assert dashboard.queues[1].name == "Validation Review"
        assert dashboard.queues[1].badge_color == "badge-red"
        assert dashboard.queues[2].name == "Normalizations"
        assert dashboard.queues[2].badge_color == "badge-blue"
        assert dashboard.queues[3].name == "Households"
        assert dashboard.queues[3].badge_color == "badge-green"

    def test_get_dashboard_urls(self):
        """Test that dashboard contains correct navigation URLs."""
        dashboard = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert "/duplicates" in dashboard.queues[0].action_url
        assert "/validation" in dashboard.queues[1].action_url
        assert "/normalizations" in dashboard.queues[2].action_url
        assert "/households" in dashboard.queues[3].action_url
        assert dashboard.audit_log_url == "/imports/IMP-2025-0101-A/audit"
        assert dashboard.export_console_url == "/imports/IMP-2025-0101-A/exports"
        assert dashboard.back_to_imports_url == "/imports"

    def test_get_dashboard_data_not_mutated(self):
        """Test that fixture data is not mutated by multiple calls."""
        dashboard1 = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        dashboard2 = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert dashboard1.batch_id == dashboard2.batch_id
        assert dashboard1.filename == dashboard2.filename
        assert dashboard1.progress == dashboard2.progress


class TestDashboardService:
    """Test dashboard_service module."""

    def test_get_import_dashboard_returns_dict(self):
        """Test that get_import_dashboard returns a dictionary."""
        result = get_import_dashboard("IMP-2025-0101-A")
        assert isinstance(result, dict)

    def test_get_import_dashboard_has_required_keys(self):
        """Test that returned dict has batch and queue_status keys."""
        result = get_import_dashboard("IMP-2025-0101-A")
        assert "batch" in result
        assert "queue_status" in result

    def test_get_import_dashboard_batch_data(self):
        """Test that dashboard dict contains correct batch data."""
        result = get_import_dashboard("IMP-2025-0101-A")
        batch = result["batch"]
        assert batch["id"] == "IMP-2025-0101-A"
        assert batch["filename"] == "donors_q1_2025.csv"
        assert batch["progress"] == 42

    def test_get_import_dashboard_queue_status(self):
        """Test that dashboard dict contains correct queue status."""
        result = get_import_dashboard("IMP-2025-0101-A")
        queue_status = result["queue_status"]
        assert queue_status["duplicates_pending"] == 3
        assert queue_status["validation_issues"] == 8
        assert queue_status["normalizations_pending"] == 6
        assert queue_status["households_pending"] == 5

    def test_get_import_dashboard_template_ready(self):
        """Test that returned data is ready for Jinja2 template rendering."""
        result = get_import_dashboard("IMP-2025-0101-A")
        batch = result["batch"]
        queue_status = result["queue_status"]

        # Verify template can access all needed attributes
        assert batch["id"]
        assert batch["filename"]
        assert isinstance(batch["progress"], int)
        assert isinstance(queue_status["duplicates_pending"], int)
        assert isinstance(queue_status["validation_issues"], int)
        assert isinstance(queue_status["normalizations_pending"], int)
        assert isinstance(queue_status["households_pending"], int)
