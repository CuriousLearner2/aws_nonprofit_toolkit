from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))

import pre_commit_gate  # noqa: E402
import runtime_evidence  # noqa: E402


TASK_ID = "HOUSEHOLDER-RUNTIME-EVIDENCE-TASK-ID-FIX-20260731"
OLD_TASK_ID = "HOUSEHOLDER-60-MINUTE-AUTONOMY-TRIAL-20260731"
FAKE_DIFF = b"fake-diff"
FAKE_FINGERPRINT = hashlib.sha256(FAKE_DIFF).hexdigest()


@pytest.fixture(autouse=True)
def workflow_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOUSEHOLDER_LANE", "workflow-ci")


def _result(returncode: int = 0, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _ledger_snapshot(
    fingerprint: str = FAKE_FINGERPRINT,
    task_id: str = TASK_ID,
    *,
    state: str = "review_green",
    acceptance_green: bool = True,
    review_fingerprint: str | None = None,
) -> dict[str, object]:
    return {
        "acceptance_green": acceptance_green,
        "active_batch": "primary",
        "counters": {
            "focused_runs_allowed": 4,
            "focused_runs_used": 2,
            "implementation_repair_allowed": 1,
            "implementation_repair_used": 0,
            "primary_allowed": 1,
            "primary_used": 1,
            "review_cycles_allowed": 2,
            "review_cycles_used": 1,
            "review_repair_allowed": 1,
            "review_repair_used": 0,
            "test_harness_repair_allowed": 1,
            "test_harness_repair_used": 0,
        },
        "deadline_at": None,
        "environment_retry_used": False,
        "failure_classified": False,
        "failure_type": None,
        "focused_run_active": False,
        "remaining": {
            "environment_retries": 1,
            "focused_runs": 2,
            "implementation_repairs": 1,
            "primary_batches": 0,
            "review_cycles": 1,
            "review_repairs": 1,
            "test_harness_repairs": 1,
        },
        "review_active": False,
        "review_fingerprint": fingerprint if review_fingerprint is None else review_fingerprint,
        "schema_version": 1,
        "state": state,
        "task_id": task_id,
        "terminal_reason": None,
    }


def _receipts(
    fingerprint: str = FAKE_FINGERPRINT,
    head: str = "deadbeef",
    task_id: str = TASK_ID,
) -> tuple[dict[str, object], dict[str, object]]:
    reviewer = {
        "task_id": task_id,
        "verdict": "VERDICT=ACCEPT",
        "reviewed_head": head,
        "reviewed_diff_sha256": fingerprint,
        "reviewed_at": "2026-07-31T12:00:00Z",
        "authorized_exceptions": [],
    }
    breaker = {
        "task_id": task_id,
        "verdict": "BREAKER=PASS",
        "reviewed_head": head,
        "reviewed_diff_sha256": fingerprint,
        "reviewed_at": "2026-07-31T12:01:00Z",
        "authorized_exceptions": [],
    }
    return reviewer, breaker


def _command_map(
    fingerprint: str = FAKE_FINGERPRINT,
    head: str = "deadbeef",
    task_id: str = TASK_ID,
    *,
    state: str = "review_green",
    acceptance_green: bool = True,
    review_fingerprint: str | None = None,
) -> dict[tuple[str, ...], SimpleNamespace]:
    ledger_json = json.dumps(
        _ledger_snapshot(
            fingerprint,
            task_id=task_id,
            state=state,
            acceptance_green=acceptance_green,
            review_fingerprint=review_fingerprint,
        )
    )
    python = str(runtime_evidence.venv_python())
    return {
        (python, "scripts/ci/householder_state.py", "status", "--task-id", task_id): _result(stdout=ledger_json),
        ("git", "rev-parse", "HEAD"): _result(stdout=f"{head}\n"),
        ("git", "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"): _result(stdout=FAKE_DIFF),
        ("git", "diff", "--cached", "--name-only"): _result(stdout="Givebutter/scripts/ci/runtime_evidence.py\nGivebutter/tests/unit/test_runtime_evidence.py\n"),
        ("git", "status", "--short", "--untracked-files=all"): _result(stdout=" M Givebutter/scripts/ci/runtime_evidence.py\n?? Givebutter/exports_uat/run.csv\n"),
        ("git", "config", "--get", "user.name"): _result(stdout="Test User\n"),
        ("git", "config", "--get", "user.email"): _result(stdout="test@example.com\n"),
        (python, "scripts/ci/check_no_artifacts.py"): _result(),
        (python, "scripts/ci/check_task_untracked.py"): _result(),
        (python, "scripts/ci/check_staged_tree_integrity.py"): _result(),
        (python, "scripts/ci/check_lane_scope.py", "--lane", "workflow-ci", "--verbose"): _result(),
        (python, "-m", "pytest", "-q"): _result(),
    }


def test_resolve_task_id_cli_only():
    assert runtime_evidence._resolve_task_id(TASK_ID, {}) == TASK_ID


def test_resolve_task_id_environment_only():
    assert runtime_evidence._resolve_task_id(None, {"HOUSEHOLDER_TASK_ID": TASK_ID}) == TASK_ID


def test_resolve_task_id_matching_cli_and_environment():
    assert runtime_evidence._resolve_task_id(TASK_ID, {"HOUSEHOLDER_TASK_ID": TASK_ID}) == TASK_ID


def test_resolve_task_id_rejects_missing_identity():
    with pytest.raises(ValueError, match="task_id required"):
        runtime_evidence._resolve_task_id(None, {})


def test_resolve_task_id_rejects_conflicting_identities():
    with pytest.raises(ValueError, match="task_id mismatch"):
        runtime_evidence._resolve_task_id(TASK_ID, {"HOUSEHOLDER_TASK_ID": OLD_TASK_ID})


def test_generate_runtime_evidence_cli_manual_mode_writes_expected_record(monkeypatch, tmp_path):
    fingerprint = FAKE_FINGERPRINT
    head = "deadbeef"
    mapping = _command_map(fingerprint, head=head)
    commands: list[tuple[str, ...]] = []
    output = tmp_path / "runtime-evidence.json"
    readiness = tmp_path / "commit-readiness.json"

    def fake_run(argv, cwd=None, env=None, binary=False):
        key = tuple(argv)
        commands.append(key)
        result = mapping[key]
        if binary:
            return _result(returncode=result.returncode, stdout=FAKE_DIFF, stderr=b"")
        return result

    monkeypatch.setattr(runtime_evidence, "run_command", fake_run)
    monkeypatch.setattr(pre_commit_gate, "run_workflow_ci_lane_guard", lambda: _result(returncode=0))
    monkeypatch.setattr(pre_commit_gate, "list_staged_files", lambda: ["Givebutter/scripts/ci/runtime_evidence.py", "Givebutter/tests/unit/test_runtime_evidence.py"])
    monkeypatch.setattr(pre_commit_gate, "get_current_head", lambda: head)
    monkeypatch.setattr(pre_commit_gate, "staged_diff_sha256", lambda: fingerprint)
    monkeypatch.setattr(runtime_evidence, "default_readiness_path", lambda: readiness)
    monkeypatch.delenv(runtime_evidence.TASK_ID_ENV, raising=False)

    exit_code = runtime_evidence.main(
        [
            "generate",
            "--task-id",
            TASK_ID,
            "--manual-reviewer-criteria",
            "ACCEPT",
            "--manual-breaker-criteria",
            "PASS",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    packet = json.loads(readiness.read_text(encoding="utf-8"))
    assert written["reviewer_receipt"]["provenance"] == "manual reviewer criteria"
    assert written["breaker_receipt"]["provenance"] == "manual breaker criteria"
    assert written["reviewer_receipt"]["criteria"] == "ACCEPT"
    assert written["breaker_receipt"]["criteria"] == "PASS"
    assert packet["qa_verdict"] == "QA=PASS"
    assert commands[:5] == [
        (str(runtime_evidence.venv_python()), "scripts/ci/householder_state.py", "status", "--task-id", TASK_ID),
        ("git", "rev-parse", "HEAD"),
        ("git", "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"),
        (str(runtime_evidence.venv_python()), "scripts/ci/check_no_artifacts.py"),
        (str(runtime_evidence.venv_python()), "scripts/ci/check_task_untracked.py"),
    ]


def test_generate_runtime_evidence_writes_expected_record(monkeypatch, tmp_path):
    fingerprint = FAKE_FINGERPRINT
    head = "deadbeef"
    reviewer, breaker = _receipts(fingerprint, head=head)
    mapping = _command_map(fingerprint, head=head)
    commands: list[tuple[str, ...]] = []

    def fake_run(argv, cwd=None, env=None, binary=False):
        key = tuple(argv)
        commands.append(key)
        result = mapping[key]
        if binary:
            return _result(returncode=result.returncode, stdout=FAKE_DIFF, stderr=b"")
        return result

    monkeypatch.setattr(runtime_evidence, "run_command", fake_run)
    monkeypatch.setattr(pre_commit_gate, "run_workflow_ci_lane_guard", lambda: _result(returncode=0))
    monkeypatch.setattr(pre_commit_gate, "list_staged_files", lambda: ["Givebutter/scripts/ci/runtime_evidence.py", "Givebutter/tests/unit/test_runtime_evidence.py"])
    monkeypatch.setattr(pre_commit_gate, "get_current_head", lambda: head)
    monkeypatch.setattr(pre_commit_gate, "staged_diff_sha256", lambda: fingerprint)

    output = tmp_path / "runtime-evidence.json"
    readiness = tmp_path / "commit-readiness.json"
    evidence = runtime_evidence.generate_runtime_evidence(
        TASK_ID,
        reviewer,
        breaker,
        output_path=output,
        readiness_output_path=readiness,
    )

    assert output.exists()
    assert readiness.exists()
    written = json.loads(output.read_text(encoding="utf-8"))
    packet = json.loads(readiness.read_text(encoding="utf-8"))
    assert written["qa_verdict"] == "not_required"
    assert written["ledger"]["state"] == "review_green"
    assert written["git"]["head"] == head
    assert written["git"]["staged_diff_sha256"] == fingerprint
    assert written["reviewer_receipt"]["verdict"] == "VERDICT=ACCEPT"
    assert written["breaker_receipt"]["verdict"] == "BREAKER=PASS"
    assert packet["qa_verdict"] == "QA=PASS"
    assert packet["reviewed_head"] == head
    assert packet["reviewed_diff_sha256"] == fingerprint
    assert pre_commit_gate.validate_readiness_packet(packet, {"HOUSEHOLDER_TASK_ID": TASK_ID, "HOUSEHOLDER_LANE": "workflow-ci"}) == []
    assert commands[:5] == [
        (str(runtime_evidence.venv_python()), "scripts/ci/householder_state.py", "status", "--task-id", TASK_ID),
        ("git", "rev-parse", "HEAD"),
        ("git", "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"),
        (str(runtime_evidence.venv_python()), "scripts/ci/check_no_artifacts.py"),
        (str(runtime_evidence.venv_python()), "scripts/ci/check_task_untracked.py"),
    ]
    assert len(written["gate_results"]) == 5
    assert evidence["output_path"] == str(output)


@pytest.mark.parametrize(
    ("reviewer_criteria", "breaker_criteria", "message"),
    [
        ("REQUEST_CHANGES", "PASS", "manual reviewer criteria must be ACCEPT"),
        ("ACCEPT", "FAIL", "manual breaker criteria must be PASS"),
    ],
)
def test_generate_runtime_evidence_rejects_manual_criteria(monkeypatch, tmp_path, reviewer_criteria, breaker_criteria, message):
    mapping = _command_map()
    monkeypatch.setattr(runtime_evidence, "run_command", lambda argv, cwd=None, env=None, binary=False: mapping[tuple(argv)] if not binary else _result(stdout=FAKE_DIFF, stderr=b""))

    with pytest.raises(ValueError, match=message):
        runtime_evidence.generate_runtime_evidence(
            TASK_ID,
            manual_reviewer_criteria=reviewer_criteria,
            manual_breaker_criteria=breaker_criteria,
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_manual_and_external_mode_conflict(monkeypatch, tmp_path):
    reviewer, breaker = _receipts()
    mapping = _command_map()
    monkeypatch.setattr(runtime_evidence, "run_command", lambda argv, cwd=None, env=None, binary=False: mapping[tuple(argv)] if not binary else _result(stdout=FAKE_DIFF, stderr=b""))

    with pytest.raises(ValueError, match="manual and external review modes are mutually exclusive"):
        runtime_evidence.generate_runtime_evidence(
            TASK_ID,
            reviewer,
            breaker,
            manual_reviewer_criteria="ACCEPT",
            manual_breaker_criteria="PASS",
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_non_review_green_ledger(monkeypatch, tmp_path):
    reviewer, breaker = _receipts()
    mapping = _command_map(state="editing", acceptance_green=False)

    monkeypatch.setattr(runtime_evidence, "run_command", lambda argv, cwd=None, env=None, binary=False: mapping[tuple(argv)] if not binary else _result(stdout=FAKE_DIFF, stderr=b""))

    with pytest.raises(ValueError, match="review_green"):
        runtime_evidence.generate_runtime_evidence(
            TASK_ID,
            manual_reviewer_criteria="ACCEPT",
            manual_breaker_criteria="PASS",
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_wrong_task_id(monkeypatch, tmp_path):
    mapping = _command_map()

    def fake_run(argv, cwd=None, env=None, binary=False):
        key = tuple(argv)
        if key == (str(runtime_evidence.venv_python()), "scripts/ci/householder_state.py", "status", "--task-id", "HOUSEHOLDER-RUNTIME-EVIDENCE-UNKNOWN-20260731"):
            return _result(stdout=json.dumps(_ledger_snapshot(task_id=TASK_ID)))
        result = mapping[key]
        if binary:
            return _result(returncode=result.returncode, stdout=FAKE_DIFF, stderr=b"")
        return result

    monkeypatch.setattr(runtime_evidence, "run_command", fake_run)

    with pytest.raises(ValueError, match="ledger task_id mismatch"):
        runtime_evidence.generate_runtime_evidence(
            "HOUSEHOLDER-RUNTIME-EVIDENCE-UNKNOWN-20260731",
            manual_reviewer_criteria="ACCEPT",
            manual_breaker_criteria="PASS",
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_wrong_head(monkeypatch, tmp_path):
    mapping = _command_map()
    original_manual_receipt = runtime_evidence._manual_receipt

    def stale_manual_receipt(*, role, task_id, head, fingerprint, criteria):
        receipt = original_manual_receipt(
            role=role,
            task_id=task_id,
            head="cafebabe",
            fingerprint=fingerprint,
            criteria=criteria,
        )
        return receipt

    monkeypatch.setattr(runtime_evidence, "_manual_receipt", stale_manual_receipt)
    monkeypatch.setattr(runtime_evidence, "run_command", lambda argv, cwd=None, env=None, binary=False: mapping[tuple(argv)] if not binary else _result(stdout=FAKE_DIFF, stderr=b""))

    with pytest.raises(ValueError, match="reviewed_head mismatch"):
        runtime_evidence.generate_runtime_evidence(
            TASK_ID,
            manual_reviewer_criteria="ACCEPT",
            manual_breaker_criteria="PASS",
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_wrong_staged_fingerprint(monkeypatch, tmp_path):
    mapping = _command_map()

    def fake_run(argv, cwd=None, env=None, binary=False):
        key = tuple(argv)
        if key == (str(runtime_evidence.venv_python()), "scripts/ci/householder_state.py", "status", "--task-id", TASK_ID):
            return _result(stdout=json.dumps(_ledger_snapshot("stale-fingerprint")))
        if key == ("git", "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"):
            return _result(stdout=b"stale", stderr=b"")
        result = mapping[key]
        if binary:
            return _result(returncode=result.returncode, stdout=FAKE_DIFF, stderr=b"")
        return result

    monkeypatch.setattr(runtime_evidence, "run_command", fake_run)

    with pytest.raises(ValueError, match="staged fingerprint changed during review"):
        runtime_evidence.generate_runtime_evidence(
            TASK_ID,
            manual_reviewer_criteria="ACCEPT",
            manual_breaker_criteria="PASS",
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_wrong_review_fingerprint(monkeypatch, tmp_path):
    reviewer, breaker = _receipts()
    mapping = _command_map(review_fingerprint="wrong-review-fingerprint")
    monkeypatch.setattr(runtime_evidence, "run_command", lambda argv, cwd=None, env=None, binary=False: mapping[tuple(argv)] if not binary else _result(stdout=FAKE_DIFF, stderr=b""))

    with pytest.raises(ValueError, match="staged fingerprint changed during review"):
        runtime_evidence.generate_runtime_evidence(
            TASK_ID,
            manual_reviewer_criteria="ACCEPT",
            manual_breaker_criteria="PASS",
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_stale_fingerprint(monkeypatch, tmp_path):
    reviewer, breaker = _receipts()
    mapping = _command_map()

    def fake_run(argv, cwd=None, env=None, binary=False):
        key = tuple(argv)
        if key == (str(runtime_evidence.venv_python()), "scripts/ci/householder_state.py", "status", "--task-id", TASK_ID):
            return _result(stdout=json.dumps(_ledger_snapshot("stale-fingerprint")))
        result = mapping[key]
        if binary:
            return _result(returncode=result.returncode, stdout=FAKE_DIFF, stderr=b"")
        return result

    monkeypatch.setattr(runtime_evidence, "run_command", fake_run)

    with pytest.raises(ValueError, match="staged fingerprint changed during review"):
        runtime_evidence.generate_runtime_evidence(TASK_ID, reviewer, breaker, output_path=tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_ledger_task_mismatch(monkeypatch, tmp_path):
    fingerprint = FAKE_FINGERPRINT
    reviewer, breaker = _receipts(fingerprint)
    mapping = _command_map(fingerprint, task_id=TASK_ID)

    def fake_run(argv, cwd=None, env=None, binary=False):
        key = tuple(argv)
        if key == (str(runtime_evidence.venv_python()), "scripts/ci/householder_state.py", "status", "--task-id", TASK_ID):
            return _result(stdout=json.dumps(_ledger_snapshot(fingerprint, task_id=OLD_TASK_ID)))
        result = mapping[key]
        if binary:
            return _result(returncode=result.returncode, stdout=FAKE_DIFF, stderr=b"")
        return result

    monkeypatch.setattr(runtime_evidence, "run_command", fake_run)

    with pytest.raises(ValueError, match="ledger task_id mismatch"):
        runtime_evidence.generate_runtime_evidence(TASK_ID, reviewer, breaker, output_path=tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


def test_generate_runtime_evidence_rejects_unauthorized_exceptions(monkeypatch, tmp_path):
    fingerprint = FAKE_FINGERPRINT
    reviewer, breaker = _receipts(fingerprint)
    reviewer["authorized_exceptions"] = [
        {
            "exception_id": "mixed-1",
            "exception_type": "mixed_scope_exception",
            "authorized": False,
            "applies_to_gate_ids": ["workflow_ci_lane_guard"],
        }
    ]
    mapping = _command_map(fingerprint)
    monkeypatch.setattr(runtime_evidence, "run_command", lambda argv, cwd=None, env=None, binary=False: mapping[tuple(argv)] if not binary else _result(stdout=FAKE_DIFF, stderr=b""))

    with pytest.raises(ValueError, match="authorized must be true"):
        runtime_evidence.generate_runtime_evidence(TASK_ID, reviewer, breaker, output_path=tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


def test_atomic_write_cleans_up_partial_output(monkeypatch, tmp_path):
    fingerprint = FAKE_FINGERPRINT
    reviewer, breaker = _receipts(fingerprint)
    mapping = _command_map(fingerprint)
    monkeypatch.setattr(runtime_evidence, "run_command", lambda argv, cwd=None, env=None, binary=False: mapping[tuple(argv)] if not binary else _result(stdout=FAKE_DIFF, stderr=b""))
    replace_calls: list[tuple[str, str]] = []
    real_replace = runtime_evidence.os.replace

    def flaky_replace(src, dst):
        replace_calls.append((str(src), str(dst)))
        if len(replace_calls) == 2:
            raise OSError("replace failed")
        return real_replace(src, dst)

    monkeypatch.setattr(runtime_evidence.os, "replace", flaky_replace)

    output = tmp_path / "runtime-evidence.json"
    readiness = tmp_path / "commit-readiness.json"
    with pytest.raises(OSError, match="replace failed"):
        runtime_evidence.generate_runtime_evidence(
            TASK_ID,
            reviewer,
            breaker,
            output_path=output,
            readiness_output_path=readiness,
        )

    assert not output.exists()
    assert not readiness.exists()
    assert not any(tmp_path.iterdir())
