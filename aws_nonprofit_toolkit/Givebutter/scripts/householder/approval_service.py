"""
Approval Service for v1.1 Review Screen Refinement

Handles batch approval with and without overrides.
Persists approval_status and override_details to ImportBatch.
Creates AuditLogRecord for approval action.
Ensures raw data and review items remain unchanged.
"""

from typing import Optional, List, Dict, Any
from .approval_override_policy import canonical_override_field
from .approval_remaining_issues_policy import project_remaining_issues
from .approval_repository import ApprovalRepositoryProtocol
from .repository_provider import get_approval_repository


def approve_batch(
    batch_id: str,
    approval_status: str,
    rows_with_overrides: Optional[List[Dict[str, Any]]] = None,
    reviewer: Optional[str] = None,
    database_url: Optional[str] = None,
    repository: Optional[ApprovalRepositoryProtocol] = None,
) -> Dict[str, Any]:
    """
    Approve a batch with or without overrides.

    Workflow:
    1. Validate batch exists and is not already approved
    2. Validate approval_status is 'approved' or 'approved_with_overrides'
    3. If approved_with_overrides, validate rows_with_overrides list
    4. Update ImportBatch.approval_status
    5. If approved_with_overrides, populate ImportBatch.override_details
    6. Create AuditLogRecord for approval action
    7. Return approval result with audit log id

    Does NOT mutate RawImportRow or ReviewItem.

    Args:
        batch_id: Import batch ID
        approval_status: 'approved' or 'approved_with_overrides'
        rows_with_overrides: List of rows with unresolved issues (for approved_with_overrides)
                           Each item: {'raw_import_row_id': int, 'row_index': int, 'issues': [{'field': str, 'reason': str}, ...]}
        reviewer: Optional reviewer identifier
        database_url: Database connection URL (optional)

    Returns:
        Dict with approval result:
        {
            'success': bool,
            'approval_status': str,
            'batch_id': str,
            'override_count': int,
            'audit_log_id': int,
            'timestamp': datetime
        }

    Raises:
        ValueError: If batch not found, invalid approval_status, or invalid override list
    """
    if approval_status not in ('approved', 'approved_with_overrides'):
        raise ValueError(f"Invalid approval_status: {approval_status}")
    repository = repository or get_approval_repository(
        {'GIVEBUTTER_DATABASE_URL': database_url} if database_url else None
    )
    batch = repository.get_batch(batch_id)
    if batch.approval_status in ('approved', 'approved_with_overrides'):
        raise ValueError(f"Batch '{batch_id}' is already {batch.approval_status}")

    if approval_status == 'approved' and check_batch_remaining_issues(
        batch_id=batch_id, database_url=database_url, repository=repository
    ):
        raise ValueError("Batch has unresolved issues; use approved_with_overrides to review them")

    override_details = None
    if approval_status == 'approved_with_overrides':
        if not rows_with_overrides:
            raise ValueError("approved_with_overrides requires rows_with_overrides list")
        overrides = []
        valid_rows = {row.raw_import_row_id for row in repository.list_rows(batch_id)}
        for row_override in rows_with_overrides:
            row_id = row_override.get('raw_import_row_id')
            if row_id not in valid_rows:
                raise ValueError(f"Raw import row {row_id} not found")
            issues = row_override.get('issues', [])
            override_entry = {
                'raw_import_row_id': row_id,
                'row_index': row_override.get('row_index'),
                'issues': issues,
            }
            field = canonical_override_field(issues)
            if field:
                override_entry['field'] = field
            overrides.append(override_entry)
        override_details = {'overrides': overrides}

    write = repository.persist_approval(
        batch_id, approval_status, override_details, reviewer
    )
    return {
        'success': True,
        'approval_status': approval_status,
        'batch_id': batch_id,
        'override_count': len((override_details or {}).get('overrides', [])),
        'audit_log_id': write.audit_log_id,
        'timestamp': write.timestamp,
    }


def get_batch_approval_status(
    batch_id: str,
    database_url: Optional[str] = None,
    repository: Optional[ApprovalRepositoryProtocol] = None,
) -> Dict[str, Any]:
    """
    Get current approval status for a batch.

    Args:
        batch_id: Import batch ID
        database_url: Database connection URL (optional)

    Returns:
        Dict with approval status:
        {
            'batch_id': str,
            'approval_status': str or None,
            'override_count': int,
            'override_details': dict or None
        }

    Raises:
        ValueError: If batch not found
    """
    repository = repository or get_approval_repository(
        {'GIVEBUTTER_DATABASE_URL': database_url} if database_url else None
    )
    batch = repository.get_batch(batch_id)
    override_count = len((batch.override_details or {}).get('overrides', []))
    return {
        'batch_id': batch_id,
        'approval_status': batch.approval_status,
        'override_count': override_count,
        'override_details': batch.override_details,
    }


def check_batch_remaining_issues(
    batch_id: str,
    database_url: Optional[str] = None,
    repository: Optional[ApprovalRepositoryProtocol] = None,
) -> List[Dict[str, Any]]:
    """
    Check for remaining unresolved issues in batch.

    Returns list of rows with remaining issues OR rows with follow-up/defer decisions
    for approval override modal.

    Args:
        batch_id: Import batch ID
        database_url: Database connection URL (optional)

    Returns:
        List of rows with remaining issues:
        [
            {
                'raw_import_row_id': int,
                'row_index': int,
                'issues': [{...}, ...],
                'row_status': str,
                'decision_warning': str (optional - for follow-up/defer rows)
            }
        ]

    Raises:
        ValueError: If batch not found
    """
    from .row_status_service import derive_row_status
    from .issue_recalculation_service import recalculate_row_issues
    from .row_decision_service import get_rows_with_follow_up, get_rows_with_defer

    repository = repository or get_approval_repository(
        {'GIVEBUTTER_DATABASE_URL': database_url} if database_url else None
    )
    repository.get_batch(batch_id)

    # Get rows with pending decisions
    follow_up_rows = set(get_rows_with_follow_up(batch_id=batch_id, database_url=database_url))
    defer_rows = set(get_rows_with_defer(batch_id=batch_id, database_url=database_url))

    # Get all raw rows in batch
    rows = repository.list_rows(batch_id)

    issues_by_row = {}
    status_by_row = {}
    for row in rows:
        issues_by_row[row.id] = recalculate_row_issues(
            batch_id=batch_id,
            raw_import_row_id=row.id,
            database_url=database_url
        )
        status_by_row[row.id] = derive_row_status(
            batch_id=batch_id,
            raw_import_row_id=row.id,
            database_url=database_url
        )

    return project_remaining_issues(
        rows=rows,
        issues_by_row=issues_by_row,
        status_by_row=status_by_row,
        follow_up_rows=follow_up_rows,
        defer_rows=defer_rows,
    )
