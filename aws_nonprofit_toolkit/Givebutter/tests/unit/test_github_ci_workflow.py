"""Contract tests for the repository-root GitHub Actions CI workflow."""

from __future__ import annotations

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


def test_ci_uses_absolute_venv_python_for_critical_commands():
    text = _workflow_text()

    assert '"$GIVEBUTTER_DIR/.venv/bin/python" \\\n            "$GIVEBUTTER_DIR/scripts/ci/test_gate.py"' in text
    assert '-- "$GIVEBUTTER_DIR/.venv/bin/python" -m pytest' in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" "$GIVEBUTTER_DIR/scripts/ci/check_no_artifacts.py"' in text
    assert '"$GIVEBUTTER_DIR/.venv/bin/python" -m compileall scripts tests' in text
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
