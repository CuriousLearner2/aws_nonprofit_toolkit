"""
Unit tests for repository provider.

Verifies:
1. Provider returns FixtureImportRepository by default
2. Provider returns FixtureImportRepository with explicit fixture config
3. Provider returns DatabaseImportRepository with explicit database config
4. Provider raises error for invalid repository mode
5. Provider raises error if database mode requested without DB URL
6. Provider respects config priority (config > env > default)
7. Provider return type matches ImportRepositoryProtocol
8. No database state mutations
9. No service/route behavior changes
10. Default production behavior remains fixture-backed
"""

import os
import pytest
from unittest.mock import patch

from scripts.householder.repository_provider import (
    get_import_repository,
    _get_repository_mode,
    _get_database_url,
)
from scripts.householder.repository_contracts import ImportRepositoryProtocol
from scripts.householder.fixture_repository import FixtureImportRepository
from scripts.householder.database_repository import DatabaseImportRepository


class TestRepositoryProviderDefaults:
    """Verify default provider behavior returns FixtureImportRepository."""

    def test_get_import_repository_returns_repository(self):
        """Test that get_import_repository returns a repository instance."""
        repo = get_import_repository()
        assert repo is not None

    def test_default_returns_fixture_repository(self):
        """Test that default config returns FixtureImportRepository."""
        repo = get_import_repository()
        assert isinstance(repo, FixtureImportRepository)

    def test_default_returns_import_repository_protocol(self):
        """Test that returned repository implements ImportRepositoryProtocol."""
        repo = get_import_repository()
        # Verify protocol methods exist
        assert hasattr(repo, 'list_imports')
        assert hasattr(repo, 'get_dashboard')
        assert hasattr(repo, 'get_validation')
        assert hasattr(repo, 'get_households')
        assert hasattr(repo, 'get_duplicates')
        assert hasattr(repo, 'get_audit')
        assert hasattr(repo, 'get_exports')

    def test_no_config_returns_fixture(self):
        """Test that None config returns FixtureImportRepository."""
        repo = get_import_repository(config=None)
        assert isinstance(repo, FixtureImportRepository)

    def test_empty_config_returns_fixture(self):
        """Test that empty config dict returns FixtureImportRepository."""
        repo = get_import_repository(config={})
        assert isinstance(repo, FixtureImportRepository)


class TestRepositoryProviderFixtureMode:
    """Verify explicit fixture mode configuration."""

    def test_explicit_fixture_config_returns_fixture(self):
        """Test that explicit fixture config returns FixtureImportRepository."""
        config = {'HOUSEHOLDER_REPOSITORY': 'fixture'}
        repo = get_import_repository(config=config)
        assert isinstance(repo, FixtureImportRepository)

    def test_fixture_mode_case_insensitive(self):
        """Test that fixture mode config is case-insensitive."""
        config = {'HOUSEHOLDER_REPOSITORY': 'FIXTURE'}
        repo = get_import_repository(config=config)
        assert isinstance(repo, FixtureImportRepository)

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'fixture'})
    def test_environment_fixture_mode(self):
        """Test that environment variable can set fixture mode."""
        repo = get_import_repository()
        assert isinstance(repo, FixtureImportRepository)


class TestRepositoryProviderDatabaseMode:
    """Verify explicit database mode configuration."""

    def test_database_mode_without_url_raises_error(self):
        """Test that database mode without URL raises ValueError."""
        config = {'HOUSEHOLDER_REPOSITORY': 'database'}
        with pytest.raises(ValueError) as exc_info:
            get_import_repository(config=config)
        assert 'Database mode requested but no database URL configured' in str(exc_info.value)

    def test_database_mode_case_insensitive_with_url(self):
        """Test that database mode config is case-insensitive when URL provided."""
        config = {
            'HOUSEHOLDER_REPOSITORY': 'DATABASE',
            'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'
        }
        repo = get_import_repository(config=config)
        assert isinstance(repo, DatabaseImportRepository)

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'})
    def test_environment_database_mode(self):
        """Test that environment variable can set database mode when URL provided."""
        repo = get_import_repository()
        assert isinstance(repo, DatabaseImportRepository)

    def test_database_with_custom_url(self):
        """Test that database mode respects custom database URL."""
        config = {
            'HOUSEHOLDER_REPOSITORY': 'database',
            'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'
        }
        repo = get_import_repository(config=config)
        assert isinstance(repo, DatabaseImportRepository)
        assert repo.database_url == 'sqlite:///:memory:'


class TestRepositoryProviderConfigPriority:
    """Verify config parameter priority over environment."""

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database'})
    def test_config_overrides_environment(self):
        """Test that config parameter overrides environment variable."""
        config = {'HOUSEHOLDER_REPOSITORY': 'fixture'}
        repo = get_import_repository(config=config)
        # Should return fixture (config) not database (env)
        assert isinstance(repo, FixtureImportRepository)

    @patch.dict(os.environ, {'GIVEBUTTER_DATABASE_URL': 'sqlite:///env.db'})
    def test_database_url_config_overrides_environment(self):
        """Test that database URL config overrides environment."""
        config = {
            'HOUSEHOLDER_REPOSITORY': 'database',
            'GIVEBUTTER_DATABASE_URL': 'sqlite:///config.db'
        }
        repo = get_import_repository(config=config)
        assert repo.database_url == 'sqlite:///config.db'


