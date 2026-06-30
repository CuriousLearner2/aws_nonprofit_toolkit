"""
Integration tests for autosave corrections appearing in export.

Verify that successful autosave corrections are applied to export preview and CSV.
"""

import pytest
import tempfile
import csv
from pathlib import Path
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewDecision, create_db_engine
)
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.export_file_service import generate_export_file
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
def temp_export_dir():
    """Create temporary directory for exports."""
    export_dir = tempfile.mkdtemp()
    yield export_dir
    # Cleanup
    import shutil
    shutil.rmtree(export_dir, ignore_errors=True)


@pytest.fixture
def client_with_db(temp_db, temp_export_dir, monkeypatch):
    """Flask test client configured with temporary database."""
    database_url, engine = temp_db

    # Monkeypatch environment variable
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)

    # Configure Flask app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client, database_url, engine, temp_export_dir, sessionmaker(bind=engine)


def setup_autosave_test_batch(database_url):
    """Set up a batch for testing autosave export."""
    SessionLocal = sessionmaker(bind=create_db_engine(database_url))
    session = SessionLocal()

    try:
        batch = ImportBatch(
            id='autosave-export-test',
            filename='test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id='autosave-export-test',
            row_index=0,
            raw_csv_data={
                'transaction_id': 'TX001',
                'date': '2024-01-15',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'email': 'alice@oldomain.com',  # Will be corrected via autosave
                'phone': '(555) 123-4567',
                'amount': '100.00',
                'address': '789 Oak Ave',
            }
        )
        session.add(raw_row)
        session.flush()
        raw_row_id = raw_row.id

        # Create ImportContact with original values
        import_contact = ImportContact(
            batch_id='autosave-export-test',
            raw_import_row_id=raw_row_id,
            first_name='Alice',
            last_name='Johnson',
            email='alice@oldomain.com',
            phone='(555) 123-4567',
            address_line1='789 Oak Ave',
            amount=100.00
        )
        session.add(import_contact)
        session.commit()

        return batch.id, raw_row_id
    finally:
        session.close()


