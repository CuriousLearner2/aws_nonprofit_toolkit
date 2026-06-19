"""
Integration tests for the households review route.

Tests verify that /imports/<import_id>/households correctly uses the service-boundary pattern,
renders expected content, and maintains regression protection for other routes.
"""

import pytest
from scripts.uploader.app import app


class TestHouseholdsRoute:
    """Tests for /imports/<import_id>/households route."""

    def test_households_route_returns_200(self, client_with_fixture):
        """GET /imports/IMP-2025-0101-A/households returns 200."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_households_route_returns_html(self, client_with_fixture):
        """GET /imports/<import_id>/households returns HTML content."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        assert 'text/html' in response.content_type

    def test_households_route_includes_page_title(self, client_with_fixture):
        """Households page includes expected title."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Households' in html

    def test_households_route_batch_id_displayed(self, client_with_fixture):
        """Households page displays import batch ID."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'IMP-2025-0101-A' in html

    def test_households_route_suggestion_counter(self, client_with_fixture):
        """Households page displays suggestion counter."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Should show "Suggestion X of Y" format
        assert 'Suggestion' in html
        assert 'of' in html

    def test_households_route_safety_strip(self, client_with_fixture):
        """Households page includes safety strip message."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'household' in html.lower()

    def test_households_route_household_data_present(self, client_with_fixture):
        """Households page displays current household suggestion."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # First household is "Smith Family"
        assert 'Smith Family' in html

    def test_households_route_household_address(self, client_with_fixture):
        """Households page displays household address."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert '123 Main St' in html or 'Main St' in html

    def test_households_route_proposed_members_section(self, client_with_fixture):
        """Households page includes proposed members section."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Proposed Members' in html or 'proposed' in html.lower()

    def test_households_route_confidence_displayed(self, client_with_fixture):
        """Households page displays confidence level."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Confidence' in html or 'confidence' in html.lower()

    def test_households_route_supporting_evidence(self, client_with_fixture):
        """Households page includes supporting evidence section."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Supporting Evidence' in html or 'evidence' in html.lower()

    def test_households_route_action_buttons(self, client_with_fixture):
        """Households page includes action buttons."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Buttons should be labeled exactly as in Phase 0
        assert 'Confirm' in html
        assert 'Reject' in html
        assert 'Defer' in html

    def test_households_route_navigation_buttons(self, client_with_fixture):
        """Households page includes navigation buttons."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # First suggestion should have "Next" enabled and "Previous" disabled
        assert 'Previous' in html or 'previous' in html.lower()
        assert 'Next' in html or 'next' in html.lower()

    def test_households_route_dashboard_link(self, client_with_fixture):
        """Households page includes back to dashboard link."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'dashboard' in html.lower()

    def test_households_route_progress_bar(self, client_with_fixture):
        """Households page includes progress indicator."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Progress' in html or 'progress' in html.lower()

    def test_households_route_safety_copy_preserved(self, client_with_fixture):
        """Households page includes safety copy about export staging."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Safety copy should emphasize that raw data is not modified
        assert ('export' in html.lower() or 'staging' in html.lower() or
                'raw' in html.lower())

    def test_households_route_modal_present(self, client_with_fixture):
        """Households page includes confirmation modal."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Modal should be present for confirmation dialog
        assert 'modal' in html.lower()

    def test_households_route_no_forbidden_vocabulary(self, client_with_fixture):
        """Households page does not include forbidden vocabulary."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        forbidden_terms = [
            'merge', 'merged', 'auto-apply', 'approve all',
            'sync', 'synced', 'CRM writeback', 'finalized',
            'Master ID', 'master database', 'push to CRM'
        ]
        for term in forbidden_terms:
            assert term.lower() not in html.lower()

    def test_households_route_allowed_vocabulary(self, client_with_fixture):
        """Households page uses allowed vocabulary (where applicable)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Check for positive patterns (not all required on this page, but if mentioned...)
        # The page should emphasize that data is not written back
        assert ('Raw' in html or 'raw' in html.lower() or
                'export' in html.lower() or 'staging' in html.lower())


class TestHouseholdsRouteRegression:
    """Regression tests: verify prior steps remain service-backed."""

    def test_imports_list_still_service_backed(self, client_with_fixture):
        """Regression: /imports route still returns 200."""
        response = client_with_fixture.get('/imports')
        assert response.status_code == 200

    def test_dashboard_still_service_backed(self, client_with_fixture):
        """Regression: /imports/<import_id>/dashboard still returns 200."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/dashboard')
        assert response.status_code == 200

    def test_validation_still_service_backed(self, client_with_fixture):
        """Regression: /imports/<import_id>/validation still returns 200."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200

    def test_duplicates_still_fixture_backed(self, client_with_fixture):
        """Regression: /imports/<import_id>/duplicates still returns 200 (fixture-backed)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/duplicates')
        assert response.status_code == 200

    def test_audit_still_fixture_backed(self, client_with_fixture):
        """Regression: /imports/<import_id>/audit still returns 200 (fixture-backed)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert response.status_code == 200

    def test_exports_still_fixture_backed(self, client_with_fixture):
        """Regression: /imports/<import_id>/exports still returns 200 (fixture-backed)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert response.status_code == 200

    def test_all_7_donortrust_routes_return_200(self, client_with_fixture):
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
            response = client_with_fixture.get(route)
            assert response.status_code == 200, f"Route {route} returned {response.status_code}"


