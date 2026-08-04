#!/usr/bin/env python3
"""Immutable campaign-contract storage for Householder."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import shlex
import tempfile
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from .householder_paths import (
        CanonicalPathError,
        canonical_changed_paths,
        canonicalize,
        canonicalize_git_path,
        canonicalize_many,
        discover_layout,
        resolve_in_project,
        sha256_patch,
        to_git_path,
        validate_project_relative,
    )
except ImportError:  # pragma: no cover - direct script execution
    from householder_paths import (
        CanonicalPathError,
        canonical_changed_paths,
        canonicalize,
        canonicalize_git_path,
        canonicalize_many,
        discover_layout,
        resolve_in_project,
        sha256_patch,
        to_git_path,
        validate_project_relative,
    )



SCHEMA_VERSION = 1
PARENT_SCHEMA_VERSION = 2
PARENT_STAGES = ("STRUCTURE", "INTEGRATION", "CLEANUP")
PARENT_TERMINAL_STATES = {"VALIDATED", "COMMITTED"}
STATE_DIR = Path("Givebutter/.artifacts")
STATE_PREFIX = "householder-campaign"
PROJECT_MARKERS = (
    "scripts/ci/householder_campaign.py",
    "scripts/ci/architecture_slice_gate.py",
    "scripts/householder/autosave_service.py",
    "tests/integration/test_autosave_validation.py",
)


def repo_root() -> Path:
    return _discover_repo_root()


def _discover_repo_root(script_file: Path | None = None) -> Path:
    """Discover the Git root from the wrapper's own checkout location."""
    source = Path(script_file) if script_file is not None else Path(__file__)
    try:
        resolved_file = source.resolve(strict=True)
    except OSError as exc:
        raise ValueError("REPOSITORY_ROOT_DISCOVERY_FAILED: wrapper path is unavailable") from exc
    if source != resolved_file:
        raise ValueError("REPOSITORY_ROOT_DISCOVERY_FAILED: wrapper path is symlinked")
    anchor = resolved_file.parent
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=anchor,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("REPOSITORY_ROOT_DISCOVERY_FAILED: wrapper is outside a Git checkout")
    try:
        root = Path(result.stdout.strip()).resolve(strict=True)
        resolved_file.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("REPOSITORY_ROOT_DISCOVERY_FAILED: discovered root conflicts with wrapper checkout") from exc
    return root


def _discover_project_root(git_root: Path) -> Path:
    """Find the sole canonical Householder project beneath a Git root."""
    git_root = Path(git_root).resolve(strict=True)
    candidates = [git_root, git_root / "aws_nonprofit_toolkit" / "Givebutter"]
    valid: list[Path] = []
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if resolved != candidate or not resolved.is_dir():
            raise ValueError("PROJECT_ROOT_DISCOVERY_FAILED: project root is symlinked")
        if not all((resolved / marker).is_file() for marker in PROJECT_MARKERS):
            continue
        if not _under(resolved, git_root, "PROJECT_ROOT_DISCOVERY_FAILED"):
            raise ValueError("PROJECT_ROOT_DISCOVERY_FAILED: project root escapes Git root")
        valid.append(resolved)
    if len(valid) != 1:
        raise ValueError("PROJECT_ROOT_DISCOVERY_FAILED: expected exactly one Householder project root")
    return valid[0]


def project_root() -> Path:
    return _discover_project_root(repo_root())


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow() -> str:
    return _now_utc().isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_task_id(task_id: str) -> str:
    cleaned = task_id.strip()
    if cleaned != task_id or not cleaned or "/" in cleaned or "\\" in cleaned:
        raise CampaignError("INVALID_CAMPAIGN_ID", "campaign-id must be a non-empty string without path separators")
    return cleaned


def _record_path(task_id: str) -> Path:
    return repo_root() / STATE_DIR / f"{STATE_PREFIX}.{task_id}.json"


def _lock_path(task_id: str) -> Path:
    return _record_path(task_id).with_name(_record_path(task_id).name + ".lock")


@contextmanager
def _record_lock(task_id: str):
    lock_path = _lock_path(task_id)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - non-POSIX fallback
            pass
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except ImportError:  # pragma: no cover - non-POSIX fallback
            pass
        handle.close()


def _git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd or repo_root(), capture_output=True, text=True, check=False)


def _git_output(args: list[str], *, cwd: Path | None = None) -> str:
    result = _git(args, cwd=cwd)
    if result.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed")
    return result.stdout


def _current_branch(cwd: Path) -> str:
    branch = _git_output(["branch", "--show-current"], cwd=cwd).strip()
    if not branch:
        raise ValueError("detached HEAD is not allowed")
    return branch


def _json_sha256(payload: Any) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _digest_contract(contract: dict[str, Any]) -> dict[str, Any]:
    digest_contract = dict(contract)
    digest_contract.pop("campaign_type", None)
    return digest_contract


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _normalize_authorized_file(value: Any) -> str:
    cleaned = _require_string(value, "authorized_files entry")
    if cleaned.startswith(("/", "./")) or "\\" in cleaned:
        raise ValueError("authorized_files must be normalized")
    path = PurePosixPath(cleaned)
    if path.as_posix() != cleaned or any(part == ".." for part in path.parts):
        raise ValueError("authorized_files must be normalized")
    return cleaned


def _normalize_work_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("work_items must contain objects")
    required = {"id", "type", "description", "acceptance_criteria", "focused_test_commands", "allowed_action_types"}
    missing = required - set(item)
    if missing:
        raise ValueError("work item missing required fields")
    acceptance = item["acceptance_criteria"]
    commands = item["focused_test_commands"]
    actions = item["allowed_action_types"]
    if not isinstance(acceptance, list) or not acceptance:
        raise ValueError("acceptance_criteria must be a non-empty list")
    if not isinstance(commands, list) or not commands:
        raise ValueError("focused_test_commands must be a non-empty list")
    if not isinstance(actions, list) or not actions:
        raise ValueError("allowed_action_types must be a non-empty list")
    normalized_commands: list[list[str]] = []
    for command in commands:
        if not isinstance(command, list) or not command:
            raise ValueError("focused_test_commands must contain command lists")
        normalized_commands.append([_require_string(part, "focused_test_commands entry") for part in command])
    return {
        "id": _require_string(item["id"], "work_item id"),
        "type": _require_string(item["type"], "work_item type"),
        "description": _require_string(item["description"], "work_item description"),
        "acceptance_criteria": [_require_string(entry, "acceptance_criteria entry") for entry in acceptance],
        "focused_test_commands": normalized_commands,
        "allowed_action_types": [_require_string(entry, "allowed_action_types entry") for entry in actions],
    }


def _normalize_contract(contract: Any) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ValueError("campaign contract must be an object")
    required = {
        "schema_version",
        "task_id",
        "campaign_type",
        "workflow_id",
        "strategy_id",
        "work_items",
        "authorized_files",
        "implementation_changed_lines_max",
        "test_changed_lines_max",
        "tracked_files_max",
        "focused_runs_max",
        "implementation_repairs_max",
        "test_harness_repairs_max",
        "review_repairs_max",
    }
    missing = required - set(contract)
    if missing:
        raise ValueError("campaign contract missing required fields")
    if contract["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported campaign contract schema")
    work_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw_item in contract["work_items"]:
        item = _normalize_work_item(raw_item)
        if item["id"] in seen_ids:
            raise ValueError("duplicate work-item IDs")
        seen_ids.add(item["id"])
        work_items.append(item)
    files: list[str] = []
    seen_files: set[str] = set()
    for raw in contract["authorized_files"]:
        path = _normalize_authorized_file(raw)
        if path in seen_files:
            raise ValueError("duplicate authorized_files")
        seen_files.add(path)
        files.append(path)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": _validate_task_id(_require_string(contract["task_id"], "task_id")),
        "campaign_type": _require_string(contract["campaign_type"], "campaign_type"),
        "workflow_id": _require_string(contract["workflow_id"], "workflow_id"),
        "strategy_id": _require_string(contract["strategy_id"], "strategy_id"),
        "work_items": work_items,
        "authorized_files": files,
        "implementation_changed_lines_max": _require_int(contract["implementation_changed_lines_max"], "implementation_changed_lines_max"),
        "test_changed_lines_max": _require_int(contract["test_changed_lines_max"], "test_changed_lines_max"),
        "tracked_files_max": _require_int(contract["tracked_files_max"], "tracked_files_max"),
        "focused_runs_max": _require_int(contract["focused_runs_max"], "focused_runs_max"),
        "implementation_repairs_max": _require_int(contract["implementation_repairs_max"], "implementation_repairs_max"),
        "test_harness_repairs_max": _require_int(contract["test_harness_repairs_max"], "test_harness_repairs_max"),
        "review_repairs_max": _require_int(contract["review_repairs_max"], "review_repairs_max"),
    }


def _load_record(task_id: str) -> dict[str, Any]:
    path = _record_path(task_id)
    if not path.exists():
        raise ValueError("campaign record missing")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("campaign record malformed") from exc
    if not isinstance(record, dict):
        raise ValueError("campaign record malformed")
    required = {
        "schema_version",
        "task_id",
        "branch",
        "worktree_path",
        "head_sha",
        "main_sha",
        "contract",
        "contract_sha256",
        "current_work_item_index",
        "work_item_statuses",
        "counters",
        "pending_action",
        "final_state",
        "stop_reason",
        "created_at",
    }
    missing = required - set(record)
    if missing:
        raise ValueError("campaign record missing required fields")
    if record["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported campaign record schema")
    if record["task_id"] != task_id:
        raise ValueError("task_id mismatch")
    normalized = _normalize_contract(record["contract"])
    if normalized != record["contract"]:
        raise ValueError("stored contract mutated")
    if _json_sha256(_digest_contract(normalized)) != record["contract_sha256"]:
        raise ValueError("contract digest mismatch")
    if not isinstance(record["work_item_statuses"], list) or len(record["work_item_statuses"]) != len(normalized["work_items"]):
        raise ValueError("campaign record malformed")
    if not isinstance(record["counters"], dict):
        raise ValueError("campaign record malformed")
    return record


def _write_atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            tmp_path = Path(handle.name)
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except OSError:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()
        raise


def _current_identity() -> dict[str, str]:
    root = repo_root()
    return {
        "branch": _current_branch(root),
        "worktree_path": str(Path.cwd().resolve()),
        "head_sha": _git_output(["rev-parse", "HEAD"], cwd=root).strip(),
        "main_sha": _git_output(["rev-parse", "origin/main"], cwd=root).strip(),
    }


def _initialize_record(task_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    identity = _current_identity()
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        **identity,
        "contract": contract,
        "contract_sha256": _json_sha256(_digest_contract(contract)),
        "current_work_item_index": 0,
        "work_item_statuses": ["pending" for _ in contract["work_items"]],
        "counters": {
            "focused_runs_used": 0,
            "implementation_repairs_used": 0,
            "review_repairs_used": 0,
            "test_harness_repairs_used": 0,
        },
        "pending_action": None,
        "final_state": "active",
        "stop_reason": None,
        "created_at": _utcnow(),
    }


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {**record, "campaign_type": record["contract"]["campaign_type"]}


def campaign_initialize(task_id: str, contract_file: Path | str) -> dict[str, Any]:
    raise ValueError("legacy repo-local campaign state is disabled; use the external ledger")


def campaign_status(task_id: str) -> dict[str, Any]:
    raise ValueError("legacy repo-local campaign state is disabled; use the external ledger")


# External stateful ledger surface. Legacy repo-local state APIs are disabled.
DEFAULT_LEDGER_ROOT = Path("/private/tmp/householder-campaigns")
LEDGER_ROOT = Path(os.environ.get("HOUSEHOLDER_LEDGER_ROOT", str(DEFAULT_LEDGER_ROOT)))
DISCOVERY_RUN_ROOT = Path("/private/tmp/householder-discoveries")
DISCOVERY_DEADLINE = timedelta(minutes=30)
CAMPAIGN_STATES = {"READY", "ACTIVE", "VALIDATING", "COMMITTED", "FAILED", "QUARANTINED", "STOPPED"}
CAMPAIGN_TERMINAL = {"COMMITTED", "FAILED", "QUARANTINED", "STOPPED"}
SUITE_REGISTRY = {
    "wrapper-unit": ["python3", "-m", "pytest", "-q", "tests/unit/test_householder_campaign.py"],
    "export-preview-unit": [sys.executable, "-m", "pytest", "-q", "tests/unit/test_export_preview_service.py"],
    "validation-unit": [sys.executable, "-m", "pytest", "-q", "tests/unit/test_validation_service.py"],
    "ingestion-unit": [sys.executable, "-m", "pytest", "-q", "tests/unit/test_ingestion_service.py"],
    "ingestion-database-integration": [sys.executable, "-m", "pytest", "-q", "tests/integration/test_ingestion_service_database.py"],
    "issue-recalculation-integration": [sys.executable, "-m", "pytest", "-q", "tests/integration/test_validation_review_workflows.py"],
    "autosave-integration": [sys.executable, "-m", "pytest", "-q", "tests/integration/test_autosave_validation.py"],
}


