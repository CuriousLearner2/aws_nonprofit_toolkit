"""Database-backed UAT regressions for address and amount correction lifecycles."""

from __future__ import annotations

import csv
from io import BytesIO, StringIO
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from scripts.householder.approval_service import get_batch_approval_status
from scripts.householder.autosave_service import get_effective_values
from scripts.householder.database_models import ImportContact, RawImportRow, ReviewItem, ReviewItemSubject, create_db_engine
from scripts.householder.export_file_service import _encode_csv_field
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.readiness_service import get_export_readiness
from scripts.householder.validation_service import get_validation_review


def _config(database_url):
    return {"HOUSEHOLDER_REPOSITORY": "database", "GIVEBUTTER_DATABASE_URL": database_url}


def _upload(client, content: str, filename: str) -> str:
    response = client.post(
        "/upload",
        data={"file": (BytesIO(content.encode("utf-8")), filename)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["batch_id"]


def _rows(database_url, batch_id):
    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        return session.query(RawImportRow).filter_by(batch_id=batch_id).order_by(RawImportRow.row_index).all()
    finally:
        session.close()


def _validation_item_for(database_url, batch_id, raw_row_id, field):
    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        contact = session.query(ImportContact).filter_by(batch_id=batch_id, raw_import_row_id=raw_row_id).one()
        matches = []
        for item, subject in session.query(ReviewItem, ReviewItemSubject).join(ReviewItemSubject).filter(
            ReviewItem.batch_id == batch_id,
            ReviewItem.item_type == "validation",
            ReviewItemSubject.subject_id == contact.id,
        ).all():
            payload_field = str((item.payload_json or {}).get("field", "")).lower()
            if payload_field == field or (field == "address" and payload_field in {"address 1", "address_1", "street address"}):
                matches.append((item, subject))
        assert len(matches) == 1, f"Expected one {field} validation item, got {len(matches)}"
        return matches[0]
    finally:
        session.close()


def _seed_address_warning(database_url, batch_id, raw_row_id, *, reason="missing", description="Missing address"):
    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        contact = session.query(ImportContact).filter_by(batch_id=batch_id, raw_import_row_id=raw_row_id).one()
        item = ReviewItem(
            batch_id=batch_id,
            item_type="validation",
            status="pending",
            confidence=1.0,
            payload_json={
                "field": "address",
                "reason": reason,
                "description": description,
                "severity": "warning",
            },
        )
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(
            review_item_id=item.id,
            subject_type="import_contact_snapshot",
            subject_id=contact.id,
            role="primary",
        ))
        session.commit()
    finally:
        session.close()


def _blank_address_raw(database_url, raw_row_id):
    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        row = session.query(RawImportRow).filter_by(id=raw_row_id).one()
        data = dict(row.raw_csv_data)
        data["Address 1"] = ""
        row.raw_csv_data = data
        session.commit()
    finally:
        session.close()


def _review_row(review, name):
    return next(row for row in review["validation_issues"] if row["name"] == name)


def _downloaded_rows(client, batch_id, export_dir):
    export_dir.mkdir(parents=True, exist_ok=True)
    client.application.config["EXPORT_OUTPUT_DIR"] = str(export_dir)
    generated = client.post(f"/imports/{batch_id}/exports/generate")
    assert generated.status_code == 200, generated.get_json()
    file_data = generated.get_json()["file"]
    downloaded = client.get(f"/imports/{batch_id}/exports/download/{file_data['audit_log_id']}")
    assert downloaded.status_code == 200
    return list(csv.DictReader(StringIO(downloaded.data.decode("utf-8"))))


def test_address_warning_correction_reload_readiness_preview_csv(client_with_database, test_db_path, tmp_path):
    csv_content = (
        "Name,Email,Phone,Amount,Date,Transaction ID,Address 1\n"
        'Address Target,target@example.com,5551234567,100.00,2026-06-12,ADDR001,123 Main St\n'
        'Address Control,control@example.com,5559876543,200.00,2026-06-13,ADDR002,456 Oak Ave\n'
    )
    batch_id = _upload(client_with_database, csv_content, "address-persistence.csv")
    database_url = test_db_path
    rows = _rows(database_url, batch_id)
    target, control = rows
    _blank_address_raw(database_url, target.id)
    _seed_address_warning(database_url, batch_id, target.id)
    item, subject = _validation_item_for(database_url, batch_id, target.id, "address")
    assert subject.subject_id == target.id
    assert (item.payload_json or {}).get("field", "").lower() == "address"
    assert (item.payload_json or {}).get("severity") == "warning"

    before = get_validation_review(batch_id, config=_config(database_url))
    address_before = _review_row(before, "Address Target")["issues"]
    assert len(address_before) == 1
    assert address_before[0]["field"] == "address"
    assert address_before[0]["severity"] == "warning"
    assert _review_row(before, "Address Control")["issues"] == []
    readiness_before = get_export_readiness(batch_id, config=_config(database_url))
    assert readiness_before.is_export_ready is False
    assert readiness_before.blocker_count == 1
    correction = client_with_database.post(
        f"/imports/{batch_id}/autosave",
        json={"raw_import_row_id": target.id, "corrected_values": {"address": "123 Main St, Springfield, IL 62701"}},
    )
    assert correction.status_code == 200, correction.get_json()

    with client_with_database.application.test_client() as reloaded_client:
        reloaded = reloaded_client.get(f"/imports/{batch_id}/validation")
        assert reloaded.status_code == 200
    after = get_validation_review(batch_id, config=_config(database_url))
    assert _review_row(after, "Address Target")["address"] == "123 Main St, Springfield, IL 62701"
    assert _review_row(after, "Address Target")["issues"] == []
    assert _review_row(after, "Address Control")["address"] == "456 Oak Ave"
    assert _review_row(after, "Address Control")["issues"] == []
    effective = get_effective_values(batch_id, target.id, database_url)
    assert effective["address"] == "123 Main St, Springfield, IL 62701"

    approval = client_with_database.post(f"/imports/{batch_id}/approve-batch", json={"approval_status": "approved"})
    assert approval.status_code == 200, approval.get_json()
    assert get_batch_approval_status(batch_id, database_url=database_url)["approval_status"] == "approved"
    preview = build_export_preview(batch_id, config=_config(database_url))
    assert preview.is_export_ready is True
    assert [row.to_dict()["address_line1"] for row in preview.export_rows] == [
        "123 Main St, Springfield, IL 62701", "456 Oak Ave"
    ]
    downloaded_rows = _downloaded_rows(client_with_database, batch_id, tmp_path / "address-exports")
    assert [row["address_line1"] for row in downloaded_rows] == [
        _encode_csv_field("123 Main St, Springfield, IL 62701"), _encode_csv_field("456 Oak Ave")
    ]
    assert control.raw_csv_data["Address 1"] == "456 Oak Ave"


def test_blank_address_without_seeded_issue_projects_one_warning(client_with_database, test_db_path):
    csv_content = (
        "Name,Email,Phone,Amount,Date,Transaction ID,Address 1\n"
        'Blank Address,target@example.com,5551234567,100.00,2026-06-12,ADDR001,\n'
        'Address Control,control@example.com,5559876543,200.00,2026-06-13,ADDR002,456 Oak Ave\n'
    )
    batch_id = _upload(client_with_database, csv_content, "blank-address-warning.csv")
    review = get_validation_review(batch_id, config=_config(test_db_path))
    target = _review_row(review, "Blank Address")
    address_issues = [issue for issue in target["issues"] if issue["field"] == "address"]

    assert len(address_issues) == 1, target
    assert address_issues[0]["severity"] == "warning"
    assert [issue for issue in target["issues"] if issue["field"] != "address"] == []
    assert _review_row(review, "Address Control")["issues"] == []


def test_amount_error_correction_reload_readiness_preview_csv(client_with_database, test_db_path, tmp_path):
    csv_content = (
        "Name,Email,Phone,Amount,Date,Transaction ID,Address 1\n"
        'Amount Target,target@example.com,5551234567,not-an-amount,2026-06-12,AMT001,"123 Main St, Springfield IL"\n'
        'Amount Control,control@example.com,5559876543,200.00,2026-06-13,AMT002,456 Oak Ave\n'
    )
    batch_id = _upload(client_with_database, csv_content, "amount-persistence.csv")
    database_url = test_db_path
    target, control = _rows(database_url, batch_id)
    _seed_address_warning(database_url, batch_id, target.id, reason="format", description="Malformed address")
    item, subject = _validation_item_for(database_url, batch_id, target.id, "amount")
    assert subject.subject_id == target.id
    assert (item.payload_json or {}).get("field", "").lower() == "amount"
    assert (item.payload_json or {}).get("severity") == "error"

    before = get_validation_review(batch_id, config=_config(database_url))
    target_before = _review_row(before, "Amount Target")
    assert {issue["field"]: issue["severity"] for issue in target_before["issues"]} == {"amount": "error", "address": "warning"}
    readiness_before = get_export_readiness(batch_id, config=_config(database_url))
    assert readiness_before.is_export_ready is False
    assert readiness_before.blocker_count == 1
    approval_before = client_with_database.post(f"/imports/{batch_id}/approve-batch", json={"approval_status": "approved"})
    assert approval_before.status_code == 400

    correction = client_with_database.post(
        f"/imports/{batch_id}/autosave",
        json={"raw_import_row_id": target.id, "corrected_values": {"amount": "$1,250.50"}},
    )
    assert correction.status_code == 200, correction.get_json()
    assert correction.get_json()["effective_values"]["amount"] == "1250.50"
    with client_with_database.application.test_client() as reloaded_client:
        reloaded = reloaded_client.get(f"/imports/{batch_id}/validation")
        assert reloaded.status_code == 200
    after = get_validation_review(batch_id, config=_config(database_url))
    target_after = _review_row(after, "Amount Target")
    assert target_after["amount"] == "1250.50"
    assert {issue["field"]: issue["severity"] for issue in target_after["issues"]} == {"address": "warning"}
    assert _review_row(after, "Amount Control")["amount"] == "200.00"
    effective = get_effective_values(batch_id, target.id, database_url)
    assert effective["amount"] == "1250.50"
    disposition = client_with_database.post(
        f"/imports/{batch_id}/row-decision",
        json={
            "raw_import_row_id": target.id,
            "decision": "accept_as_is",
            "notes": "Reviewed remaining address warning",
            "reviewer_name": "UAT Reviewer",
            "interaction_sequence": 1,
        },
    )
    assert disposition.status_code == 200, disposition.get_json()
    readiness_after = get_export_readiness(batch_id, config=_config(database_url))
    assert readiness_after.is_export_ready is True
    assert readiness_after.blocker_count == 0
    assert readiness_after.warning_count == 1
    approval = client_with_database.post(f"/imports/{batch_id}/approve-batch", json={"approval_status": "approved"})
    assert approval.status_code == 200, approval.get_json()
    preview = build_export_preview(batch_id, config=_config(database_url))
    assert [row.to_dict()["amount"] for row in preview.export_rows] == ["1250.50", "200.00"]
    downloaded_rows = _downloaded_rows(client_with_database, batch_id, tmp_path / "amount-exports")
    assert [row["amount"] for row in downloaded_rows] == ["1250.50", "200.00"]
    assert control.raw_csv_data["Amount"] == "200.00"
