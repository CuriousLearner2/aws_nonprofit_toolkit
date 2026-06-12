"""
Unit tests for DonorTrust v1 import service.

Tests verify that the service boundary correctly transforms fixture data
into view models suitable for template rendering.

Phase 1B-Step 5J: Tests for repository provider wiring.
"""

import pytest
from scripts.householder.service_contracts import ImportSummary
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.database_repository import DatabaseImportRepository
from scripts.householder.import_service import get_imports


class TestImportSummary:
    """Test ImportSummary view model."""

    def test_import_summary_creation(self):
        """Test that ImportSummary can be created with required fields."""
        summary = ImportSummary(
            id="TEST-001",
            filename="test.csv",
            record_count=100,
            status="In Review",
            progress=50,
            uploaded_timestamp="2d ago",
        )
        assert summary.id == "TEST-001"
        assert summary.filename == "test.csv"
        assert summary.record_count == 100
        assert summary.status == "In Review"
        assert summary.progress == 50
        assert summary.uploaded_timestamp == "2d ago"

    def test_import_summary_to_template_dict(self):
        """Test conversion to template-compatible dict."""
        summary = ImportSummary(
            id="TEST-002",
            filename="test2.csv",
            record_count=200,
            status="Complete",
            progress=100,
            uploaded_timestamp="5d ago",
        )
        template_dict = summary.to_template_dict()
        assert isinstance(template_dict, dict)
        assert template_dict["id"] == "TEST-002"
        assert template_dict["filename"] == "test2.csv"
        assert template_dict["record_count"] == 200
        assert template_dict["status"] == "Complete"
        assert template_dict["progress"] == 100
        assert template_dict["uploaded_timestamp"] == "5d ago"

    def test_import_summary_frozen(self):
        """Test that ImportSummary is immutable."""
        summary = ImportSummary(
            id="TEST-003",
            filename="test3.csv",
            record_count=50,
            status="Pending",
            progress=0,
        )
        with pytest.raises(AttributeError):
            summary.id = "CHANGED"


class TestFixtureImportRepository:
    """Test FixtureImportRepository."""

    def test_list_imports_returns_list(self):
        """Test that list_imports returns a non-empty list."""
        imports = FixtureImportRepository.list_imports()
        assert isinstance(imports, list)
        assert len(imports) > 0

    def test_list_imports_returns_import_summary_objects(self):
        """Test that each item is an ImportSummary."""
        imports = FixtureImportRepository.list_imports()
        for imp in imports:
            assert isinstance(imp, ImportSummary)

    def test_list_imports_contains_expected_fixture_data(self):
        """Test that fixture data is correctly loaded."""
        imports = FixtureImportRepository.list_imports()
        ids = [imp.id for imp in imports]
        assert "IMP-2025-0101-A" in ids
        # Find the main batch
        main_batch = next((imp for imp in imports if imp.id == "IMP-2025-0101-A"), None)
        assert main_batch is not None
        assert main_batch.filename == "donors_q1_2025.csv"
        assert main_batch.record_count == 50
        assert main_batch.progress == 42

    def test_list_imports_formats_timestamps(self):
        """Test that uploaded_at is converted to relative time strings."""
        imports = FixtureImportRepository.list_imports()
        for imp in imports:
            if imp.uploaded_timestamp:
                # Should be relative time like "2d ago", "5h ago", etc.
                assert isinstance(imp.uploaded_timestamp, str)
                assert len(imp.uploaded_timestamp) > 0

    def test_list_imports_data_not_mutated(self):
        """Test that original fixture data is not modified."""
        # Call list_imports twice
        imports1 = FixtureImportRepository.list_imports()
        imports2 = FixtureImportRepository.list_imports()
        # Both should return the same data
        assert len(imports1) == len(imports2)
        for imp1, imp2 in zip(imports1, imports2):
            assert imp1.id == imp2.id
            assert imp1.filename == imp2.filename


