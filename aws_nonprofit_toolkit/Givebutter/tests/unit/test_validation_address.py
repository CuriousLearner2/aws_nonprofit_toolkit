"""Unit tests for address validation."""
import pytest
from processor import validate_address


class TestAddressValidation:
    """Test address validation function."""

    @pytest.mark.unit
    def test_valid_complete_address(self):
        """Test valid complete address."""
        record = {
            'Address 1': '123 Main St',
            'City': 'Springfield',
            'State': 'IL'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_missing_address_1_column(self):
        """Test when address 1 column is missing."""
        record = {
            'City': 'Springfield',
            'State': 'IL'
        }
        header_map = {
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_missing_city_column(self):
        """Test when city column is missing."""
        record = {
            'Address 1': '123 Main St',
            'State': 'IL'
        }
        header_map = {
            'address_1': 'Address 1',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_missing_state_column(self):
        """Test when state column is missing."""
        record = {
            'Address 1': '123 Main St',
            'City': 'Springfield'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_empty_address_1(self):
        """Test empty address 1 field."""
        record = {
            'Address 1': '',
            'City': 'Springfield',
            'State': 'IL'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'WARNING'
        assert reason == 'Missing address'

    @pytest.mark.unit
    def test_empty_city(self):
        """Test empty city field."""
        record = {
            'Address 1': '123 Main St',
            'City': '',
            'State': 'IL'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_empty_state(self):
        """Test empty state field."""
        record = {
            'Address 1': '123 Main St',
            'City': 'Springfield',
            'State': ''
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_all_address_fields_empty(self):
        """Test all address fields empty."""
        record = {
            'Address 1': '',
            'City': '',
            'State': ''
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'WARNING'
        assert reason == 'Missing address'

    @pytest.mark.unit
    def test_address_with_apartment(self):
        """Test address with apartment number."""
        record = {
            'Address 1': '123 Main St, Apt 4B',
            'City': 'New York',
            'State': 'NY'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_address_with_special_characters(self):
        """Test address with special characters."""
        record = {
            'Address 1': "123 O'Brien St, Suite #200",
            'City': 'San Francisco',
            'State': 'CA'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_address_with_zip(self):
        """Test complete address with zip code (when zip column exists)."""
        record = {
            'Address 1': '123 Main St',
            'City': 'Springfield',
            'State': 'IL',
            'Zip': '62701'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State',
            'zip': 'Zip'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_international_address(self):
        """Test international address format."""
        record = {
            'Address 1': 'Oxford Street 5',
            'City': 'London',
            'State': 'England'
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_address_with_whitespace(self):
        """Test address fields with leading/trailing whitespace."""
        record = {
            'Address 1': '  123 Main St  ',
            'City': '  Springfield  ',
            'State': '  IL  '
        }
        header_map = {
            'address_1': 'Address 1',
            'city': 'City',
            'state': 'State'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_no_address_columns_in_mapping(self):
        """Test when no address columns are in mapping."""
        record = {
            'Name': 'John Smith'
        }
        header_map = {
            'name': 'Name'
        }

        tier, reason = validate_address(record, header_map)
        assert tier == 'PASS'
