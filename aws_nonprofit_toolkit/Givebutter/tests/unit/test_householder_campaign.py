from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.ci import householder_campaign as campaign


def git(repo: Path, *args: str) -> str:
    env = os.environ.copy()
    for key in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True, env=env).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir(); git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.com"); git(root, "config", "user.name", "Test User")
    (root / "scripts/ci").mkdir(parents=True); (root / "scripts/ci/architecture_slice_gate.py").write_text("gate\n")
    (root / "seed.txt").write_text("seed\n"); git(root, "add", "."); git(root, "commit", "-qm", "seed")
    monkeypatch.setattr(campaign, "LEDGER_ROOT", tmp_path / "campaigns")
    return root


@pytest.fixture
def contract(tmp_path):
    path = tmp_path / "contract.json"; path.write_text('{"task":"contained"}\n')
    return {"path": str(path), "sha256": campaign._json_sha256(json.loads(path.read_text()))}


def initialize(repo, contract, campaign_id="campaign-01"):
    gate = git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py")
    return campaign.campaign_ledger_init(campaign_id, "init-" + campaign_id, repo, gate, [contract])


def commit_change(repo, name="change.txt"):
    (repo / name).write_text("change\n"); git(repo, "add", name); git(repo, "commit", "-qm", "campaign change")
    return git(repo, "rev-parse", "HEAD")


def result(commit_sha, index=0, passed=True):
    return {"contract_index": index, "gate_pass": passed, "tests_pass": passed, "patch_sha": "a" * 64, "commit_sha": commit_sha}


def admit(campaign_id="campaign-01", index=0, operation_id="edit-1"):
    return campaign.campaign_ledger_start_edit(campaign_id, index, operation_id)


def fails(call, match=None):
    with pytest.raises(ValueError, match=match): call()


