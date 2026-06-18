"""
Duplicates Service - Orchestrates duplicate review data.

PHASE 1A REMEDIATION: This module was missing from Phase 1A implementation
but is imported by app.py. Created here to complete Phase 1A.

Phase 1B-Step 5O: Wired to use repository provider for flexible repository selection.

Routes duplicate review requests to repository and returns template-ready view models.
"""

from typing import Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository


def get_duplicates_review(import_id: str, index: int = 0, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """
    Get duplicates review page data for a specific import.

    Service orchestration: calls repository to fetch duplicate candidates,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch duplicate data for
        index: Zero-based index of duplicate pair to display. Clamped to valid range.
               Defaults to 0 (first pair).
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed duplicates.

    Returns:
        Dictionary with 'batch', 'candidate', navigation, and index keys,
        ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    duplicates_vm = repository.get_duplicates(import_id, index=index)
    return duplicates_vm.to_template_dict()
