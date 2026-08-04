from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts" / "ci"))

from householder_paths import (  # noqa: E402
    CanonicalPathError,
    RepositoryLayout,
    canonical_changed_paths,
    canonicalize,
    canonicalize_many,
    discover_layout,
    sha256_patch,
    to_git_path,
)


MARKERS = (
    "scripts/ci/householder_campaign.py",
    "scripts/ci/architecture_slice_gate.py",
    "scripts/householder/autosave_service.py",
    "tests/integration/test_autosave_validation.py",
)


def make_layout(tmp_path: Path, nested: bool) -> tuple[RepositoryLayout, Path]:
    project = tmp_path / "aws_nonprofit_toolkit" / "Givebutter" if nested else tmp_path
    for marker in MARKERS:
        path = project / marker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("marker\n", encoding="utf-8")
    target = project / "scripts/ci/householder_paths.py"
    target.write_text("path\n", encoding="utf-8")
    return discover_layout(tmp_path), target


@pytest.mark.parametrize("nested", [False, True])
def test_flat_and_nested_representations_are_identical(tmp_path: Path, nested: bool) -> None:
    layout, target = make_layout(tmp_path, nested)
    project_form = "scripts/ci/householder_paths.py"
    representations = [project_form, str(target)]
    if nested:
        representations.append(to_git_path(project_form, layout))
    assert {canonicalize(value, layout) for value in representations} == {project_form}


def test_conformance_matrix_has_one_canonical_snapshot(tmp_path: Path) -> None:
    snapshots = []
    for nested, category in itertools.product((False, True), ("test", "production")):
        layout, target = make_layout(tmp_path / f"{nested}-{category}", nested)
        relative = "tests/unit/test_householder_paths.py" if category == "test" else "scripts/ci/householder_paths.py"
        path = layout.project_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("one\ntwo\n", encoding="utf-8")
        forms = [relative, str(path)]
        if nested:
            forms.append(to_git_path(relative, layout))
        canonical = tuple(canonicalize(form, layout) for form in forms)
        snapshots.append((category, canonical, path.read_text(encoding="utf-8").count("\n"), sha256_patch(path.read_bytes())))
    assert set(snapshots[0][1]) == set(snapshots[2][1]) == {"tests/unit/test_householder_paths.py"}
    assert set(snapshots[1][1]) == set(snapshots[3][1]) == {"scripts/ci/householder_paths.py"}
    assert snapshots[0][2:] == snapshots[2][2:]
    assert snapshots[1][2:] == snapshots[3][2:]


@pytest.mark.parametrize("value", ["../escape.py", "scripts/../escape.py", "", "/tmp/escape.py", "scripts\\bad.py"])
def test_invalid_paths_fail_closed(tmp_path: Path, value: str) -> None:
    layout, _ = make_layout(tmp_path, nested=True)
    with pytest.raises(CanonicalPathError):
        canonicalize(value, layout)


def test_duplicate_aliases_are_rejected_before_ledger_creation(tmp_path: Path) -> None:
    layout, target = make_layout(tmp_path, nested=True)
    with pytest.raises(CanonicalPathError, match="duplicate aliases"):
        canonicalize_many(["scripts/ci/householder_paths.py", str(target)], layout)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    layout, _ = make_layout(tmp_path, nested=True)
    outside = tmp_path / "outside.py"
    outside.write_text("outside\n", encoding="utf-8")
    link = layout.project_root / "scripts/ci/escape.py"
    link.symlink_to(outside)
    with pytest.raises(CanonicalPathError):
        canonicalize("scripts/ci/escape.py", layout)


def test_ambiguous_project_roots_are_rejected(tmp_path: Path) -> None:
    make_layout(tmp_path, nested=False)
    nested = tmp_path / "aws_nonprofit_toolkit" / "Givebutter"
    for marker in MARKERS:
        path = nested / marker
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("duplicate\n", encoding="utf-8")
    with pytest.raises(CanonicalPathError, match="ambiguous"):
        discover_layout(tmp_path)
