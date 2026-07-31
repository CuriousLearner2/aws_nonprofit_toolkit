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
from uuid import uuid4
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASK_ID = "HOUSEHOLDER-STATE-STORE-20260730"
SCHEMA_VERSION = 1
STATE_REL_PATH = Path("Givebutter/.artifacts/householder-task-state.json")
STATE_FIELDS = {
    "schema_version",
    "task_id",
    "state",
    "state_digest",
    "created_at",
    "updated_at",
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


def _digest(state: dict[str, Any]) -> str:
    payload = {key: value for key, value in state.items() if key != "state_digest"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _validate_state(state: dict[str, Any], *, allow_terminal: bool = False) -> None:
    missing = STATE_FIELDS - set(state)
    if missing:
        raise ValueError(f"state missing required fields: {', '.join(sorted(missing))}")
    if state["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported schema")
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
    for field in COUNTER_FIELDS:
        _ensure_counter(field, state[field])
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
    }


def initialize(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        if state_path().exists():
            raise ValueError("state already exists")
        return _write_state(_base_state(task_id))


def load(task_id: str) -> dict[str, Any]:
    with _exclusive_lock():
        state = _read_state()
        if state["task_id"] != task_id:
            raise ValueError("task_id mismatch")
        return state


def status(task_id: str) -> dict[str, Any]:
    state = load(task_id)
    report = {
        "schema_version": state["schema_version"],
        "task_id": state["task_id"],
        "state": state["state"],
        "counters": {field: state[field] for field in COUNTER_FIELDS},
    }
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
        else:  # pragma: no cover
            raise ValueError("unknown command")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
