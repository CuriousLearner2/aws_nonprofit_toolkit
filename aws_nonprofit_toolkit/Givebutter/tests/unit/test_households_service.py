"""
Unit tests for households service and view models.

Tests cover HouseholdRow, HouseholdPageViewModel, FixtureImportRepository.get_households(),
and households_service.get_households_review().
"""

import pytest
from scripts.householder.service_contracts import (
    HouseholdRow,
    HouseholdPageViewModel,
)
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder import households_service


class TestHouseholdRow:
    """Tests for HouseholdRow frozen dataclass."""

    def test_household_row_creation(self):
        """HouseholdRow can be created with all fields."""
        row = HouseholdRow(
            id="HH-001",
            suggested_name="Smith Family",
            address="123 Main St, Springfield, IL 62701",
            confidence="98%",
            proposed_members=("John Smith (TXN-001)", "Robert Smith (TXN-003)"),
            evidence=("Shared last name: Smith", "Same address"),
            conflicts=(),
            status="Pending",
        )
        assert row.id == "HH-001"
        assert row.suggested_name == "Smith Family"
        assert row.confidence == "98%"

    def test_household_row_is_frozen(self):
        """HouseholdRow frozen dataclass prevents modification."""
        row = HouseholdRow(
            id="HH-001",
            suggested_name="Smith Family",
            address="123 Main St",
            confidence="98%",
            proposed_members=(),
            evidence=(),
            conflicts=(),
        )
        with pytest.raises(Exception):
            row.id = "HH-002"

    def test_household_row_to_dict(self):
        """HouseholdRow.to_dict() converts to dictionary."""
        row = HouseholdRow(
            id="HH-001",
            suggested_name="Smith Family",
            address="123 Main St, Springfield, IL 62701",
            confidence="98%",
            proposed_members=("John Smith (TXN-001)", "Robert Smith (TXN-003)"),
            evidence=("Shared last name: Smith", "Same address"),
            conflicts=(),
            status="Pending",
        )
        result = row.to_dict()
        assert result["id"] == "HH-001"
        assert result["suggested_name"] == "Smith Family"
        assert result["confidence"] == "98%"
        assert result["proposed_members"] == ("John Smith (TXN-001)", "Robert Smith (TXN-003)")
        assert result["evidence"] == ("Shared last name: Smith", "Same address")

    def test_household_row_with_conflicts(self):
        """HouseholdRow.to_dict() includes conflicts when present."""
        row = HouseholdRow(
            id="HH-002",
            suggested_name="Williams Family",
            address="999 Cedar Ln, Springfield, IL 62706",
            confidence="95%",
            proposed_members=("Sarah Williams (P-008)", "Sara Williams (P-009)"),
            evidence=("Similar names", "Matching addresses"),
            conflicts=("Email addresses differ",),
            status="Pending",
        )
        result = row.to_dict()
        assert result["conflicts"] == ("Email addresses differ",)