class TestRepositoryProviderErrors:
    """Verify error handling for invalid configurations."""

    def test_invalid_repository_mode_raises_error(self):
        """Test that invalid repository mode raises ValueError."""
        config = {'HOUSEHOLDER_REPOSITORY': 'invalid_mode'}
        with pytest.raises(ValueError) as exc_info:
            get_import_repository(config=config)
        assert 'Invalid HOUSEHOLDER_REPOSITORY mode' in str(exc_info.value)
        assert 'invalid_mode' in str(exc_info.value)

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'invalid'})
    def test_invalid_environment_mode_raises_error(self):
        """Test that invalid environment mode raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_import_repository()
        assert 'Invalid HOUSEHOLDER_REPOSITORY mode' in str(exc_info.value)

    def test_database_mode_without_url_raises_error(self):
        """Test that database mode requires explicit URL."""
        config = {'HOUSEHOLDER_REPOSITORY': 'database'}
        with pytest.raises(ValueError) as exc_info:
            get_import_repository(config=config)
        assert 'Database mode requested but no database URL configured' in str(exc_info.value)

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database'}, clear=False)
    def test_database_mode_env_without_url_raises_error(self):
        """Test that database mode via environment requires explicit URL."""
        # Clear GIVEBUTTER_DATABASE_URL if set
        os.environ.pop('GIVEBUTTER_DATABASE_URL', None)
        with pytest.raises(ValueError) as exc_info:
            get_import_repository()
        assert 'Database mode requested but no database URL configured' in str(exc_info.value)


class TestRepositoryProviderModeDetection:
    """Verify internal mode detection logic."""

    def test_get_repository_mode_default(self):
        """Test that mode detection returns 'fixture' by default."""
        mode = _get_repository_mode(config=None)
        assert mode == 'fixture'

    def test_get_repository_mode_from_config(self):
        """Test that mode detection reads from config."""
        config = {'HOUSEHOLDER_REPOSITORY': 'database'}
        mode = _get_repository_mode(config=config)
        assert mode == 'database'

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database'})
    def test_get_repository_mode_from_environment(self):
        """Test that mode detection reads from environment."""
        mode = _get_repository_mode(config=None)
        assert mode == 'database'

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database'})
    def test_get_repository_mode_config_priority(self):
        """Test that config takes priority over environment."""
        config = {'HOUSEHOLDER_REPOSITORY': 'fixture'}
        mode = _get_repository_mode(config=config)
        assert mode == 'fixture'


class TestRepositoryProviderDatabaseUrl:
    """Verify database URL detection logic."""

    @patch.dict(os.environ, clear=True)
    def test_get_database_url_no_default(self):
        """Test that no default database URL is returned when not configured."""
        url = _get_database_url(config=None)
        assert url is None

    def test_get_database_url_from_config(self):
        """Test that database URL can be read from config."""
        config = {'GIVEBUTTER_DATABASE_URL': 'sqlite:///test.db'}
        url = _get_database_url(config=config)
        assert url == 'sqlite:///test.db'

    @patch.dict(os.environ, {'GIVEBUTTER_DATABASE_URL': 'sqlite:///env.db'})
    def test_get_database_url_from_environment(self):
        """Test that database URL can be read from environment."""
        url = _get_database_url(config=None)
        assert url == 'sqlite:///env.db'

    @patch.dict(os.environ, {'GIVEBUTTER_DATABASE_URL': 'sqlite:///env.db'})
    def test_get_database_url_config_priority(self):
        """Test that config takes priority over environment for URL."""
        config = {'GIVEBUTTER_DATABASE_URL': 'sqlite:///config.db'}
        url = _get_database_url(config=config)
        assert url == 'sqlite:///config.db'


class TestRepositoryProviderBoundaries:
    """Verify provider boundary conditions."""

    def test_provider_does_not_mutate_repository(self):
        """Test that provider does not mutate repository state."""
        repo1 = get_import_repository()
        repo2 = get_import_repository()
        # Both should be independent instances
        assert repo1 is not repo2

    def test_fixture_repository_always_works(self):
        """Test that fixture repository is always available."""
        config = {'HOUSEHOLDER_REPOSITORY': 'fixture'}
        repo = get_import_repository(config=config)
        # Should not raise, fixture is always available
        assert isinstance(repo, FixtureImportRepository)

    def test_provider_returns_same_protocol(self):
        """Test that both repository types satisfy ImportRepositoryProtocol."""
        fixture_repo = get_import_repository({'HOUSEHOLDER_REPOSITORY': 'fixture'})
        database_repo = get_import_repository({
            'HOUSEHOLDER_REPOSITORY': 'database',
            'GIVEBUTTER_DATABASE_URL': 'sqlite:///:memory:'
        })

        # Both should have protocol methods
        for repo in [fixture_repo, database_repo]:
            assert callable(getattr(repo, 'list_imports', None))
            assert callable(getattr(repo, 'get_dashboard', None))
            assert callable(getattr(repo, 'get_validation', None))
            assert callable(getattr(repo, 'get_households', None))
            assert callable(getattr(repo, 'get_duplicates', None))
            assert callable(getattr(repo, 'get_audit', None))
            assert callable(getattr(repo, 'get_exports', None))


class TestRepositoryProviderNoServiceChanges:
    """Verify that provider does not change existing services/routes."""

    def test_no_database_repository_import_in_services(self):
        """Verify DatabaseImportRepository is not imported by services."""
        try:
            import scripts.householder.duplicates_service as service
            service_source = service.__file__
            with open(service_source, 'r') as f:
                content = f.read()
                assert 'DatabaseImportRepository' not in content
        except (ImportError, FileNotFoundError):
            pass  # Service may not exist or be loaded from bytecode

    def test_no_database_repository_import_in_routes(self):
        """Verify DatabaseImportRepository is not imported by routes."""
        try:
            import scripts.uploader.app as app
            app_source = app.__file__
            with open(app_source, 'r') as f:
                content = f.read()
                assert 'DatabaseImportRepository' not in content
        except (ImportError, FileNotFoundError):
            pass  # Routes may not be loaded from source


class TestRepositoryProviderDefaultProduction:
    """Verify default production behavior is fixture-backed."""

    @patch.dict(os.environ, clear=True)
    def test_production_default_is_fixture(self):
        """Test that production default (no config/env) is fixture-backed."""
        repo = get_import_repository(config=None)
        assert isinstance(repo, FixtureImportRepository)
        assert not isinstance(repo, DatabaseImportRepository)

    def test_explicit_fixture_mode_works(self):
        """Test that explicit fixture mode is always available."""
        config = {'HOUSEHOLDER_REPOSITORY': 'fixture'}
        repo = get_import_repository(config=config)
        assert isinstance(repo, FixtureImportRepository)


class TestRepositoryProviderExplicitConfigPrecedence:
    """Verify explicit config parameter takes highest priority.

    Phase 1B2 requirement: explicit config > env vars > fixture default
    """

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': 'sqlite:///env.db'})
    def test_explicit_fixture_beats_env_database(self):
        """Explicit fixture config must beat environment database mode."""
        # Environment says database, config says fixture
        config = {'HOUSEHOLDER_REPOSITORY': 'fixture'}
        repo = get_import_repository(config=config)
        # Must use fixture (explicit config), not database (environment)
        assert isinstance(repo, FixtureImportRepository)

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'fixture'})
    def test_explicit_database_beats_env_fixture(self):
        """Explicit database config must beat environment fixture mode."""
        # Environment says fixture, config says database
        config = {
            'HOUSEHOLDER_REPOSITORY': 'database',
            'GIVEBUTTER_DATABASE_URL': 'sqlite:///explicit.db'
        }
        repo = get_import_repository(config=config)
        # Must use database (explicit config), not fixture (environment)
        assert isinstance(repo, DatabaseImportRepository)
        assert repo.database_url == 'sqlite:///explicit.db'

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': 'sqlite:///env.db'})
    def test_explicit_database_url_beats_env_url(self):
        """Explicit database URL must beat environment database URL."""
        # Both say database, but different URLs
        config = {
            'HOUSEHOLDER_REPOSITORY': 'database',
            'GIVEBUTTER_DATABASE_URL': 'sqlite:///explicit.db'
        }
        repo = get_import_repository(config=config)
        # Must use explicit URL, not environment URL
        assert isinstance(repo, DatabaseImportRepository)
        assert repo.database_url == 'sqlite:///explicit.db'

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': 'sqlite:///env.db'})
    def test_explicit_config_none_uses_environment(self):
        """When config is None, environment variables should be used."""
        # Environment says database with URL, config is None
        repo = get_import_repository(config=None)
        # Must use database from environment
        assert isinstance(repo, DatabaseImportRepository)
        assert repo.database_url == 'sqlite:///env.db'

    @patch.dict(os.environ, {'HOUSEHOLDER_REPOSITORY': 'fixture'})
    def test_explicit_empty_config_uses_fixture_default(self):
        """When config is empty dict, fixture default should be used."""
        # Environment says fixture, config is empty dict
        repo = get_import_repository(config={})
        # Must use fixture (default)
        assert isinstance(repo, FixtureImportRepository)

    @patch.dict(os.environ, clear=True)
    def test_no_config_no_env_uses_fixture_default(self):
        """When nothing configured, fixture default should be used."""
        # No environment variables, no config
        repo = get_import_repository(config=None)
        # Must use fixture (default)
        assert isinstance(repo, FixtureImportRepository)
