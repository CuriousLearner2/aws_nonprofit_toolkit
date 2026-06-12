"""
Duplicates Service - Orchestrates duplicate review data.

PHASE 1A REMEDIATION: This module was missing from Phase 1A implementation
but is imported by app.py. Created here to complete Phase 1A.

Routes duplicate review requests to FixtureImportRepository and
returns template-ready view models.
"""

from typing import Dict, Any
from .fixture_repository import FixtureImportRepository


def get_duplicates_review(import_id: str) -> Dict[str, Any]:
    """
    Get duplicates review page data for a specific import.

    Service orchestration: calls repository to fetch duplicate candidates,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch duplicate data for

    Returns:
        Dictionary with 'batch', 'candidate', and navigation keys,
        ready for template
    """
    duplicates_vm = FixtureImportRepository.get_duplicates(import_id)
    return duplicates_vm.to_template_dict()
