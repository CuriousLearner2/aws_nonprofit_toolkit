"""
Exports Service - Service layer for exports console route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.
"""

from typing import Dict, Any
from .fixture_repository import FixtureImportRepository


def get_export_console(import_id: str) -> Dict[str, Any]:
    """
    Get export console page data for a specific import.

    Service orchestration: calls repository to fetch export data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch export data for

    Returns:
        Dictionary with 'batch', 'export_options', 'staged_record_count',
        'total_decisions', 'household_count', and 'recent_exports' keys, ready for template
    """
    exports_vm = FixtureImportRepository.get_exports(import_id)
    return exports_vm.to_template_dict()
