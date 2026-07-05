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

    def test_dashboard_shows_attention_banner(self, client_with_fixture):
        """Test that dashboard renders a compact needs-attention banner."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        html = response.data.decode('utf-8')

        assert 'data-testid="dashboard-related-links"' in html
        assert 'data-testid="dashboard-attention-banner"' in html
        assert 'data-testid="dashboard-next-step-note"' in html
        assert 'data-testid="dashboard-jump-strip"' in html
        assert 'data-testid="dashboard-jump-validation"' in html
        assert 'data-testid="dashboard-jump-duplicates"' in html
        assert 'data-testid="dashboard-jump-normalizations"' in html
        assert 'data-testid="dashboard-jump-households"' in html
        assert 'Review queues should be handled before export.' in html
        assert 'Blockers require attention before export under existing rules.' in html
        assert 'Warnings are review-relevant but distinct from blockers.' in html
        assert 'Raw source rows remain unchanged.' in html
        assert 'data-attention-queue="validation"' in html
        assert 'href="#dashboard-validation-review"' in html
        assert 'href="#dashboard-possible-duplicates"' in html
        assert 'href="#dashboard-normalizations"' in html
        assert 'href="#dashboard-households"' in html
        assert 'href="/imports/IMP-2025-0101-A/readiness"' in html
        assert 'href="/imports/IMP-2025-0101-A/exports"' in html
        assert 'href="/imports/IMP-2025-0101-A/audit"' in html
        assert 'Possible Duplicates' in html
        assert 'Validation Review' in html
        assert 'Normalizations' in html
        assert 'Households' in html
        assert '/imports/IMP-2025-0101-A/validation' in html
        assert '/imports/IMP-2025-0101-A/duplicates' in html
        assert '/imports/IMP-2025-0101-A/normalizations' in html
        assert '/imports/IMP-2025-0101-A/households' in html
        assert 'id="dashboard-validation-review"' in html
        assert 'id="dashboard-possible-duplicates"' in html
        assert 'id="dashboard-normalizations"' in html
        assert 'id="dashboard-households"' in html

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

    def test_dashboard_jump_strip_targets_are_stable(self, client_with_fixture):
        """Test that jump links point to real in-page queue section ids."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        html = response.data.decode('utf-8')

        jump_targets = {
            'dashboard-validation-review': 'Validation Review',
            'dashboard-possible-duplicates': 'Possible Duplicates',
            'dashboard-normalizations': 'Normalizations',
            'dashboard-households': 'Households',
        }

        for target_id, label in jump_targets.items():
            assert f'id="{target_id}"' in html
            assert f'href="#{target_id}"' in html
            assert label in html

    def test_imports_route_still_works(self, client_with_fixture):
        """Test that /imports route still works (Step 1 regression check)."""
        response = client_with_fixture.get('/imports')
        assert response.status_code == 200
        assert b'Imports' in response.data

    def test_imports_route_shows_status_orientation(self, client_with_fixture):
        """Test that /imports explains status badges and review navigation."""
        response = client_with_fixture.get('/imports')
        html = response.data.decode('utf-8')

        assert 'data-testid="imports-status-orientation"' in html
        assert 'Imports are reviewed before export.' in html
        assert 'Status and progress badges show the current review state.' in html
        assert 'Review opens the import review workflow.' in html
        assert 'Raw source data remains unchanged.' in html
        assert 'Batch ID' in html
        assert 'Status' in html
        assert 'Review' in html

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
