"""Tests to verify all FAIL tier validators return actionable suggestions."""
import pytest
from processor import (
    validate_email, validate_amount, validate_transaction_id,
    validate_date, validate_name
)


class TestFailTierSuggestions:
    """Verify that FAIL tier validation errors include suggestions."""

    @pytest.mark.unit
    def test_empty_email_has_suggestion(self):
        """FAIL tier should return a suggestion for empty email."""
        record = {'Email': ''}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"
        assert len(suggestion) > 0, "Suggestion should not be empty"

    @pytest.mark.unit
    def test_invalid_email_has_suggestion(self):
        """FAIL tier should return a suggestion for invalid email format."""
        record = {'Email': 'anna.mueller'}  # Missing @
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"
        assert len(suggestion) > 0, "Suggestion should not be empty"

    @pytest.mark.unit
    def test_empty_amount_has_suggestion(self):
        """FAIL tier should return a suggestion for empty amount."""
        record = {'Amount': ''}
        header_map = {'amount': 'Amount'}
        reference = {'amount_statistics': {'valid_range': [1, 100000]}, 'high_dollar_threshold': 1000}

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"

    @pytest.mark.unit
    def test_zero_amount_has_suggestion(self):
        """FAIL tier should return a suggestion for zero amount."""
        record = {'Amount': '0'}
        header_map = {'amount': 'Amount'}
        reference = {'amount_statistics': {'valid_range': [1, 100000]}, 'high_dollar_threshold': 1000}

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"

    @pytest.mark.unit
    def test_missing_transaction_id_has_suggestion(self):
        """FAIL tier should return a suggestion for missing transaction ID."""
        record = {'Transaction ID': ''}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"

    @pytest.mark.unit
    def test_missing_date_has_suggestion(self):
        """FAIL tier should return a suggestion for missing date."""
        record = {'Date': ''}
        header_map = {'date': 'Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"

    @pytest.mark.unit
    def test_empty_name_has_suggestion(self):
        """FAIL tier should return a suggestion for empty name."""
        record = {'Name': ''}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason, suggestion = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"

    @pytest.mark.unit
    def test_short_name_has_suggestion(self):
        """FAIL tier should return a suggestion for name too short."""
        record = {'Name': 'A'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason, suggestion = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None, "FAIL tier should include suggestion"
        assert 'character' in suggestion.lower() or 'length' in suggestion.lower()
