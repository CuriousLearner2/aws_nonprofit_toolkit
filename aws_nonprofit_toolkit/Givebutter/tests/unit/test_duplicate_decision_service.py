"""
Unit tests for duplicate decision service layer.

Tests service-level validation: decision values, config requirements, optional parameters.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.duplicate_decision_service import record_duplicate_decision


class TestDuplicateDecisionServiceValidation:
    """Test service layer validation for duplicate decisions."""

    def test_valid_same_person_decision(self):
        """Test that valid 'same_person' decision is accepted."""
        with pytest.raises(ValueError, match="database configuration"):
            # Will fail on database config check, but passes decision validation
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='same_person',
            )

    def test_valid_different_people_decision(self):
        """Test that valid 'different_people' decision is accepted."""
        with pytest.raises(ValueError, match="database configuration"):
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='different_people',
            )

    def test_valid_defer_decision(self):
        """Test that valid 'defer' decision is accepted."""
        with pytest.raises(ValueError, match="database configuration"):
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='defer',
            )

    def test_invalid_decision_rejected(self):
        """Test that invalid decision is rejected."""
        with pytest.raises(ValueError, match="Invalid decision"):
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='invalid_decision',
            )

    def test_empty_decision_rejected(self):
        """Test that empty decision is rejected."""
        with pytest.raises(ValueError, match="Invalid decision"):
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='',
            )

    def test_validation_decision_values_rejected(self):
        """Test that validation decision values are rejected."""
        for decision in ['accept_issue', 'dismiss_issue']:
            with pytest.raises(ValueError, match="Invalid decision"):
                record_duplicate_decision(
                    import_id='IMP-2025-0101-A',
                    review_item_id=1,
                    decision=decision,
                )

    def test_normalization_decision_values_rejected(self):
        """Test that normalization decision values are rejected."""
        for decision in ['accept_normalization', 'reject_normalization']:
            with pytest.raises(ValueError, match="Invalid decision"):
                record_duplicate_decision(
                    import_id='IMP-2025-0101-A',
                    review_item_id=1,
                    decision=decision,
                )

    def test_missing_database_config_rejected(self):
        """Test that missing database config is rejected."""
        with pytest.raises(ValueError, match="database configuration"):
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='same_person',
                config={},  # Empty config
            )

    def test_notes_optional(self):
        """Test that notes parameter is optional."""
        with pytest.raises(ValueError, match="database configuration"):
            # Decision validation passes with or without notes
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='same_person',
                notes=None,
            )

    def test_reviewer_optional(self):
        """Test that reviewer parameter is optional."""
        with pytest.raises(ValueError, match="database configuration"):
            # Decision validation passes with or without reviewer
            record_duplicate_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='defer',
                reviewer=None,
            )
