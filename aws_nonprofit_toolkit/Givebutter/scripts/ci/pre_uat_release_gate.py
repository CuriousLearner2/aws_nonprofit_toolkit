#!/usr/bin/env python3
"""Fail-closed pre-UAT release gate assembled from existing focused tests."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    name: str
    command: tuple[str, ...]
    timeout: int


def _pytest(*targets: str) -> tuple[str, ...]:
    return (sys.executable, "-m", "pytest", *targets, "-x", "-q")


CORPUS_TARGETS = (
    # Existing 100-row processor corpus plus the existing edge-case fixtures.
    "tests/integration/test_processor_full.py::TestProcessorFullPipeline::test_process_large_csv",
    "tests/integration/test_processor_full.py::TestProcessorFullPipeline::test_process_csv_with_typos",
    "tests/integration/test_processor_full.py::TestProcessorFullPipeline::test_process_csv_with_missing_data",
    "tests/integration/test_email_severity_consistency.py",
    "tests/unit/test_contact_validation_projection.py",
    "tests/e2e/test_international_phone_contract.py",
    "tests/e2e/test_address_issue_integrity_dom.py",
)


def components() -> tuple[Component, ...]:
    e2e_gate = (sys.executable, "scripts/ci/e2e_gate.py")

    def e2e(target: str, timeout: int = 300) -> tuple[str, ...]:
        return e2e_gate + ("--timeout", str(timeout), "--", *_pytest(target))

    return (
        Component(
            "pre-UAT reviewer journey",
            e2e("tests/e2e/test_pre_uat_reviewer_journey.py"),
            360,
        ),
        Component(
            "mutation/projection matrix",
            _pytest("tests/unit/test_row_state_transition_matrix.py"),
            120,
        ),
        Component(
            "fresh-session/reload smoke",
            e2e("tests/e2e/test_final_product_smoke.py"),
            360,
        ),
        Component(
            "approval/export checks",
            _pytest(
                "tests/integration/test_file_approval_row_dispositions.py",
                "tests/integration/test_export_preview_consistency.py",
            ),
            180,
        ),
        Component(
            "realistic corpus smoke",
            _pytest(*CORPUS_TARGETS),
            360,
        ),
        Component(
            "Hypothesis reviewer state-machine suite",
            e2e("tests/e2e/test_hypothesis_reviewer_state_machine.py"),
            360,
        ),
        Component(
            "fault-injection reviewer-state suite",
            e2e("tests/e2e/test_reviewer_fault_injection.py"),
            360,
        ),
    )


def _failure_count(output: str, returncode: int) -> int:
    """Extract pytest failure/error count; unknown nonzero results count as one red."""
    import re

    matches = [
        int(value)
        for value in re.findall(r"(?:^|\s)(\d+)\s+(?:failed|error|errors?)\b", output)
    ]
    return sum(matches) if matches else (1 if returncode else 0)


def run_component(component: Component) -> tuple[bool, float, str, int]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            component.command,
            timeout=component.timeout,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        elapsed = time.monotonic() - started
        output = result.stdout.strip()
        tail = output.splitlines()[-1] if output else "no output"
        return result.returncode == 0, elapsed, tail, _failure_count(output, result.returncode)
    except subprocess.TimeoutExpired:
        return False, time.monotonic() - started, "TIMEOUT", 1
    except OSError as error:
        return False, time.monotonic() - started, f"OSError: {error}", 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Householder pre-UAT release gate")
    parser.add_argument("--list", action="store_true", help="list component commands and exit")
    args = parser.parse_args()

    selected = components()
    if args.list:
        for component in selected:
            print(f"{component.name}: {' '.join(component.command)}")
        return 0

    failed = 0
    print("Householder pre-UAT release gate")
    for component in selected:
        passed, elapsed, detail, reds = run_component(component)
        status = "PASS" if passed else "FAIL"
        failed += reds
        print(f"[{status}] {component.name} ({elapsed:.1f}s) — {detail}")

    print(f"relevant red count: {failed}")
    verdict = "READY_FOR_UAT" if failed == 0 else "NOT_READY_FOR_UAT"
    print(verdict)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
