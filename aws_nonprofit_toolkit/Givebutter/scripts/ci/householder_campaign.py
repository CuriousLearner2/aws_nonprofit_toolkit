#!/usr/bin/env python3
"""Immutable campaign-contract storage for Householder."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 1
STATE_DIR = Path("Givebutter/.artifacts")
STATE_PREFIX = "householder-campaign"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_task_id(task_id: str) -> str:
    cleaned = task_id.strip()
    if cleaned != task_id or not cleaned or "/" in cleaned or "\\" in cleaned:
        raise ValueError("task_id must be a non-empty string without path separators")
    return cleaned


def _record_path(task_id: str) -> Path:
    return repo_root() / STATE_DIR / f"{STATE_PREFIX}.{task_id}.json"


def _lock_path(task_id: str) -> Path:
    return _record_path(task_id).with_name(_record_path(task_id).name + ".lock")


@contextmanager
def _record_lock(task_id: str):
    lock_path = _lock_path(task_id)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
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


def _git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd or repo_root(), capture_output=True, text=True, check=False)


def _git_output(args: list[str], *, cwd: Path | None = None) -> str:
    result = _git(args, cwd=cwd)
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed")
    return result.stdout


def _current_branch(cwd: Path) -> str:
    branch = _git_output(["branch", "--show-current"], cwd=cwd).strip()
    if not branch:
        raise ValueError("detached HEAD is not allowed")
    return branch


def _json_sha256(payload: Any) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _digest_contract(contract: dict[str, Any]) -> dict[str, Any]:
    digest_contract = dict(contract)
    digest_contract.pop("campaign_type", None)
    return digest_contract


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _normalize_authorized_file(value: Any) -> str:
    cleaned = _require_string(value, "authorized_files entry")
    if cleaned.startswith(("/", "./")) or "\\" in cleaned:
        raise ValueError("authorized_files must be normalized")
    path = PurePosixPath(cleaned)
    if path.as_posix() != cleaned or any(part == ".." for part in path.parts):
        raise ValueError("authorized_files must be normalized")
    return cleaned


def _normalize_work_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("work_items must contain objects")
    required = {"id", "type", "description", "acceptance_criteria", "focused_test_commands", "allowed_action_types"}
    missing = required - set(item)
    if missing:
        raise ValueError("work item missing required fields")
    acceptance = item["acceptance_criteria"]
    commands = item["focused_test_commands"]
    actions = item["allowed_action_types"]
    if not isinstance(acceptance, list) or not acceptance:
        raise ValueError("acceptance_criteria must be a non-empty list")
    if not isinstance(commands, list) or not commands:
        raise ValueError("focused_test_commands must be a non-empty list")
    if not isinstance(actions, list) or not actions:
        raise ValueError("allowed_action_types must be a non-empty list")
    normalized_commands: list[list[str]] = []
    for command in commands:
        if not isinstance(command, list) or not command:
            raise ValueError("focused_test_commands must contain command lists")
        normalized_commands.append([_require_string(part, "focused_test_commands entry") for part in command])
    return {
        "id": _require_string(item["id"], "work_item id"),
        "type": _require_string(item["type"], "work_item type"),
        "description": _require_string(item["description"], "work_item description"),
        "acceptance_criteria": [_require_string(entry, "acceptance_criteria entry") for entry in acceptance],
        "focused_test_commands": normalized_commands,
        "allowed_action_types": [_require_string(entry, "allowed_action_types entry") for entry in actions],
    }


def _normalize_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ValueError("campaign contract must be an object")
    required = {
        "schema_version",
        "task_id",
        "campaign_type",
        "workflow_id",
        "strategy_id",
        "work_items",
        "authorized_files",
        "implementation_changed_lines_max",
        "test_changed_lines_max",
        "tracked_files_max",
        "focused_runs_max",
        "implementation_repairs_max",
        "test_harness_repairs_max",
        "review_repairs_max",
    }
    missing = required - set(contract)
    if missing:
        raise ValueError("campaign contract missing required fields")
    if contract["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported campaign contract schema")
    work_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_item in contract["work_items"]:
        item = _normalize_work_item(raw_item)
        if item["id"] in seen_ids:
            raise ValueError("duplicate work-item IDs")
        seen_ids.add(item["id"])
        work_items.append(item)
    files: list[str] = []
    seen_files: set[str] = set()
    for raw in contract["authorized_files"]:
        path = _normalize_authorized_file(raw)
        if path in seen_files:
            raise ValueError("duplicate authorized_files")
        seen_files.add(path)
        files.append(path)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": _validate_task_id(_require_string(contract["task_id"], "task_id")),
        "campaign_type": _require_string(contract["campaign_type"], "campaign_type"),
        "workflow_id": _require_string(contract["workflow_id"], "workflow_id"),
        "strategy_id": _require_string(contract["strategy_id"], "strategy_id"),
        "work_items": work_items,
        "authorized_files": files,
        "implementation_changed_lines_max": _require_int(contract["implementation_changed_lines_max"], "implementation_changed_lines_max"),
        "test_changed_lines_max": _require_int(contract["test_changed_lines_max"], "test_changed_lines_max"),
        "tracked_files_max": _require_int(contract["tracked_files_max"], "tracked_files_max"),
        "focused_runs_max": _require_int(contract["focused_runs_max"], "focused_runs_max"),
        "implementation_repairs_max": _require_int(contract["implementation_repairs_max"], "implementation_repairs_max"),
        "test_harness_repairs_max": _require_int(contract["test_harness_repairs_max"], "test_harness_repairs_max"),
        "review_repairs_max": _require_int(contract["review_repairs_max"], "review_repairs_max"),
    }


def _load_record(task_id: str) -> dict[str, Any]:
    path = _record_path(task_id)
    if not path.exists():
        raise ValueError("campaign record missing")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("campaign record malformed") from exc
    if not isinstance(record, dict):
        raise ValueError("campaign record malformed")
    required = {
        "schema_version",
        "task_id",
        "branch",
        "worktree_path",
        "head_sha",
        "main_sha",
        "contract",
        "contract_sha256",
        "current_work_item_index",
        "work_item_statuses",
        "counters",
        "pending_action",
        "final_state",
        "stop_reason",
        "created_at",
    }
    missing = required - set(record)
    if missing:
        raise ValueError("campaign record missing required fields")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported campaign record schema")
    if record["task_id"] != task_id:
        raise ValueError("task_id mismatch")
    normalized = _normalize_contract(record["contract"])
    if normalized != record["contract"]:
        raise ValueError("stored contract mutated")
    if _json_sha256(_digest_contract(normalized)) != record["contract_sha256"]:
        raise ValueError("contract digest mismatch")
    if not isinstance(record["work_item_statuses"], list) or len(record["work_item_statuses"]) != len(normalized["work_items"]):
        raise ValueError("campaign record malformed")
    if not isinstance(record["counters"], dict):
        raise ValueError("campaign record malformed")
    return record


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            tmp_path = Path(handle.name)
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except OSError:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        raise


def _current_identity() -> dict[str, str]:
    root = repo_root()
    return {
        "branch": _current_branch(root),
        "worktree_path": str(Path.cwd().resolve()),
        "head_sha": _git_output(["rev-parse", "HEAD"], cwd=root).strip(),
        "main_sha": _git_output(["rev-parse", "origin/main"], cwd=root).strip(),
    }


def _initialize_record(task_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    identity = _current_identity()
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        **identity,
        "contract": contract,
        "contract_sha256": _json_sha256(_digest_contract(contract)),
        "current_work_item_index": 0,
        "work_item_statuses": ["pending" for _ in contract["work_items"]],
        "counters": {
            "focused_runs_used": 0,
            "implementation_repairs_used": 0,
            "review_repairs_used": 0,
            "test_harness_repairs_used": 0,
        },
        "pending_action": None,
        "final_state": "active",
        "stop_reason": None,
        "created_at": _utcnow(),
    }


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {**record, "campaign_type": record["contract"]["campaign_type"]}


def campaign_initialize(task_id: str, contract_file: Path | str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    contract_path = Path(contract_file)
    with _record_lock(task_id):
        path = _record_path(task_id)
        if path.exists():
            raise ValueError("reinitialization rejected")
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("campaign contract malformed") from exc
        normalized = _normalize_contract(contract)
        if normalized["task_id"] != task_id:
            raise ValueError("task_id mismatch")
        _write_atomic_json(path, _initialize_record(task_id, normalized))
        return _public_record(_load_record(task_id))


def campaign_status(task_id: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    with _record_lock(task_id):
        record = _load_record(task_id)
        identity = _current_identity()
        if record["branch"] != identity["branch"]:
            raise ValueError("branch mismatch")
        if record["worktree_path"] != identity["worktree_path"]:
            raise ValueError("worktree mismatch")
        if record["head_sha"] != identity["head_sha"] or record["main_sha"] != identity["main_sha"]:
            raise ValueError("repository identity mismatch")
        return _public_record(record)
