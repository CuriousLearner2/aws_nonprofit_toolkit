#!/usr/bin/env python3
"""Fixed-argv, preflight-first Householder campaign launcher."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import secrets
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
PYTHON311_VENV = os.environ.get("HOUSEHOLDER_PYTHON311_VENV", "/Users/gautambiswas/.householder/envs/python311")
EXPECTED_ENVIRONMENT_FINGERPRINT = os.environ.get("HOUSEHOLDER_ENVIRONMENT_FINGERPRINT", "")
REMOTE_URL = os.environ.get("HOUSEHOLDER_GITHUB_REMOTE", "")
MARKERS = ("scripts/ci/householder_campaign.py", "scripts/ci/architecture_slice_gate.py", "scripts/householder/autosave_service.py", "tests/integration/test_autosave_validation.py")
ERRORS = {"BASELINE_UNAVAILABLE", "BASELINE_MISMATCH", "MIRROR_UNAVAILABLE", "CHECKOUT_COLLISION", "PROJECT_ROOT_UNAVAILABLE", "PROJECT_ROOT_AMBIGUOUS", "ENVIRONMENT_MISMATCH", "SUITE_PREFLIGHT_FAILED", "SUITE_PATH_INVALID", "SCOPE_OVERLAP", "SCOPE_LOCK_LIVE", "SCOPE_LOCK_IDENTITY_AMBIGUOUS", "SCOPE_LOCK_STALE_UNSAFE", "PROCESS_IDENTITY_CORRUPT", "CONTRACT_INVALID", "WRAPPER_INITIALIZATION_FAILED", "LAUNCH_STATE_CONFLICT", "PARTIAL_CLEANUP_FAILED", "LAUNCHER_STAGE_OVERRIDE_REJECTED"}


class LaunchError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        if code not in ERRORS: raise ValueError(code)
        super().__init__(message); self.code = code; self.details = details or {}


def _sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def _digest(value: Any) -> str: return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


PROCESS_TOKEN = secrets.token_urlsafe(32)
PROCESS_TOKEN_CREATED_AT = _now()


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
    if isinstance(value, dict) and any(field in value for field in ("stage", "stage_id", "stage_index", "command_override", "suite_override", "file_override")):
        raise LaunchError("LAUNCHER_STAGE_OVERRIDE_REJECTED", "stage selection is ledger-owned")
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


def _declared_packages(project: Path) -> list[str]:
    packages: list[str] = []
    for path in (project / "requirements.txt", project / "requirements-test.txt"):
        if not path.is_file():
            raise LaunchError("ENVIRONMENT_MISMATCH", f"declared requirements file is missing: {path.name}")
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                packages.append(line.split("==", 1)[0].split("[", 1)[0].strip())
    return list(dict.fromkeys(packages))


def _environment_executable() -> tuple[Path, bool]:
    if PYTHON311_VENV:
        root = Path(PYTHON311_VENV).expanduser()
        candidate = root / "bin" / "python3.11"
        if not candidate.is_file():
            candidate = root / "bin" / "python"
        if not candidate.is_file() or not (root / "pyvenv.cfg").is_file():
            raise LaunchError("ENVIRONMENT_MISMATCH", "configured Python 3.11 venv is incomplete")
        if root.resolve() != root:
            raise LaunchError("ENVIRONMENT_MISMATCH", "configured Python 3.11 venv is symlinked")
        return candidate, True
    candidate = Path(PYTHON311) if Path(PYTHON311).is_absolute() else Path(shutil.which(PYTHON311) or "")
    if not candidate.is_file():
        raise LaunchError("ENVIRONMENT_MISMATCH", "approved Python 3.11 executable is unavailable")
    return candidate, False


def _environment(project: Path) -> dict[str, Any]:
    executable, is_venv = _environment_executable()
    probe = subprocess.run([str(executable), "-c", "import platform,sys; print(sys.executable); print(*sys.version_info[:3]); print(platform.platform()); print(platform.machine())"], text=True, capture_output=True, check=False)
    lines = probe.stdout.splitlines()
    if probe.returncode or len(lines) != 4 or lines[1].split()[:2] != ["3", "11"]:
        raise LaunchError("ENVIRONMENT_MISMATCH", "approved executable is not Python 3.11", {"stdout": probe.stdout, "stderr": probe.stderr})
    requirements = [project / "requirements.txt", project / "requirements-test.txt"]
    declared = _declared_packages(project)
    package_probe = "import importlib.metadata,json; names=json.loads(__import__('sys').argv[1]); out={}; missing=[]\nfor name in names:\n key=name.lower().replace('_','-')\n try: out[key]=importlib.metadata.version(name)\n except importlib.metadata.PackageNotFoundError:\n  try: out[key]=importlib.metadata.version(key)\n  except importlib.metadata.PackageNotFoundError: missing.append(name)\nprint(json.dumps({'versions':out,'missing':missing},sort_keys=True))"
    package_run = subprocess.run([str(executable), "-c", package_probe, json.dumps(declared)], text=True, capture_output=True, check=False)
    if package_run.returncode:
        raise LaunchError("ENVIRONMENT_MISMATCH", "package probe failed", {"stdout": package_run.stdout, "stderr": package_run.stderr})
    try:
        package_result = json.loads(package_run.stdout)
    except json.JSONDecodeError as exc:
        raise LaunchError("ENVIRONMENT_MISMATCH", "package probe returned invalid JSON", {"stdout": package_run.stdout, "stderr": package_run.stderr}) from exc
    packages = package_result.get("versions", {})
    missing = package_result.get("missing", [])
    if missing:
        raise LaunchError("ENVIRONMENT_MISMATCH", "declared packages are unavailable", {"missing_packages": missing, "python_executable": lines[0]})
    import_names = [name.lower().replace("-", "_") for name in declared]
    import_probe = "import importlib.util,json; names=json.loads(__import__('sys').argv[1]); print(json.dumps([name for name in names if importlib.util.find_spec(name) is None]))"
    import_run = subprocess.run([str(executable), "-c", import_probe, json.dumps(import_names)], text=True, capture_output=True, check=False)
    if import_run.returncode:
        raise LaunchError("ENVIRONMENT_MISMATCH", "import probe failed", {"stdout": import_run.stdout, "stderr": import_run.stderr})
    missing_imports = json.loads(import_run.stdout or "[]")
    if missing_imports:
        raise LaunchError("ENVIRONMENT_MISMATCH", "declared imports are unavailable", {"missing_imports": missing_imports, "python_executable": lines[0]})
    freeze = subprocess.run([str(executable), "-m", "pip", "freeze"], text=True, capture_output=True, check=False)
    if freeze.returncode:
        raise LaunchError("ENVIRONMENT_MISMATCH", "pip freeze failed", {"stdout": freeze.stdout, "stderr": freeze.stderr})
    fingerprint_payload = {"python_version": lines[1], "python_executable": lines[0], "requirements_sha256": {p.name: _sha(p.read_bytes()) for p in requirements}, "freeze_sha256": _sha(freeze.stdout.encode()), "installed_packages": packages, "imported_modules": import_names, "platform": lines[2], "architecture": lines[3], "venv": is_venv}
    fingerprint = _sha(json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode())
    if not is_venv and EXPECTED_ENVIRONMENT_FINGERPRINT != fingerprint:
        raise LaunchError("ENVIRONMENT_MISMATCH", "bare interpreter does not match expected environment fingerprint", {"fingerprint": fingerprint})
    return {**fingerprint_payload, "fingerprint": fingerprint}


def _wrapper(project: Path):
    path = project / "scripts/ci/householder_campaign.py"
    spec = importlib.util.spec_from_file_location("householder_fixed_wrapper", path)
    if spec is None or spec.loader is None: raise LaunchError("WRAPPER_INITIALIZATION_FAILED", "wrapper cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    try: spec.loader.exec_module(module)
    except Exception as exc: raise LaunchError("WRAPPER_INITIALIZATION_FAILED", "wrapper failed to load") from exc
    return module


def _suite_records(project: Path, suite_ids: list[str], executable: str, environment: dict[str, Any]) -> list[dict[str, Any]]:
    registry = getattr(_wrapper(project), "SUITE_REGISTRY", {})
    records = []
    for suite_id in suite_ids:
        argv = registry.get(suite_id)
        if not isinstance(argv, list) or len(argv) < 2 or any(not isinstance(a, str) for a in argv): raise LaunchError("SUITE_PREFLIGHT_FAILED", f"suite is not in fixed registry: {suite_id}")
        command = [executable, *argv[1:]]
        referenced = [arg for arg in argv[1:] if arg.startswith("tests/") or arg.startswith("scripts/")]
        missing = [arg for arg in referenced if not (project / arg).is_file()]
        if missing:
            raise LaunchError("SUITE_PATH_INVALID", f"fixed suite paths are missing: {suite_id}", {"missing_paths": missing})
        records.append({"suite_id": suite_id, "argv": command, "cwd_role": "project_root", "cwd": str(project), "interpreter": executable, "environment_fingerprint": environment["fingerprint"]})
    return records


def _preflight(project: Path, suite_ids: list[str], executable: str, environment: dict[str, Any], deadline: float) -> list[dict[str, Any]]:
    results = []
    for record in _suite_records(project, suite_ids, executable, environment):
        command = record["argv"]
        try: run = subprocess.run(command, cwd=project, text=True, capture_output=True, check=False, timeout=max(1, int(deadline - time.time())))
        except (OSError, subprocess.TimeoutExpired) as exc: raise LaunchError("SUITE_PREFLIGHT_FAILED", f"suite did not complete: {record['suite_id']}") from exc
        entry = {**record, "exit_code": run.returncode, "passed": run.returncode == 0, "stdout": run.stdout, "stderr": run.stderr}; results.append(entry)
        if run.returncode: raise LaunchError("SUITE_PREFLIGHT_FAILED", f"suite failed: {record['suite_id']}", {"suite_results": results})
    return results


def _process_identity(pid: int) -> str | None:
    try: result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="], text=True, capture_output=True, check=False)
    except OSError: return None
    return result.stdout.strip() or None


def _alive(pid: int) -> bool | None:
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False
    except PermissionError: return None
    except OSError: return None


def _process_token_root() -> Path:
    return STATE_ROOT / "process-tokens"


def _process_registration_path(pid: int) -> Path:
    return _process_token_root() / f"pid-{pid}.json"


def _process_owner_path(pid: int, token: str) -> Path:
    return _process_token_root() / f"owner-{pid}-{token}.json"


def _process_state(campaign_id: str, operation_id: str) -> tuple[Path, Path]:
    pid = os.getpid()
    registration = _process_registration_path(pid)
    owner = _process_owner_path(pid, PROCESS_TOKEN)
    state = {"pid": pid, "process_token": PROCESS_TOKEN, "campaign_id": campaign_id, "operation_id": operation_id, "created_at": PROCESS_TOKEN_CREATED_AT}
    try:
        _atomic(registration, state)
        _atomic(owner, state)
    except OSError as exc:
        owner.unlink(missing_ok=True)
        registration.unlink(missing_ok=True)
        raise LaunchError("PROCESS_IDENTITY_CORRUPT", "process identity state cannot be persisted") from exc
    return registration, owner


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LaunchError("PROCESS_IDENTITY_CORRUPT", "process identity state is unreadable") from exc
    if not isinstance(value, dict):
        raise LaunchError("PROCESS_IDENTITY_CORRUPT", "process identity state is malformed")
    return value


def _validate_process_owner(record: dict[str, Any]) -> None:
    try:
        pid = int(record["pid"]); token = record["process_token"]; owner_path = Path(record["owner_state"])
        if not isinstance(token, str) or not token or owner_path != _process_owner_path(pid, token): raise ValueError
        owner = _read_json(owner_path)
        registration = _read_json(_process_registration_path(pid))
        required = {"pid": pid, "process_token": token, "campaign_id": record["campaign_id"], "operation_id": record["launcher_operation_id"], "created_at": record["process_created_at"]}
        if any(owner.get(key) != value for key, value in required.items()) or any(registration.get(key) != value for key, value in required.items()): raise ValueError
    except (KeyError, TypeError, ValueError):
        raise LaunchError("PROCESS_IDENTITY_CORRUPT", "process identity token state does not match lock")


def _cleanup_process_state(registration: Path | None, owner: Path | None) -> None:
    if owner is not None: owner.unlink(missing_ok=True)
    if registration is not None:
        try:
            current = _read_json(registration)
        except LaunchError:
            registration.unlink(missing_ok=True)
            current = {}
        if current.get("process_token") == PROCESS_TOKEN: registration.unlink(missing_ok=True)


@contextmanager
def scope_lock(campaign_id: str, mode: str, checkout: Path, paths: list[str], operation_id: str):
    if mode == "discovery": yield []; return
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    guard = LOCK_ROOT / ".scope.lock"
    with guard.open("a+") as handle:
        import fcntl; fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        acquired: list[Path] = []
        registration: Path | None = None
        owner: Path | None = None
        try:
            requested = set(paths)
            registration, owner = _process_state(campaign_id, operation_id)
            for path in sorted(LOCK_ROOT.glob("*.json")):
                record = _read_json(path)
                try: pid = int(record["pid"])
                except (KeyError, TypeError, ValueError) as exc: raise LaunchError("PROCESS_IDENTITY_CORRUPT", "scope lock owner is malformed") from exc
                alive = _alive(pid)
                if alive is None: raise LaunchError("SCOPE_LOCK_IDENTITY_AMBIGUOUS", "scope lock process liveness is ambiguous")
                _validate_process_owner(record)
                if alive:
                    supplementary = _process_identity(pid)
                    if supplementary and record.get("process_start_identity") and supplementary != record["process_start_identity"]:
                        raise LaunchError("PROCESS_IDENTITY_CORRUPT", "supplementary process identity does not match lock")
                    if requested.intersection(record.get("authorized_paths", [])):
                        raise LaunchError("SCOPE_LOCK_LIVE", "live scope lock overlaps requested scope", {"error_class": "SCOPE_OVERLAP"})
                    raise LaunchError("SCOPE_LOCK_LIVE", "scope lock owner is live")
                path.unlink(missing_ok=True)
                owner_path = Path(record["owner_state"])
                owner_path.unlink(missing_ok=True)
                _process_registration_path(pid).unlink(missing_ok=True)
            target = LOCK_ROOT / f"{campaign_id}-{uuid.uuid4().hex}.json"
            record = {"campaign_id": campaign_id, "mode": mode, "checkout": str(checkout), "authorized_paths": sorted(requested), "pid": os.getpid(), "process_token": PROCESS_TOKEN, "owner_state": str(owner), "process_created_at": PROCESS_TOKEN_CREATED_AT, "process_start_identity": _process_identity(os.getpid()), "acquisition_timestamp": _now(), "launcher_operation_id": operation_id}
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as output: json.dump(record, output, sort_keys=True); output.write("\n"); output.flush(); os.fsync(output.fileno())
            acquired.append(target); yield [str(target)]
        finally:
            for path in acquired: path.unlink(missing_ok=True)
            _cleanup_process_state(registration, owner)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
        environment = _environment(project); suites = _preflight(project, payload["suite_ids"], environment["python_executable"], environment, time.time() + payload["time_limit_seconds"])
        with scope_lock(payload["campaign_id"], payload["mode"], project, payload["authorized_production_paths"] + payload["authorized_test_paths"], operation_id) as locks:
            wrapper = _wrapper(project)
            if payload["mode"] == "discovery": wrapper_state = wrapper.campaign_discovery_start(payload["campaign_id"], operation_id)
            else:
                contract = _contract(project, payload, operation_id, wrapper); gate = _git_out(project, "hash-object", str(project / "scripts/ci/architecture_slice_gate.py")); contract_sha = wrapper._json_sha256(json.loads(contract.read_text(encoding="utf-8")))
                wrapper.campaign_ledger_init(payload["campaign_id"], operation_id, project, gate, [{"path": str(contract), "sha256": contract_sha}], payload["suite_ids"])
                if wrapper.is_parent_contract(contract):
                    wrapper_state = wrapper.campaign_parent_next(payload["campaign_id"], operation_id + "-start-stage")
                else:
                    wrapper.campaign_ledger_next(payload["campaign_id"]); wrapper_state = wrapper.campaign_ledger_start_edit(payload["campaign_id"], 0, operation_id + "-start-edit")
            output = {"status": "ready", "error_code": None, "baseline": resolution, "checkout": str(checkout), "git_root": identity["git_root"], "project_root": identity["project_root"], "environment_fingerprint": environment, "suite_results": suites, "typed_suite_records": suites, "acquired_locks": locks, "ledger_path": str(wrapper._ledger_file(payload["campaign_id"])), "wrapper_state": wrapper_state}
            _atomic(state_path, {"input_sha256": digest, "operation_id": operation_id, "status": "ready", "output": output}); return output
    except LaunchError:
        try: shutil.rmtree(checkout); state_path.unlink(missing_ok=True)
        except OSError as exc: raise LaunchError("PARTIAL_CLEANUP_FAILED", "partial cleanup failed") from exc
        raise
    except Exception as exc:
        try: shutil.rmtree(checkout); state_path.unlink(missing_ok=True)
        except OSError as cleanup: raise LaunchError("PARTIAL_CLEANUP_FAILED", "partial cleanup failed") from cleanup
        raise LaunchError("WRAPPER_INITIALIZATION_FAILED", "launcher failed") from exc


def _bounded(value: Any, limit: int = 20000) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "\n...[truncated]"
    if isinstance(value, list):
        return [_bounded(item, limit) for item in value]
    if isinstance(value, dict):
        return {key: _bounded(item, limit) for key, item in value.items()}
    return value


def doctor(payload: dict[str, Any] | Path) -> dict[str, Any]:
    payload = load_input(payload) if isinstance(payload, Path) else _normalise_input(payload)
    checkout: Path | None = None
    try:
        resolution = _resolve_baseline(payload["baseline"])
        LAUNCH_ROOT.mkdir(parents=True, exist_ok=True)
        checkout = Path(tempfile.mkdtemp(prefix=f"doctor-{payload['campaign_id']}-", dir=LAUNCH_ROOT))
        shutil.rmtree(checkout)
        _clone(checkout, payload["baseline"])
        project = discover_project_root(checkout)
        environment = _environment(project)
        suites = _preflight(project, payload["suite_ids"], environment["python_executable"], environment, time.time() + payload["time_limit_seconds"])
        return _bounded({"status": "READY", "error_code": None, "baseline": resolution, "git_root": str(Path(_git_out(project, "rev-parse", "--show-toplevel"))), "project_root": str(project), "environment_fingerprint": environment, "suite_records": suites})
    except LaunchError as exc:
        return _bounded({"status": "ERROR", "error_code": exc.code, "message": str(exc), **exc.details})
    except Exception as exc:
        return _bounded({"status": "ERROR", "error_code": "WRAPPER_INITIALIZATION_FAILED", "message": str(exc)})
    finally:
        if checkout is not None:
            shutil.rmtree(checkout, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic Householder campaign launcher"); parser.add_argument("command", choices=["launch", "doctor"]); parser.add_argument("--input", required=True, type=Path); args = parser.parse_args(argv)
    if args.command == "doctor":
        output = doctor(args.input)
        print(json.dumps(output, sort_keys=True)); return 0 if output["status"] == "READY" else 1
    try: output = launch(args.input)
    except LaunchError as exc: output = {"status": "failed", "error_code": exc.code, "message": str(exc), **exc.details}
    except Exception as exc: output = {"status": "failed", "error_code": "WRAPPER_INITIALIZATION_FAILED", "message": str(exc)}
    print(json.dumps(output, sort_keys=True)); return 0 if output["status"] == "ready" else 1


if __name__ == "__main__": raise SystemExit(main())
