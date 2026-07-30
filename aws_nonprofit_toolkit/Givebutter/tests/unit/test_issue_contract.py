"""Unit tests for the canonical validation issue contract."""

from scripts.householder.issue_contract import ValidationIssueContract


def test_persisted_and_synthetic_shapes_share_identity_and_keep_metadata():
    persisted = {
        "field": "ADDRESS 1",
        "issue_type": "format-invalid",
        "reason": "missing",
        "severity": "warning",
        "source": "validation",
        "issue_description": "Missing address",
        "review_item_id": 17,
    }
    synthetic = {
        "field": "Street Address",
        "reason": "missing",
        "severity": "WARNING",
        "source": "validation",
        "description": "Missing address",
        "issue_id": 22,
        "overridden": False,
    }

    persisted_contract = ValidationIssueContract.from_mapping(persisted)
    synthetic_contract = ValidationIssueContract.from_mapping(synthetic)

    assert persisted_contract.identity == synthetic_contract.identity
    assert persisted_contract.normalized_field == "address"
    assert synthetic_contract.normalized_field == "address"
    assert persisted_contract.issue_type == "format-invalid"
    assert synthetic_contract.issue_type is None
    assert persisted_contract.message == "Missing address"
    assert synthetic_contract.message == "Missing address"
    assert persisted_contract.metadata["review_item_id"] == 17
    assert synthetic_contract.metadata["issue_id"] == 22


def test_contract_round_trip_preserves_metadata_and_source_information():
    raw_issue = {
        "field": "Address Line 1",
        "issue_type": "format-invalid",
        "issue_reason": "missing",
        "issue_description": "Missing address",
        "severity": "WARNING",
        "source": "Validation",
        "source_specific_metadata": {"column": "Address 1"},
    }

    contract = ValidationIssueContract.from_mapping(raw_issue)
    mapping = contract.to_mapping()

    assert contract.identity[0] == "address"
    assert contract.reason == "missing"
    assert contract.severity == "warning"
    assert contract.source == "validation"
    assert mapping["field"] == "Address Line 1"
    assert mapping["issue_type"] == "format-invalid"
    assert mapping["reason"] == "missing"
    assert mapping["severity"] == "warning"
    assert mapping["source"] == "validation"
    assert mapping["message"] == "Missing address"
    assert mapping["issue_description"] == "Missing address"
    assert mapping["issue_reason"] == "missing"
    assert mapping["source_specific_metadata"] == {"column": "Address 1"}


def test_distinct_validation_issues_remain_distinct():
    missing = ValidationIssueContract.from_mapping(
        {
            "field": "Address 1",
            "reason": "missing",
            "severity": "warning",
            "source": "validation",
        }
    )
    format_issue = ValidationIssueContract.from_mapping(
        {
            "field": "Address 1",
            "reason": "format",
            "severity": "warning",
            "source": "validation",
        }
    )

    assert missing.identity != format_issue.identity
