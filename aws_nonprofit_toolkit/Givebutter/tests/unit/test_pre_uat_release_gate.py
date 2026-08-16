"""Focused contract tests for the pre-UAT release-gate composition."""

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parents[2] / "scripts" / "ci"))
from pre_uat_release_gate import components, run_component  # noqa: E402


def test_gate_contains_all_required_existing_components():
    names = [component.name for component in components()]
    assert names == [
        "pre-UAT reviewer journey",
        "mutation/projection matrix",
        "fresh-session/reload smoke",
        "approval/export checks",
        "realistic corpus smoke",
    ]


def test_gate_components_are_fail_closed_and_use_existing_tests():
    for component in components():
        assert component.timeout > 0
        assert component.command
        assert any("pytest" in part for part in component.command)
        for target in component.command:
            if target.startswith("tests/"):
                assert Path(target.split("::", 1)[0]).exists(), target


def test_failed_component_is_reported_as_failure():
    from pre_uat_release_gate import Component

    passed, _, detail, reds = run_component(Component("broken", (sys.executable, "-c", "raise SystemExit(7)"), 5))
    assert passed is False
    assert detail == "no output"
    assert reds == 1


def test_missing_executable_is_fail_closed():
    from pre_uat_release_gate import Component

    passed, _, detail, reds = run_component(Component("missing", ("/missing/pre-uat-command",), 5))
    assert passed is False
    assert detail.startswith("OSError:")
    assert reds == 1


def test_corpus_component_includes_100_row_and_edge_case_coverage():
    corpus = next(component for component in components() if component.name == "realistic corpus smoke")
    command = " ".join(corpus.command)
    assert "test_process_large_csv" in command
    assert "test_process_csv_with_typos" in command
    assert "test_process_csv_with_missing_data" in command
    assert "test_email_severity_consistency.py" in command
    assert "test_contact_validation_projection.py" in command
    assert "test_international_phone_contract.py" in command
    assert "test_address_issue_integrity_dom.py" in command
