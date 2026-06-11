"""
Validation Service - Service layer for validation review route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.
"""

from typing import Dict, Any
from .fixture_repository import FixtureImportRepository


def get_validation_review(import_id: str) -> Dict[str, Any]:
    """
    Get validation review page data for a specific import.

    Service orchestration: calls repository to fetch validation data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch validation data for

    Returns:
        Dictionary with 'batch', 'validation_issues', 'queue_status', and 'total_records' keys, ready for template
    """
    validation_vm = FixtureImportRepository.get_validation(import_id)
    return validation_vm.to_template_dict()
