"""
Unit tests for household decision service layer.

Tests service-level validation: decision values, config requirements, optional parameters.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.household_decision_service import record_household_decision


class TestHouseholdDecisionServiceValidation:
    """Test service layer validation for household decisions."""

    def test_valid_confirm_household_decision(self):
        """Test that valid 'confirm_household' decision is accepted."""
        with pytest.raises(ValueError, match="database configuration"):
            # Will fail on database config check, but passes decision validation
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='confirm_household',
            )

    def test_valid_reject_household_decision(self):
        """Test that valid 'reject_household' decision is accepted."""
        with pytest.raises(ValueError, match="database configuration"):
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='reject_household',
            )

    def test_valid_defer_decision(self):
        """Test that valid 'defer' decision is accepted."""
        with pytest.raises(ValueError, match="database configuration"):
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='defer',
            )

    def test_invalid_decision_rejected(self):
        """Test that invalid decision is rejected."""
        with pytest.raises(ValueError, match="Invalid decision"):
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='invalid_decision',
            )

    def test_empty_decision_rejected(self):
        """Test that empty decision is rejected."""
        with pytest.raises(ValueError, match="Invalid decision"):
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='',
            )

    def test_validation_decision_values_rejected(self):
        """Test that validation decision values are rejected."""
        for decision in ['accept_issue', 'dismiss_issue']:
            with pytest.raises(ValueError, match="Invalid decision"):
                record_household_decision(
                    import_id='IMP-2025-0101-A',
                    review_item_id=1,
                    decision=decision,
                )

    def test_normalization_decision_values_rejected(self):
        """Test that normalization decision values are rejected."""
        for decision in ['accept_normalization', 'reject_normalization']:
            with pytest.raises(ValueError, match="Invalid decision"):
                record_household_decision(
                    import_id='IMP-2025-0101-A',
                    review_item_id=1,
                    decision=decision,
                )

    def test_duplicate_decision_values_rejected(self):
        """Test that duplicate decision values are rejected."""
        for decision in ['same_person', 'different_people']:
            with pytest.raises(ValueError, match="Invalid decision"):
                record_household_decision(
                    import_id='IMP-2025-0101-A',
                    review_item_id=1,
                    decision=decision,
                )

    def test_missing_database_config_rejected(self):
        """Test that missing database config is rejected."""
        with pytest.raises(ValueError, match="database configuration"):
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='confirm_household',
                config={},  # Empty config
            )

    def test_notes_optional(self):
        """Test that notes parameter is optional."""
        with pytest.raises(ValueError, match="database configuration"):
            # Decision validation passes with or without notes
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='confirm_household',
                notes=None,
            )

    def test_reviewer_optional(self):
        """Test that reviewer parameter is optional."""
        with pytest.raises(ValueError, match="database configuration"):
            # Decision validation passes with or without reviewer
            record_household_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='reject_household',
                reviewer=None,
            )