class TestHouseholdPageViewModel:
    """Tests for HouseholdPageViewModel frozen dataclass."""

    def test_household_page_view_model_creation(self):
        """HouseholdPageViewModel can be created with all fields."""
        household = HouseholdRow(
            id="HH-001",
            suggested_name="Smith Family",
            address="123 Main St",
            confidence="98%",
            proposed_members=("John Smith (TXN-001)",),
            evidence=("Shared address",),
            conflicts=(),
        )
        view_model = HouseholdPageViewModel(
            batch_id="IMP-2025-0101-A",
            filename="donors_q1_2025.csv",
            progress=42,
            current_household=household,
            current_household_index=1,
            total_households=5,
        )
        assert view_model.batch_id == "IMP-2025-0101-A"
        assert view_model.current_household_index == 1
        assert view_model.total_households == 5

    def test_household_page_view_model_is_frozen(self):
        """HouseholdPageViewModel frozen dataclass prevents modification."""
        household = HouseholdRow(
            id="HH-001",
            suggested_name="Smith Family",
            address="123 Main St",
            confidence="98%",
            proposed_members=(),
            evidence=(),
            conflicts=(),
        )
        view_model = HouseholdPageViewModel(
            batch_id="IMP-2025-0101-A",
            filename="donors_q1_2025.csv",
            progress=42,
            current_household=household,
            current_household_index=1,
            total_households=5,
        )
        with pytest.raises(Exception):
            view_model.batch_id = "IMP-2025-0102-B"

    def test_household_page_view_model_to_template_dict(self):
        """HouseholdPageViewModel.to_template_dict() converts to template-ready format."""
        household = HouseholdRow(
            id="HH-001",
            suggested_name="Smith Family",
            address="123 Main St, Springfield, IL 62701",
            confidence="98%",
            proposed_members=("John Smith (TXN-001)", "Robert Smith (TXN-003)"),
            evidence=("Shared last name: Smith", "Same address"),
            conflicts=(),
            status="Pending",
        )
        view_model = HouseholdPageViewModel(
            batch_id="IMP-2025-0101-A",
            filename="donors_q1_2025.csv",
            progress=42,
            current_household=household,
            current_household_index=1,
            total_households=5,
        )
        result = view_model.to_template_dict()
        assert "batch" in result
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"
        assert result["batch"]["progress"] == 42
        assert "current_household" in result
        assert result["current_household"]["id"] == "HH-001"
        assert result["current_household_index"] == 1
        assert result["total_households"] == 5

    def test_household_page_view_model_navigation_state(self):
        """HouseholdPageViewModel correctly represents navigation state."""
        household = HouseholdRow(
            id="HH-002",
            suggested_name="Williams Family",
            address="999 Cedar Ln",
            confidence="95%",
            proposed_members=(),
            evidence=(),
            conflicts=(),
        )
        view_model = HouseholdPageViewModel(
            batch_id="IMP-2025-0101-A",
            filename="donors_q1_2025.csv",
            progress=50,
            current_household=household,
            current_household_index=2,
            total_households=5,
        )
        result = view_model.to_template_dict()
        assert result["current_household_index"] == 2
        assert result["total_households"] == 5


class TestFixtureImportRepositoryHouseholds:
    """Tests for FixtureImportRepository.get_households()."""

    def test_get_households_returns_view_model(self):
        """get_households() returns HouseholdPageViewModel."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        assert isinstance(result, HouseholdPageViewModel)

    def test_get_households_batch_metadata(self):
        """get_households() includes correct batch metadata."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        assert result.batch_id == "IMP-2025-0101-A"
        assert result.filename == "donors_q1_2025.csv"

    def test_get_households_current_household(self):
        """get_households() returns first household as current."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        assert result.current_household_index == 1
        assert isinstance(result.current_household, HouseholdRow)

    def test_get_households_total_count(self):
        """get_households() includes total household count."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        assert result.total_households > 0

    def test_get_households_first_household_data(self):
        """get_households() returns correct first household data."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        household = result.current_household
        assert household.id == "HH-001"
        assert household.suggested_name == "Smith Family"
        assert household.address == "123 Main St, Springfield, IL 62701"
        assert household.confidence == "98%"

    def test_get_households_household_members(self):
        """get_households() includes proposed members."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        household = result.current_household
        assert len(household.proposed_members) == 2
        assert "John Smith (TXN-001)" in household.proposed_members

    def test_get_households_household_evidence(self):
        """get_households() includes supporting evidence."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        household = result.current_household
        assert len(household.evidence) > 0
        assert any("Smith" in ev for ev in household.evidence)

    def test_get_households_household_conflicts(self):
        """get_households() includes conflicts when present."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        household = result.current_household
        # First household (HH-001) has no conflicts
        assert len(household.conflicts) == 0

    def test_get_households_fixture_not_mutated(self):
        """get_households() does not mutate fixture data."""
        result1 = FixtureImportRepository.get_households("IMP-2025-0101-A")
        result2 = FixtureImportRepository.get_households("IMP-2025-0101-A")
        # Verify both calls return identical data
        assert result1.current_household.id == result2.current_household.id
        assert result1.current_household.suggested_name == result2.current_household.suggested_name


