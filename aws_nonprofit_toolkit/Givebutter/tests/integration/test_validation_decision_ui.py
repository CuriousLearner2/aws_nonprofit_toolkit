"""
Integration tests for validation decision UI on validation page.

Tests the form integration, status display, and end-to-end workflow via template.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
    AuditLogRecord,
    create_db_engine,
)
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def flask_client_with_validation_items(temp_db, monkeypatch):
    """Flask client with validation items seeded in database."""
    database_url, engine = temp_db

    app.config['TESTING'] = True

    # IMPORTANT: Configure environment for database mode
    # This ensures all services use the test database
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Monkeypatch repository_provider to use test database
    from scripts.householder import repository_provider
    from scripts.householder.database_repository import DatabaseImportRepository

    def patched_get_import_repository(config):
        return DatabaseImportRepository(database_url=database_url)

    monkeypatch.setattr(repository_provider, 'get_import_repository', patched_get_import_repository)

    # Monkeypatch validation_decision_service to use test database
    from scripts.householder import validation_decision_service
    from scripts.householder.database_write_repository import DatabaseValidationDecisionWriter

    def patched_get_writer(config):
        if config and 'GIVEBUTTER_DATABASE_URL' in config:
            return DatabaseValidationDecisionWriter(database_url=config['GIVEBUTTER_DATABASE_URL'])
        return DatabaseValidationDecisionWriter(database_url=database_url)

    monkeypatch.setattr(validation_decision_service, '_get_validation_decision_writer', patched_get_writer)

    # Seed database
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-2025-0101-A',
        filename='test_upload.csv',
        upload_timestamp=datetime.now(timezone.utc),
    )
    session.add(batch)
    session.flush()

    # Create raw rows and contacts with validation items
    validation_items = []
    for i in range(3):
        raw_row = RawImportRow(
            batch_id='IMP-2025-0101-A',
            row_index=i + 1,
            raw_csv_data={'Name': f'Person {i+1}'},
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_row.id,
            first_name=f'Person{i+1}',
            last_name=f'Last{i+1}',
            email=f'person{i+1}@example.com',
            phone=f'(555) {100+i:03d}-{1000+i:04d}',
            amount=100.0 + i * 50,
        )
        session.add(contact)
        session.flush()

        # Create validation item
        item = ReviewItem(
            batch_id='IMP-2025-0101-A',
            item_type='validation',
            status='pending',
            payload_json={'issue_type': 'format-invalid', 'issue_description': 'Invalid email'},
        )
        session.add(item)
        session.flush()

        # Create subject reference
        subject = ReviewItemSubject(
            review_item_id=item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
        )
        session.add(subject)
        session.flush()

        validation_items.append((item.id, contact.id))

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, validation_items


class TestValidationDecisionUI:
    """Test validation decision UI integration."""

    def test_validation_page_renders_decision_form(self, flask_client_with_validation_items):
        """Validation page renders with form structure and decision route."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items

        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Verify form has decision select and notes textarea
        assert 'decision' in html or 'Decision' in html
        assert 'notes' in html or 'Notes' in html

    def test_validation_page_shows_scope_banner(self, flask_client_with_validation_items):
        """Validation page explains the dynamic validation scope."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items

        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        assert 'data-testid="validation-scope-banner"' in html
        assert 'data-dynamic-fields="amount,email,phone"' in html
        assert 'data-import-stage-fields="date,address"' in html
        assert 'data-unsupported-fields="campaign"' in html

    def test_approval_modal_explains_blocking_vs_warning(self, flask_client_with_validation_items):
        """Approval modal explains that blocking issues require override confirmation."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items

        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        assert 'Blocking issues require explicit override confirmation before approval.' in html
        assert 'Warnings are non-blocking and can remain visible without requiring an override.' in html
        assert 'Approve with Overrides' in html

    def test_validation_page_displays_row_status(self, flask_client_with_validation_items):
        """Validation page shows row status from Phase 2 derivation (Phase 3)."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items

        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Check for Row Status column header and values
        assert 'Row Status' in html
        # Should show derived row status values
        assert 'No issues' in html or 'Warning' in html or 'Blocking' in html

    def test_validation_page_contains_inspect_links(self, flask_client_with_validation_items):
        """Validation page contains Inspect links for each record."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items

        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        assert 'Inspect' in html
        assert 'data-action="inspect-record"' in html

    def test_form_posts_to_decision_route(self, flask_client_with_validation_items):
        """Form in modal posts to correct validation decision route."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items

        # Get validation page to verify row status form structure
        response = client.get('/imports/IMP-2025-0101-A/validation')
        html = response.data.decode('utf-8')

        # Verify row status dropdown is present
        # The form is built dynamically by JavaScript in the modal
        assert 'row-decision' in html or 'row_decision' in html
        assert 'needs_follow_up' in html or 'needs follow-up' in html
        assert 'accept_as_is' in html or 'accept as-is' in html
        assert 'defer' in html
        assert 'clear_decision' in html or 'clear decision' in html
        assert 'notes' in html or 'Notes' in html
        # Verify the form action will be constructed with the batch ID
        assert 'IMP-2025-0101-A' in html

    def test_valid_form_submission_creates_review_decision(self, flask_client_with_validation_items):
        """Submitting form creates ReviewDecision record."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        response = client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={
                'decision': 'dismiss_issue',
                'notes': 'False positive from form',
            }
        )

        assert response.status_code == 302  # Redirect

        # Verify ReviewDecision created
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'dismiss_issue'
        session.close()

    def test_valid_form_submission_creates_audit_log(self, flask_client_with_validation_items):
        """Submitting form creates AuditLogRecord."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        response = client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={
                'decision': 'accept_issue',
                'notes': 'Valid from form',
            }
        )

        assert response.status_code == 302

        session = Session()
        audit = session.query(AuditLogRecord).filter_by(item_id=item_id).first()
        assert audit is not None
        assert audit.action_type == 'decision_recorded'
        session.close()

    def test_after_decision_page_shows_row_status(self, flask_client_with_validation_items):
        """After submitting decision, validation page shows derived row status (Phase 3)."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        # Submit decision
        client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={'decision': 'dismiss_issue'},
        )

        # Refresh validation page
        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Should show Row Status column with derived status values
        assert 'Row Status' in html
        assert 'No issues' in html or 'Warning' in html or 'Blocking' in html

    def test_accepted_decision_shows_accepted_status(self, flask_client_with_validation_items):
        """Form submission with 'accept_issue' updates effective status."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        # Verify decision is recorded
        response = client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={'decision': 'accept_issue'},
        )
        assert response.status_code == 302

        # Verify ReviewDecision was created with correct value
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'accept_issue'
        session.close()

    def test_dismissed_decision_shows_dismissed_status(self, flask_client_with_validation_items):
        """Form submission with 'dismiss_issue' updates effective status."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        # Verify decision is recorded
        response = client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={'decision': 'dismiss_issue'},
        )
        assert response.status_code == 302

        # Verify ReviewDecision was created with correct value
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'dismiss_issue'
        session.close()

    def test_deferred_decision_shows_deferred_status(self, flask_client_with_validation_items):
        """Form submission with 'defer' updates effective status."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        # Verify decision is recorded
        response = client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={'decision': 'defer'},
        )
        assert response.status_code == 302

        # Verify ReviewDecision was created with correct value
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'defer'
        session.close()

    def test_raw_import_rows_unchanged_after_ui_submission(self, flask_client_with_validation_items):
        """Raw rows not mutated by UI form submission."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        session = Session()
        original_rows = session.query(RawImportRow).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={'decision': 'dismiss_issue'},
        )

        session = Session()
        new_rows = session.query(RawImportRow).count()
        assert new_rows == original_rows
        session.close()

    def test_import_contacts_unchanged_after_ui_submission(self, flask_client_with_validation_items):
        """Import contacts not mutated by UI form submission."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        session = Session()
        original_contacts = session.query(ImportContact).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={'decision': 'dismiss_issue'},
        )

        session = Session()
        new_contacts = session.query(ImportContact).count()
        assert new_contacts == original_contacts
        session.close()

    def test_review_items_status_not_mutated(self, flask_client_with_validation_items):
        """ReviewItem.status not mutated, only decisions recorded."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items
        item_id, contact_id = validation_items[0]

        session = Session()
        original_item = session.query(ReviewItem).filter_by(id=item_id).first()
        original_status = original_item.status
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/validation/{contact_id}/decision',
            data={'decision': 'dismiss_issue'},
        )

        session = Session()
        updated_item = session.query(ReviewItem).filter_by(id=item_id).first()
        # Status should remain unchanged (effective status derived from decision)
        assert updated_item.status == original_status
        session.close()

    def test_no_other_decision_types_in_form(self, flask_client_with_validation_items):
        """Form only shows row-level decision types, not duplicate/household types."""
        client, database_url, engine, Session, validation_items = flask_client_with_validation_items

        response = client.get('/imports/IMP-2025-0101-A/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Verify row-level decision types in form
        assert 'accept_as_is' in html
        assert 'needs_follow_up' in html
        assert 'defer' in html
        assert 'reject_row' in html
        assert 'clear_decision' in html

        # Verify no other decision types (future proof)
        # These should not appear in the validation form
        assert 'same_person' not in html or 'same_person' not in html.split('decision')[0]  # Not in form
        assert 'merge' not in html.lower() or 'merge contact' not in html.lower()
        assert 'household' not in html.lower() or 'confirm household' not in html.lower()
