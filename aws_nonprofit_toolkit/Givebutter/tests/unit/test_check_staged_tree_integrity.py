"""Unit tests for the staged-tree integrity guard."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import shlex
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ci"))

import check_staged_tree_integrity  # noqa: E402


def _run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _init_repo() -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="staged-tree-test-"))
    _run_git(["git", "init"], tmpdir)
    _run_git(["git", "config", "user.email", "test@example.com"], tmpdir)
    _run_git(["git", "config", "user.name", "Test User"], tmpdir)
    _write(tmpdir / "scripts/householder/__init__.py", "")
    _write(
        tmpdir / "scripts/householder/issue_recalculation_service.py",
        "def recalculate_row_issues():\n    return ['baseline']\n",
    )
    _write(tmpdir / "tests/unit/test_smoke.py", "def test_smoke():\n    assert True\n")
    _run_git(["git", "add", "scripts", "tests"], tmpdir)
    _run_git(["git", "commit", "-m", "seed"], tmpdir)
    return tmpdir


def test_staged_tree_blocks_when_import_depends_on_untracked_module(capsys):
    repo = _init_repo()
    try:
        check_staged_tree_integrity.get_repo_root = lambda: repo  # type: ignore[assignment]
        _write(
            repo / "scripts/householder/issue_reconciliation.py",
            "def reconcile_missing_address_issues():\n    return ['working-tree-only']\n",
        )
        _write(
            repo / "scripts/householder/issue_recalculation_service.py",
            "from .issue_reconciliation import reconcile_missing_address_issues\n"
            "def recalculate_row_issues():\n"
            "    return reconcile_missing_address_issues()\n",
        )
        _run_git(["git", "add", "scripts/householder/issue_recalculation_service.py"], repo)

        exit_code = check_staged_tree_integrity.check_staged_tree_integrity()
        captured = capsys.readouterr()
        assert exit_code != 0
        assert "issue_reconciliation" in captured.out or "issue_reconciliation" in captured.err
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_staged_tree_passes_when_tree_is_self_contained(capsys):
    repo = _init_repo()
    try:
        check_staged_tree_integrity.get_repo_root = lambda: repo  # type: ignore[assignment]
        _write(
            repo / "scripts/householder/issue_reconciliation.py",
            "def reconcile_missing_address_issues():\n    return []\n",
        )
        _run_git(["git", "add", "scripts/householder/issue_reconciliation.py"], repo)
        _run_git(["git", "add", "scripts/householder/issue_recalculation_service.py"], repo)
        exit_code = check_staged_tree_integrity.check_staged_tree_integrity()
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Staged-tree integrity is clean" in captured.out
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_explicit_command_failure_is_preserved(capsys):
    repo = _init_repo()
    try:
        check_staged_tree_integrity.get_repo_root = lambda: repo  # type: ignore[assignment]
        _write(
            repo / "scripts/householder/issue_reconciliation.py",
            "def reconcile_missing_address_issues():\n    return []\n",
        )
        _run_git(["git", "add", "scripts/householder/issue_reconciliation.py"], repo)
        _run_git(["git", "add", "scripts/householder/issue_recalculation_service.py"], repo)
        exit_code = check_staged_tree_integrity.check_staged_tree_integrity(
            [f"{shlex.quote(sys.executable)} -c \"import sys; sys.exit(3)\""]
        )
        captured = capsys.readouterr()
        assert exit_code == 3
        assert "exit code 3" in captured.out
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_malformed_command_fails_closed():
    repo = _init_repo()
    try:
        check_staged_tree_integrity.get_repo_root = lambda: repo  # type: ignore[assignment]
        _write(
            repo / "scripts/householder/issue_reconciliation.py",
            "def reconcile_missing_address_issues():\n    return []\n",
        )
        _run_git(["git", "add", "scripts/householder/issue_reconciliation.py"], repo)
        _run_git(["git", "add", "scripts/householder/issue_recalculation_service.py"], repo)
        exit_code = check_staged_tree_integrity.check_staged_tree_integrity(["   "])
        assert exit_code == 1
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_temporary_tree_is_cleaned_up(monkeypatch):
    repo = _init_repo()
    tracked_tempdirs: list[Path] = []

    class TrackingTempDir:
        def __init__(self, *args, **kwargs):
            self.path = Path(tempfile.mkdtemp(prefix="staged-tree-cleanup-"))
            tracked_tempdirs.append(self.path)
            self.cleaned = False

        def __enter__(self):
            return str(self.path)

        def __exit__(self, exc_type, exc, tb):
            self.cleaned = True
            shutil.rmtree(self.path, ignore_errors=True)
            return False

    try:
        check_staged_tree_integrity.get_repo_root = lambda: repo  # type: ignore[assignment]
        _write(
            repo / "scripts/householder/issue_reconciliation.py",
            "def reconcile_missing_address_issues():\n    return []\n",
        )
        _run_git(["git", "add", "scripts/householder/issue_reconciliation.py"], repo)
        _run_git(["git", "add", "scripts/householder/issue_recalculation_service.py"], repo)
        monkeypatch.setattr(check_staged_tree_integrity.tempfile, "TemporaryDirectory", TrackingTempDir)
        exit_code = check_staged_tree_integrity.check_staged_tree_integrity()
        assert exit_code == 0
        assert tracked_tempdirs
        assert not tracked_tempdirs[0].exists()
    finally:
        shutil.rmtree(repo, ignore_errors=True)
