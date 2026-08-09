"""Unit tests for the pre-commit hook gate."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts/ci"))

import pre_commit_gate  # noqa: E402
from pre_commit_gate import (  # noqa: E402
    EXPECTED_GATE_SPECS,
    PACKET_REPO_PATH,
    build_env,
    check_blocked_artifacts,
    check_commit_readiness,
    get_givebutter_dir,
    get_readiness_packet_path,
    get_venv_python,
    is_blocked_artifact,
    resolve_command,
    run_staged_tree_integrity_guard,
    run_task_untracked_guard,
    staged_diff_sha256,
    commit_mode,
    validate_readiness_packet,
    verify_venv_commands,
)

BASELINE_SHA = "a" * 40


def gate_result(
    gate_id: str,
    group: str,
    status: str = "passed",
    exit_code: int | None = 0,
    required: bool = True,
    command: str | None = None,
    exception_id: str | None = None,
) -> dict:
    default_command = EXPECTED_GATE_SPECS[gate_id]["command"] if gate_id in EXPECTED_GATE_SPECS else None
    return {
        "gate_id": gate_id,
        "group": group,
        "command": command
        or default_command
        or (
            "./.venv/bin/python scripts/ci/check_lane_scope.py --lane workflow-ci --verbose"
            if group == "scope"
            else "./.venv/bin/python scripts/ci/check_no_artifacts.py"
        ),
        "required": required,
        "status": status,
        "exit_code": exit_code,
        **({"exception_id": exception_id} if exception_id is not None else {}),
    }


def gate_exception(exception_id: str, *gate_ids: str) -> dict:
    return {
        "exception_id": exception_id,
        "exception_type": "mixed_scope_exception",
        "authorized": True,
        "applies_to_gate_ids": list(gate_ids),
    }


def valid_packet(diff_hash: str = "abc", head: str = "deadbeef", task_id: str = "TASK-1") -> dict:
    return {
        "schema_version": 2,
        "task_id": task_id,
        "reviewer_verdict": "VERDICT=ACCEPT",
        "breaker_verdict": "BREAKER=PASS",
        "qa_verdict": "QA=PASS",
        "canonical_gates_passed": True,
        "scope_guard_passed": True,
        "commit_authorized": True,
        "push_authorized": False,
        "reviewed_head": head,
        "reviewed_diff_sha256": diff_hash,
        "reviewed_at": "2026-07-23T12:00:00Z",
        "informational_notes": ["future hardening only"],
        "required_changes": [],
        "required_roles": ["Breaker", "QA", "Reviewer"],
        "gate_results": [
            gate_result("check_no_artifacts", "canonical"),
            gate_result("check_task_untracked", "canonical"),
            gate_result("check_staged_tree_integrity", "canonical"),
            gate_result("full_unit_integration_gate", "canonical"),
            gate_result("workflow_ci_lane_guard", "scope"),
        ],
        "authorized_exceptions": [],
    }


@pytest.fixture
def readiness_context(monkeypatch):
    monkeypatch.setattr("pre_commit_gate.list_staged_files", lambda: ["Givebutter/example.py"])
    monkeypatch.setattr("pre_commit_gate.get_current_head", lambda: "deadbeef")
    monkeypatch.setattr("pre_commit_gate.staged_diff_sha256", lambda: "abc")
    monkeypatch.setattr("pre_commit_gate.run_workflow_ci_lane_guard", lambda: SimpleNamespace(returncode=0))
    return {
        "HOUSEHOLDER_TASK_ID": "TASK-1",
        "HOUSEHOLDER_LANE": "workflow-ci",
        "HOUSEHOLDER_INTEGRATION_BASELINE": BASELINE_SHA,
    }


def test_build_env_prepends_givebutter_venv_bin(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/local/bin")
    assert build_env()["PATH"].startswith(f"{get_givebutter_dir() / '.venv/bin'}:")


def test_build_env_clears_transient_hook_environment(monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/wrong/.git")
    monkeypatch.setenv("GIT_WORK_TREE", "/wrong")
    monkeypatch.setenv("GIT_INDEX_FILE", "index.lock")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k unrelated")
    env = build_env()
    assert "GIT_DIR" not in env
    assert "GIT_WORK_TREE" not in env
    assert "PYTEST_ADDOPTS" not in env
    assert "GIT_INDEX_FILE" not in env


def test_commit_mode_defaults_to_normal_and_accepts_explicit_heavy():
    assert commit_mode({}) == "normal"
    assert commit_mode({"HOUSEHOLDER_COMMIT_MODE": "heavy"}) == "heavy"


def test_commit_mode_rejects_unknown_mode():
    with pytest.raises(ValueError, match="must be normal or heavy"):
        commit_mode({"HOUSEHOLDER_COMMIT_MODE": "bypass"})


def test_resolve_command_finds_project_venv_bins():
    env = build_env()
    assert str(get_givebutter_dir() / ".venv/bin") in (resolve_command("python", env) or "")
    assert str(get_givebutter_dir() / ".venv/bin") in (resolve_command("pytest", env) or "")


def test_venv_python_can_import_email_validator():
    result = subprocess.run(
        [str(get_venv_python()), "-c", "import sys, email_validator; print(sys.executable)"],
        cwd=get_givebutter_dir(), env=build_env(), capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert Path(result.stdout.strip()).resolve() == get_venv_python().resolve()


def test_is_blocked_artifact_detects_known_patterns():
    assert is_blocked_artifact("Givebutter/.DS_Store")
    assert is_blocked_artifact("Givebutter/screenshots/example.png")
    assert is_blocked_artifact("Givebutter/cache/__pycache__/module.pyc")
    assert not is_blocked_artifact("Givebutter/scripts/ci/pre_commit_gate.py")


def test_check_blocked_artifacts_blocks_staged_artifacts(monkeypatch, capsys):
    monkeypatch.setattr("pre_commit_gate.list_staged_files", lambda: ["Givebutter/screenshots/example.png"])
    assert check_blocked_artifacts() == 1
    assert "blocked artifact pattern" in capsys.readouterr().out


def test_verify_venv_commands_fails_when_commands_missing(monkeypatch, capsys):
    monkeypatch.setattr("pre_commit_gate.resolve_command", lambda command, env: None)
    assert verify_venv_commands(build_env()) == 1
    assert "virtualenv" in capsys.readouterr().err


def test_staged_diff_hashes_exact_bytes(monkeypatch):
    payload = b"diff --git a/x b/x\n"
    monkeypatch.setattr("pre_commit_gate.get_staged_diff_bytes", lambda: payload)
    assert staged_diff_sha256() == hashlib.sha256(payload).hexdigest()


def test_exact_accept_pass_pass_succeeds(readiness_context):
    assert validate_readiness_packet(valid_packet(), readiness_context) == []


def test_reviewer_required_breaker_not_required_succeeds(readiness_context):
    packet = valid_packet()
    packet["required_roles"] = ["Reviewer"]
    packet["breaker_verdict"] = "NOT_REQUIRED"
    packet["qa_verdict"] = "NOT_REQUIRED"
    assert validate_readiness_packet(packet, readiness_context) == []


def test_breaker_required_pass_succeeds(readiness_context):
    packet = valid_packet()
    packet["required_roles"] = ["Breaker", "Reviewer"]
    packet["qa_verdict"] = "NOT_REQUIRED"
    assert validate_readiness_packet(packet, readiness_context) == []


@pytest.mark.parametrize(
    ("roles", "breaker", "qa", "message"),
    [
        (["Breaker", "Reviewer"], "NOT_REQUIRED", "NOT_REQUIRED", "breaker_verdict"),
        (["QA", "Reviewer"], "NOT_REQUIRED", None, "qa_verdict"),
        (["Reviewer", "Unknown"], "NOT_REQUIRED", "NOT_REQUIRED", "required_roles"),
        (["Reviewer", "Reviewer"], "NOT_REQUIRED", "NOT_REQUIRED", "required_roles"),
        (["Breaker"], "NOT_REQUIRED", "NOT_REQUIRED", "Reviewer is always required"),
        (None, "NOT_REQUIRED", "NOT_REQUIRED", "required_roles"),
        ([" Reviewer "], "NOT_REQUIRED", "NOT_REQUIRED", "unknown roles"),
        (["Reviewer "], "NOT_REQUIRED", "NOT_REQUIRED", "unknown roles"),
        (["\tReviewer\n"], "NOT_REQUIRED", "NOT_REQUIRED", "unknown roles"),
        ([123], "NOT_REQUIRED", "NOT_REQUIRED", "role names"),
    ],
)
def test_required_role_state_fails_closed(readiness_context, roles, breaker, qa, message):
    packet = valid_packet()
    packet["required_roles"] = roles
    packet["breaker_verdict"] = breaker
    packet["qa_verdict"] = qa
    errors = validate_readiness_packet(packet, readiness_context)
    assert any(message in error for error in errors)


def baseline_debt_packet() -> dict:
    packet = valid_packet()
    packet["gate_results"][3].update(
        {
            "status": "baseline_debt_verified",
            "exit_code": 1,
            "evidence": {
                "baseline_sha": BASELINE_SHA,
                "current_staged_fingerprint": "abc",
                "command": "./.venv/bin/python -m pytest -q",
                "baseline_command": "./.venv/bin/python -m pytest -q",
                "current_command": "./.venv/bin/python -m pytest -q",
                "baseline_result": {"total": 1, "passed": 0, "failed": 1, "skipped": 0},
                "current_result": {"total": 1, "passed": 0, "failed": 1, "skipped": 0},
                "new_result": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
                "baseline_failing_identities": ["tests/unit/test_old.py::test_old"],
                "current_failing_identities": ["tests/unit/test_old.py::test_old"],
                "new_failing_identities": [],
                "no_new_failing_identities": True,
                "reviewed_head": "deadbeef",
                "reviewed_staged_fingerprint": "abc",
            },
        }
    )
    return packet


def test_valid_baseline_debt_evidence_is_accepted(readiness_context):
    packet = baseline_debt_packet()
    assert validate_readiness_packet(packet, readiness_context) == []


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda e: e.update(current_staged_fingerprint="wrong"), "staged fingerprint"),
        (lambda e: e.update(baseline_sha="wrong"), "baseline_sha"),
        (lambda e: e.update(command="wrong"), "command"),
        (lambda e: e.update(new_failing_identities="not-a-list"), "new_failing_identities"),
        (lambda e: e.update(new_failing_identities=None), "new_failing_identities"),
        (lambda e: e.update(new_failing_identities={}), "new_failing_identities"),
        (lambda e: e.update(new_failing_identities=[["tests/unit/test_new.py::test_new"]]), "new_failing_identities"),
        (lambda e: e.update(new_failing_identities=[""]), "new_failing_identities"),
        (lambda e: e.update(baseline_failing_identities=["tests/unit/test_old.py::test_old", "tests/unit/test_old.py::test_old"]), "duplicate"),
        (lambda e: e.update(current_failing_identities=["tests/unit/test_old.py::test_old", "tests/unit/test_new.py::test_new"], new_failing_identities=["tests/unit/test_new.py::test_new"], no_new_failing_identities=False, current_result={"total": 2, "passed": 0, "failed": 2, "skipped": 0}), "current-only"),
        (lambda e: e.pop("baseline_failing_identities"), "missing"),
        (lambda e: e.update(baseline_failing_identities=[123]), "valid normalized"),
        (lambda e: e.update(baseline_result={"total": 2, "passed": 0, "failed": 2, "skipped": 0}), "failed"),
        (lambda e: e.update(current_result={"total": 2, "passed": 0, "failed": 2, "skipped": 0}), "failed"),
        (lambda e: e.update(new_result={"total": 1, "passed": 0, "failed": 1, "skipped": 0}), "new_result"),
        (lambda e: e.update(baseline_result={"total": 3, "passed": 0, "failed": 1, "skipped": 0}), "sum"),
        (lambda e: e.update(reviewed_head="stale"), "reviewed_head"),
        (lambda e: e.update(reviewed_staged_fingerprint="stale"), "reviewed fingerprint"),
    ],
)
def test_baseline_debt_evidence_fails_closed(readiness_context, mutation, message):
    packet = baseline_debt_packet()
    mutation(packet["gate_results"][3]["evidence"])
    errors = validate_readiness_packet(packet, readiness_context)
    assert any(message in error for error in errors)


@pytest.mark.parametrize("missing_key", ["total", "passed", "failed", "skipped"])
def test_baseline_debt_rejects_incomplete_result_counts(readiness_context, missing_key):
    packet = baseline_debt_packet()
    packet["gate_results"][3]["evidence"]["current_result"].pop(missing_key)
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("current_result is missing required counts" in error for error in errors)


def test_baseline_debt_rejects_unknown_evidence_fields(readiness_context):
    packet = baseline_debt_packet()
    packet["gate_results"][3]["evidence"]["unexpected"] = True
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("unknown fields" in error for error in errors)


def test_baseline_debt_rejects_unknown_result_count(readiness_context):
    packet = baseline_debt_packet()
    packet["gate_results"][3]["evidence"]["current_result"]["errors"] = 0
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("unknown counts" in error for error in errors)


def test_schema_version_two_required(readiness_context):
    packet = valid_packet()
    packet["schema_version"] = 1
    assert any("schema_version" in e for e in validate_readiness_packet(packet, readiness_context))


def test_malformed_gate_ledger_values_return_structured_errors(monkeypatch, readiness_context):
    monkeypatch.setattr("pre_commit_gate.run_workflow_ci_lane_guard", lambda: MagicMock(returncode=1))
    packet = valid_packet()
    packet["gate_results"][4]["status"] = "failed"
    packet["gate_results"][4]["exit_code"] = 1
    packet["gate_results"][4]["exception_id"] = "mixed-scope-1"
    packet["canonical_gates_passed"] = True
    packet["scope_guard_passed"] = False
    packet["commit_authorized"] = True
    packet["gate_results"][0]["gate_id"] = []
    packet["gate_results"][0]["group"] = []
    packet["gate_results"][0]["status"] = []
    packet["authorized_exceptions"] = [
        {
            "exception_id": "mixed-scope-1",
            "exception_type": [],
            "authorized": True,
            "applies_to_gate_ids": ["workflow_ci_lane_guard"],
        }
    ]
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("gate_id" in e for e in errors)
    assert any("group" in e for e in errors)
    assert any("status" in e for e in errors)
    assert any("exception_type" in e for e in errors)


@pytest.mark.parametrize("value", ["Accept", "Accept with minor follow-up", "VERDICT=REQUEST_CHANGES", "VERDICT=REJECT"])
def test_invalid_or_nonaccept_reviewer_verdict_fails(value, readiness_context):
    packet = valid_packet(); packet["reviewer_verdict"] = value
    assert any("reviewer_verdict" in e for e in validate_readiness_packet(packet, readiness_context))


@pytest.mark.parametrize("field,value", [("breaker_verdict", None), ("breaker_verdict", "pass"), ("qa_verdict", None), ("qa_verdict", "Pass")])
def test_missing_or_invalid_breaker_qa_fails(field, value, readiness_context):
    packet = valid_packet(); packet[field] = value
    assert any(field in e for e in validate_readiness_packet(packet, readiness_context))


def test_summary_booleans_must_match_gate_results(readiness_context):
    canonical_mismatch = valid_packet()
    canonical_mismatch["canonical_gates_passed"] = False
    assert any("canonical_gates_passed" in e for e in validate_readiness_packet(canonical_mismatch, readiness_context))

    scope_mismatch = valid_packet()
    scope_mismatch["scope_guard_passed"] = False
    assert any("scope_guard_passed" in e for e in validate_readiness_packet(scope_mismatch, readiness_context))


def test_commit_authorized_false_fails(readiness_context):
    packet = valid_packet(); packet["commit_authorized"] = False
    assert any("commit_authorized" in e for e in validate_readiness_packet(packet, readiness_context))


def test_valid_packet_requires_lane_guard_pass(monkeypatch, readiness_context):
    packet = valid_packet()
    monkeypatch.setattr("pre_commit_gate.run_workflow_ci_lane_guard", lambda: SimpleNamespace(returncode=1))
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("must pass for packets without an authorized mixed-scope exception" in e for e in errors)


def test_required_changes_blocks(readiness_context):
    packet = valid_packet(); packet["required_changes"] = ["fix this"]
    assert any("required_changes" in e for e in validate_readiness_packet(packet, readiness_context))


def test_informational_notes_do_not_block(readiness_context):
    packet = valid_packet(); packet["informational_notes"] = ["DB guard for future multi-worker support"]
    assert validate_readiness_packet(packet, readiness_context) == []


def test_task_mismatch_and_missing_env_fail(readiness_context):
    packet = valid_packet(task_id="OTHER")
    assert any("task_id" in e for e in validate_readiness_packet(packet, readiness_context))
    assert any("HOUSEHOLDER_TASK_ID" in e for e in validate_readiness_packet(valid_packet(), {}))


def test_head_and_fingerprint_mismatch_fail(readiness_context):
    packet = valid_packet(head="old", diff_hash="old")
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("reviewed_head" in e for e in errors)
    assert any("reviewed_diff_sha256" in e for e in errors)


def test_failed_scope_gate_requires_structured_exception(readiness_context):
    packet = valid_packet()
    packet["canonical_gates_passed"] = True
    packet["scope_guard_passed"] = False
    packet["commit_authorized"] = False
    packet["gate_results"][4]["status"] = "failed"
    packet["gate_results"][4]["exit_code"] = 1
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("authorized" in e for e in errors)
    assert any("commit_authorized" in e for e in errors)


def test_failed_scope_gate_with_matching_exception_passes(monkeypatch, readiness_context):
    packet = valid_packet()
    packet["canonical_gates_passed"] = True
    packet["scope_guard_passed"] = False
    packet["commit_authorized"] = True
    packet["gate_results"][4]["status"] = "failed"
    packet["gate_results"][4]["exit_code"] = 1
    packet["gate_results"][4]["exception_id"] = "mixed-scope-1"
    packet["authorized_exceptions"] = [gate_exception("mixed-scope-1", "workflow_ci_lane_guard")]
    monkeypatch.setattr("pre_commit_gate.run_workflow_ci_lane_guard", lambda: SimpleNamespace(returncode=1))
    assert validate_readiness_packet(packet, readiness_context) == []


def test_failed_scope_gate_with_lane_guard_crash_fails_closed(monkeypatch, readiness_context):
    packet = valid_packet()
    packet["canonical_gates_passed"] = True
    packet["scope_guard_passed"] = False
    packet["commit_authorized"] = True
    packet["gate_results"][4]["status"] = "failed"
    packet["gate_results"][4]["exit_code"] = 1
    packet["gate_results"][4]["exception_id"] = "mixed-scope-1"
    packet["authorized_exceptions"] = [gate_exception("mixed-scope-1", "workflow_ci_lane_guard")]
    monkeypatch.setattr("pre_commit_gate.run_workflow_ci_lane_guard", lambda: None)
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("could not be executed" in e for e in errors)


def test_failed_scope_gate_with_nonstandard_lane_exit_fails_closed(monkeypatch, readiness_context):
    packet = valid_packet()
    packet["canonical_gates_passed"] = True
    packet["scope_guard_passed"] = False
    packet["commit_authorized"] = True
    packet["gate_results"][4]["status"] = "failed"
    packet["gate_results"][4]["exit_code"] = 1
    packet["gate_results"][4]["exception_id"] = "mixed-scope-1"
    packet["authorized_exceptions"] = [gate_exception("mixed-scope-1", "workflow_ci_lane_guard")]
    monkeypatch.setattr("pre_commit_gate.run_workflow_ci_lane_guard", lambda: SimpleNamespace(returncode=2))
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("must exit 1" in e for e in errors)


def test_missing_scope_gate_fails(readiness_context):
    packet = valid_packet()
    packet["gate_results"] = [packet["gate_results"][0]]
    packet["canonical_gates_passed"] = True
    packet["scope_guard_passed"] = True
    packet["commit_authorized"] = True
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("missing required gate_ids" in e for e in errors)


def test_missing_canonical_gate_fails(readiness_context):
    packet = valid_packet()
    packet["gate_results"] = [packet["gate_results"][3]]
    packet["canonical_gates_passed"] = True
    packet["scope_guard_passed"] = True
    packet["commit_authorized"] = True
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("missing required gate_ids" in e for e in errors)


def test_required_false_gate_fails(readiness_context):
    packet = valid_packet()
    packet["gate_results"][3]["required"] = False
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("required must be true" in e for e in errors)


def test_failed_canonical_gate_cannot_be_exception_authorized(readiness_context):
    packet = valid_packet()
    packet["canonical_gates_passed"] = False
    packet["commit_authorized"] = False
    packet["gate_results"][0]["status"] = "failed"
    packet["gate_results"][0]["exit_code"] = 1
    packet["gate_results"][0]["exception_id"] = "mixed-scope-1"
    packet["authorized_exceptions"] = [gate_exception("mixed-scope-1", "check_no_artifacts")]
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("cannot be exception-authorized" in e for e in errors)
    assert any("commit_authorized" in e for e in errors)


def test_required_gate_not_run_fails(readiness_context):
    packet = valid_packet()
    packet["scope_guard_passed"] = False
    packet["canonical_gates_passed"] = True
    packet["commit_authorized"] = False
    packet["gate_results"][3]["status"] = "not_run"
    packet["gate_results"][3]["exit_code"] = None
    errors = validate_readiness_packet(packet, readiness_context)
    assert any("not_run" in e for e in errors)


def test_packet_cannot_be_staged(monkeypatch, readiness_context):
    monkeypatch.setattr("pre_commit_gate.list_staged_files", lambda: [PACKET_REPO_PATH])
    assert any("must not be staged" in e for e in validate_readiness_packet(valid_packet(), readiness_context))


def test_push_authorization_is_independent(readiness_context):
    packet = valid_packet(); packet["push_authorized"] = False
    assert validate_readiness_packet(packet, readiness_context) == []


def test_unstaged_changes_do_not_affect_staged_fingerprint(monkeypatch):
    first = b"staged-only"
    monkeypatch.setattr("pre_commit_gate.get_staged_diff_bytes", lambda: first)
    before = staged_diff_sha256()
    # An unstaged working-tree change is deliberately absent from the canonical staged-diff bytes.
    after = staged_diff_sha256()
    assert before == after


def test_missing_and_malformed_packet_fail(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr("pre_commit_gate.get_readiness_packet_path", lambda: missing)
    assert check_commit_readiness({"HOUSEHOLDER_TASK_ID": "TASK-1"}) == 1
    missing.write_text("{not-json", encoding="utf-8")
    assert check_commit_readiness({"HOUSEHOLDER_TASK_ID": "TASK-1"}) == 1
    assert "COMMIT BLOCKED" in capsys.readouterr().out


def test_valid_packet_file_passes(monkeypatch, tmp_path, readiness_context):
    path = tmp_path / "commit-readiness.json"
    path.write_text(json.dumps(valid_packet()), encoding="utf-8")
    monkeypatch.setattr("pre_commit_gate.get_readiness_packet_path", lambda: path)
    assert check_commit_readiness(readiness_context) == 0


def test_run_task_untracked_guard_preserves_failure_exit_code(monkeypatch):
    monkeypatch.setattr("pre_commit_gate.subprocess.run", lambda *args, **kwargs: MagicMock(returncode=4))
    assert run_task_untracked_guard().returncode == 4


def test_run_staged_tree_integrity_guard_preserves_failure_exit_code(monkeypatch):
    monkeypatch.setattr("pre_commit_gate.subprocess.run", lambda *args, **kwargs: MagicMock(returncode=6))
    assert run_staged_tree_integrity_guard().returncode == 6


def test_main_normal_mode_skips_readiness_but_keeps_scope_guards(monkeypatch, capsys):
    calls: list[str] = []

    monkeypatch.setattr("pre_commit_gate.verify_venv_commands", lambda env: calls.append("verify") or 0)
    monkeypatch.setattr(
        "pre_commit_gate.run_task_untracked_guard",
        lambda: calls.append("task") or SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        "pre_commit_gate.run_staged_tree_integrity_guard",
        lambda: calls.append("staged") or SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr("pre_commit_gate.check_blocked_artifacts", lambda: calls.append("artifacts") or 0)
    monkeypatch.setattr("pre_commit_gate.run_declared_lane_guard", lambda env: calls.append("lane") or SimpleNamespace(returncode=0))
    monkeypatch.setattr("pre_commit_gate.check_commit_readiness", lambda env: calls.append("readiness") or 0)

    assert pre_commit_gate.main() == 0
    assert calls == ["verify", "task", "staged", "artifacts", "lane"]
    assert "Pre-commit" in capsys.readouterr().out


def test_main_heavy_mode_runs_readiness(monkeypatch):
    calls: list[str] = []
    monkeypatch.setenv("HOUSEHOLDER_COMMIT_MODE", "heavy")
    monkeypatch.setattr("pre_commit_gate.verify_venv_commands", lambda env: 0)
    monkeypatch.setattr("pre_commit_gate.run_task_untracked_guard", lambda: SimpleNamespace(returncode=0))
    monkeypatch.setattr("pre_commit_gate.run_staged_tree_integrity_guard", lambda: SimpleNamespace(returncode=0))
    monkeypatch.setattr("pre_commit_gate.check_blocked_artifacts", lambda: 0)
    monkeypatch.setattr("pre_commit_gate.run_declared_lane_guard", lambda env: SimpleNamespace(returncode=0))
    monkeypatch.setattr("pre_commit_gate.check_commit_readiness", lambda env: calls.append("readiness") or 0)
    assert pre_commit_gate.main() == 0
    assert calls == ["readiness"]
