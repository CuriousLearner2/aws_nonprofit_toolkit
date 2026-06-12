"""
Repository Provider - Configurable repository selection.

Phase 1B-Step 5I: Infrastructure boundary for repository selection.

Provides a single entry point to select between FixtureImportRepository and
DatabaseImportRepository based on configuration. Default is fixture-backed.

Does not perform service swapping. Routes and services remain unchanged.
Future service refactoring will use this provider.
"""

import os
from typing import Optional, Any, Mapping

from .repository_contracts import ImportRepositoryProtocol
from .fixture_repository import FixtureImportRepository
from .database_repository import DatabaseImportRepository


def get_import_repository(
    config: Optional[Mapping[str, Any]] = None,
) -> ImportRepositoryProtocol:
    """
    Get a repository instance based on configuration.

    Default behavior: returns FixtureImportRepository (Phase 0 fixtures).

    Database behavior: returns DatabaseImportRepository when explicitly
    configured via HOUSEHOLDER_REPOSITORY=database environment variable
    or config dict.

    Args:
        config: Optional configuration mapping. Keys checked:
                - 'HOUSEHOLDER_REPOSITORY': 'fixture' (default) or 'database'

    Returns:
        ImportRepositoryProtocol: Either FixtureImportRepository or
                                 DatabaseImportRepository.

    Raises:
        ValueError: If repository mode is invalid or database mode is
                   selected without required configuration.

    Environment Variables:
        HOUSEHOLDER_REPOSITORY: 'fixture' (default) or 'database'
        GIVEBUTTER_DATABASE_URL: For database mode (optional, uses default if not set)
    """
    # Determine which repository to use
    repository_mode = _get_repository_mode(config)

    if repository_mode == "fixture":
        return FixtureImportRepository()

    elif repository_mode == "database":
        return _create_database_repository(config)

    else:
        raise ValueError(
            f"Invalid HOUSEHOLDER_REPOSITORY mode: {repository_mode}. "
            f"Valid modes: 'fixture' (default), 'database'."
        )


def _get_repository_mode(config: Optional[Mapping[str, Any]] = None) -> str:
    """
    Determine repository mode from config or environment.

    Priority:
    1. config['HOUSEHOLDER_REPOSITORY'] if provided
    2. HOUSEHOLDER_REPOSITORY environment variable if set
    3. Default: 'fixture'

    Args:
        config: Optional configuration mapping.

    Returns:
        str: 'fixture' or 'database'
    """
    # Check config dict first (highest priority)
    if config and "HOUSEHOLDER_REPOSITORY" in config:
        return config["HOUSEHOLDER_REPOSITORY"].lower()

    # Check environment variable (medium priority)
    env_mode = os.getenv("HOUSEHOLDER_REPOSITORY", "").lower()
    if env_mode:
        return env_mode

    # Default to fixture (lowest priority)
    return "fixture"


def _create_database_repository(
    config: Optional[Mapping[str, Any]] = None,
) -> DatabaseImportRepository:
    """
    Create a DatabaseImportRepository instance.

    Requires explicit database URL configuration.
    Looks for database URL in order:
    1. config['GIVEBUTTER_DATABASE_URL'] if provided
    2. GIVEBUTTER_DATABASE_URL environment variable if set
    3. Raises error if not configured

    Args:
        config: Optional configuration mapping.

    Returns:
        DatabaseImportRepository: Database-backed repository instance.

    Raises:
        ValueError: If database URL is not explicitly configured.
    """
    database_url = _get_database_url(config)

    if not database_url:
        raise ValueError(
            "Database mode requested but no database URL configured. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or "
            "pass config with 'GIVEBUTTER_DATABASE_URL' key."
        )

    return DatabaseImportRepository(database_url=database_url)


def _get_database_url(config: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    """
    Get database URL from config or environment.

    Database mode requires explicit URL configuration.
    No implicit defaults are used.

    Priority:
    1. config['GIVEBUTTER_DATABASE_URL'] if provided
    2. GIVEBUTTER_DATABASE_URL environment variable if set
    3. None (no default)

    Args:
        config: Optional configuration mapping.

    Returns:
        str: Database URL for SQLAlchemy, or None if not configured.
    """
    # Check config dict first
    if config and "GIVEBUTTER_DATABASE_URL" in config:
        return config["GIVEBUTTER_DATABASE_URL"]

    # Check environment variable
    env_url = os.getenv("GIVEBUTTER_DATABASE_URL", "")
    if env_url:
        return env_url

    # No default - database mode requires explicit configuration
    return None
