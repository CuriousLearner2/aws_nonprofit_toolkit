#!/usr/bin/env python3
"""Guard task-related untracked files before commit readiness."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT_NAME = Path(__file__).resolve().parents[2].name

TASK_PREFIXES = (
    "scripts/",
    "tests/",
    "templates/",
    ".claude/",
    ".github/",
    "migrations/",
)
TASK_EXACT_FILES = {
    "schema.sql",
}
ALLOWED_RUNTIME_PATTERNS = (
    ".DS_Store",
    "exports_uat/",
)


def get_repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("Error: not in a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(result.stdout.strip())


def normalize_path(filepath: str) -> str:
    normalized = filepath.replace("\\", "/").strip()
    anchors = (
        f"{PROJECT_ROOT_NAME}/",
        "/scripts/",
        "/tests/",
        "/templates/",
        "/.claude/",
        "/.github/",
        "/migrations/",
        "/schema.sql",
    )
    for anchor in anchors:
        index = normalized.find(anchor)
        if index != -1:
            return normalized[index + len(anchor):]
    return normalized


def get_untracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _matches_runtime_pattern(path: str) -> bool:
    return path == ".DS_Store" or path.endswith("/.DS_Store") or path.startswith("exports_uat/")


def classify_untracked_file(filepath: str) -> tuple[str, str]:
    normalized = normalize_path(filepath)
    if _matches_runtime_pattern(normalized):
        return "runtime", "ALLOW approved runtime artifact"
    if normalized in TASK_EXACT_FILES:
        return "task", "BLOCK untracked task-related file"
    if (
        normalized.startswith(TASK_PREFIXES)
        or "/templates/" in normalized
        or "/.claude/" in normalized
        or "/.github/" in normalized
        or "/scripts/" in normalized
        or "/tests/" in normalized
    ):
        return "task", "BLOCK untracked task-related file"
    if normalized.startswith("migrations/") or "/migrations/" in normalized or normalized.endswith(".sql"):
        return "task", "BLOCK untracked migration/schema file"
    return "other", "BLOCK untracked non-runtime file"


def check_task_untracked(untracked_files: list[str] | None = None) -> int:
    print("Checking untracked task files...")
    files = untracked_files if untracked_files is not None else get_untracked_files()
    blocked = []
    allowed = []

    for filepath in files:
        category, disposition = classify_untracked_file(filepath)
        normalized = normalize_path(filepath)
        print(f"- {normalized} [{category}] {disposition}")
        if disposition.startswith("BLOCK"):
            blocked.append(normalized)
        else:
            allowed.append(normalized)

    if blocked:
        print("\nCOMMIT BLOCKED: Remove or stage task-related untracked files before committing.")
        for filepath in blocked:
            print(f"  - {filepath}")
        return 1

    if not files:
        print("✓ No untracked files found")
    else:
        print("✓ No blocking untracked files found")
    return 0


def main() -> int:
    _ = get_repo_root()
    return check_task_untracked()


if __name__ == "__main__":
    raise SystemExit(main())
