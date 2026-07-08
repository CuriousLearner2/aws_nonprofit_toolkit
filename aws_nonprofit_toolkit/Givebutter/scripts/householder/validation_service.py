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
from .issue_recalculation_service import recalculate_row_issues, _validate_effective_values
from .row_status_service import derive_row_status


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

    # Enrich validation_issues with row_status and issues using recalculation service
    for record in result.get('validation_issues', []):
        raw_import_row_id = record.get('raw_import_row_id')

        if raw_import_row_id:
            try:
                # Get all issues for this row (recalculates based on effective values)
                all_issues = recalculate_row_issues(
                    import_id,
                    raw_import_row_id,
                    database_url=database_url,
                )

                # Get row status
                row_status = derive_row_status(
                    import_id,
                    raw_import_row_id,
                    database_url=database_url,
                )

                # Format issues for template
                record['issues'] = [
                    {
                        'field': issue.get('field', 'unknown'),
                        'reason': issue.get('description', 'Issue detected'),
                        'severity': issue.get('severity', 'warning')
                    }
                    for issue in all_issues
                ]
                record['row_status'] = row_status
            except (ValueError, Exception):
                # Fall back to fixture-provided data if batch/row not in database
                # (e.g., when using fixture repository with synthetic row IDs)
                # First check if fixture has an issue_type
                if record.get('issue_type') and not record.get('issues'):
                    # Format fixture-provided issue_type/issue_description to issues list
                    record['issues'] = [
                        {
                            'field': record.get('issue_field', 'unknown'),
                            'reason': record.get('issue_description', 'Issue detected'),
                            'severity': 'error' if record.get('issue_type') == 'missing-required' else 'warning'
                        }
                    ]
                elif not record.get('issue_type'):
                    # No fixture-provided issue_type; validate fixture fields to detect issues
                    fixture_values = {
                        'amount': record.get('amount'),
                        'email': record.get('email'),
                        'phone': record.get('phone'),
                        'address': record.get('address'),
                    }
                    validation_issues = _validate_effective_values(fixture_values)
                    record['issues'] = [
                        {
                            'field': issue.get('field', 'unknown'),
                            'reason': issue.get('description', 'Issue detected'),
                            'severity': issue.get('severity', 'warning')
                        }
                        for issue in validation_issues
                    ]
                else:
                    # Shouldn't reach here, but be safe
                    record['issues'] = []

                # Set row_status based on whether there are blocking or warning issues.
                if not record.get('row_status'):
                    has_blocking = any(
                        issue.get('severity') == 'error'
                        for issue in record.get('issues', [])
                    )
                    has_warning = any(
                        issue.get('severity') != 'error'
                        for issue in record.get('issues', [])
                    )

                    if has_blocking:
                        record['row_status'] = 'Blocking'
                    elif has_warning:
                        record['row_status'] = 'Warning'
                    else:
                        record['row_status'] = 'No issues'
        else:
            # No issue in this record
            record['row_status'] = 'No issues'
            record['issues'] = []

    return result
