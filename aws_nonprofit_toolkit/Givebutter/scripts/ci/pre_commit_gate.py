#!/usr/bin/env python3
"""Pre-commit gate for Givebutter tests and machine-readable commit readiness."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

BLOCKED_PATTERNS = (
    ".DS_Store", "scheduled_tasks.lock", "screenshots/", "traces/", "videos/",
    "__pycache__", "*.pyc", "*.pyo", ".pytest_cache", "givebutter.db", "listings.db",
)
PACKET_RELATIVE_TO_GIVEBUTTER = Path(".artifacts/commit-readiness.json")
PACKET_REPO_PATH = "Givebutter/.artifacts/commit-readiness.json"
REQUIRED_PACKET_FIELDS = {
    "schema_version", "task_id", "reviewer_verdict", "breaker_verdict", "qa_verdict",
    "canonical_gates_passed", "scope_guard_passed", "commit_authorized",
    "push_authorized", "reviewed_head", "reviewed_diff_sha256", "reviewed_at",
    "informational_notes", "required_changes",
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
    venv_bin = str(get_givebutter_dir() / ".venv/bin")
    env["PATH"] = f"{venv_bin}:{env['PATH']}" if env.get("PATH") else venv_bin
    return env


def resolve_command(command: str, env: dict[str, str]) -> str | None:
    return shutil.which(command, path=env.get("PATH"))


def run_git(args: list[str], *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args], cwd=get_repo_root(), capture_output=True,
        text=not binary, check=False,
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
    missing = sorted(REQUIRED_PACKET_FIELDS - packet.keys())
    if missing:
        errors.append(f"missing required packet fields: {', '.join(missing)}")
        return errors

    if packet["schema_version"] != 1:
        errors.append("schema_version must equal 1")

    current_task_id = env.get("HOUSEHOLDER_TASK_ID", "").strip()
    if not current_task_id:
        errors.append("HOUSEHOLDER_TASK_ID is required as the independent current-task identity")
    elif packet["task_id"] != current_task_id:
        errors.append("task_id does not match HOUSEHOLDER_TASK_ID")

    exact_values = {
        "reviewer_verdict": "VERDICT=ACCEPT",
        "breaker_verdict": "BREAKER=PASS",
        "qa_verdict": "QA=PASS",
    }
    for field, expected in exact_values.items():
        if packet[field] != expected:
            errors.append(f"{field} must equal {expected}")

    for field in ("canonical_gates_passed", "scope_guard_passed", "commit_authorized"):
        if packet[field] is not True:
            errors.append(f"{field} must be true")

    if not isinstance(packet["push_authorized"], bool):
        errors.append("push_authorized must be a boolean")

    if not _is_empty_required_changes(packet["required_changes"]):
        errors.append("required_changes must be empty for commit eligibility")

    if not _valid_reviewed_at(packet["reviewed_at"]):
        errors.append("reviewed_at must be a valid ISO-8601 timestamp")

    staged = list_staged_files()
    if PACKET_REPO_PATH in staged or str(PACKET_RELATIVE_TO_GIVEBUTTER) in staged:
        errors.append("commit-readiness packet must not be staged")

    try:
        head = get_current_head()
        fingerprint = staged_diff_sha256()
    except RuntimeError as exc:
        errors.append(str(exc))
        return errors

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


def run_pytest_gate(env: dict[str, str]) -> int:
    print("Running unit + integration tests...\n")
    result = subprocess.run(
        [str(get_venv_python()), "-m", "pytest", "tests/unit", "tests/integration", "-q", "--tb=short"],
        cwd=get_givebutter_dir(), env=env, check=False,
    )
    if result.returncode != 0:
        print("\n❌ COMMIT BLOCKED: Unit/integration tests failed!")
    return result.returncode


def main() -> int:
    env = build_env()
    print("\033[1;33mPre-commit: validating readiness, artifacts, and tests...\033[0m\n")
    if verify_venv_commands(env) != 0:
        return 1
    if check_blocked_artifacts() != 0:
        return 1
    if check_commit_readiness(env) != 0:
        return 1
    exit_code = run_pytest_gate(env)
    if exit_code == 0:
        print("\n\033[0;32m✓ Pre-commit checks passed!\033[0m\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
