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

    # Enrich validation_issues with row_status and issues
    # Use issue_type/issue_description from the ValidationRow data
    for record in result.get('validation_issues', []):
        issue_type = record.get('issue_type')
        issue_description = record.get('issue_description')
        issue_field = record.get('issue_field')
        issue_reason = record.get('issue_reason')

        if issue_type:
            # Map issue_type codes to readable labels
            issue_labels = {
                'format-invalid': 'Invalid Format',
                'missing-required': 'Missing Required Field',
                'length-exceeded': 'Length Exceeded',
            }
            status_label = issue_labels.get(issue_type, f'Unknown Issue')
            record['row_status'] = status_label

            # Create issue object with field and reason for template
            record['issues'] = [{
                'field': issue_field or issue_type,
                'reason': issue_reason or issue_description or 'Issue detected',
                'severity': 'error'
            }] if issue_type else []
        else:
            # No issue in this record
            record['row_status'] = 'No issues'
            record['issues'] = []

    return result
