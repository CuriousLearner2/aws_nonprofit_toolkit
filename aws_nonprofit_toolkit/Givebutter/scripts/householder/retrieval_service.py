"""Read-only retrieval views over the existing import and review records."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from .database_models import ImportBatch, ImportContact, RawImportRow, ReviewDecision
from .database_repository import get_db_session
from .issue_recalculation_service import recalculate_row_issues
from .row_status_policy import derive_row_status
from .row_decision_service import get_row_decision_state


_DISPOSITIONS = {"accept_as_is", "needs_follow_up", "reject_row"}


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _in_date_range(uploaded: Optional[datetime], date_from: str, date_to: str) -> bool:
    if not uploaded:
        return not date_from and not date_to
    value = uploaded.date().isoformat()
    return (not date_from or value >= date_from) and (not date_to or value <= date_to)


def search_import_rows(
    config: Optional[Mapping[str, Any]] = None,
    *,
    query: str = "",
    disposition: str = "all",
    status: str = "all",
    reviewer: str = "",
    batch_id: str = "all",
    date_from: str = "",
    date_to: str = "",
) -> dict[str, Any]:
    """Search existing rows without creating a cross-import source of truth."""
    database_url = (config or {}).get("GIVEBUTTER_DATABASE_URL")
    if not database_url:
        return {"results": [], "batches": [], "database_available": False}

    session = get_db_session(database_url)
    try:
        batches = session.query(ImportBatch).order_by(ImportBatch.upload_timestamp.desc()).all()
        batch_map = {batch.id: batch for batch in batches}
        selected_batches = [
            batch for batch in batches
            if (batch_id in ("", "all") or batch.id == batch_id)
            and _in_date_range(batch.upload_timestamp, date_from, date_to)
        ]
        selected_ids = {batch.id for batch in selected_batches}
        rows = session.query(ImportContact, RawImportRow).join(
            RawImportRow, RawImportRow.id == ImportContact.raw_import_row_id
        ).filter(ImportContact.batch_id.in_(selected_ids or {"__none__"})).all()

        q = query.strip().casefold()
        reviewer_q = reviewer.strip().casefold()
        results = []
        for contact, raw_row in rows:
            decisions = session.query(ReviewDecision).filter_by(
                batch_id=contact.batch_id,
                raw_import_row_id=contact.raw_import_row_id,
            ).order_by(ReviewDecision.created_at.asc(), ReviewDecision.id.asc()).all()
            effective = dict(raw_row.raw_csv_data or {})
            for decision_record in decisions:
                if decision_record.reviewed_values:
                    effective.update(decision_record.reviewed_values)

            values = {
                "transaction_id": effective.get("transaction_id", effective.get("Transaction ID", "")),
                "name": effective.get("name") or " ".join(
                    part for part in [effective.get("first_name", contact.first_name), effective.get("last_name", contact.last_name)] if part
                ),
                "email": effective.get("email", contact.email),
                "phone": effective.get("phone", contact.phone),
            }
            haystack = " ".join(_text(value) for value in values.values()).casefold()
            if q and q not in haystack:
                continue

            state = get_row_decision_state(contact.batch_id, contact.raw_import_row_id, database_url)
            active_disposition = state.get("decision") if state.get("has_decision") else ""
            if disposition not in ("", "all") and (
                active_disposition if active_disposition else "none"
            ) != disposition:
                continue
            if reviewer_q and (
                not state.get("has_decision")
                or reviewer_q not in _text(state.get("reviewer")).casefold()
            ):
                continue

            issues = recalculate_row_issues(contact.batch_id, contact.raw_import_row_id, database_url=database_url)
            row_status = derive_row_status(issues)
            if status not in ("", "all") and row_status.casefold() != status.casefold():
                continue

            batch = batch_map[contact.batch_id]
            results.append({
                "batch_id": contact.batch_id,
                "filename": batch.filename,
                "uploaded": batch.upload_timestamp.isoformat() if batch.upload_timestamp else "",
                "row_id": contact.id,
                "raw_import_row_id": contact.raw_import_row_id,
                "transaction_id": _text(values["transaction_id"]),
                "name": _text(values["name"]),
                "email": _text(values["email"]),
                "phone": _text(values["phone"]),
                "status": row_status,
                "issue_count": len(issues),
                "disposition": active_disposition,
                "disposition_label": {
                    "accept_as_is": "Accept as-is",
                    "needs_follow_up": "Needs follow-up",
                    "reject_row": "Reject row",
                }.get(active_disposition, "No disposition"),
                "reviewer": state.get("reviewer") or "" if state.get("has_decision") else "",
                "reason": state.get("notes") or "" if state.get("has_decision") else "",
                "timestamp": state.get("timestamp") or "" if state.get("has_decision") else "",
                "validation_url": f"/imports/{contact.batch_id}/validation#validation-row-{contact.id}",
            })

        return {
            "results": results,
            "batches": [{"id": batch.id, "filename": batch.filename} for batch in batches],
            "database_available": True,
            "query": query,
            "disposition": disposition,
            "status": status,
            "reviewer": reviewer,
            "batch_id": batch_id,
            "date_from": date_from,
            "date_to": date_to,
        }
    finally:
        session.close()
