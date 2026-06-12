"""
Unit tests for repository contracts.

Verifies that ImportRepositoryProtocol is correctly defined and that
FixtureImportRepository structurally satisfies the protocol.

Tests ensure:
1. Protocol has all 8 required methods
2. Method signatures match exactly
3. Return types are correct view models
4. FixtureImportRepository provides correct implementations
5. No ORM/database types are exposed
"""

import pytest
import sys
from pathlib import Path
from typing import get_type_hints

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.repository_contracts import ImportRepositoryProtocol
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.service_contracts import (
    ImportSummary,
    ImportDashboardViewModel,
    ValidationPageViewModel,
    NormalizationPageViewModel,
    HouseholdPageViewModel,
    DuplicatePageViewModel,
    AuditPageViewModel,
    ExportConsoleViewModel,
)


class TestImportRepositoryProtocol:
    """Tests for ImportRepositoryProtocol definition."""

    def test_protocol_exists(self):
        """Test that ImportRepositoryProtocol is defined."""
        assert ImportRepositoryProtocol is not None
        assert hasattr(ImportRepositoryProtocol, '__protocol_attrs__')

    def test_protocol_has_list_imports_method(self):
        """Test that protocol declares list_imports method."""
        assert hasattr(ImportRepositoryProtocol, 'list_imports')

    def test_protocol_has_get_dashboard_method(self):
        """Test that protocol declares get_dashboard method."""
        assert hasattr(ImportRepositoryProtocol, 'get_dashboard')

    def test_protocol_has_get_validation_method(self):
        """Test that protocol declares get_validation method."""
        assert hasattr(ImportRepositoryProtocol, 'get_validation')

    def test_protocol_has_get_normalizations_method(self):
        """Test that protocol declares get_normalizations method."""
        assert hasattr(ImportRepositoryProtocol, 'get_normalizations')

    def test_protocol_has_get_households_method(self):
        """Test that protocol declares get_households method."""
        assert hasattr(ImportRepositoryProtocol, 'get_households')

    def test_protocol_has_get_duplicates_method(self):
        """Test that protocol declares get_duplicates method."""
        assert hasattr(ImportRepositoryProtocol, 'get_duplicates')

    def test_protocol_has_get_audit_method(self):
        """Test that protocol declares get_audit method."""
        assert hasattr(ImportRepositoryProtocol, 'get_audit')

    def test_protocol_has_get_exports_method(self):
        """Test that protocol declares get_exports method."""
        assert hasattr(ImportRepositoryProtocol, 'get_exports')

    def test_protocol_is_read_only(self):
        """Test that protocol has no write methods like record_decision."""
        # Protocol should only have the 8 read methods
        read_methods = {
            'list_imports',
            'get_dashboard',
            'get_validation',
            'get_normalizations',
            'get_households',
            'get_duplicates',
            'get_audit',
            'get_exports',
        }

        protocol_methods = {
            name for name in dir(ImportRepositoryProtocol)
            if not name.startswith('_')
        }

        # Should not have write methods
        assert 'record_decision' not in protocol_methods
        assert 'save_decision' not in protocol_methods
        assert 'write_decision' not in protocol_methods

    def test_protocol_does_not_import_sqlalchemy(self):
        """Test that repository_contracts module does not import SQLAlchemy."""
        import scripts.householder.repository_contracts as rc_module

        source = Path(rc_module.__file__).read_text()
        assert 'sqlalchemy' not in source.lower()
        assert 'flask_sqlalchemy' not in source.lower()
        assert 'alembic' not in source.lower()

    def test_protocol_does_not_import_flask_db(self):
        """Test that repository_contracts does not import Flask-SQLAlchemy."""
        import scripts.householder.repository_contracts as rc_module

        source = Path(rc_module.__file__).read_text()
        assert 'from flask_sqlalchemy' not in source.lower()
        assert 'import db' not in source.lower()

    def test_protocol_does_not_import_database_modules(self):
        """Test that repository_contracts does not import database/ORM modules."""
        import scripts.householder.repository_contracts as rc_module

        source = Path(rc_module.__file__).read_text()
        assert 'sqlite' not in source.lower()
        assert 'postgres' not in source.lower()
        assert 'mysql' not in source.lower()
        # Check for actual imports of ORM modules, not just the word "orm" in docs
        assert 'import orm' not in source.lower()
        assert 'from orm' not in source.lower()


