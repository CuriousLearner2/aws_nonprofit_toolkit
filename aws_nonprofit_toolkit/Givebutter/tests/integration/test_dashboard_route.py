"""
Integration tests for dashboard route service boundary.

Verify that the /imports/<import_id>/dashboard route returns correct
content and status code after service-boundary migration.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app


class TestDashboardRoute:
    """Test dashboard route integration."""

    def test_dashboard_route_returns_200(self, client_with_fixture):
        """Test that dashboard route returns 200 status."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert response.status_code == 200

    def test_dashboard_contains_title(self, client_with_fixture):
        """Test that dashboard contains page title."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'Import Dashboard' in response.data

    def test_dashboard_contains_batch_id(self, client_with_fixture):
        """Test that dashboard displays batch ID."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'IMP-2025-0101-A' in response.data

    def test_dashboard_contains_filename(self, client_with_fixture):
        """Test that dashboard displays source filename."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'donors_q1_2025.csv' in response.data

    def test_dashboard_contains_progress(self, client_with_fixture):
        """Test that dashboard displays progress percentage."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'42%' in response.data

    def test_dashboard_contains_duplicates_queue(self, client_with_fixture):
        """Test that dashboard contains duplicates review queue."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'Possible Duplicates' in response.data
        assert b'Review Duplicates' in response.data

    def test_dashboard_contains_validation_queue(self, client_with_fixture):
        """Test that dashboard contains validation review queue."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'Validation Review' in response.data
        assert b'Review Records' in response.data

    def test_dashboard_contains_normalizations_queue(self, client_with_fixture):
        """Test that dashboard contains normalizations review queue."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'Normalizations' in response.data
        assert b'Review Normalizations' in response.data

    def test_dashboard_contains_households_queue(self, client_with_fixture):
        """Test that dashboard contains households review queue."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'Households' in response.data
        assert b'Review Households' in response.data

    def test_dashboard_queue_counts(self, client_with_fixture):
        """Test that dashboard displays correct queue counts."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        # Check badge counts
        assert b'>3<' in response.data  # Duplicates
        assert b'>8<' in response.data  # Validation
        assert b'>6<' in response.data  # Normalizations
        assert b'>5<' in response.data  # Households

    def test_dashboard_navigation_links(self, client_with_fixture):
        """Test that dashboard contains navigation links."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert b'/imports/IMP-2025-0101-A/duplicates' in response.data
        assert b'/imports/IMP-2025-0101-A/validation' in response.data
        assert b'/imports/IMP-2025-0101-A/normalizations' in response.data
        assert b'/imports/IMP-2025-0101-A/households' in response.data
        assert b'/imports/IMP-2025-0101-A/audit' in response.data
        assert b'/imports/IMP-2025-0101-A/exports' in response.data
        assert b'/imports' in response.data  # Back link

    def test_imports_route_still_works(self, client_with_fixture):
        """Test that /imports route still works (Step 1 regression check)."""
        response = client_with_fixture.get('/imports')
        assert response.status_code == 200
        assert b'Imports' in response.data

    def test_duplicates_route_untouched(self, client_with_fixture):
        """Test that duplicates route was not modified."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200
        assert b'Possible Duplicates' in response.data

    def test_validation_route_untouched(self, client_with_fixture):
        """Test that validation route was not modified."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        assert b'Validation' in response.data

    def test_households_route_untouched(self, client_with_fixture):
        """Test that households route was not modified."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_audit_route_untouched(self, client_with_fixture):
        """Test that audit route was not modified."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert response.status_code == 200

    def test_exports_route_untouched(self, client_with_fixture):
        """Test that exports route was not modified."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert response.status_code == 200
