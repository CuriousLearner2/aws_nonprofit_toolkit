"""
Integration tests for the normalizations review route.

Tests verify that /imports/<import_id>/normalizations correctly uses the service-boundary pattern,
renders expected content, maintains data integrity, and preserves audit trail semantics.
"""

import pytest
from scripts.uploader.app import app
from scripts.householder.database_models import (
    get_session,
    create_db_engine,
    ReviewItem,
    ReviewDecision,
    AuditLogRecord,
)


class TestNormalizationsRoute:
    """Tests for /imports/<import_id>/normalizations route."""

    def test_normalizations_route_returns_200_with_database(self, client_with_database):
        """GET /imports/IMP-TEST-001/normalizations returns 200."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        assert response.status_code == 200

    def test_normalizations_route_returns_html(self, client_with_database):
        """GET /imports/<import_id>/normalizations returns HTML content."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        assert 'text/html' in response.content_type

    def test_normalizations_page_includes_title(self, client_with_database):
        """Normalizations page includes expected title."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'Normalizations' in html

    def test_normalizations_page_displays_batch_id(self, client_with_database):
        """Normalizations page displays import batch ID."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'IMP-TEST-001' in html

    def test_normalizations_page_displays_suggestion_counter(self, client_with_database):
        """Normalizations page displays suggestion counter."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        # Should show "Suggestion X of Y" format
        assert 'Suggestion' in html
        assert 'of' in html

    def test_normalizations_page_includes_safety_strip(self, client_with_database):
        """Normalizations page includes safety strip message."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'Raw import rows remain unchanged' in html

    def test_normalizations_page_shows_summary_strip(self, client_with_database):
        """Normalizations page renders a compact suggestion summary strip."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)

        assert 'data-testid="normalization-summary-strip"' in html
        assert 'data-summary-metric="contact"' in html
        assert 'data-summary-metric="field"' in html
        assert 'data-summary-metric="reason"' in html
        assert 'data-summary-metric="status"' in html
        assert 'data-summary-contact="Jon Smith"' in html
        assert 'data-summary-field="Email"' in html
        assert 'data-summary-reason="Email standardization"' in html
        assert 'data-summary-status="Pending"' in html
        assert 'Suggested for' in html
        assert 'Field' in html
        assert 'Reason' in html
        assert 'Current status' in html
        assert 'Jon Smith' in html
        assert 'Email' in html
        assert 'Email standardization' in html
        assert 'Pending' in html

    def test_normalizations_page_original_value_label(self, client_with_database):
        """Normalizations page displays 'Original Value' label."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'Original Value' in html

    def test_normalizations_page_suggested_value_label(self, client_with_database):
        """Normalizations page displays 'Suggested Value' label."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'Suggested Value' in html

    def test_normalizations_page_action_buttons(self, client_with_database):
        """Normalizations page includes action buttons."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        # Buttons should be labeled exactly as in specification
        assert 'Accept Suggestion' in html
        assert 'Reject Suggestion' in html
        assert 'Defer' in html

    def test_normalizations_page_navigation_buttons(self, client_with_database):
        """Normalizations page includes navigation buttons."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'Previous' in html or 'previous' in html.lower()
        assert 'Next' in html or 'next' in html.lower()

    def test_normalizations_page_dashboard_link(self, client_with_database):
        """Normalizations page includes back to dashboard link."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'dashboard' in html.lower()

    def test_normalizations_page_safety_footer(self, client_with_database):
        """Normalizations page includes safety footer."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        # Safety copy should appear
        assert 'audit trail' in html.lower()

    def test_normalizations_page_notes_textarea(self, client_with_database):
        """Normalizations page includes notes textarea."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'Notes (optional)' in html

    def test_normalizations_page_defer_advisory(self, client_with_database):
        """Normalizations page displays defer advisory text."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        assert 'explain why' in html.lower()

    def test_normalizations_empty_state(self, client_with_database, initialized_test_db):
        """Normalizations page shows completion message when no suggestions pending."""
        # Create a new batch with no normalization items
        from scripts.householder.database_models import ImportBatch
        from datetime import datetime

        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        empty_batch = ImportBatch(
            id='IMP-EMPTY-001',
            filename='empty_batch.csv',
            status='pending',
            raw_row_count=0,
            upload_timestamp=datetime.now(),
        )
        session.add(empty_batch)
        session.commit()
        session.close()

        response = client_with_database.get('/imports/IMP-EMPTY-001/normalizations')
        html = response.get_data(as_text=True)
        # Should show completion message
        assert 'All normalizations reviewed' in html or 'Suggestion 0 of 0' in html

    def test_normalizations_page_no_forbidden_vocabulary(self, client_with_database):
        """Normalizations page does not include forbidden vocabulary."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations')
        html = response.get_data(as_text=True)
        forbidden_terms = [
            'merge', 'merged', 'auto-apply', 'approve all',
            'sync', 'synced', 'CRM writeback', 'finalized',
            'Master ID', 'master database', 'push to CRM'
        ]
        for term in forbidden_terms:
            assert term.lower() not in html.lower()


