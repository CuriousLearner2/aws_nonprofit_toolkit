"""Fail-closed database selection for automated Householder tests."""

import pytest

from scripts.householder.database_models import create_db_engine


def test_automated_mode_rejects_implicit_worktree_database(monkeypatch):
    monkeypatch.setenv("HOUSEHOLDER_AUTOMATED_TEST", "1")

    with pytest.raises(RuntimeError, match="explicit ephemeral database URL"):
        create_db_engine()


def test_pytest_child_process_marker_rejects_implicit_worktree_database(monkeypatch):
    monkeypatch.delenv("HOUSEHOLDER_AUTOMATED_TEST", raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/e2e/test_gate.py::test_state")

    with pytest.raises(RuntimeError, match="explicit ephemeral database URL"):
        create_db_engine()


def test_automated_mode_allows_explicit_test_database(monkeypatch, tmp_path):
    monkeypatch.setenv("HOUSEHOLDER_AUTOMATED_TEST", "1")

    engine = create_db_engine(f"sqlite:///{tmp_path / 'isolated.db'}")

    assert engine.url.database == str(tmp_path / "isolated.db")
