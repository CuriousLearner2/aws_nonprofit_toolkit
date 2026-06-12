"""
Dashboard Service - Service layer for import dashboard route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5K: Wired to use repository provider for flexible repository selection.
"""

from typing import Dict, Any, Optional, Mapping
from .repository_provider import get_import_repository


def get_import_dashboard(import_id: str, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """
    Get import dashboard data for a specific import.

    Service orchestration: calls repository to fetch dashboard data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch dashboard for
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed dashboard.

    Returns:
        Dictionary with 'batch' and 'queue_status' keys, ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    dashboard_vm = repository.get_dashboard(import_id)
    return dashboard_vm.to_template_dict()
