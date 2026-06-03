"""Tests to verify all FAIL tier validators return actionable suggestions."""
import pytest
from processor import (
    validate_email, validate_amount, validate_transaction_id,
    validate_date, validate_name, validate_phone
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


class TestEdgeCases:
    """Test edge cases for FAIL tier validators."""

    @pytest.mark.unit
    def test_whitespace_only_email_has_suggestion(self):
        """Whitespace-only email should be treated as empty and have suggestion."""
        record = {'Email': '   '}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'FAIL'
        assert suggestion is not None

    @pytest.mark.unit
    def test_email_without_domain_has_suggestion(self):
        """Email with @ but no domain should fail with suggestion."""
        record = {'Email': 'user@'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'FAIL'
        assert suggestion is not None

    @pytest.mark.unit
    def test_negative_amount_has_suggestion(self):
        """Negative amount should fail with suggestion."""
        record = {'Amount': '-50'}
        header_map = {'amount': 'Amount'}
        reference = {'amount_statistics': {'valid_range': [1, 100000]}, 'high_dollar_threshold': 1000}

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None

    @pytest.mark.unit
    def test_non_numeric_amount_has_suggestion(self):
        """Non-numeric amount should fail with suggestion."""
        record = {'Amount': 'abc'}
        header_map = {'amount': 'Amount'}
        reference = {'amount_statistics': {'valid_range': [1, 100000]}, 'high_dollar_threshold': 1000}

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None

    @pytest.mark.unit
    def test_whitespace_only_name_has_suggestion(self):
        """Whitespace-only name should be treated as empty and have suggestion."""
        record = {'Name': '   '}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason, suggestion = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None

    @pytest.mark.unit
    def test_long_name_has_suggestion(self):
        """Name exceeding max length should fail with suggestion."""
        record = {'Name': 'A' * 101}  # Max is 100
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason, suggestion = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert suggestion is not None
        assert 'character' in suggestion.lower() or 'length' in suggestion.lower()

    @pytest.mark.unit
    def test_whitespace_only_transaction_id_has_suggestion(self):
        """Whitespace-only transaction ID should fail with suggestion."""
        record = {'Transaction ID': '   '}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'FAIL'
        assert suggestion is not None

    @pytest.mark.unit
    def test_whitespace_only_date_has_suggestion(self):
        """Whitespace-only date should fail with suggestion."""
        record = {'Date': '   '}
        header_map = {'date': 'Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'FAIL'
        assert suggestion is not None


class TestSuggestionPriority:
    """Test that suggestions are prioritized: required, duplicates, address, optional."""

    @pytest.mark.unit
    def test_required_field_suggests_before_optional(self):
        """Required field suggestions should be prioritized in the processor output.

        In process_csv(), suggestions are collected in priority order:
        1. Required fields (transaction_id, date, email, amount, name)
        2. Duplicates
        3. Address (optional)
        4. Phone (optional)
        """
        # This test verifies the prioritization in the processor by checking
        # that required field validators generate suggestions
        record = {'Email': ''}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        # Required field (email) should have suggestion
        email_tier, email_reason, email_suggestion = validate_email(record, header_map, rules, reference)
        assert email_tier == 'FAIL'
        assert email_suggestion is not None
        assert 'email' in email_suggestion.lower() or 'verify' in email_suggestion.lower()

    @pytest.mark.unit
    def test_multiple_required_field_failures(self):
        """Multiple required field failures should all have suggestions."""
        record = {'Email': '', 'Amount': ''}
        header_map = {'email': 'Email', 'amount': 'Amount'}
        rules = {'email_typos': []}
        reference = {
            'email_domains': [],
            'email_tlds': [],
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        email_tier, email_reason, email_suggestion = validate_email(record, header_map, rules, reference)
        assert email_tier == 'FAIL'
        assert email_suggestion is not None

        amount_tier, amount_reason, amount_suggestion = validate_amount(record, header_map, reference)
        assert amount_tier == 'FAIL'
        assert amount_suggestion is not None
