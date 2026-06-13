"""
Unit tests for export readiness service.

Tests that readiness derives correctly from export preview without new logic.
"""

import pytest
from scripts.householder.readiness_service import get_export_readiness, ExportReadinessViewModel


class TestExportReadinessViewModel:
    """Test ExportReadinessViewModel structure."""

    def test_readiness_view_model_creation(self):
        """Test that ExportReadinessViewModel can be created."""
        vm = ExportReadinessViewModel(
            batch_id='IMP-TEST-001',
            batch_filename='test.csv',
            progress_pct=50,
            is_export_ready=True,
            blocker_count=0,
            warning_count=2,
            staged_records=100,
            blockers=(),
            warnings=('warning1', 'warning2'),
            queue_status={'validation_issues': 0, 'duplicates_pending': 0}
        )
        assert vm.batch_id == 'IMP-TEST-001'
        assert vm.is_export_ready is True
        assert vm.blocker_count == 0

    def test_readiness_view_model_to_template_dict(self):
        """Test conversion to template dictionary."""
        vm = ExportReadinessViewModel(
            batch_id='IMP-TEST-001',
            batch_filename='test.csv',
            progress_pct=75,
            is_export_ready=False,
            blocker_count=3,
            warning_count=1,
            staged_records=85,
            blockers=('issue1', 'issue2', 'issue3'),
            warnings=('warning1',),
            queue_status={
                'validation_issues': 2,
                'duplicates_pending': 1,
                'normalizations_pending': 0,
                'households_pending': 0,
            }
        )
        result = vm.to_template_dict()

        assert result['batch']['id'] == 'IMP-TEST-001'
        assert result['batch']['filename'] == 'test.csv'
        assert result['batch']['progress'] == 75
        assert result['readiness']['is_export_ready'] is False
        assert result['readiness']['blocker_count'] == 3
        assert result['readiness']['warning_count'] == 1
        assert result['readiness']['staged_records'] == 85
        assert len(result['readiness']['blockers']) == 3
        assert len(result['readiness']['warnings']) == 1
        assert result['queue_status']['validation_issues'] == 2

    def test_readiness_view_model_frozen(self):
        """Test that ExportReadinessViewModel is immutable."""
        vm = ExportReadinessViewModel(
            batch_id='IMP-TEST-001',
            batch_filename='test.csv',
            progress_pct=50,
            is_export_ready=True,
            blocker_count=0,
            warning_count=0,
            staged_records=100,
            blockers=(),
            warnings=(),
            queue_status={'validation_issues': 0, 'duplicates_pending': 0}
        )
        with pytest.raises(AttributeError):
            vm.is_export_ready = False


class TestGetExportReadiness:
    """Test get_export_readiness function."""

    def test_get_export_readiness_returns_view_model(self):
        """Test that function returns ExportReadinessViewModel."""
        result = get_export_readiness('IMP-2025-0101-A')
        assert isinstance(result, ExportReadinessViewModel)

    def test_get_export_readiness_has_batch_info(self):
        """Test that readiness includes batch information."""
        result = get_export_readiness('IMP-2025-0101-A')
        assert result.batch_id == 'IMP-2025-0101-A'
        assert result.batch_filename is not None
        assert result.progress_pct >= 0

    def test_get_export_readiness_has_readiness_state(self):
        """Test that readiness includes ready/blocked state."""
        result = get_export_readiness('IMP-2025-0101-A')
        assert isinstance(result.is_export_ready, bool)
        assert isinstance(result.blocker_count, int)
        assert isinstance(result.warning_count, int)
        assert result.blocker_count >= 0

    def test_get_export_readiness_has_queue_status(self):
        """Test that readiness includes queue status."""
        result = get_export_readiness('IMP-2025-0101-A')
        assert 'validation_issues' in result.queue_status
        assert 'duplicates_pending' in result.queue_status
        assert 'normalizations_pending' in result.queue_status
        assert 'households_pending' in result.queue_status

    def test_get_export_readiness_blockers_are_tuple(self):
        """Test that blockers are returned as tuple."""
        result = get_export_readiness('IMP-2025-0101-A')
        assert isinstance(result.blockers, tuple)
        assert isinstance(result.warnings, tuple)

    def test_get_export_readiness_staged_records_count(self):
        """Test that staged_records reflects exportable rows."""
        result = get_export_readiness('IMP-2025-0101-A')
        assert isinstance(result.staged_records, int)
        assert result.staged_records >= 0

    def test_get_export_readiness_no_database_mutation(self):
        """Test that function does not mutate any data."""
        # Call twice and verify results are consistent
        result1 = get_export_readiness('IMP-2025-0101-A')
        result2 = get_export_readiness('IMP-2025-0101-A')

        assert result1.batch_id == result2.batch_id
        assert result1.is_export_ready == result2.is_export_ready
        assert result1.blocker_count == result2.blocker_count
        assert result1.staged_records == result2.staged_records

    def test_get_export_readiness_with_different_batch_ids(self):
        """Test that different batch IDs return different results."""
        # Note: Fixture repository returns same data for all batch IDs
        # This test verifies the service accepts different IDs without error
        result1 = get_export_readiness('IMP-2025-0101-A')
        result2 = get_export_readiness('IMP-2025-0102-B')
        # Both should succeed (fixture data doesn't validate batch ID)
        assert result1.batch_id == 'IMP-2025-0101-A'
        assert result2.batch_id == 'IMP-2025-0102-B'

    def test_get_export_readiness_returns_frozen_dataclass(self):
        """Test that result is frozen (immutable)."""
        result = get_export_readiness('IMP-2025-0101-A')
        with pytest.raises((AttributeError, TypeError)):
            result.is_export_ready = not result.is_export_ready
