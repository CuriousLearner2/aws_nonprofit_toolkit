import json
import subprocess
from pathlib import Path

import pytest


MODULE = Path(__file__).parents[2] / "scripts/uploader/static/js/validation_filter_state.js"


def transition(selection, action):
    script = (
        "const f=require(process.argv[1]);"
        "console.log(JSON.stringify(f.transition(JSON.parse(process.argv[2]), process.argv[3])));"
    )
    result = subprocess.run(
        ["node", "-e", script, str(MODULE), json.dumps(selection), action],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    ("selection", "action", "expected"),
    [
        ([], "Blocking", ["Blocking"]),
        ([], "Warning", ["Warning"]),
        (["Blocking"], "Warning", ["Blocking", "Warning"]),
        (["Warning"], "Blocking", ["Warning", "Blocking"]),
        (["Blocking", "Warning"], "No issues", ["No issues"]),
        (["No issues"], "Blocking", ["Blocking"]),
        (["No issues"], "Warning", ["Warning"]),
        (["Blocking", "Warning"], "all", []),
    ],
)
def test_severity_selection_transitions(selection, action, expected):
    assert transition(selection, action) == expected


def test_clicking_an_active_severity_removes_only_that_severity():
    assert transition(["Blocking", "Warning"], "Blocking") == ["Warning"]


@pytest.mark.parametrize(
    ("row_status", "selection", "expected"),
    [
        ("Blocking", ["Blocking"], True),
        ("Warning", ["Warning"], True),
        ("Blocking", ["Blocking", "Warning"], True),
        ("Warning", ["Blocking", "Warning"], True),
        ("No issues", ["Blocking", "Warning"], False),
        ("No issues", ["No issues"], True),
        ("Warning", ["No issues"], False),
        ("No issues", [], True),
    ],
)
def test_severity_filter_matches_rows(row_status, selection, expected):
    script = (
        "const f=require(process.argv[1]);"
        "console.log(f.matches(process.argv[2], JSON.parse(process.argv[3])));"
    )
    result = subprocess.run(
        ["node", "-e", script, str(MODULE), row_status, json.dumps(selection)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == str(expected).lower()
