"""Deterministic, ORM-free planning for processed CSV ingestion."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from .ingestion_audit_policy import build_ingestion_audit_details
from .ingestion_value_policy import extract_digits_from_phone, parse_amount, split_name


@dataclass(frozen=True)
class RowPlan:
    row_index: int
    validation_tier: str
    raw_csv_data: Mapping[str, Any]
    contact_values: Mapping[str, Any]
    validation_items: tuple[Mapping[str, Any], ...]
    normalization_items: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class IngestionPlan:
    batch_id: str
    original_filename: str
    uploader: str
    imported_at: datetime
    header_mapping: Mapping[str, str]
    rows: tuple[RowPlan, ...]
    pass_count: int
    warning_count: int
    fail_count: int
    validation_items_created: int
    normalization_items_created: int
    audit_details: Mapping[str, Any]


def _value(row: Mapping[str, Any], mapping: Mapping[str, str], key: str) -> Any:
    column = mapping.get(key)
    return row.get(column) if column else None


def _contact_values(row: Mapping[str, Any], mapping: Mapping[str, str]) -> dict[str, Any]:
    name = _value(row, mapping, "name")
    first_name, last_name = split_name(name) if name else (None, None)
    phone = _value(row, mapping, "phone")
    if phone:
        phone = extract_digits_from_phone(phone) or None
    amount_value = _value(row, mapping, "amount")
    return {
        "first_name": first_name, "last_name": last_name,
        "email": _value(row, mapping, "email"), "phone": phone,
        "address_line1": _value(row, mapping, "address_1"),
        "address_line2": _value(row, mapping, "address_2"),
        "city": _value(row, mapping, "city"), "state": _value(row, mapping, "state"),
        "postal_code": _value(row, mapping, "zip"),
        "amount": parse_amount(amount_value) if amount_value else None,
    }


def _items(row: Mapping[str, Any], tier: str) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    validations: list[dict[str, Any]] = []
    normalizations: list[dict[str, Any]] = []
    issues_value = str(row.get("Issues", "")).strip()
    suggestions_value = str(row.get("Suggested_Modifications", "")).strip()
    suggestions = [s.strip() for s in suggestions_value.split(";") if s.strip()] if suggestions_value and suggestions_value.lower() != "none" else []
    if tier != "PASS" and issues_value and issues_value.lower() != "none":
        suggestion = suggestions[0] if suggestions else None
        for issue_text in (s.strip() for s in issues_value.split(";") if s.strip()):
            field, description = (issue_text.split(":", 1)[0].strip(), issue_text) if ":" in issue_text else ("unknown", issue_text)
            validations.append({"field": field, "issue": description, "suggestion": suggestion, "validation_tier": tier})
    if tier == "PASS" and suggestions_value and suggestions_value.lower() not in ("none", "nan", "<na>", ""):
        for suggestion in suggestions:
            normalizations.append({"field": "unknown", "raw_value": None, "normalized_value": suggestion, "basis": "processor suggestion", "confidence": 0.85})
    return tuple(validations), tuple(normalizations)


def plan_ingestion(*, batch_id: str, original_filename: str, uploader: str, imported_at: datetime, header_mapping: Mapping[str, str], rows: list[Mapping[str, Any]]) -> IngestionPlan:
    planned: list[RowPlan] = []
    pass_count = warning_count = fail_count = validation_count = normalization_count = 0
    for row_index, row in enumerate(rows):
        data = dict(row)
        tier = str(data.get("Validation_Tier", "FAIL")).strip()
        if tier == "PASS": pass_count += 1
        elif tier == "WARNING": warning_count += 1
        else: fail_count += 1
        validations, normalizations = _items(data, tier)
        validation_count += len(validations); normalization_count += len(normalizations)
        planned.append(RowPlan(row_index, tier, data, _contact_values(data, header_mapping), validations, normalizations))
    return IngestionPlan(
        batch_id=batch_id, original_filename=original_filename, uploader=uploader, imported_at=imported_at,
        header_mapping=dict(header_mapping), rows=tuple(planned), pass_count=pass_count,
        warning_count=warning_count, fail_count=fail_count, validation_items_created=validation_count,
        normalization_items_created=normalization_count,
        audit_details=build_ingestion_audit_details(
            filename=original_filename, record_count=len(planned), pass_count=pass_count,
            warning_count=warning_count, fail_count=fail_count, validation_items=validation_count,
            normalization_items=normalization_count,
        ),
    )
