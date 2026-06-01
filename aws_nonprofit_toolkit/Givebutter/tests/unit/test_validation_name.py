"""Unit tests for name validation."""
import pytest
from processor import validate_name


class TestNameValidation:
    """Test name validation function."""

    @pytest.mark.unit
    def test_valid_name(self):
        """Test valid name passes."""
        record = {'Name': 'John Smith'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'
        assert reason is None

    @pytest.mark.unit
    def test_valid_single_character_name_with_minimum(self):
        """Test name with exactly minimum length."""
        record = {'Name': 'Jo'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_valid_maximum_length_name(self):
        """Test name at maximum length."""
        record = {'Name': 'A' * 100}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_name_too_short(self):
        """Test name shorter than minimum length."""
        record = {'Name': 'J'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'too short' in reason.lower()

    @pytest.mark.unit
    def test_name_too_long(self):
        """Test name longer than maximum length."""
        record = {'Name': 'A' * 101}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'too long' in reason.lower()

    @pytest.mark.unit
    def test_empty_name(self):
        """Test empty name field."""
        record = {'Name': ''}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_name_with_whitespace_only(self):
        """Test name with only whitespace."""
        record = {'Name': '   '}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_missing_name_column(self):
        """Test missing name column."""
        record = {'Email': 'test@gmail.com'}
        header_map = {}  # No name mapping
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'not found' in reason.lower()

    @pytest.mark.unit
    def test_name_with_special_characters(self):
        """Test name with special characters."""
        record = {'Name': "O'Brien-Smith"}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_name_with_unicode_characters(self):
        """Test name with unicode/international characters."""
        record = {'Name': 'José García'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_name_with_chinese_characters(self):
        """Test name with Chinese characters."""
        record = {'Name': '王小明'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_name_with_extra_whitespace(self):
        """Test name with leading/trailing whitespace."""
        record = {'Name': '  John Smith  '}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_business_name(self):
        """Test business name."""
        record = {'Name': 'Acme Corporation, Inc.'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_name_with_numbers(self):
        """Test name with numbers."""
        record = {'Name': 'John 3rd Smith'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_custom_min_length(self):
        """Test custom minimum length requirement."""
        record = {'Name': 'A'}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 5, 'max_length': 100}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'too short' in reason.lower()

    @pytest.mark.unit
    def test_custom_max_length(self):
        """Test custom maximum length requirement."""
        record = {'Name': 'A' * 51}
        header_map = {'name': 'Name'}
        reference = {'name_patterns': {'min_length': 2, 'max_length': 50}}

        tier, reason = validate_name(record, header_map, reference)
        assert tier == 'FAIL'
        assert 'too long' in reason.lower()
