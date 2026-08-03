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
    raise ValueError("legacy repo-local campaign state is disabled; use the external ledger")


def campaign_status(task_id: str) -> dict[str, Any]:
    raise ValueError("legacy repo-local campaign state is disabled; use the external ledger")


# External stateful ledger surface. Legacy repo-local state APIs are disabled.
LEDGER_ROOT = Path("/private/tmp/householder-campaigns")
CAMPAIGN_STATES = {"READY", "ACTIVE", "VALIDATING", "COMMITTED", "FAILED", "QUARANTINED", "STOPPED"}
CAMPAIGN_TERMINAL = {"COMMITTED", "FAILED", "QUARANTINED", "STOPPED"}


def _ledger_file(campaign_id: str) -> Path:
    return LEDGER_ROOT / _validate_task_id(campaign_id) / "state.json"


@contextmanager
def _ledger_lock(campaign_id: str):
    file = _ledger_file(campaign_id)
    file.parent.mkdir(parents=True, exist_ok=True)
    lock = file.with_name(".state.lock").open("a+", encoding="utf-8")
    try:
        import fcntl
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        import fcntl
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def _ledger_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _ledger_identity(repo: Path) -> tuple[str, bool, str]:
    return (
        _ledger_git(repo, "rev-parse", "HEAD"),
        bool(_ledger_git(repo, "status", "--porcelain", "--untracked-files=all")),
        _ledger_git(repo, "hash-object", str(repo / "scripts/ci/architecture_slice_gate.py")),
    )


def _ledger_contract(path: str, expected: str) -> dict[str, str]:
    file = Path(path).resolve()
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("contract unreadable") from exc
    if _json_sha256(payload) != expected:
        raise ValueError("contract digest mismatch")
    return {"path": str(file), "sha256": expected}


