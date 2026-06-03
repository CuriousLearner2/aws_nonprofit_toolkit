"""Unit tests for transaction ID validation."""
import pytest
from processor import validate_transaction_id


class TestTransactionIDValidation:
    """Test transaction ID validation function."""

    @pytest.mark.unit
    def test_valid_transaction_id(self):
        """Test valid transaction ID passes."""
        record = {'Transaction ID': '12345'}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_valid_donation_id(self):
        """Test valid donation ID (fuzzy match) passes."""
        record = {'Donation ID': 'donor-123456'}
        header_map = {'transaction_id': 'Donation ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_empty_transaction_id_fails(self):
        """Test empty transaction ID fails (required field)."""
        record = {'Transaction ID': ''}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'FAIL'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_whitespace_only_transaction_id_fails(self):
        """Test whitespace-only transaction ID fails."""
        record = {'Transaction ID': '   '}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'FAIL'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_missing_transaction_id_column_fails(self):
        """Test missing transaction ID column fails (required field)."""
        record = {'Name': 'John Smith'}
        header_map = {}  # No transaction_id mapping

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'FAIL'
        assert 'column not found' in reason.lower()

    @pytest.mark.unit
    def test_numeric_transaction_id(self):
        """Test numeric transaction ID."""
        record = {'Transaction ID': '98765432'}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_alphanumeric_transaction_id(self):
        """Test alphanumeric transaction ID."""
        record = {'Transaction ID': 'TXN-2026-05-001'}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_transaction_id_with_whitespace(self):
        """Test transaction ID with surrounding whitespace."""
        record = {'Transaction ID': '  12345  '}
        header_map = {'transaction_id': 'Transaction ID'}

        tier, reason, suggestion = validate_transaction_id(record, header_map)
        assert tier == 'PASS'