class TestNormalizationsDecisions:
    """Tests for normalizations decision persistence."""

    def test_accept_normalization_decision_persists(self, client_with_database, initialized_test_db):
        """Accept normalization decision is persisted to database."""
        from scripts.householder.database_models import ReviewItem
        import json

        # Get first normalization review item
        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        if norm_item:
            # Simulate accept decision
            decision = ReviewDecision(
                batch_id='IMP-TEST-001',
                review_item_id=norm_item.id,
                decision='accept_normalization',
                reviewer='Test Reviewer',
            )
            session.add(decision)
            session.commit()

            # Verify decision was persisted
            persisted_decision = session.query(ReviewDecision).filter_by(
                review_item_id=norm_item.id
            ).first()
            assert persisted_decision is not None
            assert persisted_decision.decision == 'accept_normalization'

        session.close()

    def test_post_accept_normalization_decision(self, client_with_database, initialized_test_db):
        """POST /imports/<import_id>/normalizations/<review_item_id>/decision accepts normalization."""
        from scripts.householder.database_models import ReviewItem

        # Get first normalization review item
        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        assert norm_item is not None, "Test data should have a normalization item"
        session.close()

        # POST decision
        response = client_with_database.post(
            f'/imports/IMP-TEST-001/normalizations/{norm_item.id}/decision',
            data={'decision': 'accept_normalization'}
        )

        # Should redirect
        assert response.status_code in [302, 303], f"Expected redirect (302/303), got {response.status_code}"

        # Verify decision was persisted
        session = get_session(engine)
        persisted_decision = session.query(ReviewDecision).filter_by(
            review_item_id=norm_item.id,
            decision='accept_normalization'
        ).first()
        assert persisted_decision is not None
        session.close()

    def test_post_reject_normalization_decision(self, client_with_database, initialized_test_db):
        """POST /imports/<import_id>/normalizations/<review_item_id>/decision rejects normalization."""
        from scripts.householder.database_models import ReviewItem

        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).offset(1).first()

        if not norm_item:
            pytest.skip("Test requires at least 2 normalization items")

        session.close()

        # POST reject decision
        response = client_with_database.post(
            f'/imports/IMP-TEST-001/normalizations/{norm_item.id}/decision',
            data={'decision': 'reject_normalization'}
        )

        assert response.status_code in [302, 303]

        # Verify decision was persisted
        session = get_session(engine)
        persisted_decision = session.query(ReviewDecision).filter_by(
            review_item_id=norm_item.id,
            decision='reject_normalization'
        ).first()
        assert persisted_decision is not None
        session.close()

    def test_post_defer_normalization_decision(self, client_with_database, initialized_test_db):
        """POST /imports/<import_id>/normalizations/<review_item_id>/decision defers normalization."""
        from scripts.householder.database_models import ReviewItem

        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).offset(2).first()

        if not norm_item:
            pytest.skip("Test requires at least 3 normalization items")

        session.close()

        # POST defer decision with optional notes
        response = client_with_database.post(
            f'/imports/IMP-TEST-001/normalizations/{norm_item.id}/decision',
            data={
                'decision': 'defer',
                'notes': 'Need to verify with source system'
            }
        )

        assert response.status_code in [302, 303]

        # Verify decision was persisted with notes
        session = get_session(engine)
        persisted_decision = session.query(ReviewDecision).filter_by(
            review_item_id=norm_item.id,
            decision='defer'
        ).first()
        assert persisted_decision is not None
        # Verify notes are in reviewed_values
        assert persisted_decision.reviewed_values is not None
        if isinstance(persisted_decision.reviewed_values, dict):
            assert 'notes' in persisted_decision.reviewed_values
            assert persisted_decision.reviewed_values['notes'] == 'Need to verify with source system'
        session.close()

    def test_post_invalid_decision_returns_400(self, client_with_database, initialized_test_db):
        """POST with invalid decision returns 400."""
        from scripts.householder.database_models import ReviewItem

        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        assert norm_item is not None
        session.close()

        # POST with invalid decision
        response = client_with_database.post(
            f'/imports/IMP-TEST-001/normalizations/{norm_item.id}/decision',
            data={'decision': 'invalid_decision'}
        )

        assert response.status_code == 400
        assert 'error' in response.get_data(as_text=True).lower()

    def test_post_nonexistent_item_returns_400(self, client_with_database):
        """POST with nonexistent review_item_id returns 400."""
        response = client_with_database.post(
            f'/imports/IMP-TEST-001/normalizations/99999/decision',
            data={'decision': 'accept_normalization'}
        )

        assert response.status_code == 400
        assert 'error' in response.get_data(as_text=True).lower()

    def test_reject_normalization_decision_persists(self, client_with_database, initialized_test_db):
        """Reject normalization decision is persisted to database."""
        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        if norm_item:
            decision = ReviewDecision(
                batch_id='IMP-TEST-001',
                review_item_id=norm_item.id,
                decision='reject_normalization',
                reviewer='Test Reviewer',
            )
            session.add(decision)
            session.commit()

            persisted_decision = session.query(ReviewDecision).filter_by(
                review_item_id=norm_item.id
            ).first()
            assert persisted_decision is not None
            assert persisted_decision.decision == 'reject_normalization'

        session.close()

    def test_defer_normalization_decision_persists(self, client_with_database, initialized_test_db):
        """Defer normalization decision is persisted."""
        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        if norm_item:
            decision = ReviewDecision(
                batch_id='IMP-TEST-001',
                review_item_id=norm_item.id,
                decision='defer',
                reviewer='Test Reviewer',
            )
            session.add(decision)
            session.commit()

            persisted_decision = session.query(ReviewDecision).filter_by(
                review_item_id=norm_item.id
            ).first()
            assert persisted_decision is not None
            assert persisted_decision.decision == 'defer'

        session.close()


