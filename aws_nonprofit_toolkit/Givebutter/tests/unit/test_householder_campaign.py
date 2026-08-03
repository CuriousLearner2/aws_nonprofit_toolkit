from __future__ import annotations

import importlib
import json
import os
import shutil
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
    (root / "scripts/ci").mkdir(parents=True)
    shutil.copy2(Path(campaign.__file__).with_name("architecture_slice_gate.py"), root / "scripts/ci/architecture_slice_gate.py")
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n")
    (root / "seed.txt").write_text("seed\n"); git(root, "add", "."); git(root, "commit", "-qm", "seed")
    monkeypatch.setattr(campaign, "LEDGER_ROOT", tmp_path / "campaigns")
    return root


@pytest.fixture
def contract(repo, tmp_path):
    path = tmp_path / "contract.json"; path.write_text(json.dumps({
        "task_id": "test-campaign-contract",
        "seam": "new-seam",
        "typed_contract": {
            "baseline_head": git(repo, "rev-parse", "HEAD"),
            "gate_sha": git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"),
            "allowed_files": [],
            "max_production_lines": 10,
            "max_test_lines": 10,
            "suite_ids": ["wrapper-unit"],
            "invariants": ["behavior-preserved"],
            "completed_seams": [
                "decision-policy", "ingestion-value-policy", "phone-type-policy",
                "issue-contract-policy", "export-download-path-policy", "phone-format-policy",
                "approval-remaining-issues-policy", "export-csv-policy", "export-filename-policy",
                "recalculation-input-policy", "row-status-policy", "approval-override-policy",
                "row-decision-policy",
            ],
            "completed_seam_files": {
                "decision-policy": ["scripts/householder/decision_policy.py"],
                "ingestion-value-policy": ["scripts/householder/ingestion_value_policy.py"],
                "phone-type-policy": ["scripts/householder/phone_type_policy.py"],
                "issue-contract-policy": ["scripts/householder/issue_contract_policy.py"],
                "export-download-path-policy": ["scripts/householder/export_path_policy.py"],
                "phone-format-policy": ["scripts/householder/phone_format_policy.py"],
                "approval-remaining-issues-policy": ["scripts/householder/approval_remaining_issues_policy.py"],
                "export-csv-policy": ["scripts/householder/export_csv_policy.py"],
                "export-filename-policy": ["scripts/householder/export_filename_policy.py"],
                "recalculation-input-policy": ["scripts/householder/recalculation_input_policy.py"],
                "row-status-policy": ["scripts/householder/row_status_policy.py"],
                "approval-override-policy": ["scripts/householder/approval_override_policy.py"],
                "row-decision-policy": ["scripts/householder/row_decision_policy.py"],
            },
            "protected_files": [
                "scripts/ci/campaign_state.py", "scripts/ci/check_lane_scope.py",
                "scripts/ci/check_task_untracked.py", "scripts/ci/pre_commit_gate.py",
                "tests/unit/test_campaign_state.py",
            ],
        },
    }) + "\n")
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


def validated_edit(repo, contract, monkeypatch, campaign_id):
    item = _edit_contract(repo, contract, [
        "scripts/householder/new_policy.py",
        "tests/unit/test_householder_campaign.py",
    ])
    initialize(repo, item, campaign_id)
    campaign.campaign_ledger_next(campaign_id)
    campaign.campaign_ledger_start_edit(campaign_id, 0, "edit-" + campaign_id)
    path = repo / "scripts/householder/new_policy.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("POLICY = 'validated'\n")
    test_path = repo / "tests/unit/test_householder_campaign.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("def test_fixture_suite():\n    assert True\n")
    return campaign.campaign_ledger_finish_edit(campaign_id, 0, "finish-" + campaign_id)


def commit_validated_file(repo):
    git(repo, "add", "scripts/householder/new_policy.py", "tests/unit/test_householder_campaign.py")
    git(repo, "commit", "-qm", "validated implementation")
    return git(repo, "rev-parse", "HEAD")


def fails(call, match=None):
    with pytest.raises(ValueError, match=match): call()


