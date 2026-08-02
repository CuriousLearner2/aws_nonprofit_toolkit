from __future__ import annotations

from scripts.householder.row_status_policy import derive_row_status


def test_derive_row_status_blocking_wins():
    assert derive_row_status([{"severity": "warning"}, {"severity": "error"}]) == "Blocking"


def test_derive_row_status_warning_when_no_errors():
    assert derive_row_status([{"severity": "warning"}, {"severity": "info"}]) == "Warning"


def test_derive_row_status_no_issues_when_empty():
    assert derive_row_status([]) == "No issues"


def test_derive_row_status_defaults_non_error_to_warning():
    assert derive_row_status([{"severity": None}]) == "Warning"
