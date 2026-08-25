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
from .reviewer_state_service import project_reviewer_row_state


def get_validation_review(import_id: str, config: Optional[Mapping[str, Any]] = None, disposition_filter: Optional[str] = None) -> Dict[str, Any]:
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

    # Enrich every row through the single reviewer-state projection.

    for record in result.get('validation_issues', []):
        raw_import_row_id = record.get('raw_import_row_id')
        record['disposition'] = record.get('disposition') or ''

        if raw_import_row_id:
            try:
                # Get all issues for this row (recalculates based on effective values)
                all_issues = recalculate_row_issues(
                    import_id,
                    raw_import_row_id,
                    database_url=database_url,
                )

                row_status = derive_row_status(issues=all_issues)

                # Format issues for template
                record['issues'] = [
                    {
                        'field': issue.get('field', 'unknown'),
                        'reason': issue.get('description', 'Issue detected'),
                        'severity': issue.get('severity', 'warning')
                    }
                    for issue in all_issues
                ]
                projection = project_reviewer_row_state(
                    batch_id=import_id,
                    raw_import_row_id=raw_import_row_id,
                    database_url=database_url,
                    issues=all_issues,
                    row_status=row_status,
                )
                projected = projection.to_dict()
                # Keep the template/API issue contract (field, reason,
                # severity); the projection's raw issue snapshot may use
                # validator-native ``description`` instead of ``reason``.
                projected['issues'] = record['issues']
                record.update(projected)
                record['disposition'] = projection.effective_disposition
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
                    # using the same blank-allowed review-time policy as DB-backed rows.
                    fixture_values = {
                        'date': record.get('date'),
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

                # Set row_status through the canonical row-status service.
                projection = project_reviewer_row_state(
                    batch_id=None,
                    raw_import_row_id=raw_import_row_id or 0,
                    issues=record.get('issues', []),
                    row_status=record.get('row_status') or derive_row_status(issues=record.get('issues', [])),
                    decision_state={"has_decision": False, "history": []},
                )
                record.update(projection.to_dict())
                record['disposition'] = projection.effective_disposition
        else:
            # No issue in this record
            record['issues'] = []
            projection = project_reviewer_row_state(
                batch_id=None,
                raw_import_row_id=0,
                issues=[],
                row_status='No issues',
                decision_state={"has_decision": False, "history": []},
            )
            record.update(projection.to_dict())
            record['disposition'] = projection.effective_disposition

    valid_disposition_filters = {
        'all', 'none', 'accept_as_is', 'needs_follow_up', 'reject_row',
    }
    if disposition_filter in valid_disposition_filters and disposition_filter != 'all':
        target = '' if disposition_filter == 'none' else disposition_filter
        result['validation_issues'] = [
            record for record in result.get('validation_issues', [])
            if (record.get('disposition') or '') == target
        ]

    return result
