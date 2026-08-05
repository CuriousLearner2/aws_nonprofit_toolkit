"""Service boundary for recalculating an edited processing record."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from processor import (
    assign_tier,
    build_header_mapping,
    load_reference_list,
    load_rules,
    validate_address,
    validate_amount,
    validate_date,
    validate_email,
    validate_name,
    validate_phone,
    validate_transaction_id,
)

logger = logging.getLogger(__name__)


def _record_validation_result(validation_results, issues, suggestions, field, result):
    tier, reason, suggestion = result
    validation_results[field] = {"tier": tier, "reason": reason}
    if reason:
        labels = {"transaction_id": "Transaction ID"}
        issues.append(f"{labels.get(field, field.replace('_', ' ').title())}: {reason}")
    if suggestion:
        suggestions.append(suggestion)


def _persist_record(record, header_map, processing_dir, filename, new_tier, issues, suggestions):
    path = processing_dir / filename
    df = pd.read_csv(path, dtype="str", encoding="utf-8").fillna("")
    record_idx = None
    txn_id_col = header_map.get("transaction_id")
    if txn_id_col and txn_id_col in record:
        for idx, row in df.iterrows():
            if str(row[txn_id_col]).strip() == str(record[txn_id_col]).strip():
                record_idx = idx
                break
    if record_idx is None:
        return

    for col_name in header_map.values():
        if col_name in record:
            if col_name not in df.columns:
                df[col_name] = ""
            df.at[record_idx, col_name] = record[col_name]
    df.at[record_idx, "Validation_Tier"] = new_tier
    df.at[record_idx, "Issues"] = "; ".join(issues) if issues else "None"
    df.at[record_idx, "Suggested_Modifications"] = "; ".join(suggestions) if suggestions else ""
    if record.get("Operator_Decision"):
        if "Operator_Decision" not in df.columns:
            df["Operator_Decision"] = ""
        df.at[record_idx, "Operator_Decision"] = record["Operator_Decision"]
    if "Operator_Notes" in record:
        if "Operator_Notes" not in df.columns:
            df["Operator_Notes"] = ""
        df.at[record_idx, "Operator_Notes"] = record["Operator_Notes"]
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Saved edits to %s at index %s", filename, record_idx)


def recalculate_tier(record, processing_dir: Path, filename: str):
    """Recalculate validation and persist the matching edited CSV row."""
    rules = load_rules()
    reference = load_reference_list()
    header_map = build_header_mapping(record.keys())
    validation_results = {}
    issues = []
    suggestions = []

    _record_validation_result(validation_results, issues, suggestions, "transaction_id", validate_transaction_id(record, header_map))
    _record_validation_result(validation_results, issues, suggestions, "date", validate_date(record, header_map))
    _record_validation_result(validation_results, issues, suggestions, "email", validate_email(record, header_map, rules, reference))
    _record_validation_result(validation_results, issues, suggestions, "amount", validate_amount(record, header_map, reference))
    _record_validation_result(validation_results, issues, suggestions, "name", validate_name(record, header_map, reference))
    _record_validation_result(validation_results, issues, suggestions, "phone", validate_phone(record, header_map, rules))

    tier, reason = validate_address(record, header_map)
    validation_results["address"] = {"tier": tier, "reason": reason}
    if reason:
        issues.append(f"Address: {reason}")

    new_tier = assign_tier(validation_results)
    try:
        _persist_record(record, header_map, processing_dir, filename, new_tier, issues, suggestions)
    except Exception as exc:
        logger.error("Failed to save edits to CSV: %s", exc)
    logger.info("Recalculated tier for %s: %s", filename, new_tier)
    return {"tier": new_tier, "issues": issues[:5], "suggestions": suggestions[:5]}
