"""
Validation Service - Service layer for validation review route.

Thin orchestration layer that hides data source (fixture, database, API)
from the Flask route. Returns template-ready dictionaries.

Phase 1B-Step 5L: Wired to use repository provider for flexible repository selection.
Phase 3: Enriched with row_status and issues from Phase 2 services.
"""

from typing import Dict, Any, Optional, Mapping
import os

from .repository_provider import get_import_repository
from .issue_recalculation_service import recalculate_row_issues
from .issue_presentation import project_validation_record
from .validation_failure_policy import is_expected_validation_failure


def get_validation_review(import_id: str, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """
    Get validation review page data for a specific import.

    Service orchestration: calls repository to fetch validation data,
    enriches records with row_status and issues from Phase 2 services,
    returns as template-ready dictionary.

    Args:
        import_id: Import ID to fetch validation data for
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed validation.

    Returns:
        Dictionary with 'batch', 'validation_issues', 'queue_status', and 'total_records' keys, ready for template

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    validation_vm = repository.get_validation(import_id)
    result = validation_vm.to_template_dict()
    database_url = None
    if config:
        database_url = config.get('GIVEBUTTER_DATABASE_URL')

    # Enrich every repository row through the one canonical projection boundary.
    for record in result.get('validation_issues', []):
        try:
            project_validation_record(
                record, import_id, database_url=database_url,
                recalculation=recalculate_row_issues,
            )
        except Exception as error:
            if not is_expected_validation_failure(error):
                raise
            # Synthetic fixture rows may carry only the fixture issue contract.
            record.pop('row_status', None)
            record.pop('issues', None)
            project_validation_record(
                record, import_id, database_url=None,
                recalculation=recalculate_row_issues,
                use_database=False,
            )

    return result
