"""Unit tests for the pre-commit hook gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

from pre_commit_gate import (  # noqa: E402
    BLOCKED_PATTERNS,
    build_env,
    check_blocked_artifacts,
    get_givebutter_dir,
    get_repo_root,
    get_venv_python,
    is_blocked_artifact,
    resolve_command,
    run_pytest_gate,
    verify_venv_commands,
)


def test_build_env_prepends_givebutter_venv_bin(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/local/bin")

    env = build_env()

    assert env["PATH"].startswith(f"{get_givebutter_dir() / '.venv' / 'bin'}:")


def test_resolve_command_finds_project_venv_bins():
    env = build_env()

    python_path = resolve_command("python", env)
    pytest_path = resolve_command("pytest", env)

    assert python_path is not None
    assert pytest_path is not None
    assert str(get_givebutter_dir() / ".venv" / "bin") in python_path
    assert str(get_givebutter_dir() / ".venv" / "bin") in pytest_path


def test_venv_python_can_import_email_validator():
    env = build_env()

    result = subprocess.run(
        [
            str(get_venv_python()),
            "-c",
            "import sys, email_validator; print(sys.executable); print(email_validator.__version__)",
        ],
        cwd=get_givebutter_dir(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert str(get_venv_python()) in result.stdout
    assert "email_validator" not in result.stderr


def test_is_blocked_artifact_detects_known_patterns():
    assert is_blocked_artifact("Givebutter/.DS_Store")
    assert is_blocked_artifact("Givebutter/screenshots/example.png")
    assert is_blocked_artifact("Givebutter/cache/__pycache__/module.cpython-311.pyc")
    assert is_blocked_artifact("Givebutter/tmp/output.pyc")
    assert not is_blocked_artifact("Givebutter/scripts/ci/pre_commit_gate.py")


def test_check_blocked_artifacts_blocks_staged_artifacts(monkeypatch, capsys):
    monkeypatch.setattr(
        "pre_commit_gate.list_staged_files",
        lambda: ["Givebutter/screenshots/example.png"],
    )

    exit_code = check_blocked_artifacts()

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "blocked artifact pattern" in out


def test_verify_venv_commands_requires_project_venv(monkeypatch):
    env = build_env()

    assert verify_venv_commands(env) == 0


def test_verify_venv_commands_fails_cleanly_when_venv_commands_missing(monkeypatch, capsys):
    env = build_env()
    monkeypatch.setattr("pre_commit_gate.resolve_command", lambda command, env: None)

    assert verify_venv_commands(env) == 1

    out = capsys.readouterr()
    assert "must resolve inside the Givebutter virtualenv" in out.err
    assert out.out == ""


def test_run_pytest_gate_preserves_failure_exit_code(monkeypatch):
    env = build_env()

    fake_result = MagicMock(returncode=7)
    monkeypatch.setattr("pre_commit_gate.subprocess.run", lambda *args, **kwargs: fake_result)

    assert run_pytest_gate(env) == 7
