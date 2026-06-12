"""
Households Service - Service layer for households review route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5N: Wired to use repository provider for flexible repository selection.
"""

from typing import Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository


def get_households_review(import_id: str, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """
    Get households review page data for a specific import.

    Service orchestration: calls repository to fetch households data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch households data for
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed households.

    Returns:
        Dictionary with 'batch', 'current_household', 'current_household_index',
        and 'total_households' keys, ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    households_vm = repository.get_households(import_id)
    return households_vm.to_template_dict()
