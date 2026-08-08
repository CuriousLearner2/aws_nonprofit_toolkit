"""Resolve the declared task lane for scope-gate routing."""

from __future__ import annotations

import os
from collections.abc import Mapping


_ALIASES = {
    "workflow": "workflow-ci",
    "ci": "workflow-ci",
    "workflow-ci": "workflow-ci",
    "product": "product",
    "invariant": "product",
    "product/invariant": "product",
    "test": "test-only",
    "test-only": "test-only",
}


def resolve_declared_lane(env: Mapping[str, str] | None = None) -> str:
    values = os.environ if env is None else env
    raw_lane = values.get("HOUSEHOLDER_LANE", "").strip().lower()
    lane = _ALIASES.get(raw_lane)
    if lane is None:
        raise ValueError("HOUSEHOLDER_LANE must be one of workflow-ci, product, or test-only")
    return lane


def lane_guard_spec(lane: str) -> tuple[str, str]:
    try:
        return {
            "workflow-ci": ("workflow_ci_lane_guard", "workflow-ci"),
            "product": ("product_lane_guard", "product"),
            "test-only": ("test_only_lane_guard", "test-only"),
        }[lane]
    except KeyError as exc:
        raise ValueError(f"unsupported declared lane: {lane}") from exc
