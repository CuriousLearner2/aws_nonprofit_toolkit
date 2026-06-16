"""
Integration tests for audit log route service boundary.

Verify that the /imports/<import_id>/audit route returns correct
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


class TestAuditRoute:
    """Test audit log route integration."""

    def test_audit_route_returns_200(self, client):
        """Test that audit route returns 200 status."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert response.status_code == 200

    def test_audit_contains_title(self, client):
        """Test that audit page contains title."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'Audit Log' in response.data

    def test_audit_contains_batch_id(self, client):
        """Test that audit page displays batch ID."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'IMP-2025-0101-A' in response.data

    def test_audit_contains_batch_metadata(self, client):
        """Test that audit page displays batch metadata."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'Batch:' in response.data
        assert b'Total Entries:' in response.data

    def test_audit_contains_safety_strip(self, client):
        """Test that audit page contains safety messaging."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'immutable' in response.data or b'compliance' in response.data

    def test_audit_contains_filter_control(self, client):
        """Test that audit page contains filter dropdown."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'action-filter' in response.data

    def test_audit_contains_export_button(self, client):
        """Test that audit page contains export button."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'Export' in response.data

    def test_audit_contains_table_headers(self, client):
        """Test that audit page contains table headers."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'Timestamp' in response.data
        assert b'Action' in response.data
        assert b'Details' in response.data
        assert b'Reviewer' in response.data

    def test_audit_contains_audit_entries(self, client):
        """Test that audit page contains audit entries."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        # Should have entries with reviewer names
        assert b'Sarah Lee' in response.data or b'James Martinez' in response.data

    def test_audit_contains_navigation_back_to_dashboard(self, client):
        """Test that audit page has back to dashboard link."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'/imports/IMP-2025-0101-A/dashboard' in response.data

    def test_audit_contains_navigation_back_to_imports(self, client):
        """Test that audit page has back to imports link."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert b'Back to Imports' in response.data

    def test_audit_no_forbidden_vocabulary(self, client):
        """Test that audit page does not contain forbidden vocabulary."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
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

    def test_households_route_still_works(self, client):
        """Test that /households route still works (Step 5 regression check)."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_duplicates_route_still_works(self, client):
        """Test that /duplicates route still works (Step 6 regression check)."""
        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200

    def test_exports_route_untouched(self, client):
        """Test that exports route was not modified."""
        response = client.get('/imports/IMP-2025-0101-A/exports')
        assert response.status_code == 200
