from collections.abc import Mapping
from typing import Any

from .address_policy import ADDRESS_SOURCE_ALIASES

_ADDRESS_FIELD_ALIASES = {alias.casefold() for alias in ADDRESS_SOURCE_ALIASES}


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
