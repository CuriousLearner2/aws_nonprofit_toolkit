from collections.abc import Mapping
from typing import Any

_ADDRESS_FIELD_ALIASES = {
    'address',
    'address 1',
    'address_1',
    'address line 1',
    'address_line_1',
    'street address',
    'street_address',
}


def normalize_validation_issue_field(field: Any) -> str:
    normalized = field.strip().lower() if isinstance(field, str) else ''
    return 'address' if normalized in _ADDRESS_FIELD_ALIASES else normalized


def validation_issue_identity(issue: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        normalize_validation_issue_field(issue.get('field')),
        str(issue.get('reason') or '').strip().lower(),
        str(issue.get('severity') or '').strip().lower(),
        str(issue.get('source') or '').strip().lower(),
    )
