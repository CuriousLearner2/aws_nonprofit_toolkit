"""Authoritative reviewer-visible row state projection.

This module combines the already-canonical status, disposition, and gating
policies.  It is deliberately read-only: projection must never create review
records or mutate imported data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .approval_remaining_issues_policy import project_row_gating
from .row_decision_service import (
    get_row_decision_state,
    project_effective_disposition,
)
from .row_status_service import derive_row_status


@dataclass(frozen=True)
class ReviewerRowState:
    raw_import_row_id: int
    row_status: str
    issues: tuple[Mapping[str, Any], ...]
    effective_disposition: str
    current_human_decision: Optional[Mapping[str, Any]]
    history: tuple[Mapping[str, Any], ...]
    interaction_sequence: int
    last_event: Optional[Mapping[str, Any]]
    approval_blocked: bool
    export_included: bool
    export_eligible: bool
    export_blocked: bool
    blockers: tuple[str, ...]

    @property
    def has_human_decision(self) -> bool:
        return self.current_human_decision is not None

    def to_dict(self) -> dict[str, Any]:
        current = self.current_human_decision or {}
        return {
            "row_status": self.row_status,
            "issues": [dict(issue) for issue in self.issues],
            "effective_disposition": self.effective_disposition,
            "has_human_decision": self.has_human_decision,
            # Compatibility names retained for the existing row-decision API.
            "has_decision": self.has_human_decision,
            "decision": current.get("decision"),
            "notes": current.get("notes"),
            "reviewer": current.get("reviewer"),
            "timestamp": current.get("timestamp"),
            "current_decision": current.get("decision"),
            "current_notes": current.get("notes"),
            "current_reviewer": current.get("reviewer"),
            "current_timestamp": current.get("timestamp"),
            "interaction_sequence": self.interaction_sequence,
            "last_event": dict(self.last_event) if self.last_event else None,
            "history": [dict(entry) for entry in self.history],
            "approval_blocked": self.approval_blocked,
            "export_included": self.export_included,
            "export_eligible": self.export_eligible,
            "export_blocked": self.export_blocked,
            "blockers": list(self.blockers),
        }


def project_reviewer_row_state(
    *,
    batch_id: Optional[str],
    raw_import_row_id: int,
    database_url: Optional[str] = None,
    issues: Optional[list[Mapping[str, Any]]] = None,
    row_status: Optional[str] = None,
    row_index: int = 0,
    has_unresolved_validation: Optional[bool] = None,
    decision_state: Optional[Mapping[str, Any]] = None,
    base_blockers: tuple[str, ...] = (),
) -> ReviewerRowState:
    """Project all reviewer-facing state from one consistent snapshot.

    Callers that already have a production snapshot may provide ``issues``,
    ``row_status``, and ``decision_state``.  Otherwise the projection reads
    the current persisted row state through the existing services.
    """
    normalized_issues = tuple(dict(issue) for issue in (issues or ()))
    if row_status is None:
        row_status = derive_row_status(
            batch_id=batch_id,
            raw_import_row_id=raw_import_row_id,
            database_url=database_url,
            issues=list(normalized_issues) if issues is not None else None,
        )
    if decision_state is None:
        if not batch_id or not database_url:
            decision_state = {"has_decision": False, "history": []}
        else:
            decision_state = get_row_decision_state(
                batch_id, raw_import_row_id, database_url
            )

    human = None
    if decision_state.get("has_decision"):
        human = {
            "decision": decision_state.get("decision"),
            "notes": decision_state.get("notes"),
            "reviewer": decision_state.get("reviewer"),
            "timestamp": decision_state.get("timestamp"),
        }
    effective = project_effective_disposition(
        row_status=row_status,
        human_disposition=human.get("decision") if human else None,
    ) or ""
    if has_unresolved_validation is None:
        has_unresolved_validation = any(
            issue.get("severity") == "error"
            for issue in normalized_issues
        )

    gating = project_row_gating(
        raw_import_row_id=raw_import_row_id,
        row_index=row_index,
        row_status=row_status,
        has_unresolved_validation=has_unresolved_validation,
        human_disposition=effective or None,
        base_blockers=base_blockers,
    )
    return ReviewerRowState(
        raw_import_row_id=raw_import_row_id,
        row_status=row_status,
        issues=normalized_issues,
        effective_disposition=effective,
        current_human_decision=human,
        history=tuple(decision_state.get("history") or ()),
        interaction_sequence=int(decision_state.get("interaction_sequence") or 0),
        last_event=decision_state.get("last_event"),
        approval_blocked=gating.export_blocked,
        export_included=gating.export_included,
        export_eligible=gating.export_included and not gating.export_blocked,
        export_blocked=gating.export_blocked,
        blockers=gating.blockers,
    )
