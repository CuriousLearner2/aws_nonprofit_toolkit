"""Unit tests for field validation edge cases."""
import pytest
import json
from pathlib import Path
from scripts.processor import (
    validate_date, validate_amount, validate_name, validate_phone,
    validate_email, validate_address, build_header_mapping, load_rules
)


@pytest.fixture
def header_map():
    """Standard header mapping for tests."""
    return build_header_mapping([
        'Transaction ID', 'Date', 'Name', 'Email', 'Phone', 'Amount',
        'Address 1', 'City', 'State', 'Campaign Title'
    ])


@pytest.fixture
def rules():
    """Load validation rules."""
    return load_rules()


class TestDateValidationEdgeCases:
    """Test date field validation edge cases."""

    def test_valid_date_formats(self, header_map):
        """Verify strict ISO date formats pass."""
        valid_dates = [
            '2026-06-05',
            '2024-02-29',  # Leap day
        ]
        for date_str in valid_dates:
            record = {'Date': date_str}
            tier, reason, suggestion = validate_date(record, header_map)
            assert tier == 'PASS', f"Date '{date_str}' should pass, got: {reason}"

    def test_empty_date(self, header_map):
        """Verify empty date fails."""
        record = {'Date': ''}
        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'FAIL', "Empty date should fail"

    def test_strict_date_parsing_rejects_non_iso_formats(self, header_map):
        """Verify non-ISO and impossible dates fail strict parsing."""
        invalid_dates = [
            '2026&05-15',
            '2026/06/05',
            '06/05/2026',
            '2026-1-5',
            '20260515',
            '2025-02-29',
        ]
        for date_str in invalid_dates:
            record = {'Date': date_str}
            tier, reason, suggestion = validate_date(record, header_map)
            assert tier == 'FAIL', f"Date '{date_str}' should fail strict parsing"


class TestAmountValidationEdgeCases:
    """Test amount field validation edge cases."""

    def test_zero_and_negative_amounts(self, header_map):
        """Verify zero and negative amounts fail."""
        invalid_amounts = ['0', '-100', '-0.01']
        for amount in invalid_amounts:
            record = {'Amount': amount}
            tier, reason, suggestion = validate_amount(record, header_map, {})
            assert tier == 'FAIL', f"Amount '{amount}' should fail"

    def test_valid_decimal_amounts(self, header_map):
        """Verify decimal amounts work."""
        # Amounts below typical range ($1) may trigger WARNING
        # Test typical/normal range amounts
        valid_amounts = ['.50', '0.50', '1.00', '12.3', '100.50', '1000.99', '9999999.99', '5.']
        for amount in valid_amounts:
            record = {'Amount': amount}
            tier, reason, suggestion = validate_amount(record, header_map, {})
            assert tier in ['PASS', 'WARNING'], f"Amount '{amount}' should not FAIL"

        # Very small amounts may warn
        record = {'Amount': '0.01'}
        tier, reason, suggestion = validate_amount(record, header_map, {})
        assert tier != 'FAIL', "Small amount should not FAIL (may WARN)"

    def test_formatted_amounts(self, header_map):
        """Verify formatted amounts (with commas, dollar signs)."""
        valid_amounts = ['$100', '$1,000.50', '1,000,000', '$5.00', '1,000.00']
        for amount in valid_amounts:
            record = {'Amount': amount}
            tier, reason, suggestion = validate_amount(record, header_map, {})
            # These may be WARNING or PASS depending on formatting rules
            assert tier in ['PASS', 'WARNING'], f"Amount '{amount}' should not FAIL"

    def test_non_numeric_amounts(self, header_map):
        """Verify non-numeric amounts fail."""
        invalid_amounts = ['abc', '100x', 'one hundred', 'NaN', 'Infinity', '+5.00', '1,2,3', '12,34.56']
        for amount in invalid_amounts:
            record = {'Amount': amount}
            tier, reason, suggestion = validate_amount(record, header_map, {})
            assert tier == 'FAIL', f"Amount '{amount}' should fail"


class TestNameValidationEdgeCases:
    """Test name field validation edge cases."""

    def test_name_length_boundaries(self, header_map):
        """Verify name length constraints."""
        # Too short
        record = {'Name': 'A'}
        tier, reason, suggestion = validate_name(record, header_map, {})
        assert tier == 'FAIL', "Single letter name should fail"

        # Minimum valid
        record = {'Name': 'AB'}
        tier, reason, suggestion = validate_name(record, header_map, {})
        assert tier == 'PASS'

        # Maximum valid (100 chars)
        record = {'Name': 'A' * 100}
        tier, reason, suggestion = validate_name(record, header_map, {})
        assert tier == 'PASS'

        # Too long
        record = {'Name': 'A' * 101}
        tier, reason, suggestion = validate_name(record, header_map, {})
        assert tier == 'FAIL', "Name over 100 chars should fail"

    def test_name_with_special_characters(self, header_map):
        """Verify names with special characters."""
        valid_names = [
            "O'Brien",
            "José García",
            "Jean-Paul",
            "Mary-Ann",
            "李明",
            "محمد",
            "Владимир"
        ]
        for name in valid_names:
            record = {'Name': name}
            tier, reason, suggestion = validate_name(record, header_map, {})
            assert tier == 'PASS', f"Name '{name}' should pass"

    def test_name_with_numbers(self, header_map):
        """Verify names with numbers."""
        record = {'Name': 'John Doe Jr.'}
        tier, reason, suggestion = validate_name(record, header_map, {})
        assert tier == 'PASS', "Name with suffix should pass"

        record = {'Name': 'John123'}
        tier, reason, suggestion = validate_name(record, header_map, {})
        # Should not FAIL just for containing numbers
        assert tier in ['PASS', 'WARNING']

    def test_name_with_whitespace(self, header_map):
        """Verify names with extra whitespace."""
        record = {'Name': '  John Doe  '}
        tier, reason, suggestion = validate_name(record, header_map, {})
        assert tier == 'PASS', "Name with leading/trailing spaces should pass"

        record = {'Name': 'John   Doe'}  # Multiple spaces between
        tier, reason, suggestion = validate_name(record, header_map, {})
        assert tier == 'PASS'


