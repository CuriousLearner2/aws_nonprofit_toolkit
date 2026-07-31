"""Unit tests for the task-untracked guardrail script."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ci"))

import check_task_untracked  # noqa: E402


def test_classify_task_related_paths():
    assert check_task_untracked.classify_untracked_file("Givebutter/scripts/ci/new_guard.py")[0] == "task"
    assert check_task_untracked.classify_untracked_file("Givebutter/tests/unit/test_new.py")[0] == "task"
    assert check_task_untracked.classify_untracked_file("Givebutter/.claude/agents/orchestrator.md")[0] == "task"
    assert check_task_untracked.classify_untracked_file("Givebutter/.github/workflows/new.yml")[0] == "task"
    assert check_task_untracked.classify_untracked_file("Givebutter/migrations/003_new.sql")[0] == "task"
    assert check_task_untracked.classify_untracked_file("Givebutter/schema.sql")[0] == "task"


def test_allowed_runtime_artifacts_pass(capsys):
    exit_code = check_task_untracked.check_task_untracked(
        [
            ".DS_Store",
            "Givebutter/exports_uat/run-1.csv",
            "Givebutter/.artifacts/commit-readiness.json",
            "Givebutter/.artifacts/householder-task-state.json",
            "Givebutter/.artifacts/householder-task-state.json.lock",
            "Givebutter/.artifacts/householder-task-state.20260731T123456000000Z.1234567890abcdef.archive.json",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[runtime] ALLOW approved runtime artifact" in captured.out
    assert "No blocking untracked files found" in captured.out


def test_householder_runtime_artifacts_are_allowed_and_similar_names_are_blocked(capsys):
    exit_code = check_task_untracked.check_task_untracked(
        [
            "Givebutter/.artifacts/commit-readiness.json",
            "Givebutter/.artifacts/householder-task-state.json",
            "Givebutter/.artifacts/householder-task-state.json.lock",
            "Givebutter/.artifacts/householder-task-state.20260731T123456000000Z.1234567890abcdef.archive.json",
            "Givebutter/.artifacts/commit-readiness.snapshot.json",
            "Givebutter/.artifacts/householder-task-state.snapshot.json",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "commit-readiness.json [runtime]" in captured.out
    assert "householder-task-state.json [runtime]" in captured.out
    assert "householder-task-state.json.lock [runtime]" in captured.out
    assert "archive.json [runtime]" in captured.out
    assert "commit-readiness.snapshot.json [other]" in captured.out
    assert "householder-task-state.snapshot.json [other]" in captured.out
    assert "BLOCK untracked non-runtime file" in captured.out


def test_task_files_block_commit_and_print_exact_names(capsys):
    exit_code = check_task_untracked.check_task_untracked(
        [
            "Givebutter/tests/unit/test_guard.py",
            "Givebutter/scripts/ci/new_guard.py",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Givebutter/tests/unit/test_guard.py" not in captured.out
    assert "tests/unit/test_guard.py" in captured.out
    assert "scripts/ci/new_guard.py" in captured.out
    assert "BLOCK untracked task-related file" in captured.out


def test_mixed_runtime_and_task_files_blocks(capsys):
    exit_code = check_task_untracked.check_task_untracked(
        [".DS_Store", "Givebutter/exports_uat/run-1.csv", "Givebutter/templates/snippet.html"]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert ".DS_Store [runtime]" in captured.out
    assert "exports_uat/run-1.csv [runtime]" in captured.out
    assert "templates/snippet.html [task]" in captured.out


def test_no_untracked_files_pass(capsys):
    exit_code = check_task_untracked.check_task_untracked([])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No untracked files found" in captured.out