class TestHouseholdsService:
    """Tests for households_service.get_households_review()."""

    def test_get_households_review_returns_dict(self):
        """get_households_review() returns dictionary."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        assert isinstance(result, dict)

    def test_get_households_review_has_batch_key(self):
        """get_households_review() includes 'batch' key."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        assert "batch" in result

    def test_get_households_review_has_current_household_key(self):
        """get_households_review() includes 'current_household' key."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        assert "current_household" in result

    def test_get_households_review_has_navigation_keys(self):
        """get_households_review() includes navigation keys."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        assert "current_household_index" in result
        assert "total_households" in result

    def test_get_households_review_batch_structure(self):
        """get_households_review() batch has required keys."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        batch = result["batch"]
        assert "id" in batch
        assert "filename" in batch
        assert "progress" in batch

    def test_get_households_review_current_household_structure(self):
        """get_households_review() current_household has required keys."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        household = result["current_household"]
        assert "id" in household
        assert "suggested_name" in household
        assert "address" in household
        assert "confidence" in household
        assert "proposed_members" in household
        assert "evidence" in household

    def test_get_households_review_navigation_values(self):
        """get_households_review() navigation values are correct."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        assert result["current_household_index"] == 1
        assert result["total_households"] > 0

    def test_get_households_review_template_ready(self):
        """get_households_review() returns template-ready dictionary."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        # Verify all top-level keys expected by template are present
        expected_keys = {"batch", "current_household", "current_household_index", "total_households"}
        actual_keys = set(result.keys())
        assert expected_keys.issubset(actual_keys)


class TestHouseholdsServiceProviderWiring:
    """Test that households_service uses repository provider (Phase 1B-Step 5N)."""

    def test_get_households_review_default_uses_fixture_repository(self):
        """Test that default config returns fixture-backed households."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"
        assert result["batch"]["progress"] == 42

    def test_get_households_review_with_none_config_uses_fixture(self):
        """Test that None config explicitly uses fixture repository."""
        result = households_service.get_households_review("IMP-2025-0101-A", config=None)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_households_review_with_empty_config_uses_fixture(self):
        """Test that empty dict config uses fixture repository."""
        result = households_service.get_households_review("IMP-2025-0101-A", config={})
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_households_review_with_explicit_fixture_config(self):
        """Test that explicit fixture config returns fixture-backed households."""
        config = {"HOUSEHOLDER_REPOSITORY": "fixture"}
        result = households_service.get_households_review("IMP-2025-0101-A", config=config)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"

    def test_get_households_review_database_mode_without_url_raises_error(self):
        """Test that database mode without GIVEBUTTER_DATABASE_URL raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "database"}
        with pytest.raises(ValueError) as exc_info:
            households_service.get_households_review("IMP-2025-0101-A", config=config)
        assert "Database mode requested but no database URL configured" in str(exc_info.value)

    def test_get_households_review_invalid_repository_mode_raises_error(self):
        """Test that invalid repository mode raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "invalid_mode"}
        with pytest.raises(ValueError) as exc_info:
            households_service.get_households_review("IMP-2025-0101-A", config=config)
        assert "Invalid HOUSEHOLDER_REPOSITORY mode" in str(exc_info.value)

    def test_get_households_review_template_dict_shape_unchanged(self):
        """Test that template dict shape is identical after provider wiring."""
        # Get households with default (fixture)
        fixture_result = households_service.get_households_review("IMP-2025-0101-A")
        # Get households with explicit fixture config
        config_result = households_service.get_households_review("IMP-2025-0101-A", config={"HOUSEHOLDER_REPOSITORY": "fixture"})

        # Both should have same shape and data
        assert fixture_result["batch"]["id"] == config_result["batch"]["id"]
        assert fixture_result["batch"]["filename"] == config_result["batch"]["filename"]
        assert fixture_result["batch"]["progress"] == config_result["batch"]["progress"]
        assert fixture_result["current_household_index"] == config_result["current_household_index"]
        assert fixture_result["total_households"] == config_result["total_households"]

    def test_get_households_review_returns_dicts_not_orm_objects(self):
        """Test that result contains dicts, not ORM objects."""
        result = households_service.get_households_review("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert isinstance(result["batch"], dict)
        assert isinstance(result["current_household"], dict)
        # Verify no ORM objects
        assert not hasattr(result, '__table__')
        assert not hasattr(result["batch"], '__table__')
