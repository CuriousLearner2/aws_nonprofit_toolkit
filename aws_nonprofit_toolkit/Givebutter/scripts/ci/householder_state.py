#!/usr/bin/env python3
"""Task-state storage for Householder workflow tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

TASK_ID = "HOUSEHOLDER-STATE-TRANSITIONS-20260731"
SCHEMA_VERSION = 1
STATE_REL_PATH = Path("Givebutter/.artifacts/householder-task-state.json")
ALLOWED_BATCHES = ("primary", "implementation_repair", "test_harness_repair", "review_repair")
ALLOWED_FAILURE_TYPES = ("implementation", "test_harness", "review", "environment_only", "hard_stop")
ALLOWED_VERSIONS = ("ACCEPT", "REQUEST_CHANGES", "REJECT", "PASS", "FAIL")
STATE_FIELDS = {
    "schema_version",
    "task_id",
    "state",
    "state_digest",
    "created_at",
    "updated_at",
    "deadline_at",
    "primary_allowed",
    "primary_used",
    "implementation_repair_allowed",
    "implementation_repair_used",
    "test_harness_repair_allowed",
    "test_harness_repair_used",
    "review_repair_allowed",
    "review_repair_used",
    "focused_runs_allowed",
    "focused_runs_used",
    "review_cycles_allowed",
    "review_cycles_used",
    "active_batch",
    "focused_run_active",
    "failure_classified",
    "failure_type",
    "environment_retry_used",
    "review_active",
    "review_fingerprint",
    "acceptance_green",
    "terminal_reason",
}
COUNTER_FIELDS = (
    "primary_allowed",
    "primary_used",
    "implementation_repair_allowed",
    "implementation_repair_used",
    "test_harness_repair_allowed",
    "test_harness_repair_used",
    "review_repair_allowed",
    "review_repair_used",
    "focused_runs_allowed",
    "focused_runs_used",
    "review_cycles_allowed",
    "review_cycles_used",
)
BOOL_FIELDS = (
    "focused_run_active",
    "failure_classified",
    "environment_retry_used",
    "review_active",
    "acceptance_green",
)
ALLOWED_STATES = {"idle", "editing", "focused", "blocked", "review", "review_green", "terminal"}
REPAIR_FOR_FAILURE = {
    "implementation": "implementation_repair",
    "test_harness": "test_harness_repair",
    "review": "review_repair",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def state_path() -> Path:
    return repo_root() / STATE_REL_PATH


def archive_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return state_path().with_name(f"{state_path().stem}.{stamp}.{uuid4().hex}.archive.json")


def lock_path() -> Path:
    return state_path().with_name(f"{state_path().name}.lock")


def run_git(args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(["git", *args], cwd=repo_root(), capture_output=True, text=not binary, check=False)


def current_head() -> str:
    result = run_git(["rev-parse", "HEAD"])
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("unable to resolve HEAD")
    return result.stdout.strip()


def current_staged_fingerprint() -> str:
    result = run_git(["diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"], binary=True)
    if result.returncode != 0:
        raise ValueError("unable to read staged fingerprint")
    return hashlib.sha256(result.stdout).hexdigest()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ensure_counter(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _ensure_optional_text(name: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string or null")
    return value


def _ensure_bool(name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _deadline_exceeded(state: dict[str, Any]) -> bool:
    deadline_at = state.get("deadline_at")
    if deadline_at is None:
        return False
    return datetime.now(timezone.utc) >= _parse_utc(deadline_at)


def _remaining(allowed: int, used: int) -> int:
    return max(allowed - used, 0)


def _repair_batch_for_failure(failure_type: str | None) -> str | None:
    if failure_type is None:
        return None
    return REPAIR_FOR_FAILURE.get(failure_type)


def _validate_review_verdict(verdict: str) -> str:
    if verdict not in ("ACCEPT", "REQUEST_CHANGES", "REJECT"):
        raise ValueError("reviewer verdict must be ACCEPT, REQUEST_CHANGES, or REJECT")
    return verdict


def _validate_breaker_verdict(verdict: str) -> str:
    if verdict not in ("PASS", "FAIL"):
        raise ValueError("breaker verdict must be PASS or FAIL")
    return verdict


def _digest(state: dict[str, Any]) -> str:
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _validate_state(state: dict[str, Any], *, allow_terminal: bool = False) -> None:
    missing = STATE_FIELDS - set(state)
    if missing:
        raise ValueError(f"state missing required fields: {', '.join(sorted(missing))}")
    if state["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema")
    if state["state"] not in ALLOWED_STATES:
        raise ValueError("unsupported state")
    if state["state"] == "terminal" and not allow_terminal:
        raise ValueError("terminal state")
    if not isinstance(state["task_id"], str) or not state["task_id"]:
        raise ValueError("task_id must be a non-empty string")
    if not isinstance(state["state"], str) or not state["state"]:
        raise ValueError("state must be a non-empty string")
    if not isinstance(state["created_at"], str) or not state["created_at"]:
        raise ValueError("created_at must be a non-empty string")
    if not isinstance(state["updated_at"], str) or not state["updated_at"]:
        raise ValueError("updated_at must be a non-empty string")
    _ensure_optional_text("deadline_at", state["deadline_at"])
    for field in COUNTER_FIELDS:
        _ensure_counter(field, state[field])
    _ensure_optional_text("active_batch", state["active_batch"])
    if state["active_batch"] is not None and state["active_batch"] not in ALLOWED_BATCHES:
        raise ValueError("active_batch must be one of the allowed batches")
    for field in BOOL_FIELDS:
        _ensure_bool(field, state[field])
    _ensure_optional_text("failure_type", state["failure_type"])
    if state["failure_type"] is not None and state["failure_type"] not in ALLOWED_FAILURE_TYPES:
        raise ValueError("failure_type must be one of the allowed failure types")
    _ensure_optional_text("review_fingerprint", state["review_fingerprint"])
    _ensure_optional_text("terminal_reason", state["terminal_reason"])
    if state["state_digest"] != _digest(state):
        raise ValueError("state digest mismatch")


def _write_state(state: dict[str, Any]) -> dict[str, Any]:
    data = dict(state)
    data["updated_at"] = _utcnow()
    data["state_digest"] = _digest(data)
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    target = state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
            tmp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, target)
    except Exception:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        raise
    return data


@contextmanager
def _exclusive_lock():
    target = lock_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    handle = target.open("a+", encoding="utf-8")
    try:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - non-POSIX fallback
            pass
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except ImportError:  # pragma: no cover - non-POSIX fallback
            pass
        handle.close()


def _read_state(*, allow_terminal: bool = False) -> dict[str, Any]:
    path = state_path()
    if not path.exists():
        raise ValueError("state missing")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("state malformed") from exc
    if not isinstance(state, dict):
        raise ValueError("state malformed")
    _validate_state(state, allow_terminal=allow_terminal)
    return state


def _base_state(task_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "state": "idle",
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
        "deadline_at": None,
        "primary_allowed": 1,
        "primary_used": 0,
        "implementation_repair_allowed": 1,
        "implementation_repair_used": 0,
        "test_harness_repair_allowed": 1,
        "test_harness_repair_used": 0,
        "review_repair_allowed": 1,
        "review_repair_used": 0,
        "focused_runs_allowed": 4,
        "focused_runs_used": 0,
        "review_cycles_allowed": 2,
        "review_cycles_used": 0,
        "active_batch": None,
        "focused_run_active": False,
        "failure_classified": False,
        "failure_type": None,
        "environment_retry_used": False,
        "review_active": False,
        "review_fingerprint": None,
        "acceptance_green": False,
        "terminal_reason": None,
    }


def _reload_review_state(state: dict[str, Any]) -> dict[str, Any]:
    review_fingerprint = state["review_fingerprint"]
    if review_fingerprint is None:
        return state
    if review_fingerprint == current_staged_fingerprint():
        return state
    refreshed = dict(state)
    refreshed["review_active"] = False
    refreshed["acceptance_green"] = False
    refreshed["review_fingerprint"] = None
    if refreshed["state"] == "review_green":
        refreshed["state"] = "editing" if refreshed["active_batch"] else "idle"
    elif refreshed["state"] == "review":
        refreshed["state"] = "editing" if refreshed["active_batch"] else "idle"
    return refreshed


def _load_mutable_state(task_id: str) -> dict[str, Any]:
    state = _read_state(allow_terminal=True)
    if state["task_id"] != task_id:
        raise ValueError("task_id mismatch")
    return _reload_review_state(state)


def _write_mutable_state(state: dict[str, Any]) -> dict[str, Any]:
    return _write_state(state)


def _terminalize(state: dict[str, Any], reason: str) -> dict[str, Any]:
    terminal = dict(state)
    terminal["state"] = "terminal"
    terminal["terminal_reason"] = reason
    terminal["review_active"] = False
    terminal["acceptance_green"] = False
    terminal["review_fingerprint"] = None
    terminal["focused_run_active"] = False
    return terminal


def _deadline_guard(state: dict[str, Any]) -> None:
    if _deadline_exceeded(state):
        raise ValueError("deadline exceeded")


def _terminalize_if_deadline_exceeded(state: dict[str, Any]) -> None:
    if _deadline_exceeded(state):
        _write_mutable_state(_terminalize(state, "deadline exceeded"))
        raise ValueError("deadline exceeded")


def _require_writable(state: dict[str, Any]) -> None:
    if state["state"] == "terminal":
        raise ValueError(state["terminal_reason"] or "terminal state")
    if state["review_active"] and state["review_fingerprint"] == current_staged_fingerprint():
        raise ValueError("review frozen at current staged fingerprint")
    if state["acceptance_green"] and state["review_fingerprint"] == current_staged_fingerprint():
        raise ValueError("review frozen at current staged fingerprint")
    if state["focused_run_active"]:
        raise ValueError("focused run already active")
    if state["focused_runs_used"] >= state["focused_runs_allowed"]:
        raise ValueError("focused-run limit exceeded")
    if state["failure_classified"] is False and state["state"] == "blocked":
        raise ValueError("classification required after failed focused run")


def _remaining_report(state: dict[str, Any]) -> dict[str, int]:
    return {
        "primary_batches": _remaining(state["primary_allowed"], state["primary_used"]),
        "implementation_repairs": _remaining(state["implementation_repair_allowed"], state["implementation_repair_used"]),
        "test_harness_repairs": _remaining(state["test_harness_repair_allowed"], state["test_harness_repair_used"]),
        "review_repairs": _remaining(state["review_repair_allowed"], state["review_repair_used"]),
        "focused_runs": _remaining(state["focused_runs_allowed"], state["focused_runs_used"]),
        "review_cycles": _remaining(state["review_cycles_allowed"], state["review_cycles_used"]),
        "environment_retries": 0 if state["environment_retry_used"] else 1,
    }


def _report_view(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": state["schema_version"],
        "task_id": state["task_id"],
        "state": state["state"],
        "active_batch": state["active_batch"],
        "focused_run_active": state["focused_run_active"],
        "failure_classified": state["failure_classified"],
        "failure_type": state["failure_type"],
        "environment_retry_used": state["environment_retry_used"],
        "review_active": state["review_active"],
        "review_fingerprint": state["review_fingerprint"],
        "acceptance_green": state["acceptance_green"],
        "terminal_reason": state["terminal_reason"],
        "deadline_at": state["deadline_at"],
        "counters": {field: state[field] for field in COUNTER_FIELDS},
        "remaining": _remaining_report(state),
    }


def _begin_batch(state: dict[str, Any], batch: str) -> dict[str, Any]:
    if batch not in ALLOWED_BATCHES:
        raise ValueError("unknown batch")
    if state["state"] == "terminal":
        raise ValueError(state["terminal_reason"] or "terminal state")
    if batch == "primary":
        if state["active_batch"] is not None:
            raise ValueError("duplicate primary batch")
        if state["primary_used"] >= state["primary_allowed"]:
            terminal = _terminalize(state, "primary batch exhausted")
            _write_mutable_state(terminal)
            raise ValueError("primary batch exhausted")
        state["primary_used"] += 1
    else:
        if not state["failure_classified"]:
            raise ValueError("classification required after failed focused run")
        expected = _repair_batch_for_failure(state["failure_type"])
        if expected != batch:
            raise ValueError("wrong repair batch")
        used_field = f"{batch}_used"
        allowed_field = f"{batch}_allowed"
        if state[used_field] >= state[allowed_field]:
            terminal = _terminalize(state, "repair batch exhausted")
            _write_mutable_state(terminal)
            raise ValueError("repair batch exhausted")
        state[used_field] += 1
    state["active_batch"] = batch
    state["state"] = "editing"
    state["focused_run_active"] = False
    state["environment_retry_used"] = False
    state["terminal_reason"] = None
    return state


def _can_begin_focused_run(state: dict[str, Any]) -> tuple[bool, str]:
    if state["state"] == "terminal":
        return False, state["terminal_reason"] or "terminal state"
    if state["review_active"] and state["review_fingerprint"] == current_staged_fingerprint():
        return False, "review frozen at current staged fingerprint"
    if state["acceptance_green"] and state["review_fingerprint"] == current_staged_fingerprint():
        return False, "review frozen at current staged fingerprint"
    if not state["active_batch"]:
        return False, "no active batch"
    if state["focused_run_active"]:
        return False, "focused run already active"
    if state["focused_runs_used"] >= state["focused_runs_allowed"]:
        return False, "focused-run limit exceeded"
    if state["state"] == "blocked" and not state["failure_classified"]:
        return False, "classification required after failed focused run"
    if state["environment_retry_used"] and not state["failure_classified"]:
        return False, "environment retry already used"
    if state["failure_classified"]:
        if state["failure_type"] == "environment_only":
            if state["environment_retry_used"]:
                return False, "environment retry already used"
            return True, ""
        expected = _repair_batch_for_failure(state["failure_type"])
        if state["active_batch"] != expected:
            return False, "repair batch required"
    return True, ""


def _can_write(state: dict[str, Any]) -> tuple[bool, str]:
    if state["state"] == "terminal":
        return False, state["terminal_reason"] or "terminal state"
    if state["review_active"] and state["review_fingerprint"] == current_staged_fingerprint():
        return False, "review frozen at current staged fingerprint"
    if state["acceptance_green"] and state["review_fingerprint"] == current_staged_fingerprint():
        return False, "review frozen at current staged fingerprint"
    if state["focused_run_active"]:
        return False, "focused run already active"
    if state["focused_runs_used"] >= state["focused_runs_allowed"]:
        return False, "focused-run limit exceeded"
    if state["state"] == "blocked" and not state["failure_classified"]:
        return False, "classification required after failed focused run"
    if state["failure_classified"]:
        if state["failure_type"] == "environment_only":
            return False, "environment retry is focused only"
        expected = _repair_batch_for_failure(state["failure_type"])
        if state["active_batch"] != expected:
            return False, "repair batch required"
    return True, ""


def _success(state: dict[str, Any]) -> dict[str, Any]:
    return _write_mutable_state(state)


def begin_edit(task_id: str, batch: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _load_mutable_state(task_id)
        _deadline_guard(state)
        if state["focused_runs_used"] >= state["focused_runs_allowed"]:
            _write_mutable_state(_terminalize(state, "focused-run limit exceeded"))
            raise ValueError("focused-run limit exceeded")
        _require_writable(state)
        updated = _begin_batch(state, batch)
        return _success(updated)


def begin_focused_run(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _load_mutable_state(task_id)
        _deadline_guard(state)
        allowed, reason = _can_begin_focused_run(state)
        if not allowed:
            if reason == "focused-run limit exceeded":
                _write_mutable_state(_terminalize(state, reason))
            raise ValueError(reason)
        state["focused_run_active"] = True
        state["focused_runs_used"] += 1
        if state["failure_classified"] and state["failure_type"] == "environment_only":
            state["environment_retry_used"] = True
        state["state"] = "focused"
        return _success(state)


def finish_focused_run(task_id: str, exit_code: int) -> dict[str, Any]:
    with _exclusive_lock():
        state = _load_mutable_state(task_id)
        _terminalize_if_deadline_exceeded(state)
        if not state["focused_run_active"]:
            raise ValueError("no active focused run")
        state["focused_run_active"] = False
        if exit_code == 0:
            state["failure_classified"] = False
            state["failure_type"] = None
            state["state"] = "editing"
            return _success(state)
        state["state"] = "blocked"
        state["failure_classified"] = False
        state["failure_type"] = None
        state["acceptance_green"] = False
        state["review_active"] = False
        state["review_fingerprint"] = None
        if state["focused_runs_used"] >= state["focused_runs_allowed"]:
            return _write_mutable_state(_terminalize(state, "focused-run limit exceeded"))
        return _write_mutable_state(state)


def classify_failure(task_id: str, failure_type: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _load_mutable_state(task_id)
        if state["state"] != "blocked" or state["failure_classified"]:
            raise ValueError("no failed focused run to classify")
        if failure_type not in ALLOWED_FAILURE_TYPES:
            raise ValueError("unknown failure type")
        if failure_type == "hard_stop":
            return _write_mutable_state(_terminalize(state, "hard stop classified"))
        state["failure_classified"] = True
        state["failure_type"] = failure_type
        state["state"] = "blocked"
        if failure_type == "environment_only":
            state["environment_retry_used"] = False
        return _success(state)


def begin_review(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _load_mutable_state(task_id)
        _deadline_guard(state)
        if state["state"] == "terminal":
            raise ValueError(state["terminal_reason"] or "terminal state")
        if not state["active_batch"]:
            raise ValueError("no active batch")
        if state["state"] == "blocked" and not state["failure_classified"]:
            raise ValueError("classification required after failed focused run")
        if state["failure_classified"] and state["failure_type"] == "environment_only":
            raise ValueError("environment retry required before review")
        if state["failure_classified"] and state["failure_type"] == "review" and state["active_batch"] != "review_repair":
            raise ValueError("review repair batch required")
        if state["failure_classified"]:
            raise ValueError("repair batch required")
        if state["acceptance_green"] and state["review_fingerprint"] == current_staged_fingerprint():
            raise ValueError("review frozen at current staged fingerprint")
        if state["review_active"] and state["review_fingerprint"] == current_staged_fingerprint():
            raise ValueError("review already active")
        if state["review_cycles_used"] >= state["review_cycles_allowed"]:
            return _write_mutable_state(_terminalize(state, "review-cycle limit exceeded"))
        state["review_cycles_used"] += 1
        state["review_active"] = True
        state["acceptance_green"] = False
        state["review_fingerprint"] = current_staged_fingerprint()
        state["state"] = "review"
        return _success(state)


def finish_review(task_id: str, reviewer_verdict: str, breaker_verdict: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _read_state(allow_terminal=True)
        if state["task_id"] != task_id:
            raise ValueError("task_id mismatch")
        reviewer_verdict = _validate_review_verdict(reviewer_verdict)
        breaker_verdict = _validate_breaker_verdict(breaker_verdict)
        _terminalize_if_deadline_exceeded(state)
        if not state["review_active"]:
            raise ValueError("no active review")
        if state["review_fingerprint"] != current_staged_fingerprint():
            raise ValueError("staged fingerprint changed during review")
        state["review_active"] = False
        if reviewer_verdict == "ACCEPT" and breaker_verdict == "PASS":
            state["acceptance_green"] = True
            state["state"] = "review_green"
            return _success(state)
        state["acceptance_green"] = False
        state["failure_classified"] = True
        state["failure_type"] = "review"
        state["state"] = "blocked"
        return _success(state)


def can_write(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _load_mutable_state(task_id)
        allowed, reason = _can_write(state)
        report = _report_view(state)
        report.update({"allowed": allowed, "reason": None if allowed else reason})
        return report


def can_run_focused(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _load_mutable_state(task_id)
        allowed, reason = _can_begin_focused_run(state)
        report = _report_view(state)
        report.update({"allowed": allowed, "reason": None if allowed else reason})
        if not allowed:
            raise ValueError(reason)
        return report


def initialize(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        if state_path().exists():
            existing = _read_state(allow_terminal=True)
            if existing["task_id"] == task_id:
                raise ValueError("state already exists")
            archive = archive_path()
            archive.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return _write_state(_base_state(task_id))


def load(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _read_state()
        if state["task_id"] != task_id:
            raise ValueError("task_id mismatch")
        return state


def status(task_id: str) -> dict[str, Any]:
    state = load(task_id)
    report = _report_view(state)
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def reset(task_id: str, authorized_reset: bool) -> dict[str, Any]:
    if not authorized_reset:
        raise ValueError("authorized reset required")
    with _exclusive_lock():
        existing = _read_state(allow_terminal=True)
        if existing["task_id"] != task_id:
            raise ValueError("task_id mismatch")
        archive = archive_path()
        archive.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return _write_state(_base_state(task_id))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="householder_state.py")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("initialize")
    init.add_argument("--task-id", required=True)

    status_cmd = sub.add_parser("status")
    status_cmd.add_argument("--task-id", required=True)

    reset_cmd = sub.add_parser("reset")
    reset_cmd.add_argument("--task-id", required=True)
    reset_cmd.add_argument("--authorized-reset", action="store_true", required=True)

    begin_edit_cmd = sub.add_parser("begin-edit")
    begin_edit_cmd.add_argument("--task-id", required=True)
    begin_edit_cmd.add_argument("--batch", required=True)

    begin_focused_run_cmd = sub.add_parser("begin-focused-run")
    begin_focused_run_cmd.add_argument("--task-id", required=True)

    finish_focused_run_cmd = sub.add_parser("finish-focused-run")
    finish_focused_run_cmd.add_argument("--task-id", required=True)
    finish_focused_run_cmd.add_argument("--exit-code", required=True, type=int)

    classify_cmd = sub.add_parser("classify-failure")
    classify_cmd.add_argument("--task-id", required=True)
    classify_cmd.add_argument("--type", required=True)

    begin_review_cmd = sub.add_parser("begin-review")
    begin_review_cmd.add_argument("--task-id", required=True)

    finish_review_cmd = sub.add_parser("finish-review")
    finish_review_cmd.add_argument("--task-id", required=True)
    finish_review_cmd.add_argument("--reviewer", required=True)
    finish_review_cmd.add_argument("--breaker", required=True)

    can_write_cmd = sub.add_parser("can-write")
    can_write_cmd.add_argument("--task-id", required=True)

    can_run_cmd = sub.add_parser("can-run-focused")
    can_run_cmd.add_argument("--task-id", required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "initialize":
            initialize(args.task_id)
        elif args.command == "status":
            status(args.task_id)
        elif args.command == "reset":
            reset(args.task_id, args.authorized_reset)
        elif args.command == "begin-edit":
            begin_edit(args.task_id, args.batch)
        elif args.command == "begin-focused-run":
            begin_focused_run(args.task_id)
        elif args.command == "finish-focused-run":
            finish_focused_run(args.task_id, args.exit_code)
        elif args.command == "classify-failure":
            classify_failure(args.task_id, args.type)
        elif args.command == "begin-review":
            begin_review(args.task_id)
        elif args.command == "finish-review":
            finish_review(args.task_id, args.reviewer, args.breaker)
        elif args.command == "can-write":
            report = can_write(args.task_id)
            print(json.dumps(report, indent=2, sort_keys=True))
        elif args.command == "can-run-focused":
            report = can_run_focused(args.task_id)
            print(json.dumps(report, indent=2, sort_keys=True))
        else:  # pragma: no cover
            raise ValueError("unknown command")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
