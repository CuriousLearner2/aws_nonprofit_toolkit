#!/usr/bin/env python3
"""
Simplified pre-commit gate: automated safety checks only.

Tier 1 (docs/tests-only): tests
Tier 2 (normal product): tests + Reviewer workflow requirement
Tier 3 (export/readiness/persistence/contracts): tests + E2E + Reviewer + Breaker workflow requirements
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

BLOCKED_PATTERNS = (
    ".DS_Store", "scheduled_tasks.lock", "screenshots/", "traces/", "videos/",
    "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "givebutter.db", "listings.db",
)

# Tier 3 contract modules (highest risk: export, readiness, persistence)
TIER3_CRITICAL_MODULES = {
    "export_preview_service",
    "readiness_service",
    "database_models",
    "database_write_repository",
    "approval_service",
    "write_repository_contracts",
    "service_contracts",
}

# E2E lane mapping for Tier 3 contract files
# Maps contract modules to their relevant E2E test files
TIER3_E2E_MAPPING = {
    "export_preview_service": [
        "tests/e2e/test_validation_export_blocking.py",
        "tests/e2e/test_export_recent_exports_refresh.py",
    ],
    "readiness_service": [
        "tests/e2e/test_validation_export_blocking.py",
    ],
    "approval_service": [
        "tests/e2e/test_validation_export_blocking.py",
    ],
    "write_repository_contracts": [
        "tests/e2e/test_validation_export_blocking.py",
    ],
    "service_contracts": [],  # Abstract; conservative fallback
    # database_models, database_write_repository: no safe mapping; use full E2E
}


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_givebutter_dir() -> Path:
    return get_repo_root() / "Givebutter"


def get_venv_python() -> Path:
    return get_givebutter_dir() / ".venv/bin/python"


def build_env() -> dict[str, str]:
    env = os.environ.copy()
    venv_bin = str(get_givebutter_dir() / ".venv/bin")
    env["PATH"] = f"{venv_bin}:{env['PATH']}" if env.get("PATH") else venv_bin
    return env


def run_git(args: list[str]) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args], cwd=get_repo_root(), capture_output=True, text=True, check=False
    )


def list_staged_files() -> list[str]:
    result = run_git(["diff", "--cached", "--name-only"])
    if result.returncode != 0:
        raise RuntimeError("git diff --cached --name-only failed")
    return [line for line in result.stdout.splitlines() if line]


def detect_change_tier(staged_files: list[str]) -> int:
    """
    Classify change by risk tier based on file paths.

    Returns:
      1 = Tier 1: docs/tests/tooling only (no reviewer required)
      2 = Tier 2: normal product code (reviewer required)
      3 = Tier 3: export/readiness/persistence contracts (reviewer + breaker required)
    """
    tier = 1

    for filepath in staged_files:
        # Check if this is a Tier 3 critical module
        if any(module in filepath for module in TIER3_CRITICAL_MODULES):
            return 3  # Highest tier; any Tier 3 file makes whole commit Tier 3

        # Check for migrations and schema files (Tier 3)
        if filepath.startswith("migrations/") or filepath.endswith(".sql"):
            return 3

        # Check if this is Tier 1 only (docs/tests/tooling)
        tier1_patterns = ("docs/", "tests/", ".claude/", ".github/", ".codex/")
        if any(filepath.startswith(p) for p in tier1_patterns):
            continue

        if filepath.endswith(".md") and not any(p in filepath for p in ["scripts/", "migrations/"]):
            continue

        # Tooling/CI changes are Tier 2
        tier2_patterns = ("scripts/ci/", "pre-commit", "pre-push", "AGENTS.md")
        if any(pattern in filepath for pattern in tier2_patterns):
            tier = max(tier, 2)
            continue

        # Unknown product files default to Tier 2 (conservative upward)
        if filepath.startswith("scripts/"):
            tier = max(tier, 2)

    return tier


def print_tier_requirements(tier: int) -> None:
    """Print workflow requirements for this tier (advisory only)."""
    print()
    if tier == 1:
        print("ℹ️  Tier 1 (docs/tests only) — no reviewer required.")
    elif tier == 2:
        print("ℹ️  Tier 2 change detected (normal product/code).")
        print("   Workflow requirement: Reviewer must be run before pushing.")
        print("   See: .claude/agents/reviewer.md")
    elif tier == 3:
        print("ℹ️  Tier 3 change detected (export/readiness/persistence/contracts).")
        print("   Workflow requirements before pushing:")
        print("   - Reviewer MUST be run")
        print("   - Breaker MUST be run")
        print("   See: .claude/agents/reviewer.md, .claude/agents/breaker.md")
    print()


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


def resolve_command(command: str, env: dict[str, str]) -> str | None:
    import shutil
    return shutil.which(command, path=env.get("PATH"))


def verify_venv_commands(env: dict[str, str]) -> int:
    python_path = resolve_command("python", env)
    pytest_path = resolve_command("pytest", env)
    expected_bin = str(get_givebutter_dir() / ".venv/bin")
    if not python_path or not pytest_path or not python_path.startswith(expected_bin) or not pytest_path.startswith(expected_bin):
        print("Error: python and pytest must resolve inside the Givebutter virtualenv", file=sys.stderr)
        return 1
    return 0


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


def run_task_untracked_guard() -> int:
    result = run_guard([str(get_venv_python()), "scripts/ci/check_task_untracked.py"])
    if result is None or result.returncode != 0:
        print("\n❌ COMMIT BLOCKED: Untracked task files must be removed or staged before committing.")
        return 1
    return 0


def run_staged_tree_integrity_guard() -> int:
    result = run_guard([str(get_venv_python()), "scripts/ci/check_staged_tree_integrity.py"])
    if result is None or result.returncode != 0:
        print("\n❌ COMMIT BLOCKED: Staged-tree integrity must pass before committing.")
        return 1
    return 0


def get_relevant_e2e_tests_for_tier3(staged_files: list[str]) -> list[str]:
    """
    Determine which E2E tests to run for Tier 3 changes.

    If a safe relevant-lane mapping exists, run only those tests.
    If no safe mapping can be determined, conservatively use full E2E suite.
    """
    relevant_tests = set()

    for filepath in staged_files:
        # Check each Tier 3 module for mappings
        for module_name, e2e_files in TIER3_E2E_MAPPING.items():
            if module_name in filepath:
                if e2e_files:
                    # Has a mapping; use it
                    relevant_tests.update(e2e_files)
                else:
                    # No mapping available (abstract or fallback); use full E2E
                    return []  # Empty list signals full E2E suite

        # Tier 3 modules without explicit mapping: use full E2E
        if any(module in filepath for module in ("database_models", "database_write_repository")):
            return []  # Full E2E suite

    # If we found relevant mappings, return them
    if relevant_tests:
        return sorted(list(relevant_tests))

    # No mappings found; default to full E2E (conservative)
    return []


def run_pytest_gate(env: dict[str, str], include_e2e: list[str] | bool = False) -> int:
    """
    Run unit and integration tests. Optionally include E2E.

    Args:
        include_e2e: False = no E2E
                    True = full E2E suite
                    list = specific E2E test files
    """
    print("Running unit + integration tests...\n")

    cmd = [str(get_venv_python()), "-m", "pytest", "tests/unit", "tests/integration", "-q", "--tb=short"]

    if include_e2e is True:
        cmd.append("tests/e2e")
    elif isinstance(include_e2e, list) and include_e2e:
        cmd.extend(include_e2e)

    result = subprocess.run(cmd, cwd=get_givebutter_dir(), env=env, check=False)

    if result.returncode != 0:
        print("\n❌ COMMIT BLOCKED: Tests failed!")
        return 1

    return 0


def main() -> int:
    import os

    env = build_env()
    print("\033[1;33mPre-commit: automated safety checks...\033[0m\n")

    # All tiers: verify venv
    if verify_venv_commands(env) != 0:
        return 1

    # All tiers: check for untracked task files
    if run_task_untracked_guard() != 0:
        return 1

    # All tiers: check staged-tree integrity
    if run_staged_tree_integrity_guard() != 0:
        return 1

    # All tiers: check for blocked artifacts
    if check_blocked_artifacts() != 0:
        return 1

    # Determine tier and run appropriate tests
    staged = list_staged_files()
    tier = detect_change_tier(staged)

    # Run tests based on tier
    if tier == 3:
        # Tier 3: full unit/integration + relevant or full E2E
        e2e_tests = get_relevant_e2e_tests_for_tier3(staged)
        if e2e_tests:
            print(f"Running Tier 3 with relevant E2E lane ({len(e2e_tests)} test file(s))...\n")
            exit_code = run_pytest_gate(env, include_e2e=e2e_tests)
        else:
            print("Running Tier 3 with full E2E suite (no safe relevant-lane mapping)...\n")
            exit_code = run_pytest_gate(env, include_e2e=True)
    else:
        # Tier 1-2: unit/integration only
        exit_code = run_pytest_gate(env, include_e2e=False)

    if exit_code != 0:
        return exit_code

    # Print workflow requirements (advisory)
    print_tier_requirements(tier)

    print("\033[0;32m✓ Automated safety checks passed!\033[0m\n")
    return 0


if __name__ == "__main__":
    import os
    raise SystemExit(main())
