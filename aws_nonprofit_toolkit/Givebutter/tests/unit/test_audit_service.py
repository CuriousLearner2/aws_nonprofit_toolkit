"""
Unit tests for audit log service.

Tests verify that the service boundary correctly transforms fixture data
into view models and dictionaries suitable for template rendering.
"""

import pytest
from scripts.householder.service_contracts import (
    AuditLogEntry,
    AuditPageViewModel,
)
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.audit_service import get_audit_log


class TestAuditLogEntry:
    """Test AuditLogEntry view model."""

    def test_audit_log_entry_creation(self):
        """Test that AuditLogEntry can be created with required fields."""
        entry = AuditLogEntry(
            timestamp="2026-06-11 10:30:00",
            reviewer="Sarah Lee",
            action="marked as Same Person",
            details="Email variation consistent with household pattern",
        )
        assert entry.timestamp == "2026-06-11 10:30:00"
        assert entry.reviewer == "Sarah Lee"
        assert entry.action == "marked as Same Person"

    def test_audit_log_entry_frozen(self):
        """Test that AuditLogEntry is immutable."""
        entry = AuditLogEntry(
            timestamp="2026-06-11 10:30:00",
            reviewer="Sarah Lee",
            action="marked as Same Person",
            details="Email variation consistent with household pattern",
        )
        with pytest.raises(AttributeError):
            entry.reviewer = "Changed"

    def test_audit_log_entry_to_dict(self):
        """Test conversion to dictionary."""
        entry = AuditLogEntry(
            timestamp="2026-06-11 10:30:00",
            reviewer="Sarah Lee",
            action="marked as Same Person",
            details="Email variation consistent with household pattern",
        )
        entry_dict = entry.to_dict()
        assert isinstance(entry_dict, dict)
        assert entry_dict["timestamp"] == "2026-06-11 10:30:00"
        assert entry_dict["reviewer"] == "Sarah Lee"


class TestAuditPageViewModel:
    """Test AuditPageViewModel."""

    def test_audit_page_view_model_creation(self):
        """Test that AuditPageViewModel can be created."""
        entry1 = AuditLogEntry(
            timestamp="2026-06-11 10:30:00",
            reviewer="Sarah Lee",
            action="marked as Same Person",
            details="Email variation consistent with household pattern",
        )
        entry2 = AuditLogEntry(
            timestamp="2026-06-11 10:15:00",
            reviewer="James Martinez",
            action="confirmed Household #HH-001",
            details="Smith family confirmed via manual lookup",
        )
        vm = AuditPageViewModel(
            batch_id="IMP-TEST-001",
            filename="test.csv",
            progress=50,
            audit_entries=(entry1, entry2),
        )
        assert vm.batch_id == "IMP-TEST-001"
        assert vm.progress == 50
        assert len(vm.audit_entries) == 2

    def test_audit_page_view_model_to_template_dict(self):
        """Test conversion to template-compatible dict."""
        entry = AuditLogEntry(
            timestamp="2026-06-11 10:30:00",
            reviewer="Sarah Lee",
            action="marked as Same Person",
            details="Email variation consistent with household pattern",
        )
        vm = AuditPageViewModel(
            batch_id="IMP-TEST-002",
            filename="test2.csv",
            progress=75,
            audit_entries=(entry,),
        )
        template_dict = vm.to_template_dict()
        assert isinstance(template_dict, dict)
        assert template_dict["batch"]["id"] == "IMP-TEST-002"
        assert template_dict["batch"]["filename"] == "test2.csv"
        assert template_dict["batch"]["progress"] == 75
        assert len(template_dict["audit_log"]) == 1
        assert template_dict["audit_log"][0]["reviewer"] == "Sarah Lee"

    def test_audit_page_view_model_frozen(self):
        """Test that AuditPageViewModel is immutable."""
        entry = AuditLogEntry("2026-06-11 10:30:00", "Sarah Lee", "action", "details")
        vm = AuditPageViewModel("IMP-TEST-003", "test.csv", 25, (entry,))
        with pytest.raises(AttributeError):
            vm.batch_id = "CHANGED"


class TestFixtureImportRepository:
    """Test FixtureImportRepository audit method."""

    def test_get_audit_returns_view_model(self):
        """Test that get_audit returns AuditPageViewModel."""
        audit = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        assert isinstance(audit, AuditPageViewModel)

    def test_get_audit_batch_data(self):
        """Test that audit page contains correct batch data."""
        audit = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        assert audit.batch_id == "IMP-2025-0101-A"
        assert audit.filename == "donors_q1_2025.csv"
        assert audit.progress == 42

    def test_get_audit_has_entries(self):
        """Test that audit page contains audit entries."""
        audit = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        assert len(audit.audit_entries) > 0

    def test_get_audit_entry_fields(self):
        """Test that audit entries have required fields."""
        audit = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        first_entry = audit.audit_entries[0]
        assert hasattr(first_entry, 'timestamp')
        assert hasattr(first_entry, 'reviewer')
        assert hasattr(first_entry, 'action')
        assert hasattr(first_entry, 'details')

    def test_get_audit_first_entry(self):
        """Test that first audit entry has expected data."""
        audit = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        first_entry = audit.audit_entries[0]
        assert first_entry.reviewer == "Sarah Lee"
        assert "Same Person" in first_entry.action or "marked" in first_entry.action

    def test_get_audit_data_not_mutated(self):
        """Test that fixture data is not mutated by multiple calls."""
        audit1 = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        audit2 = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        assert audit1.batch_id == audit2.batch_id
        assert len(audit1.audit_entries) == len(audit2.audit_entries)


