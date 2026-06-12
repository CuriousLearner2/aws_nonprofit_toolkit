"""
Exports Service - Service layer for exports console route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5Q: Wired to use repository provider for flexible repository selection.
"""

from typing import Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository


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
