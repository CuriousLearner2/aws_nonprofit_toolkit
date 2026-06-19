"""
Export File Service - Generates CSV export files from approved preview.

Phase 2-Step 14: Generates explicit CSV export files with audit logging.
Does NOT mutate source data or call external systems.
"""

import os
import csv
import json
import logging
from io import StringIO
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Mapping, Any
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database_models import AuditLogRecord
from .export_preview_service import build_export_preview

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Base exception for export operations."""
    pass


class ExportBlockedError(ExportError):
    """Export blocked due to unresolved issues."""
    def __init__(self, blockers: list, blocked_count: int):
        self.blockers = blockers
        self.blocked_count = blocked_count
        self.message = f"Export blocked: {blocked_count} unresolved issue(s)"
        super().__init__(self.message)


class ExportUnresolvedHouseholdWarningError(ExportError):
    """Export requires confirmation for unresolved households."""
    def __init__(self, deferred_count: int):
        self.deferred_count = deferred_count
        self.message = f"Export has {deferred_count} unresolved household(s) — confirmation required"
        super().__init__(self.message)


class ExportUnresolvedDuplicateWarningError(ExportError):
    """Export requires confirmation for unresolved duplicates."""
    def __init__(self, deferred_count: int):
        self.deferred_count = deferred_count
        self.message = f"Export has {deferred_count} unresolved duplicate pair(s) — confirmation required"
        super().__init__(self.message)


class ExportUnresolvedValidationWarningError(ExportError):
    """Export requires confirmation for deferred validation issues."""
    def __init__(self, deferred_count: int):
        self.deferred_count = deferred_count
        self.message = f"Export has {deferred_count} deferred validation issue(s) — confirmation required"
        super().__init__(self.message)


class ExportIOError(ExportError):
    """File I/O error during export generation."""
    pass


@dataclass(frozen=True)
class ExportFileResult:
    """Result of successful export file generation."""
    import_id: str
    filename: str
    file_path: str
    row_count: int
    warning_count: int
    blocked_count: int
    audit_log_id: Optional[int]
    generated_at: datetime

    def to_dict(self) -> dict:
        """Convert to dictionary for template/JSON response."""
        return {
            "import_id": self.import_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "row_count": self.row_count,
            "warning_count": self.warning_count,
            "blocked_count": self.blocked_count,
            "audit_log_id": self.audit_log_id,
            "generated_at": self.generated_at.isoformat(),
        }


def _sanitize_filename(filename: str) -> str:
    """Prevent directory traversal and invalid characters."""
    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '')
    # Remove leading dots
    filename = filename.lstrip('.')
    # Limit to alphanumeric, hyphen, underscore, dot
    filename = ''.join(c for c in filename if c.isalnum() or c in '-_.')
    return filename


def _generate_safe_filename(import_id: str, timestamp: datetime) -> str:
    """Generate safe export filename with collision avoidance."""
    sanitized_id = _sanitize_filename(import_id)
    ts = timestamp.strftime('%Y%m%d_%H%M%S')
    return f"{sanitized_id}_export_{ts}.csv"


def _ensure_output_dir(output_dir: str) -> None:
    """Ensure output directory exists and is writable."""
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ExportIOError(f"Cannot create output directory: {output_dir}. {str(e)}")


def _get_safe_file_path(output_dir: str, filename: str) -> str:
    """Get absolute file path with collision avoidance."""
    base_path = os.path.join(output_dir, filename)

    if not os.path.exists(base_path):
        return base_path

    # Collision handling: append _01, _02, etc.
    name, ext = os.path.splitext(filename)
    for i in range(1, 1000):
        collision_name = f"{name}_{i:02d}{ext}"
        collision_path = os.path.join(output_dir, collision_name)
        if not os.path.exists(collision_path):
            return collision_path

    raise ExportIOError(f"Cannot find available filename for {filename}")


def _encode_csv_field(value: Any) -> str:
    """Encode value for CSV field."""
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (list, tuple)):
        # Semicolon-separated string for list/tuple fields
        return ";".join(str(v) for v in value if v is not None)

    return str(value)


def _generate_csv_content(export_rows: tuple) -> str:
    """Generate CSV content from export rows."""
    # Define header order exactly as specified
    header = [
        'source_row_index', 'transaction_id', 'first_name', 'last_name', 'email', 'phone',
        'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'amount',
        'validation_status', 'validation_issues', 'normalized_fields', 'normalization_warnings',
        'duplicate_group_id', 'duplicate_decision', 'duplicate_warnings',
        'household_group_id', 'household_group_label', 'household_members', 'household_decision', 'household_warnings',
        'export_warnings'
    ]

    # Use StringIO to generate CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(header)

    # Write rows
    for row in export_rows:
        csv_row = [
            _encode_csv_field(row.source_row_index),
            _encode_csv_field(row.transaction_id),
            _encode_csv_field(row.first_name),
            _encode_csv_field(row.last_name),
            _encode_csv_field(row.email),
            _encode_csv_field(row.phone),
            _encode_csv_field(row.address_line1),
            _encode_csv_field(row.address_line2),
            _encode_csv_field(row.city),
            _encode_csv_field(row.state),
            _encode_csv_field(row.postal_code),
            _encode_csv_field(row.amount),
            _encode_csv_field(row.validation_status),
            _encode_csv_field(row.validation_issues),
            _encode_csv_field(row.normalized_fields),
            _encode_csv_field(row.normalization_warnings),
            _encode_csv_field(row.duplicate_group_id),
            _encode_csv_field(row.duplicate_decision),
            _encode_csv_field(row.duplicate_warnings),
            _encode_csv_field(row.household_group_id),
            _encode_csv_field(row.household_group_label),
            _encode_csv_field(row.household_members),
            _encode_csv_field(row.household_decision),
            _encode_csv_field(row.household_warnings),
            _encode_csv_field(row.export_warnings),
        ]
        writer.writerow(csv_row)

    return output.getvalue()


def _write_csv_file(file_path: str, content: str) -> None:
    """Write CSV content to file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        raise ExportIOError(f"Failed to write export file: {str(e)}")


