"""
Normalizations Service - Service layer for normalizations review route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5M: Wired to use repository provider for flexible repository selection.
"""

from typing import Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository


def get_normalizations_review(import_id: str, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """
    Get normalizations review page data for a specific import.

    Service orchestration: calls repository to fetch normalizations data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch normalizations data for
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed normalizations.

    Returns:
        Dictionary with 'batch', 'current_suggestion', 'current_suggestion_index',
        and 'total_suggestions' keys, ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    normalizations_vm = repository.get_normalizations(import_id)
    return normalizations_vm.to_template_dict()