class TestImportService:
    """Test import_service module."""

    def test_get_imports_returns_list(self):
        """Test that get_imports returns a list."""
        result = get_imports()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_imports_returns_dicts(self):
        """Test that get_imports returns dicts, not ORM objects."""
        result = get_imports()
        for item in result:
            assert isinstance(item, dict)

    def test_get_imports_contains_required_fields(self):
        """Test that each dict has all required fields for template."""
        result = get_imports()
        required_fields = {"id", "filename", "record_count", "status", "progress", "uploaded_timestamp"}
        for item in result:
            assert all(field in item for field in required_fields)

    def test_get_imports_main_batch_data(self):
        """Test that main fixture batch is correctly provided."""
        result = get_imports()
        main = next((item for item in result if item["id"] == "IMP-2025-0101-A"), None)
        assert main is not None
        assert main["filename"] == "donors_q1_2025.csv"
        assert main["record_count"] == 50
        assert main["status"] == "In Review"
        assert main["progress"] == 42

    def test_get_imports_template_ready(self):
        """Test that returned data is ready for Jinja2 template rendering."""
        result = get_imports()
        for item in result:
            # Verify template can access all needed attributes
            assert item["id"]
            assert item["filename"]
            assert isinstance(item["record_count"], int)
            assert item["status"]
            assert isinstance(item["progress"], int)
            # uploaded_timestamp can be None or string
            assert item["uploaded_timestamp"] is None or isinstance(item["uploaded_timestamp"], str)


class TestImportServiceProviderWiring:
    """Test that import_service uses repository provider (Phase 1B-Step 5J)."""

    def test_get_imports_default_uses_fixture_repository(self):
        """Test that default config returns fixture-backed imports."""
        result = get_imports()
        # Should return fixture data by default
        assert isinstance(result, list)
        assert len(result) > 0
        main = next((item for item in result if item["id"] == "IMP-2025-0101-A"), None)
        assert main is not None
        assert main["filename"] == "donors_q1_2025.csv"

    def test_get_imports_with_none_config_uses_fixture(self):
        """Test that None config explicitly uses fixture repository."""
        result = get_imports(config=None)
        assert isinstance(result, list)
        assert len(result) > 0
        main = next((item for item in result if item["id"] == "IMP-2025-0101-A"), None)
        assert main is not None

    def test_get_imports_with_empty_config_uses_fixture(self):
        """Test that empty dict config uses fixture repository."""
        result = get_imports(config={})
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_imports_with_explicit_fixture_config(self):
        """Test that explicit fixture config returns fixture-backed imports."""
        config = {"HOUSEHOLDER_REPOSITORY": "fixture"}
        result = get_imports(config=config)
        assert isinstance(result, list)
        assert len(result) > 0
        main = next((item for item in result if item["id"] == "IMP-2025-0101-A"), None)
        assert main is not None
        assert main["filename"] == "donors_q1_2025.csv"

    def test_get_imports_database_mode_without_url_raises_error(self):
        """Test that database mode without GIVEBUTTER_DATABASE_URL raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "database"}
        with pytest.raises(ValueError) as exc_info:
            get_imports(config=config)
        assert "Database mode requested but no database URL configured" in str(exc_info.value)

    def test_get_imports_invalid_repository_mode_raises_error(self):
        """Test that invalid repository mode raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "invalid_mode"}
        with pytest.raises(ValueError) as exc_info:
            get_imports(config=config)
        assert "Invalid HOUSEHOLDER_REPOSITORY mode" in str(exc_info.value)

    def test_get_imports_template_dict_shape_unchanged(self):
        """Test that template dict shape is identical after provider wiring."""
        # Get imports with default (fixture)
        fixture_result = get_imports()
        # Get imports with explicit fixture config
        config_result = get_imports(config={"HOUSEHOLDER_REPOSITORY": "fixture"})

        # Both should have same shape and data
        assert len(fixture_result) == len(config_result)
        for f_item, c_item in zip(fixture_result, config_result):
            assert f_item["id"] == c_item["id"]
            assert f_item["filename"] == c_item["filename"]
            assert f_item["record_count"] == c_item["record_count"]
            assert f_item["status"] == c_item["status"]
            assert f_item["progress"] == c_item["progress"]

    def test_get_imports_returns_dicts_not_orm_objects(self):
        """Test that result contains dicts, not ORM objects."""
        result = get_imports()
        for item in result:
            assert isinstance(item, dict)
            assert not hasattr(item, '__table__')  # Not an ORM object
