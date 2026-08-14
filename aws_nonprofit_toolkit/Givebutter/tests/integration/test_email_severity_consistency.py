"""Regression coverage for canonical email issue severity across ingestion/recalculation."""

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ReviewItem,
    ReviewItemSubject,
)
from scripts.householder.ingestion_service import ingest_processed_csv
from scripts.householder.issue_recalculation_service import recalculate_row_issues


@pytest.mark.parametrize(
    "email, expected_severity",
    [
        ("alice@", "error"),
        ("@gmail.com", "error"),
        ("alice@@gmail.com", "error"),
        ("alice@gmai.com", "warning"),
        ("alice@gmal.com", "warning"),
        ("alice@gmial.com", "warning"),
        ("alice@gmail.com", None),
    ],
)
def test_recalculation_reclassifies_stale_email_severity_and_is_stable(
    tmp_path: Path, email: str, expected_severity: str | None
):
    database_url = f"sqlite:///{tmp_path / 'email-severity.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        batch = ImportBatch(
            id="email-severity-batch",
            filename="emails.csv",
            upload_timestamp=datetime.now(timezone.utc),
            status="pending_review",
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()
        raw_row = RawImportRow(
            batch_id=batch.id,
            row_index=1,
            raw_csv_data={"email": email},
        )
        session.add(raw_row)
        session.flush()
        issue = ReviewItem(
            batch_id=batch.id,
            item_type="validation",
            status="pending",
            confidence=1.0,
            payload_json={
                "field": "email",
                "reason": "possible_typo",
                "description": "stale imported email issue",
                "severity": "error",
            },
        )
        session.add(issue)
        session.flush()
        session.add(
            ReviewItemSubject(
                review_item_id=issue.id,
                subject_type="import_raw_row",
                subject_id=raw_row.id,
                role="primary",
            )
        )
        session.commit()
        row_id = raw_row.id
    finally:
        session.close()

    first = recalculate_row_issues("email-severity-batch", row_id, database_url)
    second = recalculate_row_issues("email-severity-batch", row_id, database_url)
    assert first == second
    if expected_severity is None:
        assert not [item for item in first if item.get("field") == "email"]
    else:
        email_issues = [item for item in first if item.get("field") == "email"]
        assert len(email_issues) == 1
        assert email_issues[0]["severity"] == expected_severity


@pytest.mark.parametrize(
    "email, processed_tier, expected_severity",
    [
        ("alice@", "FAIL", "error"),
        ("@gmail.com", "FAIL", "error"),
        ("alice@@gmail.com", "FAIL", "error"),
        ("alice@gmai.com", "FAIL", "warning"),
        ("alice@gmal.com", "FAIL", "warning"),
        ("alice@gmial.com", "FAIL", "warning"),
        ("alice@gmail.com", "FAIL", None),
    ],
)
def test_ingestion_uses_canonical_email_severity_and_drops_stale_valid_issue(
    tmp_path: Path, email: str, processed_tier: str, expected_severity: str | None
):
    csv_path = tmp_path / "emails.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Donation ID",
                "Date",
                "Donor Name",
                "Email",
                "Phone",
                "Amount",
                "Validation_Tier",
                "Issues",
                "Suggested_Modifications",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Donation ID": "EMAIL-1",
                "Date": "2026-06-12",
                "Donor Name": "Alice Example",
                "Email": email,
                "Phone": "4155551234",
                "Amount": "100.00",
                "Validation_Tier": processed_tier,
                "Issues": "Email: stale processor classification",
                "Suggested_Modifications": "",
            }
        )

    database_url = f"sqlite:///{tmp_path / 'ingestion.db'}"
    from scripts.householder.database_models import init_db, get_session, ImportContact

    init_db(database_url)
    result = ingest_processed_csv(str(csv_path), "emails.csv", database_url)
    assert result.status == "success"

    session = get_session(init_db(database_url))
    try:
        contact = session.query(ImportContact).filter_by(batch_id=result.batch_id).one()
        assert contact.email == email
        items = session.query(ReviewItem).filter_by(
            batch_id=result.batch_id, item_type="validation"
        ).all()
        email_items = [item for item in items if item.payload_json.get("field") == "Email"]
        if expected_severity is None:
            assert email_items == []
        else:
            assert len(email_items) == 1
            assert email_items[0].payload_json["severity"] == expected_severity
    finally:
        session.close()
