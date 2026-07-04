"""
Integration tests for audit log route service boundary.

Verify that the /imports/<import_id>/audit route returns correct
content and status code after service-boundary migration.

Validation Decision Audit Visibility Tests:
- Validation override (accept_issue) decisions appear in Audit Log
- Deferred validation decisions appear in Audit Log
- Audit entries include decision details (field, issue, action)
"""

import pytest
import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewItem,
    ReviewItemSubject, ReviewDecision, AuditLogRecord, create_db_engine
)
from scripts.householder import validation_decision_service


@pytest.fixture
def database_backed_client():
    """Create Flask test client with database backend.

    Sets up temporary SQLite database with test data and configures Flask
    for database mode. Yields client and database URL for test use.
    """
    # Create temporary database
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    # Set environment for Flask
    os.environ['HOUSEHOLDER_REPOSITORY'] = 'database'
    os.environ['GIVEBUTTER_DATABASE_URL'] = database_url

    app.config['TESTING'] = True

    try:
        with app.test_client() as test_client:
            yield test_client, database_url, db_path
    finally:
        Path(db_path).unlink(missing_ok=True)


class TestAuditRoute:
    """Test audit log route integration."""

    def test_audit_route_returns_200(self, client_with_fixture):
        """Test that audit route returns 200 status."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert response.status_code == 200

    def test_audit_contains_title(self, client_with_fixture):
        """Test that audit page contains title."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'Audit Log' in response.data

    def test_audit_contains_batch_id(self, client_with_fixture):
        """Test that audit page displays batch ID."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'IMP-2025-0101-A' in response.data

    def test_audit_contains_batch_metadata(self, client_with_fixture):
        """Test that audit page displays batch metadata."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'Batch:' in response.data
        assert b'Total Entries:' in response.data

    def test_audit_contains_safety_strip(self, client_with_fixture):
        """Test that audit page contains safety messaging."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'immutable' in response.data or b'compliance' in response.data

    def test_audit_contains_filter_control(self, client_with_fixture):
        """Test that audit page contains filter dropdown."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'action-filter' in response.data

    def test_audit_action_filter_wiring_is_rendered(self, client_with_fixture):
        """Test that audit rows expose client-side filter hooks."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        html = response.data.decode('utf-8', errors='ignore')

        assert 'data-testid="audit-filter-orientation"' in html
        assert 'The action filter narrows the rows shown here.' in html
        assert 'Audit entries are append-only reviewer/system actions.' in html
        assert 'If no rows match, no matching audit events are currently displayed.' in html
        assert 'data-audit-row' in html
        assert 'data-action-key="marked-duplicate"' in html
        assert 'data-action-key="household-confirmed"' in html
        assert 'data-action-key="record-deferred"' in html
        assert 'audit-empty-state' in html
        assert "actionFilter.addEventListener('change', applyActionFilter);" in html
        assert 'row.hidden = !matches;' in html
        assert 'applyActionFilter();' in html

    def test_audit_contains_export_button(self, client_with_fixture):
        """Test that audit page contains export button."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'Export' in response.data

    def test_audit_contains_table_headers(self, client_with_fixture):
        """Test that audit page contains table headers."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'Timestamp' in response.data
        assert b'Action' in response.data
        assert b'Details' in response.data
        assert b'Reviewer' in response.data

    def test_audit_contains_audit_entries(self, client_with_fixture):
        """Test that audit page contains audit entries."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        # Should have entries with reviewer names
        assert b'Sarah Lee' in response.data or b'James Martinez' in response.data

    def test_audit_contains_navigation_back_to_dashboard(self, client_with_fixture):
        """Test that audit page has back to dashboard link."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'/imports/IMP-2025-0101-A/dashboard' in response.data

    def test_audit_contains_navigation_back_to_imports(self, client_with_fixture):
        """Test that audit page has back to imports link."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
        assert b'Back to Imports' in response.data

    def test_audit_no_forbidden_vocabulary(self, client_with_fixture):
        """Test that audit page does not contain forbidden vocabulary."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/audit')
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

    def test_exports_route_untouched(self, client_with_fixture):
        """Test that exports route was not modified."""
        response = client_with_fixture.get('/imports/IMP-2025-0101-A/exports')
        assert response.status_code == 200


class TestValidationDecisionAuditVisibility:
    """Test that validation ReviewDecision entries appear in Audit Log with details."""

    def test_validation_override_decision_appears_in_audit_log(self, database_backed_client):
        """Test that validation override (accept_issue) decision appears in Audit Log.

        Scenario:
        1. Seed ImportBatch, ImportContact, validation ReviewItem
        2. Create ReviewDecision with decision='accept_issue'
        3. Verify Audit Log contains the decision action
        4. Verify decision details are visible
        """
        test_client, database_url, db_path = database_backed_client
        batch_id = 'validation-override-audit-test'

        # Seed test data
        engine = create_db_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Create batch
            batch = ImportBatch(
                id=batch_id,
                filename='validation_override_audit.csv',
                upload_timestamp=datetime.now(timezone.utc),
                status='pending_review',
                raw_row_count=1
            )
            session.add(batch)
            session.flush()

            # Create raw row
            raw_row = RawImportRow(
                batch_id=batch_id,
                row_index=1,
                raw_csv_data={
                    'name': 'Test Contact',
                    'email': '',
                    'phone': '(555) 111-1111',
                    'address': '123 Main St',
                    'amount': '100.00'
                }
            )
            session.add(raw_row)
            session.flush()

            # Create contact
            contact = ImportContact(
                batch_id=batch_id,
                raw_import_row_id=raw_row.id,
                first_name='Test',
                last_name='Contact',
                email='',  # Missing email - validation issue
                phone='(555) 111-1111',
                address_line1='123 Main St',
                amount=100.00
            )
            session.add(contact)
            session.flush()

            # Create validation review item
            val_item = ReviewItem(
                batch_id=batch_id,
                item_type='validation',
                confidence=1.0,
                payload_json={
                    'field': 'email',
                    'issue': 'missing_email',
                    'validation_tier': 'critical'
                }
            )
            session.add(val_item)
            session.flush()

            # Link contact to validation item
            subject = ReviewItemSubject(
                review_item_id=val_item.id,
                subject_type='import_contact_snapshot',
                subject_id=contact.id,
                role='primary'
            )
            session.add(subject)
            session.flush()
            session.commit()

            val_item_id = val_item.id

        finally:
            session.close()

        # Record validation decision through service (creates AuditLogRecord)
        validation_decision_service.record_validation_decision(
            import_id=batch_id,
            review_item_id=val_item_id,
            decision='accept_issue',
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer',
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url
            }
        )

        # Fetch audit log page
        response = test_client.get(f'/imports/{batch_id}/audit')
        assert response.status_code == 200

        # Verify decision appears in audit log (as text content)
        html = response.data.decode('utf-8', errors='ignore')

        # Expected: Audit Log should show the validation override decision
        assert 'accept_issue' in html.lower() or 'validation' in html.lower() or 'accepted' in html.lower(), \
            f"Validation override decision not found in Audit Log. HTML substring: ...{html[2000:2500]}..."

        # Verify decision details are present (field, issue)
        assert 'email' in html.lower(), \
            "Decision field ('email') not visible in Audit Log"

    def test_deferred_validation_decision_appears_in_audit_log(self, database_backed_client):
        """Test that deferred validation decision appears in Audit Log.

        Scenario:
        1. Seed ImportBatch, ImportContact, validation ReviewItem
        2. Create ReviewDecision with decision='defer'
        3. Verify Audit Log contains the deferral action
        4. Verify decision details are visible
        """
        test_client, database_url, db_path = database_backed_client
        batch_id = 'validation-defer-audit-test'

        # Seed test data
        engine = create_db_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Create batch
            batch = ImportBatch(
                id=batch_id,
                filename='validation_defer_audit.csv',
                upload_timestamp=datetime.now(timezone.utc),
                status='pending_review',
                raw_row_count=1
            )
            session.add(batch)
            session.flush()

            # Create raw row
            raw_row = RawImportRow(
                batch_id=batch_id,
                row_index=1,
                raw_csv_data={
                    'name': 'Test Contact',
                    'email': '',
                    'phone': '(555) 222-2222',
                    'address': '456 Oak St',
                    'amount': '200.00'
                }
            )
            session.add(raw_row)
            session.flush()

            # Create contact
            contact = ImportContact(
                batch_id=batch_id,
                raw_import_row_id=raw_row.id,
                first_name='Test',
                last_name='Contact',
                email='',  # Missing email - validation issue
                phone='(555) 222-2222',
                address_line1='456 Oak St',
                amount=200.00
            )
            session.add(contact)
            session.flush()

            # Create validation review item
            val_item = ReviewItem(
                batch_id=batch_id,
                item_type='validation',
                confidence=1.0,
                payload_json={
                    'field': 'email',
                    'issue': 'missing_email',
                    'validation_tier': 'critical'
                }
            )
            session.add(val_item)
            session.flush()

            # Link contact to validation item
            subject = ReviewItemSubject(
                review_item_id=val_item.id,
                subject_type='import_contact_snapshot',
                subject_id=contact.id,
                role='primary'
            )
            session.add(subject)
            session.flush()
            session.commit()

            val_item_id = val_item.id

        finally:
            session.close()

        # Record validation decision through service (creates AuditLogRecord)
        validation_decision_service.record_validation_decision(
            import_id=batch_id,
            review_item_id=val_item_id,
            decision='defer',
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer',
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url
            }
        )

        # Fetch audit log page
        response = test_client.get(f'/imports/{batch_id}/audit')
        assert response.status_code == 200

        # Verify decision appears in audit log
        html = response.data.decode('utf-8', errors='ignore')

        # Expected: Audit Log should show the deferral decision
        assert 'defer' in html.lower() or 'validation' in html.lower() or 'deferred' in html.lower(), \
            f"Deferred validation decision not found in Audit Log. HTML substring: ...{html[2000:2500]}..."

        # Verify decision details are present
        assert 'email' in html.lower(), \
            "Decision field ('email') not visible in Audit Log"


class TestExportAuditVisibility:
    """Test that export_generated audit entries show confirmation details."""

    def test_export_confirmation_details_visible_in_audit_log(self, database_backed_client):
        """Test that export confirmation flags appear in Audit Log page.

        Scenario:
        1. Create ImportBatch and export directory
        2. Call generate_export_file() with specific confirmation flags
        3. Fetch Audit Log page
        4. Verify confirmation flags and deferred counts are visible
        """
        test_client, database_url, db_path = database_backed_client
        batch_id = 'export-audit-visibility-test'
        export_dir = str(Path(db_path).parent / "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Create test batch
        engine = create_db_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            batch = ImportBatch(
                id=batch_id,
                filename='export_test.csv',
                upload_timestamp=datetime.now(timezone.utc),
                status='export_ready',
                raw_row_count=0
            )
            session.add(batch)
            session.commit()
        finally:
            session.close()

        # Import here to avoid circular imports
        from scripts.householder.export_file_service import generate_export_file
        from scripts.householder.service_contracts import ExportPreviewResult, ExportRow

        # Create a mock export (with no data rows, just to test audit)
        result = generate_export_file(
            batch_id,
            export_dir,
            reviewer='export-tester',
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url
            },
            confirmed_unresolved_validations=True,
            confirmed_unresolved_households=False,
            confirmed_unresolved_duplicates=True,
        )

        # Fetch audit log page
        response = test_client.get(f'/imports/{batch_id}/audit')
        assert response.status_code == 200

        # Verify export entry appears in audit log
        html = response.data.decode('utf-8', errors='ignore')

        # Verify export_generated action is present
        assert 'export' in html.lower(), \
            "Export action not found in Audit Log"

        # Verify confirmation flags are visible in readable format
        # Should show formatted text like "✓ Validation", "✗ Households", etc.
        # OR raw JSON if formatting fails gracefully
        assert 'Export Confirmations' in html or 'confirmed_unresolved_validations' in html, \
            "Export confirmation details not visible in Audit Log"

        # Verify at least one confirmation indicator is present
        # ✓ indicates confirmed, ✗ indicates not confirmed
        assert ('Validation' in html or 'validation' in html) and \
               ('Households' in html or 'households' in html), \
            "Confirmation flags (Validation/Households) not visible in Audit Log"

        # Verify deferred counts are present
        assert ('Deferred Items' in html or 'deferred' in html.lower()) and \
               ('Validation' in html or 'validation' in html), \
            "Deferred counts not visible in Audit Log"

        # Verify reviewer name is present
        assert 'export-tester' in html.lower(), \
            "Export reviewer name not visible in Audit Log"


class TestFollowUpNotesInAuditDisplay:
    """Test that Follow Up decision notes are visible in Audit Log UI."""

    def test_follow_up_notes_visible_in_audit_html(self, database_backed_client):
        """Test that Follow Up notes appear in audit log HTML output.

        Scenario:
        1. Create ImportBatch and RawImportRow
        2. Record a row-level decision with notes via row_decision_service
        3. Verify audit log HTML contains the notes text
        """
        from scripts.householder.row_decision_service import record_row_decision

        test_client, database_url, db_path = database_backed_client
        batch_id = 'follow-up-notes-test'

        # Seed test data
        engine = create_db_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Create batch
            batch = ImportBatch(
                id=batch_id,
                filename='follow_up_notes.csv',
                upload_timestamp=datetime.now(timezone.utc),
                status='pending_review',
                raw_row_count=1
            )
            session.add(batch)
            session.flush()

            # Create raw row
            raw_row = RawImportRow(
                batch_id=batch_id,
                row_index=1,
                raw_csv_data={
                    'name': 'Contact with Follow Up',
                    'email': 'test@example.com',
                    'phone': '(555) 222-2222',
                }
            )
            session.add(raw_row)
            session.flush()

            row_id = raw_row.id
            session.commit()
            session.close()

            # Record Follow Up decision with notes
            unique_notes = f"Awaiting phone confirmation - {datetime.now(timezone.utc).isoformat()}"
            result = record_row_decision(
                batch_id=batch_id,
                raw_import_row_id=row_id,
                decision='needs_follow_up',
                notes=unique_notes,
                reviewer='test-reviewer',
                database_url=database_url
            )

            assert result['success'], f"Decision recording failed: {result}"

            # Fetch audit log page
            response = test_client.get(f'/imports/{batch_id}/audit')
            assert response.status_code == 200
            html = response.data.decode('utf-8', errors='ignore')

            # Verify notes appear in Details column
            assert unique_notes in html, \
                f"Follow Up notes not found in audit HTML: {unique_notes}"

            # Verify the page structure is intact
            assert 'Audit Log' in html, "Audit log title missing"
            assert 'Details' in html, "Details column header missing"

        finally:
            session.close()
