from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field as dataclass_field
from types import MappingProxyType
from typing import Any

from .issue_identity import normalize_validation_issue_field, validation_issue_identity

_CORE_KEYS = {"field", "issue_type", "reason", "severity", "source", "message", "normalized_field", "identity"}


def _first_text(issue: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = issue.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


@dataclass(frozen=True, slots=True)
class ValidationIssueContract:
    identity: tuple[str, str, str, str]
    field: str
    normalized_field: str
    issue_type: str | None
    reason: str
    severity: str
    source: str
    message: str
    metadata: Mapping[str, Any] = dataclass_field(
        default_factory=lambda: MappingProxyType({}),
        hash=False,
    )

    @classmethod
    def from_mapping(cls, issue: Mapping[str, Any]) -> "ValidationIssueContract":
        field = _first_text(issue, "field", "issue_field")
        normalized_field = normalize_validation_issue_field(field)
        reason = _first_text(issue, "reason", "issue_reason").lower()
        severity = _first_text(issue, "severity", default="warning").lower()
        source = _first_text(issue, "source").lower()
        issue_type_value = issue.get("issue_type")
        issue_type = None if issue_type_value is None else str(issue_type_value).strip()
        message = _first_text(issue, "message", "description", "issue_description", default=reason)
        identity = validation_issue_identity(
            {
                "field": field,
                "reason": reason,
                "severity": severity,
                "source": source,
            }
        )
        metadata = {key: value for key, value in issue.items() if key not in _CORE_KEYS}
        return cls(
            identity=identity,
            field=field,
            normalized_field=normalized_field,
            issue_type=issue_type,
            reason=reason,
            severity=severity,
            source=source,
            message=message,
            metadata=MappingProxyType(metadata),
        )

    def to_mapping(self) -> dict[str, Any]:
        mapping = dict(self.metadata)
        mapping.update(
            {
                "identity": self.identity,
                "field": self.field,
                "normalized_field": self.normalized_field,
                "issue_type": self.issue_type,
                "reason": self.reason,
                "severity": self.severity,
                "source": self.source,
                "message": self.message,
            }
        )
        return mapping
