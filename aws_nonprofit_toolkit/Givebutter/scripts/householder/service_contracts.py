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
    transaction_id: str = ""
    raw_import_row_id: Optional[int] = None
    issue_type: Optional[str] = None
    issue_description: Optional[str] = None
    issue_field: Optional[str] = None
    issue_reason: Optional[str] = None
    effective_status: str = "pending"

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "date": self.date,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "amount": self.amount,
            "address": self.address,
            "raw_import_row_id": self.raw_import_row_id,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "issue_field": self.issue_field,
            "issue_reason": self.issue_reason,
            "effective_status": self.effective_status,
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
    effective_status: str = "pending"

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
            "effective_status": self.effective_status,
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
    effective_status: str = "pending"

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
            "effective_status": self.effective_status,
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
    effective_status: str = "pending"

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "contact_a": self.contact_a.to_dict(),
            "contact_b": self.contact_b.to_dict(),
            "supporting_evidence": self.supporting_evidence,
            "conflicting_evidence": self.conflicting_evidence,
            "status": self.status,
            "effective_status": self.effective_status,
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
            "current_candidate_index": self.current_candidate_index,
            "total_candidates": self.total_candidates,
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


@dataclass(frozen=True)
class ExportCard:
    """
    Single export card for /imports/<import_id>/exports.

    Represents one export format option with metadata.
    Frozen dataclass ensures immutability.
    """
    id: str
    title: str
    description: str
    status: str
    files_ready: int

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "files_ready": self.files_ready,
        }


@dataclass(frozen=True)
class ExportConsoleViewModel:
    """
    Complete export console view model for /imports/<import_id>/exports.

    Contains batch metadata, export cards, and staging statistics.
    Frozen dataclass ensures immutability.
    """
    batch_id: str
    filename: str
    progress: int
    export_cards: tuple  # Tuple of ExportCard
    staged_record_count: int
    total_decisions: int
    household_count: int
    recent_exports: tuple  # Tuple of recent export records (empty for Phase 1A)

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.filename,
                "progress": self.progress,
            },
            "export_options": [card.to_dict() for card in self.export_cards],
            "staged_record_count": self.staged_record_count,
            "total_decisions": self.total_decisions,
            "household_count": self.household_count,
            "recent_exports": list(self.recent_exports),
        }


@dataclass(frozen=True)
class ExportRow:
    """
    Single derived export row based on reviewer decisions.

    Represents one contact with original values, applied normalizations,
    and decision-derived context (groupings, warnings).
    Frozen dataclass ensures immutability.
    """
    source_row_index: Optional[int]
    transaction_id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    amount: Optional[str]

    validation_status: str
    validation_issues: tuple
    normalized_fields: tuple
    normalization_warnings: tuple

    duplicate_group_id: Optional[str]
    duplicate_decision: Optional[str]
    duplicate_warnings: tuple

    household_group_id: Optional[str]
    household_group_label: Optional[str]
    household_members: tuple
    household_decision: Optional[str]
    household_warnings: tuple

    export_warnings: tuple
    export_blocked: bool
    export_derived_at: 'datetime' = None

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        from datetime import datetime, timezone
        derived_at = self.export_derived_at if isinstance(self.export_derived_at, datetime) else datetime.now(timezone.utc)
        return {
            "source_row_index": self.source_row_index,
            "transaction_id": self.transaction_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "amount": self.amount,
            "validation_status": self.validation_status,
            "validation_issues": self.validation_issues,
            "normalized_fields": self.normalized_fields,
            "normalization_warnings": self.normalization_warnings,
            "duplicate_group_id": self.duplicate_group_id,
            "duplicate_decision": self.duplicate_decision,
            "duplicate_warnings": self.duplicate_warnings,
            "household_group_id": self.household_group_id,
            "household_group_label": self.household_group_label,
            "household_members": self.household_members,
            "household_decision": self.household_decision,
            "household_warnings": self.household_warnings,
            "export_warnings": self.export_warnings,
            "export_blocked": self.export_blocked,
            "export_derived_at": derived_at.isoformat(),
        }


@dataclass(frozen=True)
class ExportPreviewResult:
    """
    Result of export preview derivation.

    Contains derived export rows, blockers, warnings, and readiness status.
    Frozen dataclass ensures immutability.
    """
    import_id: str
    export_rows: tuple
    blockers: tuple
    warnings: tuple
    row_count: int
    blocked_count: int
    warning_count: int
    is_export_ready: bool
    derived_at: 'datetime'
    deferred_household_count: int = 0
    deferred_duplicate_count: int = 0
    deferred_validation_count: int = 0

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        from datetime import datetime
        return {
            "import_id": self.import_id,
            "export_rows": [row.to_dict() for row in self.export_rows],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "row_count": self.row_count,
            "blocked_count": self.blocked_count,
            "warning_count": self.warning_count,
            "is_export_ready": self.is_export_ready,
            "derived_at": self.derived_at.isoformat() if isinstance(self.derived_at, datetime) else self.derived_at,
            "deferred_household_count": self.deferred_household_count,
            "deferred_duplicate_count": self.deferred_duplicate_count,
            "deferred_validation_count": self.deferred_validation_count,
        }
