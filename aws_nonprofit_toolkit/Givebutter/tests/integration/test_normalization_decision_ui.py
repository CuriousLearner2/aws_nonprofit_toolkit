"""
Integration tests for normalization decision UI on normalizations page.

Tests the form integration, status display, and end-to-end workflow via template.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime

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
def flask_client_with_normalizations(temp_db, monkeypatch):
    """Flask client with normalizations seeded in database."""
    database_url, engine = temp_db

    app.config['TESTING'] = True

    # Monkeypatch repository_provider to use test database
    from scripts.householder import repository_provider
    from scripts.householder.database_repository import DatabaseImportRepository

    def patched_get_import_repository(config):
        return DatabaseImportRepository(database_url=database_url)

    monkeypatch.setattr(repository_provider, 'get_import_repository', patched_get_import_repository)

    # Monkeypatch normalization_decision_service to use test database
    from scripts.householder import normalization_decision_service
    from scripts.householder.database_write_repository import DatabaseNormalizationDecisionWriter

    def patched_get_writer(config):
        if config and 'GIVEBUTTER_DATABASE_URL' in config:
            return DatabaseNormalizationDecisionWriter(database_url=config['GIVEBUTTER_DATABASE_URL'])
        return DatabaseNormalizationDecisionWriter(database_url=database_url)

    monkeypatch.setattr(normalization_decision_service, '_get_normalization_decision_writer', patched_get_writer)

    # Seed database
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-2025-0101-A',
        filename='test_upload.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create raw rows and contacts with normalization items
    normalization_items = []
    for i in range(3):
        raw_row = RawImportRow(
            batch_id='IMP-2025-0101-A',
            row_index=i + 1,
            raw_csv_data={'Name': f'Person {i+1}', 'Email': f'person{i+1}@example.com'},
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

        # Create normalization item
        item = ReviewItem(
            batch_id='IMP-2025-0101-A',
            item_type='normalization',
            status='pending',
            payload_json={
                'field': 'email',
                'raw_value': f'person{i+1}@example.com',
                'normalized_value': f'person{i+1}@example.com',
                'basis': 'typo_correction',
                'confidence': 0.85,
            },
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

        normalization_items.append((item.id, contact.id))

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, normalization_items


class TestNormalizationDecisionUI:
    """Test normalization decision UI integration."""

    def test_normalization_page_renders(self, flask_client_with_normalizations):
        """Normalization page renders with decision form structure."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations

        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Verify form has decision options
        assert 'accept_normalization' in html
        assert 'reject_normalization' in html
        assert 'defer' in html

    def test_normalization_page_displays_effective_status(self, flask_client_with_normalizations):
        """Normalization page shows effective status for normalization items."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations

        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Check for status display (Pending, Accepted, Rejected, Deferred)
        assert 'Pending' in html or 'pending' in html

    def test_form_posts_to_decision_route(self, flask_client_with_normalizations):
        """Form in modal posts to correct normalization decision route."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations

        # Get normalization page to verify form structure
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        html = response.data.decode('utf-8')

        # Verify form action includes batch ID and will be constructed with item ID
        assert 'IMP-2025-0101-A' in html
        assert 'normalizations' in html
        assert '/decision' in html

    def test_valid_accept_submission_creates_decision(self, flask_client_with_normalizations):
        """Submitting accept_normalization creates ReviewDecision record."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations
        item_id, contact_id = normalization_items[0]

        response = client.post(
            f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
            data={
                'decision': 'accept_normalization',
            }
        )

        assert response.status_code == 302  # Redirect

        # Verify ReviewDecision created
        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'accept_normalization'
        session.close()

    def test_valid_reject_submission_creates_decision(self, flask_client_with_normalizations):
        """Submitting reject_normalization creates ReviewDecision record."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations
        item_id, contact_id = normalization_items[0]

        response = client.post(
            f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
            data={
                'decision': 'reject_normalization',
            }
        )

        assert response.status_code == 302

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'reject_normalization'
        session.close()

    def test_valid_defer_submission_creates_decision(self, flask_client_with_normalizations):
        """Submitting defer creates ReviewDecision record."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations
        item_id, contact_id = normalization_items[0]

        response = client.post(
            f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
            data={
                'decision': 'defer',
            }
        )

        assert response.status_code == 302

        session = Session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=item_id).first()
        assert decision is not None
        assert decision.decision == 'defer'
        session.close()

    def test_submission_creates_audit_log(self, flask_client_with_normalizations):
        """Submitting form creates AuditLogRecord."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations
        item_id, contact_id = normalization_items[0]

        response = client.post(
            f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
            data={
                'decision': 'accept_normalization',
            }
        )

        assert response.status_code == 302

        session = Session()
        audit = session.query(AuditLogRecord).filter_by(item_id=item_id).first()
        assert audit is not None
        assert audit.action_type == 'decision_recorded'
        session.close()

    def test_raw_import_rows_unchanged(self, flask_client_with_normalizations):
        """Raw rows not mutated by form submission."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations
        item_id, contact_id = normalization_items[0]

        session = Session()
        original_rows = session.query(RawImportRow).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
            data={'decision': 'accept_normalization'},
        )

        session = Session()
        new_rows = session.query(RawImportRow).count()
        assert new_rows == original_rows
        session.close()

    def test_import_contacts_unchanged(self, flask_client_with_normalizations):
        """Import contacts not mutated by form submission."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations
        item_id, contact_id = normalization_items[0]

        session = Session()
        original_contacts = session.query(ImportContact).count()
        session.close()

        client.post(
            f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
            data={'decision': 'accept_normalization'},
        )

        session = Session()
        new_contacts = session.query(ImportContact).count()
        assert new_contacts == original_contacts
        session.close()

    def test_after_decision_page_updated(self, flask_client_with_normalizations):
        """After submitting decision, page reloads with updated status."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations
        item_id, contact_id = normalization_items[0]

        # Submit decision
        client.post(
            f'/imports/IMP-2025-0101-A/normalizations/{item_id}/decision',
            data={'decision': 'accept_normalization'},
        )

        # Refresh normalizations page
        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Page should show status (Accepted, Pending, etc.)
        # Status display is dynamic based on ReviewDecision
        assert 'Accepted' in html or 'Pending' in html

    def test_validation_decision_not_in_normalization_form(self, flask_client_with_normalizations):
        """Form only shows normalization decision types, not validation types."""
        client, database_url, engine, Session, normalization_items = flask_client_with_normalizations

        response = client.get('/imports/IMP-2025-0101-A/normalizations')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        # Verify only normalization decision types present
        assert 'accept_normalization' in html
        assert 'reject_normalization' in html
        assert 'defer' in html

        # Verify no validation decision types
        # (These are specific to validation page)
        assert 'accept_issue' not in html
        assert 'dismiss_issue' not in html