def test_happy_path_restart_and_deterministic_next(repo, contract, monkeypatch):
    initial = initialize(repo, contract); assert campaign.campaign_ledger_init("campaign-01", "init-campaign-01", repo, git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"), [contract]) == initial
    assert campaign.campaign_ledger_next("campaign-01")["kind"] == "IMPLEMENT"; admission = admit(); assert admission["contract_index"] == 0
    fails(lambda: campaign.campaign_ledger_record_result("campaign-01", "result-1", {"contract_index": 0}), "EDIT_NOT_VALIDATED")
    before = campaign.campaign_ledger_status("campaign-01"); loaded = importlib.reload(campaign)
    monkeypatch.setattr(loaded, "LEDGER_ROOT", Path(repo).parent / "campaigns"); assert loaded.campaign_ledger_status("campaign-01") == before


def test_absent_dirty_and_stale_commands_fail_closed(repo, contract):
    head = git(repo, "rev-parse", "HEAD")
    calls = [lambda: campaign.campaign_ledger_status("missing"), lambda: campaign.campaign_ledger_next("missing"),
             lambda: campaign.campaign_ledger_record_result("missing", "op", result(head)), lambda: campaign.campaign_ledger_quarantine("missing", "op", "x"),
             lambda: campaign.campaign_ledger_stop("missing", "op", "x")]
    for call in calls: fails(call, "LEDGER_UNAVAILABLE")
    initialize(repo, contract); (repo / "dirty").write_text("x")
    fails(lambda: campaign.campaign_ledger_status("campaign-01"), "DIRTY_WORKTREE"); (repo / "dirty").unlink(); commit_change(repo); fails(lambda: campaign.campaign_ledger_status("campaign-01"), "STALE_HEAD")


def test_contract_gate_and_ledger_mutations_fail_closed(repo, contract, tmp_path):
    initialize(repo, contract); Path(contract["path"]).write_text('{"task":"mutated"}\n')
    fails(lambda: campaign.campaign_ledger_status("campaign-01"), "CONTRACT_MUTATED")
    other = tmp_path / "other.json"; other.write_text('{"task":"other"}\n')
    campaign.LEDGER_ROOT = tmp_path / "other-campaigns"; fresh = {"path": str(other), "sha256": campaign._json_sha256(json.loads(other.read_text()))}
    initialize(repo, fresh, "campaign-02"); (repo / "scripts/ci/architecture_slice_gate.py").write_text("mutated\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "gate mutation")
    fails(lambda: campaign.campaign_ledger_status("campaign-02"), "GATE_MUTATED"); initialize(repo, fresh, "campaign-03"); path = Path(campaign.LEDGER_ROOT) / "campaign-03/state.json"; payload = json.loads(path.read_text()); payload["state"] = "COMMITTED"; path.write_text(json.dumps(payload)); fails(lambda: campaign.campaign_ledger_next("campaign-03"), "CHECKPOINT_MISMATCH")


def test_legacy_path_prompt_state_and_repeated_transitions_are_rejected(repo, contract):
    initialize(repo, contract); legacy = repo / "Givebutter/.artifacts/householder-campaign.campaign-01.json"
    (repo / ".git/info/exclude").write_text("Givebutter/.artifacts/\n"); legacy.parent.mkdir(parents=True); legacy.write_text('{"state":"COMMITTED"}\n')
    before = campaign.campaign_ledger_status("campaign-01"); assert campaign.campaign_ledger_status("campaign-01") == before
    fails(lambda: campaign.campaign_initialize("campaign-01", legacy), "disabled"); campaign.campaign_ledger_next("campaign-01"); fails(lambda: campaign.campaign_ledger_record_result("campaign-01", "prompt", {"contract_index": 0}), "EDIT_NOT_ADMITTED"); quarantined = campaign.campaign_ledger_quarantine("campaign-01", "term-1", "manual"); assert campaign.campaign_ledger_quarantine("campaign-01", "term-1", "manual") == quarantined; fails(lambda: campaign.campaign_ledger_quarantine("campaign-01", "term-2", "again"), "ILLEGAL_TRANSITION")


def test_stop_repeat_and_atomic_write_failure(repo, contract, monkeypatch):
    initialize(repo, contract, "campaign-02"); stopped = campaign.campaign_ledger_stop("campaign-02", "term-1", "manual"); assert campaign.campaign_ledger_stop("campaign-02", "term-1", "manual") == stopped; fails(lambda: campaign.campaign_ledger_stop("campaign-02", "term-2", "again"), "ILLEGAL_TRANSITION")
    original = campaign.os.replace; monkeypatch.setattr(campaign.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("replace failed")))
    with pytest.raises(OSError, match="replace failed"): initialize(repo, contract, "campaign-03")
    assert not (Path(campaign.LEDGER_ROOT) / "campaign-03/state.json").exists(); monkeypatch.setattr(campaign.os, "replace", original)


def test_operation_conflict_is_stable_and_restart_safe(repo, contract, monkeypatch):
    initialize(repo, contract); campaign.campaign_ledger_next("campaign-01"); admit(); commit = commit_change(repo); path = Path(campaign.LEDGER_ROOT) / "campaign-01/state.json"; before = path.read_bytes()
    fails(lambda: campaign.campaign_ledger_record_result("campaign-01", "result-1", result(commit)), "FABRICATED_RESULT_REJECTED"); assert path.read_bytes() == before
    loaded = importlib.reload(campaign); monkeypatch.setattr(loaded, "LEDGER_ROOT", Path(repo).parent / "campaigns"); fails(lambda: loaded.campaign_ledger_record_result("campaign-01", "result-1", result(commit)), "FABRICATED_RESULT_REJECTED")


def test_event_append_failure_leaves_no_checkpoint(repo, contract, monkeypatch):
    original = Path.open
    def fail_events(path, *args, **kwargs):
        if path.name == "events.jsonl": raise OSError("append failed")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail_events)
    fails(lambda: initialize(repo, contract, "campaign-04"), "EVENT_APPEND_FAILED")
    root = Path(campaign.LEDGER_ROOT) / "campaign-04"
    assert not (root / "state.json").exists() and not (root / "events.jsonl").exists()
