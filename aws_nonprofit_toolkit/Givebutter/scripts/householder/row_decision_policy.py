"""Row decision normalization and sequencing policy."""

from typing import Optional, Any


def normalize_row_decision_notes(notes: Optional[str]) -> Optional[str]:
    if notes is None:
        return None

    normalized = notes.strip()
    return normalized or None


def normalize_interaction_sequence(interaction_sequence: Optional[Any]) -> Optional[int]:
    if interaction_sequence is None:
        return None

    try:
        normalized = int(interaction_sequence)
    except (TypeError, ValueError):
        raise ValueError("Row decision requires a valid interaction_sequence")

    if normalized < 1:
        raise ValueError("Row decision requires interaction_sequence >= 1")

    return normalized
