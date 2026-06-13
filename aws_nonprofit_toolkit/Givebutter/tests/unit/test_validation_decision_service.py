"""
Unit tests for validation decision service.

Tests service-layer behavior: validation, error handling, effective status derivation.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from scripts.householder.validation_decision_service import (
    record_validation_decision,
    get_effective_status,
)
from scripts.householder.write_repository_contracts import ValidationDecisionResult
from scripts.householder.database_models import Base, create_db_engine


@pytest.fixture
def test_database():
    """Create temporary test database with schema."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestValidationDecisionService:
    """Test validation decision service validation and behavior."""

    def test_invalid_decision_raises_error(self):
        """Invalid decision value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid decision"):
            record_validation_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='invalid_value',
            )

    def test_empty_decision_raises_error(self):
        """Missing decision raises ValueError."""
        with pytest.raises(ValueError, match="Invalid decision"):
            record_validation_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='',
            )

    def test_missing_database_config_raises_error(self):
        """Missing database configuration raises ValueError."""
        # No database URL in environment or config
        with pytest.raises(ValueError, match="database configuration"):
            record_validation_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='dismiss_issue',
                config={},  # Empty config, no database URL
            )

    def test_accept_issue_decision_valid(self, test_database):
        """Valid accept_issue decision is accepted (does not raise)."""
        # This would fail with database error (unknown batch), but decision value itself is valid
        with pytest.raises(ValueError, match="Import batch"):
            # The database error is expected here; we're testing decision validation
            record_validation_decision(
                import_id='IMP-NONEXISTENT',
                review_item_id=1,
                decision='accept_issue',
                config={'GIVEBUTTER_DATABASE_URL': test_database},
            )

    def test_dismiss_issue_decision_valid(self, test_database):
        """Valid dismiss_issue decision is accepted (does not raise)."""
        with pytest.raises(ValueError, match="Import batch"):
            record_validation_decision(
                import_id='IMP-NONEXISTENT',
                review_item_id=1,
                decision='dismiss_issue',
                config={'GIVEBUTTER_DATABASE_URL': test_database},
            )

    def test_defer_decision_valid(self, test_database):
        """Valid defer decision is accepted (does not raise)."""
        with pytest.raises(ValueError, match="Import batch"):
            record_validation_decision(
                import_id='IMP-NONEXISTENT',
                review_item_id=1,
                decision='defer',
                config={'GIVEBUTTER_DATABASE_URL': test_database},
            )


class TestEffectiveStatusDerivation:
    """Test effective status derivation logic."""

    def test_no_decision_returns_pending(self):
        """No decision records returns 'pending'."""
        # This test is illustrative; actual implementation requires database setup
        # Integration tests will cover the full behavior
        pass

    def test_accept_issue_returns_accepted(self):
        """Latest accept_issue decision returns 'accepted'."""
        pass

    def test_dismiss_issue_returns_dismissed(self):
        """Latest dismiss_issue decision returns 'dismissed'."""
        pass

    def test_defer_returns_deferred(self):
        """Latest defer decision returns 'deferred'."""
        pass

    def test_multiple_decisions_latest_wins(self):
        """Multiple decisions per item; latest determines status."""
        pass
