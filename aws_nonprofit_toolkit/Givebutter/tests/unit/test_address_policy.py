import pytest

from scripts.householder.address_policy import (
    evaluate_address_issue,
    find_address_source_column,
    get_address_source_value,
    has_address_source,
)


@pytest.mark.parametrize(
    "column",
    ["Address 1", "Street Address", "Address Line 1", "Address", "address_1"],
)
def test_recognized_address_aliases_define_source_capability(column):
    raw = {column: "123 Main St"}

    assert has_address_source(raw) is True
    assert find_address_source_column(raw) == column
    assert get_address_source_value(raw) == "123 Main St"


def test_address_one_remains_preferred_when_multiple_aliases_are_present():
    raw = {"Address": "generic", "Address 1": "preferred"}

    assert find_address_source_column(raw) == "Address 1"
    assert get_address_source_value(raw) == "preferred"


def test_missing_source_has_no_address_capability():
    assert has_address_source({"Name": "Ada"}) is False
    assert find_address_source_column(["Name", "Email"]) is None


@pytest.mark.parametrize("raw_data", [None, "legacy-json", ["Address 1"]])
def test_legacy_non_mapping_source_payload_is_not_an_address_source(raw_data):
    assert has_address_source(raw_data) is False
    assert get_address_source_value(raw_data) is None


@pytest.mark.parametrize("value", [None, "", "   ", "nan"])
def test_canonical_address_evaluator_emits_one_warning_for_blank_value(value):
    issue = evaluate_address_issue(value)

    assert issue == {
        "field": "address",
        "reason": "missing",
        "description": "Missing address",
        "severity": "warning",
        "is_new": True,
    }


def test_canonical_address_evaluator_is_clean_for_populated_value():
    assert evaluate_address_issue("123 Main St, Springfield, IL 62701") is None