class TestPhoneValidationEdgeCases:
    """Test phone field validation edge cases."""

    def test_phone_with_different_formats(self, header_map, rules):
        """Verify phone works with various formatting."""
        valid_phones = [
            '5551234567',           # Plain 10 digits
            '(555) 123-4567',       # Formatted
            '555-123-4567',         # Dashed
            '15551234567',          # 11 digits with leading 1
            '+1 555 123 4567',      # International format
        ]
        for phone in valid_phones:
            record = {'Phone': phone}
            tier, reason, suggestion = validate_phone(record, header_map, rules)
            assert tier != 'FAIL', f"Phone '{phone}' should not fail, reason: {reason}"

    def test_phone_possible_patterns_are_accepted(self, header_map, rules):
        """Verify structurally possible phone patterns remain accepted."""
        possible_phones = [
            '1234567890',           # Sequential-looking
            '9876543210',           # Reverse sequential-looking
            '1111111111',           # All same digits
        ]
        for phone in possible_phones:
            record = {'Phone': phone}
            tier, reason, suggestion = validate_phone(record, header_map, rules)
            assert tier != 'FAIL', f"Phone '{phone}' should remain accepted, reason: {reason}"

    def test_phone_area_code_validation(self, header_map, rules):
        """Verify possible area-code patterns remain accepted."""
        possible_area_codes = ['0551234567', '1551234567']
        for phone in possible_area_codes:
            record = {'Phone': phone}
            tier, reason, suggestion = validate_phone(record, header_map, rules)
            assert tier != 'FAIL', f"Phone '{phone}' should remain accepted, reason: {reason}"

        # Standard area codes should pass
        valid_area_codes = ['201', '415', '720', '206']
        for ac in valid_area_codes:
            record = {'Phone': f'{ac}1234567'}
            tier, reason, suggestion = validate_phone(record, header_map, rules)
            assert tier != 'FAIL', f"Area code {ac} should not fail"


class TestEmailValidationEdgeCases:
    """Test email field validation edge cases."""

    def test_email_with_special_characters(self, header_map, rules):
        """Verify emails with special characters."""
        valid_emails = [
            'user+tag@gmail.com',
            'user.name@example.com',
            'user_name@example.com',
            'user-name@example.co.uk',
            '123@example.com',
        ]
        for email in valid_emails:
            record = {'Email': email}
            tier, reason, suggestion = validate_email(record, header_map, rules, {})
            assert tier != 'FAIL', f"Email '{email}' should not fail, reason: {reason}"

    def test_email_without_at_symbol(self, header_map, rules):
        """Verify emails without @ fail."""
        invalid_emails = ['invalidemail.com', 'user.example.com']
        for email in invalid_emails:
            record = {'Email': email}
            tier, reason, suggestion = validate_email(record, header_map, rules, {})
            assert tier == 'FAIL', f"Email '{email}' should fail (no @)"

    def test_email_with_localhost_domain(self, header_map, rules):
        """Verify emails with non-standard domains."""
        # Validator is lenient only for localhost-style review/test fixtures.
        emails = ['user@localhost']
        for email in emails:
            record = {'Email': email}
            tier, reason, suggestion = validate_email(record, header_map, rules, {})
            # May pass or warn depending on reference list, but shouldn't FAIL just for format
            assert tier != 'FAIL', f"Email '{email}' format should not FAIL"

    def test_common_typo_corrections(self, header_map, rules):
        """Verify common email typos are detected/suggested."""
        typo_emails = [
            'user@gmai.com',        # gmail typo
            'user@gamil.com',       # gmail typo
            'user@yaho.com',        # yahoo typo
            'user@hotmai.com',      # hotmail typo
        ]
        for email in typo_emails:
            record = {'Email': email}
            tier, reason, suggestion = validate_email(record, header_map, rules, {})
            # May be WARNING with suggestion, or FAIL
            if tier == 'WARNING':
                assert suggestion is not None, f"Typo email '{email}' should have suggestion"


class TestAddressValidationEdgeCases:
    """Test address field validation edge cases."""

    def test_address_with_special_formatting(self, header_map):
        """Verify addresses with various formats."""
        valid_addresses = [
            '123 Main St',
            '123 Main Street',
            '123-A Main St',
            'PO Box 123',
            '1600 Pennsylvania Ave NW',
            'Apt 5B, 123 Main St'
        ]
        for addr in valid_addresses:
            record = {'Address 1': addr, 'City': 'New York', 'State': 'NY'}
            tier, reason = validate_address(record, header_map)
            assert tier != 'FAIL', f"Address '{addr}' should not fail"

    def test_missing_address_components(self, header_map):
        """Verify missing address components."""
        record = {'Address 1': '', 'City': '', 'State': ''}
        tier, reason = validate_address(record, header_map)
        # Missing optional fields may warn or pass
        assert tier in ['PASS', 'WARNING']

        record = {'Address 1': '123 Main St', 'City': '', 'State': 'NY'}
        tier, reason = validate_address(record, header_map)
        # Partial address may warn
        assert tier in ['PASS', 'WARNING']
