"""Focused tests for launcher environment verification and doctor output."""

import importlib.util
import sys
from pathlib import Path

import pytest


LAUNCHER_PATH = Path(__file__).parents[2] / "scripts" / "ci" / "householder_launcher.py"
sys.path.insert(0, str(LAUNCHER_PATH.parent))
SPEC = importlib.util.spec_from_file_location("householder_launcher_under_test", LAUNCHER_PATH)
launcher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(launcher)


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "requirements.txt").write_text("pytest==7.4.3\n", encoding="utf-8")
    (project / "requirements-test.txt").write_text("pytest-asyncio==0.21.1\n", encoding="utf-8")
    return project


def _markers(project: Path) -> None:
    for marker in launcher.MARKERS:
        path = project / marker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# marker\n", encoding="utf-8")


def test_verified_venv_fingerprint_contains_required_identity(tmp_path, monkeypatch):
    project = _project(tmp_path)
    venv = Path("/private/tmp/householder-python311-autosave-20260803")
    monkeypatch.setattr(launcher, "PYTHON311_VENV", str(venv))
    result = launcher._environment(project)
    assert result["venv"] is True
    assert result["python_version"].startswith("3 11")
    assert result["python_executable"].endswith("python3.11")
    assert len(result["fingerprint"]) == 64
    assert result["installed_packages"]["pytest"] == "7.4.3"


def test_durable_venv_is_the_default_configuration():
    assert launcher.PYTHON311_VENV == "/Users/gautambiswas/.householder/envs/python311"


def test_incomplete_configured_venv_is_rejected(tmp_path, monkeypatch):
    project = _project(tmp_path)
    monkeypatch.setattr(launcher, "PYTHON311_VENV", str(tmp_path / "incomplete-venv"))
    with pytest.raises(launcher.LaunchError) as exc:
        launcher._environment(project)
    assert exc.value.code == "ENVIRONMENT_MISMATCH"


def test_bare_interpreter_is_rejected_without_expected_fingerprint(tmp_path, monkeypatch):
    project = _project(tmp_path)
    monkeypatch.setattr(launcher, "PYTHON311_VENV", "")
    monkeypatch.setattr(launcher, "PYTHON311", "/opt/homebrew/bin/python3.11")
    monkeypatch.setattr(launcher, "EXPECTED_ENVIRONMENT_FINGERPRINT", "")
    with pytest.raises(launcher.LaunchError, match="expected environment fingerprint") as exc:
        launcher._environment(project)
    assert exc.value.code == "ENVIRONMENT_MISMATCH"


def test_missing_declared_package_is_environment_mismatch(tmp_path, monkeypatch):
    project = _project(tmp_path)
    (project / "requirements.txt").write_text("package-that-cannot-exist==1.0\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "PYTHON311_VENV", "/private/tmp/householder-python311-autosave-20260803")
    with pytest.raises(launcher.LaunchError) as exc:
        launcher._environment(project)
    assert exc.value.code == "ENVIRONMENT_MISMATCH"
    assert exc.value.details["missing_packages"] == ["package-that-cannot-exist"]


def test_suite_records_are_fixed_to_project_root_and_verified_interpreter(tmp_path):
    project = tmp_path / "project"
    (project / "tests").mkdir(parents=True)
    suite = project / "tests" / "test_fixed.py"
    suite.write_text("", encoding="utf-8")
    monkey_environment = {"fingerprint": "f" * 64}

    class Wrapper:
        SUITE_REGISTRY = {"fixed": ["ignored", "-m", "pytest", "-q", "tests/test_fixed.py"]}

    original = launcher._wrapper
    try:
        launcher._wrapper = lambda _: Wrapper
        records = launcher._suite_records(project, ["fixed"], "/approved/python", monkey_environment)
    finally:
        launcher._wrapper = original
    assert records == [{
        "suite_id": "fixed",
        "argv": ["/approved/python", "-m", "pytest", "-q", "tests/test_fixed.py"],
        "cwd_role": "project_root",
        "cwd": str(project),
        "interpreter": "/approved/python",
        "environment_fingerprint": "f" * 64,
    }]


def test_missing_fixed_suite_path_is_distinct_from_environment_error(tmp_path):
    class Wrapper:
        SUITE_REGISTRY = {"missing": ["ignored", "-m", "pytest", "-q", "tests/missing.py"]}

    original = launcher._wrapper
    try:
        launcher._wrapper = lambda _: Wrapper
        with pytest.raises(launcher.LaunchError) as exc:
            launcher._suite_records(tmp_path, ["missing"], "/approved/python", {"fingerprint": "f" * 64})
    finally:
        launcher._wrapper = original
    assert exc.value.code == "SUITE_PATH_INVALID"


@pytest.mark.parametrize("nested", [False, True])
def test_project_root_discovery_supports_flat_and_nested_layouts(tmp_path, nested):
    root = tmp_path / "checkout"
    project = root / "aws_nonprofit_toolkit" / "Givebutter" if nested else root
    for marker in launcher.MARKERS:
        path = project / marker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    assert launcher.discover_project_root(root) == project


def test_doctor_success_is_bounded_and_does_not_use_scope_or_campaign_ledger(monkeypatch, tmp_path):
    payload = {"baseline": "a" * 40, "campaign_id": "doctor-test", "mode": "campaign", "authorized_production_paths": [], "authorized_test_paths": ["tests/test.py"], "suite_ids": ["fixed"], "time_limit_seconds": 10}
    project = tmp_path / "project"
    project.mkdir()
    _markers(project)
    calls = []
    monkeypatch.setattr(launcher, "_resolve_baseline", lambda _: {"sha": payload["baseline"]})
    monkeypatch.setattr(launcher, "_clone", lambda checkout, baseline: (project / "tests").mkdir(exist_ok=True))
    monkeypatch.setattr(launcher, "discover_project_root", lambda _: project)
    monkeypatch.setattr(launcher, "_git_out", lambda *args: str(project))
    monkeypatch.setattr(launcher, "_environment", lambda _: {"fingerprint": "f" * 64, "python_executable": "/approved/python"})
    monkeypatch.setattr(launcher, "_preflight", lambda *args: calls.append(args) or [{"suite_id": "fixed", "passed": True}])
    monkeypatch.setattr(launcher, "LAUNCH_ROOT", tmp_path / "launches")
    monkeypatch.setattr(launcher, "scope_lock", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("doctor must not lock scope")))
    result = launcher.doctor(payload)
    assert result["status"] == "READY"
    assert result["suite_records"][0]["suite_id"] == "fixed"
    assert calls