TYPED_CONTRACT_FIELDS = {
    "baseline_head",
    "gate_sha",
    "allowed_files",
    "max_production_lines",
    "max_test_lines",
    "suite_ids",
    "invariants",
    "completed_seams",
    "completed_seam_files",
    "protected_files",
}

PARENT_CONTRACT_FIELDS = {
    "id", "authorized_files", "stages",
}
PARENT_STAGE_FIELDS = {
    "id", "ordinal", "allowed_files", "suite_ids", "max_production_lines",
    "max_test_lines", "required_evidence",
}
PARENT_ERROR_CODES = {
    "PARENT_CONTRACT_MALFORMED", "PARENT_SCOPE_CONFLICT", "PARENT_SEAM_COMPLETED",
    "STAGE_NOT_FOUND", "STAGE_ORDER_VIOLATION", "STAGE_FILE_OUTSIDE_PARENT",
    "STAGE_ALREADY_COMPLETE", "STAGE_EVIDENCE_INCOMPLETE",
    "STAGE_RETRY_MISMATCH", "LAUNCHER_STAGE_OVERRIDE_REJECTED",
}
PARENT_EVIDENCE_FIELDS = {"gate_pass", "tests_pass", "diff_check_pass", "scope_pass", "ceiling_pass"}


def configure_ledger_root(root: str | Path) -> Path:
    """Set the external ledger root for this wrapper process."""
    global LEDGER_ROOT
    LEDGER_ROOT = Path(root)
    return LEDGER_ROOT


def _normalized_relative_paths(items: Any, field: str) -> list[str]:
    if type(items) is not list:
        raise _fail("CONTRACT_MALFORMED", f"{field} must be a JSON array")
    normalized: list[str] = []
    for item in items:
        try:
            value = validate_project_relative(item, field=field)
        except CanonicalPathError as exc:
            raise _fail("CONTRACT_MALFORMED", f"{field} entries must be relative paths") from exc
        normalized.append(value)
    if len(normalized) != len(set(normalized)):
        raise _fail("CONTRACT_MALFORMED", f"{field} entries must be unique")
    return normalized


def _strict_typed_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _fail("CONTRACT_MALFORMED", "typed contract must be an object")
    unknown = set(value) - TYPED_CONTRACT_FIELDS
    missing = TYPED_CONTRACT_FIELDS - set(value)
    if unknown or missing:
        raise _fail("CONTRACT_MALFORMED", "typed contract has missing or unknown fields")
    for field in ("baseline_head", "gate_sha"):
        item = value[field]
        if type(item) is not str or not item or item.strip() != item:
            raise _fail("CONTRACT_MALFORMED", f"{field} must be a trimmed string")
    for field in ("max_production_lines", "max_test_lines"):
        item = value[field]
        if type(item) is not int or item < 0 or item > 1_000_000:
            raise _fail("CONTRACT_MALFORMED", f"{field} must be a bounded non-negative integer")
    for field in ("suite_ids", "invariants"):
        items = value[field]
        if type(items) is not list or (field == "suite_ids" and not items):
            raise _fail("CONTRACT_MALFORMED", f"{field} must be a JSON array")
        if any(type(item) is not str or not item or item.strip() != item for item in items):
            raise _fail("CONTRACT_MALFORMED", f"{field} entries must be trimmed strings")
        if len(items) != len(set(items)):
            raise _fail("CONTRACT_MALFORMED", f"{field} entries must be unique")
    normalized = dict(value)
    normalized["allowed_files"] = _normalized_relative_paths(value["allowed_files"], "allowed_files")
    normalized["protected_files"] = _normalized_relative_paths(value["protected_files"], "protected_files")
    seams = value["completed_seams"]
    if type(seams) is not list or any(type(item) is not str or not item or item.strip() != item for item in seams):
        raise _fail("CONTRACT_MALFORMED", "completed_seams entries must be trimmed strings")
    if len(seams) != len(set(seams)):
        raise _fail("CONTRACT_MALFORMED", "completed_seams entries must be unique")
    seam_files = value["completed_seam_files"]
    if type(seam_files) is not dict or any(type(key) is not str or not key or key.strip() != key for key in seam_files):
        raise _fail("CONTRACT_MALFORMED", "completed_seam_files must map seam IDs to arrays")
    normalized["completed_seams"] = list(seams)
    normalized["completed_seam_files"] = {key: _normalized_relative_paths(files, f"completed_seam_files[{key}]") for key, files in seam_files.items()}
    return {field: normalized[field] for field in sorted(TYPED_CONTRACT_FIELDS)}


def _strict_contract(payload: Any, *, baseline_head: str | None = None, gate_sha: str | None = None, suite_ids: list[str] | None = None) -> dict[str, Any]:
    """Validate the exact typed metadata while preserving gate contract fields."""
    if not isinstance(payload, dict):
        raise _fail("CONTRACT_MALFORMED", "contract must be an object")
    typed = payload.get("typed_contract")
    strict_fields = TYPED_CONTRACT_FIELDS
    if typed is not None and set(payload) - {"typed_contract", "seam", "task_id"}:
        raise _fail("CONTRACT_MALFORMED", "typed contract envelope has unknown fields")
    if typed is None and strict_fields.intersection(payload):
        if set(payload) != strict_fields:
            raise _fail("CONTRACT_MALFORMED", "strict contract has missing or unknown fields")
        typed = payload
    if typed is None:
        typed = {
            "baseline_head": payload.get("baseline_head", payload.get("baseline_ref", baseline_head or "legacy")),
            "gate_sha": payload.get("gate_sha", payload.get("gate_blob_sha", gate_sha or "legacy")),
            "allowed_files": payload.get("allowed_files", payload.get("authorized_files", [])),
            "max_production_lines": payload.get("max_production_lines", payload.get("production_changed_lines_max", 0)),
            "max_test_lines": payload.get("max_test_lines", payload.get("test_changed_lines_max", 0)),
            "suite_ids": payload.get("suite_ids", suite_ids or ["wrapper-unit"]),
            "invariants": payload.get("invariants", []),
            "completed_seams": payload.get("completed_seams"),
            "completed_seam_files": payload.get("completed_seam_files"),
            "protected_files": payload.get("protected_files"),
        }
    parent = typed.get("parent_seam") if isinstance(typed, dict) else None
    if parent is not None:
        base = dict(typed)
        base.pop("parent_seam", None)
        normalized = _strict_typed_dict(base)
        normalized["parent_seam"] = _strict_parent_contract(parent, normalized)
    else:
        normalized = _strict_typed_dict(typed)
    if baseline_head is not None and normalized["baseline_head"] != baseline_head:
        raise _fail("BASELINE_MISMATCH", "contract baseline does not match repository HEAD")
    if gate_sha is not None and normalized["gate_sha"] != gate_sha:
        raise _fail("GATE_MUTATED", "contract gate digest does not match campaign gate")
    if any(item not in SUITE_REGISTRY for item in normalized["suite_ids"]):
        raise _fail("SUITE_NOT_ALLOWED", "typed contract contains an unknown suite")
    return normalized


