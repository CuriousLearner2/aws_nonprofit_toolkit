"""
Service Contracts - Data models for DonorTrust v1 screens.

View models define the shape of data that each Jinja template needs.
Templates receive plain dataclasses, not ORM objects.
Service layer hides whether data comes from fixtures, database, or API.
"""

from dataclasses import dataclass
from typing import Optional, List


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


@dataclass(frozen=True)
class ValidationRow:
    """
    Single validation record for /imports/<import_id>/validation.

    Represents one donor record with validation issue details.
    Frozen dataclass ensures immutability.
    """
    id: str
    date: str
    name: str
    email: str
    phone: str
    amount: str
    address: str
    issue_type: Optional[str] = None
    issue_description: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "date": self.date,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "amount": self.amount,
            "address": self.address,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
        }


@dataclass(frozen=True)
class ValidationPageViewModel:
    """
    Complete validation review page view model for /imports/<import_id>/validation.

    Contains batch metadata, validation records, and queue status.
    Frozen dataclass ensures immutability.
    """
    batch_id: str
    filename: str
    progress: int
    validation_rows: tuple  # Tuple of ValidationRow
    validation_issues_count: int
    total_records: int

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.filename,
                "progress": self.progress,
            },
            "validation_issues": [row.to_dict() for row in self.validation_rows],
            "queue_status": {
                "validation_issues": self.validation_issues_count,
            },
            "total_records": self.total_records,
        }


@dataclass(frozen=True)
class NormalizationRow:
    """
    Single normalization suggestion for /imports/<import_id>/normalizations.

    Represents one field cleanup suggestion with original and suggested values.
    Frozen dataclass ensures immutability.
    """
    id: str
    contact_name: str
    field_name: str
    original_value: str
    suggested_value: str
    normalization_type: str
    status: str = "Pending"

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "contact_name": self.contact_name,
            "field_name": self.field_name,
            "original_value": self.original_value,
            "suggested_value": self.suggested_value,
            "normalization_type": self.normalization_type,
            "status": self.status,
        }


@dataclass(frozen=True)
class NormalizationPageViewModel:
    """
    Complete normalization review page view model for /imports/<import_id>/normalizations.

    Contains batch metadata and the current suggestion with navigation state.
    Frozen dataclass ensures immutability.
    """
    batch_id: str
    filename: str
    progress: int
    current_suggestion: NormalizationRow
    current_suggestion_index: int
    total_suggestions: int

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.filename,
                "progress": self.progress,
            },
            "current_suggestion": self.current_suggestion.to_dict(),
            "current_suggestion_index": self.current_suggestion_index,
            "total_suggestions": self.total_suggestions,
        }


@dataclass(frozen=True)
class HouseholdRow:
    """
    Single household suggestion for /imports/<import_id>/households.

    Represents one household grouping with proposed members and supporting/conflicting evidence.
    Frozen dataclass ensures immutability.
    """
    id: str
    suggested_name: str
    address: str
    confidence: str
    proposed_members: tuple  # Tuple of member names
    evidence: tuple  # Tuple of evidence strings
    conflicts: tuple  # Tuple of conflict strings
    status: str = "Pending"

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "suggested_name": self.suggested_name,
            "address": self.address,
            "confidence": self.confidence,
            "proposed_members": self.proposed_members,
            "evidence": self.evidence,
            "conflicts": self.conflicts,
            "status": self.status,
        }


@dataclass(frozen=True)
class HouseholdPageViewModel:
    """
    Complete household review page view model for /imports/<import_id>/households.

    Contains batch metadata and the current household suggestion with navigation state.
    Frozen dataclass ensures immutability.
    """
    batch_id: str
    filename: str
    progress: int
    current_household: HouseholdRow
    current_household_index: int
    total_households: int

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.filename,
                "progress": self.progress,
            },
            "current_household": self.current_household.to_dict(),
            "current_household_index": self.current_household_index,
            "total_households": self.total_households,
        }


@dataclass(frozen=True)
class DuplicateContact:
    """
    Contact information for duplicate comparison.

    Represents one side of a duplicate pair comparison.
    Frozen dataclass ensures immutability.
    """
    id: str
    name: str
    email: str
    phone: str
    address: str

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
        }


@dataclass(frozen=True)
class DuplicateCandidate:
    """
    Single duplicate candidate pair for /imports/<import_id>/duplicates.

    Represents two potentially duplicate contacts with supporting/conflicting evidence.
    Frozen dataclass ensures immutability.
    """
    id: str
    contact_a: DuplicateContact
    contact_b: DuplicateContact
    supporting_evidence: tuple  # Tuple of evidence strings
    conflicting_evidence: tuple  # Tuple of conflict strings
    status: str = "Pending"

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "contact_a": self.contact_a.to_dict(),
            "contact_b": self.contact_b.to_dict(),
            "supporting_evidence": self.supporting_evidence,
            "conflicting_evidence": self.conflicting_evidence,
            "status": self.status,
        }


@dataclass(frozen=True)
class DuplicatePageViewModel:
    """
    Complete duplicates review page view model for /imports/<import_id>/duplicates.

    Contains batch metadata and the current duplicate candidate with navigation state.
    Frozen dataclass ensures immutability.
    """
    batch_id: str
    filename: str
    progress: int
    current_candidate: DuplicateCandidate
    current_candidate_index: int
    total_candidates: int

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.filename,
                "progress": self.progress,
            },
            "candidate": self.current_candidate.to_dict(),
        }


@dataclass(frozen=True)
class AuditLogEntry:
    """
    Single audit log entry for /imports/<import_id>/audit.

    Represents one reviewer action or system event with timestamp and details.
    Frozen dataclass ensures immutability.
    """
    timestamp: str
    reviewer: str
    action: str
    details: str

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "timestamp": self.timestamp,
            "reviewer": self.reviewer,
            "action": self.action,
            "details": self.details,
        }


@dataclass(frozen=True)
class AuditPageViewModel:
    """
    Complete audit log view model for /imports/<import_id>/audit.

    Contains batch metadata and all audit entries for immutable compliance record.
    Frozen dataclass ensures immutability.
    """
    batch_id: str
    filename: str
    progress: int
    audit_entries: tuple  # Tuple of AuditLogEntry

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.filename,
                "progress": self.progress,
            },
            "audit_log": [entry.to_dict() for entry in self.audit_entries],
        }
