"""
Exports Service - Service layer for exports console route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5Q: Wired to use repository provider for flexible repository selection.
Phase 2-Step 16: Added get_recent_exports() to fetch from audit log.
"""

import os
from typing import Dict, Any, Optional, Mapping, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .repository_provider import get_import_repository
from .database_models import AuditLogRecord


def get_export_console(import_id: str, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """
    Get export console page data for a specific import.

    Service orchestration: calls repository to fetch export data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch export data for
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed exports.

    Returns:
        Dictionary with 'batch', 'export_options', 'staged_record_count',
        'total_decisions', 'household_count', and 'recent_exports' keys, ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    exports_vm = repository.get_exports(import_id)
    return exports_vm.to_template_dict()


def get_recent_exports(import_id: str, config: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get recently generated exports from audit log.

    Queries audit_log for export_generated records for the specified import,
    returns as template-ready list sorted by generation time (newest first).

    Args:
        import_id: Import batch ID
        config: Optional database configuration

    Returns:
        List of dictionaries with: audit_log_id, filename, generated_at, row_count, warning_count

    Raises:
        ValueError: If database config invalid or missing
    """
    if not config:
        config = {}

    # Get database URL
    database_url = config.get('GIVEBUTTER_DATABASE_URL')
    if not database_url:
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        # No database configured, return empty list
        return []

    try:
        # Create database session
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Query audit records for export_generated actions
            records = session.query(AuditLogRecord).filter_by(
                batch_id=import_id,
                action_type="export_generated"
            ).order_by(
                AuditLogRecord.action_timestamp.desc()  # Newest first
            ).all()

            # Convert to template-ready format
            exports = []
            for record in records:
                details = record.details or {}
                exports.append({
                    "audit_log_id": record.id,
                    "filename": details.get('filename', 'Unknown'),
                    "export_type": details.get('export_type', 'csv'),
                    "generated_at": record.action_timestamp.isoformat() if record.action_timestamp else '',
                    "generated_timestamp": record.action_timestamp.strftime('%Y-%m-%d %H:%M') if record.action_timestamp else '',
                    "row_count": details.get('row_count', 0),
                    "warning_count": details.get('warning_count', 0),
                    "file_size": "0 B",  # Not stored, placeholder for template
                })

            return exports

        finally:
            session.close()

    except Exception as e:
        # Log error but return empty list to prevent console breakage
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching recent exports: {str(e)}")
        return []
