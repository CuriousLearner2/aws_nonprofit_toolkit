"""
Unit tests for normalization decision service.

Tests service layer validation and error handling for normalization decisions.
"""

import pytest
from scripts.householder.normalization_decision_service import record_normalization_decision


class TestNormalizationDecisionServiceValidation:
    """Test normalization decision service validation logic."""

    def test_valid_accept_normalization_decision(self):
        """Valid accept_normalization decision passes validation."""
        # This would fail with database error (no config), but validation passes
        try:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='accept_normalization',
                notes='Confirms typo fix',
                config={}
            )
        except ValueError as e:
            # Should be database error, not validation error
            assert 'Invalid decision' not in str(e)
        except Exception:
            # Expected: database configuration error or database error
            pass

    def test_valid_reject_normalization_decision(self):
        """Valid reject_normalization decision passes validation."""
        try:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='reject_normalization',
                notes='Original is correct',
                config={}
            )
        except ValueError as e:
            # Should be database error, not validation error
            assert 'Invalid decision' not in str(e)
        except Exception:
            # Expected: database configuration error or database error
            pass

    def test_valid_defer_decision(self):
        """Valid defer decision passes validation."""
        try:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='defer',
                notes='Need more context',
                config={}
            )
        except ValueError as e:
            # Should be database error, not validation error
            assert 'Invalid decision' not in str(e)
        except Exception:
            # Expected: database configuration error or database error
            pass

    def test_invalid_decision_value_raises_error(self):
        """Invalid decision value raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='invalid_decision',
                config={}
            )
        assert 'Invalid decision' in str(exc_info.value)
        assert 'accept_normalization' in str(exc_info.value)
        assert 'reject_normalization' in str(exc_info.value)

    def test_empty_decision_raises_error(self):
        """Empty decision string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='',
                config={}
            )
        assert 'Invalid decision' in str(exc_info.value)

    def test_validation_decision_not_accepted(self):
        """Validation decision types not accepted for normalization."""
        with pytest.raises(ValueError) as exc_info:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='accept_issue',  # validation decision, not normalization
                config={}
            )
        assert 'Invalid decision' in str(exc_info.value)

    def test_missing_database_config_raises_error(self):
        """Missing database config raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='accept_normalization',
                config=None  # No config, no env var
            )
        assert 'database configuration' in str(exc_info.value).lower()

    def test_notes_optional(self):
        """Notes parameter is optional."""
        try:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='accept_normalization',
                notes=None,  # No notes
                config={}
            )
        except ValueError as e:
            # Should be database error, not validation error
            assert 'Invalid decision' not in str(e)
        except Exception:
            # Expected: database error
            pass

    def test_reviewer_optional(self):
        """Reviewer parameter is optional."""
        try:
            record_normalization_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='accept_normalization',
                reviewer=None,  # No reviewer
                config={}
            )
        except ValueError as e:
            # Should be database error, not validation error
            assert 'Invalid decision' not in str(e)
        except Exception:
            # Expected: database error
            pass
