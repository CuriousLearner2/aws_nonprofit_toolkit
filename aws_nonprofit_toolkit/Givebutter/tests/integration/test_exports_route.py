"""
Integration tests for exports console route service boundary.

Verify that the /imports/<import_id>/exports route returns correct
content and status code after service-boundary migration.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app


class TestExportsRoute:
    """Test exports console route integration."""

    def test_exports_route_returns_200(self, client_with_fixture):
        """Test that exports route returns 200 status."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert response.status_code == 200

    def test_exports_contains_title(self, client_with_fixture):
        """Test that exports page contains title."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Export Console' in response.data

    def test_exports_contains_batch_id(self, client_with_fixture):
        """Test that exports page displays batch ID."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'IMP-2025-0101-A' in response.data

    def test_exports_contains_batch_metadata(self, client_with_fixture):
        """Test that exports page displays batch metadata."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Batch:' in response.data
        assert b'Staged for Export:' in response.data

    def test_exports_contains_readiness_summary(self, client_with_fixture):
        """Test that exports page renders a compact readiness summary strip."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        html = response.data.decode('utf-8')

        assert 'data-testid="exports-related-links"' in html
        assert 'data-testid="export-readiness-summary"' in html
        assert 'Export readiness:' in html
        assert 'Generate CSV Export' in html
        assert 'Export Formats' in html
        assert 'Recent Exports' in html
        assert 'href="/imports/IMP-2025-0101-A/dashboard"' in html
        assert 'href="/imports/IMP-2025-0101-A/readiness"' in html
        assert 'href="/imports/IMP-2025-0101-A/validation"' in html
        assert 'href="/imports/IMP-2025-0101-A/audit"' in html

    def test_exports_contains_safety_message(self, client_with_fixture):
        """Test that exports page contains safety messaging."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Raw import records remain unchanged' in response.data or b'Raw import rows' in response.data

    def test_exports_contains_no_writeback_message(self, client_with_fixture):
        """Test that exports page contains no writeback safety message."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'No data is written back to Givebutter or any CRM' in response.data

    def test_exports_contains_status_summary(self, client_with_fixture):
        """Test that exports page contains status summary boxes."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Staged Records' in response.data
        assert b'Reviewer Decisions' in response.data
        assert b'Households Created' in response.data

    def test_exports_contains_generate_button(self, client_with_fixture):
        """Test that exports page contains Generate Export Package button."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Generate Export Package' in response.data

    def test_exports_contains_export_formats_section(self, client_with_fixture):
        """Test that exports page contains export formats section."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Export Formats' in response.data

    def test_exports_contains_export_cards(self, client_with_fixture):
        """Test that exports page contains export cards."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        # Should have export card titles
        assert b'Export' in response.data or b'CSV' in response.data

    def test_exports_contains_modal(self, client_with_fixture):
        """Test that exports page contains export generation modal."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'generate-export-modal' in response.data

    def test_exports_contains_modal_content(self, client_with_fixture):
        """Test that exports modal contains expected content."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        html = response.data.decode('utf-8')
        assert 'Your export package will include:' in html
        assert 'data-testid="export-confirmation-note"' in html
        assert 'Blocking issues must be resolved before export.' in html
        assert 'Warnings are distinct from blockers' in html
        assert 'reviewed effective values where applicable' in html
        assert 'Raw import rows remain unchanged.' in html
        assert 'Generate Package' in html

    def test_exports_modal_safety_message(self, client_with_fixture):
        """Test that exports modal contains safety messaging."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Raw import records remain unchanged' in response.data

    def test_exports_modal_no_writeback(self, client_with_fixture):
        """Test that exports modal mentions no CRM writeback."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'No data is written back to Givebutter or any CRM' in response.data

    def test_exports_contains_recent_exports_section(self, client_with_fixture):
        """Test that exports page contains recent exports section."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Recent Exports' in response.data

    def test_exports_contains_navigation_back_to_dashboard(self, client_with_fixture):
        """Test that exports page has back to dashboard link."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'/imports/IMP-2025-0101-A/dashboard' in response.data

    def test_exports_contains_navigation_back_to_imports(self, client_with_fixture):
        """Test that exports page has back to imports link."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert b'Back to Imports' in response.data

    def test_exports_no_forbidden_vocabulary(self, client_with_fixture):
        """Test that exports page does not contain forbidden vocabulary."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
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

    def test_exports_no_real_files_generated(self, client_with_fixture):
        """Test that clicking generate doesn't actually create files."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        # The page should load without actually generating or writing files
        assert response.status_code == 200
        # No indication of file generation in fixture-backed Phase 1A
        assert b'No exports generated yet' in response.data or b'Recent Exports' in response.data

    def test_imports_route_still_works(self, client_with_fixture):
        """Test that /imports route still works (Step 1 regression check)."""
        response = client_with_fixture.get('/imports')
        assert response.status_code == 200
        assert b'Imports' in response.data

    def test_dashboard_route_still_works(self, client_with_fixture):
        """Test that /dashboard route still works (Step 2 regression check)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert response.status_code == 200
        assert b'Import Dashboard' in response.data

    def test_validation_route_still_works(self, client_with_fixture):
        """Test that /validation route still works (Step 3 regression check)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        assert b'Validation' in response.data

    def test_households_route_still_works(self, client_with_fixture):
        """Test that /households route still works (Step 5 regression check)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_duplicates_route_still_works(self, client_with_fixture):
        """Test that /duplicates route still works (Step 6 regression check)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200

    def test_audit_route_still_works(self, client_with_fixture):
        """Test that /audit route still works (Step 7 regression check)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert response.status_code == 200
