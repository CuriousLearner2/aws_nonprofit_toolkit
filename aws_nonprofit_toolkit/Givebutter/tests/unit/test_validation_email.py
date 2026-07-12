"""Unit tests for email validation."""

import pytest

from processor import validate_email
from scripts.householder.email_validation_service import (
    EMAIL_FORMAT_ERROR,
    EMAIL_REQUIRED_ERROR,
    validate_review_email,
)


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
    def test_empty_email_fails(self):
        """Test empty email field fails validation (required field)."""
        record = {'Email': ''}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'FAIL'
        assert 'empty' in reason.lower()

    @pytest.mark.unit
    def test_missing_email_column_fails(self):
        """Test missing email column fails validation (required field)."""
        record = {'Email': 'test@gmail.com'}
        header_map = {}  # No email mapping
        rules = {'email_typos': []}
        reference = {'email_domains': [], 'email_tlds': []}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'FAIL'
        assert 'column not found' in reason.lower()

    @pytest.mark.unit
    def test_email_case_insensitive(self):
        """Test email comparison is case insensitive."""
        record = {'Email': 'John@GMAIL.COM'}
        header_map = {'email': 'Email'}
        rules = {'email_typos': []}
        reference = {'email_domains': ['gmail.com'], 'email_tlds': ['com']}

        tier, reason, suggestion = validate_email(record, header_map, rules, reference)
        assert tier == 'PASS'


class TestCanonicalEmailValidationService:
    """Test the canonical review-time email validator."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "USER@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@example.co.uk",
            "user@localhost",
            "user@例え.テスト",
            "δοκιμή@παράδειγμα.δοκιμή",
        ],
    )
    def test_validate_review_email_accepts_common_valid_addresses(self, email):
        result = validate_review_email(email)
        assert result.valid is True
        assert result.blocking_error is None
        assert result.normalized_value == email.strip()

    @pytest.mark.parametrize(
        "email",
        [
            "user",
            "@example.com",
            "user@",
            "user@example",
            "user@internal",
            "user example@example.com",
            "user..name@example.com",
            "Jane Doe <jane@example.com>",
            '"user"@example.com',
            "user@[127.0.0.1]",
            "user@example.",
            "user@example..com",
        ],
    )
    def test_validate_review_email_rejects_malformed_addresses(self, email):
        result = validate_review_email(email)
        assert result.valid is False
        assert result.blocking_error in {EMAIL_FORMAT_ERROR, "Invalid email format (missing @)"}

    @pytest.mark.parametrize(
        "email",
        ["", "   ", None],
    )
    def test_validate_review_email_rejects_blank_values(self, email):
        result = validate_review_email(email)
        assert result.valid is False
        assert result.blocking_error == EMAIL_REQUIRED_ERROR

    def test_validate_review_email_can_allow_blank(self):
        result = validate_review_email("   ", allow_blank=True)
        assert result.valid is True
        assert result.normalized_value == ""

    def test_validate_review_email_preserves_trimmed_input(self):
        result = validate_review_email("  User+Tag@Example.COM  ")
        assert result.valid is True
        assert result.normalized_value == "User+Tag@Example.COM"

    @pytest.mark.parametrize(
        "email",
        [
            "user..name@localhost",
            '"john"@localhost',
            ("a" * 65) + "@localhost",
        ],
    )
    def test_validate_review_email_rejects_malformed_localhost_addresses(self, email):
        result = validate_review_email(email)
        assert result.valid is False
        assert result.blocking_error == EMAIL_FORMAT_ERROR

    @pytest.mark.parametrize(
        "email",
        [
            ("a" * 65) + "@example.com",
            "user@" + ("a" * 246) + ".com",
        ],
    )
    def test_validate_review_email_rejects_oversized_addresses(self, email):
        result = validate_review_email(email)
        assert result.valid is False
        assert result.blocking_error == EMAIL_FORMAT_ERROR

    @pytest.mark.parametrize(
        "email, warning_fragment",
        [
            ("user@gmai.com", "gmail.com"),
            ("user@gamil.com", "gmail.com"),
            ("user@yaho.com", "yahoo.com"),
        ],
    )
    def test_validate_review_email_warns_on_common_typos(self, email, warning_fragment):
        result = validate_review_email(email)
        assert result.valid is True
        assert result.warnings
        assert warning_fragment in result.warnings[0]
