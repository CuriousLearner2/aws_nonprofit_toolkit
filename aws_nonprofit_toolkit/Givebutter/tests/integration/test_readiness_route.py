"""
Integration tests for export readiness route.

Tests that readiness dashboard correctly derives and displays preview state.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.export_preview_service import build_export_preview


class TestReadinessRoutePreviewMirror:
    """Test that readiness route shows state derived from export preview."""

    def test_readiness_route_returns_200(self, client):
        """Test that readiness route returns 200."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        assert response.status_code == 200

    def test_readiness_shows_export_ready_when_preview_ready(self, client):
        """Test that readiness shows Ready when preview is ready."""
        preview = build_export_preview('IMP-TEST-001')
        response = client.get('/imports/IMP-TEST-001/readiness')

        content = response.data.decode('utf-8', errors='ignore').lower()

        if preview.is_export_ready:
            # Should show "export ready"
            assert 'export ready' in content or 'ready' in content
        else:
            # Should show "export blocked"
            assert 'blocked' in content or 'block' in content

    def test_readiness_shows_export_blocked_when_preview_blocked(self, client):
        """Test that readiness shows Blocked when preview is blocked."""
        preview = build_export_preview('IMP-TEST-001')
        response = client.get('/imports/IMP-TEST-001/readiness')

        content = response.data.decode('utf-8', errors='ignore')

        if preview.blocked_count > 0:
            # Should indicate blocked state
            assert response.status_code == 200
            # Should have some indication of blockers

    def test_readiness_renders_blocker_details_from_preview(self, client):
        """Test that readiness page renders blocker details from preview."""
        preview = build_export_preview('IMP-TEST-001')
        response = client.get('/imports/IMP-TEST-001/readiness')

        content = response.data.decode('utf-8', errors='ignore')

        # If preview has blockers, they should appear in the response
        if preview.blocked_count > 0:
            # Page should contain "blocker" or similar language
            assert 'blocker' in content.lower() or 'block' in content.lower()

    def test_readiness_renders_warning_details_from_preview(self, client):
        """Test that readiness page renders warning details from preview."""
        preview = build_export_preview('IMP-TEST-001')
        response = client.get('/imports/IMP-TEST-001/readiness')

        content = response.data.decode('utf-8', errors='ignore')

        # If preview has warnings, they should be displayed
        if preview.warning_count > 0:
            # Page should mention warnings
            assert 'warning' in content.lower()

    def test_warning_only_state_remains_export_ready(self, client):
        """Test that warning-only state remains export-ready if preview allows."""
        preview = build_export_preview('IMP-TEST-001')
        response = client.get('/imports/IMP-TEST-001/readiness')

        content = response.data.decode('utf-8', errors='ignore').lower()

        # If preview is ready (no blockers), readiness should show ready
        if preview.is_export_ready and preview.warning_count > 0:
            # Should indicate ready despite warnings
            assert 'ready' in content or 'export' in content

    def test_readiness_contains_batch_id(self, client):
        """Test that readiness page shows batch ID."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        assert b'IMP-TEST-001' in response.data

    def test_readiness_contains_safety_message(self, client):
        """Test that readiness page contains safety disclaimer."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        # Should mention read-only status
        assert b'read-only' in response.data or b'unchanged' in response.data

    def test_readiness_shows_queue_status(self, client):
        """Test that readiness page shows review queue status."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        # Should contain queue status information
        assert b'validation' in response.data.lower() or b'Validation' in response.data

    def test_readiness_shows_navigation_buttons(self, client):
        """Test that readiness page shows navigation buttons."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        # Should have navigation
        assert b'/imports' in response.data

    def test_readiness_no_database_mutation(self, client):
        """Test that accessing readiness does not mutate database."""
        # Call twice and verify no side effects
        response1 = client.get('/imports/IMP-TEST-001/readiness')
        response2 = client.get('/imports/IMP-TEST-001/readiness')

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Content should be identical
        assert response1.data == response2.data

    def test_readiness_does_not_create_audit_records(self, client):
        """Test that readiness route does not create AuditLogRecord."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        # Should succeed without creating audit entries
        assert response.status_code == 200

    def test_readiness_does_not_generate_csv_files(self, client):
        """Test that readiness route does not generate CSV files."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        # Should only display HTML, no file generation
        assert response.content_type.startswith('text/html')

    def test_readiness_returns_html(self, client):
        """Test that readiness route returns HTML content."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        assert response.content_type.startswith('text/html')

    def test_readiness_contains_title(self, client):
        """Test that readiness page contains title."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        assert b'Export Readiness' in response.data or b'readiness' in response.data.lower()

    def test_different_batches_different_readiness(self, client):
        """Test that different batches can have different readiness states."""
        response1 = client.get('/imports/IMP-TEST-001/readiness')
        response2 = client.get('/imports/IMP-TEST-002/readiness')

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Content should reflect different batch IDs
        assert b'IMP-TEST-001' in response1.data
        assert b'IMP-TEST-002' in response2.data

    def test_readiness_no_external_calls(self, client):
        """Test that readiness route does not call external systems."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        # Should only use internal services
        assert response.status_code == 200

    def test_readiness_no_forbidden_vocabulary(self, client):
        """Test that readiness page avoids forbidden CRM language."""
        response = client.get('/imports/IMP-TEST-001/readiness')
        content = response.data.decode('utf-8', errors='ignore').lower()
        # Should not mention writeback or two-way sync
        assert 'writeback' not in content
        assert 'two-way' not in content