def make_layout(tmp_path, nested):
    root = tmp_path / ("root" if nested else "Givebutter")
    worktree = root / "Givebutter" if nested else root
    (worktree / "scripts/ci").mkdir(parents=True)
    (worktree / "scripts/ci/architecture_slice_gate.py").write_text("gate\n")
    git(worktree, "init", "-q"); git(worktree, "config", "user.email", "test@example.com"); git(worktree, "config", "user.name", "Test User")
    git(worktree, "add", "."); git(worktree, "commit", "-qm", "seed")
    wrapper = worktree / "scripts/ci/householder_campaign.py"
    shutil.copy2(Path(campaign.__file__), wrapper)
    return root, worktree, wrapper


@pytest.mark.parametrize("nested", [False, True])
def test_repo_root_discovers_flat_and_nested_git_roots(tmp_path, nested):
    root, worktree, wrapper = make_layout(tmp_path, nested)
    assert campaign._discover_repo_root(wrapper) == Path(git(worktree, "rev-parse", "--show-toplevel"))
    identity = campaign._ledger_identity(worktree)
    assert identity["worktree_path"] == str(worktree.resolve())
    assert identity["git_common_dir"] == str(Path(git(worktree, "rev-parse", "--git-common-dir")).resolve())
    assert not list(tmp_path.glob("**/householder-campaign.*.json"))


def test_repo_root_discovery_fails_outside_git_and_for_symlink(tmp_path):
    outside = tmp_path / "outside" / "scripts/ci"
    outside.mkdir(parents=True)
    script = outside / "householder_campaign.py"
    script.write_text("wrapper\n")
    fails(lambda: campaign._discover_repo_root(script), "REPOSITORY_ROOT_DISCOVERY_FAILED")

    _, worktree, wrapper = make_layout(tmp_path / "valid", False)
    link = worktree / "scripts/ci/linked_campaign.py"
    link.symlink_to(wrapper)
    fails(lambda: campaign._discover_repo_root(link), "REPOSITORY_ROOT_DISCOVERY_FAILED")


def test_persisted_worktree_identity_mismatch_fails_closed(repo, contract):
    initialize(repo, contract)
    record = campaign._ledger_load("campaign-01")
    record["worktree_path"] = str(repo.parent / "substituted")
    with pytest.raises(ValueError, match="WORKTREE_MISMATCH"):
        campaign._ledger_validate(record)


