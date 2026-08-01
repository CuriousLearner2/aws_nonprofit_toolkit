#!/usr/bin/env python3
"""Isolated worktree runner for Householder campaigns."""

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


SCHEMA_VERSION = 1
TASK_BRANCH_PREFIX = "codex/"
STATE_DIR = Path("Givebutter/.artifacts")
ALLOWED_RUNTIME_ROOTS = ("Givebutter/.artifacts/", "Givebutter/exports_uat/", ".DS_Store")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _record_path(task_id: str) -> Path:
    return repo_root() / STATE_DIR / f"householder-runner.{task_id}.json"


def _lock_path(task_id: str) -> Path:
    return _record_path(task_id).with_name(_record_path(task_id).name + ".lock")


def _task_branch(task_id: str) -> str:
    return f"{TASK_BRANCH_PREFIX}{task_id}"


def _validate_task_id(task_id: str) -> str:
    cleaned = task_id.strip()
    if cleaned != task_id or not cleaned or "/" in cleaned or "\\" in cleaned:
        raise ValueError("task_id must be a non-empty string without path separators")
    return cleaned


def run_git(args: list[str], *, cwd: Path | None = None, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd or repo_root(),
        capture_output=True,
        text=not binary,
        check=False,
    )


def _git_output(args: list[str], *, cwd: Path | None = None, binary: bool = False) -> str:
    result = run_git(args, cwd=cwd, binary=binary)
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed")
    if binary:
        raise TypeError("binary output requested from _git_output")
    return result.stdout


def _current_branch(cwd: Path) -> str:
    branch = _git_output(["branch", "--show-current"], cwd=cwd).strip()
    if not branch:
        raise ValueError("detached HEAD is not allowed")
    return branch


def _status_entries(cwd: Path) -> list[tuple[str, str]]:
    result = run_git(["status", "--porcelain", "--untracked-files=all"], cwd=cwd)
    if result.returncode != 0:
        raise ValueError("git status failed")
    entries: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip()
        entries.append((status, path))
    return entries


def _is_allowed_runtime_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return (
        normalized == ".DS_Store"
        or normalized.endswith("/.DS_Store")
        or normalized.startswith("Givebutter/.artifacts/")
        or normalized.startswith("Givebutter/exports_uat/")
    )


def _is_clean_worktree(cwd: Path) -> bool:
    for status, path in _status_entries(cwd):
        if status == "??":
            if not _is_allowed_runtime_path(path):
                return False
            continue
        return False
    return True


def _worktree_python(worktree: Path) -> Path:
    candidate = worktree / "Givebutter" / "venv" / "bin" / "python"
    return candidate if candidate.exists() else Path(sys.executable)


def _ledger_script(worktree: Path) -> Path:
    return worktree / "Givebutter" / "scripts" / "ci" / "householder_state.py"


def run_householder_state(worktree: Path, args: list[str], *, json_output: bool = True) -> Any:
    command = [str(_worktree_python(worktree)), str(_ledger_script(worktree)), *args]
    result = subprocess.run(command, cwd=worktree, capture_output=True, text=True, shell=False, check=False)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or result.stdout.strip() or "householder_state command failed")
    if not json_output:
        return result
    if not result.stdout.strip():
        raise ValueError("householder_state command produced no JSON")
    return json.loads(result.stdout)


def _main_status(report_root: Path, base_sha: str) -> dict[str, Any]:
    head = _git_output(["rev-parse", "HEAD"], cwd=report_root).strip()
    origin_main = _git_output(["rev-parse", "origin/main"], cwd=report_root).strip()
    tracked_clean = run_git(["status", "--short", "--untracked-files=no"], cwd=report_root).stdout.strip() == ""
    return {
        "head": head,
        "origin_main": origin_main,
        "base_sha": base_sha,
        "tracked_clean": tracked_clean,
        "main_unchanged": head == origin_main == base_sha and tracked_clean,
    }


def _record_exists(task_id: str) -> bool:
    return _record_path(task_id).exists()


def _load_record(task_id: str) -> dict[str, Any]:
    path = _record_path(task_id)
    if not path.exists():
        raise ValueError("task record missing")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("task record malformed") from exc
    if not isinstance(record, dict):
        raise ValueError("task record malformed")
    expected_keys = {
        "schema_version",
        "task_id",
        "branch",
        "worktree_parent",
        "worktree_path",
        "base_sha",
        "created_at",
    }
    missing = expected_keys - set(record)
    if missing:
        raise ValueError("task record missing required fields")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported task record schema")
    if record["task_id"] != task_id:
        raise ValueError("task_id mismatch")
    if record["branch"] != _task_branch(task_id):
        raise ValueError("branch mismatch")
    return record


