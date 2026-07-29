"""Unit tests for canonical validation issue identity."""

from scripts.householder.issue_identity import (
    normalize_validation_issue_field,
    validation_issue_identity,
)


def test_address_aliases_and_casing_share_identity():
    persisted = {
        "field": "ADDRESS 1",
        "reason": "missing",
        "severity": "warning",
        "source": "validation",
        "description": "Missing address",
    }
    synthetic = {
        "field": "Street Address",
        "reason": "missing",
        "severity": "warning",
        "source": "validation",
        "description": "Missing address",
    }

    assert normalize_validation_issue_field("Address Line 1") == "address"
    assert validation_issue_identity(persisted) == validation_issue_identity(synthetic)


def test_distinct_issues_remain_distinct():
    missing = {
        "field": "Address 1",
        "reason": "missing",
        "severity": "warning",
        "source": "validation",
    }
    po_box = {
        "field": "Address 1",
        "reason": "format",
        "severity": "warning",
        "source": "validation",
    }

    assert validation_issue_identity(missing) != validation_issue_identity(po_box)


def test_message_differences_do_not_split_identity():
    left = {
        "field": "Address 1",
        "reason": "missing",
        "severity": "warning",
        "source": "validation",
        "description": "Missing address",
    }
    right = {
        "field": "address",
        "reason": "missing",
        "severity": "warning",
        "source": "validation",
        "description": "Address is blank",
    }

    assert validation_issue_identity(left) == validation_issue_identity(right)


def test_source_participates_in_identity_when_present():
    import_source = {
        "field": "Address 1",
        "reason": "missing",
        "severity": "warning",
        "source": "import",
    }
    validation_source = {
        "field": "Address 1",
        "reason": "missing",
        "severity": "warning",
        "source": "validation",
    }

    assert validation_issue_identity(import_source) != validation_issue_identity(validation_source)
