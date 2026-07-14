"""Unit tests for phone_validation_service using phonenumbers library."""
import pytest
from householder.phone_validation_service import (
    validate_review_phone,
    validate_phone,
    is_valid_phone,
    format_phone,
)


@pytest.mark.unit
class TestPhoneValidationService:
    """Test phone validation using Google's phonenumbers library."""

    # ===== validate_phone() tests =====

    def test_validate_us_phone_basic(self):
        """Test validation of basic US phone number."""
        result = validate_phone('4155552671', 'US')
        assert result['valid'] is True
        assert result['formatted'] == '+14155552671'
        assert result['country_code'] == 1
        assert result['region'] == 'US'
        assert result['number_type'] in ['MOBILE', 'FIXED_LINE', 'FIXED_LINE_OR_MOBILE']

    def test_validate_us_phone_formatted(self):
        """Test validation of formatted US phone number."""
        result = validate_phone('(415) 555-2671', 'US')
        assert result['valid'] is True
        assert result['formatted'] == '+14155552671'

    def test_validate_us_phone_with_country_code(self):
        """Test validation of US phone with +1 prefix."""
        result = validate_phone('+1 415 555 2671', 'US')
        assert result['valid'] is True
        assert result['formatted'] == '+14155552671'

    def test_validate_international_gb(self):
        """Test validation of UK phone number."""
        result = validate_phone('2079460958', 'GB')
        assert result['valid'] is False
        assert 'error' in result

    def test_validate_international_fr(self):
        """Test validation of French phone number."""
        result = validate_phone('140205050', 'FR')
        assert result['valid'] is False
        assert 'error' in result

    def test_validate_invalid_too_short(self):
        """Test validation of too-short phone number."""
        result = validate_phone('555', 'US')
        assert result['valid'] is False
        assert 'error' in result

    def test_validate_invalid_too_long(self):
        """Test validation of too-long phone number."""
        result = validate_phone('123456789012345', 'US')
        assert result['valid'] is False
        assert 'error' in result

    def test_validate_invalid_format(self):
        """Test validation of completely invalid format."""
        result = validate_phone('abc-def-ghij', 'US')
        assert result['valid'] is False
        assert 'error' in result

    def test_validate_empty_phone(self):
        """Test validation of empty phone number."""
        result = validate_phone('', 'US')
        assert result['valid'] is False
        assert 'error' in result

    def test_validate_review_phone_blank_policy(self):
        """Test blank phone policy for the canonical helper."""
        blank_disallowed = validate_review_phone('', allow_blank=False)
        assert blank_disallowed.valid is False
        assert blank_disallowed.blocking_error == 'Phone number is empty'

        blank_allowed = validate_review_phone('', allow_blank=True)
        assert blank_allowed.valid is True
        assert blank_allowed.normalized_value == ''

    def test_validate_review_phone_trims_whitespace(self):
        """Test whitespace is trimmed before validation."""
        result = validate_review_phone('  (415) 555-2671  ', allow_blank=False)
        assert result.valid is True
        assert result.normalized_value == '(415) 555-2671'

    def test_validate_review_phone_rejects_short_domestic_number(self):
        """Test 7-digit domestic numbers are rejected under the strict 10-digit policy."""
        result = validate_review_phone('5612346', allow_blank=False)
        assert result.valid is False
        assert result.blocking_error == 'Invalid phone format'

    def test_validate_returns_all_fields(self):
        """Test that validation returns all expected fields."""
        result = validate_phone('4155552671', 'US')
        assert 'valid' in result
        assert 'formatted' in result
        assert 'national' in result
        assert 'international' in result
        assert 'country_code' in result
        assert 'region' in result
        assert 'number_type' in result

    # ===== is_valid_phone() tests =====

    def test_is_valid_phone_true(self):
        """Test simple boolean validation - valid phone."""
        assert is_valid_phone('4155552671', 'US') is True

    def test_is_valid_phone_false(self):
        """Test simple boolean validation - invalid phone."""
        assert is_valid_phone('555', 'US') is False

    def test_is_valid_phone_formatted(self):
        """Test boolean validation with formatted phone."""
        assert is_valid_phone('(415) 555-2671', 'US') is True

    def test_is_valid_phone_international(self):
        """Test boolean validation with international format."""
        assert is_valid_phone('+1 415 555 2671', 'US') is True

    # ===== format_phone() tests =====

    def test_format_phone_e164(self):
        """Test E164 formatting."""
        result = format_phone('(415) 555-2671', 'US', 'E164')
        assert result == '+14155552671'

    def test_format_phone_national(self):
        """Test national format."""
        result = format_phone('(415) 555-2671', 'US', 'NATIONAL')
        assert '415' in result
        assert '555' in result
        assert '2671' in result

    def test_format_phone_international(self):
        """Test international format."""
        result = format_phone('4155552671', 'US', 'INTERNATIONAL')
        assert '+1' in result

    def test_format_phone_invalid_returns_none(self):
        """Test that invalid phone returns None."""
        result = format_phone('555', 'US', 'E164')
        assert result is None

    def test_format_phone_default_e164(self):
        """Test that default format is E164."""
        result = format_phone('(415) 555-2671', 'US')
        assert result == '+14155552671'

    def test_format_phone_invalid_format_type(self):
        """Test that invalid format type defaults to E164."""
        result = format_phone('(415) 555-2671', 'US', 'INVALID')
        assert result == '+14155552671'

    # ===== Country-specific tests =====

    def test_uk_phone_with_uk_country_code(self):
        """Test UK phone number with GB country code."""
        result = validate_phone('2079460958', 'GB')
        assert result['valid'] is False
        assert 'error' in result

    def test_canadian_phone(self):
        """Test Canadian phone number."""
        result = validate_phone('6135551234', 'CA')
        assert result['valid'] is True
        assert result['country_code'] == 1  # Canada shares country code with US
        assert result['region'] == 'CA'

    def test_australian_phone(self):
        """Test Australian phone number."""
        result = validate_phone('291234567', 'AU')
        assert result['valid'] is False
        assert 'error' in result

    # ===== Edge cases =====

    def test_phone_with_extension(self):
        """Test phone with extension is rejected under the strict 10-digit policy."""
        result = validate_phone('4155552671x123', 'US')
        assert result['valid'] is False
        assert 'error' in result

    def test_phone_with_leading_plus_and_country_mismatch(self):
        """Test that explicit +1 prefix works regardless of country param."""
        result = validate_phone('+14155552671', 'GB')
        # Should parse as US number due to explicit +1
        assert result['valid'] is True
        assert result['country_code'] == 1

    def test_repeated_phone_number_formats(self):
        """Test various formats of the same phone number."""
        formats = [
            '4155552671',
            '415-555-2671',
            '(415) 555-2671',
            '415.555.2671',
            '+1 415 555 2671',
            '1-415-555-2671',
        ]
        for fmt in formats:
            result = validate_phone(fmt, 'US')
            assert result['valid'] is True, f"Failed for format: {fmt}"
            assert result['formatted'] == '+14155552671'