@pytest.mark.integration
class TestAutosaveExport:
    """Test suite for autosave corrections in export."""

    def test_successful_autosave_appears_in_export_preview(self, client_with_db):
        """Successful autosave correction must appear in export preview."""
        client, database_url, engine, export_dir, Session = client_with_db
        batch_id, raw_row_id = setup_autosave_test_batch(database_url)

        # Autosave email correction
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'alice@example.com'}
            }
        )

        # Should succeed
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['effective_values']['email'] == 'alice@example.com'

        # Build export preview
        preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
        assert preview.is_export_ready

        # Verify corrected email in preview
        assert len(preview.export_rows) == 1
        assert preview.export_rows[0].email == 'alice@example.com', \
            f"Export preview should contain corrected email, got: {preview.export_rows[0].email}"

        # Verify raw data unchanged
        session = Session()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_row_id).first()
            assert raw_row.raw_csv_data['email'] == 'alice@oldomain.com', \
                "Raw data should be unchanged"
        finally:
            session.close()

    def test_successful_autosave_appears_in_generated_csv(self, client_with_db):
        """Successful autosave correction must appear in generated CSV."""
        client, database_url, engine, export_dir, Session = client_with_db
        batch_id, raw_row_id = setup_autosave_test_batch(database_url)

        # Autosave email correction
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'alice@example.com'}
            }
        )

        assert response.status_code == 200

        # Generate export CSV
        result = generate_export_file(
            batch_id,
            export_dir,
            config={'GIVEBUTTER_DATABASE_URL': database_url}
        )

        csv_file = Path(result.file_path)
        assert csv_file.exists(), "CSV file should be created"

        # Read and verify CSV
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            data_rows = list(reader)

        assert len(data_rows) == 1, "Should have 1 data row"

        # Find email column
        email_col_index = header.index('email')

        # Verify corrected email in CSV
        csv_email = data_rows[0][email_col_index]
        assert csv_email == 'alice@example.com', \
            f"CSV should contain corrected email, got: {csv_email}"

        # Verify original email is NOT in CSV
        assert 'alice@oldomain.com' not in csv_email, \
            "Original email should not appear in CSV"

    def test_failed_autosave_still_not_in_export(self, client_with_db):
        """Regression: Failed autosave corrections still do not export."""
        client, database_url, engine, export_dir, Session = client_with_db
        batch_id, raw_row_id = setup_autosave_test_batch(database_url)

        # Try to autosave invalid email
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'invalid-email'}
            }
        )

        # Should fail
        assert response.status_code == 400

        # Build export preview
        preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        # Verify original email in preview (not the failed value)
        assert len(preview.export_rows) == 1
        assert preview.export_rows[0].email == 'alice@oldomain.com', \
            f"Export should keep original email after failed autosave"

    def test_latest_autosave_wins_same_field(self, client_with_db):
        """Later autosave decisions on same field override earlier ones."""
        client, database_url, engine, export_dir, Session = client_with_db
        batch_id, raw_row_id = setup_autosave_test_batch(database_url)

        # First autosave
        response1 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'alice.v1@example.com'}
            }
        )
        assert response1.status_code == 200

        # Second autosave (should override first for email field)
        response2 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'alice.v2@example.com'}
            }
        )
        assert response2.status_code == 200

        # Build export preview
        preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        # Verify latest version in export
        assert len(preview.export_rows) == 1
        assert preview.export_rows[0].email == 'alice.v2@example.com', \
            "Export should contain latest autosave value"

    def test_multiple_field_autosaves_merge(self, client_with_db):
        """Multiple autosaves on different fields are all applied (merged) in export."""
        client, database_url, engine, export_dir, Session = client_with_db
        batch_id, raw_row_id = setup_autosave_test_batch(database_url)

        # First autosave: email
        response1 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'alice@example.com'}
            }
        )
        assert response1.status_code == 200

        # Second autosave: amount (different field)
        response2 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '250.50'}
            }
        )
        assert response2.status_code == 200

        # Build export preview
        preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        # Verify BOTH corrections are in export
        assert len(preview.export_rows) == 1
        assert preview.export_rows[0].email == 'alice@example.com', \
            f"Export should contain email correction, got: {preview.export_rows[0].email}"
        assert preview.export_rows[0].amount == '250.50', \
            f"Export should contain amount correction, got: {preview.export_rows[0].amount}"

    def test_multiple_field_autosaves_with_override(self, client_with_db):
        """Later autosaves override earlier ones per field, but earlier corrections on other fields persist."""
        client, database_url, engine, export_dir, Session = client_with_db
        batch_id, raw_row_id = setup_autosave_test_batch(database_url)

        # First autosave: email
        response1 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'alice.v1@example.com'}
            }
        )
        assert response1.status_code == 200

        # Second autosave: amount
        response2 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '250.50'}
            }
        )
        assert response2.status_code == 200

        # Third autosave: email again (override first email correction)
        response3 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'alice.v2@example.com'}
            }
        )
        assert response3.status_code == 200

        # Build export preview
        preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})

        # Verify: latest email + latest amount
        assert len(preview.export_rows) == 1
        assert preview.export_rows[0].email == 'alice.v2@example.com', \
            f"Should have latest email, got: {preview.export_rows[0].email}"
        assert preview.export_rows[0].amount == '250.50', \
            f"Should keep amount correction, got: {preview.export_rows[0].amount}"

    def test_autosave_merge_deterministic_with_timestamp_collision(self, client_with_db):
        """Verify row-level autosave merge is deterministic even with identical timestamps."""
        client, database_url, engine, export_dir, Session = client_with_db
        batch_id, raw_row_id = setup_autosave_test_batch(database_url)

        # Insert two decisions with IDENTICAL timestamps (simulating collision)
        session = Session()
        try:
            frozen_time = datetime(2026, 6, 19, 12, 0, 0, 500000)

            # Create both decisions with same timestamp
            d1 = ReviewDecision(
                batch_id=batch_id,
                review_item_id=None,
                raw_import_row_id=raw_row_id,
                decision='accept_issue',
                reviewed_values={'email': 'v1@example.com'},
                created_at=frozen_time
            )
            session.add(d1)
            session.flush()

            d2 = ReviewDecision(
                batch_id=batch_id,
                review_item_id=None,
                raw_import_row_id=raw_row_id,
                decision='accept_issue',
                reviewed_values={'email': 'v2@example.com'},
                created_at=frozen_time  # SAME
            )
            session.add(d2)
            session.commit()

            # Run export multiple times - should always get v2 (later decision by ID)
            for run in range(3):
                preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
                assert preview.export_rows[0].email == 'v2@example.com', \
                    f"Run {run}: Expected v2, got {preview.export_rows[0].email}"
        finally:
            session.close()
