"""Database-backed UAT regression for correcting and reloading an email issue."""

from io import BytesIO
import csv
import json

from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import (
    ImportBatch,
    ImportContact,
    RawImportRow,
    ReviewDecision,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from scripts.householder.readiness_service import get_export_readiness
from scripts.householder.validation_service import get_validation_review
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.export_file_service import _encode_csv_field
from scripts.householder.approval_service import get_batch_approval_status


CSV = (
    "Name,Email,Phone,Amount,Date,Transaction ID,Address 1\n"
    "Malformed,not-an-email,5551234567,100.00,2026-06-12,TXN001,\n"
    "Control,control@example.com,5559876543,200.00,2026-06-13,TXN002,456 Oak Ave\n"
)


def _database_config(database_url):
    return {
        "HOUSEHOLDER_REPOSITORY": "database",
        "GIVEBUTTER_DATABASE_URL": database_url,
    }


def test_invalid_email_correction_persists_through_approval_and_export(
    client_with_database, test_db_path, tmp_path
):
    client = client_with_database
    database_url = test_db_path
    config = _database_config(database_url)

    upload = client.post(
        "/upload",
        data={"file": (BytesIO(CSV.encode("utf-8")), "email-persistence.csv")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200, upload.get_json()
    upload_data = upload.get_json()
    batch_id = upload_data["batch_id"]
    assert upload_data["raw_row_count"] == 2

    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        rows = session.query(RawImportRow).filter_by(batch_id=batch_id).order_by(RawImportRow.row_index).all()
        contacts = session.query(ImportContact).filter_by(batch_id=batch_id).order_by(ImportContact.id).all()
        email_items = []
        for item, subject in session.query(ReviewItem, ReviewItemSubject).join(ReviewItemSubject).filter(
            ReviewItem.batch_id == batch_id,
            ReviewItem.item_type == "validation",
        ).all():
            if str((item.payload_json or {}).get("field", "")).lower() == "email":
                email_items.append((item, subject))
        assert len(rows) == len(contacts) == 2
        assert len(email_items) == 1
        review_item, subject = email_items[0]
        malformed_contact = next(contact for contact in contacts if contact.email == "not-an-email")
        assert subject.subject_id == malformed_contact.id
        assert rows[0].raw_csv_data["Email"] == "not-an-email"
    finally:
        session.close()

    readiness_before = get_export_readiness(batch_id, config=config)
    assert readiness_before.is_export_ready is False
    assert readiness_before.blocker_count > 0

    approval_before = client.post(
        f"/imports/{batch_id}/approve-batch",
        json={"approval_status": "approved"},
    )
    assert approval_before.status_code == 400
    assert "unresolved issues" in approval_before.get_json()["error"]

    correction = client.post(
        f"/imports/{batch_id}/validation/{review_item.id}/save-correction",
        json={"reviewed_values": {"email": "corrected@example.com"}},
    )
    assert correction.status_code == 200, correction.get_json()
    assert correction.get_json()["success"] is True

    # A new request/application read must see the persisted effective value.
    with client.application.test_client() as reloaded_client:
        readiness_after_response = reloaded_client.get(f"/imports/{batch_id}/readiness")
        assert readiness_after_response.status_code == 200

    corrected_review = get_validation_review(batch_id, config=config)
    corrected_row = next(
        row for row in corrected_review["validation_issues"]
        if row["name"] == "Malformed"
    )
    assert corrected_row["issues"] == [
        {"field": "address", "reason": "Missing address", "severity": "warning"}
    ]
    disposition = client.post(
        f"/imports/{batch_id}/row-decision",
        json={
            "raw_import_row_id": corrected_row["raw_import_row_id"],
            "decision": "accept_as_is",
            "notes": "Reviewed remaining address warning",
            "reviewer_name": "UAT Reviewer",
            "interaction_sequence": 1,
        },
    )
    assert disposition.status_code == 200, disposition.get_json()

    readiness_after = get_export_readiness(batch_id, config=config)
    assert readiness_after.is_export_ready is True
    assert readiness_after.blocker_count == 0

    validation = get_validation_review(batch_id, config=config)
    validation_rows = validation["validation_issues"]
    corrected_row = next(row for row in validation_rows if row["name"] == "Malformed")
    control_row = next(row for row in validation_rows if row["name"] == "Control")
    assert corrected_row["email"] == "corrected@example.com"
    assert corrected_row["issues"] == [
        {"field": "address", "reason": "Missing address", "severity": "warning"}
    ]
    assert control_row["email"] == "control@example.com"

    approval = client.post(
        f"/imports/{batch_id}/approve-batch",
        json={"approval_status": "approved"},
    )
    assert approval.status_code == 200, approval.get_json()
    assert approval.get_json()["success"] is True
    assert approval.get_json()["approval_status"] == "approved"

    with client.application.test_client() as reloaded_client:
        preview_response = reloaded_client.post(f"/imports/{batch_id}/exports/preview")
        assert preview_response.status_code == 200
        reloaded_approval = get_batch_approval_status(batch_id, database_url=database_url)
        assert reloaded_approval["approval_status"] == "approved"

    preview = build_export_preview(batch_id, config=config)
    assert preview.is_export_ready is True
    assert preview.blocked_count == 0
    assert preview.row_count == 2
    preview_rows = [row.to_dict() for row in preview.export_rows]
    assert [row["email"] for row in preview_rows] == [
        "corrected@example.com",
        "control@example.com",
    ]

    preview_marker = "const preview = "
    preview_start = preview_response.data.decode("utf-8").index(preview_marker) + len(preview_marker)
    preview_end = preview_response.data.decode("utf-8").index(";\n", preview_start)
    preview_payload = json.loads(preview_response.data.decode("utf-8")[preview_start:preview_end])
    assert preview_payload["row_count"] == 2
    assert preview_payload["blocked_count"] == 0
    preview_payload_rows = [
        {key: value for key, value in row.items() if key != "export_derived_at"}
        for row in preview_payload["export_rows"]
    ]
    expected_preview_rows = [
        {key: value for key, value in row.items() if key != "export_derived_at"}
        for row in preview_rows
    ]
    expected_preview_rows = json.loads(json.dumps(expected_preview_rows))
    assert preview_payload_rows == expected_preview_rows
    assert [row["email"] for row in preview_payload["export_rows"]] == [
        "corrected@example.com",
        "control@example.com",
    ]

    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    client.application.config["EXPORT_OUTPUT_DIR"] = str(export_dir)
    generated = client.post(f"/imports/{batch_id}/exports/generate")
    assert generated.status_code == 200, generated.get_json()
    generated_data = generated.get_json()
    assert generated_data["status"] == "success"
    assert generated_data["file"]["row_count"] == 2

    downloaded = client.get(
        f"/imports/{batch_id}/exports/download/{generated_data['file']['audit_log_id']}"
    )
    assert downloaded.status_code == 200
    downloaded_rows = list(csv.DictReader(downloaded.data.decode("utf-8").splitlines()))
    expected_columns = [
        "source_row_index", "transaction_id", "date", "first_name", "last_name", "email", "phone",
        "address_line1", "address_line2", "city", "state", "postal_code", "amount",
        "validation_status", "validation_issues", "normalized_fields", "normalization_warnings",
        "duplicate_group_id", "duplicate_decision", "duplicate_warnings", "household_group_id",
        "household_group_label", "household_members", "household_decision", "household_warnings",
        "export_warnings",
    ]
    assert list(downloaded_rows[0]) == expected_columns
    assert downloaded_rows == [
        {
            key: _encode_csv_field(row[key])
            for key in expected_columns
        }
        for row in preview_payload["export_rows"]
    ]
    assert [row["email"] for row in downloaded_rows] == [
        "corrected@example.com",
        "control@example.com",
    ]

    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        batch = session.query(ImportBatch).filter_by(id=batch_id).one()
        assert batch.approval_status == "approved"
        decision = session.query(ReviewDecision).filter_by(review_item_id=review_item.id).one()
        assert decision.reviewed_values == {"email": "corrected@example.com"}
        persisted_contact = session.query(ImportContact).filter_by(id=subject.subject_id).one()
        assert persisted_contact.email == "not-an-email"
        persisted_raw = session.query(RawImportRow).filter_by(id=persisted_contact.raw_import_row_id).one()
        assert persisted_raw.raw_csv_data["Email"] == "not-an-email"
    finally:
        session.close()


def test_record_details_projects_specific_email_reason_without_generic_duplicate(
    client_with_database,
):
    upload = client_with_database.post(
        "/upload",
        data={"file": (BytesIO(CSV.encode("utf-8")), "email-details-reason.csv")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200, upload.get_json()
    batch_id = upload.get_json()["batch_id"]

    page = client_with_database.get(f"/imports/{batch_id}/validation")
    assert page.status_code == 200
    html = page.data.decode("utf-8")
    assert "Invalid email format" in html, html
    assert "Issue with Email" not in html
