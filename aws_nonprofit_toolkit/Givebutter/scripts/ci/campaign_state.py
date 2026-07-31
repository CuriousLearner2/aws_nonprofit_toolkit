#!/usr/bin/env python3
"""Validate frozen campaign authorization against the exact staged Git scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any
TASK_ID = "MACHINE-ENFORCED-CAMPAIGN-STATE-20260730"
AUTHORIZATION_DIR = Path("Givebutter/.claude/task-authorizations")
AUTHORIZATION_PATH = AUTHORIZATION_DIR / f"{TASK_ID}.json"
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]
def authorization_path(task_id: str = TASK_ID) -> Path:
    cleaned = task_id.strip()
    if cleaned != task_id or not cleaned or "/" in cleaned or "\\" in cleaned: raise ValueError("authorization task ID mismatch")
    return AUTHORIZATION_DIR / f"{cleaned}.json"
def auth_file(task_id: str = TASK_ID) -> Path:
    return repo_root() / authorization_path(task_id)
def run_git(args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(["git", *args], cwd=repo_root(), capture_output=True, text=not binary, check=False)
def freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(freeze(v) for v in value)
    return value
def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
def git_blob_hash(spec: str) -> str:
    result = run_git(["rev-parse", spec])
    blob = result.stdout.strip()
    if result.returncode != 0 or not blob:
        raise ValueError(f"unable to resolve git blob: {spec}")
    return blob
def git_blob_bytes(spec: str) -> bytes:
    result = run_git(["show", spec], binary=True)
    if result.returncode != 0:
        raise ValueError(f"unable to read git blob: {spec}")
    return result.stdout
def normalize(path: str) -> str:
    cleaned = path.replace("\\", "/").removeprefix("./").strip(); prefix = f"{repo_root().name}/"
    return cleaned[len(prefix):] if cleaned.startswith(prefix) else cleaned

def _head_auth_intro_commit(pathspec: str) -> str:
    result = run_git(["log", "--diff-filter=A", "--format=%H", "--", pathspec])
    if result.returncode != 0:
        raise ValueError("authorization introduction commit not found")
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not commits:
        raise ValueError("authorization introduction commit not found")
    return commits[0]

def _authorization_facts(task_id: str) -> dict[str, Any]:
    path = auth_file(task_id)
    pathspec = str(authorization_path(task_id))
    object_path = str(Path(repo_root().name) / authorization_path(task_id))
    if not path.exists():
        raise ValueError(f"authorization file missing: {path}")
    head_tree = run_git(["ls-tree", "--full-name", "HEAD", "--", pathspec])
    if head_tree.returncode != 0 or not head_tree.stdout.strip():
        raise ValueError(f"authorization file must exist in HEAD: {path}")
    tracked = run_git(["ls-files", "--error-unmatch", "--", pathspec])
    if tracked.returncode != 0:
        raise ValueError(f"authorization file must be tracked: {path}")
    head_blob = git_blob_hash(f"HEAD:{object_path}")
    try:
        index_blob = git_blob_hash(f":0:{object_path}")
    except ValueError as exc:
        raise ValueError("authorization staged content mismatch") from exc
    if index_blob != head_blob:
        raise ValueError("authorization staged content mismatch")
    head_bytes = git_blob_bytes(f"HEAD:{object_path}")
    index_bytes = git_blob_bytes(f":0:{object_path}")
    if index_bytes != head_bytes:
        raise ValueError("authorization staged content mismatch")
    worktree_bytes = path.read_bytes()
    if worktree_bytes != head_bytes:
        raise ValueError("authorization working tree content mismatch")
    committed_sha256 = hashlib.sha256(head_bytes).hexdigest()
    if sha256_file(path) != committed_sha256:
        raise ValueError("authorization SHA-256 mismatch")
    intro_commit = _head_auth_intro_commit(pathspec)
    if run_git(["merge-base", "--is-ancestor", intro_commit, "HEAD"]).returncode != 0:
        raise ValueError("authorization commit is not an ancestor of HEAD")
    return {"path": path, "sha256": committed_sha256, "git_blob": head_blob, "introduction_commit": intro_commit}

def load_authorization(task_id: str = TASK_ID) -> MappingProxyType[str, Any]:
    path = auth_file(task_id)
    if not path.exists():
        raise ValueError(f"authorization file missing: {path}")
    auth = read_json(path)
    if not isinstance(auth, dict):
        raise ValueError("authorization must be a JSON object")
    if auth.get("task_id") != task_id or auth.get("campaign_id") != task_id:
        raise ValueError("authorization task ID mismatch")
    _authorization_facts(task_id)
    return freeze(auth)

def _staged_entries() -> list[tuple[str, str, str | None]]:
    result = run_git(["diff", "--cached", "--name-status", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"])
    if result.returncode != 0:
        raise ValueError("unable to inspect staged scope")
    entries: list[tuple[str, str, str | None]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status[0] in {"R", "C"} and len(parts) >= 3:
            entries.append((status[0], normalize(parts[2]), normalize(parts[1])))
        elif len(parts) >= 2:
            entries.append((status[0], normalize(parts[1]), None))
    return entries


def _numstat() -> dict[str, tuple[int, int]]:
    result = run_git(["diff", "--cached", "--numstat", "--find-renames", "--find-copies", "--find-copies-harder", "--diff-filter=ACDMRT"])
    if result.returncode != 0:
        raise ValueError("unable to count staged lines")
    counts: dict[str, tuple[int, int]] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        added, deleted, path = line.split("\t", 2)
        if added == "-" or deleted == "-":
            raise ValueError("binary or uncountable change staged")
        counts[normalize(path.split(" => ", 1)[-1])] = (int(added), int(deleted))
    return counts


def _category(path: str, auth: MappingProxyType[str, Any]) -> str | None:
    impl = set(auth["authorized_implementation_files"]) | set(auth.get("authorized_optional_implementation_files", ()))
    tests = set(auth["authorized_test_files"])
    if path in impl:
        return "implementation"
    if path in tests:
        return "test"
    return None


def collect_scope_report(task_id: str) -> dict[str, Any]:
    auth = load_authorization(task_id)
    facts = _authorization_facts(task_id)
    staged = _staged_entries()
    counts = _numstat()
    head = run_git(["rev-parse", "HEAD"]).stdout.strip()
    fingerprint = run_git(["diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"], binary=True).stdout
    auth_path = normalize(str(authorization_path(task_id)))
    impl_files: list[str] = []
    test_files: list[str] = []
    impl_added = impl_deleted = test_added = test_deleted = 0
    deleted_files = additions = modifications = renames = copies = 0
    for status, path, old_path in staged:
        if path == auth_path or old_path == auth_path:
            raise ValueError("authorization file may not be staged")
        category = _category(path, auth)
        old_category = _category(old_path, auth) if old_path else category
        if status[0] in {"R", "C"}:
            if category is None or old_category is None:
                raise ValueError(f"rename/copy must stay within authorized scope: {old_path} -> {path}")
            if old_category != category:
                raise ValueError(f"mixed-scope staged path: {old_path} -> {path}")
            target_category = category
        else:
            if category is None and old_category is None:
                raise ValueError(f"unauthorized staged path: {path}")
            if old_category and category and old_category != category:
                raise ValueError(f"mixed-scope staged path: {old_path} -> {path}")
            target_category = category or old_category
        target = path if status != "D" else old_path or path
        added, deleted = counts.get(path, counts.get(old_path or path, (0, 0)))
        if target_category == "implementation":
            impl_files.append(target)
            impl_added += added
            impl_deleted += deleted
        else:
            test_files.append(target)
            test_added += added
            test_deleted += deleted
        additions += status == "A"
        modifications += status == "M"
        renames += status[0] == "R"
        copies += status[0] == "C"
        deleted_files += status == "D"
    report = {
        "task_id": task_id,
        "head": head,
        "staged_diff_sha256": hashlib.sha256(fingerprint).hexdigest(),
        "authorization": {
            "task_id": auth["task_id"],
            "sha256": facts["sha256"],
            "git_blob": facts["git_blob"],
            "ancestor_commit": facts["introduction_commit"],
        },
        "implementation_files": tuple(sorted(set(impl_files))),
        "test_files": tuple(sorted(set(test_files))),
        "implementation_file_count": len(set(impl_files)),
        "test_file_count": len(set(test_files)),
        "implementation_line_budget": {"inserted": impl_added, "deleted": impl_deleted, "actual": impl_added + impl_deleted, "allowed": auth["implementation_line_budget"]},
        "test_line_budget": {"inserted": test_added, "deleted": test_deleted, "actual": test_added + test_deleted, "allowed": auth["test_line_budget"]},
        "remaining_budgets": {
            "implementation_files": auth["maximum_implementation_files"] - len(set(impl_files)),
            "test_files": auth["maximum_test_files"] - len(set(test_files)),
            "implementation_lines": auth["implementation_line_budget"] - (impl_added + impl_deleted),
            "test_lines": auth["test_line_budget"] - (test_added + test_deleted),
        },
        "status_counts": {"additions": additions, "modifications": modifications, "renames": renames, "copies": copies, "deletions": deleted_files},
    }
    if report["implementation_file_count"] > auth["maximum_implementation_files"]:
        raise ValueError("implementation file budget exceeded")
    if report["test_file_count"] > auth["maximum_test_files"]:
        raise ValueError("test file budget exceeded")
    if report["implementation_line_budget"]["actual"] > auth["implementation_line_budget"]:
        raise ValueError("implementation line budget exceeded")
    if report["test_line_budget"]["actual"] > auth["test_line_budget"]:
        raise ValueError("test line budget exceeded")
    return report


def print_report(report: dict[str, Any]) -> None:
    print(f"task_id: {report['task_id']}")
    print(f"head: {report['head']}")
    print(f"staged_diff_sha256: {report['staged_diff_sha256']}")
    print(f"implementation_files ({report['implementation_file_count']}): {', '.join(report['implementation_files']) or 'none'}")
    print(f"test_files ({report['test_file_count']}): {', '.join(report['test_files']) or 'none'}")
    print(
        "implementation_lines: "
        f"+{report['implementation_line_budget']['inserted']} -{report['implementation_line_budget']['deleted']} "
        f"(actual {report['implementation_line_budget']['actual']}, remaining {report['remaining_budgets']['implementation_lines']})"
    )
    print(
        "test_lines: "
        f"+{report['test_line_budget']['inserted']} -{report['test_line_budget']['deleted']} "
        f"(actual {report['test_line_budget']['actual']}, remaining {report['remaining_budgets']['test_lines']})"
    )
    print(f"remaining_file_budgets: implementation={report['remaining_budgets']['implementation_files']} test={report['remaining_budgets']['test_files']}")
    print(
        "counts: "
        f"additions={report['status_counts']['additions']} modifications={report['status_counts']['modifications']} "
        f"renames={report['status_counts']['renames']} copies={report['status_counts']['copies']} deletions={report['status_counts']['deletions']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="campaign_state.py")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate-scope")
    validate.add_argument("--task-id", required=True)
    args = parser.parse_args(argv)
    try:
        report = collect_scope_report(args.task_id)
        print_report(report)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
