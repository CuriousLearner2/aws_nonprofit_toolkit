"""Parity tests for email/phone validator results and issue projection."""

import csv
import pytest

from scripts.householder.database_models import ImportContact, ReviewItem, get_session, init_db
from scripts.householder.ingestion_service import ingest_processed_csv
from scripts.householder.issue_recalculation_service import _validate_effective_values
from scripts.householder.phone_validation_service import build_phone_validation_issue, validate_review_phone

@pytest.mark.parametrize(
    ("value", "expected_severity"),
    [("(415) 555-1234", None), ("+44 20 7946 0958", None), ("555", "warning"), ("not a phone", "error")],
)
def test_phone_projection_preserves_canonical_result(value, expected_severity):
    result = validate_review_phone(value, allow_blank=False, default_region="US")
    issue = build_phone_validation_issue(value)
    actual = "warning" if result.warnings else "error" if not result.valid else None
    assert actual == expected_severity
    assert (issue or {}).get("severity") == expected_severity


@pytest.mark.parametrize(
    ("field", "value", "expected_severity"),
    [("phone", "555", "warning"), ("phone", "not a phone", "error")],
)
def test_recalculation_projection_matches_canonical_validator(field, value, expected_severity):
    issues = _validate_effective_values({field: value})
    field_issues = [issue for issue in issues if issue.get("field") == field]
    assert len(field_issues) == 1
    assert field_issues[0]["severity"] == expected_severity


def test_recalculation_keeps_canonical_warning_message_stable():
    first = _validate_effective_values({"phone": "555"})
    second = _validate_effective_values({"phone": "555"})
    assert first == second
    assert first[0]["description"] == validate_review_phone("555").warnings[0]


@pytest.mark.parametrize(
    ("phone", "expected_severity"),
    [("+44 20 7946 0958", None), ("555", "warning"), ("not a phone", "error")],
)
def test_ingestion_uses_canonical_phone_projection(tmp_path, phone, expected_severity):
    csv_path = tmp_path / "phones.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "Donation ID", "Date", "Donor Name", "Email", "Phone", "Amount",
            "Validation_Tier", "Issues", "Suggested_Modifications",
        ])
        writer.writeheader()
        writer.writerow({
            "Donation ID": "PHONE-1", "Date": "2026-06-12", "Donor Name": "Phone Example",
            "Email": "phone@example.com", "Phone": phone, "Amount": "10.00",
            "Validation_Tier": "FAIL", "Issues": "Phone: stale processor classification",
            "Suggested_Modifications": "",
        })

    database_url = f"sqlite:///{tmp_path / 'phones.db'}"
    init_db(database_url)
    result = ingest_processed_csv(str(csv_path), "phones.csv", database_url)
    session = get_session(init_db(database_url))
    try:
        contact = session.query(ImportContact).filter_by(batch_id=result.batch_id).one()
        expected_contact_phone = "".join(character for character in phone if character.isdigit()) or None
        assert contact.phone == expected_contact_phone
        items = session.query(ReviewItem).filter_by(
            batch_id=result.batch_id, item_type="validation"
        ).all()
        phone_items = [item for item in items if item.payload_json.get("field") == "Phone"]
        if expected_severity is None:
            assert phone_items == []
        else:
            assert len(phone_items) == 1
            assert phone_items[0].payload_json["severity"] == expected_severity
    finally:
        session.close()
