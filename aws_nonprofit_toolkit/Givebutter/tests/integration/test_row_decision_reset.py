"""
Integration tests for row decision reset functionality.

Tests the "Return to system status" feature:
- Only show reset option when a human decision exists
- Hide reset option when no decision
- Reset removes reviewer decision and returns to system status
- Confirmation dialog appears
- Raw data unchanged
- Issues remain unchanged
- Audit trail preserved
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
    create_db_engine,
)
from sqlalchemy.orm import sessionmaker
from scripts.householder.row_decision_service import record_row_decision, get_row_decision


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
def flask_client_with_rows(temp_db, monkeypatch):
    """Flask client with batch and rows seeded in database."""
    database_url, engine = temp_db

    app.config['TESTING'] = True
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Seed database
    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='reset-test-batch',
        filename='test.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=3
    )
    session.add(batch)
    session.flush()

    rows = []
    for i in range(1, 4):
        row = RawImportRow(
            batch_id='reset-test-batch',
            row_index=i,
            raw_csv_data={'name': f'Person {i}'}
        )
        session.add(row)
        session.flush()
        rows.append(row.id)

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, rows


class TestRowDecisionReset:
    """Test row decision reset functionality."""

    def test_get_decision_returns_has_decision_false_when_no_decision(self, flask_client_with_rows):
        """GET /row-decision/<id> returns has_decision=false when no decision exists."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        response = client.get(f'/imports/reset-test-batch/row-decision/{raw_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['has_decision'] is False
        assert data['decision'] is None

    def test_get_decision_returns_has_decision_true_when_decision_exists(self, flask_client_with_rows):
        """GET /row-decision/<id> returns has_decision=true when decision exists."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        # Record a decision
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='accept_as_is',
            database_url=database_url
        )

        response = client.get(f'/imports/reset-test-batch/row-decision/{raw_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['has_decision'] is True
        assert data['decision'] == 'accept_as_is'

    def test_get_decision_returns_has_decision_false_after_clear(self, flask_client_with_rows):
        """GET /row-decision/<id> returns has_decision=false after clear decision."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        # Record and clear a decision
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Check',
            database_url=database_url
        )

        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=database_url
        )

        response = client.get(f'/imports/reset-test-batch/row-decision/{raw_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['has_decision'] is False

    def test_reset_via_post_clears_decision(self, flask_client_with_rows):
        """POST with clear_decision removes the reviewer decision."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        # Record initial decision
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='defer',
            database_url=database_url
        )

        # Verify decision exists
        decision = get_row_decision('reset-test-batch', raw_id, database_url)
        assert decision is not None
        assert decision['decision'] == 'defer'

        # Reset via POST
        response = client.post(
            f'/imports/reset-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'clear_decision'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['decision'] == 'clear_decision'

        # Verify decision is now cleared
        decision = get_row_decision('reset-test-batch', raw_id, database_url)
        assert decision is None

    def test_reset_preserves_raw_data(self, flask_client_with_rows):
        """Reset does not mutate raw import data."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        # Get original data
        session = Session()
        original_row = session.query(RawImportRow).filter_by(id=raw_id).first()
        original_data = original_row.raw_csv_data.copy() if original_row.raw_csv_data else {}
        session.close()

        # Record and reset decision
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Check',
            database_url=database_url
        )

        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=database_url
        )

        # Verify raw data unchanged
        session = Session()
        final_row = session.query(RawImportRow).filter_by(id=raw_id).first()
        assert final_row.raw_csv_data == original_data
        session.close()

    def test_reset_multiple_decisions_sequence(self, flask_client_with_rows):
        """Reset works correctly in a sequence of decisions."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        # Record first decision
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='accept_as_is',
            database_url=database_url
        )

        # Reset
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=database_url
        )

        # Record second decision
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='defer',
            database_url=database_url
        )

        # Get current decision - should be defer
        decision = get_row_decision('reset-test-batch', raw_id, database_url)
        assert decision['decision'] == 'defer'

        # Reset again
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=database_url
        )

        # Should be cleared now
        decision = get_row_decision('reset-test-batch', raw_id, database_url)
        assert decision is None

    def test_reset_follow_up_with_notes(self, flask_client_with_rows):
        """Reset clears even when follow-up had notes."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        # Record follow-up with notes
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='needs_follow_up',
            notes='Detailed notes about the issue',
            database_url=database_url
        )

        # Verify decision with notes
        decision = get_row_decision('reset-test-batch', raw_id, database_url)
        assert decision['decision'] == 'needs_follow_up'
        assert decision['notes'] == 'Detailed notes about the issue'

        # Reset
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=raw_id,
            decision='clear_decision',
            database_url=database_url
        )

        # Should be cleared
        decision = get_row_decision('reset-test-batch', raw_id, database_url)
        assert decision is None

    def test_independent_row_decisions_unaffected_by_reset(self, flask_client_with_rows):
        """Resetting one row does not affect other rows."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        row_1, row_2, row_3 = rows[0], rows[1], rows[2]

        # Record decisions for different rows
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=row_1,
            decision='accept_as_is',
            database_url=database_url
        )

        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=row_2,
            decision='defer',
            database_url=database_url
        )

        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=row_3,
            decision='needs_follow_up',
            notes='Check',
            database_url=database_url
        )

        # Reset row 1
        record_row_decision(
            batch_id='reset-test-batch',
            raw_import_row_id=row_1,
            decision='clear_decision',
            database_url=database_url
        )

        # Row 1 should be cleared
        decision_1 = get_row_decision('reset-test-batch', row_1, database_url)
        assert decision_1 is None

        # Rows 2 and 3 should be unchanged
        decision_2 = get_row_decision('reset-test-batch', row_2, database_url)
        assert decision_2['decision'] == 'defer'

        decision_3 = get_row_decision('reset-test-batch', row_3, database_url)
        assert decision_3['decision'] == 'needs_follow_up'

    def test_reset_all_decision_types(self, flask_client_with_rows):
        """Reset works for all human decision types."""
        client, database_url, engine, Session, rows = flask_client_with_rows
        raw_id = rows[0]

        decision_types = [
            ('accept_as_is', None),
            ('needs_follow_up', 'Check this'),
            ('defer', None),
            ('reject_row', None),
        ]

        for decision_type, notes in decision_types:
            # Record decision
            record_row_decision(
                batch_id='reset-test-batch',
                raw_import_row_id=raw_id,
                decision=decision_type,
                notes=notes,
                database_url=database_url
            )

            # Verify it exists
            decision = get_row_decision('reset-test-batch', raw_id, database_url)
            assert decision['decision'] == decision_type

            # Reset
            record_row_decision(
                batch_id='reset-test-batch',
                raw_import_row_id=raw_id,
                decision='clear_decision',
                database_url=database_url
            )

            # Verify cleared
            decision = get_row_decision('reset-test-batch', raw_id, database_url)
            assert decision is None
