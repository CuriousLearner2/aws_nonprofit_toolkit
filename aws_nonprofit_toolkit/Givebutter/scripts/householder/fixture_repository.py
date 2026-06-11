"""
Fixture Repository - Serves Phase 0 fixture data through service interface.

This adapter allows screens to be backed by fixtures during Phase 1A while
maintaining the service boundary. Later, this can be swapped for SQLiteRepository
or other implementations without changing routes or templates.

Does not mutate fixtures. Provides read-only access only.
"""

from typing import List
from datetime import datetime

try:
    from scripts.uploader.fixtures import IMPORTS_LIST, IMPORT_BATCH, QUEUE_STATUS
except ImportError:
    # Fallback for direct script execution
    from uploader.fixtures import IMPORTS_LIST, IMPORT_BATCH, QUEUE_STATUS

from .service_contracts import ImportSummary, DashboardQueueCard, ImportDashboardViewModel


class FixtureImportRepository:
    """
    Provides fixture import data through service interface.

    This repository adapts Phase 0 fixture data into service-contract
    view models. It can be swapped for other implementations (e.g.,
    SQLiteRepository) without changing routes or templates.
    """

    @staticmethod
    def list_imports() -> List[ImportSummary]:
        """
        Return list of all imports as ImportSummary view models.

        Returns:
            List of ImportSummary objects ready for template rendering.
            Data is shaped to match what /imports template expects.
        """
        summaries = []

        for import_item in IMPORTS_LIST:
            # Format timestamp as relative time string
            uploaded_str = None
            if 'uploaded_at' in import_item:
                dt_value = import_item['uploaded_at']
                if isinstance(dt_value, datetime):
                    uploaded_str = FixtureImportRepository._format_relative_time(dt_value)
                else:
                    uploaded_str = str(dt_value)

            summary = ImportSummary(
                id=import_item['id'],
                filename=import_item['filename'],
                record_count=import_item['record_count'],
                status=import_item['status'],
                progress=import_item['progress'],
                uploaded_timestamp=uploaded_str,
            )
            summaries.append(summary)

        return summaries

    @staticmethod
    def get_dashboard(import_id: str) -> ImportDashboardViewModel:
        """
        Return import dashboard data as ImportDashboardViewModel.

        Adapts IMPORT_BATCH and QUEUE_STATUS fixtures into dashboard
        view model. Returns data ready for template rendering.

        Args:
            import_id: Import ID (unused for fixture data, preserved for API consistency)

        Returns:
            ImportDashboardViewModel with batch and queue status.
        """
        # Build queue cards in order: Duplicates, Validation, Normalizations, Households
        queue_cards = (
            DashboardQueueCard(
                name="Possible Duplicates",
                description="Side-by-side comparison: mark records as the same person",
                pending_count=QUEUE_STATUS.get('duplicates_pending', 0),
                badge_color="badge-amber",
                action_label="Review Duplicates",
                action_url=f"/imports/{IMPORT_BATCH['id']}/duplicates",
            ),
            DashboardQueueCard(
                name="Validation Review",
                description="Inspect all records, identify validation issues",
                pending_count=QUEUE_STATUS.get('validation_issues', 0),
                badge_color="badge-red",
                action_label="Review Records",
                action_url=f"/imports/{IMPORT_BATCH['id']}/validation",
            ),
            DashboardQueueCard(
                name="Normalizations",
                description="Review field cleanup suggestions",
                pending_count=QUEUE_STATUS.get('normalizations_pending', 0),
                badge_color="badge-blue",
                action_label="Review Normalizations",
                action_url=f"/imports/{IMPORT_BATCH['id']}/normalizations",
            ),
            DashboardQueueCard(
                name="Households",
                description="Confirm/defer household groupings",
                pending_count=QUEUE_STATUS.get('households_pending', 0),
                badge_color="badge-green",
                action_label="Review Households",
                action_url=f"/imports/{IMPORT_BATCH['id']}/households",
            ),
        )

        return ImportDashboardViewModel(
            batch_id=IMPORT_BATCH['id'],
            filename=IMPORT_BATCH['filename'],
            progress=IMPORT_BATCH['progress'],
            queues=queue_cards,
            audit_log_url=f"/imports/{IMPORT_BATCH['id']}/audit",
            export_console_url=f"/imports/{IMPORT_BATCH['id']}/exports",
            back_to_imports_url="/imports",
        )

    @staticmethod
    def _format_relative_time(dt: datetime) -> str:
        """
        Format datetime as relative time string (e.g., '2h ago').

        Consistent with existing app.py format_relative_time utility.
        """
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f'{minutes}m ago'
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f'{hours}h ago'
        else:
            days = int(seconds // 86400)
            return f'{days}d ago'