class TestAuditService:
    """Test audit_service module."""

    def test_get_audit_log_returns_dict(self):
        """Test that get_audit_log returns a dictionary."""
        result = get_audit_log("IMP-2025-0101-A")
        assert isinstance(result, dict)

    def test_get_audit_log_has_required_keys(self):
        """Test that returned dict has all required keys."""
        result = get_audit_log("IMP-2025-0101-A")
        assert "batch" in result
        assert "audit_log" in result

    def test_get_audit_log_batch_data(self):
        """Test that audit dict contains correct batch data."""
        result = get_audit_log("IMP-2025-0101-A")
        batch = result["batch"]
        assert batch["id"] == "IMP-2025-0101-A"
        assert batch["filename"] == "donors_q1_2025.csv"
        assert batch["progress"] == 42

    def test_get_audit_log_entries(self):
        """Test that audit dict contains audit entries."""
        result = get_audit_log("IMP-2025-0101-A")
        audit_log = result["audit_log"]
        assert isinstance(audit_log, list)
        assert len(audit_log) > 0

    def test_get_audit_log_entry_structure(self):
        """Test that audit entries have expected structure."""
        result = get_audit_log("IMP-2025-0101-A")
        audit_log = result["audit_log"]
        first_entry = audit_log[0]
        assert "timestamp" in first_entry
        assert "reviewer" in first_entry
        assert "action" in first_entry
        assert "details" in first_entry

    def test_get_audit_log_template_ready(self):
        """Test that returned data is ready for Jinja2 template rendering."""
        result = get_audit_log("IMP-2025-0101-A")
        batch = result["batch"]
        audit_log = result["audit_log"]

        # Verify template can access all needed attributes
        assert batch["id"]
        assert batch["filename"]
        assert isinstance(batch["progress"], int)
        assert len(audit_log) > 0
        first_entry = audit_log[0]
        assert first_entry["timestamp"]
        assert first_entry["reviewer"]
        assert first_entry["action"]
        assert first_entry["details"]


class TestAuditServiceProviderWiring:
    """Test that audit_service uses repository provider (Phase 1B-Step 5P)."""

    def test_get_audit_log_default_uses_fixture_repository(self):
        """Test that default config returns fixture-backed audit."""
        result = get_audit_log("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"
        assert result["batch"]["progress"] == 42

    def test_get_audit_log_with_none_config_uses_fixture(self):
        """Test that None config explicitly uses fixture repository."""
        result = get_audit_log("IMP-2025-0101-A", config=None)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_audit_log_with_empty_config_uses_fixture(self):
        """Test that empty dict config uses fixture repository."""
        result = get_audit_log("IMP-2025-0101-A", config={})
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_audit_log_with_explicit_fixture_config(self):
        """Test that explicit fixture config returns fixture-backed audit."""
        config = {"HOUSEHOLDER_REPOSITORY": "fixture"}
        result = get_audit_log("IMP-2025-0101-A", config=config)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"

    def test_get_audit_log_database_mode_without_url_raises_error(self):
        """Test that database mode without GIVEBUTTER_DATABASE_URL raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "database"}
        with pytest.raises(ValueError) as exc_info:
            get_audit_log("IMP-2025-0101-A", config=config)
        assert "Database mode requested but no database URL configured" in str(exc_info.value)

    def test_get_audit_log_invalid_repository_mode_raises_error(self):
        """Test that invalid repository mode raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "invalid_mode"}
        with pytest.raises(ValueError) as exc_info:
            get_audit_log("IMP-2025-0101-A", config=config)
        assert "Invalid HOUSEHOLDER_REPOSITORY mode" in str(exc_info.value)

    def test_get_audit_log_template_dict_shape_unchanged(self):
        """Test that template dict shape is identical after provider wiring."""
        # Get audit with default (fixture)
        fixture_result = get_audit_log("IMP-2025-0101-A")
        # Get audit with explicit fixture config
        config_result = get_audit_log("IMP-2025-0101-A", config={"HOUSEHOLDER_REPOSITORY": "fixture"})

        # Both should have same shape and data
        assert fixture_result["batch"]["id"] == config_result["batch"]["id"]
        assert fixture_result["batch"]["filename"] == config_result["batch"]["filename"]
        assert fixture_result["batch"]["progress"] == config_result["batch"]["progress"]
        assert len(fixture_result["audit_log"]) == len(config_result["audit_log"])

    def test_get_audit_log_returns_dicts_not_orm_objects(self):
        """Test that result contains dicts, not ORM objects."""
        result = get_audit_log("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert isinstance(result["batch"], dict)
        assert isinstance(result["audit_log"], list)
        if len(result["audit_log"]) > 0:
            assert isinstance(result["audit_log"][0], dict)
        # Verify no ORM objects
        assert not hasattr(result, '__table__')
        assert not hasattr(result["batch"], '__table__')
