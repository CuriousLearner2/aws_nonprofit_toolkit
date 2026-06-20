"""Integration tests for export preview-to-export consistency.

Verifies that preview counts/warnings/blockers match generated export CSV,
audit snapshot, and download behavior using real database data.
"""

import pytest
import sys
import csv
import tempfile
from pathlib import Path
from datetime import datetime
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ImportContact, ReviewItem, ReviewDecision, AuditLogRecord
)
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.export_file_service import generate_export_file, ExportBlockedError
from sqlalchemy.orm import sessionmaker
import os


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    from scripts.householder.database_models import create_db_engine
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def preview_consistency_db(temp_db, monkeypatch, tmp_path):
    """Database fixture with test data for preview consistency tests."""
    database_url, engine = temp_db

    # Configure app
    app.config['TESTING'] = True
    export_dir = str(tmp_path / "exports")
    os.makedirs(export_dir, exist_ok=True)
    app.config['EXPORT_OUTPUT_DIR'] = export_dir

    # Set environment variable
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')

    yield database_url, engine, export_dir

    # Cleanup
    app.config['EXPORT_OUTPUT_DIR'] = '/tmp/givebutter/exports'


def test_preview_row_count_matches_generated_csv(preview_consistency_db):
    """Preview row_count matches generated CSV data row count."""
    database_url, engine, export_dir = preview_consistency_db

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch with 3 rows
    batch = ImportBatch(
        id='IMP-PREVIEW-001',
        filename='test.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create 3 raw import rows
    rows_data = [
        {'transaction_id': 'TXN-001', 'first_name': 'John', 'last_name': 'Smith', 'email': 'john@test.com', 'amount': '100.00'},
        {'transaction_id': 'TXN-002', 'first_name': 'Jane', 'last_name': 'Doe', 'email': 'jane@test.com', 'amount': '200.00'},
        {'transaction_id': 'TXN-003', 'first_name': 'Bob', 'last_name': 'Jones', 'email': 'bob@test.com', 'amount': '150.00'},
    ]

    raw_rows = []
    for idx, data in enumerate(rows_data, 1):
        row = RawImportRow(
            batch_id='IMP-PREVIEW-001',
            row_index=idx,
            raw_csv_data=data,
        )
        session.add(row)
        raw_rows.append(row)
    session.flush()

    # Create import contacts (3 contacts)
    for idx, data in enumerate(rows_data, 1):
        contact = ImportContact(
            batch_id='IMP-PREVIEW-001',
            raw_import_row_id=raw_rows[idx-1].id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            amount=float(data['amount']),
        )
        session.add(contact)
    session.commit()

    # Build preview
    preview = build_export_preview('IMP-PREVIEW-001', config={'GIVEBUTTER_DATABASE_URL': database_url})

    # Verify preview has correct row count
    assert preview.row_count == 3, f"Expected 3 rows in preview, got {preview.row_count}"

    # Generate export
    result = generate_export_file(
        import_id='IMP-PREVIEW-001',
        output_dir=export_dir,
        reviewer='test_user',
        config={'GIVEBUTTER_DATABASE_URL': database_url},
    )

    # Read generated CSV
    with open(result.file_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()

    csv_rows = list(csv.reader(StringIO(csv_content)))
    # CSV has header + data rows
    data_row_count = len(csv_rows) - 1

    # Verify CSV row count matches preview
    assert data_row_count == preview.row_count, (
        f"CSV data row count {data_row_count} does not match preview row_count {preview.row_count}"
    )

    # Verify audit stores correct row count
    assert result.row_count == preview.row_count, (
        f"Result row_count {result.row_count} does not match preview row_count {preview.row_count}"
    )

    session.close()


def test_preview_counts_match_audit_snapshot(preview_consistency_db):
    """Preview counts match audit snapshot (warning_count, blocked_count, row_count)."""
    database_url, engine, export_dir = preview_consistency_db

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch with 2 rows
    batch = ImportBatch(
        id='IMP-COUNTS-001',
        filename='test.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create 2 raw import rows
    rows_data = [
        {'transaction_id': 'TXN-001', 'first_name': 'Alice', 'last_name': 'A', 'email': 'alice@test.com', 'amount': '100.00'},
        {'transaction_id': 'TXN-002', 'first_name': 'Bob', 'last_name': 'B', 'email': 'bob@test.com', 'amount': '200.00'},
    ]

    raw_rows = []
    for idx, data in enumerate(rows_data, 1):
        row = RawImportRow(
            batch_id='IMP-COUNTS-001',
            row_index=idx,
            raw_csv_data=data,
        )
        session.add(row)
        raw_rows.append(row)
    session.flush()

    # Create import contacts
    for idx, data in enumerate(rows_data, 1):
        contact = ImportContact(
            batch_id='IMP-COUNTS-001',
            raw_import_row_id=raw_rows[idx-1].id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            amount=float(data['amount']),
        )
        session.add(contact)
    session.commit()

    # Build preview
    preview = build_export_preview('IMP-COUNTS-001', config={'GIVEBUTTER_DATABASE_URL': database_url})

    # Generate export
    result = generate_export_file(
        import_id='IMP-COUNTS-001',
        output_dir=export_dir,
        reviewer='test_user',
        config={'GIVEBUTTER_DATABASE_URL': database_url},
    )

    # Fetch audit record
    record = session.query(AuditLogRecord).filter_by(id=result.audit_log_id).first()
    assert record is not None, f"Audit record not found: id={result.audit_log_id}"

    audit_details = record.details

    # Verify counts match
    assert audit_details['row_count'] == preview.row_count, (
        f"Audit row_count {audit_details['row_count']} does not match preview {preview.row_count}"
    )
    assert audit_details['warning_count'] == preview.warning_count, (
        f"Audit warning_count {audit_details['warning_count']} does not match preview {preview.warning_count}"
    )
    assert audit_details['blocked_count'] == preview.blocked_count, (
        f"Audit blocked_count {audit_details['blocked_count']} does not match preview {preview.blocked_count}"
    )

    session.close()


def test_preview_deferred_counts_match_audit_snapshot(preview_consistency_db):
    """Preview deferred_validation_count matches audit snapshot."""
    database_url, engine, export_dir = preview_consistency_db

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-DEFERRED-001',
        filename='test.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create 1 raw import row
    row = RawImportRow(
        batch_id='IMP-DEFERRED-001',
        row_index=1,
        raw_csv_data={'transaction_id': 'TXN-001', 'first_name': 'Test', 'last_name': 'User', 'email': 'test@test.com', 'amount': '100.00'},
    )
    session.add(row)
    session.flush()

    # Create import contact
    contact = ImportContact(
        batch_id='IMP-DEFERRED-001',
        raw_import_row_id=row.id,
        first_name='Test',
        last_name='User',
        email='test@test.com',
        amount=100.00,
    )
    session.add(contact)

    # Create validation review item with deferred decision
    val_item = ReviewItem(
        batch_id='IMP-DEFERRED-001',
        item_type='validation',
        status='pending',
        payload_json={'issue_type': 'missing_phone', 'issue': 'Phone missing'},
    )
    session.add(val_item)
    session.flush()

    # Create deferred review decision
    decision = ReviewDecision(
        batch_id='IMP-DEFERRED-001',
        review_item_id=val_item.id,
        decision='defer',
        reviewer='test_user',
    )
    session.add(decision)
    session.commit()

    # Build preview
    preview = build_export_preview('IMP-DEFERRED-001', config={'GIVEBUTTER_DATABASE_URL': database_url})

    # Verify preview shows deferred validation count
    assert preview.deferred_validation_count > 0, (
        f"Expected deferred validation count > 0, got {preview.deferred_validation_count}"
    )

    # Generate export with confirmation
    result = generate_export_file(
        import_id='IMP-DEFERRED-001',
        output_dir=export_dir,
        reviewer='test_user',
        config={'GIVEBUTTER_DATABASE_URL': database_url},
        confirmed_unresolved_validations=True,
    )

    # Fetch audit record
    record = session.query(AuditLogRecord).filter_by(id=result.audit_log_id).first()
    assert record is not None

    audit_details = record.details
    audit_deferred_counts = audit_details.get('deferred_counts', {})

    # Verify deferred counts match
    assert audit_deferred_counts.get('deferred_validation_count') == preview.deferred_validation_count, (
        f"Audit deferred_validation_count {audit_deferred_counts.get('deferred_validation_count')} "
        f"does not match preview {preview.deferred_validation_count}"
    )

    # Verify confirmation flag is set
    assert audit_details['confirmations'].get('confirmed_unresolved_validations') is True, (
        "Audit confirmation flag not set"
    )

    session.close()


def test_preview_warning_counts_match_audit_snapshot(preview_consistency_db):
    """Preview warning_count matches audit snapshot (not just blockers)."""
    database_url, engine, export_dir = preview_consistency_db

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-WARN-001',
        filename='test.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create raw import row
    row = RawImportRow(
        batch_id='IMP-WARN-001',
        row_index=1,
        raw_csv_data={'transaction_id': 'TXN-001', 'first_name': 'Test', 'last_name': 'User', 'email': 'test@test.com', 'amount': '100.00'},
    )
    session.add(row)
    session.flush()

    # Create import contact
    contact = ImportContact(
        batch_id='IMP-WARN-001',
        raw_import_row_id=row.id,
        first_name='Test',
        last_name='User',
        email='test@test.com',
        amount=100.00,
    )
    session.add(contact)

    # Create validation review item (generates warning, not blocker)
    val_item = ReviewItem(
        batch_id='IMP-WARN-001',
        item_type='validation',
        status='pending',
        payload_json={'issue_type': 'missing_phone', 'issue': 'Phone missing'},
    )
    session.add(val_item)
    session.commit()

    # Build preview
    preview = build_export_preview('IMP-WARN-001', config={'GIVEBUTTER_DATABASE_URL': database_url})

    # Verify preview shows warnings (export_ready=True but has warning_count)
    assert preview.is_export_ready is True, (
        "Unresolved validation should not block export, only warn"
    )
    assert preview.warning_count > 0, (
        f"Expected warning_count > 0, got {preview.warning_count}"
    )

    # Generate export (succeeds despite warnings)
    result = generate_export_file(
        import_id='IMP-WARN-001',
        output_dir=export_dir,
        reviewer='test_user',
        config={'GIVEBUTTER_DATABASE_URL': database_url},
    )

    # Fetch audit record
    record = session.query(AuditLogRecord).filter_by(id=result.audit_log_id).first()
    assert record is not None

    audit_details = record.details

    # Verify warning count matches preview
    assert audit_details['warning_count'] == preview.warning_count, (
        f"Audit warning_count {audit_details['warning_count']} does not match preview {preview.warning_count}"
    )

    # Verify export was created successfully
    assert os.path.exists(result.file_path), "Export file should be created despite warnings"

    session.close()


def test_deferred_validation_blocks_export_without_confirmation(preview_consistency_db):
    """Deferred validation items block export until confirmed."""
    database_url, engine, export_dir = preview_consistency_db

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='IMP-DEFER-TEST-001',
        filename='test.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create raw import row
    row = RawImportRow(
        batch_id='IMP-DEFER-TEST-001',
        row_index=1,
        raw_csv_data={'transaction_id': 'TXN-001', 'first_name': 'Test', 'last_name': 'User', 'email': 'test@test.com', 'amount': '100.00'},
    )
    session.add(row)
    session.flush()

    # Create import contact
    contact = ImportContact(
        batch_id='IMP-DEFER-TEST-001',
        raw_import_row_id=row.id,
        first_name='Test',
        last_name='User',
        email='test@test.com',
        amount=100.00,
    )
    session.add(contact)

    # Create validation review item
    val_item = ReviewItem(
        batch_id='IMP-DEFER-TEST-001',
        item_type='validation',
        status='pending',
        payload_json={'issue_type': 'missing_phone', 'issue': 'Phone missing'},
    )
    session.add(val_item)
    session.flush()

    # Create deferred decision
    decision = ReviewDecision(
        batch_id='IMP-DEFER-TEST-001',
        review_item_id=val_item.id,
        decision='defer',
        reviewer='test_user',
    )
    session.add(decision)
    session.commit()

    # Build preview
    preview = build_export_preview('IMP-DEFER-TEST-001', config={'GIVEBUTTER_DATABASE_URL': database_url})

    # Verify preview shows deferred items
    assert preview.deferred_validation_count > 0, (
        f"Expected deferred_validation_count > 0, got {preview.deferred_validation_count}"
    )

    # Attempt export WITHOUT confirmation; should fail
    from scripts.householder.export_file_service import ExportUnresolvedValidationWarningError
    with pytest.raises(ExportUnresolvedValidationWarningError) as exc_info:
        generate_export_file(
            import_id='IMP-DEFER-TEST-001',
            output_dir=export_dir,
            reviewer='test_user',
            config={'GIVEBUTTER_DATABASE_URL': database_url},
            confirmed_unresolved_validations=False,
        )

    assert exc_info.value.deferred_count > 0

    # Verify no export was created yet
    audit_records = session.query(AuditLogRecord).filter_by(batch_id='IMP-DEFER-TEST-001').all()
    assert len(audit_records) == 0, "No audit record should exist before confirmation"

    # Now export WITH confirmation; should succeed
    result = generate_export_file(
        import_id='IMP-DEFER-TEST-001',
        output_dir=export_dir,
        reviewer='test_user',
        config={'GIVEBUTTER_DATABASE_URL': database_url},
        confirmed_unresolved_validations=True,
    )

    # Verify export file was created
    assert os.path.exists(result.file_path), f"Export file not created: {result.file_path}"

    # Verify audit record was created with confirmation flag
    record = session.query(AuditLogRecord).filter_by(id=result.audit_log_id).first()
    assert record is not None
    assert record.details['confirmations']['confirmed_unresolved_validations'] is True, (
        "Confirmation flag should be True in audit record"
    )

    session.close()


def test_generated_csv_includes_row_level_reviewed_values(preview_consistency_db):
    """Generated CSV uses row-level ReviewDecision effective values, not raw values."""
    database_url, engine, export_dir = preview_consistency_db

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch with 1 row
    batch = ImportBatch(
        id='IMP-EFFECTIVE-001',
        filename='test_effective.csv',
        upload_timestamp=datetime.utcnow(),
    )
    session.add(batch)
    session.flush()

    # Create raw import row with original values
    raw_data = {
        'transaction_id': 'TXN-EFFECTIVE-001',
        'first_name': 'John',
        'last_name': 'Smith',
        'email': 'john.smith@example.com',
        'amount': '100.00',
    }
    raw_row = RawImportRow(
        batch_id='IMP-EFFECTIVE-001',
        row_index=1,
        raw_csv_data=raw_data,
    )
    session.add(raw_row)
    session.flush()

    # Create import contact from raw values
    contact = ImportContact(
        batch_id='IMP-EFFECTIVE-001',
        raw_import_row_id=raw_row.id,
        first_name=raw_data['first_name'],
        last_name=raw_data['last_name'],
        email=raw_data['email'],
        amount=float(raw_data['amount']),
    )
    session.add(contact)
    session.flush()

    # Create row-level ReviewDecision with reviewed/corrected values
    reviewed_email = 'corrected.email@example.com'
    reviewed_amount = 350.75
    row_decision = ReviewDecision(
        batch_id='IMP-EFFECTIVE-001',
        raw_import_row_id=raw_row.id,
        review_item_id=None,  # Row-level decision
        decision='accept',
        reviewed_values={'email': reviewed_email, 'amount': reviewed_amount}
    )
    session.add(row_decision)
    session.commit()

    # Generate export
    result = generate_export_file(
        import_id='IMP-EFFECTIVE-001',
        output_dir=export_dir,
        reviewer='test_user',
        config={'GIVEBUTTER_DATABASE_URL': database_url},
    )

    # Read generated CSV
    with open(result.file_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()

    csv_rows = list(csv.reader(StringIO(csv_content)))
    headers = csv_rows[0]
    data_row = csv_rows[1]  # First and only data row

    # Verify effective email appears in CSV
    email_idx = headers.index('email') if 'email' in headers else headers.index('Email')
    assert data_row[email_idx] == reviewed_email, (
        f"CSV should contain reviewed email '{reviewed_email}', got '{data_row[email_idx]}'"
    )

    # Verify effective amount appears in CSV (formatted as string)
    amount_idx = headers.index('amount') if 'amount' in headers else headers.index('Amount')
    csv_amount_str = data_row[amount_idx]
    # Amount might be formatted as "350.75" or "$350.75"
    assert reviewed_amount == float(csv_amount_str.replace('$', '').replace(',', '')), (
        f"CSV should contain reviewed amount {reviewed_amount}, got '{csv_amount_str}'"
    )

    # Verify raw data is unchanged
    modified_row = session.query(RawImportRow).filter_by(id=raw_row.id).first()
    assert modified_row.raw_csv_data.get('email') == raw_data['email'], (
        "Raw data should not be modified"
    )
    assert modified_row.raw_csv_data.get('amount') == raw_data['amount'], (
        "Raw data should not be modified"
    )

    session.close()
