"""
Integration test: Failed autosave values do not appear in generated CSV.

Proves the full chain from failed autosave to export generation:
1. Seed a row with a valid email.
2. Attempt autosave with an invalid email (400 error).
3. Verify no ReviewDecision was saved for the failed value.
4. Generate export preview and CSV.
5. Assert original email is in CSV, failed email is not.
6. Assert raw source data remains unchanged.
"""

import pytest
import csv
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewDecision, ReviewItem,
    create_db_engine,
)
from scripts.householder.export_file_service import generate_export_file
from scripts.householder.export_preview_service import build_export_preview


@pytest.fixture
def temp_db_and_export_dir():
    """Create temporary SQLite database and export directory."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    export_dir = tempfile.mkdtemp()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine, export_dir

    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    for f in Path(export_dir).glob('*'):
        f.unlink()
    Path(export_dir).rmdir()


@pytest.fixture
def flask_client_with_batch(temp_db_and_export_dir, monkeypatch):
    """Flask client with database and batch seeded."""
    database_url, engine, export_dir = temp_db_and_export_dir

    app.config['TESTING'] = True
    app.config['EXPORT_OUTPUT_DIR'] = export_dir
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setitem(app.config, 'HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setitem(app.config, 'GIVEBUTTER_DATABASE_URL', database_url)

    # Seed database
    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='failed-autosave-test',
        filename='test.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=1
    )
    session.add(batch)
    session.flush()

    # Create one row with valid email
    row = RawImportRow(
        batch_id='failed-autosave-test',
        row_index=1,
        raw_csv_data={
            'transaction_id': 'TXN-001',
            'name': 'John Smith',
            'email': 'john.smith@example.com',
            'phone': '415-555-1234',
            'amount': '100.00'
        }
    )
    session.add(row)
    session.flush()
    raw_id = row.id

    # Create ImportContact (required by export)
    contact = ImportContact(
        batch_id='failed-autosave-test',
        raw_import_row_id=raw_id,
        first_name='John',
        last_name='Smith',
        email='john.smith@example.com',
        phone='415-555-1234',
        address_line1=None,
        address_line2=None,
        city=None,
        state=None,
        postal_code=None,
        amount=100.00,
    )
    session.add(contact)
    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, export_dir, Session, raw_id


class TestFailedAutosaveExclusionFromCSV:
    """Test that failed autosave values do not appear in generated CSV."""

    def test_failed_autosave_value_not_in_generated_csv(self, flask_client_with_batch):
        """
        Failed autosave email does not appear in generated CSV.

        Chain:
        1. Original email: john.smith@example.com (valid)
        2. Attempt autosave: invalid-email (fails with 400)
        3. No decision saved for failed autosave
        4. Generate export CSV
        5. Original email in CSV: YES
        6. Failed email in CSV: NO
        7. Raw data unchanged: YES
        """
        client, database_url, engine, export_dir, Session, raw_id = flask_client_with_batch

        # Step 2: Attempt autosave with invalid email
        response = client.post(
            '/imports/failed-autosave-test/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid-email'}
            }
        )

        # Step 2a: Verify autosave failed
        assert response.status_code == 400, "Autosave should fail for invalid email"

        # Step 3: Verify no ReviewDecision was saved
        session = Session()
        decision = session.query(ReviewDecision).filter_by(
            raw_import_row_id=raw_id
        ).first()
        assert decision is None, "No decision should be saved for failed autosave"

        # Verify raw data unchanged
        raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
        original_email = raw_row.raw_csv_data['email']
        assert original_email == 'john.smith@example.com', "Raw data should be unchanged"

        session.close()

        # Step 4: Generate export preview and CSV
        preview = build_export_preview('failed-autosave-test')
        assert preview.is_export_ready, "Export should be ready (no blockers)"
        assert preview.row_count == 1

        # Step 4b: Generate actual CSV file
        result = generate_export_file(
            'failed-autosave-test',
            export_dir,
            config={'GIVEBUTTER_DATABASE_URL': database_url}
        )

        # Step 5: Read and verify CSV content
        csv_file = Path(result.file_path)
        assert csv_file.exists(), "CSV file should be created"

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            data_rows = list(reader)

        assert len(data_rows) == 1, "Should have 1 data row"

        # Find email column
        email_col_index = header.index('email')

        # Step 5a: Original email should be in CSV
        original_email_in_csv = data_rows[0][email_col_index]
        assert original_email_in_csv == 'john.smith@example.com', \
            f"Original email should be in CSV, got: {original_email_in_csv}"

        # Step 5b: Failed email should NOT be in CSV
        assert 'invalid-email' not in original_email_in_csv, \
            "Failed autosave email should not appear in CSV"

        # Step 6: Verify other fields are present and correct
        name_col_index = header.index('first_name')
        assert data_rows[0][name_col_index] == 'John', "First name should be correct"

        # Step 7: Verify raw data still unchanged after export
        session = Session()
        raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
        assert raw_row.raw_csv_data['email'] == 'john.smith@example.com', \
            "Raw data should remain unchanged after export (append-only principle)"
        session.close()
