"""
Integration tests for inline field validation.

Tests that the validation functions properly detect invalid test phone numbers,
invalid emails, invalid amounts, etc., which are used in the frontend and backend.
"""

import pytest


@pytest.mark.integration
class TestInlinePhoneValidation:
    """Test phone validation catches invalid test patterns."""

    def test_sequential_test_number_invalid(self):
        """Sequential test number 1234567890 should be invalid."""
        from scripts.processor import validate_phone

        record = {
            'Phone': '1234567890'
        }
        header_map = {'phone': 'Phone'}
        rules = {
            'invalid_phone_patterns': [
                {'pattern': '^(.)\\1{9}$', 'reason': 'All digits are identical'},
                {'pattern': '^1234567890$', 'reason': 'Sequential test number'},
                {'pattern': '^9876543210$', 'reason': 'Reverse sequential'},
                {'pattern': '^555[0-1]\\d{6}$', 'reason': 'Reserved test number'}
            ]
        }

        tier, reason, suggestion = validate_phone(record, header_map, rules)

        assert tier == 'FAIL', "Sequential test number should fail validation"
        assert 'Sequential' in reason, f"Expected 'Sequential' in reason, got: {reason}"
        assert suggestion == 'Please use a valid phone number'

    def test_all_same_digits_invalid(self):
        """Phone with all same digits should be invalid."""
        from scripts.processor import validate_phone

        record = {'Phone': '5555555555'}
        header_map = {'phone': 'Phone'}
        rules = {
            'invalid_phone_patterns': [
                {'pattern': '^(.)\\1{9}$', 'reason': 'All digits are identical'},
                {'pattern': '^1234567890$', 'reason': 'Sequential test number'},
                {'pattern': '^9876543210$', 'reason': 'Reverse sequential'},
                {'pattern': '^555[0-1]\\d{6}$', 'reason': 'Reserved test number'}
            ]
        }

        tier, reason, suggestion = validate_phone(record, header_map, rules)

        assert tier == 'FAIL'
        assert 'identical' in reason.lower()

    def test_reserved_test_pattern_invalid(self):
        """Reserved test pattern 555-01xx-xxxx should be invalid."""
        from scripts.processor import validate_phone

        record = {'Phone': '5550123456'}
        header_map = {'phone': 'Phone'}
        rules = {
            'invalid_phone_patterns': [
                {'pattern': '^(.)\\1{9}$', 'reason': 'All digits are identical'},
                {'pattern': '^1234567890$', 'reason': 'Sequential test number'},
                {'pattern': '^9876543210$', 'reason': 'Reverse sequential'},
                {'pattern': '^555[0-1]\\d{6}$', 'reason': 'Reserved test number'}
            ]
        }

        tier, reason, suggestion = validate_phone(record, header_map, rules)

        assert tier == 'FAIL'
        assert 'Reserved' in reason or 'reserved' in reason.lower()

    def test_valid_phone_passes(self):
        """Valid phone number should pass."""
        from scripts.processor import validate_phone

        record = {'Phone': '2125551234'}  # Valid NYC area code
        header_map = {'phone': 'Phone'}
        rules = {
            'invalid_phone_patterns': [
                {'pattern': '^(.)\\1{9}$', 'reason': 'All digits are identical'},
                {'pattern': '^1234567890$', 'reason': 'Sequential test number'},
                {'pattern': '^9876543210$', 'reason': 'Reverse sequential'},
                {'pattern': '^555[0-1]\\d{6}$', 'reason': 'Reserved test number'}
            ]
        }

        tier, reason, suggestion = validate_phone(record, header_map, rules)

        assert tier == 'PASS'
        assert reason is None


@pytest.mark.integration
class TestInlineEmailValidation:
    """Test email validation catches invalid formats."""

    def test_email_without_at_invalid(self):
        """Email without @ should be invalid."""
        from scripts.processor import validate_email

        record = {'Email': 'notanemail'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': {}}
        reference = {'domains': ['gmail.com', 'yahoo.com']}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)

        assert tier == 'FAIL'
        assert '@' in reason.lower() or 'invalid' in reason.lower()

    def test_email_with_typo_shows_suggestion(self):
        """Email with known typo should show warning and suggestion."""
        from scripts.processor import validate_email

        record = {'Email': 'user@gmai.com'}  # Common typo
        header_map = {'email': 'Email'}
        rules = {
            'email_typos': [
                {'from': 'gmai.com', 'to': 'gmail.com', 'confidence': 0.99}
            ]
        }
        reference = {'domains': ['gmail.com', 'yahoo.com']}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)

        # Typos result in WARNING tier with suggestion
        assert tier == 'WARNING'
        assert suggestion is not None

    def test_valid_email_passes(self):
        """Valid email should pass."""
        from scripts.processor import validate_email

        record = {'Email': 'user@example.com'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': {}}
        reference = {'domains': ['gmail.com', 'yahoo.com']}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)

        assert tier == 'PASS'


@pytest.mark.integration
class TestInlineAmountValidation:
    """Test amount validation catches invalid formats."""

    def test_zero_amount_invalid(self):
        """Zero amount should be invalid."""
        from scripts.processor import validate_amount

        record = {'Amount': '0'}
        header_map = {'amount': 'Amount'}
        rules = {'high_dollar_threshold': 1000}
        reference = {}

        tier, reason, suggestion = validate_amount(record, header_map, reference)

        assert tier == 'FAIL'

    def test_negative_amount_invalid(self):
        """Negative amount should be invalid."""
        from scripts.processor import validate_amount

        record = {'Amount': '-100'}
        header_map = {'amount': 'Amount'}
        rules = {'high_dollar_threshold': 1000}
        reference = {}

        tier, reason, suggestion = validate_amount(record, header_map, reference)

        assert tier == 'FAIL'

    def test_non_numeric_amount_invalid(self):
        """Non-numeric amount should be invalid."""
        from scripts.processor import validate_amount

        record = {'Amount': 'notanumber'}
        header_map = {'amount': 'Amount'}
        rules = {'high_dollar_threshold': 1000}
        reference = {}

        tier, reason, suggestion = validate_amount(record, header_map, reference)

        assert tier == 'FAIL'

    def test_valid_amount_passes(self):
        """Valid amount should pass."""
        from scripts.processor import validate_amount

        record = {'Amount': '150.50'}
        header_map = {'amount': 'Amount'}
        rules = {'high_dollar_threshold': 1000}
        reference = {}

        tier, reason, suggestion = validate_amount(record, header_map, reference)

        assert tier == 'PASS'
