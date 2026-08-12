"""Integration tests for address issue reconciliation."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.autosave_service import autosave_row_corrections
from scripts.householder.database_models import (
    Base,
    ImportContact,
    ImportBatch,
    RawImportRow,
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
)
from scripts.householder.database_repository import DatabaseImportRepository
from scripts.householder.issue_recalculation_service import recalculate_row_issues


def _seed_batch(database_url: str, *, raw_row_data: dict[str, str], issue_payload: dict) -> int:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        batch = ImportBatch(
            id="address-integrity-batch",
            filename="address.csv",
            upload_timestamp=datetime.now(timezone.utc),
            status="pending_review",
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(batch_id=batch.id, row_index=1, raw_csv_data=raw_row_data)
        session.add(raw_row)
        session.flush()

        review_item = ReviewItem(
            batch_id=batch.id,
            item_type="validation",
            status="pending",
            confidence=1.0,
            payload_json=issue_payload,
        )
        session.add(review_item)
        session.flush()
        session.add(
            ReviewItemSubject(
                review_item_id=review_item.id,
                subject_type="import_raw_row",
                subject_id=raw_row.id,
                role="primary",
            )
        )
        session.commit()
        return raw_row.id
    finally:
        session.close()


def test_missing_address_is_single_issue_and_clears_on_valid_correction():
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = f"sqlite:///{Path(tmpdir) / 'address.db'}"
        raw_row_id = _seed_batch(
            database_url,
            raw_row_data={"Address 1": ""},
            issue_payload={
                "field": "ADDRESS 1",
                "reason": "missing",
                "severity": "warning",
                "description": "Missing address",
            },
        )

        first = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)
        second = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)

        assert len(first) == 1
        assert first == second
        assert first[0]["description"] == "Missing address"

        autosave_row_corrections(
            "address-integrity-batch",
            raw_row_id,
            {"Address 1": "123 Main St"},
            database_url=database_url,
        )

        after_first = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)
        after_second = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)

        assert after_first == []
        assert after_second == []

        session = sessionmaker(bind=create_engine(database_url))()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_row_id).one()
            assert raw_row.raw_csv_data["Address 1"] == ""
        finally:
            session.close()


def test_populated_contact_address_clears_stale_raw_missing_warning():
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = f"sqlite:///{Path(tmpdir) / 'address-contact.db'}"
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        batch = ImportBatch(
            id='address-contact-batch', filename='address.csv',
            upload_timestamp=datetime.now(timezone.utc), raw_row_count=1,
        )
        session.add(batch)
        session.flush()
        raw = RawImportRow(batch_id=batch.id, row_index=1, raw_csv_data={'Address 1': ''})
        session.add(raw)
        session.flush()
        session.add(ImportContact(
            batch_id=batch.id, raw_import_row_id=raw.id,
            first_name='Address', last_name='Contact',
            address_line1='123 Main St, Springfield, IL 62701',
        ))
        issue = ReviewItem(
            batch_id=batch.id, item_type='validation', status='pending',
            payload_json={'field': 'address', 'reason': 'missing',
                          'severity': 'warning', 'description': 'Missing address'},
        )
        session.add(issue)
        session.flush()
        session.add(ReviewItemSubject(
            review_item_id=issue.id, subject_type='import_raw_row',
            subject_id=raw.id, role='primary',
        ))
        session.commit()
        batch_id = batch.id
        raw_id = raw.id
        session.close()

        assert recalculate_row_issues(batch_id, raw_id, database_url) == []


def test_explicit_blank_address_correction_keeps_source_capable_warning():
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = f"sqlite:///{Path(tmpdir) / 'address-correction.db'}"
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        batch = ImportBatch(
            id='address-correction-batch', filename='address.csv',
            upload_timestamp=datetime.now(timezone.utc), raw_row_count=1,
        )
        session.add(batch)
        session.flush()
        raw = RawImportRow(
            batch_id=batch.id, row_index=1,
            raw_csv_data={'Address 1': '123 Main St, Springfield, IL 62701'},
        )
        session.add(raw)
        session.flush()
        contact = ImportContact(
            batch_id=batch.id, raw_import_row_id=raw.id,
            first_name='Address', last_name='Correction',
            address_line1='123 Main St, Springfield, IL 62701',
        )
        session.add(contact)
        session.flush()
        issue = ReviewItem(
            batch_id=batch.id, item_type='validation', status='pending',
            payload_json={'field': 'address', 'reason': 'missing',
                          'severity': 'warning', 'description': 'Missing address'},
        )
        session.add(issue)
        session.flush()
        session.add(ReviewItemSubject(
            review_item_id=issue.id, subject_type='import_raw_row',
            subject_id=raw.id, role='primary',
        ))
        session.add(ReviewDecision(
            batch_id=batch.id, raw_import_row_id=raw.id,
            decision='accept_issue', reviewed_values={'address': ''},
        ))
        session.commit()
        batch_id = batch.id
        raw_id = raw.id
        session.close()

        issues = recalculate_row_issues(batch_id, raw_id, database_url)
        assert len(issues) == 1
        assert issues[0]['field'] == 'address'
        assert issues[0]['description'] == 'Missing address'
        assert issues[0]['severity'] == 'warning'


def test_source_without_address_field_has_no_warning_and_hides_address():
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = f"sqlite:///{Path(tmpdir) / 'address-absent.db'}"
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        batch = ImportBatch(
            id='address-absent-batch', filename='no-address.csv',
            upload_timestamp=datetime.now(timezone.utc), raw_row_count=1,
        )
        session.add(batch)
        session.flush()
        raw = RawImportRow(
            batch_id=batch.id, row_index=1,
            raw_csv_data={'Name': 'No Address Source', 'Email': 'n@example.com'},
        )
        session.add(raw)
        session.flush()
        session.add(ImportContact(
            batch_id=batch.id, raw_import_row_id=raw.id,
            first_name='No', last_name='Address',
            email='n@example.com', address_line1='Snapshot address',
        ))
        session.commit()
        batch_id = batch.id
        raw_id = raw.id
        session.close()

        assert recalculate_row_issues(batch_id, raw_id, database_url) == []
        row = DatabaseImportRepository(database_url).get_validation(batch_id).validation_rows[0]
        assert row.address_visible is False


def _seed_batch_with_duplicate_address_issues(
    database_url: str,
    *,
    raw_row_data: dict[str, str],
) -> int:
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        batch = ImportBatch(
            id="address-integrity-batch",
            filename="address.csv",
            upload_timestamp=datetime.now(timezone.utc),
            status="pending_review",
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(batch_id=batch.id, row_index=1, raw_csv_data=raw_row_data)
        session.add(raw_row)
        session.flush()

        for index, field in enumerate(("ADDRESS 1", "street address"), start=1):
            review_item = ReviewItem(
                batch_id=batch.id,
                item_type="validation",
                status="pending",
                confidence=1.0,
                payload_json={
                    "field": field,
                    "reason": "missing",
                    "severity": "warning",
                    "description": f"Missing address #{index}",
                },
            )
            session.add(review_item)
            session.flush()
            session.add(
                ReviewItemSubject(
                    review_item_id=review_item.id,
                    subject_type="import_raw_row",
                    subject_id=raw_row.id,
                    role="primary",
                )
            )

        session.commit()
        return raw_row.id
    finally:
        session.close()


def test_non_address_row_does_not_gain_missing_address():
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = f"sqlite:///{Path(tmpdir) / 'no-address.db'}"
        raw_row_id = _seed_batch(
            database_url,
            raw_row_data={"Name": "A"},
            issue_payload={
                "field": "name",
                "reason": "missing",
                "severity": "warning",
                "description": "Missing name",
            },
        )

        issues = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)
        assert all(issue.get("field") != "address" for issue in issues)


def test_duplicate_missing_address_issues_collapse_and_clear_on_valid_correction():
    with tempfile.TemporaryDirectory() as tmpdir:
        database_url = f"sqlite:///{Path(tmpdir) / 'address-duplicates.db'}"
        raw_row_id = _seed_batch_with_duplicate_address_issues(
            database_url,
            raw_row_data={"Address 1": ""},
        )

        first = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)
        second = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)

        assert len(first) == 1
        assert first == second
        assert first[0]["field"].lower() in {"address", "address 1", "street address"}
        assert "Missing address" in first[0]["description"]

        autosave_row_corrections(
            "address-integrity-batch",
            raw_row_id,
            {"Address 1": "123 Main St"},
            database_url=database_url,
        )

        after_correction = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)
        after_reload = recalculate_row_issues("address-integrity-batch", raw_row_id, database_url)

        assert after_correction == []
        assert after_reload == []

        session = sessionmaker(bind=create_engine(database_url))()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_row_id).one()
            assert raw_row.raw_csv_data["Address 1"] == ""
        finally:
            session.close()
