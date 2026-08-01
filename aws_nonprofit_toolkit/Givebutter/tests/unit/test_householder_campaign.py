from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

import householder_campaign  # noqa: E402


TASK_ID = "HOUSEHOLDER-CAMPAIGN-MODULE-V2-20260801"
_GIT_ENV_STRIP = (
    "GIT_INDEX_FILE",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in _GIT_ENV_STRIP:
        env.pop(key, None)
    return env


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=check, env=git_env())


@pytest.fixture(autouse=True)
def sanitize_git_subprocesses(monkeypatch):
    original_run = subprocess.run

    def sanitized_run(*args, **kwargs):
        env = dict(kwargs.get("env", os.environ.copy()))
        for key in _GIT_ENV_STRIP:
            env.pop(key, None)
        kwargs["env"] = env
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", sanitized_run)
    yield


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    origin = tmp_path / "origin.git"
    repo.mkdir(parents=True, exist_ok=True)
    origin.mkdir(parents=True, exist_ok=True)
    git(origin, "init", "--bare")
    git(repo, "init")
    git(repo, "branch", "-M", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(repo, "add", "seed.txt")
    git(repo, "commit", "-m", "seed")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-u", "origin", "main")
    git(repo, "fetch", "origin", "main")
    return repo


def bind(monkeypatch, repo: Path) -> None:
    monkeypatch.setattr(householder_campaign, "repo_root", lambda: repo)


def record_path(repo: Path, task_id: str = TASK_ID) -> Path:
    return repo / "Givebutter/.artifacts" / f"householder-campaign.{task_id}.json"


def read_record(repo: Path, task_id: str = TASK_ID) -> dict[str, object]:
    return json.loads(record_path(repo, task_id).read_text(encoding="utf-8"))


def write_record(repo: Path, payload: dict[str, object], task_id: str = TASK_ID) -> None:
    record_path(repo, task_id).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_contract(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def contract_payload(*, campaign_type: str = "workflow", work_item_prefix: str = "item") -> dict[str, object]:
    return {
        "schema_version": 1,
        "task_id": TASK_ID,
        "campaign_type": campaign_type,
        "workflow_id": "workflow-01",
        "strategy_id": "strategy-01",
        "work_items": [
            {
                "id": f"{work_item_prefix}-0",
                "type": "inspect-work-item",
                "description": "inspect the initial work item",
                "acceptance_criteria": ["item inspected"],
                "focused_test_commands": [["python", "-c", "print('inspect')"]],
                "allowed_action_types": ["inspect-work-item", "start-edit"],
            },
            {
                "id": f"{work_item_prefix}-1",
                "type": "start-edit",
                "description": "open the edit batch",
                "acceptance_criteria": ["edit batch started"],
                "focused_test_commands": [["python", "-c", "print('edit')"]],
                "allowed_action_types": ["start-edit", "run-focused", "completed"],
            },
        ],
        "authorized_files": [
            "Givebutter/scripts/ci/householder_runner.py",
            "Givebutter/tests/unit/test_householder_campaign.py",
        ],
        "implementation_changed_lines_max": 350,
        "test_changed_lines_max": 450,
        "tracked_files_max": 2,
        "focused_runs_max": 4,
        "implementation_repairs_max": 1,
        "test_harness_repairs_max": 1,
        "review_repairs_max": 1,
    }


def test_initialize_and_status_are_deterministic(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    contract_file = write_contract(tmp_path / "contract.json", contract_payload())

    report = householder_campaign.campaign_initialize(TASK_ID, contract_file)
    record_before = record_path(repo).read_bytes()
    status = householder_campaign.campaign_status(TASK_ID)
    record_after = record_path(repo).read_bytes()

    assert report == status
    assert report["task_id"] == TASK_ID
    assert report["campaign_type"] == "workflow"
    assert report["current_work_item_index"] == 0
    assert report["pending_action"] is None
    assert report["final_state"] == "active"
    assert report["stop_reason"] is None
    assert report["work_item_statuses"] == ["pending", "pending"]
    assert report["counters"] == {
        "focused_runs_used": 0,
        "implementation_repairs_used": 0,
        "review_repairs_used": 0,
        "test_harness_repairs_used": 0,
    }
    assert record_before == record_after


def test_schema_and_required_field_validation(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    contract_file = tmp_path / "contract.json"

    missing = contract_payload()
    missing.pop("workflow_id")
    write_contract(contract_file, missing)
    with pytest.raises(ValueError, match="missing required fields"):
        householder_campaign.campaign_initialize(TASK_ID, contract_file)

    invalid = contract_payload()
    invalid["schema_version"] = 2
    write_contract(contract_file, invalid)
    with pytest.raises(ValueError, match="unsupported campaign contract schema"):
        householder_campaign.campaign_initialize(TASK_ID, contract_file)


def test_duplicate_ids_and_paths_are_rejected(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    contract_file = tmp_path / "contract.json"

    duplicate_ids = contract_payload()
    duplicate_ids["work_items"][1]["id"] = duplicate_ids["work_items"][0]["id"]
    write_contract(contract_file, duplicate_ids)
    with pytest.raises(ValueError, match="duplicate work-item IDs"):
        householder_campaign.campaign_initialize(TASK_ID, contract_file)

    duplicate_paths = contract_payload()
    duplicate_paths["authorized_files"] = [
        "Givebutter/scripts/ci/householder_runner.py",
        "Givebutter/scripts/ci/householder_runner.py",
    ]
    write_contract(contract_file, duplicate_paths)
    with pytest.raises(ValueError, match="duplicate authorized_files"):
        householder_campaign.campaign_initialize(TASK_ID, contract_file)

    non_normalized = contract_payload()
    non_normalized["authorized_files"] = [
        "Givebutter/scripts/ci/householder_runner.py",
        "./Givebutter/tests/unit/test_householder_campaign.py",
    ]
    write_contract(contract_file, non_normalized)
    with pytest.raises(ValueError, match="normalized"):
        householder_campaign.campaign_initialize(TASK_ID, contract_file)


def test_stable_normalized_digest_and_campaign_type_does_not_change_mechanics(monkeypatch, tmp_path):
    repo_a = make_repo(tmp_path / "workflow")
    repo_b = make_repo(tmp_path / "audit")
    contract_file = tmp_path / "contract.json"

    bind(monkeypatch, repo_a)
    monkeypatch.chdir(repo_a)
    workflow = contract_payload(campaign_type="workflow")
    digest_workflow = householder_campaign.campaign_initialize(TASK_ID, write_contract(contract_file, workflow))["contract_sha256"]

    bind(monkeypatch, repo_b)
    monkeypatch.chdir(repo_b)
    audit = contract_payload(campaign_type="audit")
    digest_audit = householder_campaign.campaign_initialize(TASK_ID, write_contract(contract_file, audit))["contract_sha256"]

    assert digest_workflow == digest_audit
    workflow_status = householder_campaign.campaign_status(TASK_ID)
    assert workflow_status["campaign_type"] == "audit"
    assert workflow_status["current_work_item_index"] == 0
    assert workflow_status["pending_action"] is None
    assert workflow_status["final_state"] == "active"


def test_initialization_is_atomic_and_reinitialization_is_rejected(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    contract_file = write_contract(tmp_path / "contract.json", contract_payload())
    record_file = record_path(repo)

    original_replace = householder_campaign.os.replace

    def failing_replace(*_args, **_kwargs):
        raise OSError("boom")

    monkeypatch.setattr(householder_campaign.os, "replace", failing_replace)
    with pytest.raises(OSError, match="boom"):
        householder_campaign.campaign_initialize(TASK_ID, contract_file)
    assert not record_file.exists()

    monkeypatch.setattr(householder_campaign.os, "replace", original_replace)
    result = householder_campaign.campaign_initialize(TASK_ID, contract_file)
    assert result["final_state"] == "active"

    with pytest.raises(ValueError, match="reinitialization rejected"):
        householder_campaign.campaign_initialize(TASK_ID, contract_file)


def test_mutation_and_digest_mismatch_are_rejected(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    contract_file = write_contract(tmp_path / "contract.json", contract_payload())
    householder_campaign.campaign_initialize(TASK_ID, contract_file)

    mutated = read_record(repo)
    mutated["contract"]["workflow_id"] = "mutated"
    write_record(repo, mutated)
    with pytest.raises(ValueError, match="contract digest mismatch"):
        householder_campaign.campaign_status(TASK_ID)

    corrupted = read_record(repo)
    corrupted["contract_sha256"] = "0" * 64
    write_record(repo, corrupted)
    with pytest.raises(ValueError, match="contract digest mismatch"):
        householder_campaign.campaign_status(TASK_ID)


def test_campaign_status_returns_deterministic_json_payload(monkeypatch, tmp_path):
    repo = make_repo(tmp_path)
    bind(monkeypatch, repo)
    monkeypatch.chdir(repo)
    contract_file = write_contract(tmp_path / "contract.json", contract_payload())

    householder_campaign.campaign_initialize(TASK_ID, contract_file)
    first = householder_campaign.campaign_status(TASK_ID)
    second = householder_campaign.campaign_status(TASK_ID)

    assert first == second
    assert first["contract_sha256"] == second["contract_sha256"]
