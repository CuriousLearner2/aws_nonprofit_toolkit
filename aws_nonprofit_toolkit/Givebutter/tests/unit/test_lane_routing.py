from __future__ import annotations

from types import SimpleNamespace

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts" / "ci"))

import pre_commit_gate  # noqa: E402
import runtime_evidence  # noqa: E402
from lane_routing import resolve_declared_lane  # noqa: E402


@pytest.mark.parametrize(
    ("declared", "canonical"),
    [("workflow", "workflow-ci"), ("product", "product"), ("invariant", "product"), ("test", "test-only")],
)
def test_declared_lane_normalizes_to_supported_lane(declared: str, canonical: str) -> None:
    assert resolve_declared_lane({"HOUSEHOLDER_LANE": declared}) == canonical


@pytest.mark.parametrize(
    ("lane", "gate_id", "guard_lane"),
    [("workflow-ci", "workflow_ci_lane_guard", "workflow-ci"),
     ("product", "product_lane_guard", "product"),
     ("test-only", "test_only_lane_guard", "test-only")],
)
def test_readiness_and_packet_specs_route_to_declared_lane(
    lane: str, gate_id: str, guard_lane: str
) -> None:
    readiness = runtime_evidence.readiness_gate_specs(lane)[-1]
    packet = pre_commit_gate.expected_gate_specs({"HOUSEHOLDER_LANE": lane})[gate_id]
    expected_command = f"./.venv/bin/python scripts/ci/check_lane_scope.py --lane {guard_lane} --verbose"
    assert readiness["gate_id"] == gate_id
    assert readiness["command"] == expected_command
    assert packet["command"] == expected_command


def test_declared_lane_guard_dispatches_without_falling_back_to_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(pre_commit_gate, "run_product_lane_guard", lambda: calls.append("product") or SimpleNamespace(returncode=0))
    monkeypatch.setattr(pre_commit_gate, "run_test_only_lane_guard", lambda: calls.append("test-only") or SimpleNamespace(returncode=0))
    assert pre_commit_gate.run_declared_lane_guard({"HOUSEHOLDER_LANE": "product"}).returncode == 0
    assert pre_commit_gate.run_declared_lane_guard({"HOUSEHOLDER_LANE": "test-only"}).returncode == 0
    assert calls == ["product", "test-only"]


@pytest.mark.parametrize("env", [{}, {"HOUSEHOLDER_LANE": "unknown"}])
def test_missing_or_unknown_lane_fails_closed(env: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        resolve_declared_lane(env)
    with pytest.raises(ValueError):
        pre_commit_gate.expected_gate_specs(env)