def test_doctor_retry_is_idempotent_at_command_result_level(monkeypatch, tmp_path):
    payload = {"baseline": "a" * 40, "campaign_id": "doctor-retry", "mode": "campaign", "authorized_production_paths": [], "authorized_test_paths": [], "suite_ids": ["fixed"], "time_limit_seconds": 10}
    project = tmp_path / "project"
    project.mkdir()
    _markers(project)
    monkeypatch.setattr(launcher, "_resolve_baseline", lambda _: {"sha": payload["baseline"]})
    monkeypatch.setattr(launcher, "_clone", lambda checkout, baseline: None)
    monkeypatch.setattr(launcher, "discover_project_root", lambda _: project)
    monkeypatch.setattr(launcher, "_git_out", lambda *args: str(project))
    monkeypatch.setattr(launcher, "_environment", lambda _: {"fingerprint": "f" * 64, "python_executable": "/approved/python"})
    monkeypatch.setattr(launcher, "_preflight", lambda *args: [{"suite_id": "fixed", "passed": True}])
    monkeypatch.setattr(launcher, "LAUNCH_ROOT", tmp_path / "launches")
    first = launcher.doctor(payload)
    second = launcher.doctor(payload)
    assert first["status"] == second["status"] == "READY"
    assert first["error_code"] == second["error_code"] is None


def test_doctor_preserves_bounded_preflight_stdout_and_stderr(monkeypatch, tmp_path):
    payload = {"baseline": "a" * 40, "campaign_id": "doctor-error", "mode": "campaign", "authorized_production_paths": [], "authorized_test_paths": [], "suite_ids": ["fixed"], "time_limit_seconds": 10}
    project = tmp_path / "project"
    project.mkdir()
    _markers(project)
    monkeypatch.setattr(launcher, "_resolve_baseline", lambda _: {"sha": payload["baseline"]})
    monkeypatch.setattr(launcher, "_clone", lambda checkout, baseline: None)
    monkeypatch.setattr(launcher, "discover_project_root", lambda _: project)
    monkeypatch.setattr(launcher, "_git_out", lambda *args: str(project))
    monkeypatch.setattr(launcher, "_environment", lambda _: {"fingerprint": "f" * 64, "python_executable": "/approved/python"})
    monkeypatch.setattr(launcher, "_preflight", lambda *args: (_ for _ in ()).throw(launcher.LaunchError("SUITE_PREFLIGHT_FAILED", "suite failed", {"stdout": "o" * 21000, "stderr": "e" * 21000})))
    monkeypatch.setattr(launcher, "LAUNCH_ROOT", tmp_path / "launches")
    result = launcher.doctor(payload)
    assert result["error_code"] == "SUITE_PREFLIGHT_FAILED"
    assert result["stdout"].endswith("...[truncated]")
    assert result["stderr"].endswith("...[truncated]")
    assert len(result["stdout"]) < 20100