def _create_audit_record(
    session,
    import_id: str,
    filename: str,
    file_path: str,
    preview,
    reviewer: Optional[str],
    confirmed_unresolved_validations: bool = False,
    confirmed_unresolved_households: bool = False,
    confirmed_unresolved_duplicates: bool = False,
) -> int:
    """Create audit log record for export generation."""
    # Build details JSON
    details = {
        "export_type": "csv",
        "filename": filename,
        "file_path": file_path,
        "row_count": preview.row_count,
        "warning_count": preview.warning_count,
        "blocked_count": preview.blocked_count,
        "is_export_ready": preview.is_export_ready,
        "warnings_summary": list(preview.warnings) if preview.warnings else [],
        "decision_summary": {
            "validation_decisions": 0,
            "normalization_decisions": 0,
            "duplicate_decisions": 0,
            "household_decisions": 0,
        },
        "generated_by": reviewer or "system",
        "generated_at": datetime.utcnow().isoformat(),
        "confirmations": {
            "confirmed_unresolved_validations": confirmed_unresolved_validations,
            "confirmed_unresolved_households": confirmed_unresolved_households,
            "confirmed_unresolved_duplicates": confirmed_unresolved_duplicates,
        },
        "deferred_counts": {
            "deferred_validation_count": getattr(preview, 'deferred_validation_count', 0),
            "deferred_household_count": getattr(preview, 'deferred_household_count', 0),
            "deferred_duplicate_count": getattr(preview, 'deferred_duplicate_count', 0),
        },
    }

    # Create audit record
    record = AuditLogRecord(
        batch_id=import_id,
        action_type="export_generated",
        action_timestamp=datetime.utcnow(),
        actor=reviewer,
        item_id=None,
        decision_id=None,
        details=details,
    )

    session.add(record)
    session.commit()

    return record.id


