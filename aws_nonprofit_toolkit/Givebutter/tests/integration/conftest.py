"""Pytest configuration for integration tests.

Provides database fixtures for database-mode testing.
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    init_db,
    create_db_engine,
    get_session,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
    AuditLogRecord,
)
from .seed_database import seed_test_data


@pytest.fixture
def test_db_path(tmp_path):
    """Provide isolated test database path."""
    db_path = tmp_path / "givebutter_test.db"
    return f"sqlite:///{db_path}"


@pytest.fixture
def initialized_test_db(test_db_path):
    """Create test database with schema and seed data."""
    # Create database schema using models
    engine = init_db(test_db_path)
    session = get_session(engine)

    try:
        # Seed with test data
        seed_test_data(session)

        session.commit()

        yield test_db_path
    finally:
        session.close()


@pytest.fixture
def client_with_fixture(monkeypatch):
    """Create Flask test client with fixture mode configured.

    Function-scoped fixture that configures repository mode to use in-memory
    fixture data (not database). Uses monkeypatch for environment cleanup
    that reverts after test.
    """
    # IMPORTANT: Reset Flask app state and environment first
    # This ensures we don't inherit configuration from previous tests
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'fixture')
    monkeypatch.delenv('GIVEBUTTER_DATABASE_URL', raising=False)

    # Create app in test mode
    app.config['TESTING'] = True

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def client_with_database(monkeypatch, initialized_test_db):
    """Create Flask test client with database mode configured.

    Function-scoped fixture that configures repository mode to use a seeded
    SQLite database. Uses monkeypatch for environment cleanup that reverts
    after test.
    """
    # IMPORTANT: Configure database mode via environment variables
    # This resets any previous fixture mode configuration
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', initialized_test_db)

    # Create app in test mode
    app.config['TESTING'] = True

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def client(monkeypatch, initialized_test_db):
    """Create Flask test client with database mode configured.

    Deprecated: Use client_with_database or client_with_fixture instead.
    This fixture exists for backward compatibility with existing tests.
    """
    # IMPORTANT: Reset environment to database mode
    # This ensures proper cleanup from previous tests
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', initialized_test_db)

    # Create app in test mode
    app.config['TESTING'] = True

    with app.test_client() as test_client:
        yield test_client
