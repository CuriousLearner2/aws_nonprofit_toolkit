#!/usr/bin/env python3
"""Guard staged-tree integrity by materializing the exact staged snapshot."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT_NAME = Path(__file__).resolve().parents[2].name
STAGED_TREE_ANCHORS = (
    "/scripts/",
    "/tests/",
    "/templates/",
    "/.claude/",
    "/.github/",
    "/migrations/",
    "/schema.sql",
)


def get_repo_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("Error: not in a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(result.stdout.strip())


def normalize_path(filepath: str) -> str:
    normalized = filepath.replace("\\", "/").strip()
    anchors = (
        f"{PROJECT_ROOT_NAME}/",
        "/scripts/",
        "/tests/",
        "/templates/",
        "/.claude/",
        "/.github/",
        "/migrations/",
        "/schema.sql",
    )
    for anchor in anchors:
        index = normalized.find(anchor)
        if index != -1:
            return normalized[index + len(anchor):]
    return normalized


def get_staged_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def infer_staged_root_relative(staged_files: list[str]) -> Path:
    for filepath in staged_files:
        normalized = filepath.replace("\\", "/").strip()
        for anchor in STAGED_TREE_ANCHORS:
            index = normalized.find(anchor)
            if index != -1:
                prefix = normalized[:index].strip("/")
                return Path(prefix) if prefix else Path(".")
    return Path(".")


def materialize_staged_tree(repo_root: Path, tempdir: Path) -> Path:
    subprocess.run(
        ["git", "checkout-index", "-a", "-f", f"--prefix={tempdir}/"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    staged_root = tempdir / infer_staged_root_relative(get_staged_files(repo_root))
    return staged_root if staged_root.exists() else tempdir


def derive_default_commands(staged_files: list[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    for filepath in staged_files:
        normalized = normalize_path(filepath)
        if not normalized.endswith(".py"):
            continue
        if normalized.startswith("tests/"):
            commands.append([
                sys.executable,
                "-m",
                "pytest",
                normalized,
                "--collect-only",
                "-q",
            ])
        else:
            module = normalized[:-3].replace("/", ".")
            commands.append([
                sys.executable,
                "-c",
                f"import importlib; importlib.import_module({module!r})",
            ])
    return commands


def run_command(command: list[str], cwd: Path) -> int:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 127
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def parse_commands(values: list[str]) -> list[list[str]]:
    parsed: list[list[str]] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("focused commands must be non-empty strings")
        try:
            parsed.append(shlex.split(value))
        except ValueError as exc:
            raise ValueError(f"malformed focused command: {value}") from exc
        if not parsed[-1]:
            raise ValueError("focused commands must not be empty")
    return parsed


def check_staged_tree_integrity(explicit_commands: list[str] | None = None) -> int:
    repo_root = get_repo_root()
    staged_files = get_staged_files(repo_root)
    with tempfile.TemporaryDirectory(prefix="staged-tree-") as tmp:
        tempdir = Path(tmp)
        staged_root = materialize_staged_tree(repo_root, tempdir)
        commands = derive_default_commands(staged_files)
        try:
            if explicit_commands:
                commands.extend(parse_commands(explicit_commands))
        except ValueError as exc:
            print(f"❌ {exc}")
            return 1

        print("Checking staged-tree integrity...")
        print(f"- staged root: {staged_root}")
        print(f"- staged files: {len(staged_files)}")

        for index, command in enumerate(commands, start=1):
            print(f"- command {index}: {' '.join(command)}")
            exit_code = run_command(command, staged_root)
            if exit_code != 0:
                print(f"❌ Staged-tree command failed with exit code {exit_code}")
                return exit_code

        print("✓ Staged-tree integrity is clean")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--command",
        action="append",
        default=[],
        help="Extra focused command to run inside the staged tree; may be repeated.",
    )
    args = parser.parse_args()
    try:
        return check_staged_tree_integrity(args.command)
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
