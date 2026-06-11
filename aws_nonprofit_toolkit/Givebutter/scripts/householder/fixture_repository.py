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
    from scripts.uploader.fixtures import IMPORTS_LIST
except ImportError:
    # Fallback for direct script execution
    from uploader.fixtures import IMPORTS_LIST

from .service_contracts import ImportSummary


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
