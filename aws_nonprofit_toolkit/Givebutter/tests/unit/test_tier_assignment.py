"""Unit tests for tier assignment logic."""
import pytest
from processor import assign_tier


class TestTierAssignment:
    """Test tier assignment function."""

    @pytest.mark.unit
    def test_all_pass_results(self):
        """Test tier assignment when all validations pass."""
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None},
            'phone': {'tier': 'PASS', 'reason': None},
            'amount': {'tier': 'PASS', 'reason': None},
            'address': {'tier': 'PASS', 'reason': None},
            'name': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_single_fail_overrides_pass(self):
        """Test that single FAIL overrides all PASS results."""
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None},
            'phone': {'tier': 'FAIL', 'reason': 'Phone too short'},
            'amount': {'tier': 'PASS', 'reason': None},
            'address': {'tier': 'PASS', 'reason': None},
            'name': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'FAIL'

    @pytest.mark.unit
    def test_multiple_fails(self):
        """Test tier assignment with multiple FAILs."""
        validation_results = {
            'email': {'tier': 'FAIL', 'reason': 'Invalid format'},
            'phone': {'tier': 'FAIL', 'reason': 'Phone too short'},
            'amount': {'tier': 'PASS', 'reason': None},
            'name': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'FAIL'

    @pytest.mark.unit
    def test_fail_overrides_warning_and_pass(self):
        """Test that FAIL overrides WARNING and PASS."""
        validation_results = {
            'email': {'tier': 'WARNING', 'reason': 'Email typo'},
            'phone': {'tier': 'FAIL', 'reason': 'Phone too short'},
            'amount': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'FAIL'

    @pytest.mark.unit
    def test_warning_with_pass(self):
        """Test WARNING without FAIL."""
        validation_results = {
            'email': {'tier': 'WARNING', 'reason': 'Email typo detected'},
            'phone': {'tier': 'PASS', 'reason': None},
            'amount': {'tier': 'PASS', 'reason': None},
            'address': {'tier': 'PASS', 'reason': None},
            'name': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'WARNING'

    @pytest.mark.unit
    def test_multiple_warnings_with_pass(self):
        """Test multiple WARNINGs with PASS."""
        validation_results = {
            'email': {'tier': 'WARNING', 'reason': 'Email typo'},
            'phone': {'tier': 'WARNING', 'reason': 'Unusual format'},
            'amount': {'tier': 'PASS', 'reason': None},
            'address': {'tier': 'WARNING', 'reason': 'Incomplete address'},
            'name': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'WARNING'

    @pytest.mark.unit
    def test_single_warning_with_multiple_pass(self):
        """Test single WARNING among multiple PASS results."""
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None},
            'phone': {'tier': 'PASS', 'reason': None},
            'amount': {'tier': 'WARNING', 'reason': 'High-dollar donation'},
            'address': {'tier': 'PASS', 'reason': None},
            'name': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'WARNING'

    @pytest.mark.unit
    def test_empty_validation_results(self):
        """Test with empty validation results."""
        validation_results = {}

        tier = assign_tier(validation_results)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_single_validation_result_pass(self):
        """Test with single validation result as PASS."""
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None}
        }

        tier = assign_tier(validation_results)
        assert tier == 'PASS'

    @pytest.mark.unit
    def test_single_validation_result_fail(self):
        """Test with single validation result as FAIL."""
        validation_results = {
            'email': {'tier': 'FAIL', 'reason': 'Invalid format'}
        }

        tier = assign_tier(validation_results)
        assert tier == 'FAIL'

    @pytest.mark.unit
    def test_single_validation_result_warning(self):
        """Test with single validation result as WARNING."""
        validation_results = {
            'email': {'tier': 'WARNING', 'reason': 'Email typo'}
        }

        tier = assign_tier(validation_results)
        assert tier == 'WARNING'

    @pytest.mark.unit
    def test_with_duplicate_check(self):
        """Test tier assignment with duplicate check field."""
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None},
            'phone': {'tier': 'PASS', 'reason': None},
            'amount': {'tier': 'PASS', 'reason': None},
            'name': {'tier': 'PASS', 'reason': None},
            'duplicate': {'tier': 'WARNING', 'reason': 'Duplicate record found'}
        }

        tier = assign_tier(validation_results)
        assert tier == 'WARNING'

    @pytest.mark.unit
    def test_duplicate_with_fail(self):
        """Test duplicate warning combined with other failures."""
        validation_results = {
            'email': {'tier': 'FAIL', 'reason': 'Invalid format'},
            'phone': {'tier': 'PASS', 'reason': None},
            'duplicate': {'tier': 'WARNING', 'reason': 'Duplicate found'}
        }

        tier = assign_tier(validation_results)
        assert tier == 'FAIL'

    @pytest.mark.unit
    def test_all_warning_no_fail(self):
        """Test all WARNING results with no FAIL."""
        validation_results = {
            'email': {'tier': 'WARNING', 'reason': 'Typo'},
            'phone': {'tier': 'WARNING', 'reason': 'Format'},
            'amount': {'tier': 'WARNING', 'reason': 'High dollar'},
            'address': {'tier': 'WARNING', 'reason': 'Incomplete'},
            'name': {'tier': 'WARNING', 'reason': 'Length'}
        }

        tier = assign_tier(validation_results)
        assert tier == 'WARNING'

    @pytest.mark.unit
    def test_fail_in_any_position(self):
        """Test that FAIL is detected regardless of field position."""
        # Fail in middle
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None},
            'phone': {'tier': 'FAIL', 'reason': 'Too short'},
            'amount': {'tier': 'PASS', 'reason': None}
        }
        assert assign_tier(validation_results) == 'FAIL'

        # Fail at beginning
        validation_results = {
            'email': {'tier': 'FAIL', 'reason': 'Invalid'},
            'phone': {'tier': 'PASS', 'reason': None},
            'amount': {'tier': 'PASS', 'reason': None}
        }
        assert assign_tier(validation_results) == 'FAIL'

        # Fail at end
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None},
            'phone': {'tier': 'PASS', 'reason': None},
            'amount': {'tier': 'FAIL', 'reason': 'Invalid'}
        }
        assert assign_tier(validation_results) == 'FAIL'

    @pytest.mark.unit
    def test_warning_in_any_position(self):
        """Test that WARNING is detected regardless of field position."""
        # Warning in middle (no fails)
        validation_results = {
            'email': {'tier': 'PASS', 'reason': None},
            'phone': {'tier': 'WARNING', 'reason': 'Format'},
            'amount': {'tier': 'PASS', 'reason': None}
        }
        assert assign_tier(validation_results) == 'WARNING'

        # Warning at beginning (no fails)
        validation_results = {
            'email': {'tier': 'WARNING', 'reason': 'Typo'},
            'phone': {'tier': 'PASS', 'reason': None},
            'amount': {'tier': 'PASS', 'reason': None}
        }
        assert assign_tier(validation_results) == 'WARNING'
