"""Canonical repository-path handling for launcher, wrapper, and gates.

All public path values emitted by this module are project-root-relative POSIX
paths.  Inputs are resolved against one immutable :class:`RepositoryLayout`
at the boundary; callers must not perform a second path interpretation.
"""

from __future__ import annotations

import hashlib
import os
import posixpath
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


class CanonicalPathError(ValueError):
    """A path cannot be represented safely in project-root form."""


PROJECT_MARKERS = (
    "scripts/ci/householder_campaign.py",
    "scripts/ci/architecture_slice_gate.py",
    "scripts/householder/autosave_service.py",
    "tests/integration/test_autosave_validation.py",
)


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _posix_input(value: str | Path) -> str:
    if not isinstance(value, (str, Path)):
        raise CanonicalPathError("path must be a string or Path")
    raw = os.fspath(value)
    if not raw or "\0" in raw:
        raise CanonicalPathError("path must be non-empty and NUL-free")
    if "\\" in raw:
        raise CanonicalPathError("backslash paths are not accepted")
    return raw


def _relative_parts(raw: str) -> tuple[str, ...]:
    if raw.startswith("/"):
        raise CanonicalPathError("absolute path was expected at the absolute-path boundary")
    # Do not normalize traversal away: it is an invalid representation even if
    # the resulting path would happen to remain inside the project.
    parts = tuple(part for part in raw.split("/") if part not in ("", "."))
    if not parts or any(part == ".." for part in parts):
        raise CanonicalPathError("path traversal or empty path is not allowed")
    if any(part in {"", "."} for part in parts):
        raise CanonicalPathError("malformed path")
    return parts


@dataclass(frozen=True)
class RepositoryLayout:
    git_root: Path
    project_root: Path
    project_prefix: str

    def __post_init__(self) -> None:
        git_root = _real(Path(self.git_root))
        project_root = _real(Path(self.project_root))
        if not git_root.is_dir() or not project_root.is_dir() or not _inside(project_root, git_root):
            raise CanonicalPathError("project root must be a directory inside the Git root")
        prefix = project_root.relative_to(git_root).as_posix()
        object.__setattr__(self, "git_root", git_root)
        object.__setattr__(self, "project_root", project_root)
        object.__setattr__(self, "project_prefix", "" if prefix == "." else prefix)


def discover_layout(git_root: Path, *, markers: Sequence[str] = PROJECT_MARKERS) -> RepositoryLayout:
    """Resolve exactly one flat or nested project root beneath ``git_root``."""
    root = _real(Path(git_root))
    if not root.is_dir():
        raise CanonicalPathError("Git root is not a directory")
    candidates = (root, root / "aws_nonprofit_toolkit" / "Givebutter")
    valid: list[Path] = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        resolved = _real(candidate)
        if resolved != candidate or not resolved.is_dir():
            raise CanonicalPathError("project root is symlinked")
        if all((resolved / marker).is_file() for marker in markers):
            valid.append(resolved)
    if not valid:
        raise CanonicalPathError("project root is unavailable")
    if len(valid) > 1:
        raise CanonicalPathError("multiple project roots are ambiguous")
    return RepositoryLayout(root, valid[0], "")


def layout_from_project(project_root: Path, *, git_root: Path | None = None) -> RepositoryLayout:
    project = _real(Path(project_root))
    if git_root is None:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode or not result.stdout.strip():
            raise CanonicalPathError("unable to resolve Git root")
        git_root = Path(result.stdout.strip())
    return RepositoryLayout(Path(git_root), project, "")


def canonicalize(value: str | Path, layout: RepositoryLayout) -> str:
    """Canonicalize one accepted input path to a project-relative POSIX path."""
    raw = _posix_input(value)
    candidate: Path
    if os.path.isabs(raw):
        candidate = _real(Path(raw))
        if not _inside(candidate, layout.project_root):
            raise CanonicalPathError("absolute path is outside project root")
        relative = candidate.relative_to(layout.project_root).as_posix()
    else:
        parts = _relative_parts(raw)
        normalized = posixpath.join(*parts)
        prefix = layout.project_prefix
        if prefix and (normalized == prefix or normalized.startswith(prefix + "/")):
            relative = normalized[len(prefix):].lstrip("/")
            if not relative:
                raise CanonicalPathError("path names the project root")
            candidate = _real(layout.git_root / normalized)
        else:
            relative = normalized
            candidate = _real(layout.project_root / normalized)
        if not _inside(candidate, layout.project_root):
            raise CanonicalPathError("path escapes project root")
    if not relative or relative == ".":
        raise CanonicalPathError("path names the project root")
    final = PurePosixPath(relative).as_posix()
    if final.startswith("../") or final == ".." or "/../" in f"/{final}/":
        raise CanonicalPathError("canonical path escapes project root")
    return final


def canonicalize_git_path(value: str | Path, layout: RepositoryLayout) -> str:
    """Canonicalize a path emitted by Git, which is Git-root-relative."""
    raw = _posix_input(value)
    if os.path.isabs(raw):
        raise CanonicalPathError("Git path must be relative to the Git root")
    if layout.project_prefix:
        parts = _relative_parts(raw)
        normalized = posixpath.join(*parts)
        if normalized != layout.project_prefix and not normalized.startswith(layout.project_prefix + "/"):
            raise CanonicalPathError("Git path is outside canonical project root")
    return canonicalize(raw, layout)


def canonicalize_many(values: Iterable[str | Path], layout: RepositoryLayout, *, field: str = "paths") -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = canonicalize(value, layout)
        if item in seen:
            raise CanonicalPathError(f"{field} contains duplicate aliases for {item}")
        seen.add(item)
        result.append(item)
    return result


def validate_project_relative(value: str, *, field: str = "path") -> str:
    """Validate an already-canonical persisted project-relative path."""
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise CanonicalPathError(f"{field} must be a canonical POSIX path")
    parts = _relative_parts(value)
    canonical = PurePosixPath(*parts).as_posix()
    if canonical != value or canonical in {".", ".."} or canonical.startswith("../"):
        raise CanonicalPathError(f"{field} must be a canonical project-relative path")
    return canonical


def resolve_in_project(value: str | Path, layout: RepositoryLayout) -> Path:
    """Resolve a canonical project-relative path without reinterpreting it."""
    relative = validate_project_relative(os.fspath(value))
    target = _real(layout.project_root / relative)
    if not _inside(target, layout.project_root):
        raise CanonicalPathError("path escapes project root")
    return target


def to_git_path(project_relative: str, layout: RepositoryLayout) -> str:
    return f"{layout.project_prefix}/{project_relative}" if layout.project_prefix else project_relative


def canonical_changed_paths(values: Iterable[str | Path], layout: RepositoryLayout) -> list[str]:
    return sorted(canonicalize_many(values, layout, field="changed paths"))


def sha256_patch(patch: bytes) -> str:
    return hashlib.sha256(patch).hexdigest()
