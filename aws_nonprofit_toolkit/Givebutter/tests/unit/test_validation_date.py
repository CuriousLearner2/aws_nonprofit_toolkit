"""Unit tests for date validation."""
import pytest
from processor import validate_date


class TestDateValidation:
    """Test date validation function."""

    @pytest.mark.unit
    def test_valid_date_iso_format(self):
        """Test valid ISO format date passes."""
        record = {'Date': '2026-05-20'}
        header_map = {'date': 'Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_valid_donation_date_fuzzy_match(self):
        """Test valid donation date (fuzzy match) passes."""
        record = {'Donation Date': '2026-05-20'}
        header_map = {'date': 'Donation Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_valid_gift_date_fuzzy_match(self):
        """Test valid gift date (fuzzy match) passes."""
        record = {'Gift Date': '05/20/2026'}
        header_map = {'date': 'Gift Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_valid_date_received_fuzzy_match(self):
        """Test valid date received (fuzzy match) passes."""
        record = {'Date Received': '2026-05-20'}
        header_map = {'date': 'Date Received'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_lowercase_donation_date_fuzzy_match(self):
        """Test lowercase donation_date (fuzzy match) passes."""
        record = {'donation_date': '2026-05-20'}
        header_map = {'date': 'donation_date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_empty_date_fails(self):
        """Test empty date field fails (required field)."""
        record = {'Date': ''}
        header_map = {'date': 'Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'FAIL'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_whitespace_only_date_fails(self):
        """Test whitespace-only date fails."""
        record = {'Date': '   '}
        header_map = {'date': 'Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'FAIL'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_missing_date_column_fails(self):
        """Test missing date column fails (required field)."""
        record = {'Name': 'John Smith'}
        header_map = {}  # No date mapping

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'FAIL'
        assert 'column not found' in reason.lower()

    @pytest.mark.unit
    def test_various_date_formats_pass(self):
        """Test various date format strings pass (format validation not enforced)."""
        date_formats = [
            '2026-05-20',      # ISO
            '05/20/2026',      # US
            '20/05/2026',      # EU
            '2026-05-20T10:00:00',  # ISO with time
            'May 20, 2026',    # Text
            '05-20-2026',      # Dash separator
            '20260520',        # YYYYMMDD
        ]

        for date_str in date_formats:
            record = {'Date': date_str}
            header_map = {'date': 'Date'}

            tier, reason, suggestion = validate_date(record, header_map)
            assert tier == 'PASS', f"Date format '{date_str}' should pass"

    @pytest.mark.unit
    def test_date_with_whitespace(self):
        """Test date with surrounding whitespace."""
        record = {'Date': '  2026-05-20  '}
        header_map = {'date': 'Date'}

        tier, reason, suggestion = validate_date(record, header_map)
        assert tier == 'PASS'