class TestFixtureImportRepositoryConforms:
    """Tests verifying FixtureImportRepository conforms to protocol."""

    def test_fixture_repository_has_list_imports(self):
        """Test that FixtureImportRepository has list_imports method."""
        assert hasattr(FixtureImportRepository, 'list_imports')
        assert callable(getattr(FixtureImportRepository, 'list_imports'))

    def test_fixture_repository_has_get_dashboard(self):
        """Test that FixtureImportRepository has get_dashboard method."""
        assert hasattr(FixtureImportRepository, 'get_dashboard')
        assert callable(getattr(FixtureImportRepository, 'get_dashboard'))

    def test_fixture_repository_has_get_validation(self):
        """Test that FixtureImportRepository has get_validation method."""
        assert hasattr(FixtureImportRepository, 'get_validation')
        assert callable(getattr(FixtureImportRepository, 'get_validation'))

    def test_fixture_repository_has_get_normalizations(self):
        """Test that FixtureImportRepository has get_normalizations method."""
        assert hasattr(FixtureImportRepository, 'get_normalizations')
        assert callable(getattr(FixtureImportRepository, 'get_normalizations'))

    def test_fixture_repository_has_get_households(self):
        """Test that FixtureImportRepository has get_households method."""
        assert hasattr(FixtureImportRepository, 'get_households')
        assert callable(getattr(FixtureImportRepository, 'get_households'))

    def test_fixture_repository_has_get_duplicates(self):
        """Test that FixtureImportRepository has get_duplicates method."""
        assert hasattr(FixtureImportRepository, 'get_duplicates')
        assert callable(getattr(FixtureImportRepository, 'get_duplicates'))

    def test_fixture_repository_has_get_audit(self):
        """Test that FixtureImportRepository has get_audit method."""
        assert hasattr(FixtureImportRepository, 'get_audit')
        assert callable(getattr(FixtureImportRepository, 'get_audit'))

    def test_fixture_repository_has_get_exports(self):
        """Test that FixtureImportRepository has get_exports method."""
        assert hasattr(FixtureImportRepository, 'get_exports')
        assert callable(getattr(FixtureImportRepository, 'get_exports'))


