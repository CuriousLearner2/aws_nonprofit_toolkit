from __future__ import annotations

import pytest

from scripts.householder.editable_field_validation import validate_editable_field_values


@pytest.mark.parametrize(
    "corrected_values, expected_field, expected_error",
    [
        ({"name": ""}, "name", "Invalid name format"),
        ({"name": "   "}, "name", "Invalid name format"),
        ({"name": 123}, "name", "Invalid name format"),
        ({"address": ""}, "address", "Invalid address format"),
        ({"address": "   "}, "address", "Invalid address format"),
        ({"address": None}, "address", "Invalid address format"),
    ],
)
def test_editable_field_policy_blocks_blank_whitespace_and_non_string_name_address(
    corrected_values,
    expected_field,
    expected_error,
):
    is_valid, errors = validate_editable_field_values(corrected_values)
    assert is_valid is False
    assert errors is not None
    assert errors[expected_field] == expected_error


def test_editable_field_policy_accepts_valid_name_address_and_keeps_existing_field_behavior():
    is_valid, errors = validate_editable_field_values(
        {
            "name": "Jane Smith",
            "address": "123 Main St",
            "email": "jane@example.com",
            "phone": "(415) 555-1234",
            "date": "2026-08-02",
            "amount": "125.00",
        }
    )
    assert is_valid is True
    assert errors is None
