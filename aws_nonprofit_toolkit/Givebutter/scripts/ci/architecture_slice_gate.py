#!/usr/bin/env python3
"""Reusable architecture-slice gate for Householder-style contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
GATE_RELATIVE_PATH = "scripts/ci/architecture_slice_gate.py"
GATE_TEST_RELATIVE_PATH = "tests/unit/test_architecture_slice_gate.py"
REQUIRED_FIELDS = {
    "task_id",
    "baseline_ref",
    "seam",
    "authorized_files",
    "allowed_new_production_files",
    "production_changed_lines_max",
    "test_changed_lines_max",
    "forbidden_files",
    "forbidden_imports",
    "forbidden_symbols",
    "required_test_commands",
    "gate_blob_sha",
}
ALLOWED_TOP_LEVEL_FIELDS = REQUIRED_FIELDS | {"schema_version"}


def _run_git(args: list[str], cwd: Path, *, check: bool = True, text: bool = True) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=text,
        check=check,
    )


def _duplicate_key_object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate contract key: {key}")
        obj[key] = value
    return obj


def _load_contract(contract_path: Path) -> Any:
    try:
        return json.loads(contract_path.read_text(encoding="utf-8"), object_pairs_hook=_duplicate_key_object_pairs_hook)
    except json.JSONDecodeError as exc:
        raise ValueError(str(exc)) from exc


def _git_repo_root(start: Path | None = None) -> Path:
    cwd = Path(start or Path.cwd())
    result = _run_git(["rev-parse", "--show-toplevel"], cwd, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("ambiguous repo roots or not in a git repository")
    return Path(result.stdout.strip()).resolve()


def _canonicalize_path(value: str) -> str:
    text = value.replace("\\", "/").strip()
    if not text:
        raise ValueError("path entries must be non-empty strings")
    if text.startswith("./"):
        text = text[2:]
    if text.startswith("/"):
        text = text[1:]
    parts = [part for part in text.split("/") if part and part != "."]
    if any(part == ".." for part in parts):
        raise ValueError(f"invalid path traversal in contract: {value!r}")
    return "/".join(parts)


def _normalize_unique_strings(values: Any, field: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field} must be a JSON array")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"{field} entries must be strings")
        item = _canonicalize_path(value)
        if item in seen:
            raise ValueError(f"{field} entries must be unique")
        seen.add(item)
        normalized.append(item)
    if not allow_empty and not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def _normalize_text_entries(values: Any, field: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{field} must be a JSON array")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} entries must be non-empty strings")
        item = value.strip()
        if item in seen:
            raise ValueError(f"{field} entries must be unique")
        seen.add(item)
        normalized.append(item)
    return normalized


def _normalize_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ValueError("contract must be a JSON object")
    unexpected = sorted(set(contract) - ALLOWED_TOP_LEVEL_FIELDS)
    if unexpected:
        raise ValueError(f"contract contains unknown fields: {', '.join(unexpected)}")
    missing = sorted(REQUIRED_FIELDS - contract.keys())
    if missing:
        raise ValueError(f"contract is missing required fields: {', '.join(missing)}")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version {contract.get('schema_version')!r}")

    normalized = dict(contract)
    normalized["task_id"] = str(contract["task_id"]).strip()
    normalized["baseline_ref"] = str(contract["baseline_ref"]).strip()
    normalized["seam"] = str(contract["seam"]).strip()
    if not normalized["task_id"] or not normalized["baseline_ref"] or not normalized["seam"]:
        raise ValueError("task_id, baseline_ref, and seam must be non-empty strings")

    normalized["authorized_files"] = _normalize_unique_strings(contract["authorized_files"], "authorized_files")
    normalized["allowed_new_production_files"] = _normalize_unique_strings(
        contract["allowed_new_production_files"],
        "allowed_new_production_files",
    )
    normalized["production_changed_lines_max"] = _coerce_positive_int(
        contract["production_changed_lines_max"],
        "production_changed_lines_max",
    )
    normalized["test_changed_lines_max"] = _coerce_positive_int(
        contract["test_changed_lines_max"],
        "test_changed_lines_max",
    )
    normalized["forbidden_files"] = _normalize_unique_strings(contract["forbidden_files"], "forbidden_files")
    normalized["forbidden_imports"] = _normalize_text_entries(contract["forbidden_imports"], "forbidden_imports")
    normalized["forbidden_symbols"] = _normalize_text_entries(contract["forbidden_symbols"], "forbidden_symbols")
    normalized["required_test_commands"] = _normalize_text_entries(
        contract["required_test_commands"],
        "required_test_commands",
    )
    normalized["gate_blob_sha"] = str(contract["gate_blob_sha"]).strip()
    if len(normalized["gate_blob_sha"]) != 40 or any(c not in "0123456789abcdef" for c in normalized["gate_blob_sha"]):
        raise ValueError("gate_blob_sha must be a git blob SHA-1 hex digest")

    if not set(normalized["allowed_new_production_files"]).issubset(normalized["authorized_files"]):
        raise ValueError("allowed_new_production_files must be a subset of authorized_files")

    return normalized


def _coerce_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _canonical_contract_sha(contract: dict[str, Any]) -> str:
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha(path: Path) -> str:
    result = _run_git(["hash-object", str(path)], path.parent if path.is_file() else Path.cwd(), check=False)
    if result.returncode != 0:
        raise ValueError(f"unable to hash gate blob at {path}")
    return result.stdout.strip()


def _parse_status_lines(repo_root: Path) -> list[tuple[str, str]]:
    result = _run_git(["status", "--porcelain=v1", "--untracked-files=all"], repo_root, check=False)
    if result.returncode != 0:
        raise ValueError("unable to inspect repository status")

    entries: list[tuple[str, str]] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line:
            continue
        status = raw_line[:2]
        payload = raw_line[3:] if len(raw_line) > 3 else ""
        if status[0] in {"R", "C"}:
            raise ValueError("renames and copies are not supported")
        entries.append((status, payload.strip()))
    return entries


def _read_file_lines(path: Path) -> int:
    data = path.read_bytes()
    if b"\0" in data:
        raise ValueError(f"binary file not supported: {path.as_posix()}")
    return len(data.splitlines())


def _tracked_numstat(repo_root: Path, baseline_ref: str, paths: list[str]) -> dict[str, tuple[int, int]]:
    if not paths:
        return {}
    result = _run_git(
        ["diff", "--numstat", "--no-ext-diff", baseline_ref, "--", *paths],
        repo_root,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"baseline reference not found: {baseline_ref}")
    counts: dict[str, tuple[int, int]] = {}
    for line in result.stdout.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise ValueError("binary changes and renames are not supported")
        added, deleted, path = parts
        if added == "-" or deleted == "-":
            raise ValueError("binary changes are not supported")
        if "->" in path or "=>" in path:
            raise ValueError("renames are not supported")
        counts[path] = (int(added), int(deleted))
    return counts


def _classify_path(path: str) -> str:
    if path.startswith("tests/"):
        return "test"
    return "production"


def evaluate_contract(
    contract_path: Path,
    contract_sha: str,
    *,
    gate_path: Path | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    repo_root = _git_repo_root(cwd)
    loaded = _load_contract(Path(contract_path))
    normalized = _normalize_contract(loaded)
    computed_contract_sha = _canonical_contract_sha(normalized)
    if computed_contract_sha != contract_sha:
        raise ValueError("contract digest mismatch")

    gate_path = gate_path or Path(__file__)
    computed_gate_blob_sha = _git_blob_sha(gate_path)
    if computed_gate_blob_sha != normalized["gate_blob_sha"]:
        raise ValueError("gate blob digest mismatch")

    changed = _parse_status_lines(repo_root)
    blocked_files = set(normalized["forbidden_files"]) | {GATE_RELATIVE_PATH, GATE_TEST_RELATIVE_PATH}
    authorized = set(normalized["authorized_files"])
    allowed_new_production = set(normalized["allowed_new_production_files"])

    tracked_paths: list[str] = []
    file_entries: list[dict[str, Any]] = []
    violations: list[str] = []

    for status, path in changed:
        normalized_path = _canonicalize_path(path)
        if normalized_path in blocked_files:
            violations.append(f"forbidden file changed: {normalized_path}")
        if normalized_path not in authorized:
            violations.append(f"unauthorized file changed: {normalized_path}")
        if status.startswith("??"):
            if normalized_path in allowed_new_production and normalized_path not in authorized:
                violations.append(f"new production file not authorized: {normalized_path}")
            if normalized_path not in allowed_new_production and _classify_path(normalized_path) == "production":
                violations.append(f"new production file not allowed: {normalized_path}")
            additions = _read_file_lines(repo_root / normalized_path)
            deletions = 0
            file_entries.append({"path": normalized_path, "additions": additions, "deletions": deletions})
        else:
            tracked_paths.append(normalized_path)

    tracked_counts = _tracked_numstat(repo_root, normalized["baseline_ref"], tracked_paths)
    for path in tracked_paths:
        if path not in tracked_counts:
            violations.append(f"missing tracked diff stats for {path}")
            continue
        additions, deletions = tracked_counts[path]
        file_entries.append({"path": path, "additions": additions, "deletions": deletions})

    file_entries.sort(key=lambda item: item["path"])

    production_additions = production_deletions = test_additions = test_deletions = 0
    for entry in file_entries:
        category = _classify_path(entry["path"])
        if category == "test":
            test_additions += entry["additions"]
            test_deletions += entry["deletions"]
        else:
            production_additions += entry["additions"]
            production_deletions += entry["deletions"]

    for path in normalized["forbidden_imports"]:
        for entry in file_entries:
            file_path = repo_root / entry["path"]
            if file_path.exists() and path in file_path.read_text(encoding="utf-8"):
                violations.append(f"forbidden import rejected: {path}")
    for symbol in normalized["forbidden_symbols"]:
        for entry in file_entries:
            file_path = repo_root / entry["path"]
            if file_path.exists() and symbol in file_path.read_text(encoding="utf-8"):
                violations.append(f"forbidden symbol rejected: {symbol}")

    if production_additions + production_deletions > normalized["production_changed_lines_max"]:
        violations.append("production line ceiling exceeded")
    if test_additions + test_deletions > normalized["test_changed_lines_max"]:
        violations.append("test line ceiling exceeded")

    result = {
        "pass": not violations,
        "contract_sha": computed_contract_sha,
        "gate_blob_sha": computed_gate_blob_sha,
        "files": file_entries,
        "production_totals": {
            "additions": production_additions,
            "deletions": production_deletions,
            "changed_lines": production_additions + production_deletions,
        },
        "test_totals": {
            "additions": test_additions,
            "deletions": test_deletions,
            "changed_lines": test_additions + test_deletions,
        },
        "violations": sorted(set(violations)),
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an architecture slice contract.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--contract-sha", required=True)
    args = parser.parse_args(argv)

    try:
        result = evaluate_contract(Path(args.contract), args.contract_sha)
    except Exception as exc:  # pragma: no cover - exercised via CLI tests
        result = {
            "pass": False,
            "contract_sha": "",
            "gate_blob_sha": "",
            "files": [],
            "production_totals": {"additions": 0, "deletions": 0, "changed_lines": 0},
            "test_totals": {"additions": 0, "deletions": 0, "changed_lines": 0},
            "violations": [str(exc)],
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 1

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
