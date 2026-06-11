"""
Normalizations Service - Service layer for normalizations review route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.
"""

from typing import Dict, Any
from .fixture_repository import FixtureImportRepository


def get_normalizations_review(import_id: str) -> Dict[str, Any]:
    """
    Get normalizations review page data for a specific import.

    Service orchestration: calls repository to fetch normalizations data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch normalizations data for

    Returns:
        Dictionary with 'batch', 'current_suggestion', 'current_suggestion_index',
        and 'total_suggestions' keys, ready for template
    """
    normalizations_vm = FixtureImportRepository.get_normalizations(import_id)
    return normalizations_vm.to_template_dict()
