"""Focused portable process-identity and scope-lock tests."""

import importlib.util
import json
from pathlib import Path

import pytest


LAUNCHER_PATH = Path(__file__).parents[2] / "scripts" / "ci" / "householder_launcher.py"
SPEC = importlib.util.spec_from_file_location("householder_launcher_scope_under_test", LAUNCHER_PATH)
launcher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(launcher)


def _roots(tmp_path, monkeypatch):
    locks = tmp_path / "locks"
    state = tmp_path / "state"
    monkeypatch.setattr(launcher, "LOCK_ROOT", locks)
    monkeypatch.setattr(launcher, "STATE_ROOT", state)
    return locks, state


def _foreign_lock(locks, state, *, pid=4242, token="foreign-token", campaign="foreign", operation="foreign-op"):
    token_root = state / "process-tokens"
    owner = token_root / f"owner-{pid}-{token}.json"
    registration = token_root / f"pid-{pid}.json"
    owner_state = {"pid": pid, "process_token": token, "campaign_id": campaign, "operation_id": operation, "created_at": "2026-08-03T00:00:00Z"}
    token_root.mkdir(parents=True)
    owner.write_text(json.dumps(owner_state), encoding="utf-8")
    registration.write_text(json.dumps(owner_state), encoding="utf-8")
    lock = locks / "foreign-lock.json"
    locks.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({
        "campaign_id": campaign,
        "mode": "campaign",
        "checkout": "/tmp/foreign",
        "authorized_paths": ["tests/owned.py"],
        "pid": pid,
        "process_token": token,
        "owner_state": str(owner),
        "process_created_at": owner_state["created_at"],
        "process_start_identity": None,
        "acquisition_timestamp": owner_state["created_at"],
        "launcher_operation_id": operation,
    }), encoding="utf-8")
    return lock, owner, registration


def test_current_process_acquires_without_ps_and_cleans_identity(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: None)
    with launcher.scope_lock("current", "campaign", tmp_path, ["tests/current.py"], "op-current") as acquired:
        assert len(acquired) == 1
        record = json.loads(Path(acquired[0]).read_text(encoding="utf-8"))
        assert record["pid"] == launcher.os.getpid()
        assert record["process_token"] == launcher.PROCESS_TOKEN
        assert Path(record["owner_state"]).is_file()
    assert not list(locks.glob("*.json"))
    assert not list((state / "process-tokens").glob("*.json"))


def test_live_foreign_pid_is_rejected(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    _foreign_lock(locks, state)
    monkeypatch.setattr(launcher, "_alive", lambda pid: True)
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: None)
    with pytest.raises(launcher.LaunchError) as exc:
        with launcher.scope_lock("current", "campaign", tmp_path, ["tests/current.py"], "op-current"):
            pass
    assert exc.value.code == "SCOPE_LOCK_LIVE"


def test_overlapping_live_writer_is_rejected_as_live_scope_conflict(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    _foreign_lock(locks, state)
    monkeypatch.setattr(launcher, "_alive", lambda pid: True)
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: None)
    with pytest.raises(launcher.LaunchError) as exc:
        with launcher.scope_lock("current", "campaign", tmp_path, ["tests/owned.py"], "op-current"):
            pass
    assert exc.value.code == "SCOPE_LOCK_LIVE"
    assert exc.value.details["error_class"] == "SCOPE_OVERLAP"


def test_permission_denied_liveness_is_ambiguous(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    _foreign_lock(locks, state)
    monkeypatch.setattr(launcher, "_alive", lambda pid: None)
    with pytest.raises(launcher.LaunchError) as exc:
        with launcher.scope_lock("current", "campaign", tmp_path, ["tests/current.py"], "op-current"):
            pass
    assert exc.value.code == "SCOPE_LOCK_IDENTITY_AMBIGUOUS"


def test_dead_pid_with_matching_owner_state_is_recovered(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    old_lock, old_owner, old_registration = _foreign_lock(locks, state)
    monkeypatch.setattr(launcher, "_alive", lambda pid: False)
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: None)
    with launcher.scope_lock("current", "campaign", tmp_path, ["tests/current.py"], "op-current") as acquired:
        assert len(acquired) == 1
        assert not old_lock.exists()
        assert not old_owner.exists()
        assert not old_registration.exists()


def test_pid_reuse_with_token_mismatch_fails_closed(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    _foreign_lock(locks, state, pid=launcher.os.getpid())
    monkeypatch.setattr(launcher, "_alive", lambda pid: True)
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: None)
    with pytest.raises(launcher.LaunchError) as exc:
        with launcher.scope_lock("current", "campaign", tmp_path, ["tests/current.py"], "op-current"):
            pass
    assert exc.value.code == "PROCESS_IDENTITY_CORRUPT"


def test_missing_token_state_fails_closed(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    lock, owner, registration = _foreign_lock(locks, state)
    owner.unlink()
    monkeypatch.setattr(launcher, "_alive", lambda pid: False)
    with pytest.raises(launcher.LaunchError) as exc:
        with launcher.scope_lock("current", "campaign", tmp_path, ["tests/current.py"], "op-current"):
            pass
    assert exc.value.code == "PROCESS_IDENTITY_CORRUPT"
    assert lock.exists()


def test_exact_retry_has_no_duplicate_lock_or_token_state(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: None)
    for _ in range(2):
        with launcher.scope_lock("same", "campaign", tmp_path, ["tests/current.py"], "same-op"):
            assert len(list(locks.glob("*.json"))) == 1
        assert not list(locks.glob("*.json"))
        assert not list((state / "process-tokens").glob("*.json"))


def test_failed_admission_cleans_lock_and_token_state(tmp_path, monkeypatch):
    locks, state = _roots(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, "_process_identity", lambda pid: None)
    with pytest.raises(RuntimeError):
        with launcher.scope_lock("failed", "campaign", tmp_path, ["tests/current.py"], "failed-op"):
            raise RuntimeError("simulated admission failure")
    assert not list(locks.glob("*.json"))
    assert not list((state / "process-tokens").glob("*.json"))