def generate_export_file(
    import_id: str,
    output_dir: str,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
    confirmed_unresolved_households: bool = False,
    confirmed_unresolved_duplicates: bool = False,
    confirmed_unresolved_validations: bool = False,
) -> ExportFileResult:
    """
    Generate CSV export file from derived preview.

    Explicit export file generation with audit logging.
    Does NOT mutate source data or call external systems.

    Args:
        import_id: Import batch ID
        output_dir: Directory to write export file (must be configured, not user-provided)
        reviewer: Optional reviewer identifier for audit log
        config: Optional configuration for database selection
        confirmed_unresolved_households: Whether user confirmed unresolved households
        confirmed_unresolved_duplicates: Whether user confirmed unresolved duplicates
        confirmed_unresolved_validations: Whether user confirmed deferred validations

    Returns:
        ExportFileResult with file metadata and audit log reference

    Raises:
        ValueError: If batch not found or database config invalid
        ExportBlockedError: If blockers exist in preview
        ExportUnresolvedHouseholdWarningError: If unresolved households exist and not confirmed
        ExportUnresolvedDuplicateWarningError: If unresolved duplicates exist and not confirmed
        ExportUnresolvedValidationWarningError: If deferred validations exist and not confirmed
        ExportIOError: For filesystem or other errors
    """
    if not config:
        config = {}

    # Get database URL
    database_url = config.get('GIVEBUTTER_DATABASE_URL')
    if not database_url:
        import os
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError(
            "Export file generation requires database configuration. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or pass config."
        )

    # Validate output directory
    if not output_dir:
        raise ExportIOError("output_dir is required")

    try:
        # Build export preview (source of truth)
        preview = build_export_preview(import_id, config=config)
    except ValueError as e:
        raise ValueError(f"Cannot generate export: {str(e)}")

    # Check for blockers
    if not preview.is_export_ready:
        raise ExportBlockedError(
            blockers=list(preview.blockers),
            blocked_count=preview.blocked_count
        )

    # Check for unresolved households
    if preview.deferred_household_count > 0 and not confirmed_unresolved_households:
        raise ExportUnresolvedHouseholdWarningError(preview.deferred_household_count)

    # Check for unresolved duplicates
    if preview.deferred_duplicate_count > 0 and not confirmed_unresolved_duplicates:
        raise ExportUnresolvedDuplicateWarningError(preview.deferred_duplicate_count)

    # Check for deferred validations
    if preview.deferred_validation_count > 0 and not confirmed_unresolved_validations:
        raise ExportUnresolvedValidationWarningError(preview.deferred_validation_count)

    # Ensure output directory exists
    _ensure_output_dir(output_dir)

    # Generate filename
    timestamp = datetime.utcnow()
    filename = _generate_safe_filename(import_id, timestamp)
    file_path = _get_safe_file_path(output_dir, filename)

    # Generate CSV content
    csv_content = _generate_csv_content(preview.export_rows)

    # Write CSV file
    _write_csv_file(file_path, csv_content)

    logger.info(f"Export file generated: {import_id} -> {file_path}")

    # Create database connection for audit log
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Create audit record
        audit_log_id = _create_audit_record(
            session,
            import_id,
            filename,
            file_path,
            preview,
            reviewer,
            confirmed_unresolved_validations,
            confirmed_unresolved_households,
            confirmed_unresolved_duplicates,
        )
    finally:
        session.close()

    # Return result
    return ExportFileResult(
        import_id=import_id,
        filename=filename,
        file_path=file_path,
        row_count=preview.row_count,
        warning_count=preview.warning_count,
        blocked_count=preview.blocked_count,
        audit_log_id=audit_log_id,
        generated_at=timestamp,
    )