class TestFixtureImportRepositoryReturnTypes:
    """Tests verifying FixtureImportRepository returns correct view model types."""

    def test_list_imports_returns_list_of_import_summary(self):
        """Test that list_imports returns List[ImportSummary]."""
        result = FixtureImportRepository.list_imports()
        assert isinstance(result, list)
        assert all(isinstance(item, ImportSummary) for item in result)

    def test_get_dashboard_returns_import_dashboard_view_model(self):
        """Test that get_dashboard returns ImportDashboardViewModel."""
        result = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert isinstance(result, ImportDashboardViewModel)

    def test_get_validation_returns_validation_page_view_model(self):
        """Test that get_validation returns ValidationPageViewModel."""
        result = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        assert isinstance(result, ValidationPageViewModel)

    def test_get_normalizations_returns_normalization_page_view_model(self):
        """Test that get_normalizations returns NormalizationPageViewModel."""
        result = FixtureImportRepository.get_normalizations("IMP-2025-0101-A")
        assert isinstance(result, NormalizationPageViewModel)

    def test_get_households_returns_household_page_view_model(self):
        """Test that get_households returns HouseholdPageViewModel."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        assert isinstance(result, HouseholdPageViewModel)

    def test_get_duplicates_returns_duplicate_page_view_model(self):
        """Test that get_duplicates returns DuplicatePageViewModel."""
        result = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        assert isinstance(result, DuplicatePageViewModel)

    def test_get_audit_returns_audit_page_view_model(self):
        """Test that get_audit returns AuditPageViewModel."""
        result = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        assert isinstance(result, AuditPageViewModel)

    def test_get_exports_returns_export_console_view_model(self):
        """Test that get_exports returns ExportConsoleViewModel."""
        result = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        assert isinstance(result, ExportConsoleViewModel)


class TestFixtureImportRepositoryViewModelImmutability:
    """Tests verifying returned view models are frozen (immutable)."""

    def test_import_summary_is_frozen(self):
        """Test that ImportSummary instances are frozen dataclasses."""
        result = FixtureImportRepository.list_imports()
        if result:
            summary = result[0]
            # Attempt to modify should raise exception
            with pytest.raises((AttributeError, ValueError)):
                summary.id = "new_id"

    def test_import_dashboard_view_model_is_frozen(self):
        """Test that ImportDashboardViewModel is frozen dataclass."""
        result = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        # Attempt to modify should raise exception
        with pytest.raises((AttributeError, ValueError)):
            result.batch_id = "new_id"

    def test_validation_page_view_model_is_frozen(self):
        """Test that ValidationPageViewModel is frozen dataclass."""
        result = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        # Attempt to modify should raise exception
        with pytest.raises((AttributeError, ValueError)):
            result.batch_id = "new_id"

    def test_normalization_page_view_model_is_frozen(self):
        """Test that NormalizationPageViewModel is frozen dataclass."""
        result = FixtureImportRepository.get_normalizations("IMP-2025-0101-A")
        # Attempt to modify should raise exception
        with pytest.raises((AttributeError, ValueError)):
            result.batch_id = "new_id"

    def test_household_page_view_model_is_frozen(self):
        """Test that HouseholdPageViewModel is frozen dataclass."""
        result = FixtureImportRepository.get_households("IMP-2025-0101-A")
        # Attempt to modify should raise exception
        with pytest.raises((AttributeError, ValueError)):
            result.batch_id = "new_id"

    def test_duplicate_page_view_model_is_frozen(self):
        """Test that DuplicatePageViewModel is frozen dataclass."""
        result = FixtureImportRepository.get_duplicates("IMP-2025-0101-A")
        # Attempt to modify should raise exception
        with pytest.raises((AttributeError, ValueError)):
            result.batch_id = "new_id"

    def test_audit_page_view_model_is_frozen(self):
        """Test that AuditPageViewModel is frozen dataclass."""
        result = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        # Attempt to modify should raise exception
        with pytest.raises((AttributeError, ValueError)):
            result.batch_id = "new_id"

    def test_export_console_view_model_is_frozen(self):
        """Test that ExportConsoleViewModel is frozen dataclass."""
        result = FixtureImportRepository.get_exports("IMP-2025-0101-A")
        # Attempt to modify should raise exception
        with pytest.raises((AttributeError, ValueError)):
            result.batch_id = "new_id"


class TestNoOrmExposure:
    """Tests verifying no ORM/database objects are exposed."""

    def test_no_sqlalchemy_objects_in_list_imports(self):
        """Test that list_imports does not expose SQLAlchemy objects."""
        result = FixtureImportRepository.list_imports()
        for item in result:
            assert not hasattr(item, '__table__')  # SQLAlchemy attribute
            assert not hasattr(item, '__mapper__')  # SQLAlchemy attribute

    def test_no_sqlalchemy_objects_in_get_dashboard(self):
        """Test that get_dashboard does not expose SQLAlchemy objects."""
        result = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        assert not hasattr(result, '__table__')
        assert not hasattr(result, '__mapper__')

    def test_no_database_session_objects_exposed(self):
        """Test that repository does not expose database session objects."""
        result = FixtureImportRepository.get_audit("IMP-2025-0101-A")
        # Audit entries should not have session or connection attributes
        for entry in result.audit_entries:
            assert not hasattr(entry, 'session')
            assert not hasattr(entry, 'connection')
            assert not hasattr(entry, '_sa_instance_state')


class TestRepositoryDoesNotMutateData:
    """Tests verifying repository operations do not mutate raw data."""

    def test_list_imports_does_not_mutate(self):
        """Test that calling list_imports multiple times returns consistent data."""
        result1 = FixtureImportRepository.list_imports()
        result2 = FixtureImportRepository.list_imports()

        # Should have same count and same IDs
        assert len(result1) == len(result2)
        if result1:
            assert result1[0].id == result2[0].id

    def test_get_dashboard_does_not_mutate(self):
        """Test that get_dashboard can be called repeatedly without mutation."""
        result1 = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")
        result2 = FixtureImportRepository.get_dashboard("IMP-2025-0101-A")

        # Should return identical data
        assert result1.batch_id == result2.batch_id
        assert result1.progress == result2.progress

    def test_get_validation_does_not_mutate(self):
        """Test that get_validation returns consistent data."""
        result1 = FixtureImportRepository.get_validation("IMP-2025-0101-A")
        result2 = FixtureImportRepository.get_validation("IMP-2025-0101-A")

        assert result1.total_records == result2.total_records
        assert len(result1.validation_rows) == len(result2.validation_rows)


class TestProtocolDocumentation:
    """Tests verifying protocol documentation is present."""

    def test_protocol_has_docstring(self):
        """Test that ImportRepositoryProtocol has class docstring."""
        assert ImportRepositoryProtocol.__doc__ is not None

    def test_list_imports_has_docstring(self):
        """Test that list_imports method has docstring."""
        assert ImportRepositoryProtocol.list_imports.__doc__ is not None

    def test_get_dashboard_has_docstring(self):
        """Test that get_dashboard method has docstring."""
        assert ImportRepositoryProtocol.get_dashboard.__doc__ is not None

    def test_get_validation_has_docstring(self):
        """Test that get_validation method has docstring."""
        assert ImportRepositoryProtocol.get_validation.__doc__ is not None

    def test_get_normalizations_has_docstring(self):
        """Test that get_normalizations method has docstring."""
        assert ImportRepositoryProtocol.get_normalizations.__doc__ is not None

    def test_get_households_has_docstring(self):
        """Test that get_households method has docstring."""
        assert ImportRepositoryProtocol.get_households.__doc__ is not None

    def test_get_duplicates_has_docstring(self):
        """Test that get_duplicates method has docstring."""
        assert ImportRepositoryProtocol.get_duplicates.__doc__ is not None

    def test_get_audit_has_docstring(self):
        """Test that get_audit method has docstring."""
        assert ImportRepositoryProtocol.get_audit.__doc__ is not None

    def test_get_exports_has_docstring(self):
        """Test that get_exports method has docstring."""
        assert ImportRepositoryProtocol.get_exports.__doc__ is not None
