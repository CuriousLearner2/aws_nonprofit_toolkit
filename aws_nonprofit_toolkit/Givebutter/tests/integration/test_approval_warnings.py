"""
Integration tests for approval warnings - checking for follow-up and defer decisions.

Tests the complete workflow:
1. Record row-level decisions (follow-up, defer)
2. Call approval endpoint to check for remaining issues
3. Verify that follow-up and defer rows are included in the warning list
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
    create_db_engine,
)
from sqlalchemy.orm import sessionmaker
from scripts.householder.row_decision_service import record_row_decision


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
def flask_client_with_batch(temp_db, monkeypatch):
    """Flask client with batch and rows (no validation items) seeded in database."""
    database_url, engine = temp_db

    app.config['TESTING'] = True

    # Set database URL in environment
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Monkeypatch repository_provider to use test database
    from scripts.householder import repository_provider
    from scripts.householder.database_repository import DatabaseImportRepository

    def patched_get_import_repository(config):
        return DatabaseImportRepository(database_url=database_url)

    monkeypatch.setattr(repository_provider, 'get_import_repository', patched_get_import_repository)

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

    # Create rows WITHOUT validation items (to test decision-only warnings)
    rows = []
    for i in range(3):
        raw_row = RawImportRow(
            batch_id='IMP-2025-0101-A',
            row_index=i + 1,
            raw_csv_data={'Name': f'Person {i+1}'},
        )
        session.add(raw_row)
        session.flush()

        rows.append(raw_row.id)

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, rows


class TestApprovalWarnings:
    """Test approval warnings for follow-up and defer decisions."""

    def test_approval_check_with_no_decisions(self, flask_client_with_batch):
        """Approval check passes when no decisions or validation issues."""
        client, database_url, engine, Session, rows = flask_client_with_batch

        # Use 'approved' status for simple approval when no issues
        response = client.post(
            '/imports/IMP-2025-0101-A/approve-batch',
            json={
                'approval_status': 'approved'
            }
        )

        # No issues or decisions, so simple approval succeeds
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['approval_status'] == 'approved'

    def test_approval_check_includes_follow_up_rows(self, flask_client_with_batch):
        """Approval check includes rows with follow-up decisions."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # Record a follow-up decision on first row
        record_row_decision(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Verify phone number',
            database_url=database_url
        )

        response = client.post(
            '/imports/IMP-2025-0101-A/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        # Should return warning about remaining issues
        assert response.status_code == 200
        data = response.get_json()
        assert data['requires_override_confirmation'] is True
        assert len(data['remaining_issues']) == 1
        assert data['remaining_issues'][0]['raw_import_row_id'] == raw_id
        assert data['remaining_issues'][0]['decision_warning'] == 'needs_follow_up'

    def test_approval_check_includes_defer_rows(self, flask_client_with_batch):
        """Approval check includes rows with defer decisions."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # Record a defer decision on first row
        record_row_decision(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_id,
            decision='defer',
            database_url=database_url
        )

        response = client.post(
            '/imports/IMP-2025-0101-A/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        # Should return warning about remaining issues
        assert response.status_code == 200
        data = response.get_json()
        assert data['requires_override_confirmation'] is True
        assert len(data['remaining_issues']) == 1
        assert data['remaining_issues'][0]['raw_import_row_id'] == raw_id
        assert data['remaining_issues'][0]['decision_warning'] == 'defer'

    def test_approval_check_includes_multiple_decision_types(self, flask_client_with_batch):
        """Approval check includes rows with different decision types."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id_1 = rows[0]
        raw_id_2 = rows[1]

        # Record follow-up for row 0
        record_row_decision(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_id_1,
            decision='needs_follow_up',
            notes='Check data',
            database_url=database_url
        )

        # Record defer for row 1
        record_row_decision(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_id_2,
            decision='defer',
            database_url=database_url
        )

        response = client.post(
            '/imports/IMP-2025-0101-A/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['requires_override_confirmation'] is True
        assert len(data['remaining_issues']) == 2

        # Verify both rows are in the list
        row_ids = [r['raw_import_row_id'] for r in data['remaining_issues']]
        assert raw_id_1 in row_ids
        assert raw_id_2 in row_ids

        # Verify correct warnings
        for issue in data['remaining_issues']:
            if issue['raw_import_row_id'] == raw_id_1:
                assert issue['decision_warning'] == 'needs_follow_up'
            else:
                assert issue['decision_warning'] == 'defer'

    def test_approval_check_excludes_cleared_decisions(self, flask_client_with_batch):
        """Approval check excludes rows with cleared decisions."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # Record and clear a decision
        record_row_decision(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Check',
            database_url=database_url
        )

        record_row_decision(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=database_url
        )

        # Use simple approval since no remaining issues for cleared decisions
        response = client.post(
            '/imports/IMP-2025-0101-A/approve-batch',
            json={
                'approval_status': 'approved'
            }
        )

        # No remaining issues for cleared decisions - simple approval succeeds
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['approval_status'] == 'approved'

    def test_approval_with_override_confirmation(self, flask_client_with_batch):
        """Can approve batch with override confirmation after checking issues."""
        client, database_url, engine, Session, rows = flask_client_with_batch
        raw_id = rows[0]

        # Record a follow-up decision
        record_row_decision(
            batch_id='IMP-2025-0101-A',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Verify',
            database_url=database_url
        )

        # First, check for issues (should require confirmation)
        response = client.post(
            '/imports/IMP-2025-0101-A/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['requires_override_confirmation'] is True

        # Now approve with override confirmation
        overrides = [{
            'raw_import_row_id': raw_id,
            'row_index': 1,
            'issues': [{'field': 'row_decision', 'reason': 'Marked as Needs follow-up'}]
        }]

        response = client.post(
            '/imports/IMP-2025-0101-A/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': overrides
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['approval_status'] == 'approved_with_overrides'
        assert data['override_count'] == 1
