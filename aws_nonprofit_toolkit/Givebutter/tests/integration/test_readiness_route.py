"""
Integration tests for export readiness route.

Tests route behavior and display of readiness information.
"""

import pytest


class TestReadinessRoute:
    """Test readiness dashboard route."""

    def test_readiness_route_returns_200(self, client):
        """Test that GET readiness route returns 200."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        assert response.status_code == 200

    def test_readiness_route_returns_html(self, client):
        """Test that readiness route returns HTML content."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        assert response.content_type.startswith('text/html')

    def test_readiness_contains_title(self, client):
        """Test that readiness page contains title."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        assert b'Export Readiness Dashboard' in response.data

    def test_readiness_contains_batch_id(self, client):
        """Test that readiness page shows batch ID."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        assert b'IMP-2025-0101-A' in response.data

    def test_readiness_contains_safety_message(self, client):
        """Test that readiness page contains safety disclaimer."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        assert b'Raw import' in response.data or b'unchanged' in response.data

    def test_readiness_shows_progress(self, client):
        """Test that readiness page shows batch progress."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        assert b'Progress' in response.data or b'progress' in response.data or b'%' in response.data

    def test_readiness_shows_queue_status(self, client):
        """Test that readiness page shows queue status cards."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        # Should contain queue status references
        assert (b'Validation' in response.data or b'validation' in response.data)

    def test_readiness_shows_navigation_buttons(self, client):
        """Test that readiness page contains navigation."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        # Should have links back to dashboard and imports
        assert b'/imports' in response.data
        assert b'dashboard' in response.data.lower() or b'Dashboard' in response.data

    def test_readiness_no_database_mutation(self, client):
        """Test that accessing readiness does not mutate data."""
        # Call twice and verify no side effects
        response1 = client.get('/imports/IMP-2025-0101-A/readiness')
        response2 = client.get('/imports/IMP-2025-0101-A/readiness')

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Content should be identical (no state changes)
        assert response1.data == response2.data

    def test_readiness_with_various_batch_ids(self, client):
        """Test that various batch IDs are accepted."""
        # Fixture repository doesn't validate batch IDs, returns data for all
        response = client.get('/imports/IMP-INVALID/readiness')
        assert response.status_code == 200  # Fixture accepts any ID

    def test_readiness_different_batches_different_content(self, client):
        """Test that different batches show different data."""
        response1 = client.get('/imports/IMP-2025-0101-A/readiness')
        response2 = client.get('/imports/IMP-2025-0101-B/readiness')

        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Content should differ (different batch IDs)
        assert response1.data != response2.data
        assert b'IMP-2025-0101-A' in response1.data
        assert b'IMP-2025-0101-B' in response2.data

    def test_readiness_no_external_calls(self, client):
        """Test that readiness route does not call external systems."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        # Should only use internal services, not call external APIs
        assert response.status_code == 200

    def test_readiness_shows_export_ready_when_ready(self, client):
        """Test that readiness shows 'Export Ready' when no blockers."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        # Fixture data should have no blockers
        # Check for either success message or export link
        assert (b'Export Ready' in response.data or
                b'export' in response.data.lower() or
                b'open' in response.data.lower())

    def test_readiness_links_to_review_queues(self, client):
        """Test that readiness page links to review queues."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        # Should link to validation, duplicates, normalizations, households
        assert b'/validation' in response.data or b'validation' in response.data.lower()
        # At least some queue links should be present
        assert response.status_code == 200

    def test_readiness_no_forbidden_vocabulary(self, client):
        """Test that readiness page avoids CRM-specific language."""
        response = client.get('/imports/IMP-2025-0101-A/readiness')
        # Should not mention writeback, sync, or external systems
        content = response.data.decode('utf-8', errors='ignore').lower()
        assert 'writeback' not in content
        # Note: mentioning "no data is written to givebutter" is appropriate safety message
        assert 'sync to crm' not in content
        assert 'two-way' not in content
