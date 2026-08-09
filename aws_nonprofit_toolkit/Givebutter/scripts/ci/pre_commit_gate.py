#!/usr/bin/env python3
"""Pre-commit gate for Givebutter tests and machine-readable commit readiness."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from lane_routing import lane_guard_spec, resolve_declared_lane
except ModuleNotFoundError:  # package import from staged-tree integrity checks
    from scripts.ci.lane_routing import lane_guard_spec, resolve_declared_lane

BLOCKED_PATTERNS = (
    ".DS_Store", "scheduled_tasks.lock", "screenshots/", "traces/", "videos/",
    "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "givebutter.db", "listings.db",
)
COMMIT_MODE_ENV = "HOUSEHOLDER_COMMIT_MODE"
PACKET_RELATIVE_TO_GIVEBUTTER = Path(".artifacts/commit-readiness.json")
PACKET_REPO_PATH = "Givebutter/.artifacts/commit-readiness.json"
REQUIRED_PACKET_FIELDS = {
    "schema_version", "task_id", "reviewer_verdict", "breaker_verdict", "qa_verdict",
    "canonical_gates_passed", "scope_guard_passed", "commit_authorized",
    "push_authorized", "reviewed_head", "reviewed_diff_sha256", "reviewed_at",
    "informational_notes", "required_changes", "required_roles", "gate_results", "authorized_exceptions",
}
ALLOWED_REQUIRED_ROLES = {"Reviewer", "Breaker", "QA"}
ALLOWED_GATE_GROUPS = {"canonical", "scope"}
ALLOWED_GATE_STATUSES = {"passed", "baseline_debt_verified", "failed", "not_run"}
ALLOWED_EXCEPTION_TYPES = {"mixed_scope_exception"}
PYTEST_IDENTITY_RE = re.compile(r"^[^\s\x00]+::[^\s\x00]+$")
BASELINE_DEBT_EVIDENCE_FIELDS = {
    "baseline_sha",
    "current_staged_fingerprint",
    "command",
    "baseline_command",
    "current_command",
    "baseline_result",
    "current_result",
    "new_result",
    "baseline_failing_identities",
    "current_failing_identities",
    "new_failing_identities",
    "no_new_failing_identities",
    "reviewed_head",
    "reviewed_staged_fingerprint",
}
RESULT_COUNT_FIELDS = {"total", "passed", "failed", "skipped"}
CANONICAL_GATE_SPECS = {
    "check_no_artifacts": {
        "group": "canonical",
        "command": "./.venv/bin/python scripts/ci/check_no_artifacts.py",
    },
    "check_task_untracked": {
        "group": "canonical",
        "command": "./.venv/bin/python scripts/ci/check_task_untracked.py",
    },
    "check_staged_tree_integrity": {
        "group": "canonical",
        "command": "./.venv/bin/python scripts/ci/check_staged_tree_integrity.py",
    },
}

EXPECTED_GATE_SPECS = {
    **CANONICAL_GATE_SPECS,
    "full_unit_integration_gate": {
        "group": "canonical",
        "command": "./.venv/bin/python -m pytest -q",
    },
    "workflow_ci_lane_guard": {
        "group": "scope",
        "command": "./.venv/bin/python scripts/ci/check_lane_scope.py --lane workflow-ci --verbose",
    },
}


def expected_gate_specs(env: dict[str, str]) -> dict[str, dict[str, str]]:
    lane = resolve_declared_lane(env)
    gate_id, guard_lane = lane_guard_spec(lane)
    return {
        **CANONICAL_GATE_SPECS,
        "full_unit_integration_gate": EXPECTED_GATE_SPECS["full_unit_integration_gate"],
        gate_id: {
            "group": "scope",
            "command": f"./.venv/bin/python scripts/ci/check_lane_scope.py --lane {guard_lane} --verbose",
        },
    }


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_givebutter_dir() -> Path:
    return get_repo_root() / "Givebutter"


def get_venv_python() -> Path:
    return get_givebutter_dir() / ".venv/bin/python"


def get_readiness_packet_path() -> Path:
    return get_givebutter_dir() / PACKET_RELATIVE_TO_GIVEBUTTER


def build_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "PYTEST_ADDOPTS",
    ):
        env.pop(key, None)
    venv_bin = str(get_givebutter_dir() / ".venv/bin")
    env["PATH"] = f"{venv_bin}:{env['PATH']}" if env.get("PATH") else venv_bin
    return env


def resolve_command(command: str, env: dict[str, str]) -> str | None:
    return shutil.which(command, path=env.get("PATH"))


def run_git(args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args], cwd=get_repo_root(), capture_output=True,
        env=build_env(), text=not binary, check=False,
    )


def list_staged_files() -> list[str]:
    result = run_git(["diff", "--cached", "--name-only"])
    if result.returncode != 0:
        raise RuntimeError("git diff --cached --name-only failed")
    return [line for line in result.stdout.splitlines() if line]


def get_current_head() -> str:
    result = run_git(["rev-parse", "HEAD"])
    if result.returncode != 0:
        raise RuntimeError("git rev-parse HEAD failed")
    return result.stdout.strip()


def get_staged_diff_bytes() -> bytes:
    result = run_git(
        ["diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"],
        binary=True,
    )
    if result.returncode != 0:
        raise RuntimeError("git staged-diff fingerprint command failed")
    return result.stdout


def staged_diff_sha256() -> str:
    return hashlib.sha256(get_staged_diff_bytes()).hexdigest()


def is_blocked_artifact(path: str) -> bool:
    return any(
        pattern in path or (pattern.startswith("*") and path.endswith(pattern[1:]))
        for pattern in BLOCKED_PATTERNS
    )


def check_blocked_artifacts() -> int:
    print("Checking for blocked artifacts...")
    for path in list_staged_files():
        if is_blocked_artifact(path):
            print(f"❌ Found blocked artifact pattern: {path}")
            print("\nCOMMIT BLOCKED: Remove blocked files and re-stage.")
            return 1
    print("✓ No blocked artifacts found\n")
    return 0


def _is_empty_required_changes(value: Any) -> bool:
    return value in (None, "", [])


def _valid_reviewed_at(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_required_roles(value: Any, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or not value:
        errors.append("required_roles must be a non-empty list")
        return set()
    if any(not isinstance(role, str) or not role for role in value):
        errors.append("required_roles must contain non-empty role names")
        return set()
    roles = list(value)
    unknown = sorted(set(roles) - ALLOWED_REQUIRED_ROLES)
    if unknown:
        errors.append("required_roles contains unknown roles: " + ", ".join(unknown))
    if len(set(roles)) != len(roles):
        errors.append("required_roles must not contain duplicates")
    if "Reviewer" not in roles:
        errors.append("Reviewer is always required")
    if roles != sorted(roles):
        errors.append("required_roles must be deterministically sorted")
    return set(roles) if not unknown else set()


def _declared_baseline_sha(env: dict[str, str], fallback: str) -> str | None:
    declared = (
        env.get("HOUSEHOLDER_INTEGRATION_BASELINE", "").strip()
        or env.get("HOUSEHOLDER_BASELINE_SHA", "").strip()
    )
    if not declared:
        return fallback or None
    if re.fullmatch(r"[0-9a-fA-F]{40}", declared):
        return declared.lower()
    result = run_git(["rev-parse", declared])
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _normalize_identity_list(
    value: Any,
    field: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> list[str] | None:
    if not isinstance(value, list):
        errors.append(f"{field} must be a list")
        return None
    identities: list[str] = []
    for index, identity in enumerate(value):
        if not isinstance(identity, str) or not identity.strip() or not PYTEST_IDENTITY_RE.fullmatch(identity.strip()):
            errors.append(f"{field}[{index}] is not a valid normalized test identity")
            continue
        identities.append(identity.strip())
    if len(set(identities)) != len(identities):
        errors.append(f"{field} must not contain duplicate identities")
    normalized = sorted(identities)
    if identities != normalized:
        errors.append(f"{field} must be deterministically sorted")
    return normalized


def _validate_result_counts(
    result: Any,
    field: str,
    failing_identities: list[str] | None,
    errors: list[str],
) -> None:
    if not isinstance(result, dict):
        errors.append(f"{field} must be an object")
        return
    missing = sorted(RESULT_COUNT_FIELDS - result.keys())
    unknown = sorted(set(result) - RESULT_COUNT_FIELDS)
    if missing:
        errors.append(f"{field} is missing required counts: {', '.join(missing)}")
    if unknown:
        errors.append(f"{field} contains unknown counts: {', '.join(unknown)}")
    for key in RESULT_COUNT_FIELDS:
        if key in result and (not _is_int(result[key]) or result[key] < 0):
            errors.append(f"{field}.{key} must be a non-negative integer")
    failed = result.get("failed")
    if failed is not None and failing_identities is not None and failed != len(failing_identities):
        errors.append(f"{field}.failed must equal the recorded failing identity count")
    total = result.get("total")
    components = [result[key] for key in ("passed", "failed", "skipped") if key in result]
    if total is not None and len(components) == 3 and total != sum(components):
        errors.append(f"{field}.total must equal the sum of passed + failed + skipped")


def validate_baseline_debt_evidence(
    evidence: Any,
    *,
    command: str,
    env: dict[str, str],
    expected_head: str,
    expected_fingerprint: str,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(evidence, dict):
        return ["baseline debt evidence must be an object"]
    unknown = sorted(set(evidence) - BASELINE_DEBT_EVIDENCE_FIELDS)
    if unknown:
        errors.append("baseline debt evidence contains unknown fields: " + ", ".join(unknown))
    missing = sorted(BASELINE_DEBT_EVIDENCE_FIELDS - evidence.keys())
    if missing:
        errors.append("baseline debt evidence is missing: " + ", ".join(missing))
        return errors
    if evidence["command"] != command:
        errors.append("baseline debt evidence command mismatch")
    if evidence["baseline_command"] != command or evidence["current_command"] != command:
        errors.append("baseline/current command identity must match the canonical broad-suite command")
    declared_baseline = _declared_baseline_sha(env, "")
    if declared_baseline is None or evidence["baseline_sha"] != declared_baseline:
        errors.append("baseline debt evidence baseline_sha does not match the declared baseline")
    if evidence["current_staged_fingerprint"] != expected_fingerprint:
        errors.append("baseline debt evidence staged fingerprint mismatch")
    if evidence["reviewed_head"] != expected_head:
        errors.append("baseline debt evidence reviewed_head mismatch")
    if evidence["reviewed_staged_fingerprint"] != expected_fingerprint:
        errors.append("baseline debt evidence reviewed fingerprint mismatch")

    baseline_ids = _normalize_identity_list(
        evidence["baseline_failing_identities"],
        "baseline_failing_identities",
        errors,
    )
    current_ids = _normalize_identity_list(
        evidence["current_failing_identities"],
        "current_failing_identities",
        errors,
    )
    new_ids = _normalize_identity_list(
        evidence["new_failing_identities"],
        "new_failing_identities",
        errors,
        allow_empty=True,
    )
    if baseline_ids is not None and current_ids is not None:
        computed_new = sorted(set(current_ids) - set(baseline_ids))
        if computed_new:
            errors.append("current-only failing identities reject BASELINE_DEBT_VERIFIED")
        if new_ids != computed_new:
            errors.append("new_failing_identities does not match baseline/current identities")
    if evidence["no_new_failing_identities"] is not True or new_ids:
        errors.append("baseline debt evidence must prove no new failing identities")
    _validate_result_counts(evidence["baseline_result"], "baseline_result", baseline_ids, errors)
    _validate_result_counts(evidence["current_result"], "current_result", current_ids, errors)
    _validate_result_counts(evidence["new_result"], "new_result", new_ids, errors)
    return errors


def _validate_gate_record(
    gate: Any,
    index: int,
    errors: list[str],
    gate_ids: set[str],
    expected_specs: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    if not isinstance(gate, dict):
        errors.append(f"gate_results[{index}] must be a JSON object")
        return None

    missing = sorted({"gate_id", "group", "command", "required", "status", "exit_code"} - gate.keys())
    if missing:
        errors.append(f"gate_results[{index}] is missing required fields: {', '.join(missing)}")
        return None

    gate_id = gate["gate_id"]
    group = gate["group"]
    command = gate["command"]
    required = gate["required"]
    status = gate["status"]
    exit_code = gate["exit_code"]
    exception_id = gate.get("exception_id")

    if not _is_nonempty_string(gate_id):
        errors.append(f"gate_results[{index}].gate_id must be a non-empty string")
    elif gate_id in gate_ids:
        errors.append(f"gate_results[{index}].gate_id must be unique")
    elif gate_id not in expected_specs:
        errors.append(
            f"gate_results[{index}].gate_id must be one of: {', '.join(sorted(expected_specs))}"
        )
    else:
        gate_ids.add(gate_id)

    expected_spec = expected_specs.get(gate_id) if _is_nonempty_string(gate_id) else None
    if expected_spec is not None:
        expected_group = expected_spec["group"]
        expected_command = expected_spec["command"]
        if not _is_nonempty_string(group):
            errors.append(f"gate_results[{index}].group must be a non-empty string")
        elif group != expected_group:
            errors.append(
                f"gate_results[{index}].group must equal {expected_group} for gate_id {gate_id}"
            )
        if not _is_nonempty_string(command):
            errors.append(f"gate_results[{index}].command must be a non-empty string")
        elif command != expected_command:
            errors.append(
                f"gate_results[{index}].command must equal {expected_command} for gate_id {gate_id}"
            )
    elif not _is_nonempty_string(group):
        errors.append(f"gate_results[{index}].group must be a non-empty string")
    elif group not in ALLOWED_GATE_GROUPS:
        errors.append(
            f"gate_results[{index}].group must be one of: {', '.join(sorted(ALLOWED_GATE_GROUPS))}"
        )

    if not _is_nonempty_string(command):
        errors.append(f"gate_results[{index}].command must be a non-empty string")

    if not isinstance(required, bool):
        errors.append(f"gate_results[{index}].required must be a boolean")
    elif required is not True:
        errors.append(f"gate_results[{index}].required must be true")

    if not _is_nonempty_string(status):
        errors.append(f"gate_results[{index}].status must be a non-empty string")
    elif status not in ALLOWED_GATE_STATUSES:
        errors.append(
            f"gate_results[{index}].status must be one of: {', '.join(sorted(ALLOWED_GATE_STATUSES))}"
        )

    if exit_code is not None and not _is_int(exit_code):
        errors.append(f"gate_results[{index}].exit_code must be an integer or null")

    if exception_id is not None and not _is_nonempty_string(exception_id):
        errors.append(f"gate_results[{index}].exception_id must be a non-empty string when present")

    if status == "passed":
        if exit_code != 0:
            errors.append(f"gate_results[{index}].exit_code must be 0 when status is passed")
        if exception_id is not None:
            errors.append(f"gate_results[{index}].exception_id must be omitted when status is passed")
    elif status == "failed":
        if not _is_int(exit_code) or exit_code == 0:
            errors.append(f"gate_results[{index}].exit_code must be a non-zero integer when status is failed")
    elif status == "baseline_debt_verified":
        if not _is_int(exit_code) or exit_code == 0:
            errors.append(
                f"gate_results[{index}].exit_code must be a non-zero integer when status is baseline_debt_verified"
            )
        if gate_id != "full_unit_integration_gate":
            errors.append("baseline_debt_verified is only valid for full_unit_integration_gate")
        if "evidence" not in gate:
            errors.append(f"gate_results[{index}].evidence is required for baseline_debt_verified")
    elif status == "not_run":
        if exit_code is not None:
            errors.append(f"gate_results[{index}].exit_code must be null when status is not_run")
        if exception_id is not None:
            errors.append(f"gate_results[{index}].exception_id must be omitted when status is not_run")
        if required is True:
            errors.append(f"gate_results[{index}] cannot be required when status is not_run")

    return {
        "gate_id": gate_id,
        "group": group,
        "command": command,
        "required": required,
        "status": status,
        "exit_code": exit_code,
        "exception_id": exception_id,
        **({"evidence": gate["evidence"]} if "evidence" in gate else {}),
    }


def _validate_authorized_exceptions(
    exceptions: Any,
    gates_by_id: dict[str, dict[str, Any]],
    errors: list[str],
) -> set[str]:
    if not isinstance(exceptions, list):
        errors.append("authorized_exceptions must be a list")
        return set()

    exception_ids: set[str] = set()
    authorized_failed_gate_ids: set[str] = set()
    for index, exc in enumerate(exceptions):
        if not isinstance(exc, dict):
            errors.append(f"authorized_exceptions[{index}] must be a JSON object")
            continue

        missing = sorted({"exception_id", "exception_type", "authorized", "applies_to_gate_ids"} - exc.keys())
        if missing:
            errors.append(
                f"authorized_exceptions[{index}] is missing required fields: {', '.join(missing)}"
            )
            continue

        exception_id = exc["exception_id"]
        exception_type = exc["exception_type"]
        authorized = exc["authorized"]
        applies_to_gate_ids = exc["applies_to_gate_ids"]

        if not _is_nonempty_string(exception_id):
            errors.append(f"authorized_exceptions[{index}].exception_id must be a non-empty string")
            continue
        if exception_id in exception_ids:
            errors.append(f"authorized_exceptions[{index}].exception_id must be unique")
            continue
        exception_ids.add(exception_id)

        if not _is_nonempty_string(exception_type):
            errors.append(f"authorized_exceptions[{index}].exception_type must be a non-empty string")
        elif exception_type not in ALLOWED_EXCEPTION_TYPES:
            errors.append(
                f"authorized_exceptions[{index}].exception_type must be one of: "
                f"{', '.join(sorted(ALLOWED_EXCEPTION_TYPES))}"
            )

        if authorized is not True:
            errors.append(f"authorized_exceptions[{index}].authorized must be true")

        if not isinstance(applies_to_gate_ids, list) or not applies_to_gate_ids:
            errors.append(
                f"authorized_exceptions[{index}].applies_to_gate_ids must be a non-empty list of gate IDs"
            )
            continue

        seen_gate_ids: set[str] = set()
        for gate_id in applies_to_gate_ids:
            if not _is_nonempty_string(gate_id):
                errors.append(
                    f"authorized_exceptions[{index}].applies_to_gate_ids must contain non-empty strings"
                )
                continue
            if gate_id in seen_gate_ids:
                errors.append(
                    f"authorized_exceptions[{index}].applies_to_gate_ids must not contain duplicates"
                )
                continue
            seen_gate_ids.add(gate_id)

            gate = gates_by_id.get(gate_id)
            if gate is None:
                errors.append(
                    f"authorized_exceptions[{index}].applies_to_gate_ids references unknown gate_id {gate_id}"
                )
                continue
            if gate["group"] != "scope":
                errors.append(
                    f"authorized_exceptions[{index}] may only authorize scope gates; {gate_id} is not scope"
                )
                continue
            if gate["status"] != "failed":
                errors.append(
                    f"authorized_exceptions[{index}].applies_to_gate_ids may only reference failed scope gates"
                )
                continue
            if gate_id in authorized_failed_gate_ids:
                errors.append(f"authorized_exceptions[{index}].applies_to_gate_ids duplicates gate_id {gate_id}")
                continue
            authorized_failed_gate_ids.add(gate_id)
            if gate.get("exception_id") != exception_id:
                errors.append(
                    f"gate_results entry {gate_id} must reference authorized_exceptions.{exception_id}"
                )

    return authorized_failed_gate_ids


def run_workflow_ci_lane_guard() -> subprocess.CompletedProcess[Any] | None:
    return run_guard([str(get_venv_python()), "scripts/ci/check_lane_scope.py", "--lane", "workflow-ci", "--verbose"])


def run_product_lane_guard() -> subprocess.CompletedProcess[Any] | None:
    return run_guard([str(get_venv_python()), "scripts/ci/check_lane_scope.py", "--lane", "product", "--verbose"])


def run_test_only_lane_guard() -> subprocess.CompletedProcess[Any] | None:
    return run_guard([str(get_venv_python()), "scripts/ci/check_lane_scope.py", "--lane", "test-only", "--verbose"])


def run_declared_lane_guard(env: dict[str, str]) -> subprocess.CompletedProcess[Any] | None:
    lane = resolve_declared_lane(env)
    if lane == "workflow-ci":
        return run_workflow_ci_lane_guard()
    if lane == "product":
        return run_product_lane_guard()
    return run_test_only_lane_guard()


def commit_mode(env: dict[str, str]) -> str:
    mode = env.get(COMMIT_MODE_ENV, "normal")
    if mode not in {"normal", "heavy"}:
        raise ValueError(f"{COMMIT_MODE_ENV} must be normal or heavy")
    return mode


def run_guard(command: list[str]) -> subprocess.CompletedProcess[Any] | None:
    try:
        return subprocess.run(
            command,
            cwd=get_givebutter_dir(),
            env=build_env(),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None


def run_task_untracked_guard() -> subprocess.CompletedProcess[Any] | None:
    return run_guard([str(get_venv_python()), "scripts/ci/check_task_untracked.py"])


def run_staged_tree_integrity_guard() -> subprocess.CompletedProcess[Any] | None:
    return run_guard([str(get_venv_python()), "scripts/ci/check_staged_tree_integrity.py"])


def load_readiness_packet(path: Path | None = None) -> dict[str, Any]:
    packet_path = path or get_readiness_packet_path()
    try:
        raw = packet_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError(f"commit-readiness packet missing: {packet_path}") from exc
    try:
        packet = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"commit-readiness packet is malformed JSON: {exc}") from exc
    if not isinstance(packet, dict):
        raise ValueError("commit-readiness packet must be a JSON object")
    return packet


def validate_readiness_packet(packet: dict[str, Any], env: dict[str, str]) -> list[str]:
    errors: list[str] = []
    try:
        selected_gate_specs = expected_gate_specs(env)
    except ValueError as exc:
        errors.append(str(exc))
        selected_gate_specs = {}
    missing = sorted(REQUIRED_PACKET_FIELDS - packet.keys())
    if missing:
        errors.append(f"missing required packet fields: {', '.join(missing)}")
        return errors

    if packet["schema_version"] != 2:
        errors.append("schema_version must equal 2")

    current_task_id = env.get("HOUSEHOLDER_TASK_ID", "").strip()
    if not current_task_id:
        errors.append("HOUSEHOLDER_TASK_ID is required as the independent current-task identity")
    elif packet["task_id"] != current_task_id:
        errors.append("task_id does not match HOUSEHOLDER_TASK_ID")

    required_roles = _validate_required_roles(packet["required_roles"], errors)
    exact_values = {
        "reviewer_verdict": "VERDICT=ACCEPT",
        "breaker_verdict": "BREAKER=PASS" if "Breaker" in required_roles else "NOT_REQUIRED",
        "qa_verdict": "QA=PASS" if "QA" in required_roles else "NOT_REQUIRED",
    }
    for field, expected in exact_values.items():
        if packet[field] != expected:
            errors.append(f"{field} must equal {expected}")

    for field in ("canonical_gates_passed", "scope_guard_passed", "commit_authorized"):
        if not isinstance(packet[field], bool):
            errors.append(f"{field} must be a boolean")

    if not isinstance(packet["push_authorized"], bool):
        errors.append("push_authorized must be a boolean")

    if not _is_empty_required_changes(packet["required_changes"]):
        errors.append("required_changes must be empty for commit eligibility")

    if not _valid_reviewed_at(packet["reviewed_at"]):
        errors.append("reviewed_at must be a valid ISO-8601 timestamp")

    gate_results = packet["gate_results"]
    if not isinstance(gate_results, list) or not gate_results:
        errors.append("gate_results must be a non-empty list")
        gate_results = []

    gates_by_id: dict[str, dict[str, Any]] = {}
    seen_gate_ids: set[str] = set()
    canonical_required_statuses: list[str] = []
    scope_required_statuses: list[str] = []
    for index, gate in enumerate(gate_results):
        normalized = _validate_gate_record(gate, index, errors, seen_gate_ids, selected_gate_specs)
        if normalized is None:
            continue
        gate_id = normalized["gate_id"]
        if not _is_nonempty_string(gate_id):
            continue
        gates_by_id[gate_id] = normalized
        if normalized["required"] is True:
            if normalized["group"] == "canonical":
                canonical_required_statuses.append(normalized["status"])
            elif normalized["group"] == "scope":
                scope_required_statuses.append(normalized["status"])

    if not gates_by_id:
        errors.append("gate_results must contain at least one valid gate record")
    else:
        expected_gate_ids = set(selected_gate_specs)
        seen_expected_gate_ids = set(gates_by_id)
        missing_gate_ids = sorted(expected_gate_ids - seen_expected_gate_ids)
        unexpected_gate_ids = sorted(seen_expected_gate_ids - expected_gate_ids)
        if missing_gate_ids:
            errors.append(
                f"gate_results is missing required gate_ids: {', '.join(missing_gate_ids)}"
            )
        if unexpected_gate_ids:
            errors.append(
                f"gate_results contains unexpected gate_ids: {', '.join(unexpected_gate_ids)}"
            )

    authorized_failed_gate_ids = _validate_authorized_exceptions(
        packet["authorized_exceptions"], gates_by_id, errors
    )

    try:
        lane_guard_result = run_declared_lane_guard(env)
    except ValueError:
        lane_guard_result = None
    if lane_guard_result is None:
        errors.append("declared lane guard could not be executed")
    elif authorized_failed_gate_ids:
        if lane_guard_result.returncode == 0:
            errors.append(
                "mixed-scope exceptions require an independently verified declared-lane conflict"
            )
        elif lane_guard_result.returncode != 1:
            errors.append(
                "declared lane guard must exit 1 to authorize a mixed-scope exception"
            )
    elif lane_guard_result.returncode != 0:
        errors.append(
            "declared lane guard must pass for packets without an authorized mixed-scope exception"
        )

    for gate_id, gate in gates_by_id.items():
        if gate["required"] is not True:
            continue
        if gate["status"] == "failed":
            if gate["group"] != "scope":
                errors.append(f"required gate {gate_id} failed and cannot be exception-authorized")
            elif gate_id not in authorized_failed_gate_ids:
                errors.append(
                    f"required scope gate {gate_id} failed but is not linked to an authorized exception"
                )
        elif gate["status"] == "not_run":
            errors.append(f"required gate {gate_id} was not run")

    derived_canonical_passed = all(
        status == "passed" or (
            status == "baseline_debt_verified"
            and gate_id == "full_unit_integration_gate"
        )
        for gate_id, gate in gates_by_id.items()
        if gate["required"] is True and gate["group"] == "canonical"
        for status in [gate["status"]]
    )
    derived_scope_passed = all(status == "passed" for status in scope_required_statuses)
    if packet["canonical_gates_passed"] is not derived_canonical_passed:
        errors.append("canonical_gates_passed does not match the recorded gate results")
    if packet["scope_guard_passed"] is not derived_scope_passed:
        errors.append("scope_guard_passed does not match the recorded gate results")

    derived_commit_authorized = derived_canonical_passed and (
        derived_scope_passed or bool(authorized_failed_gate_ids)
    )
    if packet["commit_authorized"] is not True:
        errors.append("commit_authorized must be true")
    if packet["commit_authorized"] is not derived_commit_authorized:
        errors.append("commit_authorized does not match the recorded gate results and exceptions")

    staged = list_staged_files()
    if PACKET_REPO_PATH in staged or str(PACKET_RELATIVE_TO_GIVEBUTTER) in staged:
        errors.append("commit-readiness packet must not be staged")

    try:
        head = get_current_head()
        fingerprint = staged_diff_sha256()
    except RuntimeError as exc:
        errors.append(str(exc))
        return errors

    broad_gate = gates_by_id.get("full_unit_integration_gate")
    if broad_gate and broad_gate["status"] == "baseline_debt_verified":
        errors.extend(
            validate_baseline_debt_evidence(
                broad_gate.get("evidence"),
                command=EXPECTED_GATE_SPECS["full_unit_integration_gate"]["command"],
                env=env,
                expected_head=head,
                expected_fingerprint=fingerprint,
            )
        )

    if packet["reviewed_head"] != head:
        errors.append("reviewed_head does not match current HEAD")
    if packet["reviewed_diff_sha256"] != fingerprint:
        errors.append("reviewed_diff_sha256 does not match the exact staged diff")

    return errors


def check_commit_readiness(env: dict[str, str]) -> int:
    print("Checking machine-readable commit readiness...")
    try:
        packet = load_readiness_packet()
        errors = validate_readiness_packet(packet, env)
    except ValueError as exc:
        errors = [str(exc)]

    if errors:
        for error in errors:
            print(f"❌ {error}")
        print("\nCOMMIT BLOCKED: Generate a fresh ignored readiness packet for the exact staged diff.")
        return 1
    print("✓ Commit-readiness packet matches the exact staged diff\n")
    return 0


def verify_venv_commands(env: dict[str, str]) -> int:
    python_path = resolve_command("python", env)
    pytest_path = resolve_command("pytest", env)
    expected_bin = str(get_givebutter_dir() / ".venv/bin")
    if not python_path or not pytest_path or not python_path.startswith(expected_bin) or not pytest_path.startswith(expected_bin):
        print("Error: python and pytest must resolve inside the Givebutter virtualenv", file=sys.stderr)
        return 1
    print(python_path)
    print(pytest_path)
    probe = subprocess.run(
        [str(get_venv_python()), "-c", "import sys, email_validator; print(sys.executable); print(email_validator.__version__)"],
        cwd=get_givebutter_dir(), env=env, check=False,
    )
    return probe.returncode


def main() -> int:
    env = build_env()
    try:
        mode = commit_mode(env)
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    print("\033[1;33mPre-commit: validating readiness, artifacts, and tests...\033[0m\n")
    if verify_venv_commands(env) != 0:
        return 1
    task_guard_result = run_task_untracked_guard()
    if task_guard_result is None or task_guard_result.returncode != 0:
        print("\n❌ COMMIT BLOCKED: Untracked task files must be removed or staged before committing.")
        return 1
    staged_tree_guard_result = run_staged_tree_integrity_guard()
    if staged_tree_guard_result is None or staged_tree_guard_result.returncode != 0:
        print("\n❌ COMMIT BLOCKED: Staged-tree integrity must pass before committing.")
        return 1
    if check_blocked_artifacts() != 0:
        return 1
    lane_guard = run_declared_lane_guard(env)
    if lane_guard is None or lane_guard.returncode != 0:
        print("\n❌ COMMIT BLOCKED: Declared lane scope guard failed.")
        return 1
    if mode == "heavy" and check_commit_readiness(env) != 0:
        return 1
    if mode == "normal":
        print("✓ Normal commit mode: readiness ledger and packet checks are opt-in\n")
    print("\n\033[0;32m✓ Pre-commit mechanical verification passed!\033[0m\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
