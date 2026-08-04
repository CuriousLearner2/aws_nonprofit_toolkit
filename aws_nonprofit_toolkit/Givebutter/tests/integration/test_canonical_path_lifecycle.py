"""Synthetic nested launcher/wrapper lifecycle coverage for canonical paths."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts" / "ci"))
from scripts.ci import householder_launcher as launcher


BASELINE = "5f967fc7024253d0cf369f3ece4253adfb60b109"
TARGET = "tests/integration/test_autosave_validation.py"
GIT_TARGET = "aws_nonprofit_toolkit/Givebutter/" + TARGET


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True).stdout.strip()


def _contract(path: Path, allowed: str, gate_sha: str) -> Path:
    value = {
        "typed_contract": {
            "baseline_head": BASELINE,
            "gate_sha": gate_sha,
            "allowed_files": [TARGET],
            "max_production_lines": 100,
            "max_test_lines": 100,
            "suite_ids": ["wrapper-unit"],
            "invariants": ["canonical paths are project-relative"],
            "completed_seams": [],
            "completed_seam_files": {},
            "protected_files": [],
        }
    }
    result = path / ("contract-" + allowed.replace("/", "_") + ".json")
    result.write_text(json.dumps(value) + "\n", encoding="utf-8")
    return result


def _run_case(tmp_path: Path, source: Path, authorization: str) -> dict:
    campaign_id = "canonical-nested-" + tmp_path.name[-8:]
    form = "project" if authorization == TARGET else "git"
    launcher.MIRROR_PATH = source
    launcher.LAUNCH_ROOT = tmp_path / (campaign_id + "-" + form + "-launch")
    launcher.STATE_ROOT = tmp_path / (campaign_id + "-" + form + "-state")
    launcher.LOCK_ROOT = tmp_path / (campaign_id + "-" + form + "-lock")
    original_wrapper = launcher._wrapper
    def load_wrapper(project):
        wrapper = original_wrapper(project)
        wrapper.LEDGER_ROOT = tmp_path / (campaign_id + "-" + form + "-ledger")
        return wrapper
    launcher._wrapper = load_wrapper
    gate_sha = _git(source, "hash-object", "aws_nonprofit_toolkit/Givebutter/scripts/ci/architecture_slice_gate.py")
    contract = _contract(tmp_path, authorization, gate_sha)
    payload = {
        "baseline": BASELINE,
        "campaign_id": campaign_id,
        "mode": "campaign",
        "authorized_production_paths": [],
        "authorized_test_paths": [authorization],
        "suite_ids": ["wrapper-unit"],
        "time_limit_seconds": 120,
        "typed_contract": str(contract),
    }
    doctor = launcher.doctor(payload)
    assert doctor["status"] == "READY", doctor
    launched = launcher.launch(payload)
    assert launched["status"] == "ready"
    project = Path(launched["project_root"])
    assert launched["wrapper_state"]["authorized_files"] == [TARGET]
    wrapper = launcher._wrapper(project)
    ledger = Path(launched["ledger_path"])
    before_events = ledger.with_name("events.jsonl").read_text(encoding="utf-8").splitlines()
    target = project / TARGET
    original = target.read_text(encoding="utf-8")
    target.write_text(original.replace("def test_", "def test_canonical_", 1), encoding="utf-8")
    finish = wrapper.campaign_ledger_finish_edit(campaign_id, 0, campaign_id + "-finish")
    retry_events = ledger.with_name("events.jsonl").read_text(encoding="utf-8").splitlines()
    retry = wrapper.campaign_ledger_finish_edit(campaign_id, 0, campaign_id + "-finish")
    assert retry == finish
    assert ledger.with_name("events.jsonl").read_text(encoding="utf-8").splitlines() == retry_events
    _git(project, "config", "user.email", "canonical-path-test@example.com")
    _git(project, "config", "user.name", "Canonical Path Test")
    _git(project, "add", TARGET)
    _git(project, "commit", "-m", "synthetic canonical lifecycle")
    committed = _git(project, "rev-parse", "HEAD")
    result = wrapper.campaign_ledger_record_result(campaign_id, campaign_id + "-result", {"contract_index": 0})
    result_retry = wrapper.campaign_ledger_record_result(campaign_id, campaign_id + "-result", {"contract_index": 0})
    assert result_retry == result
    events = [json.loads(line) for line in ledger.with_name("events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [event["command"] for event in events] == ["init", "next", "EDIT_STARTED", "EDIT_VALIDATED", "record-result"]
    assert len(events) == len(set(event["event_hash"] for event in events))
    assert result["state"] == "COMMITTED"
    assert result["current_head"] == committed
    committed_paths = [line.split("\t", 1)[1] for line in _git(project, "diff", "--name-status", BASELINE, "HEAD").splitlines()]
    committed_paths = [path.removeprefix("aws_nonprofit_toolkit/Givebutter/") for path in committed_paths]
    return {
        "authorized": launched["wrapper_state"]["authorized_files"],
        "changed": finish["changed_files"],
        "gate": finish["gate_result"],
        "diff_totals": finish["diff_totals"],
        "patch_sha": finish["patch_sha"],
        "committed": committed_paths,
        "events": [event["command"] for event in events],
        "project": str(project),
    }


def test_nested_lifecycle_equivalent_authorization_forms(tmp_path):
    source = Path(__file__).parents[4]
    project = _run_case(tmp_path, source, TARGET)
    git_root = _run_case(tmp_path, source, GIT_TARGET)
    assert project["authorized"] == git_root["authorized"] == [TARGET]
    assert project["changed"] == git_root["changed"]
    assert project["gate"] == git_root["gate"]
    assert project["diff_totals"] == git_root["diff_totals"]
    assert project["patch_sha"] == git_root["patch_sha"]
    assert project["committed"] == git_root["committed"] == [TARGET]
    assert project["events"] == git_root["events"]