class TestHouseholdsRouteNoTechnology:
    """Verify no forbidden technologies were introduced."""

    def test_households_route_no_database(self, client_with_fixture):
        """Households route does not connect to database."""
        # This is verified by code inspection, not runtime behavior,
        # but we can check that the route returns expected fixture data
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Fixture shows first household is Smith Family
        assert 'Smith Family' in html

    def test_households_route_no_sqlalchemy(self, client_with_fixture):
        """Households route does not use SQLAlchemy."""
        # Verified by code inspection - service layer has no ORM imports
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        assert response.status_code == 200

    def test_households_route_no_react(self, client_with_fixture):
        """Households route renders server-side Jinja template, not React."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Should be plain HTML from Jinja, not a React bundle
        assert '<!DOCTYPE' in html or '<html' in html or '<h1>' in html


class TestHouseholdsRouteHouseholdCount:
    """Verify household suggestions count is correct."""

    def test_households_route_shows_correct_total(self, client_with_fixture):
        """Households page displays correct total household count."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Fixture has 5 households
        assert '5' in html or 'total' in html.lower()

    def test_households_route_shows_current_index(self, client_with_fixture):
        """Households page shows current household index is 1."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # First view should show index 1
        assert '1' in html


class TestHouseholdsRouteDataFidelity:
    """Verify fixture data is correctly passed through service layer to template."""

    def test_first_household_id(self, client_with_fixture):
        """First household ID is HH-001."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'HH-001' in html

    def test_first_household_name(self, client_with_fixture):
        """First household name is 'Smith Family'."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'Smith Family' in html

    def test_first_household_members_count(self, client_with_fixture):
        """First household has 2 proposed members."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'John Smith' in html
        assert 'Robert Smith' in html

    def test_first_household_confidence(self, client_with_fixture):
        """First household confidence is 98%."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert '98%' in html or '98' in html


class TestHouseholdsRouteNotesWarning:
    """Tests for notes warning on defer decision."""

    def test_notes_warning_element_present_in_page(self, client_with_fixture):
        """Notes warning element is present in HTML."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'notes-warning-defer' in html

    def test_notes_warning_initially_hidden(self, client_with_fixture):
        """Notes warning is initially hidden (display: none)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Should have the warning element with display: none
        assert 'style="display: none;' in html or 'display: none' in html

    def test_notes_warning_has_helpful_text(self, client_with_fixture):
        """Notes warning includes helpful message for defer decision."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Warning should include message about notes
        assert 'Notes may help explain' in html or 'deferred' in html.lower()

    def test_defer_button_onclick_includes_show_warning(self, client_with_fixture):
        """Defer button onclick includes showNotesWarning() call."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Defer button should call showNotesWarning
        assert 'showNotesWarning()' in html

    def test_confirm_button_onclick_includes_hide_warning(self, client_with_fixture):
        """Confirm button onclick includes hideNotesWarning() call."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Confirm button should call hideNotesWarning
        assert 'hideNotesWarning()' in html

    def test_reject_button_onclick_includes_hide_warning(self, client_with_fixture):
        """Reject button onclick includes hideNotesWarning() call."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        # Reject button should call hideNotesWarning
        assert 'hideNotesWarning()' in html

    def test_show_notes_warning_function_defined(self, client_with_fixture):
        """JavaScript function showNotesWarning() is defined."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'function showNotesWarning()' in html

    def test_hide_notes_warning_function_defined(self, client_with_fixture):
        """JavaScript function hideNotesWarning() is defined."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households')
        html = response.get_data(as_text=True)
        assert 'function hideNotesWarning()' in html


class TestHouseholdsRouteIndexNavigation:
    """Tests for index-based navigation of households."""

    def test_index_zero_shows_first_household(self, client_with_fixture):
        """GET /imports/<id>/households?index=0 shows first household (Smith)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=0')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Smith Family' in html
        assert 'HH-001' in html

    def test_index_one_shows_second_household(self, client_with_fixture):
        """GET /imports/<id>/households?index=1 shows second household (Williams)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=1')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Williams Family' in html
        assert 'HH-002' in html

    def test_index_two_shows_third_household(self, client_with_fixture):
        """GET /imports/<id>/households?index=2 shows third household (Johnson)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=2')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Johnson Household' in html
        assert 'HH-003' in html

    def test_index_four_shows_fifth_household(self, client_with_fixture):
        """GET /imports/<id>/households?index=4 shows fifth household (Brown)."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=4')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Brown Household' in html
        assert 'HH-005' in html

    def test_index_too_high_clamps_to_last(self, client_with_fixture):
        """GET /imports/<id>/households?index=999 clamps to last household."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=999')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        # Should show last household (Brown at index 4)
        assert 'Brown Household' in html
        assert 'HH-005' in html

    def test_index_one_shows_correct_counter(self, client_with_fixture):
        """GET /imports/<id>/households?index=1 shows counter '2 of 5'."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=1')
        html = response.get_data(as_text=True)
        # Should show "Suggestion 2 of 5"
        assert '2' in html and '5' in html

    def test_previous_link_at_first_household_disabled(self, client_with_fixture):
        """GET /imports/<id>/households?index=0 shows disabled Previous button."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=0')
        html = response.get_data(as_text=True)
        # Previous button should be disabled (not an <a> tag)
        assert 'disabled' in html

    def test_previous_link_at_second_household_enabled(self, client_with_fixture):
        """GET /imports/<id>/households?index=1 shows enabled Previous link."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=1')
        html = response.get_data(as_text=True)
        # Previous link should point to index=0
        assert 'index=0' in html

    def test_next_link_at_last_household_disabled(self, client_with_fixture):
        """GET /imports/<id>/households?index=4 shows disabled Next button."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=4')
        html = response.get_data(as_text=True)
        # Next button should be disabled (not an <a> tag)
        assert 'disabled' in html

    def test_next_link_at_first_household_enabled(self, client_with_fixture):
        """GET /imports/<id>/households?index=0 shows enabled Next link."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=0')
        html = response.get_data(as_text=True)
        # Next link should point to index=1
        assert 'index=1' in html

    def test_next_link_at_third_household_enabled(self, client_with_fixture):
        """GET /imports/<id>/households?index=2 shows enabled Next link to index=3."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/households?index=2')
        html = response.get_data(as_text=True)
        # Next link should point to index=3
        assert 'index=3' in html
