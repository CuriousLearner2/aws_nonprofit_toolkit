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
