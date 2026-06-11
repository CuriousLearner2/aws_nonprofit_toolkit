"""
Service Contracts - Data models for DonorTrust v1 screens.

View models define the shape of data that each Jinja template needs.
Templates receive plain dataclasses, not ORM objects.
Service layer hides whether data comes from fixtures, database, or API.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ImportSummary:
    """
    Single import summary for /imports list view.

    Frozen dataclass ensures immutability. Adapts fixture data
    into a clean contract that templates and services depend on.
    """
    id: str
    filename: str
    record_count: int
    status: str
    progress: int
    uploaded_timestamp: Optional[str] = None

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "filename": self.filename,
            "record_count": self.record_count,
            "status": self.status,
            "progress": self.progress,
            "uploaded_timestamp": self.uploaded_timestamp,
        }


@dataclass(frozen=True)
class DashboardQueueCard:
    """
    Single queue card for import dashboard.

    Represents a review queue (duplicates, validation, etc.)
    with count and action link.
    """
    name: str
    description: str
    pending_count: int
    badge_color: str
    action_label: str
    action_url: str


@dataclass(frozen=True)
class ImportDashboardViewModel:
    """
    Complete dashboard view model for /imports/<import_id>/dashboard.

    Contains batch metadata and queue status for all four review queues.
    Frozen dataclass ensures immutability.
    """
    batch_id: str
    filename: str
    progress: int
    queues: tuple  # Tuple of DashboardQueueCard
    audit_log_url: str
    export_console_url: str
    back_to_imports_url: str

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.filename,
                "progress": self.progress,
            },
            "queue_status": {
                "duplicates_pending": self.queues[0].pending_count if len(self.queues) > 0 else 0,
                "validation_issues": self.queues[1].pending_count if len(self.queues) > 1 else 0,
                "normalizations_pending": self.queues[2].pending_count if len(self.queues) > 2 else 0,
                "households_pending": self.queues[3].pending_count if len(self.queues) > 3 else 0,
            },
        }
