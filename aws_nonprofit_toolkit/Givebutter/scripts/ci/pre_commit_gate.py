#!/usr/bin/env python3
"""Pre-commit hook gate that runs Givebutter checks through the project venv."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


BLOCKED_PATTERNS = (
    ".DS_Store",
    "scheduled_tasks.lock",
    "screenshots/",
    "traces/",
    "videos/",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    "givebutter.db",
    "listings.db",
)


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_givebutter_dir() -> Path:
    return get_repo_root() / "Givebutter"


def get_venv_python() -> Path:
    return get_givebutter_dir() / ".venv" / "bin" / "python"


def build_env() -> dict[str, str]:
    env = os.environ.copy()
    venv_bin = str(get_givebutter_dir() / ".venv" / "bin")
    current_path = env.get("PATH", "")
    env["PATH"] = f"{venv_bin}:{current_path}" if current_path else venv_bin
    return env


def resolve_command(command: str, env: dict[str, str]) -> str | None:
    return shutil.which(command, path=env.get("PATH"))


def list_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=get_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("git diff --cached --name-only failed")
    return [line for line in result.stdout.splitlines() if line]


def is_blocked_artifact(path: str) -> bool:
    return any(pattern in path or (pattern.startswith("*") and path.endswith(pattern[1:])) for pattern in BLOCKED_PATTERNS)


def check_blocked_artifacts() -> int:
    print("Checking for blocked artifacts...")
    for path in list_staged_files():
        if is_blocked_artifact(path):
            print(f"❌ Found blocked artifact pattern: {path}")
            print("")
            print("COMMIT BLOCKED: Remove blocked files and re-stage.")
            return 1
    print("✓ No blocked artifacts found")
    print("")
    return 0


def verify_venv_commands(env: dict[str, str]) -> int:
    python_path = resolve_command("python", env)
    pytest_path = resolve_command("pytest", env)

    if python_path is None or pytest_path is None:
        print("Error: python and pytest must resolve inside the Givebutter virtualenv", file=sys.stderr)
        return 1

    print(python_path)
    print(pytest_path)

    probe = subprocess.run(
        [
            str(get_venv_python()),
            "-c",
            "import sys, email_validator; print(sys.executable); print(email_validator.__version__)",
        ],
        cwd=get_givebutter_dir(),
        env=env,
        check=False,
    )
    return probe.returncode


def run_pytest_gate(env: dict[str, str]) -> int:
    print("Running unit + integration tests...")
    print("")
    result = subprocess.run(
        [str(get_venv_python()), "-m", "pytest", "tests/unit", "tests/integration", "-q", "--tb=short"],
        cwd=get_givebutter_dir(),
        env=env,
        check=False,
    )
    if result.returncode != 0:
        print("")
        print("❌ COMMIT BLOCKED: Unit/integration tests failed!")
        print("")
        print("Fix the failing tests and try again.")
        print("To run tests manually:")
        print(f"  cd {get_givebutter_dir()}")
        print("  pytest tests/unit tests/integration -v")
        print("")
        print("For full validation including E2E:")
        print("  pytest tests/ -q")
        print("")
    return result.returncode


def main() -> int:
    env = build_env()

    print("\033[1;33mPre-commit: Checking artifacts and running fast unit/integration tests...\033[0m")
    print("")

    if verify_venv_commands(env) != 0:
        return 1

    if check_blocked_artifacts() != 0:
        return 1

    exit_code = run_pytest_gate(env)
    if exit_code == 0:
        print("")
        print("\033[0;32m✓ Pre-commit checks passed!\033[0m")
        print("")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
