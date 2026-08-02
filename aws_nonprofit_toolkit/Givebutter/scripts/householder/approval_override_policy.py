"""Approval override canonicalization policy.

This module owns the stable field selection used when a reviewer approves a
batch with overrides.
"""

from typing import Optional, List, Dict, Any


def canonical_override_field(issues: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """
    Derive a stable field name for an override entry when the approval payload
    clearly targets a single field.

    Returns None for ambiguous or empty issue lists so we fail closed on
    multi-field approvals instead of inventing a misleading canonical field.
    """
    if not issues:
        return None

    fields = []
    for issue in issues:
        field = issue.get('field')
        if not field:
            continue

        normalized_field = str(field).strip().lower()
        if normalized_field and normalized_field not in fields:
            fields.append(normalized_field)

    if len(fields) == 1:
        return fields[0]

    return None
