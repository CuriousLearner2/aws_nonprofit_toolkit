"""Contract tests for the repository-root GitHub Actions CI workflow."""

from __future__ import annotations

import re
from pathlib import Path


EXPECTED_PYTHON_VERSION = 'python-version: "3.11.9"'
EXPECTED_GIVEBUTTER_DIR = (
    "GIVEBUTTER_DIR: ${{ github.workspace }}/aws_nonprofit_toolkit/Givebutter"
)


def _find_repository_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        workflow = parent / ".github" / "workflows" / "ci.yml"
        if workflow.is_file():
            return parent
    raise AssertionError("Could not locate repository-root .github/workflows/ci.yml")


def _workflow_text() -> str:
    return (_find_repository_root() / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )


def test_ci_uses_supported_python_and_read_only_permissions():
    text = _workflow_text()

    assert EXPECTED_PYTHON_VERSION in text
    assert "permissions:\n  contents: read" in text
    assert "pull-requests: write" not in text
    assert "contents: write" not in text


def _job_block(text: str, job_name: str) -> str:
    pattern = rf"^  {re.escape(job_name)}:\n(?:(?:    .*\n)|(?:\n))*?(?=^  [A-Za-z0-9_-]+:|\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    assert match is not None, f"Could not find job block for {job_name}"
    return match.group(0)


def test_ci_defines_one_canonical_givebutter_directory():
    text = _workflow_text()

    assert EXPECTED_GIVEBUTTER_DIR in text
    assert text.count(EXPECTED_GIVEBUTTER_DIR) == 1


def test_ci_creates_project_venv_and_persists_path_across_steps():
    text = _workflow_text()

    assert 'test ! -e "$GIVEBUTTER_DIR/.venv"' in text
    assert '"$pythonLocation/bin/python" -m venv "$GIVEBUTTER_DIR/.venv"' in text
    assert 'python -m venv "$GIVEBUTTER_DIR/.venv"' not in text
    assert 'export PATH="$GIVEBUTTER_DIR/.venv/bin:$PATH"' in text
    assert 'echo "$GIVEBUTTER_DIR/.venv/bin" >> "$GITHUB_PATH"' in text
    assert 'test -x "$GIVEBUTTER_DIR/.venv/bin/python"' in text
    assert 'test -x "$GIVEBUTTER_DIR/.venv/bin/pytest"' in text


def test_ci_verifies_interpreter_resolution_before_tests():
    text = _workflow_text()

    clean_runner_index = text.index("- name: Verify clean runner assumptions")
    verification_index = text.index("- name: Verify Givebutter virtualenv")
    test_index = text.index("- name: Run canonical unit and integration tests")
    assert clean_runner_index < verification_index < test_index
    assert '"$pythonLocation/bin/python" -m venv "$GIVEBUTTER_DIR/.venv"' in text
    assert verification_index < test_index
    assert "command -v python" in text
    assert "command -v pytest" in text
    assert "python -c \"import sys; print(sys.executable)\"" in text
    assert 'export PATH="$GIVEBUTTER_DIR/.venv/bin:$PATH"' in text
    assert 'python_executable="$(python -c \'import sys; print(sys.executable)\')"' in text
    assert "from importlib.metadata import version; import sys; print(version('playwright')); print(sys.executable)" in text


def test_ci_uses_absolute_venv_python_for_critical_commands():
    text = _workflow_text()

    assert '"$GIVEBUTTER_DIR/.venv/bin/python" \\\n            "$GIVEBUTTER_DIR/scripts/ci/test_gate.py"' in text
    assert '-- "$GIVEBUTTER_DIR/.venv/bin/python" -m pytest' in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" "$GIVEBUTTER_DIR/scripts/ci/check_no_artifacts.py"' in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" -m compileall scripts tests' in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" \\\n            "$GIVEBUTTER_DIR/scripts/ci/e2e_gate.py"' in text
    assert '-- "$GIVEBUTTER_DIR/.venv/bin/python" -m pytest \\\n            tests/e2e/test_e2e_upload_workflow.py::test_upload_drop_zone_ignores_empty_drop_and_recovers' in text
    assert 'python scripts/ci/test_gate.py' not in text
    assert 'source .venv/bin/activate' not in text


def test_ci_does_not_activate_venv_in_a_single_step_only():
    text = _workflow_text()

    assert "source .venv/bin/activate" not in text
    assert "source $GIVEBUTTER_DIR/.venv/bin/activate" not in text


def test_ci_has_manual_and_pull_request_triggers():
    text = _workflow_text()

    assert "pull_request:" in text
    assert "merge_group:" in text
    assert "workflow_dispatch:" in text


def test_ci_pins_only_browser_job_to_ubuntu_22_04():
    text = _workflow_text()

    baseline = _job_block(text, "baseline")
    browser = _job_block(text, "browser-e2e")

    assert "runs-on: ubuntu-24.04" in baseline
    assert "runs-on: ubuntu-22.04" in browser
    assert "runs-on: ubuntu-24.04" not in browser


def test_ci_adds_isolated_browser_e2e_job_for_approved_p1_workflows():
    text = _workflow_text()

    assert "browser-e2e:" in text
    assert "name: Browser E2E checks" in text
    assert "needs: baseline" in text
    assert "timeout-minutes: 45" in text
    assert "- name: Install Playwright Chromium" in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" -m playwright install --with-deps chromium' in text
    assert "- name: Run browser E2E checks" in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" \\\n            "$GIVEBUTTER_DIR/scripts/ci/e2e_gate.py"' in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" -m pytest \\\n            tests/e2e/test_e2e_upload_workflow.py::test_upload_drop_zone_ignores_empty_drop_and_recovers' in text
    assert 'tests/e2e/test_e2e_upload_workflow.py::test_upload_drop_zone_rejects_invalid_drop_and_recovers_with_drag_drop' in text
    assert 'tests/e2e/test_e2e_upload_workflow.py::test_upload_drop_zone_blocks_repeated_drops_while_upload_is_in_flight' in text
    assert 'tests/e2e/test_e2e_upload_workflow.py::test_upload_non_givebutter_csv_shows_inline_error_banner' in text
    assert 'tests/e2e/test_e2e_upload_workflow.py::test_upload_file_picker_creates_review_link_and_opens_validation' in text
    assert 'tests/e2e/test_e2e_upload_workflow.py::test_upload_file_picker_repeated_same_filename_keeps_distinct_review_links' in text
    assert 'tests/e2e/test_validation_export_blocking.py::test_validation_blocker_appears_in_export_console' in text
    assert 'tests/e2e/test_validation_export_blocking.py::test_failed_autosave_values_not_exported' in text
    assert 'tests/e2e/test_validation_export_blocking.py::test_persisted_validation_override_allows_export' in text
    assert 'tests/e2e/test_validation_export_blocking.py::test_clean_validation_export_proceeds' in text
    assert 'tests/e2e/test_validation_review_dom.py::test_all_inline_fields_persist_after_browser_refresh' in text
    assert 'tests/e2e/test_validation_review_dom.py::test_approval_overrides_produce_export_ready_readiness_after_reload' in text
    assert 'tests/e2e/test_e2e_decision_workflow.py::test_save_all_decisions_completes_review' in text
    assert 'tests/e2e/test_desktop_canonical_screens_smoke.py::test_desktop_canonical_screens_smoke' in text
    assert 'python -m pytest tests/e2e' not in text
    assert 'playwright install --with-deps chromium' in text
