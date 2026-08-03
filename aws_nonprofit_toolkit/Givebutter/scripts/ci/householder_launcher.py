#!/usr/bin/env python3
"""Fixed-argv, preflight-first Householder campaign launcher."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MIRROR_PATH = Path(os.environ.get("HOUSEHOLDER_MIRROR_PATH", "/Users/gautambiswas/householder-integration-mirror.git"))
LAUNCH_ROOT = Path(os.environ.get("HOUSEHOLDER_LAUNCH_ROOT", "/private/tmp/householder-launches"))
LOCK_ROOT = Path(os.environ.get("HOUSEHOLDER_SCOPE_LOCK_ROOT", "/private/tmp/householder-scope-locks"))
STATE_ROOT = Path(os.environ.get("HOUSEHOLDER_LAUNCH_STATE_ROOT", "/private/tmp/householder-launch-state"))
PYTHON311 = os.environ.get("HOUSEHOLDER_PYTHON311", "python3.11")
REMOTE_URL = os.environ.get("HOUSEHOLDER_GITHUB_REMOTE", "")
MARKERS = ("scripts/ci/householder_campaign.py", "scripts/ci/architecture_slice_gate.py", "scripts/householder/autosave_service.py", "tests/integration/test_autosave_validation.py")
ERRORS = {"BASELINE_UNAVAILABLE", "BASELINE_MISMATCH", "MIRROR_UNAVAILABLE", "CHECKOUT_COLLISION", "PROJECT_ROOT_UNAVAILABLE", "PROJECT_ROOT_AMBIGUOUS", "ENVIRONMENT_MISMATCH", "SUITE_PREFLIGHT_FAILED", "SCOPE_OVERLAP", "SCOPE_LOCK_STALE_UNSAFE", "CONTRACT_INVALID", "WRAPPER_INITIALIZATION_FAILED", "LAUNCH_STATE_CONFLICT", "PARTIAL_CLEANUP_FAILED"}


class LaunchError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        if code not in ERRORS: raise ValueError(code)
        super().__init__(message); self.code = code; self.details = details or {}


def _sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def _digest(value: Any) -> str: return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with temporary.open("rb") as handle: os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally: temporary.unlink(missing_ok=True)


def _git(cwd: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False, timeout=timeout)


def _git_out(cwd: Path, *args: str) -> str:
    result = _git(cwd, *args)
    if result.returncode: raise RuntimeError(result.stderr.strip() or "git failed")
    return result.stdout.strip()


def _normalise_input(value: dict[str, Any]) -> dict[str, Any]:
    required = {"baseline", "campaign_id", "mode", "authorized_production_paths", "authorized_test_paths", "suite_ids", "time_limit_seconds"}
    if not isinstance(value, dict) or set(value) - required - {"typed_contract"} or required - set(value): raise LaunchError("CONTRACT_INVALID", "input fields are missing or unknown")
    baseline = value["baseline"]
    if not isinstance(baseline, str) or len(baseline) != 40 or baseline.lower() != baseline or any(c not in "0123456789abcdef" for c in baseline): raise LaunchError("BASELINE_MISMATCH", "baseline must be an exact lowercase commit SHA")
    campaign_id = value["campaign_id"]
    if not isinstance(campaign_id, str) or not campaign_id or campaign_id.strip() != campaign_id or "/" in campaign_id or "\\" in campaign_id: raise LaunchError("CONTRACT_INVALID", "campaign_id is invalid")
    if value["mode"] not in {"discovery", "campaign"}: raise LaunchError("CONTRACT_INVALID", "mode must be discovery or campaign")
    if not isinstance(value["time_limit_seconds"], int) or value["time_limit_seconds"] <= 0: raise LaunchError("CONTRACT_INVALID", "time limit must be positive")
    result = dict(value)
    for field in ("authorized_production_paths", "authorized_test_paths"):
        paths = value[field]
        if not isinstance(paths, list) or any(not isinstance(p, str) or not p or p.strip() != p for p in paths): raise LaunchError("CONTRACT_INVALID", f"{field} is malformed")
        normalized = []
        for path in paths:
            if "\\" in path or path.startswith("/") or ".." in Path(path).parts or Path(path).as_posix() != path: raise LaunchError("CONTRACT_INVALID", f"{field} contains an escaped path")
            normalized.append(path)
        if len(normalized) != len(set(normalized)): raise LaunchError("CONTRACT_INVALID", f"{field} contains duplicate paths")
        result[field] = normalized
    suites = value["suite_ids"]
    if not isinstance(suites, list) or not suites or any(not isinstance(s, str) or not s.strip() for s in suites) or len(suites) != len(set(suites)): raise LaunchError("CONTRACT_INVALID", "suite_ids is malformed")
    return result


def load_input(path: Path) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise LaunchError("CONTRACT_INVALID", "input JSON is unreadable") from exc
    return _normalise_input(value)


def _resolve_baseline(baseline: str) -> dict[str, Any]:
    if not MIRROR_PATH.is_dir(): raise LaunchError("MIRROR_UNAVAILABLE", "configured bare mirror is unavailable")
    if _git(MIRROR_PATH, "cat-file", "-e", f"{baseline}^{{commit}}").returncode:
        if not REMOTE_URL: raise LaunchError("BASELINE_UNAVAILABLE", "exact baseline is absent from mirror")
        if _git(MIRROR_PATH, "fetch", REMOTE_URL, baseline, timeout=120).returncode: raise LaunchError("BASELINE_UNAVAILABLE", "remote fallback could not resolve exact baseline")
    try: resolved = _git_out(MIRROR_PATH, "rev-parse", f"{baseline}^{{commit}}")
    except RuntimeError as exc: raise LaunchError("BASELINE_UNAVAILABLE", "baseline cannot be resolved") from exc
    if resolved != baseline: raise LaunchError("BASELINE_MISMATCH", "mirror resolved another commit")
    return {"sha": baseline, "mirror": str(MIRROR_PATH), "verified_refs": _git_out(MIRROR_PATH, "for-each-ref", "--format=%(refname):%(objectname)", "refs/heads").splitlines()}


def discover_project_root(git_root: Path) -> Path:
    candidates = [git_root, git_root / "aws_nonprofit_toolkit" / "Givebutter"]
    valid = []
    for candidate in candidates:
        if not candidate.exists(): continue
        if candidate.is_symlink() or candidate.resolve() != candidate: raise LaunchError("PROJECT_ROOT_UNAVAILABLE", "project root is symlinked")
        if all((candidate / marker).is_file() for marker in MARKERS): valid.append(candidate)
    if not valid: raise LaunchError("PROJECT_ROOT_UNAVAILABLE", "project root is unavailable")
    if len(valid) != 1: raise LaunchError("PROJECT_ROOT_AMBIGUOUS", "multiple project roots found")
    return valid[0]


def _environment(project: Path) -> dict[str, Any]:
    executable = Path(PYTHON311) if Path(PYTHON311).is_absolute() else Path(shutil.which(PYTHON311) or "")
    if not executable.is_file(): raise LaunchError("ENVIRONMENT_MISMATCH", "approved Python 3.11 executable is unavailable")
    probe = subprocess.run([str(executable), "-c", "import platform,sys; print(sys.executable); print(*sys.version_info[:3]); print(platform.platform()); print(platform.machine())"], text=True, capture_output=True, check=False)
    lines = probe.stdout.splitlines()
    if probe.returncode or len(lines) != 4 or lines[1].split()[:2] != ["3", "11"]: raise LaunchError("ENVIRONMENT_MISMATCH", "approved executable is not Python 3.11")
    requirements = [project / "requirements.txt", project / "requirements-test.txt"]
    if any(not p.is_file() for p in requirements): raise LaunchError("ENVIRONMENT_MISMATCH", "declared requirements are missing")
    freeze = subprocess.run([str(executable), "-m", "pip", "freeze"], text=True, capture_output=True, check=False)
    if freeze.returncode: raise LaunchError("ENVIRONMENT_MISMATCH", "pip freeze failed")
    return {"python_executable": lines[0], "python_version": lines[1], "requirements_sha256": {p.name: _sha(p.read_bytes()) for p in requirements}, "freeze_sha256": _sha(freeze.stdout.encode()), "platform": lines[2], "architecture": lines[3]}


def _wrapper(project: Path):
    path = project / "scripts/ci/householder_campaign.py"
    spec = importlib.util.spec_from_file_location("householder_fixed_wrapper", path)
    if spec is None or spec.loader is None: raise LaunchError("WRAPPER_INITIALIZATION_FAILED", "wrapper cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    try: spec.loader.exec_module(module)
    except Exception as exc: raise LaunchError("WRAPPER_INITIALIZATION_FAILED", "wrapper failed to load") from exc
    return module


def _preflight(project: Path, suite_ids: list[str], executable: str, deadline: float) -> list[dict[str, Any]]:
    registry = getattr(_wrapper(project), "SUITE_REGISTRY", {})
    results = []
    for suite_id in suite_ids:
        argv = registry.get(suite_id)
        if not isinstance(argv, list) or len(argv) < 2 or any(not isinstance(a, str) for a in argv): raise LaunchError("SUITE_PREFLIGHT_FAILED", f"suite is not in fixed registry: {suite_id}")
        command = [executable, *argv[1:]]
        try: run = subprocess.run(command, cwd=project, text=True, capture_output=True, check=False, timeout=max(1, int(deadline - time.time())))
        except (OSError, subprocess.TimeoutExpired) as exc: raise LaunchError("SUITE_PREFLIGHT_FAILED", f"suite did not complete: {suite_id}") from exc
        entry = {"suite_id": suite_id, "argv": command, "cwd": str(project), "exit_code": run.returncode, "passed": run.returncode == 0}; results.append(entry)
        if run.returncode: raise LaunchError("SUITE_PREFLIGHT_FAILED", f"suite failed: {suite_id}", {"suite_results": results})
    return results


def _process_identity(pid: int) -> str | None:
    try: result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="], text=True, capture_output=True, check=False)
    except OSError: return None
    return result.stdout.strip() or None


def _alive(pid: int) -> bool | None:
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False
    except PermissionError: return None


@contextmanager
def scope_lock(campaign_id: str, mode: str, checkout: Path, paths: list[str], operation_id: str):
    if mode == "discovery": yield []; return
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    guard = LOCK_ROOT / ".scope.lock"
    with guard.open("a+") as handle:
        import fcntl; fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        acquired: list[Path] = []
        try:
            requested = set(paths)
            for path in sorted(LOCK_ROOT.glob("*.json")):
                try: record = json.loads(path.read_text(encoding="utf-8")); pid = int(record["pid"])
                except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc: raise LaunchError("SCOPE_LOCK_STALE_UNSAFE", "scope lock is unreadable") from exc
                alive = _alive(pid)
                if alive is None: raise LaunchError("SCOPE_LOCK_STALE_UNSAFE", "scope lock process is ambiguous")
                if alive is False: path.unlink(missing_ok=True); continue
                if _process_identity(pid) != record.get("process_start_identity"): raise LaunchError("SCOPE_LOCK_STALE_UNSAFE", "live lock identity mismatch")
                if requested.intersection(record.get("authorized_paths", [])): raise LaunchError("SCOPE_OVERLAP", "authorized scope overlaps active writer")
            target = LOCK_ROOT / f"{campaign_id}-{uuid.uuid4().hex}.json"
            record = {"campaign_id": campaign_id, "mode": mode, "checkout": str(checkout), "authorized_paths": sorted(requested), "pid": os.getpid(), "process_start_identity": _process_identity(os.getpid()), "acquisition_timestamp": _now(), "launcher_operation_id": operation_id}
            if not record["process_start_identity"]: raise LaunchError("SCOPE_LOCK_STALE_UNSAFE", "current process identity is unavailable")
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as output: json.dump(record, output, sort_keys=True); output.write("\n"); output.flush(); os.fsync(output.fileno())
            acquired.append(target); yield [str(target)]
        except Exception:
            for path in acquired: path.unlink(missing_ok=True)
            raise
        finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _contract(project: Path, payload: dict[str, Any], operation_id: str, wrapper: Any) -> Path:
    paths = payload["authorized_production_paths"] + payload["authorized_test_paths"]
    gate = _git_out(project, "hash-object", str(project / "scripts/ci/architecture_slice_gate.py"))
    typed = {"baseline_head": payload["baseline"], "gate_sha": gate, "allowed_files": paths, "max_production_lines": 1_000_000, "max_test_lines": 1_000_000, "suite_ids": payload["suite_ids"], "invariants": ["launcher preserves wrapper containment and public behavior"], "completed_seams": [], "completed_seam_files": {}, "protected_files": ["scripts/ci/householder_campaign.py", "scripts/ci/architecture_slice_gate.py"]}
    if payload.get("typed_contract"):
        try: supplied = json.loads(Path(payload["typed_contract"]).read_text(encoding="utf-8")); supplied = supplied.get("typed_contract", supplied)
        except (OSError, json.JSONDecodeError) as exc: raise LaunchError("CONTRACT_INVALID", "typed contract is unreadable") from exc
        if not isinstance(supplied, dict) or supplied.get("baseline_head") != payload["baseline"] or supplied.get("suite_ids") != payload["suite_ids"] or supplied.get("allowed_files") != paths: raise LaunchError("CONTRACT_INVALID", "typed contract does not match inputs")
        typed = supplied
    path = STATE_ROOT / f"{payload['campaign_id']}.{operation_id}.contract.json"
    _atomic(path, {"task_id": payload["campaign_id"], "seam": "launcher-managed-campaign", "typed_contract": typed})
    return path


def _clone(path: Path, baseline: str) -> None:
    if path.exists(): raise LaunchError("CHECKOUT_COLLISION", "checkout path already exists")
    result = subprocess.run(["git", "clone", "--no-local", "--no-checkout", str(MIRROR_PATH), str(path)], text=True, capture_output=True, check=False)
    if result.returncode: raise LaunchError("BASELINE_UNAVAILABLE", "mirror clone failed")
    if _git(path, "checkout", "--detach", baseline).returncode or _git_out(path, "rev-parse", "HEAD") != baseline: raise LaunchError("BASELINE_MISMATCH", "checkout is not pinned exactly")


def launch(payload: dict[str, Any] | Path, *, operation_id: str | None = None) -> dict[str, Any]:
    payload = load_input(payload) if isinstance(payload, Path) else _normalise_input(payload)
    operation_id = operation_id or uuid.uuid4().hex
    state_path = STATE_ROOT / f"{payload['campaign_id']}.json"
    digest = _digest(payload); previous = None
    if state_path.exists():
        try: previous = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise LaunchError("LAUNCH_STATE_CONFLICT", "launcher state is unreadable") from exc
        if previous.get("input_sha256") != digest: raise LaunchError("LAUNCH_STATE_CONFLICT", "campaign ID has different inputs")
        if previous.get("status") == "ready":
            checkout = Path(previous["output"]["checkout"])
            try: valid_checkout = checkout.is_dir() and _git_out(checkout, "rev-parse", "HEAD") == payload["baseline"]
            except RuntimeError: valid_checkout = False
            if not valid_checkout: raise LaunchError("LAUNCH_STATE_CONFLICT", "completed checkout changed")
            return previous["output"]
        if previous.get("status") != "preflight": raise LaunchError("LAUNCH_STATE_CONFLICT", "unsupported launch phase")
    resolution = _resolve_baseline(payload["baseline"]); LAUNCH_ROOT.mkdir(parents=True, exist_ok=True)
    checkout = Path(previous["checkout"]) if previous else LAUNCH_ROOT / f"{payload['campaign_id']}-{uuid.uuid4().hex[:12]}"
    needs_clone = False
    if checkout.exists():
        if not checkout.is_dir(): raise LaunchError("CHECKOUT_COLLISION", "checkout path is not a directory")
        try:
            if _git_out(checkout, "rev-parse", "HEAD") != payload["baseline"]: raise LaunchError("LAUNCH_STATE_CONFLICT", "interrupted checkout changed")
        except RuntimeError as exc: raise LaunchError("LAUNCH_STATE_CONFLICT", "interrupted checkout is invalid") from exc
    else:
        _atomic(state_path, {"input_sha256": digest, "operation_id": operation_id, "status": "preflight", "checkout": str(checkout)})
        needs_clone = True
    try:
        if needs_clone: _clone(checkout, payload["baseline"])
        project = discover_project_root(checkout); identity = {"git_root": str(Path(_git_out(project, "rev-parse", "--show-toplevel"))), "project_root": str(project), "worktree": str(project), "git_common_dir": _git_out(project, "rev-parse", "--git-common-dir"), "git_dir": _git_out(project, "rev-parse", "--git-dir")}
        environment = _environment(project); suites = _preflight(project, payload["suite_ids"], environment["python_executable"], time.time() + payload["time_limit_seconds"])
        with scope_lock(payload["campaign_id"], payload["mode"], project, payload["authorized_production_paths"] + payload["authorized_test_paths"], operation_id) as locks:
            wrapper = _wrapper(project)
            if payload["mode"] == "discovery": wrapper_state = wrapper.campaign_discovery_start(payload["campaign_id"], operation_id)
            else:
                contract = _contract(project, payload, operation_id, wrapper); gate = _git_out(project, "hash-object", str(project / "scripts/ci/architecture_slice_gate.py")); contract_sha = wrapper._json_sha256(json.loads(contract.read_text(encoding="utf-8")))
                wrapper.campaign_ledger_init(payload["campaign_id"], operation_id, project, gate, [{"path": str(contract), "sha256": contract_sha}], payload["suite_ids"]); wrapper.campaign_ledger_next(payload["campaign_id"]); wrapper_state = wrapper.campaign_ledger_start_edit(payload["campaign_id"], 0, operation_id + "-start-edit")
            output = {"status": "ready", "error_code": None, "baseline": resolution, "checkout": str(checkout), "git_root": identity["git_root"], "project_root": identity["project_root"], "environment_fingerprint": environment, "suite_results": suites, "acquired_locks": locks, "ledger_path": str(wrapper._ledger_file(payload["campaign_id"])), "wrapper_state": wrapper_state}
            _atomic(state_path, {"input_sha256": digest, "operation_id": operation_id, "status": "ready", "output": output}); return output
    except LaunchError:
        try: shutil.rmtree(checkout); state_path.unlink(missing_ok=True)
        except OSError as exc: raise LaunchError("PARTIAL_CLEANUP_FAILED", "partial cleanup failed") from exc
        raise
    except Exception as exc:
        try: shutil.rmtree(checkout); state_path.unlink(missing_ok=True)
        except OSError as cleanup: raise LaunchError("PARTIAL_CLEANUP_FAILED", "partial cleanup failed") from cleanup
        raise LaunchError("WRAPPER_INITIALIZATION_FAILED", "launcher failed") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Householder campaign launcher"); parser.add_argument("launch", choices=["launch"]); parser.add_argument("--input", required=True, type=Path); args = parser.parse_args(argv)
    try: output = launch(args.input)
    except LaunchError as exc: output = {"status": "failed", "error_code": exc.code, "message": str(exc), **exc.details}
    except Exception as exc: output = {"status": "failed", "error_code": "WRAPPER_INITIALIZATION_FAILED", "message": str(exc)}
    print(json.dumps(output, sort_keys=True)); return 0 if output["status"] == "ready" else 1


if __name__ == "__main__": raise SystemExit(main())