def test_happy_path_restart_and_deterministic_next(repo, contract, monkeypatch):
    initial = initialize(repo, contract); assert campaign.campaign_ledger_init("campaign-01", "init-campaign-01", repo, git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"), [contract]) == initial
    assert campaign.campaign_ledger_next("campaign-01")["kind"] == "IMPLEMENT"; admission = admit(); assert admission["contract_index"] == 0
    fails(lambda: campaign.campaign_ledger_record_result("campaign-01", "result-1", {"contract_index": 0}), "EDIT_NOT_VALIDATED")
    before = campaign.campaign_ledger_status("campaign-01"); loaded = importlib.reload(campaign)
    monkeypatch.setattr(loaded, "LEDGER_ROOT", Path(repo).parent / "campaigns"); assert loaded.campaign_ledger_status("campaign-01") == before


def test_validated_single_commit_closes_and_exact_retry_is_noop(repo, contract, monkeypatch):
    validation = validated_edit(repo, contract, monkeypatch, "commit-close")
    parent = validation["expected_parent_head"]
    commit = commit_validated_file(repo)
    closed = campaign.campaign_ledger_record_result("commit-close", "close-1", {"contract_index": 0})
    assert closed["state"] == "COMMITTED"
    assert closed["current_head"] == commit
    assert validation["expected_parent_head"] == parent
    events = Path(campaign._events_file("commit-close"))
    before_retry = events.read_bytes()
    assert campaign.campaign_ledger_record_result("commit-close", "close-1", {"contract_index": 0}) == closed
    assert events.read_bytes() == before_retry
    assert git(repo, "status", "--porcelain=v1", "--untracked-files=all") == ""


def test_validated_commit_closure_survives_restart(repo, contract, monkeypatch):
    validated_edit(repo, contract, monkeypatch, "commit-restart")
    commit_validated_file(repo)
    loaded = importlib.reload(campaign)
    loaded.LEDGER_ROOT = Path(repo).parent / "campaigns"
    closed = loaded.campaign_ledger_record_result("commit-restart", "close-1", {"contract_index": 0})
    assert closed["state"] == "COMMITTED"


def test_validated_commit_rejects_unrelated_or_extra_commit(repo, contract, monkeypatch):
    validated_edit(repo, contract, monkeypatch, "commit-extra")
    (repo / "unrelated.txt").write_text("outside validated patch\n")
    git(repo, "add", "unrelated.txt")
    git(repo, "commit", "-qm", "unrelated change")
    fails(lambda: campaign.campaign_ledger_record_result("commit-extra", "close-1", {"contract_index": 0}), "VALIDATED_COMMIT_REJECTED")


def test_validated_commit_rejects_amended_content(repo, contract, monkeypatch):
    validated_edit(repo, contract, monkeypatch, "commit-amended")
    (repo / "scripts/householder/new_policy.py").write_text("POLICY = 'amended'\n")
    git(repo, "add", "scripts/householder/new_policy.py")
    git(repo, "commit", "-qm", "amended implementation")
    fails(lambda: campaign.campaign_ledger_record_result("commit-amended", "close-1", {"contract_index": 0}), "VALIDATED_COMMIT_REJECTED")


def test_validated_commit_rejects_multiple_commit_advancement(repo, contract, monkeypatch):
    validated_edit(repo, contract, monkeypatch, "commit-multiple")
    commit_validated_file(repo)
    git(repo, "commit", "--allow-empty", "-qm", "second advancement")
    fails(lambda: campaign.campaign_ledger_record_result("commit-multiple", "close-1", {"contract_index": 0}), "VALIDATED_COMMIT_REJECTED")


def test_prevalidation_head_change_still_fails_stale_head(repo, contract, monkeypatch):
    monkeypatch.setitem(campaign.SUITE_REGISTRY, "wrapper-unit", ["python3", "-c", "pass"])
    item = _edit_contract(repo, contract, ["scripts/householder/new_policy.py"])
    initialize(repo, item, "commit-prevalidation-stale")
    campaign.campaign_ledger_next("commit-prevalidation-stale")
    campaign.campaign_ledger_start_edit("commit-prevalidation-stale", 0, "edit-stale")
    (repo / "unrelated.txt").write_text("head changed before validation\n")
    git(repo, "add", "unrelated.txt")
    git(repo, "commit", "-qm", "prevalidation head change")
    fails(lambda: campaign.campaign_ledger_finish_edit("commit-prevalidation-stale", 0, "finish-stale"), "STALE_HEAD")


def test_absent_dirty_and_stale_commands_fail_closed(repo, contract):
    head = git(repo, "rev-parse", "HEAD")
    calls = [lambda: campaign.campaign_ledger_status("missing"), lambda: campaign.campaign_ledger_next("missing"),
             lambda: campaign.campaign_ledger_record_result("missing", "op", result(head)), lambda: campaign.campaign_ledger_quarantine("missing", "op", "x"),
             lambda: campaign.campaign_ledger_stop("missing", "op", "x")]
    for call in calls: fails(call, "LEDGER_UNAVAILABLE")
    initialize(repo, contract); (repo / "dirty").write_text("x")
    fails(lambda: campaign.campaign_ledger_status("campaign-01"), "DIRTY_WORKTREE"); (repo / "dirty").unlink(); commit_change(repo); fails(lambda: campaign.campaign_ledger_status("campaign-01"), "STALE_HEAD")


def test_contract_gate_and_ledger_mutations_fail_closed(repo, contract, tmp_path):
    original_contract = Path(contract["path"]).read_text(); initialize(repo, contract); Path(contract["path"]).write_text('{"task":"mutated"}\n')
    fails(lambda: campaign.campaign_ledger_status("campaign-01"), "CONTRACT_MUTATED")
    other = tmp_path / "other.json"; other.write_text(original_contract)
    campaign.LEDGER_ROOT = tmp_path / "other-campaigns"; fresh = {"path": str(other), "sha256": campaign._json_sha256(json.loads(other.read_text()))}
    initialize(repo, fresh, "campaign-02"); (repo / "scripts/ci/architecture_slice_gate.py").write_text("mutated\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "gate mutation")
    fails(lambda: campaign.campaign_ledger_status("campaign-02"), "GATE_MUTATED")
    fresh_payload = json.loads(other.read_text()); fresh_payload["typed_contract"]["baseline_head"] = git(repo, "rev-parse", "HEAD"); fresh_payload["typed_contract"]["gate_sha"] = git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"); other.write_text(json.dumps(fresh_payload) + "\n"); fresh["sha256"] = campaign._json_sha256(fresh_payload)
    initialize(repo, fresh, "campaign-03"); path = Path(campaign.LEDGER_ROOT) / "campaign-03/state.json"; payload = json.loads(path.read_text()); payload["state"] = "COMMITTED"; path.write_text(json.dumps(payload)); fails(lambda: campaign.campaign_ledger_next("campaign-03"), "CHECKPOINT_MISMATCH")


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


def test_typed_contract_rejects_unknown_missing_malformed_and_duplicate_fields(tmp_path):
    valid = {
        "baseline_head": "HEAD",
        "gate_sha": "gate",
        "allowed_files": ["scripts/ci/householder_campaign.py"],
        "max_production_lines": 10,
        "max_test_lines": 10,
        "suite_ids": ["wrapper-unit"],
        "invariants": ["preserve"],
        "completed_seams": ["done-seam"],
        "completed_seam_files": {"done-seam": ["scripts/householder/done.py"]},
        "protected_files": ["scripts/ci/campaign_state.py"],
    }
    assert campaign._strict_contract(valid) == valid
    assert campaign._strict_contract({"typed_contract": valid}) == valid
    for invalid in (
        {**valid, "unexpected": True},
        {key: value for key, value in valid.items() if key != "gate_sha"},
        {**valid, "max_test_lines": "10"},
        {**valid, "suite_ids": ["not-allowed"]},
        {"typed_contract": valid, "unexpected": True},
    ):
        fails(lambda invalid=invalid: campaign._strict_contract({"typed_contract": invalid}), "CONTRACT_MALFORMED|SUITE_NOT_ALLOWED")
    reordered = {key: valid[key] for key in reversed(list(valid))}
    assert campaign._json_sha256(campaign._strict_contract(valid)) == campaign._json_sha256(campaign._strict_contract(reordered))
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"typed_contract": {"baseline_head":"HEAD", "baseline_head":"OTHER"}}')
    with pytest.raises(campaign.CampaignError, match="duplicate contract field"):
        campaign._read_json(duplicate)


@pytest.mark.parametrize("protected", [
    "scripts/ci/campaign_state.py",
    "scripts/ci/check_lane_scope.py",
    "scripts/ci/check_task_untracked.py",
    "scripts/ci/pre_commit_gate.py",
    "tests/unit/test_campaign_state.py",
])
def test_each_protected_file_is_rejected_before_event_append(repo, contract, protected):
    payload = json.loads(Path(contract["path"]).read_text())
    payload["typed_contract"]["allowed_files"] = [protected]
    path = Path(contract["path"]); path.write_text(json.dumps(payload) + "\n")
    item = {"path": str(path), "sha256": campaign._json_sha256(payload)}
    with pytest.raises(campaign.CampaignError, match="PROTECTED_FILE"):
        campaign.campaign_ledger_init("protected-" + protected.split("/")[-1], "init-protected", repo, git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"), [item])
    root = Path(campaign.LEDGER_ROOT) / ("protected-" + protected.split("/")[-1])
    assert not (root / "state.json").exists() and not (root / "events.jsonl").exists()


def test_completed_seam_id_and_file_overlap_are_rejected(repo, contract):
    payload = json.loads(Path(contract["path"]).read_text())
    payload["seam"] = "decision-policy"
    path = Path(contract["path"]); path.write_text(json.dumps(payload) + "\n")
    item = {"path": str(path), "sha256": campaign._json_sha256(payload)}
    with pytest.raises(campaign.CampaignError, match="COMPLETED_SEAM_OVERLAP"):
        campaign.campaign_ledger_init("completed-id", "init-completed-id", repo, git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"), [item])

    payload["seam"] = "new-seam"
    payload["typed_contract"]["allowed_files"] = ["scripts/householder/decision_policy.py"]
    path.write_text(json.dumps(payload) + "\n")
    item["sha256"] = campaign._json_sha256(payload)
    with pytest.raises(campaign.CampaignError, match="COMPLETED_SEAM_OVERLAP"):
        campaign.campaign_ledger_init("completed-file", "init-completed-file", repo, git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"), [item])


def test_baseline_mismatch_is_rejected_before_event_append(repo, contract):
    payload = json.loads(Path(contract["path"]).read_text())
    payload["typed_contract"]["baseline_head"] = "0" * 40
    path = Path(contract["path"]); path.write_text(json.dumps(payload) + "\n")
    item = {"path": str(path), "sha256": campaign._json_sha256(payload)}
    with pytest.raises(campaign.CampaignError, match="BASELINE_MISMATCH"):
        campaign.campaign_ledger_init("baseline-mismatch", "init-baseline-mismatch", repo, git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"), [item])
    root = Path(campaign.LEDGER_ROOT) / "baseline-mismatch"
    assert not (root / "state.json").exists() and not (root / "events.jsonl").exists()


def test_export_suite_and_gate_projection_are_wrapper_owned_and_restart_stable(repo, contract):
    assert campaign.SUITE_REGISTRY["export-preview-unit"][-1] == "tests/unit/test_export_preview_service.py"
    initialize(repo, contract)
    record = campaign.campaign_ledger_status("campaign-01")
    item = record["contracts"][0]
    assert item["gate_projection"]["authorized_files"] == []
    assert item["gate_projection_sha256"] == campaign._json_sha256(item["gate_projection"])
    loaded = importlib.reload(campaign)
    loaded.LEDGER_ROOT = Path(repo).parent / "campaigns"
    restarted = loaded.campaign_ledger_status("campaign-01")
    assert restarted["contracts"][0]["gate_projection"] == item["gate_projection"]
    tampered = dict(restarted)
    tampered["contracts"] = [dict(restarted["contracts"][0])]
    tampered["contracts"][0]["gate_projection"] = dict(item["gate_projection"], seam="tampered")
    with pytest.raises(loaded.CampaignError, match="CONTRACT_MUTATED"):
        loaded._ledger_validate(tampered)


def test_remediation_parity_suites_have_fixed_wrapper_owned_argv():
    expected = {
        "validation-unit": "tests/unit/test_validation_service.py",
        "ingestion-unit": "tests/unit/test_ingestion_service.py",
        "issue-recalculation-integration": "tests/integration/test_validation_review_workflows.py",
        "autosave-integration": "tests/integration/test_autosave_validation.py",
    }
    for suite_id, test_path in expected.items():
        assert campaign.SUITE_REGISTRY[suite_id] == [
            campaign.sys.executable,
            "-m",
            "pytest",
            "-q",
            test_path,
        ]


def test_gate_projection_is_stable_when_authorized_new_file_becomes_tracked(repo):
    baseline = git(repo, "rev-parse", "HEAD")
    item = {
        "task_id": "projection-stability",
        "seam_id": "projection-stability",
        "typed_contract": {
            "baseline_head": baseline,
            "gate_sha": git(repo, "hash-object", "scripts/ci/architecture_slice_gate.py"),
            "allowed_files": ["scripts/householder/new_policy.py"],
            "max_production_lines": 10,
            "max_test_lines": 0,
            "suite_ids": ["wrapper-unit"],
            "invariants": ["preserve behavior"],
            "completed_seams": [],
            "completed_seam_files": {},
            "protected_files": [],
        },
    }
    suites = [{"id": "wrapper-unit", "argv": list(campaign.SUITE_REGISTRY["wrapper-unit"])}]

    before = campaign._gate_projection(item, repo, suites)
    (repo / "scripts/householder/new_policy.py").parent.mkdir(parents=True, exist_ok=True)
    (repo / "scripts/householder/new_policy.py").write_text("POLICY = 'new'\n")
    git(repo, "add", "scripts/householder/new_policy.py")
    git(repo, "commit", "-qm", "track authorized new file")
    after = campaign._gate_projection(item, repo, suites)

    assert before == after
    assert before["allowed_new_production_files"] == ["scripts/householder/new_policy.py"]


def test_suite_registry_rejects_unknown_and_caller_argv():
    with pytest.raises(campaign.CampaignError, match="SUITE_NOT_ALLOWED"):
        campaign._suite_ids(["validation-unit", "tests/unit/test_ingestion_service.py"])
    assert campaign._suite_ids(["validation-unit"]) == ["validation-unit"]


def _edit_contract(repo, contract, allowed, production_limit=10):
    payload = json.loads(Path(contract["path"]).read_text())
    payload["typed_contract"]["allowed_files"] = allowed
    payload["typed_contract"]["max_production_lines"] = production_limit
    path = Path(contract["path"]).with_name("edit-" + Path(contract["path"]).name)
    path.write_text(json.dumps(payload) + "\n")
    return {"path": str(path), "sha256": campaign._json_sha256(payload)}


def test_checkpoint_allows_only_contained_admitted_dirty_edits_and_is_restart_safe(repo, contract, monkeypatch):
    edit_contract = _edit_contract(repo, contract, ["seed.txt"])
    initialize(repo, edit_contract)
    campaign.campaign_ledger_next("campaign-01"); campaign.campaign_ledger_start_edit("campaign-01", 0, "edit-1")
    (repo / "seed.txt").write_text("changed\n")
    events = Path(campaign.LEDGER_ROOT) / "campaign-01/events.jsonl"
    first = campaign.campaign_ledger_checkpoint("campaign-01", "checkpoint-1")
    before = events.read_bytes()
    assert campaign.campaign_ledger_checkpoint("campaign-01", "checkpoint-1") == first
    assert events.read_bytes() == before
    loaded = importlib.reload(campaign); monkeypatch.setattr(loaded, "LEDGER_ROOT", Path(repo).parent / "campaigns")
    assert loaded.campaign_ledger_checkpoint("campaign-01", "checkpoint-1") == first


def test_dirty_edit_checkpoint_rejects_unauthorized_and_over_ceiling_without_state_change(repo, contract):
    edit_contract = _edit_contract(repo, contract, ["seed.txt"], production_limit=1)
    initialize(repo, edit_contract); campaign.campaign_ledger_next("campaign-01"); campaign.campaign_ledger_start_edit("campaign-01", 0, "edit-1")
    state = Path(campaign.LEDGER_ROOT) / "campaign-01/state.json"; events = state.with_name("events.jsonl")
    (repo / "unauthorized.txt").write_text("bad\n"); before_state, before_events = state.read_bytes(), events.read_bytes()
    fails(lambda: campaign.campaign_ledger_checkpoint("campaign-01", "checkpoint-bad"), "UNAUTHORIZED_CHANGE")
    assert state.read_bytes() == before_state and events.read_bytes() == before_events
    (repo / "unauthorized.txt").unlink(); (repo / "seed.txt").write_text("one\ntwo\n")
    fails(lambda: campaign.campaign_ledger_checkpoint("campaign-01", "checkpoint-big"), "CEILING_EXCEEDED")
    assert state.read_bytes() == before_state and events.read_bytes() == before_events


def test_checkpoint_is_idempotent_persistent_and_stale_only_after_twelve_minutes(repo, contract, monkeypatch):
    initialize(repo, contract)
    fixed = campaign.datetime(2026, 1, 1, tzinfo=campaign.timezone.utc)
    monkeypatch.setattr(campaign, "_now_utc", lambda: fixed)
    first = campaign.campaign_ledger_checkpoint("campaign-01", "checkpoint-1")
    events = Path(campaign.LEDGER_ROOT) / "campaign-01/events.jsonl"
    before = events.read_bytes()
    assert campaign.campaign_ledger_checkpoint("campaign-01", "checkpoint-1") == first
    assert events.read_bytes() == before
    loaded = importlib.reload(campaign)
    monkeypatch.setattr(loaded, "LEDGER_ROOT", Path(repo).parent / "campaigns")
    assert loaded.campaign_ledger_checkpoint("campaign-01", "checkpoint-1") == first
    monkeypatch.setattr(loaded, "_now_utc", lambda: fixed + loaded.timedelta(minutes=11, seconds=59))
    loaded.campaign_ledger_status("campaign-01")
    monkeypatch.setattr(loaded, "_now_utc", lambda: fixed + loaded.timedelta(minutes=12, seconds=1))
    fails(lambda: loaded.campaign_ledger_status("campaign-01"), "CAMPAIGN_STALE")
    refreshed = loaded.campaign_ledger_checkpoint("campaign-01", "checkpoint-2")
    assert refreshed["checkpoint_at"].startswith("2026-01-01T00:12:01")


def discovery_findings(discovery_id="discovery-01", files=None):
    return {
        "schema_version": 1,
        "discovery_id": discovery_id,
        "findings": [{
            "finding_id": "finding-01",
            "title": "Mixed policy",
            "files": files or ["seed.txt"],
            "symbols": ["seed behavior"],
            "observed_evidence": "Focused inspection found one mixed responsibility.",
            "risk": "Policy drift.",
            "confidence": "high",
            "remediation_boundary": "Pure service-layer extraction only.",
            "required_tests": ["tests/unit/test_householder_campaign.py"],
            "estimated_size": "small",
            "dependencies": [],
            "disposition": "proven",
        }],
    }


def start_discovery(repo, tmp_path, monkeypatch, discovery_id="discovery-01"):
    monkeypatch.setattr(campaign, "repo_root", lambda: repo)
    monkeypatch.setattr(campaign, "DISCOVERY_RUN_ROOT", tmp_path / "discoveries")
    result = campaign.campaign_discovery_start(discovery_id, "start-" + discovery_id)
    findings = tmp_path / (discovery_id + "-findings.json")
    findings.write_text(json.dumps(discovery_findings(discovery_id)) + "\n")
    return result, findings


def test_discovery_happy_path_restart_and_exact_retries(repo, tmp_path, monkeypatch):
    started, findings = start_discovery(repo, tmp_path, monkeypatch)
    assert started["starting_head"] == git(repo, "rev-parse", "HEAD")
    checkpoint = campaign.campaign_discovery_checkpoint("discovery-01", "checkpoint-1", str(findings))
    events = Path(campaign.LEDGER_ROOT) / "discovery-01/events.jsonl"
    ledger_root = campaign.LEDGER_ROOT
    before = events.read_bytes()
    assert campaign.campaign_discovery_checkpoint("discovery-01", "checkpoint-1", str(findings)) == checkpoint
    assert events.read_bytes() == before
    loaded = importlib.reload(campaign)
    loaded.LEDGER_ROOT = ledger_root
    loaded.DISCOVERY_RUN_ROOT = tmp_path / "discoveries"
    loaded.repo_root = lambda: repo
    assert loaded._discovery_load("discovery-01")["state"] == "DISCOVERY_ACTIVE"
    finished = loaded.campaign_discovery_finish("discovery-01", "finish-1", str(findings))
    assert finished["state"] == "DISCOVERY_FINISHED"
    assert len(events.read_text().splitlines()) == 3
    assert loaded.campaign_discovery_finish("discovery-01", "finish-1", str(findings)) == finished
    assert json.loads(events.read_text().splitlines()[-1])["command"] == "DISCOVERY_FINISHED"


def test_discovery_conflict_and_strict_findings_fail_without_event(repo, tmp_path, monkeypatch):
    _, findings = start_discovery(repo, tmp_path, monkeypatch)
    campaign.campaign_discovery_checkpoint("discovery-01", "checkpoint-1", str(findings))
    events = Path(campaign.LEDGER_ROOT) / "discovery-01/events.jsonl"
    before = events.read_bytes()
    changed = json.loads(findings.read_text()); changed["findings"][0]["risk"] = "changed"
    findings.write_text(json.dumps(changed) + "\n")
    fails(lambda: campaign.campaign_discovery_checkpoint("discovery-01", "checkpoint-1", str(findings)), "OPERATION_CONFLICT")
    assert events.read_bytes() == before
    for text in (
        '{"schema_version":1,"discovery_id":"discovery-01","findings":[],"extra":true}',
        '{"schema_version":1,"discovery_id":"discovery-01","findings":[{"finding_id":"x","finding_id":"y"}]}',
    ):
        findings.write_text(text)
        fails(lambda: campaign.campaign_discovery_checkpoint("discovery-01", "checkpoint-bad", str(findings)), "DISCOVERY_RESULT_INVALID")
    assert events.read_bytes() == before


@pytest.mark.parametrize("mutation,expected", [
    ("tracked", "DISCOVERY_WORKTREE_CHANGED"),
    ("untracked", "DISCOVERY_WORKTREE_CHANGED"),
    ("head", "DISCOVERY_HEAD_CHANGED"),
])
def test_discovery_rejects_repository_mutation(repo, tmp_path, monkeypatch, mutation, expected):
    _, findings = start_discovery(repo, tmp_path, monkeypatch, "discovery-" + mutation)
    if mutation == "tracked":
        (repo / "seed.txt").write_text("changed\n")
    elif mutation == "untracked":
        (repo / "new.txt").write_text("new\n")
    else:
        (repo / "head.txt").write_text("head\n"); git(repo, "add", "head.txt"); git(repo, "commit", "-qm", "head change")
    events = Path(campaign.LEDGER_ROOT) / ("discovery-" + mutation + "/events.jsonl")
    before = events.read_bytes()
    fails(lambda: campaign.campaign_discovery_checkpoint("discovery-" + mutation, "checkpoint-1", str(findings)), expected)
    assert events.read_bytes() == before


def test_discovery_rejects_symlink_evidence_and_preserves_preexisting_dirty_state(repo, tmp_path, monkeypatch):
    outside = tmp_path / "outside.txt"; outside.write_text("outside\n")
    link = repo / "evidence-link"; link.symlink_to(outside)
    _, findings = start_discovery(repo, tmp_path, monkeypatch, "discovery-symlink")
    payload = discovery_findings("discovery-symlink", ["evidence-link"]); findings.write_text(json.dumps(payload) + "\n")
    events = Path(campaign.LEDGER_ROOT) / "discovery-symlink/events.jsonl"; before = events.read_bytes()
    fails(lambda: campaign.campaign_discovery_finish("discovery-symlink", "finish-1", str(findings)), "SYMLINK_ESCAPE")
    assert events.read_bytes() == before and link.is_symlink() and link.resolve() == outside


def test_discovery_stale_and_edit_admission_are_rejected(repo, tmp_path, monkeypatch):
    fixed = campaign.datetime(2026, 1, 1, tzinfo=campaign.timezone.utc)
    monkeypatch.setattr(campaign, "_now_utc", lambda: fixed)
    _, findings = start_discovery(repo, tmp_path, monkeypatch, "discovery-stale")
    campaign.campaign_discovery_checkpoint("discovery-stale", "checkpoint-before-stale", str(findings))
    monkeypatch.setattr(campaign, "_now_utc", lambda: fixed + campaign.timedelta(minutes=12, seconds=1))
    fails(lambda: campaign.campaign_discovery_checkpoint("discovery-stale", "checkpoint-1", str(findings)), "DISCOVERY_STALE")
    fails(lambda: campaign.campaign_ledger_start_edit("discovery-stale", 0, "edit-1"), "READ_ONLY_VIOLATION")


def test_discovery_commands_fail_closed_before_start(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "repo_root", lambda: repo)
    monkeypatch.setattr(campaign, "DISCOVERY_RUN_ROOT", tmp_path / "discoveries")
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps(discovery_findings("missing-discovery")) + "\n")
    fails(lambda: campaign.campaign_discovery_checkpoint("missing-discovery", "checkpoint-1", str(findings)), "DISCOVERY_NOT_STARTED")
    fails(lambda: campaign.campaign_discovery_finish("missing-discovery", "finish-1", str(findings)), "DISCOVERY_NOT_STARTED")