def _write_record(record: dict[str, Any]) -> dict[str, Any]:
    path = _record_path(record["task_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            tmp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except OSError:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        raise
    return record


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


def _ensure_worktree_parent_allowed(parent: Path) -> None:
    root = repo_root().resolve()
    resolved = parent.resolve()
    if not resolved.is_relative_to(root):
        return
    relative = resolved.relative_to(root)
    if run_git(["check-ignore", "-q", "--", str(relative)]).returncode == 0:
        return
    raise ValueError("worktree parent must be outside the repository tracked tree or ignored")


def _ensure_main_ready(base_sha: str) -> None:
    root = repo_root()
    current_branch = _current_branch(root)
    if current_branch != "main":
        raise ValueError("create must run from main")
    main_status = _main_status(root, base_sha)
    if not main_status["main_unchanged"]:
        raise ValueError("clean main and origin/main must match HEAD")


def _ensure_no_duplicates(task_id: str, worktree_path: Path, branch: str) -> None:
    if _record_exists(task_id):
        raise ValueError("duplicate task")
    if run_git(["branch", "--list", branch]).stdout.strip():
        raise ValueError("duplicate branch")
    for line in run_git(["worktree", "list", "--porcelain"]).stdout.splitlines():
        if line.startswith("worktree "):
            existing = Path(line.split(" ", 1)[1].strip()).resolve()
            if existing == worktree_path.resolve():
                raise ValueError("duplicate worktree")


def _current_worktree_for_task(task_id: str) -> Path:
    record = _load_record(task_id)
    worktree = Path(record["worktree_path"]).resolve()
    cwd = Path.cwd().resolve()
    if cwd != worktree and worktree not in cwd.parents:
        raise ValueError("must run from recorded worktree")
    if _current_branch(cwd) != record["branch"]:
        raise ValueError("wrong branch")
    return worktree


def _worktree_is_clean(worktree: Path) -> bool:
    result = run_git(["status", "--short", "--untracked-files=no"], cwd=worktree)
    if result.returncode != 0:
        raise ValueError("git status failed")
    return result.stdout.strip() == ""


def _branch_ahead_count(branch: str) -> int:
    result = run_git(["rev-list", "--count", f"origin/main..{branch}"], cwd=repo_root())
    if result.returncode != 0:
        raise ValueError("unable to compare branch with origin/main")
    return int(result.stdout.strip() or "0")


def _ensure_main_unchanged_for_record(record: dict[str, Any]) -> dict[str, Any]:
    status = _main_status(repo_root(), record["base_sha"])
    if not status["main_unchanged"]:
        raise ValueError("main branch changed")
    return status


def _ledger_before_after(worktree: Path, task_id: str, command: str, *args: str) -> tuple[dict[str, Any], dict[str, Any]]:
    before = run_householder_state(worktree, [command, "--task-id", task_id, *args], json_output=True)
    after = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
    return before, after


def _staged_diff_sha256(worktree: Path) -> str:
    result = run_git(["diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"], cwd=worktree, binary=True)
    if result.returncode != 0:
        raise ValueError("unable to read staged fingerprint")
    stdout = result.stdout if isinstance(result.stdout, bytes) else b""
    return hashlib.sha256(stdout).hexdigest()


def _staged_files(worktree: Path) -> list[str]:
    result = run_git(["diff", "--cached", "--name-only"], cwd=worktree)
    if result.returncode != 0:
        raise ValueError("unable to read staged files")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _staged_fingerprint_and_files(worktree: Path) -> tuple[str, list[str]]:
    return _staged_diff_sha256(worktree), _staged_files(worktree)


def _update_record(task_id: str, **updates: Any) -> dict[str, Any]:
    record = _load_record(task_id)
    record.update(updates)
    return _write_record(record)


def _require_frozen_review_context(task_id: str, worktree: Path) -> tuple[dict[str, Any], str, list[str]]:
    record = _load_record(task_id)
    fingerprint = _staged_diff_sha256(worktree)
    staged_files = _staged_files(worktree)
    frozen_fingerprint = record.get("frozen_staged_fingerprint")
    if frozen_fingerprint is not None and frozen_fingerprint != fingerprint:
        raise ValueError("staged fingerprint changed")
    frozen_files = record.get("frozen_staged_files")
    if frozen_files is not None and frozen_files != staged_files:
        raise ValueError("staged files changed")
    return record, fingerprint, staged_files


def _validate_receipt_snapshot(
    receipt: Any,
    *,
    field: str,
    task_id: str,
    fingerprint: str,
    expected_status: str,
    require_review_fields: bool = False,
) -> dict[str, Any]:
    if not isinstance(receipt, dict):
        raise ValueError(f"{field} receipt is required")
    if receipt.get("task_id") != task_id:
        raise ValueError(f"{field} receipt task_id mismatch")
    if receipt.get("frozen_staged_fingerprint") != fingerprint:
        raise ValueError(f"{field} receipt frozen_staged_fingerprint mismatch")
    if receipt.get("status") != expected_status:
        raise ValueError(f"{field} receipt must be {expected_status}")
    if require_review_fields:
        if receipt.get("reviewer_result") != "ACCEPT":
            raise ValueError("reviewer result must be ACCEPT")
        if receipt.get("breaker_result") != "PASS":
            raise ValueError("breaker result must be PASS")
    return dict(receipt)


def _validate_delivery_receipts(record: dict[str, Any], *, fingerprint: str) -> None:
    required = {
        "focused_receipt": "passed",
        "full_gate_receipt": "passed",
        "review_receipt": "review_green",
        "runtime_evidence_receipt": "passed",
        "readiness_receipt": "passed",
        "pre_commit_receipt": "passed",
    }
    for field, status in required.items():
        receipt = record.get(field)
        if field == "review_receipt":
            _validate_receipt_snapshot(
                receipt,
                field=field,
                task_id=record["task_id"],
                fingerprint=fingerprint,
                expected_status=status,
                require_review_fields=True,
            )
            continue
        _validate_receipt_snapshot(
            receipt,
            field=field,
            task_id=record["task_id"],
            fingerprint=fingerprint,
            expected_status=status,
        )


def start_review(task_id: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    with _record_lock(task_id):
        record = _load_record(task_id)
        worktree = _current_worktree_for_task(task_id)
        _ensure_main_unchanged_for_record(record)
        before = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        auth = run_householder_state(worktree, ["can-write", "--task-id", task_id], json_output=True)
        if not auth.get("allowed"):
            raise ValueError(auth.get("reason") or "authorization denied")
        run_householder_state(worktree, ["begin-review", "--task-id", task_id], json_output=False)
        after = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        frozen_staged_fingerprint, frozen_staged_files = _staged_fingerprint_and_files(worktree)
        updated = _update_record(
            task_id,
            frozen_staged_fingerprint=frozen_staged_fingerprint,
            frozen_staged_files=frozen_staged_files,
            review_started_at=_utcnow(),
        )
        return {
            "task_id": task_id,
            "frozen_staged_fingerprint": frozen_staged_fingerprint,
            "frozen_staged_files": frozen_staged_files,
            "ledger_before": before,
            "ledger_after": after,
            **updated,
        }


def finish_review(task_id: str, reviewer_verdict: str, breaker_verdict: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    if reviewer_verdict != "ACCEPT":
        raise ValueError("reviewer result must be ACCEPT")
    if breaker_verdict != "PASS":
        raise ValueError("breaker result must be PASS")
    with _record_lock(task_id):
        record = _load_record(task_id)
        worktree = _current_worktree_for_task(task_id)
        _ensure_main_unchanged_for_record(record)
        record, fingerprint, _ = _require_frozen_review_context(task_id, worktree)
        before = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        run_householder_state(worktree, ["finish-review", "--task-id", task_id, "--reviewer", "ACCEPT", "--breaker", "PASS"], json_output=False)
        after = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        updated = _update_record(
            task_id,
            frozen_staged_fingerprint=fingerprint,
            reviewer_verdict=reviewer_verdict,
            breaker_verdict=breaker_verdict,
            review_finished_at=_utcnow(),
        )
        return {
            "task_id": task_id,
            "reviewer_verdict": reviewer_verdict,
            "breaker_verdict": breaker_verdict,
            "reviewer_result": reviewer_verdict,
            "breaker_result": breaker_verdict,
            "ledger_before": before,
            "ledger_after": after,
            **updated,
        }


def authorize_delivery(task_id: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    with _record_lock(task_id):
        record = _load_record(task_id)
        worktree = _current_worktree_for_task(task_id)
        main_status = _ensure_main_unchanged_for_record(record)
        ledger_state = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        if ledger_state.get("state") != "review_green" or ledger_state.get("acceptance_green") is not True:
            raise ValueError("review_green required for delivery")
        if record.get("frozen_staged_fingerprint") is None:
            raise ValueError("review_green required for delivery")
        fingerprint, _ = _staged_fingerprint_and_files(worktree)
        if record.get("frozen_staged_fingerprint") != fingerprint:
            raise ValueError("staged fingerprint changed")
        _validate_delivery_receipts(record, fingerprint=fingerprint)
        return {
            "task_id": task_id,
            "allowed": True,
            "frozen_staged_fingerprint": fingerprint,
            "ledger_state": ledger_state,
            **main_status,
            **record,
        }


def cleanup(task_id: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    with _record_lock(task_id):
        record = _load_record(task_id)
        worktree = _current_worktree_for_task(task_id)
        _ensure_main_unchanged_for_record(record)
        if not _worktree_is_clean(worktree):
            raise ValueError("dirty worktree")
        if _branch_ahead_count(record["branch"]) > 0:
            raise ValueError("unpushed worktree")
        run_git(["worktree", "remove", "--force", str(worktree)], cwd=repo_root())
        record_path = _record_path(task_id)
        if record_path.exists():
            record_path.unlink()
        return {
            "task_id": task_id,
            "removed_worktree": str(worktree),
        }


def create(task_id: str, worktree_parent: Path | str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    parent = Path(worktree_parent)
    branch = _task_branch(task_id)
    worktree_path = (parent / task_id).resolve()
    with _record_lock(task_id):
        base_sha = _git_output(["rev-parse", "HEAD"], cwd=repo_root()).strip()
        origin_main = _git_output(["rev-parse", "origin/main"], cwd=repo_root()).strip()
        if base_sha != origin_main:
            raise ValueError("HEAD and origin/main must match")
        _ensure_main_ready(base_sha)
        _ensure_worktree_parent_allowed(parent)
        _ensure_no_duplicates(task_id, worktree_path, branch)
        parent.mkdir(parents=True, exist_ok=True)
        created = False
        try:
            result = run_git(["worktree", "add", "-b", branch, str(worktree_path), base_sha], cwd=repo_root())
            if result.returncode != 0:
                raise ValueError(result.stderr.strip() or result.stdout.strip() or "worktree creation failed")
            created = True
            run_householder_state(worktree_path, ["initialize", "--task-id", task_id], json_output=False)
            ledger_state = run_householder_state(worktree_path, ["status", "--task-id", task_id], json_output=True)
            record = _write_record(
                {
                    "schema_version": SCHEMA_VERSION,
                    "task_id": task_id,
                    "branch": branch,
                    "worktree_parent": str(parent.resolve()),
                    "worktree_path": str(worktree_path),
                    "base_sha": base_sha,
                    "created_at": _utcnow(),
                }
            )
            return {
                **record,
                "ledger_state": ledger_state,
                "main_unchanged": True,
            }
        except (ValueError, subprocess.CalledProcessError, OSError):
            if created:
                run_git(["worktree", "remove", "--force", str(worktree_path)], cwd=repo_root())
                run_git(["branch", "-D", branch], cwd=repo_root())
            raise


def status(task_id: str) -> dict[str, Any]:
    with _record_lock(_validate_task_id(task_id)):
        record = _load_record(task_id)
        worktree = _current_worktree_for_task(task_id)
        main_status = _ensure_main_unchanged_for_record(record)
        ledger_state = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        return {
            **record,
            "current_branch": _current_branch(worktree),
            "worktree_clean": _is_clean_worktree(worktree),
            "ledger_state": ledger_state,
            **main_status,
        }


def start_edit(task_id: str, batch: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    with _record_lock(task_id):
        record = _load_record(task_id)
        worktree = _current_worktree_for_task(task_id)
        _ensure_main_unchanged_for_record(record)
        before = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        auth = run_householder_state(worktree, ["can-write", "--task-id", task_id], json_output=True)
        if not auth.get("allowed"):
            raise ValueError(auth.get("reason") or "authorization denied")
        run_householder_state(worktree, ["begin-edit", "--task-id", task_id, "--batch", batch], json_output=False)
        after = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        counter_map = {
            "primary": "primary_used",
            "implementation_repair": "implementation_repair_used",
            "test_harness_repair": "test_harness_repair_used",
            "review_repair": "review_repair_used",
        }
        counter = counter_map.get(batch)
        if counter is None:
            raise ValueError("unknown batch")
        if after["state"] != "editing" or after["active_batch"] != batch:
            raise ValueError("partial ledger transition")
        if after["counters"][counter] != before["counters"][counter] + 1:
            raise ValueError("partial ledger transition")
        return {
            "task_id": task_id,
            "batch": batch,
            "ledger_before": before,
            "ledger_after": after,
            **record,
        }


def run_focused(task_id: str, command: list[str]) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    if not command:
        raise ValueError("focused command required")
    if command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("focused command required")
    with _record_lock(task_id):
        record = _load_record(task_id)
        worktree = _current_worktree_for_task(task_id)
        _ensure_main_unchanged_for_record(record)
        before = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        auth = run_householder_state(worktree, ["can-run-focused", "--task-id", task_id], json_output=True)
        if not auth.get("allowed"):
            raise ValueError(auth.get("reason") or "authorization denied")
        run_householder_state(worktree, ["begin-focused-run", "--task-id", task_id], json_output=False)
        exit_code = 127
        stdout = ""
        stderr = ""
        try:
            result = subprocess.run(command, cwd=worktree, capture_output=True, text=True, shell=False, check=False)
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except FileNotFoundError as exc:
            exit_code = 127
            stderr = str(exc)
        run_householder_state(worktree, ["finish-focused-run", "--task-id", task_id, "--exit-code", str(exit_code)], json_output=False)
        after = run_householder_state(worktree, ["status", "--task-id", task_id], json_output=True)
        if after["focused_run_active"]:
            raise ValueError("partial ledger transition")
        if after["counters"]["focused_runs_used"] != before["counters"]["focused_runs_used"] + 1:
            raise ValueError("partial ledger transition")
        return {
            "task_id": task_id,
            "command": tuple(command),
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "ledger_before": before,
            "ledger_after": after,
            **record,
        }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="householder_runner.py")
    sub = parser.add_subparsers(dest="command", required=True)

    create_cmd = sub.add_parser("create")
    create_cmd.add_argument("--task-id", required=True)
    create_cmd.add_argument("--worktree-parent", required=True)

    status_cmd = sub.add_parser("status")
    status_cmd.add_argument("--task-id", required=True)

    start_cmd = sub.add_parser("start-edit")
    start_cmd.add_argument("--task-id", required=True)
    start_cmd.add_argument("--batch", required=True)

    focused_cmd = sub.add_parser("run-focused")
    focused_cmd.add_argument("--task-id", required=True)
    focused_cmd.add_argument("command", nargs=argparse.REMAINDER)

    start_review_cmd = sub.add_parser("start-review")
    start_review_cmd.add_argument("--task-id", required=True)

    finish_review_cmd = sub.add_parser("finish-review")
    finish_review_cmd.add_argument("--task-id", required=True)
    finish_review_cmd.add_argument("--reviewer", required=True)
    finish_review_cmd.add_argument("--breaker", required=True)

    authorize_cmd = sub.add_parser("authorize-delivery")
    authorize_cmd.add_argument("--task-id", required=True)

    cleanup_cmd = sub.add_parser("cleanup")
    cleanup_cmd.add_argument("--task-id", required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "create":
            result = create(args.task_id, Path(args.worktree_parent))
        elif args.command == "status":
            result = status(args.task_id)
        elif args.command == "start-edit":
            result = start_edit(args.task_id, args.batch)
        elif args.command == "run-focused":
            result = run_focused(args.task_id, args.command)
        elif args.command == "start-review":
            result = start_review(args.task_id)
        elif args.command == "finish-review":
            result = finish_review(args.task_id, args.reviewer, args.breaker)
        elif args.command == "authorize-delivery":
            result = authorize_delivery(args.task_id)
        elif args.command == "cleanup":
            result = cleanup(args.task_id)
        else:  # pragma: no cover
            raise ValueError("unknown command")
        print(json.dumps(result, indent=2, sort_keys=True))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
