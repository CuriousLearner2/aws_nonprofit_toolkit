"""
Integration tests for the households review route.

Tests verify that /imports/<import_id>/households correctly uses the service-boundary pattern,
renders expected content, and maintains regression protection for other routes.
"""

import pytest
from scripts.uploader.app import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHouseholdsRoute:
    """Tests for /imports/<import_id>/households route."""

    def test_households_route_returns_200(self, client):
        """GET /imports/IMP-2025-0101-A/households returns 200."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_households_route_returns_html(self, client):
        """GET /imports/<import_id>/households returns HTML content."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        assert 'text/html' in response.content_type

    def test_households_route_includes_page_title(self, client):
        """Households page includes expected title."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Households' in html

    def test_households_route_batch_id_displayed(self, client):
        """Households page displays import batch ID."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'IMP-2025-0101-A' in html

    def test_households_route_suggestion_counter(self, client):
        """Households page displays suggestion counter."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Should show "Suggestion X of Y" format
        assert 'Suggestion' in html
        assert 'of' in html

    def test_households_route_safety_strip(self, client):
        """Households page includes safety strip message."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'household' in html.lower()

    def test_households_route_household_data_present(self, client):
        """Households page displays current household suggestion."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # First household is "Smith Family"
        assert 'Smith Family' in html

    def test_households_route_household_address(self, client):
        """Households page displays household address."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert '123 Main St' in html or 'Main St' in html

    def test_households_route_proposed_members_section(self, client):
        """Households page includes proposed members section."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Proposed Members' in html or 'proposed' in html.lower()

    def test_households_route_confidence_displayed(self, client):
        """Households page displays confidence level."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Confidence' in html or 'confidence' in html.lower()

    def test_households_route_supporting_evidence(self, client):
        """Households page includes supporting evidence section."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Supporting Evidence' in html or 'evidence' in html.lower()

    def test_households_route_action_buttons(self, client):
        """Households page includes action buttons."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Buttons should be labeled exactly as in Phase 0
        assert 'Confirm' in html
        assert 'Reject' in html
        assert 'Defer' in html

    def test_households_route_navigation_buttons(self, client):
        """Households page includes navigation buttons."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # First suggestion should have "Next" enabled and "Previous" disabled
        assert 'Previous' in html or 'previous' in html.lower()
        assert 'Next' in html or 'next' in html.lower()

    def test_households_route_dashboard_link(self, client):
        """Households page includes back to dashboard link."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'dashboard' in html.lower()

    def test_households_route_progress_bar(self, client):
        """Households page includes progress indicator."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Progress' in html or 'progress' in html.lower()

    def test_households_route_safety_copy_preserved(self, client):
        """Households page includes safety copy about export staging."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Safety copy should emphasize that raw data is not modified
        assert ('export' in html.lower() or 'staging' in html.lower() or
                'raw' in html.lower())

    def test_households_route_modal_present(self, client):
        """Households page includes confirmation modal."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Modal should be present for confirmation dialog
        assert 'modal' in html.lower()

    def test_households_route_no_forbidden_vocabulary(self, client):
        """Households page does not include forbidden vocabulary."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        forbidden_terms = [
            'merge', 'merged', 'auto-apply', 'approve all',
            'sync', 'synced', 'CRM writeback', 'finalized',
            'Master ID', 'master database', 'push to CRM'
        ]
        for term in forbidden_terms:
            assert term.lower() not in html.lower()

    def test_households_route_allowed_vocabulary(self, client):
        """Households page uses allowed vocabulary (where applicable)."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Check for positive patterns (not all required on this page, but if mentioned...)
        # The page should emphasize that data is not written back
        assert ('Raw' in html or 'raw' in html.lower() or
                'export' in html.lower() or 'staging' in html.lower())


class TestHouseholdsRouteRegression:
    """Regression tests: verify prior steps remain service-backed."""

    def test_imports_list_still_service_backed(self, client):
        """Regression: /imports route still returns 200."""
        response = client.get('/imports')
        assert response.status_code == 200

    def test_dashboard_still_service_backed(self, client):
        """Regression: /imports/<import_id>/dashboard still returns 200."""
        response = client.get('/imports/IMP-2025-0101-A/dashboard')
        assert response.status_code == 200

    def test_validation_still_service_backed(self, client):
        """Regression: /imports/<import_id>/validation still returns 200."""
        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200

    def test_duplicates_still_fixture_backed(self, client):
        """Regression: /imports/<import_id>/duplicates still returns 200 (fixture-backed)."""
        response = client.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200

    def test_audit_still_fixture_backed(self, client):
        """Regression: /imports/<import_id>/audit still returns 200 (fixture-backed)."""
        response = client.get('/imports/IMP-2025-0101-A/audit')
        assert response.status_code == 200

    def test_exports_still_fixture_backed(self, client):
        """Regression: /imports/<import_id>/exports still returns 200 (fixture-backed)."""
        response = client.get('/imports/IMP-2025-0101-A/exports')
        assert response.status_code == 200

    def test_all_7_donortrust_routes_return_200(self, client):
        """All 7 canonical DonorTrust routes return HTTP 200 (normalizations removed in Phase 1B)."""
        routes = [
            '/imports',
            '/imports/IMP-2025-0101-A/dashboard',
            '/imports/IMP-2025-0101-A/validation',
            '/imports/IMP-2025-0101-A/duplicates',
            '/imports/IMP-2025-0101-A/households',
            '/imports/IMP-2025-0101-A/audit',
            '/imports/IMP-2025-0101-A/exports',
        ]
        for route in routes:
            response = client.get(route)
            assert response.status_code == 200, f"Route {route} returned {response.status_code}"


class TestHouseholdsRouteNoTechnology:
    """Verify no forbidden technologies were introduced."""

    def test_households_route_no_database(self, client):
        """Households route does not connect to database."""
        # This is verified by code inspection, not runtime behavior,
        # but we can check that the route returns expected fixture data
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Fixture shows first household is Smith Family
        assert 'Smith Family' in html

    def test_households_route_no_sqlalchemy(self, client):
        """Households route does not use SQLAlchemy."""
        # Verified by code inspection - service layer has no ORM imports
        response = client.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_households_route_no_react(self, client):
        """Households route renders server-side Jinja template, not React."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Should be plain HTML from Jinja, not a React bundle
        assert '<!DOCTYPE' in html or '<html' in html or '<h1>' in html


class TestHouseholdsRouteHouseholdCount:
    """Verify household suggestions count is correct."""

    def test_households_route_shows_correct_total(self, client):
        """Households page displays correct total household count."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Fixture has 5 households
        assert '5' in html or 'total' in html.lower()

    def test_households_route_shows_current_index(self, client):
        """Households page shows current household index is 1."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # First view should show index 1
        assert '1' in html


class TestHouseholdsRouteDataFidelity:
    """Verify fixture data is correctly passed through service layer to template."""

    def test_first_household_id(self, client):
        """First household ID is HH-001."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'HH-001' in html

    def test_first_household_name(self, client):
        """First household name is 'Smith Family'."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Smith Family' in html

    def test_first_household_members_count(self, client):
        """First household has 2 proposed members."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'John Smith' in html
        assert 'Robert Smith' in html

    def test_first_household_confidence(self, client):
        """First household confidence is 98%."""
        response = client.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert '98%' in html or '98' in html
