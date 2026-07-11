"""Unit tests for amount validation."""
import inspect

import pytest
from processor import validate_amount
from scripts.householder.amount_validation_service import validate_review_amount


class TestAmountValidation:
    """Test amount validation function."""

    @pytest.mark.unit
    def test_valid_amount(self):
        """Test valid amount passes."""
        record = {'Amount': '100.00'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'
        assert reason is None
        assert suggestion is None

    @pytest.mark.unit
    def test_valid_amount_with_dollar_sign(self):
        """Test valid amount with dollar sign."""
        record = {'Amount': '$50.00'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_valid_amount_with_comma(self):
        """Test valid amount with comma separator."""
        record = {'Amount': '1,500.00'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 2000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_invalid_amount_with_malformed_commas(self):
        """Test amount values with malformed commas are rejected."""
        record = {'Amount': '1,2,3'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'invalid' in reason.lower() and 'format' in reason.lower()

    @pytest.mark.unit
    def test_amount_with_too_many_decimal_places(self):
        """Test amount values with more than two decimal places are rejected."""
        record = {'Amount': '100.001'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert '2 decimal places' in reason.lower()

    @pytest.mark.unit
    def test_valid_integer_amount(self):
        """Test valid integer amount (no decimals)."""
        record = {'Amount': '500'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_missing_amount(self):
        """Test missing amount field."""
        record = {'Amount': ''}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert any(word in reason.lower() for word in ['missing', 'empty']), \
            f"Expected 'missing' or 'empty' in reason, got: {reason}"

    @pytest.mark.unit
    def test_invalid_amount_format(self):
        """Test invalid amount format."""
        record = {'Amount': 'not_a_number'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'invalid' in reason.lower() and 'format' in reason.lower()

    @pytest.mark.unit
    def test_zero_amount(self):
        """Test zero amount."""
        record = {'Amount': '0'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'greater than 0' in reason

    @pytest.mark.unit
    def test_negative_amount(self):
        """Test negative amount."""
        record = {'Amount': '-100'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'greater than 0' in reason

    @pytest.mark.unit
    def test_amount_below_typical_range(self):
        """Test amount below typical range."""
        record = {'Amount': '0.50'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'WARNING'
        assert 'below typical range' in reason.lower()

    @pytest.mark.unit
    def test_amount_above_typical_range(self):
        """Test amount above typical range."""
        record = {'Amount': '150000'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'WARNING'
        assert 'above typical range' in reason.lower()

    @pytest.mark.unit
    def test_high_dollar_donation(self):
        """Test high-dollar donation is still valid (threshold is informational)."""
        record = {'Amount': '1000.00'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_high_dollar_donation_custom_threshold(self):
        """Test high-dollar donation with custom threshold."""
        record = {'Amount': '5000.00'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 10000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_missing_amount_column_fails(self):
        """Test when amount column is missing (required field)."""
        record = {'Name': 'John Smith'}
        header_map = {}  # No amount mapping
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'column not found' in reason.lower()

    @pytest.mark.unit
    def test_amount_with_whitespace(self):
        """Test amount with whitespace."""
        record = {'Amount': '  100.00  '}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_very_large_donation(self):
        """Test very large donation amount (within valid range)."""
        record = {'Amount': '50000.00'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_small_valid_donation(self):
        """Test small valid donation."""
        record = {'Amount': '1.00'}
        header_map = {'amount': 'Amount'}
        reference = {
            'amount_statistics': {'valid_range': [1, 100000]},
            'high_dollar_threshold': 1000
        }

        tier, reason, suggestion = validate_amount(record, header_map, reference)
        assert tier == 'PASS'


class TestCanonicalAmountValidation:
    """Test the Decimal-backed canonical amount validator."""

    def test_valid_decimal_variants_pass(self):
        valid_amounts = [
            '0.50',
            '5',
            '5.',
            '.50',
            '5.00',
            '12.3',
            '12.30',
            '1000',
            '1000.00',
            '$5.00',
            '1,000.00',
        ]
        for amount in valid_amounts:
            result = validate_review_amount(amount)
            assert result.valid, f"Amount '{amount}' should be valid, got: {result.blocking_error}"

    def test_invalid_amount_shapes_fail(self):
        invalid_amounts = [
            '0',
            '0.00',
            '5.001',
            '12.345',
            'abc',
            '5 dollars',
            '1.2.3',
            'NaN',
            'Infinity',
            '-Infinity',
            '+5.00',
        ]
        for amount in invalid_amounts:
            result = validate_review_amount(amount)
            assert not result.valid, f"Amount '{amount}' should be invalid"

    def test_validator_does_not_use_float(self):
        source = inspect.getsource(validate_review_amount)
        assert 'float(' not in source
