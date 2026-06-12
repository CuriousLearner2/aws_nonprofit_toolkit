"""
Unit tests for duplicates service.

Tests verify that the service boundary correctly transforms fixture data
into view models and dictionaries suitable for template rendering.
"""

import pytest
from scripts.householder.service_contracts import (
    DuplicateCandidate,
    DuplicateContact,
    DuplicatePageViewModel,
)
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.duplicates_service import get_duplicates_review


class TestDuplicateContact:
    """Test DuplicateContact view model."""

    def test_duplicate_contact_creation(self):
        """Test that DuplicateContact can be created with required fields."""
        contact = DuplicateContact(
            id="TXN-001",
            name="John Smith",
            email="john@example.com",
            phone="(555) 123-4567",
            address="123 Main St, Springfield, IL 62701",
        )
        assert contact.id == "TXN-001"
        assert contact.name == "John Smith"
        assert contact.email == "john@example.com"

    def test_duplicate_contact_frozen(self):
        """Test that DuplicateContact is immutable."""
        contact = DuplicateContact(
            id="TXN-001",
            name="John Smith",
            email="john@example.com",
            phone="(555) 123-4567",
            address="123 Main St",
        )
        with pytest.raises(AttributeError):
            contact.name = "Changed"

    def test_duplicate_contact_to_dict(self):
        """Test conversion to dictionary."""
        contact = DuplicateContact(
            id="TXN-001",
            name="John Smith",
            email="john@example.com",
            phone="(555) 123-4567",
            address="123 Main St, Springfield, IL 62701",
        )
        contact_dict = contact.to_dict()
        assert isinstance(contact_dict, dict)
        assert contact_dict["id"] == "TXN-001"
        assert contact_dict["name"] == "John Smith"
        assert contact_dict["email"] == "john@example.com"


class TestDuplicateCandidate:
    """Test DuplicateCandidate view model."""

    def test_duplicate_candidate_creation(self):
        """Test that DuplicateCandidate can be created with required fields."""
        contact_a = DuplicateContact(
            id="TXN-001",
            name="John Smith",
            email="john@example.com",
            phone="(555) 123-4567",
            address="123 Main St",
        )
        contact_b = DuplicateContact(
            id="TXN-002",
            name="Jon Smith",
            email="jon.smith@email.com",
            phone="(555) 123-4567",
            address="123 Main St",
        )
        candidate = DuplicateCandidate(
            id="DUP-001",
            contact_a=contact_a,
            contact_b=contact_b,
            supporting_evidence=("Same address", "Similar names"),
            conflicting_evidence=(),
        )
        assert candidate.id == "DUP-001"
        assert candidate.contact_a.name == "John Smith"
        assert candidate.contact_b.name == "Jon Smith"

    def test_duplicate_candidate_frozen(self):
        """Test that DuplicateCandidate is immutable."""
        contact_a = DuplicateContact("TXN-001", "John Smith", "", "", "")
        contact_b = DuplicateContact("TXN-002", "Jon Smith", "", "", "")
        candidate = DuplicateCandidate(
            id="DUP-001",
            contact_a=contact_a,
            contact_b=contact_b,
            supporting_evidence=(),
            conflicting_evidence=(),
        )
        with pytest.raises(AttributeError):
            candidate.id = "DUP-002"

    def test_duplicate_candidate_to_dict(self):
        """Test conversion to dictionary."""
        contact_a = DuplicateContact("TXN-001", "John Smith", "john@example.com", "(555) 123-4567", "123 Main St")
        contact_b = DuplicateContact("TXN-002", "Jon Smith", "jon@example.com", "(555) 123-4567", "123 Main St")
        candidate = DuplicateCandidate(
            id="DUP-001",
            contact_a=contact_a,
            contact_b=contact_b,
            supporting_evidence=("Same address",),
            conflicting_evidence=(),
        )
        candidate_dict = candidate.to_dict()
        assert isinstance(candidate_dict, dict)
        assert candidate_dict["id"] == "DUP-001"
        assert candidate_dict["contact_a"]["name"] == "John Smith"
        assert candidate_dict["contact_b"]["name"] == "Jon Smith"


