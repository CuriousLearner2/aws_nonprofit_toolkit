"""Parity coverage for the canonical row-status service contract."""

import pytest

from scripts.householder import autosave_service, validation_service
from scripts.householder.row_status_service import derive_row_status


@pytest.mark.parametrize(
    ("issues", "expected"),
    [
        ([], "No issues"),
        ([{"severity": "warning"}], "Warning"),
        ([{"severity": "error"}], "Blocking"),
        ([{"severity": "warning"}, {"severity": "error"}], "Blocking"),
    ],
)
def test_canonical_status_matrix(issues, expected):
    assert derive_row_status(issues=issues) == expected


def test_autosave_and_validation_fallbacks_delegate_to_canonical_service():
    assert autosave_service.derive_row_status is derive_row_status
    assert validation_service.derive_row_status is derive_row_status


def test_row_context_is_required_when_status_must_recalculate():
    with pytest.raises(ValueError, match="batch_id and raw_import_row_id"):
        derive_row_status()
