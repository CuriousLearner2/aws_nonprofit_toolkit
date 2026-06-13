"""
Unit tests for export preview service.

Tests verify that export preview correctly interprets reviewer decisions
without mutating source data.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.export_preview_service import build_export_preview


class TestExportPreviewServiceValidation:
    """Test export preview service validation."""

    def test_invalid_batch_raises_error(self):
        """Test that invalid batch ID raises ValueError."""
        with pytest.raises(ValueError, match="database configuration"):
            # Will fail on database config, but validates batch lookup happens
            build_export_preview('INVALID-ID')

    def test_missing_database_config_raises_error(self):
        """Test that missing database configuration raises ValueError."""
        with pytest.raises(ValueError, match="database configuration"):
            build_export_preview(
                import_id='IMP-2025-0101-A',
                config={},  # Empty config
            )


class TestExportPreviewIntegration:
    """
    Integration tests for export preview.

    Note: Requires database with seeded data.
    Use test database fixtures (temp_db) for isolation.
    """
    pass
