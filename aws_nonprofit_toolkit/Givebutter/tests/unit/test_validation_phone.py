"""Unit tests for phone validation."""
import pytest
from processor import validate_phone


class TestPhoneValidation:
    """Test phone validation function."""

    @pytest.mark.unit
    def test_valid_10_digit_phone(self):
        """Test valid 10-digit US phone number."""
        record = {'Phone': '5551234567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None
        assert suggestion is None

    @pytest.mark.unit
    def test_valid_10_digit_formatted_phone(self):
        """Test valid 10-digit phone with standard formatting."""
        record = {'Phone': '(555) 123-4567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_valid_11_digit_phone_with_leading_1(self):
        """Test valid 11-digit phone starting with 1."""
        record = {'Phone': '15551234567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_sequential_test_number_is_accepted(self):
        """Sequential-looking but possible numbers remain accepted."""
        record = {'Phone': '1234567890'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': [
            {'pattern': r'^1234567890$', 'reason': 'Sequential test number'}
        ]}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_all_same_digit_number_is_accepted(self):
        """All-same-digit but possible numbers remain accepted."""
        record = {'Phone': '5555555555'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': [
            {'pattern': r'^(\d)\1{9}$', 'reason': 'All same digit'}
        ]}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_reserved_test_555_number_is_accepted(self):
        """Reserved-looking but possible 555 numbers remain accepted."""
        record = {'Phone': '5550123456'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': [
            {'pattern': r'^555[0-1]\d{6}$', 'reason': 'Reserved test number'}
        ]}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_phone_too_short(self):
        """Test phone with fewer than 10 digits."""
        record = {'Phone': '555123'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'FAIL'
        assert 'invalid' in reason.lower()

    @pytest.mark.unit
    def test_phone_too_long(self):
        """Test phone with more than 11 digits."""
        record = {'Phone': '123456789012'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'FAIL'
        assert 'invalid' in reason.lower()

    @pytest.mark.unit
    def test_missing_phone_column(self):
        """Test when phone column is missing."""
        record = {'Name': 'John Smith'}
        header_map = {}  # No phone mapping
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'WARNING'
        assert 'not found' in reason.lower()
        assert 'Add phone numbers' in suggestion

    @pytest.mark.unit
    def test_empty_phone(self):
        """Test empty phone field."""
        record = {'Phone': ''}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'WARNING'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_area_code_starting_with_0(self):
        """Test area code starting with 0 is accepted when parseable."""
        record = {'Phone': '0551234567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_area_code_starting_with_1_as_first_digit(self):
        """Test area code starting with 1 (not as leading 1) is accepted when parseable."""
        record = {'Phone': '1551234567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_unusual_formatting_warning(self):
        """Test that unusual formatting generates warning."""
        record = {'Phone': '555.123.4567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'WARNING'
        assert 'format' in reason.lower()

    @pytest.mark.unit
    def test_phone_with_plus_sign(self):
        """Test phone with plus sign prefix."""
        record = {'Phone': '+1 (555) 123-4567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        # Should handle + sign in extraction
        assert tier in ['PASS', 'WARNING']

    @pytest.mark.unit
    def test_phone_case_insensitive(self):
        """Test phone validation is case insensitive."""
        record = {'Phone': '(555) 123-4567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_phone_with_whitespace(self):
        """Test phone with extra whitespace."""
        record = {'Phone': '  (555) 123-4567  '}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_possible_but_not_formally_valid_number_is_preserved(self):
        """Test structurally possible but unassigned numbers remain accepted."""
        record = {'Phone': '8001234567'}
        header_map = {'phone': 'Phone'}
        rules = {'invalid_phone_patterns': []}

        tier, reason, suggestion = validate_phone(record, header_map, rules)
        assert tier == 'PASS'
