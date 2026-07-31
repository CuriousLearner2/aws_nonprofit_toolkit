#!/usr/bin/env python3
"""Generate canonical runtime evidence from the committed ledger and repository gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

TASK_ID = "HOUSEHOLDER-60-MINUTE-AUTONOMY-TRIAL-20260731"
SCHEMA_VERSION = 1
QA_VERDICT = "not_required"
READINESS_QA_VERDICT = "QA=PASS"
ALLOWED_REVIEWER_VERDICTS = {"VERDICT=ACCEPT", "VERDICT=REQUEST_CHANGES", "VERDICT=REJECT"}
ALLOWED_BREAKER_VERDICTS = {"BREAKER=PASS", "BREAKER=FAIL"}
ALLOWED_EXCEPTION_TYPES = {"mixed_scope_exception"}
EVIDENCE_SUFFIX = ".runtime-evidence.json"
READINESS_SUFFIX = "commit-readiness.json"
READINESS_GATE_SPECS = (
    {"label": "check_no_artifacts", "gate_id": "check_no_artifacts", "group": "canonical", "command": "./.venv/bin/python scripts/ci/check_no_artifacts.py"},
    {"label": "check_task_untracked", "gate_id": "check_task_untracked", "group": "canonical", "command": "./.venv/bin/python scripts/ci/check_task_untracked.py"},
    {"label": "check_staged_tree_integrity", "gate_id": "check_staged_tree_integrity", "group": "canonical", "command": "./.venv/bin/python scripts/ci/check_staged_tree_integrity.py"},
    {"label": "workflow_ci_lane_guard", "gate_id": "workflow_ci_lane_guard", "group": "scope", "command": "./.venv/bin/python scripts/ci/check_lane_scope.py --lane workflow-ci --verbose"},
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def givebutter_dir() -> Path:
    return repo_root() / "Givebutter"


def venv_python() -> Path:
    return givebutter_dir() / ".venv/bin/python"


def build_env() -> dict[str, str]:
    env = os.environ.copy()
    venv_bin = str(givebutter_dir() / ".venv/bin")
    env["PATH"] = f"{venv_bin}:{env['PATH']}" if env.get("PATH") else venv_bin
    return env


def default_output_path(task_id: str = TASK_ID) -> Path:
    safe_task_id = task_id.strip()
    if not safe_task_id or safe_task_id != task_id or "/" in safe_task_id or "\\" in safe_task_id:
        raise ValueError("task_id mismatch")
    return Path(tempfile.gettempdir()) / "householder-runtime-evidence" / f"{safe_task_id}{EVIDENCE_SUFFIX}"


def default_readiness_path(task_id: str = TASK_ID) -> Path:
    safe_task_id = task_id.strip()
    if not safe_task_id or safe_task_id != task_id or "/" in safe_task_id or "\\" in safe_task_id:
        raise ValueError("task_id mismatch")
    return givebutter_dir() / ".artifacts" / READINESS_SUFFIX


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    binary: bool = False,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        list(argv),
        cwd=cwd or repo_root(),
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=not binary,
        check=False,
    )


def _command_text(argv: Sequence[str]) -> str:
    return shlex.join(str(part) for part in argv)


def _record_command(
    label: str,
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    binary: bool = False,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[Any]]:
    started_at = utc_now()
    result = run_command(argv, cwd=cwd, env=env, binary=binary)
    finished_at = utc_now()
    record: dict[str, Any] = {
        "label": label,
        "command": _command_text(argv),
        "argv": [str(part) for part in argv],
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": result.returncode,
        "status": "passed" if result.returncode == 0 else "failed",
    }
    if binary:
        stdout = result.stdout if isinstance(result.stdout, bytes) else b""
        stderr = result.stderr if isinstance(result.stderr, bytes) else b""
        record["stdout_sha256"] = hashlib.sha256(stdout).hexdigest()
        record["stdout_bytes"] = len(stdout)
        record["stderr_sha256"] = hashlib.sha256(stderr).hexdigest()
        record["stderr_bytes"] = len(stderr)
    else:
        record["stdout"] = result.stdout
        record["stderr"] = result.stderr
    return record, result


def _git_text(*args: str) -> str:
    result = run_command(["git", *args], cwd=repo_root())
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed")
    return result.stdout


def current_head() -> str:
    head = _git_text("rev-parse", "HEAD").strip()
    if not head:
        raise ValueError("unable to resolve HEAD")
    return head


def current_staged_fingerprint() -> str:
    result = run_command(
        ["git", "diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "HEAD"],
        cwd=repo_root(),
        binary=True,
    )
    if result.returncode != 0:
        raise ValueError("unable to read staged fingerprint")
    stdout = result.stdout if isinstance(result.stdout, bytes) else b""
    return hashlib.sha256(stdout).hexdigest()


def staged_files() -> tuple[str, ...]:
    output = _git_text("diff", "--cached", "--name-only")
    return tuple(line for line in (line.strip() for line in output.splitlines()) if line)


def git_status_short() -> tuple[str, ...]:
    output = _git_text("status", "--short", "--untracked-files=all")
    return tuple(line for line in (line.rstrip() for line in output.splitlines()) if line)


def _ledger_status(task_id: str) -> dict[str, Any]:
    result = run_command(
        [str(venv_python()), "scripts/ci/householder_state.py", "status", "--task-id", task_id],
        cwd=givebutter_dir(),
        env=build_env(),
    )
    if result.returncode != 0:
        raise ValueError("unable to read ledger status")
    try:
        snapshot = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("ledger status is malformed JSON") from exc
    if not isinstance(snapshot, dict):
        raise ValueError("ledger status must be a JSON object")
    return snapshot


def _validate_ledger_snapshot(snapshot: Mapping[str, Any], task_id: str, fingerprint: str) -> dict[str, Any]:
    if snapshot.get("task_id") != task_id:
        raise ValueError("ledger task_id mismatch")
    if snapshot.get("schema_version") != 1:
        raise ValueError("unsupported ledger schema")
    if snapshot.get("state") != "review_green" or snapshot.get("acceptance_green") is not True:
        raise ValueError("ledger must be review_green before runtime evidence is written")
    if snapshot.get("review_active") is True:
        raise ValueError("ledger review is still active")
    if snapshot.get("review_fingerprint") != fingerprint:
        raise ValueError("staged fingerprint changed during review")
    if snapshot.get("terminal_reason") is not None:
        raise ValueError("ledger refusal is terminal for runtime evidence")

    counters = snapshot.get("counters")
    remaining = snapshot.get("remaining")
    if not isinstance(counters, Mapping) or not isinstance(remaining, Mapping):
        raise ValueError("ledger counters are malformed")
    for name, value in counters.items():
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"ledger counter {name} must be a non-negative integer")
    for name, value in remaining.items():
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"ledger remaining budget {name} must be a non-negative integer")
    return dict(snapshot)


def _load_payload(value: Mapping[str, Any] | str | Path, *, label: str) -> dict[str, Any]:
    if isinstance(value, Path):
        payload = json.loads(value.read_text(encoding="utf-8"))
    elif isinstance(value, str):
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    else:
        payload = dict(value)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _validate_iso8601(value: Any, *, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a valid ISO-8601 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO-8601 timestamp") from exc


def _validate_exception(exception: Mapping[str, Any], gate_ids: set[str], fingerprint: str, label: str) -> dict[str, Any]:
    required = {"exception_id", "exception_type", "authorized", "applies_to_gate_ids"}
    missing = required - set(exception)
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(sorted(missing))}")
    if not isinstance(exception["exception_id"], str) or not exception["exception_id"].strip():
        raise ValueError(f"{label}.exception_id must be a non-empty string")
    if exception["exception_type"] not in ALLOWED_EXCEPTION_TYPES:
        raise ValueError(f"{label}.exception_type must be mixed_scope_exception")
    if exception["authorized"] is not True:
        raise ValueError(f"{label}.authorized must be true")
    if not isinstance(exception["applies_to_gate_ids"], list) or not exception["applies_to_gate_ids"]:
        raise ValueError(f"{label}.applies_to_gate_ids must be a non-empty list")
    unknown = [gate_id for gate_id in exception["applies_to_gate_ids"] if gate_id not in gate_ids]
    if unknown:
        raise ValueError(f"{label}.applies_to_gate_ids contains unknown gate_ids: {', '.join(sorted(unknown))}")
    if exception.get("reviewed_diff_sha256") not in (None, fingerprint):
        raise ValueError(f"{label}.reviewed_diff_sha256 must match the frozen fingerprint")
    normalized = dict(exception)
    normalized["reviewed_diff_sha256"] = fingerprint
    return normalized


def _validate_receipt(
    receipt: Mapping[str, Any] | str | Path,
    *,
    role: str,
    task_id: str,
    head: str,
    fingerprint: str,
) -> dict[str, Any]:
    payload = _load_payload(receipt, label=f"{role} receipt")
    if payload.get("task_id") != task_id:
        raise ValueError(f"{role} receipt task_id mismatch")
    if payload.get("reviewed_head") != head:
        raise ValueError(f"{role} receipt reviewed_head mismatch")
    if payload.get("reviewed_diff_sha256") != fingerprint:
        raise ValueError(f"{role} receipt reviewed_diff_sha256 mismatch")
    _validate_iso8601(payload.get("reviewed_at"), label=f"{role} receipt reviewed_at")

    verdict = payload.get("verdict")
    if role == "Reviewer":
        if verdict not in ALLOWED_REVIEWER_VERDICTS:
            raise ValueError("Reviewer receipt verdict must be VERDICT=ACCEPT, VERDICT=REQUEST_CHANGES, or VERDICT=REJECT")
    elif verdict not in ALLOWED_BREAKER_VERDICTS:
        raise ValueError("Breaker receipt verdict must be BREAKER=PASS or BREAKER=FAIL")

    raw_exceptions = payload.get("authorized_exceptions", [])
    if raw_exceptions in (None, ""):
        raw_exceptions = []
    if not isinstance(raw_exceptions, list):
        raise ValueError(f"{role} receipt authorized_exceptions must be a list when present")

    normalized = {
        "role": role,
        "task_id": task_id,
        "verdict": verdict,
        "reviewed_head": head,
        "reviewed_diff_sha256": fingerprint,
        "reviewed_at": payload["reviewed_at"],
        "authorized_exceptions": raw_exceptions,
    }
    return normalized


def _required_gate_commands() -> list[tuple[str, list[str], bool]]:
    python = str(venv_python())
    return [
        ("check_no_artifacts", [python, "scripts/ci/check_no_artifacts.py"], True),
        ("check_task_untracked", [python, "scripts/ci/check_task_untracked.py"], True),
        ("check_staged_tree_integrity", [python, "scripts/ci/check_staged_tree_integrity.py"], True),
        ("workflow_ci_lane_guard", [python, "scripts/ci/check_lane_scope.py", "--lane", "workflow-ci", "--verbose"], True),
        ("full_unit_integration_gate", [python, "-m", "pytest", "-q"], True),
    ]


def _readiness_gate_records(gate_records: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    by_label = {record["label"]: dict(record) for record in gate_records}
    readiness_records: list[dict[str, Any]] = []
    for spec in READINESS_GATE_SPECS:
        record = by_label[spec["label"]]
        normalized = {
            "gate_id": spec["gate_id"],
            "group": spec["group"],
            "command": spec["command"],
            "required": True,
            "status": record["status"],
            "exit_code": record["exit_code"],
        }
        readiness_records.append(normalized)
    return readiness_records, by_label


def _build_commit_readiness_packet(
    evidence: Mapping[str, Any],
    *,
    reviewer: Mapping[str, Any],
    breaker: Mapping[str, Any],
    readiness_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    gate_results = [dict(record) for record in readiness_records]
    authorized_exceptions = [dict(exception) for exception in evidence.get("authorized_exceptions", [])]
    canonical_passed = all(record["status"] == "passed" for record in gate_results if record["group"] == "canonical")
    scope_passed = all(record["status"] == "passed" for record in gate_results if record["group"] == "scope")
    authorized_failed_gate_ids = {
        gate_id
        for exception in authorized_exceptions
        for gate_id in exception["applies_to_gate_ids"]
    }
    reviewed_at = max(reviewer["reviewed_at"], breaker["reviewed_at"])
    packet = {
        "schema_version": 2,
        "task_id": evidence["task_id"],
        "reviewer_verdict": reviewer["verdict"],
        "breaker_verdict": breaker["verdict"],
        "qa_verdict": READINESS_QA_VERDICT,
        "canonical_gates_passed": canonical_passed,
        "scope_guard_passed": scope_passed,
        "commit_authorized": canonical_passed and (scope_passed or bool(authorized_failed_gate_ids)),
        "push_authorized": False,
        "reviewed_head": evidence["git"]["head"],
        "reviewed_diff_sha256": evidence["git"]["staged_diff_sha256"],
        "reviewed_at": reviewed_at,
        "informational_notes": ["derived from runtime evidence"],
        "required_changes": [],
        "gate_results": gate_results,
        "authorized_exceptions": authorized_exceptions,
    }
    return packet


def _run_required_gates() -> list[dict[str, Any]]:
    env = build_env()
    records: list[dict[str, Any]] = []
    for label, argv, required in _required_gate_commands():
        record, result = _record_command(label, argv, cwd=givebutter_dir(), env=env)
        record["required"] = required
        records.append(record)
        if result.returncode != 0:
            raise ValueError(f"{label} failed with exit code {result.returncode}")
    return records


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            tmp_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        raise
    return path


def generate_runtime_evidence(
    task_id: str,
    reviewer_receipt: Mapping[str, Any] | str | Path,
    breaker_receipt: Mapping[str, Any] | str | Path,
    *,
    output_path: Path | None = None,
    readiness_output_path: Path | None = None,
) -> dict[str, Any]:
    if task_id != TASK_ID:
        raise ValueError("task_id mismatch")

    ledger = _ledger_status(task_id)
    head = current_head()
    fingerprint = current_staged_fingerprint()
    ledger = _validate_ledger_snapshot(ledger, task_id, fingerprint)
    reviewer = _validate_receipt(reviewer_receipt, role="Reviewer", task_id=task_id, head=head, fingerprint=fingerprint)
    breaker = _validate_receipt(breaker_receipt, role="Breaker", task_id=task_id, head=head, fingerprint=fingerprint)

    gate_records = _run_required_gates()
    gate_ids = {record["label"] for record in gate_records}
    authorized_exceptions: list[dict[str, Any]] = []
    for receipt, label in ((reviewer, "Reviewer"), (breaker, "Breaker")):
        for index, exception in enumerate(receipt["authorized_exceptions"]):
            normalized = _validate_exception(exception, gate_ids, fingerprint, f"{label} receipt authorized_exceptions[{index}]")
            authorized_exceptions.append(normalized)

    readiness_records, _ = _readiness_gate_records(gate_records)
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "generated_at": utc_now(),
        "qa_verdict": QA_VERDICT,
        "authorization_identity": {
            "task_id": task_id,
            "git_user_name": _git_text("config", "--get", "user.name").strip() or None,
            "git_user_email": _git_text("config", "--get", "user.email").strip() or None,
        },
        "git": {
            "head": head,
            "staged_diff_sha256": fingerprint,
            "staged_files": list(staged_files()),
            "status_short": list(git_status_short()),
        },
        "ledger": ledger,
        "reviewer_receipt": reviewer,
        "breaker_receipt": breaker,
        "authorized_exceptions": authorized_exceptions,
        "gate_results": gate_records,
    }
    path = output_path or default_output_path(task_id)
    readiness_path = readiness_output_path or default_readiness_path(task_id)
    readiness_packet = _build_commit_readiness_packet(
        evidence,
        reviewer=reviewer,
        breaker=breaker,
        readiness_records=readiness_records,
    )
    try:
        _write_atomic_json(path, evidence)
        _write_atomic_json(readiness_path, readiness_packet)
    except Exception:
        if path.exists():
            path.unlink()
        if readiness_path.exists():
            readiness_path.unlink()
        raise
    evidence["output_path"] = str(path)
    evidence["readiness_output_path"] = str(readiness_path)
    return evidence


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="runtime_evidence.py")
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate")
    generate.add_argument("--task-id", required=True)
    generate.add_argument("--reviewer-receipt", required=True)
    generate.add_argument("--breaker-receipt", required=True)
    generate.add_argument("--output", default=None)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command != "generate":  # pragma: no cover
            raise ValueError("unknown command")
        evidence = generate_runtime_evidence(
            args.task_id,
            args.reviewer_receipt,
            args.breaker_receipt,
            output_path=Path(args.output) if args.output else None,
        )
        print(
            json.dumps(
                {
                    "output_path": evidence["output_path"],
                    "readiness_output_path": evidence["readiness_output_path"],
                    "qa_verdict": evidence["qa_verdict"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
