"""Unit tests for email validation."""
import pytest
from processor import validate_email


class TestEmailValidation:
    """Test email validation function."""

    @pytest.mark.unit
    def test_valid_email(self):
        """Test valid email passes."""
        record = {'Email': 'john@gmail.com'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': ['gmail.com'], 'email_tlds': ['com']}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'PASS'
        assert reason is None
        assert suggestion is None

    @pytest.mark.unit
    def test_email_typo_detected(self):
        """Test email typo is detected and suggested fix provided."""
        record = {'Email': 'john@gmai.com'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': [{'from': 'gmai.com', 'to': 'gmail.com'}]}
        reference = {'email_domains': ['gmail.com'], 'email_tlds': ['com']}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'WARNING'
        assert reason == 'Email typo detected'
        assert 'gmail.com' in suggestion

    @pytest.mark.unit
    def test_multiple_email_typos(self):
        """Test multiple email typo patterns."""
        typos = [
            ('gmai.com', 'gmail.com'),
            ('gmal.com', 'gmail.com'),
            ('yaho.com', 'yahoo.com'),
        ]

        for typo_from, typo_to in typos:
            record = {'Email': f'user@{typo_from}'}
            header_map = {'email': 'Email'}
            rules = {'email_typos': [{'from': typo_from, 'to': typo_to}]}
            reference = {'email_domains': [typo_to], 'email_tlds': ['com']}

            tier, reason, suggestion = validate_email(record, header_map, rules, reference)
            assert tier == 'WARNING'
            assert typo_to in suggestion

    @pytest.mark.unit
    def test_invalid_email_format(self):
        """Test email without @ symbol is invalid."""
        record = {'Email': 'invalidemail.com'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'FAIL'
        assert 'missing @' in reason.lower()

    @pytest.mark.unit
    def test_empty_email(self):
        """Test empty email is treated as optional."""
        record = {'Email': ''}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_missing_email_column(self):
        """Test missing email column."""
        record = {'Email': 'test@gmail.com'}
        header_map = {}  # No email mapping
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_email_case_insensitive(self):
        """Test email comparison is case insensitive."""
        record = {'Email': 'John@GMAIL.COM'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': ['gmail.com'], 'email_tlds': ['com']}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'PASS'
