from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .issue_contract import ValidationIssueContract


def _is_missing_address(contract: ValidationIssueContract) -> bool:
    return contract.normalized_field == "address" and contract.reason == "missing"


def _merge_issue_mappings(
    authoritative: Mapping[str, Any],
    supplemental: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(supplemental)
    merged.update(authoritative)
    return merged


def reconcile_missing_address_issues(
    existing_issues: Iterable[Mapping[str, Any]],
    evaluated_issues: Iterable[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    existing_records: list[tuple[ValidationIssueContract, dict[str, Any]]] = []
    for issue in existing_issues:
        contract = ValidationIssueContract.from_mapping(issue)
        if contract.normalized_field == "address":
            existing_records.append((contract, dict(issue)))

    evaluated_records: list[tuple[ValidationIssueContract, dict[str, Any]]] = []
    for issue in evaluated_issues or []:
        contract = ValidationIssueContract.from_mapping(issue)
        if contract.normalized_field == "address":
            evaluated_records.append((contract, dict(issue)))

    if not existing_records and not evaluated_records:
        return []

    ordered_identities: list[tuple[str, str, str, str]] = []
    grouped: dict[tuple[str, str, str, str], dict[str, list[tuple[ValidationIssueContract, dict[str, Any]]]]] = {}

    for origin, records in (("existing", existing_records), ("evaluated", evaluated_records)):
        for contract, mapping in records:
            if contract.identity not in grouped:
                grouped[contract.identity] = {"existing": [], "evaluated": []}
                ordered_identities.append(contract.identity)
            grouped[contract.identity][origin].append((contract, mapping))

    reconciled: list[dict[str, Any]] = []
    for identity in ordered_identities:
        existing_group = grouped[identity]["existing"]
        evaluated_group = grouped[identity]["evaluated"]

        if not existing_group and not evaluated_group:
            continue

        if existing_group:
            existing_contract, existing_mapping = existing_group[0]
            if _is_missing_address(existing_contract) and not evaluated_group:
                continue
            if evaluated_group:
                reconciled.append(
                    _merge_issue_mappings(existing_mapping, evaluated_group[0][1])
                )
            else:
                reconciled.append(dict(existing_mapping))
            continue

        reconciled.append(dict(evaluated_group[0][1]))

    return reconciled
