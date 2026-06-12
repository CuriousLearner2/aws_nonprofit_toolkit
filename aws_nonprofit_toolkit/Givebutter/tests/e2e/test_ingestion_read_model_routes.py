"""
End-to-end tests for Flask route verification.

NOTE: Full database mode routing is implemented in Phase 1C-Step 6.
These tests verify that the 8 canonical routes exist and are callable.
"""

import pytest
from pathlib import Path

from scripts.householder.ingestion_service import ingest_processed_csv
from scripts.householder.database_models import init_db


@pytest.fixture
def flask_client():
    """Create Flask test client."""
    from scripts.uploader.app import app
    app.config["TESTING"] = True
    client = app.test_client()
    return client


class TestCanonicalRoutesExist:
    """Verify all 8 canonical routes are callable (fixture mode)."""

    def test_route_imports_list_callable(self, flask_client):
        """GET /imports is callable and returns HTML."""
        response = flask_client.get("/imports")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "<table" in html or "Import" in html

    def test_route_imports_detail_callable(self, flask_client):
        """GET /imports/<batch_id>/dashboard is callable and returns HTML."""
        # Using fixture batch ID
        response = flask_client.get("/imports/IMP-2025-0101-A/dashboard")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "html" in html.lower()

    def test_route_validation_items_callable(self, flask_client):
        """GET /imports/<batch_id>/validation is callable and returns HTML."""
        response = flask_client.get("/imports/IMP-2025-0101-A/validation")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "html" in html.lower()

    def test_route_normalization_items_callable(self, flask_client):
        """GET /imports/<batch_id>/normalizations is callable and returns HTML."""
        response = flask_client.get("/imports/IMP-2025-0101-A/normalizations")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "html" in html.lower()

    def test_route_households_callable(self, flask_client):
        """GET /imports/<batch_id>/households is callable and returns HTML."""
        response = flask_client.get("/imports/IMP-2025-0101-A/households")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "html" in html.lower()

    def test_route_duplicates_callable(self, flask_client):
        """GET /imports/<batch_id>/duplicates is callable and returns HTML."""
        response = flask_client.get("/imports/IMP-2025-0101-A/duplicates")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "html" in html.lower()

    def test_route_audit_callable(self, flask_client):
        """GET /imports/<batch_id>/audit is callable and returns HTML."""
        response = flask_client.get("/imports/IMP-2025-0101-A/audit")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "html" in html.lower()

    def test_route_exports_callable(self, flask_client):
        """GET /imports/<batch_id>/exports is callable and returns HTML."""
        response = flask_client.get("/imports/IMP-2025-0101-A/exports")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "html" in html.lower()


class TestDatabaseModeReadinessNote:
    """
    Placeholder note: Full database mode integration testing deferred to Phase 1C-Step 6.

    Phase 1C-Step 6 will:
    - Wire DatabaseImportRepository to Flask routes
    - Replace fixture data with database queries
    - Add full ingestion → routing integration tests
    """

    def test_database_mode_routing_deferred_to_step_6(self):
        """Verify: Full database mode routing is Phase 1C-Step 6 work."""
        # This is a documentation test noting the scope boundary
        # Phase 1C-Step 5 verifies repository methods (integration tests)
        # Phase 1C-Step 6 will wire those methods to Flask routes
        assert True
