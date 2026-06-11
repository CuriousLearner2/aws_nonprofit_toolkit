"""
Dashboard Service - Service layer for import dashboard route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.
"""

from typing import Dict, Any
from .fixture_repository import FixtureImportRepository


def get_import_dashboard(import_id: str) -> Dict[str, Any]:
    """
    Get import dashboard data for a specific import.

    Service orchestration: calls repository to fetch dashboard data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch dashboard for

    Returns:
        Dictionary with 'batch' and 'queue_status' keys, ready for template
    """
    dashboard_vm = FixtureImportRepository.get_dashboard(import_id)
    return dashboard_vm.to_template_dict()
