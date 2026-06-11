"""
Households Service - Service layer for households review route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.
"""

from typing import Dict, Any
from .fixture_repository import FixtureImportRepository


def get_households_review(import_id: str) -> Dict[str, Any]:
    """
    Get households review page data for a specific import.

    Service orchestration: calls repository to fetch households data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch households data for

    Returns:
        Dictionary with 'batch', 'current_household', 'current_household_index',
        and 'total_households' keys, ready for template
    """
    households_vm = FixtureImportRepository.get_households(import_id)
    return households_vm.to_template_dict()