class TestDuplicatePageViewModel:
    """Test DuplicatePageViewModel."""

    def test_duplicate_page_view_model_creation(self):
        """Test that DuplicatePageViewModel can be created."""
        contact_a = DuplicateContact("TXN-001", "John Smith", "", "", "")
        contact_b = DuplicateContact("TXN-002", "Jon Smith", "", "", "")
        candidate = DuplicateCandidate(
            id="DUP-001",
            contact_a=contact_a,
            contact_b=contact_b,
            supporting_evidence=(),
            conflicting_evidence=(),
        )
        vm = DuplicatePageViewModel(
            batch_id="IMP-TEST-001",
            filename="test.csv",
            progress=50,
            current_candidate=candidate,
            current_candidate_index=1,
            total_candidates=3,
        )
        assert vm.batch_id == "IMP-TEST-001"
        assert vm.progress == 50
        assert vm.current_candidate_index == 1

    def test_duplicate_page_view_model_to_template_dict(self):
        """Test conversion to template-compatible dict."""
        contact_a = DuplicateContact("TXN-001", "John Smith", "john@example.com", "(555) 123-4567", "123 Main St")
        contact_b = DuplicateContact("TXN-002", "Jon Smith", "jon@example.com", "(555) 123-4567", "123 Main St")
        candidate = DuplicateCandidate(
            id="DUP-001",
            contact_a=contact_a,
            contact_b=contact_b,
            supporting_evidence=("Same address", "Similar names"),
            conflicting_evidence=(),
        )
        vm = DuplicatePageViewModel(
            batch_id="IMP-TEST-001",
            filename="test.csv",
            progress=50,
            current_candidate=candidate,
            current_candidate_index=1,
            total_candidates=3,
        )
        template_dict = vm.to_template_dict()
        assert isinstance(template_dict, dict)
        assert template_dict["batch"]["id"] == "IMP-TEST-001"
        assert template_dict["batch"]["filename"] == "test.csv"
        assert template_dict["candidate"]["id"] == "DUP-001"

    def test_duplicate_page_view_model_frozen(self):
        """Test that DuplicatePageViewModel is immutable."""
        contact_a = DuplicateContact("TXN-001", "John Smith", "", "", "")
        contact_b = DuplicateContact("TXN-002", "Jon Smith", "", "", "")
        candidate = DuplicateCandidate(
            id="DUP-001",
            contact_a=contact_a,
            contact_b=contact_b,
            supporting_evidence=(),
            conflicting_evidence=(),
        )
        vm = DuplicatePageViewModel(
            batch_id="IMP-TEST-001",
            filename="test.csv",
            progress=50,
            current_candidate=candidate,
            current_candidate_index=1,
            total_candidates=3,
        )
        with pytest.raises(AttributeError):
            vm.batch_id = "CHANGED"


class TestFixtureImportRepositoryDuplicates:
    """Test FixtureImportRepository duplicates method."""

    def test_get_duplicates_returns_view_model(self):
        """Test that get_duplicates returns DuplicatePageViewModel."""
        duplicates = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        assert isinstance(duplicates, DuplicatePageViewModel)

    def test_get_duplicates_batch_data(self):
        """Test that duplicates page contains correct batch data."""
        duplicates = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        assert duplicates.batch_id == "IMP-2025-0101-A"
        assert duplicates.filename == "donors_q1_2025.csv"
        assert duplicates.progress == 42

    def test_get_duplicates_current_candidate(self):
        """Test that duplicates page has a current candidate."""
        duplicates = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        assert duplicates.current_candidate_index >= 1
        assert isinstance(duplicates.current_candidate, DuplicateCandidate)

    def test_get_duplicates_total_candidates(self):
        """Test that duplicates page contains correct total count."""
        duplicates = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        assert duplicates.total_candidates > 0

    def test_get_duplicates_candidate_structure(self):
        """Test that duplicate candidate has required structure."""
        duplicates = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        candidate = duplicates.current_candidate
        assert hasattr(candidate, "id")
        assert hasattr(candidate, "contact_a")
        assert hasattr(candidate, "contact_b")

    def test_get_duplicates_data_not_mutated(self):
        """Test that fixture data is not mutated by multiple calls."""
        duplicates1 = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        duplicates2 = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        assert duplicates1.batch_id == duplicates2.batch_id
        assert duplicates1.current_candidate.id == duplicates2.current_candidate.id