def _strict_parent_contract(value: Any, base: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != PARENT_CONTRACT_FIELDS:
        raise _fail("PARENT_CONTRACT_MALFORMED", "parent contract has missing or unknown fields")
    parent_id = value["id"]
    if type(parent_id) is not str or not parent_id or parent_id.strip() != parent_id:
        raise _fail("PARENT_CONTRACT_MALFORMED", "parent id must be a trimmed string")
    authorized = _normalized_relative_paths(value["authorized_files"], "parent authorized_files")
    if authorized != base["allowed_files"]:
        raise _fail("PARENT_CONTRACT_MALFORMED", "parent authorized_files must equal the complete envelope")
    stages = value["stages"]
    if type(stages) is not list or not stages:
        raise _fail("PARENT_CONTRACT_MALFORMED", "parent stages must be a non-empty array")
    normalized_stages: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for expected, raw in enumerate(stages):
        if not isinstance(raw, dict) or set(raw) != PARENT_STAGE_FIELDS:
            raise _fail("PARENT_CONTRACT_MALFORMED", "stage has missing or unknown fields")
        stage_id = raw["id"]
        if type(stage_id) is not str or not stage_id or stage_id.strip() != stage_id or stage_id in seen_ids:
            raise _fail("PARENT_CONTRACT_MALFORMED", "stage IDs must be unique trimmed strings")
        if raw["ordinal"] != expected:
            raise _fail("PARENT_CONTRACT_MALFORMED", "stage ordinals must be contiguous")
        allowed = _normalized_relative_paths(raw["allowed_files"], f"stage {stage_id} allowed_files")
        if not set(allowed).issubset(authorized):
            raise _fail("STAGE_FILE_OUTSIDE_PARENT", "stage files must be inside the parent envelope")
        suite_ids = _suite_ids(raw["suite_ids"])
        evidence = raw["required_evidence"]
        if type(evidence) is not list or not evidence or any(type(item) is not str or not item or item.strip() != item for item in evidence):
            raise _fail("PARENT_CONTRACT_MALFORMED", "required_evidence must be a non-empty string array")
        if len(evidence) != len(set(evidence)):
            raise _fail("PARENT_CONTRACT_MALFORMED", "required_evidence entries must be unique")
        if not set(evidence).issubset(PARENT_EVIDENCE_FIELDS):
            raise _fail("PARENT_CONTRACT_MALFORMED", "required_evidence contains an unsupported field")
        normalized_stages.append({
            "id": stage_id, "ordinal": expected, "allowed_files": allowed,
            "suite_ids": suite_ids,
            "max_production_lines": _require_int(raw["max_production_lines"], "stage production ceiling"),
            "max_test_lines": _require_int(raw["max_test_lines"], "stage test ceiling"),
            "required_evidence": list(evidence),
        })
        seen_ids.add(stage_id)
    return {"id": parent_id, "authorized_files": authorized, "stages": normalized_stages}

class CampaignError(ValueError):
    def __init__(self, code: str, message: str): self.code = code; super().__init__(f"{code}: {message}")
def _fail(code: str, message: str) -> CampaignError:
    return CampaignError(code, message)
def _ledger_file(campaign_id: str) -> Path:
    return LEDGER_ROOT / _validate_task_id(campaign_id) / "state.json"
def _events_file(campaign_id: str) -> Path: return _ledger_file(campaign_id).with_name("events.jsonl")
def _operation_id(value: Any) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise _fail("INVALID_OPERATION_ID", "operation-id must be a non-empty string")
    return value
def _canonical_path(value: str | Path, code: str = "PATH_OUTSIDE_ROOT") -> Path:
    raw = str(value)
    if ".." in Path(raw).parts: raise _fail(code, "path traversal is not allowed")
    return Path(os.path.realpath(raw))


def _canonical_git_path(value: str, cwd: Path) -> Path:
    """Canonicalize a Git-produced path, including relative common-dir output."""
    path = Path(value)
    return Path(os.path.realpath(path if path.is_absolute() else cwd / path))
def _under(path: Path, root: Path, escape_code: str = "PATH_OUTSIDE_ROOT") -> bool:
    try: return os.path.commonpath((str(path), str(root))) == str(root)
    except ValueError: raise _fail(escape_code, "path is outside approved root")
def _suite_ids(value: Any) -> list[str]:
    ids = ["wrapper-unit"] if value is None else value
    if not isinstance(ids, list) or not ids or any(item not in SUITE_REGISTRY for item in ids): raise _fail("SUITE_NOT_ALLOWED", "unknown suite-id")
    return list(dict.fromkeys(ids))
def _operation_payload(command: str, payload: dict[str, Any]) -> str:
    return _json_sha256({"command": command, "payload": payload})
def _retry_result(record: dict[str, Any], operation_id: str, command: str, payload: dict[str, Any]) -> Any | None:
    digest = _operation_payload(command, payload)
    for operation in record.get("operations", []):
        if operation.get("operation_id") != operation_id:
            continue
        if operation.get("command") != command or operation.get("payload_sha256") != digest:
            raise _fail("OPERATION_CONFLICT", "operation-id was already used with different input")
        return operation["result"]
    return None
def _result_view(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "operations"}
def _record_operation(record: dict[str, Any], operation_id: str, command: str, payload: dict[str, Any], result: dict[str, Any]) -> None:
    record.setdefault("operations", []).append({"operation_id": operation_id, "command": command, "payload_sha256": _operation_payload(command, payload), "result": result})
def _suite_for(record: dict[str, Any], suite_id: str | None) -> dict[str, Any]:
    selected = suite_id or record["suites"][0]["id"]
    for suite in record["suites"]:
        if suite["id"] == selected:
            return suite
    raise _fail("SUITE_NOT_ALLOWED", "suite-id is not initialized")


DISCOVERY_TOP_LEVEL_FIELDS = {"schema_version", "discovery_id", "findings"}
DISCOVERY_FINDING_FIELDS = {
    "finding_id", "title", "files", "symbols", "observed_evidence", "risk",
    "confidence", "remediation_boundary", "required_tests", "estimated_size",
    "dependencies", "disposition",
}
DISCOVERY_DISPOSITIONS = {"proven", "needs-evidence", "test-blocked", "human-decision"}
DISCOVERY_SIZES = {"small", "medium", "large"}


def _discovery_string(value: Any, field: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise _fail("DISCOVERY_RESULT_INVALID", f"{field} must be a trimmed string")
    return value


def _validate_discovery_findings(payload: Any, record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != DISCOVERY_TOP_LEVEL_FIELDS:
        raise _fail("DISCOVERY_RESULT_INVALID", "findings envelope has missing or unknown fields")
    if payload["schema_version"] != 1 or payload["discovery_id"] != record["discovery_id"]:
        raise _fail("DISCOVERY_RESULT_INVALID", "findings identity or schema is invalid")
    if type(payload["findings"]) is not list:
        raise _fail("DISCOVERY_RESULT_INVALID", "findings must be an array")
    repo = Path(record["worktree_path"])
    normalized_findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for raw in payload["findings"]:
        if not isinstance(raw, dict) or set(raw) != DISCOVERY_FINDING_FIELDS:
            raise _fail("DISCOVERY_RESULT_INVALID", "finding has missing or unknown fields")
        finding_id = _discovery_string(raw["finding_id"], "finding_id")
        if finding_id in seen_ids:
            raise _fail("DISCOVERY_RESULT_INVALID", "finding IDs must be unique")
        seen_ids.add(finding_id)
        try:
            files = _normalized_relative_paths(raw["files"], "finding files")
        except CampaignError as exc:
            raise _fail("DISCOVERY_RESULT_INVALID", "finding files are not normalized") from exc
        for relative in files:
            candidate = repo / relative
            resolved = _canonical_path(candidate, "PATH_OUTSIDE_ROOT")
            if candidate.is_symlink():
                raise _fail("SYMLINK_ESCAPE", "finding evidence path is a symlink")
            if not _under(resolved, repo, "PATH_OUTSIDE_ROOT"):
                raise _fail("PATH_OUTSIDE_ROOT", "finding evidence path leaves the worktree")
            if not resolved.is_file():
                raise _fail("DISCOVERY_RESULT_INVALID", "finding evidence file does not exist")
        for field in ("symbols", "required_tests", "dependencies"):
            values = raw[field]
            if type(values) is not list or any(type(value) is not str or not value or value.strip() != value for value in values):
                raise _fail("DISCOVERY_RESULT_INVALID", f"{field} must be an array of strings")
        size = _discovery_string(raw["estimated_size"], "estimated_size")
        disposition = _discovery_string(raw["disposition"], "disposition")
        if size not in DISCOVERY_SIZES or disposition not in DISCOVERY_DISPOSITIONS:
            raise _fail("DISCOVERY_RESULT_INVALID", "finding enum is invalid")
        normalized_findings.append({
            "finding_id": finding_id,
            "title": _discovery_string(raw["title"], "title"),
            "files": files,
            "symbols": list(raw["symbols"]),
            "observed_evidence": _discovery_string(raw["observed_evidence"], "observed_evidence"),
            "risk": _discovery_string(raw["risk"], "risk"),
            "confidence": _discovery_string(raw["confidence"], "confidence"),
            "remediation_boundary": _discovery_string(raw["remediation_boundary"], "remediation_boundary"),
            "required_tests": list(raw["required_tests"]),
            "estimated_size": size,
            "dependencies": list(raw["dependencies"]),
            "disposition": disposition,
        })
    return {"schema_version": 1, "discovery_id": record["discovery_id"], "findings": normalized_findings}


def _discovery_findings_file(path: str | Path, record: dict[str, Any]) -> tuple[dict[str, Any], str]:
    source = _canonical_path(path, "PATH_OUTSIDE_ROOT")
    repo = Path(record["worktree_path"])
    if _under(source, repo, "PATH_OUTSIDE_ROOT"):
        raise _fail("PATH_OUTSIDE_ROOT", "findings must be outside the worktree")
    if Path(path).is_symlink():
        raise _fail("SYMLINK_ESCAPE", "findings file must not be a symlink")
    try:
        payload = _read_json(source)
    except (OSError, json.JSONDecodeError, CampaignError) as exc:
        raise _fail("DISCOVERY_RESULT_INVALID", "findings file is unreadable or malformed") from exc
    normalized = _validate_discovery_findings(payload, record)
    return normalized, _json_sha256(normalized)


def _discovery_findings_path(discovery_id: str) -> Path:
    return DISCOVERY_RUN_ROOT / _validate_task_id(discovery_id) / "findings.json"


def _store_discovery_findings(discovery_id: str, payload: dict[str, Any]) -> Path:
    path = _discovery_findings_path(discovery_id)
    _write_atomic_json(path, payload)
    return path


def _json_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("CONTRACT_MALFORMED", f"duplicate contract field: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_json_object_pairs)


def _finish_contract(path: str) -> dict[str, Any]:
    try: payload = _read_json(Path(path))
    except (OSError, json.JSONDecodeError) as exc: raise _fail("CONTRACT_NOT_INITIALIZED", "contract unreadable") from exc
    if not isinstance(payload, dict): raise _fail("CONTRACT_NOT_INITIALIZED", "contract malformed")
    return payload


def _finish_changes(record: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    repo = Path(record["worktree_path"]); authorized = set(_check_authorized(Path(record["contracts"][record["current_index"]]["path"]), repo)); status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, capture_output=True, text=True, check=False, shell=False)
    if status.returncode: raise _fail("GIT_PRECONDITION", "unable to inspect changed paths")
    raw = status.stdout
    entries = []
    for line in raw.splitlines():
        if not line: continue
        code, path = line[:2], _project_relative_path(repo, line[3:].strip().strip('"'))
        if "R" in code or "C" in code or "->" in path: raise _fail("RENAME_REJECTED", "renames and copies are not allowed")
        if path not in authorized: raise _fail("UNAUTHORIZED_CHANGE", "changed path is outside contract")
        target = repo / path
        if target.is_symlink(): raise _fail("SYMLINK_ESCAPE", "changed symlink is not allowed")
        if "160000" in _ledger_git(repo, "ls-files", "--stage", "--", path): raise _fail("SUBMODULE_REJECTED", "submodules are not allowed")
        if code == "??":
            if b"\0" in target.read_bytes(): raise _fail("BINARY_CHANGE", "binary files are not allowed")
        else:
            stats = _ledger_git(repo, "diff", "--numstat", "--no-ext-diff", "--", path).split("\t")
            if stats and stats[0] == "-": raise _fail("BINARY_CHANGE", "binary files are not allowed")
        entries.append({"path": path, "status": code})
    return entries


def _edit_diff_totals(record: dict[str, Any], changed: list[dict[str, Any]]) -> dict[str, int]:
    repo = Path(record["worktree_path"])
    totals = {"production": 0, "test": 0}
    for item in changed:
        path = item["path"]
        target = repo / path
        if item["status"] == "??":
            additions = target.read_bytes().count(b"\n")
            deletions = 0
        else:
            stats = _ledger_git(repo, "diff", "--numstat", "--no-ext-diff", "--", path).split("\t")
            if len(stats) < 2 or stats[0] == "-" or stats[1] == "-":
                raise _fail("BINARY_CHANGE", "binary files are not allowed")
            additions, deletions = int(stats[0]), int(stats[1])
        bucket = "test" if path.startswith("tests/") else "production"
        totals[bucket] += additions + deletions
    return totals


def _validate_admitted_edit_checkpoint(record: dict[str, Any]) -> None:
    pending = record.get("pending_action")
    admission = record.get("edit_admission")
    if record.get("state") != "ACTIVE" or not pending or pending.get("kind") != "IMPLEMENT":
        raise _fail("EDIT_NOT_ADMITTED", "checkpoint requires an active admitted edit")
    if admission is None or admission.get("contract_index") != record.get("current_index"):
        raise _fail("EDIT_NOT_ADMITTED", "checkpoint admission does not match current contract")
    contract = _finish_contract(record["contracts"][record["current_index"]]["path"])
    changed = _finish_changes(record, contract)
    totals = _edit_diff_totals(record, changed)
    typed = record["contracts"][record["current_index"]]["typed_contract"]
    if totals["production"] > typed["max_production_lines"] or totals["test"] > typed["max_test_lines"]:
        raise _fail("CEILING_EXCEEDED", "admitted edit exceeds contract ceiling")


def _finish_patch(repo: Path, paths: list[str]) -> bytes:
    layout = discover_layout(_canonical_path(_ledger_git(repo, "rev-parse", "--show-toplevel")), markers=PROJECT_MARKERS)
    git_root = layout.git_root
    patch = b""
    for path in sorted(paths):
        git_path = to_git_path(path, layout)
        status = _ledger_git(git_root, "status", "--porcelain=v1", "--", git_path)
        if status.startswith("??"):
            patch += subprocess.run(["git", "diff", "--binary", "--no-index", "/dev/null", git_path], cwd=git_root, capture_output=True, check=False).stdout
        else:
            patch += subprocess.run(["git", "diff", "--binary", "--no-ext-diff", "--", git_path], cwd=git_root, capture_output=True, check=False).stdout
    return patch


def _validate_validated_commit(record: dict[str, Any], *, allow_stale: bool = False) -> str:
    validation = record.get("edit_validation")
    if not validation or not isinstance(validation.get("result"), dict):
        raise _fail("EDIT_NOT_VALIDATED", "validated commit requires finish-edit evidence")
    result = validation["result"]
    expected_parent = result.get("expected_parent_head")
    validated_patch_sha = result.get("patch_sha")
    if not isinstance(expected_parent, str) or not isinstance(validated_patch_sha, str):
        raise _fail("VALIDATED_COMMIT_REJECTED", "validated commit evidence is incomplete")
    repo = Path(record["worktree_path"])
    head = _ledger_git(repo, "rev-parse", "HEAD")
    parents = _ledger_git(repo, "rev-list", "--parents", "-n", "1", head).split()
    if len(parents) != 2 or parents[1] != expected_parent:
        raise _fail("VALIDATED_COMMIT_REJECTED", "HEAD is not the expected single-parent validated commit")
    status = _ledger_git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise _fail("VALIDATED_COMMIT_REJECTED", "post-commit worktree is dirty")
    changed = result.get("changed_files")
    if not isinstance(changed, list) or any(not isinstance(item, dict) or not isinstance(item.get("path"), str) for item in changed):
        raise _fail("VALIDATED_COMMIT_REJECTED", "validated changed-file evidence is malformed")
    validated_paths = {item["path"] for item in changed}
    name_status = _ledger_git(repo, "diff", "--name-status", "--no-ext-diff", expected_parent, head).splitlines()
    if any(not line or line[0] not in {"A", "M", "D"} or len(line.split("\t")) != 2 for line in name_status):
        raise _fail("VALIDATED_COMMIT_REJECTED", "commit contains a rename, copy, or merge-style change")
    committed_paths_raw = {line.split("\t", 1)[1] for line in name_status}
    committed_paths_project = {_project_relative_path(repo, path) for path in committed_paths_raw}
    if validated_paths != committed_paths_project:
        raise _fail("VALIDATED_COMMIT_REJECTED", "commit paths differ from validated paths")
    diff_paths = committed_paths_project
    patch = subprocess.run(
        ["git", "diff", "--binary", "--no-ext-diff", expected_parent, head, "--", *sorted(diff_paths)],
        cwd=repo, capture_output=True, check=False,
    ).stdout
    if sha256_patch(patch) != validated_patch_sha:
        raise _fail("VALIDATED_COMMIT_REJECTED", "commit content differs from validated patch")
    _ledger_validate(record, expected_commit=head, allow_dirty=False, allow_stale=allow_stale)
    return head


def _validate_validated_worktree(record: dict[str, Any]) -> None:
    """Validate the exact pre-commit worktree represented by finish-stage evidence."""
    validation = record.get("edit_validation")
    if not validation or not isinstance(validation.get("result"), dict):
        raise _fail("VALIDATED_HEARTBEAT_REJECTED", "validated evidence is incomplete")
    result = validation["result"]
    expected_parent = result.get("expected_parent_head")
    if not isinstance(expected_parent, str):
        raise _fail("VALIDATED_HEARTBEAT_REJECTED", "validated parent HEAD is missing")
    repo = Path(record["worktree_path"])
    head = _ledger_git(repo, "rev-parse", "HEAD")
    if head != expected_parent:
        raise _fail("VALIDATED_HEARTBEAT_REJECTED", "validated parent HEAD changed")
    changed = _finish_changes(record, _finish_contract(record["contracts"][0]["path"]))
    expected = result.get("changed_files")
    if not isinstance(expected, list) or {item["path"] for item in changed} != {item.get("path") for item in expected}:
        raise _fail("VALIDATED_HEARTBEAT_REJECTED", "validated changed paths differ")
    patch_sha = sha256_patch(_finish_patch(repo, [item["path"] for item in changed]))
    if patch_sha != result.get("patch_sha"):
        raise _fail("VALIDATED_HEARTBEAT_REJECTED", "validated patch changed")


def campaign_ledger_finish_edit(campaign_id: str, contract_index: int, operation_id: str) -> dict[str, Any]:
    operation_id = _operation_id(operation_id); payload = {"contract_index": contract_index}
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id); retry = _retry_result(record, operation_id, "finish-edit", payload)
        if retry is not None: return retry
        _ledger_validate(record, allow_dirty=True)
        pending = record.get("pending_action"); admission = record.get("edit_admission")
        if not pending or pending.get("kind") != "IMPLEMENT" or contract_index != record["current_index"] or not admission or admission.get("contract_index") != contract_index:
            raise _fail("EDIT_NOT_ADMITTED", "edit validation requires matching admission")
        if record.get("edit_validation") and record["edit_validation"].get("contract_index") == contract_index:
            raise _fail("EDIT_ALREADY_VALIDATED", "contract edit already validated")
        repo = Path(record["worktree_path"]); contract = _finish_contract(record["contracts"][contract_index]["path"]); changed = _finish_changes(record, contract); paths = [item["path"] for item in changed]
        queued = record["contracts"][contract_index]
        projection = _gate_projection(queued, repo, record["suites"])
        projection_fd, projection_name = tempfile.mkstemp(prefix="householder-gate-", suffix=".json", dir=str(_ledger_file(campaign_id).parent))
        os.close(projection_fd)
        projection_file = Path(projection_name)
        projection_file.write_text(json.dumps(projection, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        try:
            gate = subprocess.run(["python3", str(repo / "scripts/ci/architecture_slice_gate.py"), "--contract", str(projection_file), "--contract-sha", _json_sha256(projection)], cwd=repo, capture_output=True, text=True, check=False, shell=False)
        finally:
            projection_file.unlink(missing_ok=True)
        try: gate_result = json.loads(gate.stdout)
        except json.JSONDecodeError as exc: raise _fail("GATE_FAILED", "architecture gate returned invalid evidence") from exc
        if gate.returncode or not gate_result.get("pass"): raise _fail("EDIT_VALIDATION_FAILED", "architecture gate failed")
        suite_results = []
        for suite in record["suites"]:
            run = subprocess.run(suite["argv"], cwd=record["worktree_path"], capture_output=True, text=True, check=False, shell=False)
            suite_results.append({"suite_id": suite["id"], "argv": suite["argv"], "cwd": record["worktree_path"], "exit_code": run.returncode, "passed": run.returncode == 0})
            if run.returncode: raise _fail("SUITE_FAILED", "persisted suite failed")
        check = subprocess.run(["git", "diff", "--check"], cwd=record["worktree_path"], capture_output=True, text=True, check=False, shell=False)
        if check.returncode: raise _fail("DIFF_CHECK_FAILED", "git diff --check failed")
        patch = _finish_patch(Path(record["worktree_path"]), paths); totals = {"production": gate_result.get("production_totals", {}), "test": gate_result.get("test_totals", {})}
        expected_parent_head = _ledger_git(repo, "rev-parse", "HEAD")
        output = {"contract_index": contract_index, "changed_files": gate_result.get("files", changed), "diff_totals": totals, "gate_result": gate_result, "suite_results": suite_results, "diff_check": {"passed": True}, "patch_sha": sha256_patch(patch), "gate_pass": True, "tests_pass": True, "commit_sha": expected_parent_head, "expected_parent_head": expected_parent_head, "suite_id": record["suites"][0]["id"], "admission_operation_id": admission["operation_id"]}
        record["edit_validation"] = {"contract_index": contract_index, "operation_id": operation_id, "result": output}; _record_operation(record, operation_id, "finish-edit", payload, output); _append_event(campaign_id, record, operation_id, "EDIT_VALIDATED", payload); return output
@contextmanager
def _ledger_lock(campaign_id: str):
    file = _ledger_file(campaign_id)
    file.parent.mkdir(parents=True, exist_ok=True)
    lock = file.with_name(".state.lock").open("a+", encoding="utf-8")
    try:
        import fcntl
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        import fcntl
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def _ledger_git(repo: Path, *args: str) -> str:
    if any(os.environ.get(name) for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE")):
        raise _fail("GIT_DIR_MISMATCH", "alternate Git directory is not allowed")
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False, shell=False)
    if result.returncode:
        raise _fail("GIT_PRECONDITION", f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _project_relative_path(repo: Path, path: str) -> str:
    """Normalize Git's repository-root status paths to project-root paths."""
    try:
        layout = discover_layout(_canonical_path(_ledger_git(repo, "rev-parse", "--show-toplevel")), markers=PROJECT_MARKERS)
        return canonicalize_git_path(path, layout)
    except CanonicalPathError as exc:
        raise _fail("PATH_OUTSIDE_ROOT", str(exc)) from exc


def _ledger_identity(repo: Path) -> dict[str, Any]:
    git_root = _canonical_path(_ledger_git(repo, "rev-parse", "--show-toplevel"))
    project = _discover_project_root(git_root)
    common_dir = _canonical_git_path(_ledger_git(project, "rev-parse", "--git-common-dir"), project)
    git_dir = _canonical_git_path(_ledger_git(project, "rev-parse", "--git-dir"), project)
    return {
        "head": _ledger_git(git_root, "rev-parse", "HEAD"),
        "dirty": bool(_ledger_git(git_root, "status", "--porcelain", "--untracked-files=all")),
        "gate": _ledger_git(project, "hash-object", str(project / "scripts/ci/architecture_slice_gate.py")),
        "worktree_path": str(project),
        "project_root_path": str(project),
        "git_root_path": str(git_root),
        "git_common_dir": str(common_dir),
        "git_dir": str(git_dir),
    }


def _contract_seam_id(payload: dict[str, Any]) -> str | None:
    seam = payload.get("seam")
    if seam is None:
        return None
    if type(seam) is not str or not seam or seam.strip() != seam:
        raise _fail("CONTRACT_MALFORMED", "seam must be a trimmed string")
    return seam


def _contract_task_id(payload: dict[str, Any]) -> str:
    task_id = payload.get("task_id")
    if type(task_id) is not str or not task_id or task_id.strip() != task_id:
        raise _fail("CONTRACT_MALFORMED", "task_id must be a trimmed string")
    return task_id


def _enforce_seam_boundaries(typed: dict[str, Any], seam_id: str | None) -> None:
    allowed = set(typed["allowed_files"])
    if allowed.intersection(typed["protected_files"]):
        raise _fail("PROTECTED_FILE", "allowed files overlap protected files")
    completed_files = {path for files in typed["completed_seam_files"].values() for path in files}
    if allowed.intersection(completed_files):
        raise _fail("COMPLETED_SEAM_OVERLAP", "allowed files overlap a completed seam")
    if seam_id is not None and seam_id in typed["completed_seams"]:
        raise _fail("COMPLETED_SEAM_OVERLAP", "contract seam is already completed")


def _reject_parent_scope_overlap(campaign_id: str, files: set[str]) -> None:
    if not LEDGER_ROOT.exists():
        return
    for state_path in LEDGER_ROOT.glob("*/state.json"):
        try:
            record = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise _fail("PARENT_SCOPE_CONFLICT", "active parent scope is unreadable") from exc
        if record.get("campaign_id") == campaign_id or record.get("mode") != "PARENT":
            continue
        if record.get("state") in {"COMMITTED", "FAILED"}:
            continue
        other = set(record.get("parent_files", []))
        if files.intersection(other):
            raise _fail("PARENT_SCOPE_CONFLICT", "authorized files overlap an active parent seam")


def _ledger_contract(path: str, expected: str, contract_root: Path | None = None, *, baseline_head: str | None = None, gate_sha: str | None = None, suite_ids: list[str] | None = None, typed_sha: str | None = None) -> dict[str, Any]:
    file = _canonical_path(path, "CONTRACT_NOT_INITIALIZED")
    if contract_root is not None and not _under(file, _canonical_path(contract_root), "SYMLINK_ESCAPE"):
        raise _fail("SYMLINK_ESCAPE", "contract path leaves approved root")
    try:
        payload = _read_json(file)
    except CampaignError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise _fail("CONTRACT_UNAVAILABLE", "contract unreadable") from exc
    if _json_sha256(payload) != expected:
        raise _fail("CONTRACT_MUTATED", "contract digest mismatch")
    typed = _strict_contract(payload, baseline_head=baseline_head, gate_sha=gate_sha, suite_ids=suite_ids)
    _enforce_seam_boundaries(typed, _contract_seam_id(payload))
    digest = _json_sha256(typed)
    if typed_sha is not None and digest != typed_sha:
        raise _fail("CONTRACT_MUTATED", "normalized contract digest mismatch")
    return {"path": str(file), "sha256": expected, "typed_contract": typed, "typed_contract_sha256": digest, "seam_id": _contract_seam_id(payload), "task_id": _contract_task_id(payload)}


def _gate_projection(item: dict[str, Any], repo: Path, suites: list[dict[str, Any]]) -> dict[str, Any]:
    typed = item["typed_contract"]
    git_root = _canonical_path(_ledger_git(repo, "rev-parse", "--show-toplevel"))
    project = _canonical_path(repo)
    layout = discover_layout(git_root, markers=PROJECT_MARKERS)
    allowed = list(typed["allowed_files"])
    new_production = []
    for project_path in allowed:
        baseline_path = f"{typed['baseline_head']}:{to_git_path(project_path, layout)}"
        result = subprocess.run(["git", "cat-file", "-e", baseline_path], cwd=repo, capture_output=True, text=True, check=False, shell=False)
        if result.returncode and project_path.startswith("scripts/") and not project_path.startswith("tests/"):
            new_production.append(project_path)
    return {
        "schema_version": 1,
        "task_id": item["task_id"],
        "baseline_ref": typed["baseline_head"],
        "seam": item["seam_id"],
        "authorized_files": allowed,
        "allowed_new_production_files": new_production,
        "production_changed_lines_max": typed["max_production_lines"],
        "test_changed_lines_max": typed["max_test_lines"],
        "forbidden_files": [],
        "forbidden_imports": [],
        "forbidden_symbols": [],
        "required_test_commands": [" ".join(shlex.quote(arg) for arg in suite["argv"]) for suite in suites],
        "gate_blob_sha": typed["gate_sha"],
    }


def _canonical_projection(value: dict[str, Any], repo: Path) -> dict[str, Any]:
    """Compare projection paths semantically, regardless of Git/project origin."""
    git_root = _canonical_path(_ledger_git(repo, "rev-parse", "--show-toplevel"))
    layout = discover_layout(git_root, markers=PROJECT_MARKERS)
    normalized = dict(value)
    for field in ("authorized_files", "allowed_new_production_files", "forbidden_files"):
        if field in normalized:
            try:
                normalized[field] = sorted(canonicalize_many(normalized[field], layout, field=field))
            except CanonicalPathError as exc:
                raise _fail("CONTRACT_MUTATED", "generated gate projection contains an invalid path") from exc
    if "authorized_files" in normalized and "baseline_ref" in normalized:
        normalized["allowed_new_production_files"] = sorted(
            path for path in normalized["authorized_files"]
            if path.startswith("scripts/")
            and not path.startswith("tests/")
            and _git(["cat-file", "-e", f"{normalized['baseline_ref']}:{to_git_path(path, layout)}"], cwd=repo).returncode != 0
        )
    return normalized


def _check_authorized(contract_path: Path, worktree: Path) -> None:
    try:
        payload = _read_json(contract_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise _fail("CONTRACT_NOT_INITIALIZED", "contract unreadable") from exc
    if isinstance(payload, dict) and isinstance(payload.get("typed_contract"), dict):
        raw_files = payload["typed_contract"].get("allowed_files", [])
    else:
        raw_files = payload.get("authorized_files", payload.get("allowed_files", [])) if isinstance(payload, dict) else []
    if not isinstance(raw_files, list): raise _fail("CONTRACT_NOT_INITIALIZED", "authorized files malformed")
    for raw in raw_files:
        if not isinstance(raw, str) or Path(raw).is_absolute() or ".." in Path(raw).parts: raise _fail("PATH_OUTSIDE_ROOT", "authorized file is not contained")
        resolved = _canonical_path(worktree / raw)
        if not _under(resolved, worktree, "SYMLINK_ESCAPE"): raise _fail("SYMLINK_ESCAPE", "authorized file leaves worktree")
    return raw_files


def _ledger_shape(record: dict[str, Any], campaign_id: str) -> dict[str, Any]:
    if isinstance(record, dict) and record.get("mode") == "PARENT":
        return _parent_shape(record, campaign_id)
    if isinstance(record, dict) and record.get("mode") == "DISCOVERY":
        raise _fail("READ_ONLY_VIOLATION", "discovery state cannot drive campaign edits")
    if not isinstance(record, dict) or record.get("campaign_id") != campaign_id:
        raise _fail("EVENT_LOG_CORRUPT", "replayed state malformed")
    if not isinstance(record.setdefault("operations", []), list):
        raise _fail("EVENT_LOG_CORRUPT", "replayed operations malformed")
    if any(field not in record for field in ("repo_path", "worktree_path", "project_root_path", "git_root_path", "git_common_dir", "git_dir", "contract_root", "suites", "last_checkpoint_at")):
        raise _fail("EVENT_LOG_CORRUPT", "replayed containment fields missing")
    if not isinstance(record["suites"], list) or not record["suites"] or any(not isinstance(s, dict) or s.get("id") not in SUITE_REGISTRY or s.get("argv") != SUITE_REGISTRY[s["id"]] for s in record["suites"]):
        raise _fail("SUITE_NOT_ALLOWED", "persisted suite is not allowed")
    if record.get("state") not in CAMPAIGN_STATES or not record.get("contracts"):
        raise _fail("EVENT_LOG_CORRUPT", "replayed state malformed")
    if not isinstance(record.get("current_index"), int) or not 0 <= record["current_index"] <= len(record["contracts"]):
        raise _fail("EVENT_LOG_CORRUPT", "replayed state malformed")
    pending = record.get("pending_action")
    if pending is not None:
        if not isinstance(pending, dict) or pending.get("contract_index") != record["current_index"]:
            raise _fail("EVENT_LOG_CORRUPT", "replayed pending action malformed")
        expected_kind = "IMPLEMENT" if record["state"] == "ACTIVE" else "VALIDATE"
        if record["state"] not in {"ACTIVE", "VALIDATING"} or pending.get("kind") != expected_kind:
            raise _fail("EVENT_LOG_CORRUPT", "replayed pending action malformed")
    if record["state"] == "READY" and record["current_index"] != 0 or record["state"] == "COMMITTED" and record["current_index"] != len(record["contracts"]):
        raise _fail("EVENT_LOG_CORRUPT", "replayed state malformed")
    if _json_sha256(record["contracts"]) != record.get("contract_queue_sha256"):
        raise _fail("EVENT_LOG_CORRUPT", "contract queue digest mismatch")
    try:
        datetime.fromisoformat(str(record["last_checkpoint_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise _fail("EVENT_LOG_CORRUPT", "checkpoint timestamp is invalid") from exc
    return record


def _parent_shape(record: dict[str, Any], campaign_id: str) -> dict[str, Any]:
    required = {
        "schema_version", "mode", "campaign_id", "repo_path", "worktree_path", "project_root_path",
        "git_root_path", "git_common_dir", "git_dir", "contract_root", "suites", "last_checkpoint_at",
        "contracts", "contract_queue_sha256", "gate_blob_sha", "starting_head", "current_head",
        "parent_seam", "parent_files", "current_stage_index", "active_stage", "completed_stages",
        "results", "operations", "state",
    }
    if not isinstance(record, dict) or set(record) < required or record.get("campaign_id") != campaign_id:
        raise _fail("EVENT_LOG_CORRUPT", "replayed parent state malformed")
    if record["schema_version"] != PARENT_SCHEMA_VERSION or record["mode"] != "PARENT":
        raise _fail("EVENT_LOG_CORRUPT", "replayed parent schema is invalid")
    allowed_states = {"ADMITTED", *PARENT_STAGES, "VALIDATED", "COMMITTED", "FAILED"}
    if record.get("state") not in allowed_states:
        raise _fail("EVENT_LOG_CORRUPT", "replayed parent state is invalid")
    stages = record["parent_seam"].get("stages") if isinstance(record.get("parent_seam"), dict) else None
    if not isinstance(stages, list) or not stages or record["parent_files"] != record["parent_seam"].get("authorized_files"):
        raise _fail("EVENT_LOG_CORRUPT", "replayed parent ownership is invalid")
    if not isinstance(record["current_stage_index"], int) or not -1 <= record["current_stage_index"] < len(stages):
        raise _fail("EVENT_LOG_CORRUPT", "replayed parent stage index is invalid")
    completed_limit = 0 if record["current_stage_index"] < 0 else record["current_stage_index"] + (1 if record["state"] in {"VALIDATED", "COMMITTED"} else 0)
    if not isinstance(record["completed_stages"], list) or record["completed_stages"] != [stage["id"] for stage in stages[:completed_limit]]:
        raise _fail("EVENT_LOG_CORRUPT", "replayed parent stage completion is invalid")
    if record["state"] == "ADMITTED" and record["current_stage_index"] != -1:
        raise _fail("EVENT_LOG_CORRUPT", "admitted parent has advanced stages")
    if record["state"] in PARENT_STAGES:
        expected = PARENT_STAGES.index(record["state"])
        if record["current_stage_index"] != expected or not isinstance(record.get("active_stage"), dict):
            raise _fail("EVENT_LOG_CORRUPT", "active parent stage is invalid")
    if record["state"] == "VALIDATED" and record["current_stage_index"] != len(stages) - 1:
        raise _fail("EVENT_LOG_CORRUPT", "validated parent has incomplete stages")
    if record["state"] == "COMMITTED" and not record.get("protected_files"):
        raise _fail("EVENT_LOG_CORRUPT", "committed parent has no protected files")
    if _json_sha256(record["contracts"]) != record.get("contract_queue_sha256"):
        raise _fail("EVENT_LOG_CORRUPT", "parent contract digest mismatch")
    return record


def _discovery_shape(record: dict[str, Any], discovery_id: str) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("mode") != "DISCOVERY" or record.get("discovery_id") != discovery_id:
        raise _fail("EVENT_LOG_CORRUPT", "replayed discovery state malformed")
    required = {
        "schema_version", "mode", "discovery_id", "repo_path", "worktree_path", "project_root_path", "git_root_path", "git_common_dir", "git_dir",
        "starting_head", "starting_dirty", "starting_worktree_snapshot", "gate_blob_sha", "start_time",
        "deadline_at", "last_checkpoint_at", "state", "findings_path", "findings_sha256", "operations",
    }
    if set(record) < required or record["schema_version"] != 1 or record["state"] not in {"DISCOVERY_ACTIVE", "DISCOVERY_FINISHED"}:
        raise _fail("EVENT_LOG_CORRUPT", "replayed discovery state malformed")
    if not isinstance(record["starting_worktree_snapshot"], dict) or not isinstance(record["operations"], list):
        raise _fail("EVENT_LOG_CORRUPT", "replayed discovery state malformed")
    for field in ("last_checkpoint_at", "deadline_at"):
        try:
            datetime.fromisoformat(str(record[field]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise _fail("EVENT_LOG_CORRUPT", "discovery timestamp is invalid") from exc
    return record


def _campaign_stale(record: dict[str, Any]) -> bool:
    checkpoint = datetime.fromisoformat(str(record["last_checkpoint_at"]).replace("Z", "+00:00"))
    return _now_utc() - checkpoint > timedelta(minutes=12)


def _event_state(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if k not in {"checkpoint_sequence", "checkpoint_hash"}}
def _read_event_tail(campaign_id: str, shape: Any = _ledger_shape) -> tuple[dict[str, Any], int, str]:
    path = _events_file(campaign_id)
    try: raw = path.read_bytes(); lines = raw.decode("utf-8").splitlines(); (_ for _ in ()).throw(_fail("EVENT_LOG_CORRUPT", "event log is truncated")) if not raw.endswith(b"\n") else None
    except (OSError, UnicodeDecodeError) as exc:
        code = "LEDGER_UNAVAILABLE" if not _ledger_file(campaign_id).exists() else "EVENT_LOG_CORRUPT"; raise _fail(code, "event log missing or unreadable") from exc
    if not lines: raise _fail("EVENT_LOG_CORRUPT", "event log is empty")
    previous = ""; state = None
    for expected, line in enumerate(lines, 1):
        try: event = json.loads(line)
        except json.JSONDecodeError as exc: raise _fail("EVENT_LOG_CORRUPT", "event log is malformed") from exc
        if not isinstance(event, dict) or event.get("sequence") != expected or event.get("previous_event_hash") != previous:
            raise _fail("EVENT_LOG_CORRUPT", "event sequence or link is invalid")
        digest = event.get("event_hash"); unsigned = {k: v for k, v in event.items() if k != "event_hash"}
        if not isinstance(digest, str) or _json_sha256(unsigned) != digest or not isinstance(event.get("state"), dict):
            raise _fail("EVENT_LOG_CORRUPT", "event hash or state is invalid")
        state, previous = event["state"], digest
    return shape(state, campaign_id), len(lines), previous
def _write_checkpoint(campaign_id: str, record: dict[str, Any], sequence: int, event_hash: str) -> None:
    payload = {**_event_state(record), "checkpoint_sequence": sequence, "checkpoint_hash": event_hash}; _write_atomic_json(_ledger_file(campaign_id), payload)
def _append_event(campaign_id: str, record: dict[str, Any], operation_id: str, command: str, payload: dict[str, Any], shape: Any = _ledger_shape) -> None:
    _, sequence, previous = _read_event_tail(campaign_id, shape) if _events_file(campaign_id).exists() else ({}, 0, "")
    unsigned = {"sequence": sequence + 1, "timestamp": _utcnow(), "operation_id": operation_id, "command": command, "payload_sha256": _operation_payload(command, payload), "previous_event_hash": previous, "state": _event_state(record)}
    event = {**unsigned, "event_hash": _json_sha256(unsigned)}; path = _events_file(campaign_id); path.parent.mkdir(parents=True, exist_ok=True); existed = path.exists()
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"); handle.flush(); os.fsync(handle.fileno())
    except OSError as exc:
        path.unlink() if not existed and path.exists() else None; raise _fail("EVENT_APPEND_FAILED", "event append failed") from exc
    _write_checkpoint(campaign_id, record, sequence + 1, event["event_hash"])
def _ledger_load(campaign_id: str) -> dict[str, Any]:
    record, sequence, event_hash = _read_event_tail(campaign_id)
    try:
        cached = json.loads(_ledger_file(campaign_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        _write_checkpoint(campaign_id, record, sequence, event_hash); return record
    if not isinstance(cached, dict) or cached.get("checkpoint_sequence") != sequence or cached.get("checkpoint_hash") != event_hash: raise _fail("EVENT_LOG_CORRUPT", "event log does not match checkpoint")
    if _event_state(cached) != record: raise _fail("CHECKPOINT_MISMATCH", "state checkpoint does not match event log")
    return record


def _parent_record(campaign_id: str) -> dict[str, Any]:
    record = _ledger_load(campaign_id)
    if record.get("mode") != "PARENT":
        raise _fail("PARENT_CONTRACT_MALFORMED", "campaign is not a parent seam")
    return record


def _parent_retry(record: dict[str, Any], operation_id: str, command: str, payload: dict[str, Any]) -> Any | None:
    try:
        return _retry_result(record, operation_id, command, payload)
    except CampaignError as exc:
        if exc.code == "OPERATION_CONFLICT":
            raise _fail("STAGE_RETRY_MISMATCH", "parent stage retry payload differs") from exc
        raise


def is_parent_contract(contract_path: str | Path) -> bool:
    payload = _read_json(Path(contract_path))
    typed = payload.get("typed_contract", payload) if isinstance(payload, dict) else {}
    return isinstance(typed, dict) and isinstance(typed.get("parent_seam"), dict)


def campaign_parent_status(campaign_id: str) -> dict[str, Any]:
    with _ledger_lock(campaign_id):
        record = _parent_record(campaign_id)
        _parent_validate(record, allow_dirty=record["state"] in PARENT_STAGES or record["state"] == "VALIDATED")
        return _result_view(record)


def _parent_validate(record: dict[str, Any], *, allow_dirty: bool = False, expected_commit: str | None = None, allow_stale: bool = False) -> None:
    _ledger_validate(record, expected_commit=expected_commit, allow_dirty=allow_dirty, allow_stale=allow_stale)
    parent = record["parent_seam"]
    if record["parent_files"] != parent["authorized_files"]:
        raise _fail("EVENT_LOG_CORRUPT", "parent ownership envelope changed")
    if record["state"] == "COMMITTED" and set(record.get("protected_files", [])) != set(record["parent_files"]):
        raise _fail("EVENT_LOG_CORRUPT", "committed parent protection is incomplete")


def _parent_stage(record: dict[str, Any]) -> dict[str, Any]:
    index = record.get("current_stage_index", -1)
    stages = record["parent_seam"]["stages"]
    if index < 0 or index >= len(stages):
        raise _fail("STAGE_NOT_FOUND", "no active parent stage")
    stage = stages[index]
    if record.get("active_stage", {}).get("id") != stage["id"]:
        raise _fail("STAGE_ORDER_VIOLATION", "active stage does not match ordered contract")
    return stage


def _parent_changed_files(record: dict[str, Any], stage: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    repo = Path(record["worktree_path"])
    status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, capture_output=True, text=True, check=False, shell=False)
    if status.returncode:
        raise _fail("GIT_PRECONDITION", "unable to inspect parent stage changes")
    completed = set(record.get("completed_files", []))
    permitted = completed | set(stage["allowed_files"])
    changed: list[dict[str, Any]] = []
    totals = {"production": 0, "test": 0}
    for line in status.stdout.splitlines():
        if not line:
            continue
        code, path = line[:2], _project_relative_path(repo, line[3:].strip().strip('"'))
        if "R" in code or "C" in code or "->" in path:
            raise _fail("RENAME_REJECTED", "renames and copies are not allowed")
        if path not in permitted:
            raise _fail("STAGE_FILE_OUTSIDE_PARENT", "changed file is outside the current stage ownership")
        target = repo / path
        if target.is_symlink():
            raise _fail("SYMLINK_ESCAPE", "changed symlink is not allowed")
        if code == "??":
            additions, deletions = target.read_bytes().count(b"\n"), 0
        else:
            stats = _ledger_git(repo, "diff", "--numstat", "--no-ext-diff", "--", path).split("\t")
            if len(stats) < 2 or stats[0] == "-" or stats[1] == "-":
                raise _fail("BINARY_CHANGE", "binary files are not allowed")
            additions, deletions = int(stats[0]), int(stats[1])
        bucket = "test" if path.startswith("tests/") else "production"
        totals[bucket] += additions + deletions
        changed.append({"path": path, "status": code})
    if totals["production"] > stage["max_production_lines"] or totals["test"] > stage["max_test_lines"]:
        raise _fail("CEILING_EXCEEDED", "parent stage exceeds its declared ceiling")
    return changed, totals


def _parent_projection(record: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    item = record["contracts"][0]
    projection = dict(item["gate_projection"])
    projection["seam"] = record["parent_seam"]["id"]
    projection["authorized_files"] = list(record["parent_files"])
    projection["required_test_commands"] = [
        " ".join(shlex.quote(arg) for arg in suite["argv"]) for suite in record["suites"]
    ]
    projection["production_changed_lines_max"] = max(stage["max_production_lines"] for stage in record["parent_seam"]["stages"])
    projection["test_changed_lines_max"] = max(stage["max_test_lines"] for stage in record["parent_seam"]["stages"])
    fd, name = tempfile.mkstemp(prefix="householder-parent-gate-", suffix=".json", dir=str(_ledger_file(record["campaign_id"]).parent))
    os.close(fd)
    path = Path(name)
    path.write_text(json.dumps(projection, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return path, projection


def campaign_parent_next(campaign_id: str, operation_id: str) -> dict[str, Any]:
    operation_id = _operation_id(operation_id)
    with _ledger_lock(campaign_id):
        record = _parent_record(campaign_id)
        payload: dict[str, Any] = {}
        retry = _parent_retry(record, operation_id, "parent-next", payload)
        if retry is not None:
            return retry
        _parent_validate(record, allow_dirty=False)
        if record["state"] != "ADMITTED":
            raise _fail("STAGE_ORDER_VIOLATION", "parent stage must begin at ADMITTED")
        stage = record["parent_seam"]["stages"][0]
        record["state"] = PARENT_STAGES[0]
        record["current_stage_index"] = 0
        record["active_stage"] = stage
        output = {"state": record["state"], "stage": stage}
        _record_operation(record, operation_id, "parent-next", payload, output)
        _append_event(campaign_id, record, operation_id, "PARENT_STAGE_STARTED", payload)
        return output


def campaign_parent_finish_stage(campaign_id: str, operation_id: str) -> dict[str, Any]:
    operation_id = _operation_id(operation_id)
    with _ledger_lock(campaign_id):
        record = _parent_record(campaign_id)
        payload: dict[str, Any] = {}
        retry = _parent_retry(record, operation_id, "parent-finish-stage", payload)
        if retry is not None:
            return retry
        _parent_validate(record, allow_dirty=True)
        if record["state"] not in PARENT_STAGES:
            raise _fail("STAGE_ORDER_VIOLATION", "no active stage can be finished")
        stage = _parent_stage(record)
        changed, totals = _parent_changed_files(record, stage)
        gate_path, projection = _parent_projection(record)
        try:
            gate = subprocess.run([sys.executable, str(Path(record["project_root_path"]) / "scripts/ci/architecture_slice_gate.py"), "--contract", str(gate_path), "--contract-sha", _json_sha256(projection)], cwd=record["project_root_path"], capture_output=True, text=True, check=False, shell=False)
        finally:
            gate_path.unlink(missing_ok=True)
        try:
            gate_result = json.loads(gate.stdout)
        except json.JSONDecodeError as exc:
            raise _fail("STAGE_EVIDENCE_INCOMPLETE", "stage gate returned invalid evidence") from exc
        if gate.returncode or not gate_result.get("pass"):
            raise _fail("STAGE_EVIDENCE_INCOMPLETE", "stage gate evidence failed")
        suite_results = []
        for suite_id in stage["suite_ids"]:
            suite = _suite_for(record, suite_id)
            run = subprocess.run(suite["argv"], cwd=record["project_root_path"], capture_output=True, text=True, check=False, shell=False)
            entry = {"suite_id": suite_id, "argv": suite["argv"], "exit_code": run.returncode, "passed": run.returncode == 0}
            suite_results.append(entry)
            if run.returncode:
                raise _fail("STAGE_EVIDENCE_INCOMPLETE", "stage suite evidence failed")
        diff_check = subprocess.run(["git", "diff", "--check"], cwd=record["project_root_path"], capture_output=True, text=True, check=False, shell=False)
        if diff_check.returncode:
            raise _fail("STAGE_EVIDENCE_INCOMPLETE", "stage diff evidence failed")
        evidence = {"gate_pass": True, "tests_pass": True, "diff_check_pass": True, "scope_pass": True, "ceiling_pass": True}
        if not set(stage["required_evidence"]).issubset(evidence):
            raise _fail("STAGE_EVIDENCE_INCOMPLETE", "required stage evidence is unavailable")
        record["completed_files"] = sorted(set(record.get("completed_files", [])) | {item["path"] for item in changed})
        record["completed_stages"] = record["completed_stages"] + [stage["id"]]
        record["results"].append({"stage": stage["id"], "changed_files": changed, "diff_totals": totals, "evidence": evidence, "suite_results": suite_results})
        if record["current_stage_index"] == len(record["parent_seam"]["stages"]) - 1:
            record["state"] = "VALIDATED"
            record["active_stage"] = None
            record["edit_validation"] = {"result": {"changed_files": changed, "expected_parent_head": record["starting_head"], "patch_sha": hashlib.sha256(_finish_patch(Path(record["project_root_path"]), record["completed_files"])).hexdigest()}}
        else:
            record["current_stage_index"] += 1
            record["state"] = PARENT_STAGES[record["current_stage_index"]]
            record["active_stage"] = record["parent_seam"]["stages"][record["current_stage_index"]]
        output = {"state": record["state"], "completed_stage": stage["id"], "evidence": evidence, "suite_results": suite_results}
        _record_operation(record, operation_id, "parent-finish-stage", payload, output)
        _append_event(campaign_id, record, operation_id, "PARENT_STAGE_FINISHED", payload)
        return output


def campaign_parent_commit(campaign_id: str, operation_id: str) -> dict[str, Any]:
    operation_id = _operation_id(operation_id)
    with _ledger_lock(campaign_id):
        record = _parent_record(campaign_id)
        payload: dict[str, Any] = {}
        retry = _parent_retry(record, operation_id, "parent-commit", payload)
        if retry is not None:
            return retry
        if record["state"] != "VALIDATED":
            raise _fail("STAGE_ORDER_VIOLATION", "parent commit requires VALIDATED state")
        current_head = _ledger_git(Path(record["project_root_path"]), "rev-parse", "HEAD")
        _parent_validate(record, allow_dirty=False, expected_commit=current_head)
        if current_head == record["starting_head"]:
            raise _fail("VALIDATED_COMMIT_REJECTED", "parent commit is not present")
        committed_head = _validate_validated_commit(record)
        record["protected_files"] = list(record["parent_files"])
        record["state"] = "COMMITTED"
        record["current_head"] = committed_head
        output = {"state": record["state"], "protected_files": record["protected_files"], "current_head": record["current_head"]}
        _record_operation(record, operation_id, "parent-commit", payload, output)
        _append_event(campaign_id, record, operation_id, "PARENT_COMMITTED", payload)
        return output


def campaign_parent_heartbeat(campaign_id: str, operation_id: str) -> dict[str, Any]:
    """Refresh a stale validated parent without reopening or changing its seam."""
    operation_id = _operation_id(operation_id)
    with _ledger_lock(campaign_id):
        record = _parent_record(campaign_id)
        payload: dict[str, Any] = {}
        retry = _parent_retry(record, operation_id, "parent-heartbeat", payload)
        if retry is not None:
            return retry
        if record["state"] != "VALIDATED":
            raise _fail("STAGE_ORDER_VIOLATION", "heartbeat requires VALIDATED state")
        repo = Path(record["worktree_path"])
        head = _ledger_git(repo, "rev-parse", "HEAD")
        expected_parent = record["edit_validation"]["result"].get("expected_parent_head")
        _parent_validate(record, allow_dirty=True, expected_commit=head, allow_stale=True)
        if head == expected_parent:
            _validate_validated_worktree(record)
        else:
            _validate_validated_commit(record, allow_stale=True)
        timestamp = _utcnow()
        record["last_checkpoint_at"] = timestamp
        output = {"state": record["state"], "heartbeat_at": timestamp}
        _record_operation(record, operation_id, "parent-heartbeat", payload, output)
        _append_event(campaign_id, record, operation_id, "PARENT_HEARTBEAT", payload)
        return output


def _discovery_load(discovery_id: str) -> dict[str, Any]:
    try:
        record, sequence, event_hash = _read_event_tail(discovery_id, _discovery_shape)
    except CampaignError as exc:
        if exc.code == "LEDGER_UNAVAILABLE":
            raise _fail("DISCOVERY_NOT_STARTED", "discovery ledger is not initialized") from exc
        raise
    try:
        cached = json.loads(_ledger_file(discovery_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        _write_checkpoint(discovery_id, record, sequence, event_hash)
        return record
    if not isinstance(cached, dict) or cached.get("checkpoint_sequence") != sequence or cached.get("checkpoint_hash") != event_hash:
        raise _fail("CHECKPOINT_MISMATCH", "discovery checkpoint does not match event log")
    if _event_state(cached) != record:
        raise _fail("CHECKPOINT_MISMATCH", "discovery checkpoint does not match event log")
    return record


def _ledger_validate(record: dict[str, Any], expected_commit: str | None = None, allow_dirty: bool = False, allow_stale: bool = False) -> tuple[str, str]:
    worktree = _canonical_path(record["worktree_path"])
    repo = _canonical_path(record["repo_path"])
    if repo != worktree:
        raise _fail("WORKTREE_MISMATCH", "repo and project identity differ")
    identity = _ledger_identity(worktree)
    if identity["worktree_path"] != record["worktree_path"] or identity["project_root_path"] != record["project_root_path"]:
        raise _fail("WORKTREE_MISMATCH", "worktree identity differs")
    if identity["git_root_path"] != record["git_root_path"]:
        raise _fail("WORKTREE_MISMATCH", "Git root identity differs")
    if identity["git_common_dir"] != record["git_common_dir"] or identity["git_dir"] != record["git_dir"]:
        raise _fail("GIT_DIR_MISMATCH", "Git directory identity differs")
    if identity["dirty"] and not allow_dirty:
        raise _fail("DIRTY_WORKTREE", "worktree dirty")
    if identity["gate"] != record["gate_blob_sha"]:
        raise _fail("GATE_MUTATED", "gate blob mismatch")
    contract_root = _canonical_path(record["contract_root"])
    for item in record["contracts"]:
        current = _ledger_contract(item["path"], item["sha256"], contract_root, baseline_head=record["starting_head"], gate_sha=record["gate_blob_sha"], suite_ids=[suite["id"] for suite in record["suites"]], typed_sha=item.get("typed_contract_sha256"))
        if current["typed_contract"] != item.get("typed_contract"):
            raise _fail("CONTRACT_MUTATED", "normalized contract changed")
        projection = _gate_projection(current, worktree, record["suites"])
        stored_projection = item.get("gate_projection")
        if not isinstance(stored_projection, dict) or _canonical_projection(projection, worktree) != _canonical_projection(stored_projection, worktree):
            raise _fail("CONTRACT_MUTATED", "generated gate projection changed")
        _check_authorized(Path(item["path"]), worktree)
    if identity["head"] != record["current_head"] and identity["head"] != expected_commit:
        raise _fail("STALE_HEAD", "stale HEAD")
    if not allow_stale and _campaign_stale(record):
        raise _fail("CAMPAIGN_STALE", "checkpoint is older than 12 minutes")
    return identity["head"], identity["gate"]


def _worktree_snapshot(repo: Path) -> dict[str, dict[str, Any]]:
    raw = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"],
        cwd=repo, capture_output=True, check=False, shell=False,
    )
    if raw.returncode:
        raise _fail("GIT_PRECONDITION", "unable to snapshot worktree")
    snapshot: dict[str, dict[str, Any]] = {}
    for encoded in raw.stdout.split(b"\0"):
        if not encoded:
            continue
        relative = encoded.decode("utf-8")
        path = repo / relative
        try:
            stat = path.lstat()
            if path.is_symlink():
                value = {"kind": "symlink", "sha256": _json_sha256(os.readlink(path))}
            elif path.is_file():
                value = {"kind": "file", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": stat.st_mode & 0o7777}
            else:
                value = {"kind": "other", "mode": stat.st_mode & 0o7777}
        except OSError as exc:
            raise _fail("READ_ONLY_VIOLATION", "unable to snapshot worktree") from exc
        snapshot[relative] = value
    return snapshot


def _discovery_validate(record: dict[str, Any]) -> None:
    worktree = _canonical_path(record["worktree_path"])
    repo = _canonical_path(record["repo_path"])
    if worktree != repo:
        raise _fail("WORKTREE_MISMATCH", "discovery repo and worktree differ")
    identity = _ledger_identity(worktree)
    if identity["worktree_path"] != record["worktree_path"]:
        raise _fail("WORKTREE_MISMATCH", "discovery worktree identity differs")
    if identity["project_root_path"] != record["project_root_path"] or identity["git_root_path"] != record["git_root_path"]:
        raise _fail("WORKTREE_MISMATCH", "discovery project identity differs")
    if identity["git_common_dir"] != record["git_common_dir"] or identity["git_dir"] != record["git_dir"]:
        raise _fail("GIT_DIR_MISMATCH", "discovery Git identity differs")
    if identity["head"] != record["starting_head"]:
        raise _fail("DISCOVERY_HEAD_CHANGED", "discovery HEAD changed")
    if identity["gate"] != record["gate_blob_sha"]:
        raise _fail("DISCOVERY_WORKTREE_CHANGED", "discovery gate changed")
    if _worktree_snapshot(worktree) != record["starting_worktree_snapshot"]:
        raise _fail("DISCOVERY_WORKTREE_CHANGED", "discovery worktree changed")
    checkpoint = datetime.fromisoformat(str(record["last_checkpoint_at"]).replace("Z", "+00:00"))
    deadline = datetime.fromisoformat(str(record["deadline_at"]).replace("Z", "+00:00"))
    if _now_utc() - checkpoint > timedelta(minutes=12) or _now_utc() > deadline:
        raise _fail("DISCOVERY_STALE", "discovery heartbeat or deadline expired")


def _discovery_result(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "discovery_id": record["discovery_id"],
        "state": record["state"],
        "worktree_path": record["worktree_path"],
        "project_root_path": record["project_root_path"],
        "git_root_path": record["git_root_path"],
        "git_common_dir": record["git_common_dir"],
        "starting_head": record["starting_head"],
        "starting_dirty": record["starting_dirty"],
        "deadline_at": record["deadline_at"],
        "last_checkpoint_at": record["last_checkpoint_at"],
        "findings_path": record.get("findings_path"),
        "findings_sha256": record.get("findings_sha256"),
    }


def campaign_discovery_start(discovery_id: str, operation_id: str) -> dict[str, Any]:
    discovery_id = _validate_task_id(discovery_id)
    operation_id = _operation_id(operation_id)
    payload: dict[str, Any] = {}
    with _ledger_lock(discovery_id):
        if _ledger_file(discovery_id).exists() or _events_file(discovery_id).exists():
            record = _discovery_load(discovery_id)
            retry = _retry_result(record, operation_id, "start-discovery", payload)
            if retry is not None:
                return retry
            raise _fail("DISCOVERY_ALREADY_STARTED", "discovery already exists")
        root = project_root()
        identity = _ledger_identity(root)
        now = _now_utc()
        record = {
            "schema_version": 1, "mode": "DISCOVERY", "discovery_id": discovery_id,
            "repo_path": identity["worktree_path"], "worktree_path": identity["worktree_path"],
            "project_root_path": identity["project_root_path"], "git_root_path": identity["git_root_path"],
            "git_common_dir": identity["git_common_dir"], "git_dir": identity["git_dir"],
            "starting_head": identity["head"], "starting_dirty": identity["dirty"],
            "starting_worktree_snapshot": _worktree_snapshot(root), "gate_blob_sha": identity["gate"],
            "start_time": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "deadline_at": (now + DISCOVERY_DEADLINE).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "last_checkpoint_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "state": "DISCOVERY_ACTIVE", "findings_path": None, "findings_sha256": None, "operations": [],
        }
        output = _discovery_result(record)
        _record_operation(record, operation_id, "start-discovery", payload, output)
        _append_event(discovery_id, record, operation_id, "DISCOVERY_STARTED", payload, _discovery_shape)
        return output


def _discovery_submit(discovery_id: str, operation_id: str, command: str, findings_file: str, finish: bool) -> dict[str, Any]:
    operation_id = _operation_id(operation_id)
    with _ledger_lock(discovery_id):
        record = _discovery_load(discovery_id)
        if record["state"] == "DISCOVERY_FINISHED":
            payload = {"findings_sha256": record["findings_sha256"]}
            retry = _retry_result(record, operation_id, command, payload)
            if retry is not None:
                return retry
            raise _fail("DISCOVERY_ALREADY_STARTED", "discovery is already finished")
        if record["state"] != "DISCOVERY_ACTIVE":
            raise _fail("DISCOVERY_NOT_STARTED", "discovery is not active")
        normalized, findings_sha = _discovery_findings_file(findings_file, record)
        payload = {"findings_sha256": findings_sha}
        retry = _retry_result(record, operation_id, command, payload)
        if retry is not None:
            return retry
        _discovery_validate(record)
        target = _discovery_findings_path(discovery_id)
        previous = target.read_bytes() if target.exists() else None
        _store_discovery_findings(discovery_id, normalized)
        record["findings_path"] = str(target)
        record["findings_sha256"] = findings_sha
        record["last_checkpoint_at"] = _utcnow()
        if finish:
            record["state"] = "DISCOVERY_FINISHED"
        output = {**_discovery_result(record), "findings_count": len(normalized["findings"])}
        _record_operation(record, operation_id, command, payload, output)
        try:
            _append_event(discovery_id, record, operation_id, "DISCOVERY_FINISHED" if finish else "DISCOVERY_CHECKPOINT", payload, _discovery_shape)
        except Exception:
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(previous)
            raise
        return output


def campaign_discovery_checkpoint(discovery_id: str, operation_id: str, findings_file: str) -> dict[str, Any]:
    return _discovery_submit(discovery_id, operation_id, "discovery-checkpoint", findings_file, False)


def campaign_discovery_finish(discovery_id: str, operation_id: str, findings_file: str) -> dict[str, Any]:
    return _discovery_submit(discovery_id, operation_id, "finish-discovery", findings_file, True)


def campaign_ledger_init(campaign_id: str, operation_id: str, repo: str | Path, gate_blob_sha: str, contracts: list[dict[str, str]], suite_ids: list[str] | None = None) -> dict[str, Any]:
    campaign_id = _validate_task_id(campaign_id)
    operation_id = _operation_id(operation_id)
    repo = _canonical_path(repo)
    if not contracts:
        raise _fail("INVALID_CONTRACT_QUEUE", "contract queue must not be empty")
    suites = _suite_ids(suite_ids)
    raw_contracts = [_canonical_path(item["path"], "PATH_OUTSIDE_ROOT") for item in contracts]
    try:
        contract_root = _canonical_path(os.path.commonpath([str(Path(item["path"]).absolute().parent) for item in contracts]))
    except ValueError:
        raise _fail("PATH_OUTSIDE_ROOT", "contract paths have no common root")
    requested_queue = [{"path": str(path), "sha256": item["sha256"]} for path, item in zip(raw_contracts, contracts)]
    payload = {"repo": str(repo), "gate_blob_sha": gate_blob_sha, "contracts": requested_queue, "suite_ids": suites}
    with _ledger_lock(campaign_id):
        file = _ledger_file(campaign_id)
        if file.exists() or _events_file(campaign_id).exists():
            record = _ledger_load(campaign_id)
            retry = _retry_result(record, operation_id, "init", payload)
            if retry is not None:
                return retry
            raise _fail("INIT_CONFLICT", "campaign already initialized")
        identity = _ledger_identity(repo)
        if str(repo) != identity["project_root_path"]:
            raise _fail("PROJECT_ROOT_MISMATCH", "repo is not the canonical Householder project root")
        if identity["dirty"]:
            raise _fail("DIRTY_WORKTREE", "worktree dirty")
        if identity["gate"] != gate_blob_sha:
            raise _fail("GATE_MUTATED", "gate blob mismatch")
        suite_records = [{"id": suite, "argv": list(SUITE_REGISTRY[suite])} for suite in suites]
        queue = []
        for path, item in zip(raw_contracts, contracts):
            queued = _ledger_contract(str(path), item["sha256"], contract_root, baseline_head=identity["head"], gate_sha=gate_blob_sha, suite_ids=suites)
            projection = _gate_projection(queued, Path(identity["worktree_path"]), suite_records)
            queued["gate_projection"] = projection
            queued["gate_projection_sha256"] = _json_sha256(projection)
            queue.append(queued)
            _check_authorized(path, Path(identity["worktree_path"]))
        parent = queue[0]["typed_contract"].get("parent_seam") if len(queue) == 1 else None
        if parent is not None:
            if len(queue) != 1:
                raise _fail("PARENT_CONTRACT_MALFORMED", "parent campaign requires one parent contract")
            _reject_parent_scope_overlap(campaign_id, set(parent["authorized_files"]))
            now = _utcnow()
            record = {
                "schema_version": PARENT_SCHEMA_VERSION, "mode": "PARENT", "campaign_id": campaign_id,
                "repo_path": str(repo), "worktree_path": identity["worktree_path"],
                "project_root_path": identity["project_root_path"], "git_root_path": identity["git_root_path"],
                "git_common_dir": identity["git_common_dir"], "git_dir": identity["git_dir"],
                "contract_root": str(contract_root), "starting_head": identity["head"],
                "current_head": identity["head"], "gate_blob_sha": gate_blob_sha, "contracts": queue,
                "contract_queue_sha256": _json_sha256(queue), "start_time": now, "last_checkpoint_at": now,
                "state": "ADMITTED", "current_index": 0, "pending_action": None,
                "edit_admission": None, "edit_validation": None, "parent_seam": parent,
                "parent_files": list(parent["authorized_files"]), "active_stage": None,
                "current_stage_index": -1, "completed_stages": [], "completed_files": [],
                "protected_files": [], "results": [], "stop_reason": None, "operations": [],
                "suites": suite_records,
            }
            result = _result_view(record)
            _record_operation(record, operation_id, "init", payload, result)
            _append_event(campaign_id, record, operation_id, "PARENT_ADMITTED", payload)
            return result
        record = {
            "schema_version": 1, "campaign_id": campaign_id, "repo_path": str(repo),
            "worktree_path": identity["worktree_path"], "project_root_path": identity["project_root_path"], "git_root_path": identity["git_root_path"],
            "git_common_dir": identity["git_common_dir"], "git_dir": identity["git_dir"],
            "contract_root": str(contract_root), "starting_head": identity["head"], "current_head": identity["head"], "gate_blob_sha": gate_blob_sha,
            "contracts": queue, "contract_queue_sha256": _json_sha256(queue),
            "start_time": _utcnow(), "last_checkpoint_at": _utcnow(), "state": "READY", "current_index": 0,
            "pending_action": None, "edit_admission": None, "edit_validation": None, "results": [], "stop_reason": None, "operations": [],
            "suites": suite_records,
        }
        result = _result_view(record)
        _record_operation(record, operation_id, "init", payload, result)
        _append_event(campaign_id, record, operation_id, "init", payload)
        return result


def campaign_ledger_checkpoint(campaign_id: str, operation_id: str) -> dict[str, Any]:
    operation_id = _operation_id(operation_id)
    payload: dict[str, Any] = {}
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        retry = _retry_result(record, operation_id, "checkpoint", payload)
        if retry is not None:
            return retry
        admitted_edit = bool(record.get("edit_admission") and record.get("pending_action", {}).get("kind") == "IMPLEMENT")
        _ledger_validate(record, allow_dirty=admitted_edit, allow_stale=True)
        if admitted_edit:
            _validate_admitted_edit_checkpoint(record)
        timestamp = _utcnow()
        record["last_checkpoint_at"] = timestamp
        output = {"campaign_id": campaign_id, "checkpoint_at": timestamp, "state": record["state"]}
        _record_operation(record, operation_id, "checkpoint", payload, output)
        _append_event(campaign_id, record, operation_id, "CHECKPOINT", payload)
        return output


def campaign_ledger_status(campaign_id: str) -> dict[str, Any]:
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        _ledger_validate(record, allow_dirty=bool(record.get("edit_validation")))
        return record


def campaign_ledger_next(campaign_id: str) -> dict[str, Any]:
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        _ledger_validate(record, allow_dirty=bool(record.get("edit_validation")))
        if record["state"] in CAMPAIGN_TERMINAL:
            return {"action": "STOP", "state": record["state"]}
        if record["pending_action"] is not None:
            raise _fail("ILLEGAL_TRANSITION", "repeated next transition")
        item = record["contracts"][record["current_index"]]
        kind = "IMPLEMENT" if record["state"] == "READY" else "VALIDATE"
        record["state"] = "ACTIVE" if kind == "IMPLEMENT" else "VALIDATING"
        record["pending_action"] = {"kind": kind, "contract_index": record["current_index"], "contract": item}
        _append_event(campaign_id, record, f"next-{record['current_index']}-{kind}", "next", {"contract_index": record["current_index"], "kind": kind})
        return record["pending_action"]


def campaign_ledger_start_edit(campaign_id: str, contract_index: int, operation_id: str) -> dict[str, Any]:
    operation_id = _operation_id(operation_id); payload = {"contract_index": contract_index}
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id); retry = _retry_result(record, operation_id, "start-edit", payload)
        if retry is not None: return retry
        _ledger_validate(record)
        pending = record.get("pending_action")
        if record["state"] != "ACTIVE" or not pending or pending.get("kind") != "IMPLEMENT" or contract_index != record["current_index"]:
            raise _fail("ILLEGAL_TRANSITION", "edit admission is not pending")
        admission = record.get("edit_admission")
        if admission and admission.get("contract_index") == contract_index:
            raise _fail("EDIT_ALREADY_STARTED", "contract edit already admitted")
        item = record["contracts"][contract_index]; authorized = _check_authorized(Path(item["path"]), Path(record["worktree_path"]))
        output = {"worktree_path": record["worktree_path"], "contract_index": contract_index, "contract_digest": item["sha256"], "authorized_files": authorized, "suite_ids": [suite["id"] for suite in record["suites"]], "admission_operation_id": operation_id}
        record["edit_admission"] = {"contract_index": contract_index, "operation_id": operation_id}
        _record_operation(record, operation_id, "start-edit", payload, output)
        _append_event(campaign_id, record, operation_id, "EDIT_STARTED", payload)
        return output


def campaign_ledger_record_result(campaign_id: str, operation_id: str, result: dict[str, Any], *, execute_suite: bool = False) -> dict[str, Any]:
    operation_id = _operation_id(operation_id)
    if not isinstance(result, dict):
        raise _fail("INVALID_RESULT", "result must be an object")
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        if set(result) != {"contract_index"}: raise _fail("FABRICATED_RESULT_REJECTED", "caller result evidence is not accepted")
        payload = {"contract_index": result.get("contract_index")}
        retry = _retry_result(record, operation_id, "record-result", payload)
        if retry is not None:
            return retry
        pending = record.get("pending_action")
        if pending and pending.get("kind") == "IMPLEMENT" and (not record.get("edit_admission") or record["edit_admission"].get("contract_index") != pending["contract_index"]):
            raise _fail("EDIT_NOT_ADMITTED", "implementation result requires start-edit")
        validation = record.get("edit_validation")
        if not pending or not validation or validation.get("contract_index") != pending["contract_index"]:
            raise _fail("EDIT_NOT_VALIDATED", "record-result requires finish-edit evidence")
        committed_head = None
        if pending["kind"] == "IMPLEMENT":
            expected_parent = validation.get("result", {}).get("expected_parent_head")
            current_head = _ledger_git(Path(record["worktree_path"]), "rev-parse", "HEAD")
            if expected_parent and current_head != expected_parent:
                committed_head = _validate_validated_commit(record)
            else:
                _ledger_validate(record, allow_dirty=True)
        else:
            _ledger_validate(record, allow_dirty=bool(record.get("edit_validation")))
        normalized_result = dict(validation["result"])
        normalized_result["contract_index"] = pending["contract_index"]
        if not pending or normalized_result.get("contract_index") != pending["contract_index"]:
            raise _fail("ILLEGAL_TRANSITION", "no matching pending action")
        repo = Path(record["repo_path"]).resolve()
        record["results"].append({"action": pending["kind"], **normalized_result})
        record["pending_action"] = None
        if pending["kind"] == "IMPLEMENT": record["edit_admission"] = None
        record["current_head"] = committed_head or normalized_result["commit_sha"]
        if not normalized_result["gate_pass"] or not normalized_result["tests_pass"]:
            record["state"], record["stop_reason"] = "FAILED", "gate or tests failed"
        elif pending["kind"] == "IMPLEMENT" and committed_head is None:
            record["state"] = "VALIDATING"
        else:
            record["current_index"] += 1
            record["state"] = "COMMITTED" if record["current_index"] == len(record["contracts"]) else "ACTIVE"
        output = _result_view(record)
        _record_operation(record, operation_id, "record-result", payload, output)
        _append_event(campaign_id, record, operation_id, "record-result", normalized_result)
        return output


def _campaign_terminal(campaign_id: str, operation_id: str, state: str, command: str, reason: str) -> dict[str, Any]:
    operation_id = _operation_id(operation_id)
    if not reason or not reason.strip():
        raise _fail("INVALID_REASON", "reason required")
    payload = {"reason": reason}
    with _ledger_lock(campaign_id):
        record = _ledger_load(campaign_id)
        retry = _retry_result(record, operation_id, command, payload)
        if retry is not None:
            return retry
        _ledger_validate(record, allow_dirty=bool(record.get("edit_validation")))
        if record["state"] in CAMPAIGN_TERMINAL:
            raise _fail("ILLEGAL_TRANSITION", "terminal transition repeated")
        record["state"], record["stop_reason"] = state, reason
        record["pending_action"] = None
        output = _result_view(record)
        _record_operation(record, operation_id, command, payload, output)
        _append_event(campaign_id, record, operation_id, command, payload)
        return output


def campaign_ledger_quarantine(campaign_id: str, operation_id: str, reason: str) -> dict[str, Any]:
    return _campaign_terminal(campaign_id, operation_id, "QUARANTINED", "quarantine", reason)


def campaign_ledger_stop(campaign_id: str, operation_id: str, reason: str) -> dict[str, Any]:
    return _campaign_terminal(campaign_id, operation_id, "STOPPED", "stop", reason)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Stateful external campaign ledger")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("campaign_id"); init.add_argument("operation_id"); init.add_argument("repo"); init.add_argument("gate_blob_sha")
    init.add_argument("contract", nargs="+", help="contract.json=sha256")
    init.add_argument("--suite-id", action="append", dest="suite_ids")
    for name in ("status", "next"):
        command = commands.add_parser(name); command.add_argument("campaign_id"); command.add_argument("--repo"); command.add_argument("--worktree"); command.add_argument("--contract", dest="contract_override"); command.add_argument("--suite-id")
    checkpoint = commands.add_parser("checkpoint"); checkpoint.add_argument("campaign_id"); checkpoint.add_argument("operation_id")
    discovery_start = commands.add_parser("start-discovery"); discovery_start.add_argument("discovery_id"); discovery_start.add_argument("operation_id")
    discovery_checkpoint = commands.add_parser("discovery-checkpoint"); discovery_checkpoint.add_argument("discovery_id"); discovery_checkpoint.add_argument("operation_id"); discovery_checkpoint.add_argument("findings_file")
    discovery_finish = commands.add_parser("finish-discovery"); discovery_finish.add_argument("discovery_id"); discovery_finish.add_argument("operation_id"); discovery_finish.add_argument("findings_file")
    edit = commands.add_parser("start-edit"); edit.add_argument("campaign_id"); edit.add_argument("contract_index", type=int); edit.add_argument("operation_id")
    finish = commands.add_parser("finish-edit"); finish.add_argument("campaign_id"); finish.add_argument("contract_index", type=int); finish.add_argument("operation_id")
    result = commands.add_parser("record-result")
    result.add_argument("campaign_id"); result.add_argument("operation_id"); result.add_argument("contract_index", type=int)
    result.add_argument("gate_pass", nargs="?", type=lambda value: value.lower() == "true")
    result.add_argument("tests_pass", nargs="?"); result.add_argument("patch_sha", nargs="?"); result.add_argument("commit_sha", nargs="?")
    result.add_argument("--suite-id", default=None); result.add_argument("--command", dest="arbitrary_command", default=None); result.add_argument("--repo"); result.add_argument("--worktree"); result.add_argument("--contract", dest="contract_override")
    for name in ("quarantine", "stop"):
        command = commands.add_parser(name); command.add_argument("campaign_id"); command.add_argument("operation_id"); command.add_argument("reason"); command.add_argument("--repo"); command.add_argument("--worktree"); command.add_argument("--contract", dest="contract_override"); command.add_argument("--suite-id")
    args = parser.parse_args(argv)
    try:
        if args.command != "init" and any(getattr(args, name, None) for name in ("repo", "worktree")):
            raise _fail("WORKTREE_MISMATCH", "caller path override is not allowed")
        if getattr(args, "contract_override", None):
            raise _fail("CONTRACT_NOT_INITIALIZED", "caller contract override is not allowed")
        if args.command != "record-result" and getattr(args, "suite_id", None):
            raise _fail("SUITE_NOT_ALLOWED", "caller suite override is not allowed")
        if args.command == "start-discovery": value = campaign_discovery_start(args.discovery_id, args.operation_id)
        elif args.command == "discovery-checkpoint": value = campaign_discovery_checkpoint(args.discovery_id, args.operation_id, args.findings_file)
        elif args.command == "finish-discovery": value = campaign_discovery_finish(args.discovery_id, args.operation_id, args.findings_file)
        elif args.command == "init":
            queue = [dict(zip(("path", "sha256"), item.rsplit("=", 1))) for item in args.contract]
            value = campaign_ledger_init(args.campaign_id, args.operation_id, args.repo, args.gate_blob_sha, queue, args.suite_ids)
        elif args.command == "status": value = campaign_ledger_status(args.campaign_id)
        elif args.command == "next": value = campaign_ledger_next(args.campaign_id)
        elif args.command == "checkpoint": value = campaign_ledger_checkpoint(args.campaign_id, args.operation_id)
        elif args.command == "start-edit": value = campaign_ledger_start_edit(args.campaign_id, args.contract_index, args.operation_id)
        elif args.command == "finish-edit": value = campaign_ledger_finish_edit(args.campaign_id, args.contract_index, args.operation_id)
        elif args.command == "record-result":
            if args.arbitrary_command is not None:
                raise _fail("ARBITRARY_COMMAND_REJECTED", "arbitrary command input is not allowed")
            if any(value is not None for value in (args.gate_pass, args.tests_pass, args.patch_sha, args.commit_sha, args.suite_id)):
                raise _fail("FABRICATED_RESULT_REJECTED", "caller result evidence is not accepted")
            result_payload = {"contract_index": args.contract_index}
            value = campaign_ledger_record_result(args.campaign_id, args.operation_id, result_payload, execute_suite=True)
        elif args.command == "quarantine": value = campaign_ledger_quarantine(args.campaign_id, args.operation_id, args.reason)
        else: value = campaign_ledger_stop(args.campaign_id, args.operation_id, args.reason)
        print(json.dumps(value, sort_keys=True, separators=(",", ":")))
        return 0
    except CampaignError as exc:
        parser.error(str(exc))
    except OSError as exc:
        parser.error(f"IO_ERROR: {exc}")
    except ValueError as exc:
        parser.error(f"PRECONDITION_FAILED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
