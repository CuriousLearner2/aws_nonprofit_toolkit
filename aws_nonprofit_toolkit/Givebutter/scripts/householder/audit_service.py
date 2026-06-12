"""
Audit Service - Service layer for audit log route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5P: Wired to use repository provider for flexible repository selection.
"""

from typing import Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository


def get_audit_log(import_id: str, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """
    Get audit log page data for a specific import.

    Service orchestration: calls repository to fetch audit data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch audit data for
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed audit.

    Returns:
        Dictionary with 'batch' and 'audit_log' keys, ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    audit_vm = repository.get_audit(import_id)
    return audit_vm.to_template_dict()