def _ledger_load(campaign_id: str) -> dict[str, Any]:
    try:
        record = json.loads(_ledger_file(campaign_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("ledger missing or malformed") from exc
    if not isinstance(record, dict) or record.get("campaign_id") != campaign_id:
        raise ValueError("ledger malformed")
    if record.get("state") not in CAMPAIGN_STATES or not record.get("contracts"):
        raise ValueError("ledger malformed")
    if not isinstance(record.get("current_index"), int) or not 0 <= record["current_index"] <= len(record["contracts"]):
        raise ValueError("ledger malformed")
    pending = record.get("pending_action")
    if pending is not None:
        if not isinstance(pending, dict) or pending.get("contract_index") != record["current_index"]:
            raise ValueError("ledger malformed")
        expected_kind = "IMPLEMENT" if record["state"] == "ACTIVE" else "VALIDATE"
        if record["state"] not in {"ACTIVE", "VALIDATING"} or pending.get("kind") != expected_kind:
            raise ValueError("ledger malformed")
    if record["state"] == "READY" and record["current_index"] != 0:
        raise ValueError("ledger malformed")
    if record["state"] == "COMMITTED" and record["current_index"] != len(record["contracts"]):
        raise ValueError("ledger malformed")
    if _json_sha256(record["contracts"]) != record.get("contract_queue_sha256"):
        raise ValueError("contract queue digest mismatch")
    return record


def _ledger_validate(record: dict[str, Any], expected_commit: str | None = None) -> tuple[str, str]:
    repo = Path(record["repo_path"]).resolve()
    head, dirty, gate = _ledger_identity(repo)
    if dirty:
        raise ValueError("worktree dirty")
    if gate != record["gate_blob_sha"]:
        raise ValueError("gate blob mismatch")
    for item in record["contracts"]:
        _ledger_contract(item["path"], item["sha256"])
    if head != record["current_head"] and head != expected_commit:
        raise ValueError("stale HEAD")
    return head, gate


def campaign_ledger_init(campaign_id: str, repo: str | Path, gate_blob_sha: str, contracts: list[dict[str, str]]) -> dict[str, Any]:
    campaign_id = _validate_task_id(campaign_id)
    repo = Path(repo).resolve()
    if not contracts:
        raise ValueError("contract queue must not be empty")
    with _ledger_lock(campaign_id):
        file = _ledger_file(campaign_id)
        if file.exists():
            raise ValueError("campaign already initialized")
        head, dirty, gate = _ledger_identity(repo)
        if dirty:
            raise ValueError("worktree dirty")
        if gate != gate_blob_sha:
            raise ValueError("gate blob mismatch")
        queue = [_ledger_contract(item["path"], item["sha256"]) for item in contracts]
        record = {
            "schema_version": 1, "campaign_id": campaign_id, "repo_path": str(repo),
            "starting_head": head, "current_head": head, "gate_blob_sha": gate_blob_sha,
            "contracts": queue, "contract_queue_sha256": _json_sha256(queue),
            "start_time": _utcnow(), "state": "READY", "current_index": 0,
            "pending_action": None, "results": [], "stop_reason": None,
        }
        _write_atomic_json(file, record)
        return record


def campaign_ledger_status(campaign_id: str) -> dict[str, Any]:
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        _ledger_validate(record)
        return record


def campaign_ledger_next(campaign_id: str) -> dict[str, Any]:
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        _ledger_validate(record)
        if record["state"] in CAMPAIGN_TERMINAL:
            return {"action": "STOP", "state": record["state"]}
        if record["pending_action"] is not None:
            raise ValueError("repeated next transition")
        item = record["contracts"][record["current_index"]]
        kind = "IMPLEMENT" if record["state"] == "READY" else "VALIDATE"
        record["state"] = "ACTIVE" if kind == "IMPLEMENT" else "VALIDATING"
        record["pending_action"] = {"kind": kind, "contract_index": record["current_index"], "contract": item}
        _write_atomic_json(_ledger_file(campaign_id), record)
        return record["pending_action"]


def campaign_ledger_record_result(campaign_id: str, result: dict[str, Any]) -> dict[str, Any]:
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        commit = result.get("commit_sha")
        _ledger_validate(record, commit if isinstance(commit, str) else None)
        pending = record.get("pending_action")
        allowed = {"contract_index", "gate_pass", "tests_pass", "patch_sha", "commit_sha"}
        if not pending or result.get("contract_index") != pending["contract_index"] or set(result) != allowed:
            raise ValueError("no matching pending action")
        if not isinstance(result["gate_pass"], bool) or not isinstance(result["tests_pass"], bool):
            raise ValueError("gate_pass and tests_pass must be boolean")
        if not all(isinstance(result[key], str) and result[key] for key in ("patch_sha", "commit_sha")):
            raise ValueError("patch_sha and commit_sha required")
        repo = Path(record["repo_path"]).resolve()
        if result["commit_sha"] != _ledger_git(repo, "rev-parse", "HEAD"):
            raise ValueError("commit SHA does not match HEAD")
        record["results"].append({"action": pending["kind"], **result})
        record["pending_action"] = None
        record["current_head"] = result["commit_sha"]
        if not result["gate_pass"] or not result["tests_pass"]:
            record["state"], record["stop_reason"] = "FAILED", "gate or tests failed"
        elif pending["kind"] == "IMPLEMENT":
            record["state"] = "VALIDATING"
        else:
            record["current_index"] += 1
            record["state"] = "COMMITTED" if record["current_index"] == len(record["contracts"]) else "ACTIVE"
        _write_atomic_json(_ledger_file(campaign_id), record)
        return record


def _campaign_terminal(campaign_id: str, state: str, reason: str) -> dict[str, Any]:
    if not reason or not reason.strip():
        raise ValueError("reason required")
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        _ledger_validate(record)
        if record["state"] in CAMPAIGN_TERMINAL:
            raise ValueError("terminal transition repeated")
        record["state"], record["stop_reason"] = state, reason
        record["pending_action"] = None
        _write_atomic_json(_ledger_file(campaign_id), record)
        return record


def campaign_ledger_quarantine(campaign_id: str, reason: str) -> dict[str, Any]:
    return _campaign_terminal(campaign_id, "QUARANTINED", reason)


def campaign_ledger_stop(campaign_id: str, reason: str) -> dict[str, Any]:
    return _campaign_terminal(campaign_id, "STOPPED", reason)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Stateful external campaign ledger")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("campaign_id"); init.add_argument("repo"); init.add_argument("gate_blob_sha")
    init.add_argument("contract", nargs="+", help="contract.json=sha256")
    for name in ("status", "next"):
        commands.add_parser(name).add_argument("campaign_id")
    result = commands.add_parser("record-result")
    result.add_argument("campaign_id"); result.add_argument("contract_index", type=int)
    result.add_argument("gate_pass", type=lambda value: value.lower() == "true")
    result.add_argument("tests_pass", type=lambda value: value.lower() == "true")
    result.add_argument("patch_sha"); result.add_argument("commit_sha")
    for name in ("quarantine", "stop"):
        command = commands.add_parser(name); command.add_argument("campaign_id"); command.add_argument("reason")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            queue = [dict(zip(("path", "sha256"), item.rsplit("=", 1))) for item in args.contract]
            value = campaign_ledger_init(args.campaign_id, args.repo, args.gate_blob_sha, queue)
        elif args.command == "status": value = campaign_ledger_status(args.campaign_id)
        elif args.command == "next": value = campaign_ledger_next(args.campaign_id)
        elif args.command == "record-result":
            value = campaign_ledger_record_result(args.campaign_id, {
                "contract_index": args.contract_index, "gate_pass": args.gate_pass,
                "tests_pass": args.tests_pass, "patch_sha": args.patch_sha, "commit_sha": args.commit_sha,
            })
        elif args.command == "quarantine": value = campaign_ledger_quarantine(args.campaign_id, args.reason)
        else: value = campaign_ledger_stop(args.campaign_id, args.reason)
        print(json.dumps(value, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
