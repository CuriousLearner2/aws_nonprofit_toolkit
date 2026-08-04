from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "aws_nonprofit_toolkit" / "Givebutter"))
from scripts.ci import householder_launcher as launcher


def marker_project(root: Path, nested: bool = False) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    project = root / "aws_nonprofit_toolkit/Givebutter" if nested else root
    for marker in launcher.MARKERS:
        path = project / marker; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("# marker\n")
    (project / "requirements.txt").write_text("pytest==7.4.3\n")
    (project / "requirements-test.txt").write_text("pytest-asyncio==0.21.1\n")
    return root, project


def payload() -> dict[str, object]:
    return {"baseline": "d0ffce7e3a392ffb883354b117ccae4842dbd2d9", "campaign_id": "one", "mode": "campaign", "authorized_production_paths": ["scripts/ci/policy.py"], "authorized_test_paths": ["tests/unit/test_policy.py"], "suite_ids": ["fixed"], "time_limit_seconds": 10}


def test_input_rejects_duplicate_and_escaped_paths():
    value = payload(); value["authorized_production_paths"] = ["scripts/a.py", "scripts/a.py"]
    with pytest.raises(launcher.LaunchError, match="duplicate"): launcher._normalise_input(value)
    value = payload(); value["authorized_production_paths"] = ["../a.py"]
    with pytest.raises(launcher.LaunchError, match="escaped"): launcher._normalise_input(value)


def test_flat_and_nested_project_roots_and_ambiguity(tmp_path):
    root, project = marker_project(tmp_path / "flat"); assert launcher.discover_project_root(root) == project
    root, project = marker_project(tmp_path / "nested", nested=True); assert launcher.discover_project_root(root) == project
    for marker in launcher.MARKERS:
        path = root / marker; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("duplicate")
    with pytest.raises(launcher.LaunchError, match="multiple"): launcher.discover_project_root(root)


def test_environment_fingerprint(tmp_path, monkeypatch):
    _, project = marker_project(tmp_path / "repo"); monkeypatch.setattr(launcher, "PYTHON311", sys.executable)
    result = launcher._environment(project)
    assert result["python_version"].split()[:2] == ["3", "11"]
    assert len(result["freeze_sha256"]) == 64


def test_scope_overlap_dead_recovery_and_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "LOCK_ROOT", tmp_path / "locks")
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: f"p{pid}")
    project = tmp_path / "project"; project.mkdir(); lock_dir = tmp_path / "locks"; lock_dir.mkdir()
    pid = os.getpid(); token = launcher.PROCESS_TOKEN
    owner = launcher._process_owner_path(pid, token)
    registration = launcher._process_registration_path(pid)
    identity = {"pid": pid, "process_token": token, "campaign_id": "other", "operation_id": "other-op", "created_at": launcher.PROCESS_TOKEN_CREATED_AT}
    owner.parent.mkdir(parents=True, exist_ok=True)
    owner.write_text(json.dumps(identity))
    registration.write_text(json.dumps(identity))
    other = lock_dir / "other.json"
    other.write_text(json.dumps({"pid": pid, "process_token": token, "owner_state": str(owner), "campaign_id": "other", "launcher_operation_id": "other-op", "process_created_at": launcher.PROCESS_TOKEN_CREATED_AT, "process_start_identity": f"p{pid}", "authorized_paths": ["scripts/a.py"]}))
    monkeypatch.setattr(launcher, "_process_state", lambda *_args: (None, None))
    with pytest.raises(launcher.LaunchError, match="overlaps"):
        with launcher.scope_lock("two", "campaign", project, ["scripts/a.py"], "op"): pass
    other.unlink()
    owner.unlink(); registration.unlink()
    with launcher.scope_lock("one", "campaign", project, ["scripts/a.py"], "op") as locks:
        assert len(locks) == 1
        assert Path(locks[0]).is_file()
    stale_pid = 999999; stale_token = "dead-token"
    stale_owner = launcher._process_owner_path(stale_pid, stale_token)
    stale_registration = launcher._process_registration_path(stale_pid)
    stale_identity = {"pid": stale_pid, "process_token": stale_token, "campaign_id": "stale", "operation_id": "stale-op", "created_at": launcher.PROCESS_TOKEN_CREATED_AT}
    stale_owner.parent.mkdir(parents=True, exist_ok=True)
    stale_owner.write_text(json.dumps(stale_identity)); stale_registration.write_text(json.dumps(stale_identity))
    stale = lock_dir / "stale.json"; stale.write_text(json.dumps({"pid": stale_pid, "process_token": stale_token, "owner_state": str(stale_owner), "campaign_id": "stale", "launcher_operation_id": "stale-op", "process_created_at": launcher.PROCESS_TOKEN_CREATED_AT, "process_start_identity": "gone", "authorized_paths": ["scripts/stale.py"]}))
    with launcher.scope_lock("three", "campaign", project, ["scripts/new.py"], "op") as locks: Path(locks[0]).unlink()
    with launcher.scope_lock("read", "discovery", project, ["scripts/a.py"], "op") as locks: assert locks == []


def test_fixed_suite_registry_and_exact_retry(tmp_path, monkeypatch):
    project = tmp_path / "project"; project.mkdir()
    monkeypatch.setattr(launcher, "_wrapper", lambda _: type("W", (), {"SUITE_REGISTRY": {"fixed": ["ignored", "-c", "pass"]}}))
    result = launcher._preflight(project, ["fixed"], sys.executable, __import__("time").time() + 10); assert result[0]["passed"]
    with pytest.raises(launcher.LaunchError, match="fixed registry"): launcher._preflight(project, ["missing"], sys.executable, __import__("time").time() + 10)
    value = payload(); monkeypatch.setattr(launcher, "STATE_ROOT", tmp_path / "state"); path = tmp_path / "checkout"; path.mkdir(); subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    output = {"status": "ready", "checkout": str(path)}
    (tmp_path / "state").mkdir(); (tmp_path / "state/one.json").write_text(json.dumps({"input_sha256": launcher._digest(value), "status": "ready", "output": output}))
    with pytest.raises(launcher.LaunchError, match="completed checkout"): launcher.launch(value)


def test_wrapper_ledger_root_is_unique_under_launcher_state_root(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "STATE_ROOT", tmp_path / "state")
    assert launcher._wrapper_ledger_root("campaign-a") == tmp_path / "state/wrapper-ledgers/campaign-a"
    assert launcher._wrapper_ledger_root("campaign-b") != launcher._wrapper_ledger_root("campaign-a")


def test_wrapper_initialization_error_preserves_underlying_code():
    error = launcher.LaunchError("WRAPPER_INITIALIZATION_FAILED", "launcher failed", {"underlying_error_code": "PARENT_SCOPE_CONFLICT", "underlying_error": "active parent scope is unreadable"})
    assert error.code == "WRAPPER_INITIALIZATION_FAILED"
    assert error.details == {"underlying_error_code": "PARENT_SCOPE_CONFLICT", "underlying_error": "active parent scope is unreadable"}


def test_wrapper_ledger_configuration_supports_published_baseline_wrapper(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "STATE_ROOT", tmp_path / "state")
    wrapper = type("BaselineWrapper", (), {"LEDGER_ROOT": tmp_path / "global"})()
    root = launcher._configure_wrapper_ledger(wrapper, "campaign")
    assert root == tmp_path / "state/wrapper-ledgers/campaign"
    assert wrapper.LEDGER_ROOT == root