class TestNormalizationsRawDataIntegrity:
    """Tests verify raw import data remains immutable."""

    def test_raw_data_unchanged_after_accept(self, client_with_database, initialized_test_db):
        """Raw import data remains unchanged after accepting normalization."""
        from scripts.householder.database_models import RawImportRow

        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        # Get raw row before decision
        raw_rows_before = session.query(RawImportRow).filter_by(
            batch_id='IMP-TEST-001'
        ).all()

        row_count_before = len(raw_rows_before)

        # Simulate decision
        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        if norm_item:
            decision = ReviewDecision(
                batch_id='IMP-TEST-001',
                review_item_id=norm_item.id,
                decision='accept_normalization',
            )
            session.add(decision)
            session.commit()

        # Verify raw data is unchanged
        raw_rows_after = session.query(RawImportRow).filter_by(
            batch_id='IMP-TEST-001'
        ).all()

        assert len(raw_rows_after) == row_count_before

        session.close()

    def test_raw_data_unchanged_after_reject(self, client_with_database, initialized_test_db):
        """Raw import data remains unchanged after rejecting normalization."""
        from scripts.householder.database_models import RawImportRow

        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        raw_rows_before = session.query(RawImportRow).filter_by(
            batch_id='IMP-TEST-001'
        ).all()

        row_data_before = [row.raw_csv_data for row in raw_rows_before]

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        if norm_item:
            decision = ReviewDecision(
                batch_id='IMP-TEST-001',
                review_item_id=norm_item.id,
                decision='reject_normalization',
            )
            session.add(decision)
            session.commit()

        raw_rows_after = session.query(RawImportRow).filter_by(
            batch_id='IMP-TEST-001'
        ).all()

        row_data_after = [row.raw_csv_data for row in raw_rows_after]

        assert row_data_before == row_data_after

        session.close()


