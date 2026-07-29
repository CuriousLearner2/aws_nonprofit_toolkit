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
    ImportBatch,
    RawImportRow,
    ReviewItem,
    ReviewItemSubject,
)
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
