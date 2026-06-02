"""Unit tests for header mapping."""
import pytest
from processor import build_header_mapping


class TestHeaderMapping:
    """Test header mapping function for column name matching."""

    @pytest.mark.unit
    def test_core_headers_exact_match(self):
        """Test exact match on core Givebutter headers."""
        columns = [
            'Transaction ID', 'Date', 'Name', 'Email', 'Phone',
            'Amount', 'Campaign Title', 'Status'
        ]

        mapping = build_header_mapping(columns)

        assert mapping['transaction_id'] == 'Transaction ID'
        assert mapping['name'] == 'Name'
        assert mapping['email'] == 'Email'
        assert mapping['phone'] == 'Phone'
        assert mapping['amount'] == 'Amount'
        assert mapping['campaign'] == 'Campaign Title'
        assert mapping['status'] == 'Status'

    @pytest.mark.unit
    def test_fuzzy_transaction_id_match(self):
        """Test fuzzy match for transaction ID variations."""
        # Test with 'Donation ID'
        columns = ['Donation ID', 'Name', 'Email']
        mapping = build_header_mapping(columns)
        assert mapping['transaction_id'] == 'Donation ID'

        # Test with 'Gift ID'
        columns = ['Gift ID', 'Name', 'Email']
        mapping = build_header_mapping(columns)
        assert mapping['transaction_id'] == 'Gift ID'

        # Test with 'Contribution ID'
        columns = ['Contribution ID', 'Name', 'Email']
        mapping = build_header_mapping(columns)
        assert mapping['transaction_id'] == 'Contribution ID'

    @pytest.mark.unit
    def test_fuzzy_name_match(self):
        """Test fuzzy match for name variations."""
        # Test with 'Full Name'
        columns = ['Full Name', 'Email']
        mapping = build_header_mapping(columns)
        assert mapping['name'] == 'Full Name'

        # Test with 'Donor Name'
        columns = ['Donor Name', 'Email']
        mapping = build_header_mapping(columns)
        assert mapping['name'] == 'Donor Name'

        # Test with 'Donor'
        columns = ['Donor', 'Email']
        mapping = build_header_mapping(columns)
        assert mapping['name'] == 'Donor'

    @pytest.mark.unit
    def test_fuzzy_email_match(self):
        """Test fuzzy match for email variations."""
        # Test with 'Email Address'
        columns = ['Name', 'Email Address']
        mapping = build_header_mapping(columns)
        assert mapping['email'] == 'Email Address'

        # Test with 'Primary Email'
        columns = ['Name', 'Primary Email']
        mapping = build_header_mapping(columns)
        assert mapping['email'] == 'Primary Email'

        # Test with 'Contact Email'
        columns = ['Name', 'Contact Email']
        mapping = build_header_mapping(columns)
        assert mapping['email'] == 'Contact Email'

    @pytest.mark.unit
    def test_fuzzy_phone_match(self):
        """Test fuzzy match for phone variations."""
        # Test with 'Phone Number'
        columns = ['Name', 'Phone Number']
        mapping = build_header_mapping(columns)
        assert mapping['phone'] == 'Phone Number'

        # Test with 'Contact Phone'
        columns = ['Name', 'Contact Phone']
        mapping = build_header_mapping(columns)
        assert mapping['phone'] == 'Contact Phone'

        # Test with 'Mobile Phone'
        columns = ['Name', 'Mobile Phone']
        mapping = build_header_mapping(columns)
        assert mapping['phone'] == 'Mobile Phone'

    @pytest.mark.unit
    def test_fuzzy_zip_match(self):
        """Test fuzzy match for zip/postal code variations."""
        # Test with 'Zipcode'
        columns = ['Name', 'Zipcode']
        mapping = build_header_mapping(columns)
        assert mapping['zip'] == 'Zipcode'

        # Test with 'Postal Code'
        columns = ['Name', 'Postal Code']
        mapping = build_header_mapping(columns)
        assert mapping['zip'] == 'Postal Code'

        # Test with 'ZIP Code'
        columns = ['Name', 'ZIP Code']
        mapping = build_header_mapping(columns)
        assert mapping['zip'] == 'ZIP Code'

    @pytest.mark.unit
    def test_fuzzy_campaign_match(self):
        """Test fuzzy match for campaign variations."""
        # Test with 'Fund'
        columns = ['Name', 'Fund']
        mapping = build_header_mapping(columns)
        assert mapping['campaign'] == 'Fund'

        # Test with 'Campaign'
        columns = ['Name', 'Campaign']
        mapping = build_header_mapping(columns)
        assert mapping['campaign'] == 'Campaign'

    @pytest.mark.unit
    def test_fuzzy_address_match(self):
        """Test fuzzy match for address variations."""
        # Test 'Address Line 1' vs 'Address 1'
        columns = ['Address Line 1', 'City', 'State']
        mapping = build_header_mapping(columns)
        assert mapping['address_1'] == 'Address Line 1'

        # Test 'Street Address'
        columns = ['Street Address', 'City', 'State']
        mapping = build_header_mapping(columns)
        assert mapping['address_1'] == 'Street Address'

    @pytest.mark.unit
    def test_core_headers_take_precedence_over_fuzzy(self):
        """Test that core headers match before fuzzy headers."""
        columns = ['Name', 'Email', 'Donor Name', 'Primary Email']
        mapping = build_header_mapping(columns)

        # Should match 'Name' (core) not 'Donor Name' (fuzzy)
        assert mapping['name'] == 'Name'
        # Should match 'Email' (core) not 'Primary Email' (fuzzy)
        assert mapping['email'] == 'Email'

    @pytest.mark.unit
    def test_whitespace_handling(self):
        """Test that leading/trailing whitespace is handled."""
        columns = [' Transaction ID ', '  Name  ', '  Email  ']
        mapping = build_header_mapping(columns)

        assert mapping['transaction_id'] == ' Transaction ID '
        assert mapping['name'] == '  Name  '
        assert mapping['email'] == '  Email  '

    @pytest.mark.unit
    def test_missing_optional_columns(self):
        """Test mapping when optional columns are missing."""
        columns = ['Name', 'Email']  # Missing phone, address, etc.
        mapping = build_header_mapping(columns)

        assert mapping['name'] == 'Name'
        assert mapping['email'] == 'Email'
        assert 'phone' not in mapping
        assert 'address_1' not in mapping

    @pytest.mark.unit
    def test_all_core_headers(self):
        """Test mapping with all core Givebutter headers."""
        columns = [
            'Transaction ID', 'Payout ID', 'Status', 'Date',
            'Name', 'Email', 'Phone',
            'Address 1', 'Address 2', 'City', 'State', 'Zip', 'Country',
            'Amount', 'Processing Fee', 'Givebutter Fee', 'Fees Covered',
            'Payment Method', 'Campaign Title', 'utm_source', 'utm_medium'
        ]
        mapping = build_header_mapping(columns)

        assert len(mapping) >= 15
        assert mapping['transaction_id'] == 'Transaction ID'
        assert mapping['name'] == 'Name'
        assert mapping['address_1'] == 'Address 1'
        assert mapping['campaign'] == 'Campaign Title'

    @pytest.mark.unit
    def test_custom_unmapped_columns_ignored(self):
        """Test that unmapped custom columns don't appear in mapping."""
        columns = [
            'Name', 'Email',
            'Custom Field 1', 'Custom Field 2', 'Another Custom'
        ]
        mapping = build_header_mapping(columns)

        # Standard columns mapped
        assert mapping['name'] == 'Name'
        assert mapping['email'] == 'Email'

        # Custom columns not in mapping
        assert 'Custom Field 1' not in mapping.values()
        assert 'Custom Field 2' not in mapping.values()

    @pytest.mark.unit
    def test_case_insensitive_fuzzy_matching(self):
        """Test that fuzzy matching is case-insensitive."""
        # Lowercase headers should match fuzzy options
        columns = ['donor_name', 'email_address', 'donation_date']
        mapping = build_header_mapping(columns)

        # Should match despite case differences
        assert mapping['name'] == 'donor_name'
        assert mapping['email'] == 'email_address'
        assert mapping['date'] == 'donation_date'

    @pytest.mark.unit
    def test_core_headers_case_sensitive_match(self):
        """Test that core headers still require exact case match."""
        # Core headers require exact case match (not fuzzy fallback)
        columns = ['transaction id', 'name', 'email']  # all lowercase
        mapping = build_header_mapping(columns)

        # Should not match core headers (exact case required)
        assert 'transaction_id' not in mapping
        assert 'name' not in mapping
        assert 'email' not in mapping

    @pytest.mark.unit
    def test_payment_method_variations(self):
        """Test payment method column name variations."""
        # Test 'Payment Type'
        columns = ['Name', 'Payment Type']
        mapping = build_header_mapping(columns)
        assert mapping['payment_method'] == 'Payment Type'

        # Test 'Method'
        columns = ['Name', 'Method']
        mapping = build_header_mapping(columns)
        assert mapping['payment_method'] == 'Method'