class TestNormalizationsAuditTrail:
    """Tests verify audit trail records decisions."""

    def test_normalization_decision_in_audit_log(self, client_with_database, initialized_test_db):
        """Normalization decision is recorded in audit log."""
        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        norm_item = session.query(ReviewItem).filter(
            ReviewItem.batch_id == 'IMP-TEST-001',
            ReviewItem.item_type == 'normalization'
        ).first()

        if norm_item:
            decision = ReviewDecision(
                batch_id='IMP-TEST-001',
                review_item_id=norm_item.id,
                decision='accept_normalization',
                reviewer='Alice Smith',
            )
            session.add(decision)
            session.flush()

            audit_record = AuditLogRecord(
                batch_id='IMP-TEST-001',
                action_type='decision_recorded',
                actor='Alice Smith',
                item_id=norm_item.id,
                decision_id=decision.id,
                details={'decision': 'accepted normalization suggestion'},
            )
            session.add(audit_record)
            session.commit()

            persisted_audit = session.query(AuditLogRecord).filter(
                AuditLogRecord.batch_id == 'IMP-TEST-001',
                AuditLogRecord.action_type == 'decision_recorded',
                AuditLogRecord.decision_id == decision.id
            ).first()

            assert persisted_audit is not None
            assert persisted_audit.actor == 'Alice Smith'
            assert persisted_audit.item_id == norm_item.id

        session.close()


class TestNormalizationsNavigation:
    """Tests for navigation between suggestions."""

    def test_normalizations_first_suggestion_previous_disabled(self, client_with_database):
        """First suggestion has previous button disabled."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations?index=0')
        html = response.get_data(as_text=True)
        # Previous button should exist but be disabled
        assert 'Previous' in html
        assert 'disabled' in html

    def test_normalizations_navigation_index_parameter(self, client_with_database):
        """Normalizations route respects index parameter."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations?index=0')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        # Should show Suggestion 1 of X
        assert 'Suggestion 1 of' in html

    def test_normalizations_negative_index_clamped_to_zero(self, client_with_database):
        """Negative index is clamped to 0."""
        response = client_with_database.get('/imports/IMP-TEST-001/normalizations?index=-5')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        # Should show first suggestion despite negative index
        assert 'Suggestion 1 of' in html


