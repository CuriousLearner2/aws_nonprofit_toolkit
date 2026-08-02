from __future__ import annotations

from copy import deepcopy

from scripts.householder.recalculation_input_policy import (
    prepare_recalculation_input,
    value_for_validation_field,
)


def test_prepare_recalculation_input_merges_without_mutation():
    effective_values = {
        "name": "Alice",
        "email": "alice@example.com",
        "address_line1": "123 Old St",
    }
    proposed_values = {
        "email": "alice@new.example",
        "phone": "555-1212",
    }
    original_effective = deepcopy(effective_values)
    original_proposed = deepcopy(proposed_values)

    prepared = prepare_recalculation_input(effective_values, proposed_values)

    assert prepared["name"] == "Alice"
    assert prepared["email"] == "alice@new.example"
    assert prepared["phone"] == "555-1212"
    assert effective_values == original_effective
    assert proposed_values == original_proposed


def test_prepare_recalculation_input_preserves_alias_lookup():
    effective_values = {
        "street address": "123 Main St",
        "address": "123 Main St",
        "city": "Oakland",
    }
    proposed_values = {
        "street address": "456 Oak St",
    }

    prepared = prepare_recalculation_input(effective_values, proposed_values)

    assert prepared["street address"] == "456 Oak St"
    assert prepared["address"] == "456 Oak St"
    assert value_for_validation_field(prepared, "address") == "456 Oak St"


def test_value_for_validation_field_prefers_non_blank_alias():
    values = {
        "address": "  ",
        "address 1": "123 Main St",
        "city": "",
    }

    assert value_for_validation_field(values, "address") == "123 Main St"


def test_value_for_validation_field_retains_blank_match_when_no_value():
    values = {
        "address": "   ",
        "address 1": "   ",
    }

    assert value_for_validation_field(values, "address") == "   "
