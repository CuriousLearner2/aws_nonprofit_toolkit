"""
Integration tests for normalizations review route service boundary.

Verify that the /imports/<import_id>/normalizations route returns correct
content and status code after service-boundary migration.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestNormalizationsRoute:
    """Test normalizations route integration."""

    def test_normalizations_route_returns_200(self, client):
        """Test that normalizations route returns 200 status."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert response.status_code == 200

    def test_normalizations_contains_title(self, client):
        """Test that normalizations page contains title."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Normalizations' in response.data

    def test_normalizations_contains_batch_id(self, client):
        """Test that normalizations page displays batch ID."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'IMP-2025-0101-A' in response.data

    def test_normalizations_contains_suggestion_count(self, client):
        """Test that normalizations page displays suggestion count."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        # Should display "Suggestion 1 of 6"
        assert b'Suggestion' in response.data
        assert b'1 of 6' in response.data

    def test_normalizations_contains_current_suggestion(self, client):
        """Test that normalizations page displays current suggestion."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        # First suggestion is about Name field for John Smith
        assert b'Name' in response.data
        assert b'John Smith' in response.data

    def test_normalizations_contains_field_name(self, client):
        """Test that normalizations page displays field name."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Name' in response.data

    def test_normalizations_contains_original_value(self, client):
        """Test that normalizations page displays original value."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'john smith' in response.data

    def test_normalizations_contains_suggested_value(self, client):
        """Test that normalizations page displays suggested value."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'John Smith' in response.data

    def test_normalizations_contains_normalization_type(self, client):
        """Test that normalizations page displays normalization type."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Capitalization Fix' in response.data

    def test_normalizations_contains_confirm_action(self, client):
        """Test that normalizations page contains Confirm action."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Confirm' in response.data
        assert b'accept_normalization' in response.data

    def test_normalizations_contains_reject_action(self, client):
        """Test that normalizations page contains Reject action."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Reject' in response.data
        assert b'reject_normalization' in response.data

    def test_normalizations_contains_defer_action(self, client):
        """Test that normalizations page contains Defer action."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Defer' in response.data
        assert b'defer' in response.data

    def test_normalizations_contains_navigation_previous(self, client):
        """Test that normalizations page contains Previous button."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Previous Suggestion' in response.data or b'Previous' in response.data

    def test_normalizations_contains_navigation_next(self, client):
        """Test that normalizations page contains Next button."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Next Suggestion' in response.data or b'Next' in response.data

    def test_normalizations_contains_back_to_dashboard(self, client):
        """Test that normalizations page has back to dashboard link."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'/imports/IMP-2025-0101-A/dashboard' in response.data

    def test_normalizations_contains_progress_bar(self, client):
        """Test that normalizations page displays progress bar."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Progress' in response.data

    def test_normalizations_contains_safety_message(self, client):
        """Test that normalizations page contains safety message about raw import rows."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Raw import rows remain unchanged' in response.data

    def test_normalizations_contains_decision_heading(self, client):
        """Test that normalizations page contains decision section."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert b'Your Decision' in response.data

    def test_normalizations_no_forbidden_vocabulary(self, client):
        """Test that normalizations page does not contain forbidden vocabulary."""
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        html = response.data.decode('utf-8', errors='ignore').lower()

        forbidden = [
            'merge', 'merged', 'auto-apply', 'apply all', 'approve all',
            'sync', 'synced', 'syncing', 'crm ingestion', 'crm writeback',
            'writeback', 'finalized', 'master id', 'master database',
            'primary donor profile', 'entity audit', 'donor history',
            'push to crm', 'connected to vault', 'bulk approval',
            'cleaned files', 'householded files'
        ]

        for word in forbidden:
            assert word not in html, f"Forbidden vocabulary '{word}' found in response"

    def test_imports_route_still_works(self, client):
        """Test that /imports route still works (Step 1 regression check)."""
        response = client.get('/imports')
        assert response.status_code == 200
        assert b'Imports' in response.data

    def test_dashboard_route_still_works(self, client):
        """Test that /dashboard route still works (Step 2 regression check)."""
        response = client.get('/imports/IMP-2025-0101-A/dashboard')
        assert response.status_code == 200
        assert b'Import Dashboard' in response.data

    def test_validation_route_still_works(self, client):
        """Test that /validation route still works (Step 3 regression check)."""
        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        assert b'Validation' in response.data

    def test_duplicates_route_untouched(self, client):
        """Test that duplicates route was not modified."""
        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200

    def test_households_route_untouched(self, client):
        """Test that households route was not modified."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_audit_route_untouched(self, client):
        """Test that audit route was not modified."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert response.status_code == 200

    def test_exports_route_untouched(self, client):
        """Test that exports route was not modified."""
        response = client.get('/imports/IMP-2025-0101-A/exports')
        assert response.status_code == 200
