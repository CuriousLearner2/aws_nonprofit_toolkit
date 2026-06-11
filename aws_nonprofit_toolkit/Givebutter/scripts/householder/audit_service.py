"""
Audit Service - Service layer for audit log route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.
"""

from typing import Dict, Any
from .fixture_repository import FixtureImportRepository


def get_audit_log(import_id: str) -> Dict[str, Any]:
    """
    Get audit log page data for a specific import.

    Service orchestration: calls repository to fetch audit data,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch audit data for

    Returns:
        Dictionary with 'batch' and 'audit_log' keys, ready for template
    """
    audit_vm = FixtureImportRepository.get_audit(import_id)
    return audit_vm.to_template_dict()
