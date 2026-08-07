"""Database-backed UAT regressions for editable phone and date validation."""

from io import BytesIO
import csv

from scripts.householder.autosave_service import get_effective_values
from scripts.householder.database_models import ReviewDecision, create_db_engine
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.readiness_service import get_export_readiness
from scripts.householder.validation_service import get_validation_review
from scripts.householder.phone_validation_service import validate_review_phone
from sqlalchemy.orm import sessionmaker


def _config(database_url):
    return {
        "HOUSEHOLDER_REPOSITORY": "database",
        "GIVEBUTTER_DATABASE_URL": database_url,
    }


def _upload_three_row_batch(client, field, invalid_value):
    rows = {
        "phone": [
            ["Target", "target@example.com", invalid_value, "100.00", "2026-06-12", "123 Main St", "TXN001"],
            ["Isolation", "isolation@example.com", "(415) 555-2671", "200.00", "2026-06-13", "", "TXN002"],
            ["Control", "control@example.com", "(415) 555-2672", "300.00", "2026-06-14", "456 Oak St", "TXN003"],
        ],
        "date": [
            ["Target", "target@example.com", "(415) 555-2670", "100.00", invalid_value, "123 Main St", "TXN001"],
            ["Isolation", "isolation@example.com", "(415) 555-2671", "200.00", "2026-06-13", "", "TXN002"],
            ["Control", "control@example.com", "(415) 555-2672", "300.00", "2026-06-14", "456 Oak St", "TXN003"],
        ],
    }[field]
    csv_text = "Name,Email,Phone,Amount,Date,Address 1,Transaction ID\n"
    csv_text += "\n".join(",".join(row) for row in rows) + "\n"
    response = client.post(
        "/upload",
        data={"file": (BytesIO(csv_text.encode("utf-8")), f"{field}-validation.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["batch_id"]


def _row(validation, name):
    return next(row for row in validation["validation_issues"] if row["name"] == name)


def _assert_issue(row, field, severity):
    matches = [issue for issue in row["issues"] if issue.get("field") == field]
    assert len(matches) == 1, row["issues"]
    assert matches[0]["severity"] == severity


def _run_field_regression(client, database_url, tmp_path, field, invalid_value, corrected_value):
    config = _config(database_url)
    batch_id = _upload_three_row_batch(client, field, invalid_value)
    validation_before = get_validation_review(batch_id, config=config)
    target_before = _row(validation_before, "Target")
    isolation_before = _row(validation_before, "Isolation")
    control_before = _row(validation_before, "Control")
    _assert_issue(target_before, field, "error")
    _assert_issue(isolation_before, "address", "warning")
    assert not any(issue.get("field") == "address" for issue in target_before["issues"])
    assert not any(issue.get("field") == "address" for issue in control_before["issues"])
    target_raw_id = target_before["raw_import_row_id"]

    readiness_before = get_export_readiness(batch_id, config=config)
    assert readiness_before.is_export_ready is False
    assert readiness_before.blocker_count > 0
    approval_before = client.post(
        f"/imports/{batch_id}/approve-batch",
        json={"approval_status": "approved"},
    )
    assert approval_before.status_code == 400

    correction = client.post(
        f"/imports/{batch_id}/autosave",
        json={"raw_import_row_id": target_raw_id, "corrected_values": {field: corrected_value}},
    )
    assert correction.status_code == 200, correction.get_json()
    correction_data = correction.get_json()
    assert not any(issue.get("field") == field for issue in correction_data["issues"]), correction_data
    isolation_check = _row(get_validation_review(batch_id, config=config), "Isolation")
    assert any(issue.get("field") == "address" for issue in isolation_check["issues"])

    validation_after = get_validation_review(batch_id, config=config)
    target_after = _row(validation_after, "Target")
    isolation_after = _row(validation_after, "Isolation")
    control_after = _row(validation_after, "Control")
    assert not any(issue.get("field") == field for issue in target_after["issues"])
    _assert_issue(isolation_after, "address", "warning")
    assert not any(issue.get("field") == "address" for issue in target_after["issues"])
    assert not any(issue.get("field") == "address" for issue in control_after["issues"])
    assert isolation_after["issues"] == isolation_before["issues"]
    assert control_after["issues"] == control_before["issues"]

    with client.application.test_client() as reloaded_client:
        page = reloaded_client.get(f"/imports/{batch_id}/validation")
        assert page.status_code == 200
        assert corrected_value in page.data.decode("utf-8")

    effective = get_effective_values(batch_id, target_raw_id, database_url)
    assert effective[field] == corrected_value
    disposition = client.post(
        f"/imports/{batch_id}/row-decision",
        json={
            "raw_import_row_id": isolation_after["raw_import_row_id"],
            "decision": "accept_as_is",
            "notes": "Reviewed remaining address warning",
            "reviewer_name": "UAT Reviewer",
            "interaction_sequence": 1,
        },
    )
    assert disposition.status_code == 200, disposition.get_json()
    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        decisions = [
            decision for decision in session.query(ReviewDecision).filter_by(raw_import_row_id=target_raw_id).all()
            if field in (decision.reviewed_values or {})
        ]
        assert len(decisions) == 1
        assert decisions[0].reviewed_values[field] == corrected_value
    finally:
        session.close()

    readiness_after = get_export_readiness(batch_id, config=config)
    assert readiness_after.is_export_ready is True
    assert readiness_after.blocker_count == 0
    assert readiness_after.warning_count > 0
    approval_after = client.post(
        f"/imports/{batch_id}/approve-batch",
        json={"approval_status": "approved"},
    )
    assert approval_after.status_code == 200, approval_after.get_json()

    preview = build_export_preview(batch_id, config=config)
    assert preview.is_export_ready is True
    preview_rows = [row.to_dict() for row in preview.export_rows]
    target_preview = next(row for row in preview_rows if row["first_name"] == "Target")
    isolation_preview = next(row for row in preview_rows if row["first_name"] == "Isolation")
    control_preview = next(row for row in preview_rows if row["first_name"] == "Control")
    assert target_preview[field] == corrected_value
    assert isolation_preview["first_name"] == "Isolation"
    assert control_preview["first_name"] == "Control"

    export_dir = tmp_path / f"{field}-exports"
    export_dir.mkdir()
    client.application.config["EXPORT_OUTPUT_DIR"] = str(export_dir)
    generated = client.post(f"/imports/{batch_id}/exports/generate")
    assert generated.status_code == 200, generated.get_json()
    downloaded = client.get(
        f"/imports/{batch_id}/exports/download/{generated.get_json()['file']['audit_log_id']}"
    )
    assert downloaded.status_code == 200
    csv_rows = list(csv.DictReader(downloaded.data.decode("utf-8").splitlines()))
    csv_by_name = {row["first_name"]: row for row in csv_rows}
    assert csv_by_name["Target"][field] == target_preview[field]
    assert csv_by_name["Isolation"][field] == isolation_preview[field]
    assert csv_by_name["Control"][field] == control_preview[field]


def test_database_phone_validation_isolated_from_address_warning(
    client_with_database, test_db_path, tmp_path
):
    _run_field_regression(
        client_with_database,
        test_db_path,
        tmp_path,
        field="phone",
        invalid_value="555",
        corrected_value="(415) 555-1234",
    )


def test_database_date_validation_isolated_from_address_warning(
    client_with_database, test_db_path, tmp_path
):
    _run_field_regression(
        client_with_database,
        test_db_path,
        tmp_path,
        field="date",
        invalid_value="2026&05-15",
        corrected_value="2026-05-15",
    )


def test_canonical_phone_validation_accepts_jamaica_nanp_and_us_numbers():
    jamaica = validate_review_phone("(876) 543-1810")
    us = validate_review_phone("(415) 555-2671")
    invalid = validate_review_phone("123")

    assert jamaica.valid is True
    assert us.valid is True
    assert invalid.valid is False
    assert invalid.blocking_error == "Invalid phone format"
