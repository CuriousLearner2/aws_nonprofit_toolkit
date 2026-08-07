"""Database-backed UAT regression for editable name validation."""

from io import BytesIO
import csv
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import (
    ImportContact,
    ImportBatch,
    RawImportRow,
    ReviewDecision,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from scripts.householder.export_file_service import _encode_csv_field
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.readiness_service import get_export_readiness
from scripts.householder.validation_service import get_validation_review


CSV = (
    "Name,Email,Phone,Amount,Date,Transaction ID\n"
    "J,not-an-email,5551234567,100.00,2026-06-12,TXN001\n"
    "Control,control@example.com,5559876543,200.00,2026-06-13,TXN002\n"
)


def _config(database_url):
    return {
        "HOUSEHOLDER_REPOSITORY": "database",
        "GIVEBUTTER_DATABASE_URL": database_url,
    }


def _validation_issue(session, batch_id, field):
    for item, subject in session.query(ReviewItem, ReviewItemSubject).join(
        ReviewItemSubject,
        ReviewItem.id == ReviewItemSubject.review_item_id,
    ).filter(
        ReviewItem.batch_id == batch_id,
        ReviewItem.item_type == "validation",
    ).all():
        if str((item.payload_json or {}).get("field", "")).lower() == field:
            return item, subject
    raise AssertionError(f"No {field} validation issue found")


def test_database_name_validation_persists_through_reload_preview_and_csv(
    client_with_database, test_db_path, tmp_path
):
    client = client_with_database
    database_url = test_db_path
    config = _config(database_url)

    upload = client.post(
        "/upload",
        data={"file": (BytesIO(CSV.encode("utf-8")), "name-validation.csv")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 200, upload.get_json()
    batch_id = upload.get_json()["batch_id"]

    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        rows = session.query(RawImportRow).filter_by(batch_id=batch_id).order_by(RawImportRow.row_index).all()
        contacts = session.query(ImportContact).filter_by(batch_id=batch_id).order_by(ImportContact.id).all()
        name_item, name_subject = _validation_issue(session, batch_id, "name")
        email_item, email_subject = _validation_issue(session, batch_id, "email")
        invalid_row = next(row for row in rows if row.raw_csv_data["Name"] == "J")
        control_row = next(row for row in rows if row.raw_csv_data["Name"] == "Control")
        assert name_subject.subject_id == invalid_row.id
        assert email_subject.subject_id == invalid_row.id
        assert len(rows) == len(contacts) == 2
        assert session.query(ReviewDecision).filter_by(raw_import_row_id=invalid_row.id).count() == 0
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

    invalid_save = client.post(
        f"/imports/{batch_id}/autosave",
        json={"raw_import_row_id": invalid_row.id, "corrected_values": {"name": ""}},
    )
    assert invalid_save.status_code == 400
    invalid_data = invalid_save.get_json()
    assert invalid_data["success"] is False
    assert "name" in invalid_data["validation_errors"]
    name_errors = [issue for issue in invalid_data["issues"] if issue.get("field") == "name"]
    assert name_errors
    assert all(issue["severity"] == "error" for issue in name_errors)

    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        assert session.query(ReviewDecision).filter_by(raw_import_row_id=invalid_row.id).count() == 0
        persisted_row = session.query(RawImportRow).filter_by(id=invalid_row.id).one()
        assert persisted_row.raw_csv_data["Name"] == "J"
    finally:
        session.close()

    correction = client.post(
        f"/imports/{batch_id}/autosave",
        json={"raw_import_row_id": invalid_row.id, "corrected_values": {"name": "Jane Corrected"}},
    )
    assert correction.status_code == 200, correction.get_json()
    correction_data = correction.get_json()
    assert correction_data["effective_values"]["name"] == "Jane Corrected"
    assert not any(issue.get("field") == "name" for issue in correction_data["issues"])
    assert any(issue.get("field") == "email" for issue in correction_data["issues"]), correction_data

    validation = get_validation_review(batch_id, config=config)
    corrected = next(row for row in validation["validation_issues"] if row["raw_import_row_id"] == invalid_row.id)
    control = next(row for row in validation["validation_issues"] if row["raw_import_row_id"] == control_row.id)
    assert corrected["name"] == "Jane Corrected"
    assert any(issue.get("field") == "email" for issue in corrected["issues"])
    assert not any(issue.get("field") == "name" for issue in corrected["issues"])
    assert control["name"] == "Control"
    assert control["email"] == "control@example.com"

    with client.application.test_client() as reloaded_client:
        validation_page = reloaded_client.get(f"/imports/{batch_id}/validation")
        assert validation_page.status_code == 200
        page_text = validation_page.data.decode("utf-8")
        assert "Jane Corrected" in page_text
        assert "Control" in page_text

    disposition = client.post(
        f"/imports/{batch_id}/row-decision",
        json={
            "raw_import_row_id": invalid_row.id,
            "decision": "accept_as_is",
            "notes": "Reviewed remaining email issue",
            "reviewer_name": "UAT Reviewer",
            "interaction_sequence": 1,
        },
    )
    assert disposition.status_code == 200, disposition.get_json()
    control_disposition = client.post(
        f"/imports/{batch_id}/row-decision",
        json={
            "raw_import_row_id": control_row.id,
            "decision": "accept_as_is",
            "notes": "Reviewed control row state",
            "reviewer_name": "UAT Reviewer",
            "interaction_sequence": 1,
        },
    )
    assert control_disposition.status_code == 200, control_disposition.get_json()

    readiness_after = get_export_readiness(batch_id, config=config)
    assert readiness_after.is_export_ready is True
    assert readiness_after.blocker_count == 0
    approval_after = client.post(
        f"/imports/{batch_id}/approve-batch",
        json={"approval_status": "approved"},
    )
    assert approval_after.status_code == 200

    preview = build_export_preview(batch_id, config=config)
    preview_rows = [row.to_dict() for row in preview.export_rows]
    assert any(
        row.get("first_name") == "Jane" and row.get("last_name") == "Corrected"
        for row in preview_rows
    ), preview_rows
    assert any(
        row.get("first_name") == "Control" and not row.get("last_name")
        for row in preview_rows
    ), preview_rows

    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    client.application.config["EXPORT_OUTPUT_DIR"] = str(export_dir)
    generated = client.post(
        f"/imports/{batch_id}/exports/generate",
        data={"confirmed_unresolved_validations": "true"},
    )
    assert generated.status_code == 200, generated.get_json()
    audit_id = generated.get_json()["file"]["audit_log_id"]
    downloaded = client.get(f"/imports/{batch_id}/exports/download/{audit_id}")
    assert downloaded.status_code == 200
    csv_rows = list(csv.DictReader(downloaded.data.decode("utf-8").splitlines()))
    assert [(row["first_name"], row["last_name"]) for row in csv_rows] == [
        (_encode_csv_field("Jane"), _encode_csv_field("Corrected")),
        (_encode_csv_field("Control"), _encode_csv_field("")),
    ]

    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        decisions = [
            decision for decision in session.query(ReviewDecision).filter_by(raw_import_row_id=invalid_row.id).all()
            if "name" in (decision.reviewed_values or {})
        ]
        assert len(decisions) == 1
        assert decisions[0].reviewed_values == {"name": "Jane Corrected"}
    finally:
        session.close()


def test_name_validation_exception_is_not_reported_as_success(
    client_with_database, test_db_path, monkeypatch
):
    from householder import autosave_service

    batch = ImportBatch(
        id="name-exception-batch",
        filename="name.csv",
        upload_timestamp=datetime.now(timezone.utc),
    )
    row = RawImportRow(
        batch_id=batch.id,
        row_index=1,
        raw_csv_data={"Name": "Valid", "Email": "valid@example.com"},
    )
    session = sessionmaker(bind=create_db_engine(test_db_path))()
    try:
        session.add(batch)
        session.add(row)
        session.commit()
        batch_id = batch.id
        row_id = row.id
    finally:
        session.close()

    def raise_validation_error(*args, **kwargs):
        raise RuntimeError("name validator unavailable")

    monkeypatch.setattr(autosave_service, "validate_name_correction", raise_validation_error)
    response = client_with_database.post(
        f"/imports/{batch_id}/autosave",
        json={"raw_import_row_id": row_id, "corrected_values": {"name": "Jane"}},
    )
    assert response.status_code == 500
    assert response.get_json()["error"] == "Autosave failed"