class TestDuplicatesService:
    """Test duplicates_service module."""

    def test_get_duplicates_review_returns_dict(self):
        """Test that get_duplicates_review returns a dictionary."""
        result = get_duplicates_review("IMP-2025-0101-A")
        assert isinstance(result, dict)

    def test_get_duplicates_review_has_required_keys(self):
        """Test that returned dict has required keys."""
        result = get_duplicates_review("IMP-2025-0101-A")
        assert "batch" in result
        assert "candidate" in result

    def test_get_duplicates_review_batch_data(self):
        """Test that duplicates dict contains correct batch data."""
        result = get_duplicates_review("IMP-2025-0101-A")
        batch = result["batch"]
        assert batch["id"] == "IMP-2025-0101-A"
        assert batch["filename"] == "donors_q1_2025.csv"
        assert batch["progress"] == 42

    def test_get_duplicates_review_candidate_structure(self):
        """Test that duplicates dict contains correct candidate structure."""
        result = get_duplicates_review("IMP-2025-0101-A")
        candidate = result["candidate"]
        assert isinstance(candidate, dict)
        assert "id" in candidate
        assert "contact_a" in candidate
        assert "contact_b" in candidate

    def test_get_duplicates_review_template_ready(self):
        """Test that returned data is ready for Jinja2 template rendering."""
        result = get_duplicates_review("IMP-2025-0101-A")
        batch = result["batch"]
        candidate = result["candidate"]

        # Verify template can access all needed attributes
        assert batch["id"]
        assert batch["filename"]
        assert isinstance(batch["progress"], int)
        assert candidate["id"]
        assert candidate["contact_a"]["name"]
        assert candidate["contact_b"]["name"]


class TestDuplicatesServiceProviderWiring:
    """Test that duplicates_service uses repository provider (Phase 1B-Step 5O)."""

    def test_get_duplicates_review_default_uses_fixture_repository(self):
        """Test that default config returns fixture-backed duplicates."""
        result = get_duplicates_review("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"
        assert result["batch"]["progress"] == 42

    def test_get_duplicates_review_with_none_config_uses_fixture(self):
        """Test that None config explicitly uses fixture repository."""
        result = get_duplicates_review("IMP-2025-0101-A", config=None)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_duplicates_review_with_empty_config_uses_fixture(self):
        """Test that empty dict config uses fixture repository."""
        result = get_duplicates_review("IMP-2025-0101-A", config={})
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"

    def test_get_duplicates_review_with_explicit_fixture_config(self):
        """Test that explicit fixture config returns fixture-backed duplicates."""
        config = {"HOUSEHOLDER_REPOSITORY": "fixture"}
        result = get_duplicates_review("IMP-2025-0101-A", config=config)
        assert isinstance(result, dict)
        assert result["batch"]["id"] == "IMP-2025-0101-A"
        assert result["batch"]["filename"] == "donors_q1_2025.csv"

    def test_get_duplicates_review_database_mode_without_url_raises_error(self):
        """Test that database mode without GIVEBUTTER_DATABASE_URL raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "database"}
        with pytest.raises(ValueError) as exc_info:
            get_duplicates_review("IMP-2025-0101-A", config=config)
        assert "Database mode requested but no database URL configured" in str(exc_info.value)

    def test_get_duplicates_review_invalid_repository_mode_raises_error(self):
        """Test that invalid repository mode raises ValueError."""
        config = {"HOUSEHOLDER_REPOSITORY": "invalid_mode"}
        with pytest.raises(ValueError) as exc_info:
            get_duplicates_review("IMP-2025-0101-A", config=config)
        assert "Invalid HOUSEHOLDER_REPOSITORY mode" in str(exc_info.value)

    def test_get_duplicates_review_template_dict_shape_unchanged(self):
        """Test that template dict shape is identical after provider wiring."""
        # Get duplicates with default (fixture)
        fixture_result = get_duplicates_review("IMP-2025-0101-A")
        # Get duplicates with explicit fixture config
        config_result = get_duplicates_review("IMP-2025-0101-A", config={"HOUSEHOLDER_REPOSITORY": "fixture"})

        # Both should have same shape and data
        assert fixture_result["batch"]["id"] == config_result["batch"]["id"]
        assert fixture_result["batch"]["filename"] == config_result["batch"]["filename"]
        assert fixture_result["batch"]["progress"] == config_result["batch"]["progress"]
        assert fixture_result["candidate"]["id"] == config_result["candidate"]["id"]

    def test_get_duplicates_review_returns_dicts_not_orm_objects(self):
        """Test that result contains dicts, not ORM objects."""
        result = get_duplicates_review("IMP-2025-0101-A")
        assert isinstance(result, dict)
        assert isinstance(result["batch"], dict)
        assert isinstance(result["candidate"], dict)
        # Verify no ORM objects
        assert not hasattr(result, '__table__')
        assert not hasattr(result["batch"], '__table__')