class TestNormalizationsRegression:
    """Regression tests: verify prior routes remain unaffected."""

    def test_imports_list_still_returns_200(self, client_with_database):
        """Regression: /imports route still returns 200."""
        response = client_with_database.get('/imports')
        assert response.status_code == 200

    def test_dashboard_still_returns_200(self, client_with_database):
        """Regression: /imports/<import_id>/dashboard still returns 200."""
        response = client_with_database.get('/imports/IMP-TEST-001/dashboard')
        assert response.status_code == 200

    def test_validation_still_returns_200(self, client_with_database):
        """Regression: /imports/<import_id>/validation still returns 200."""
        response = client_with_database.get('/imports/IMP-TEST-001/validation')
        assert response.status_code == 200

    def test_duplicates_still_returns_200(self, client_with_database):
        """Regression: /imports/<import_id>/duplicates still returns 200."""
        response = client_with_database.get('/imports/IMP-TEST-001/duplicates')
        assert response.status_code == 200

    def test_households_still_returns_200(self, client_with_database):
        """Regression: /imports/<import_id>/households still returns 200."""
        response = client_with_database.get('/imports/IMP-TEST-001/households')
        assert response.status_code == 200

    def test_audit_still_returns_200(self, client_with_database):
        """Regression: /imports/<import_id>/audit still returns 200."""
        response = client_with_database.get('/imports/IMP-TEST-001/audit')
        assert response.status_code == 200

    def test_exports_still_returns_200(self, client_with_database):
        """Regression: /imports/<import_id>/exports still returns 200."""
        response = client_with_database.get('/imports/IMP-TEST-001/exports')
        assert response.status_code == 200

    def test_all_8_donortrust_routes_return_200(self, client_with_database):
        """All 8 canonical DonorTrust routes return HTTP 200."""
        routes = [
            '/imports',
            '/imports/IMP-TEST-001/dashboard',
            '/imports/IMP-TEST-001/validation',
            '/imports/IMP-TEST-001/duplicates',
            '/imports/IMP-TEST-001/normalizations',
            '/imports/IMP-TEST-001/households',
            '/imports/IMP-TEST-001/audit',
            '/imports/IMP-TEST-001/exports',
        ]
        for route in routes:
            response = client_with_database.get(route)
            assert response.status_code == 200, f"Route {route} returned {response.status_code}"

    def test_multi_contact_same_field_normalization_export(self, client_with_database, initialized_test_db):
        """
        Regression: Multi-contact same-field normalization export.

        Scenario:
        - Contact A (Jon Smith) email normalization: accepted
        - Contact B (John Smith Jr.) phone normalization: rejected
        - Export must show Contact A with normalized email
        - Export must show Contact B with original phone (unchanged)
        """
        from scripts.householder.export_preview_service import build_export_preview

        # Use the test database
        engine = create_db_engine(initialized_test_db)
        session = get_session(engine)

        try:
            # Get normalization review items from the test database
            batch_id = 'IMP-TEST-001'
            normalization_items = session.query(ReviewItem).filter(
                ReviewItem.batch_id == batch_id,
                ReviewItem.item_type == 'normalization'
            ).all()

            # Should have exactly 2 normalizations from seed data
            assert len(normalization_items) == 2, f"Expected 2 normalizations, got {len(normalization_items)}"

            # Get the first two normalizations (email and phone)
            email_norm = normalization_items[0]
            phone_norm = normalization_items[1]

            # Accept the email normalization
            decision1 = ReviewDecision(
                batch_id=batch_id,
                review_item_id=email_norm.id,
                decision='accept_normalization',
                reviewer='Test Reviewer',
                reviewed_values={'field': 'email', 'normalized_value': 'jon_smith@email.com'}
            )
            session.add(decision1)

            # Reject the phone normalization
            decision2 = ReviewDecision(
                batch_id=batch_id,
                review_item_id=phone_norm.id,
                decision='reject_normalization',
                reviewer='Test Reviewer',
                reviewed_values={'field': 'phone'}
            )
            session.add(decision2)
            session.commit()

            # Build export preview using the test database
            preview = build_export_preview(batch_id, config={'GIVEBUTTER_DATABASE_URL': initialized_test_db})

            # Verify export has 5 rows (matching seed data: 5 contacts)
            assert len(preview.export_rows) == 5, f"Expected 5 export rows, got {len(preview.export_rows)}"

            # Find Contact A (Jon Smith, should have normalized email)
            jon_row = next((r for r in preview.export_rows if r.first_name == 'Jon'), None)
            assert jon_row is not None, "Jon Smith not found in export"
            assert jon_row.email == 'jon_smith@email.com', \
                f"Jon's email should be normalized to 'jon_smith@email.com', got {jon_row.email}"

            # Find Contact B (John Smith Jr., should have original phone)
            john_jr_row = next((r for r in preview.export_rows if r.first_name == 'John' and
                               r.last_name == 'Smith Jr.'), None)
            assert john_jr_row is not None, "John Smith Jr. not found in export"
            # Original phone from seed data is "(555) 111-2222"
            assert john_jr_row.phone == '(555) 111-2222', \
                f"John Jr.'s phone should remain original '(555) 111-2222', got {john_jr_row.phone}"

        finally:
            session.close()
