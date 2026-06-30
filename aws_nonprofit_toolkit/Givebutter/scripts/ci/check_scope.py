#!/usr/bin/env python3
"""
Explicit scope guard to detect unintended file changes before commit.

Helps prevent scope creep by verifying changed files match an explicit allowlist.
Supports exact paths and glob patterns (e.g., tests/**, scripts/ci/*).

Usage:
  python scripts/ci/check_scope.py --allow scripts/ci/check_scope.py \
    --allow tests/unit/test_check_scope.py
  python scripts/ci/check_scope.py --allow 'tests/**' --allow 'docs/**'

CLI:
  --allow PATTERN    file path or glob pattern to allow (required, one or more)

Output:
  Prints a clear report with:
  - Allow patterns provided
  - Actual changed files (staged, unstaged, untracked)
  - Unexpected files (if any)
  - Pass/fail status

Exit codes:
  0 = scope matches (all changed files within allowlist)
  1 = scope mismatch (unexpected files found) or argument error

No external dependencies (stdlib only).
"""

import subprocess
import sys
import fnmatch
from pathlib import Path


def get_repo_root():
    """Get git repository root path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)


def normalize_path(filepath, repo_root, current_dir):
    """
    Normalize path to be relative to current working directory.

    If filepath is relative to repo root, adjust it to be relative to cwd.
    Handles both absolute paths and repo-root-relative paths.
    """
    repo_root_path = Path(repo_root).resolve()
    current_dir_path = Path(current_dir).resolve()

    # Case 1: filepath is already absolute (provided as full path)
    if Path(filepath).is_absolute():
        filepath_abs = Path(filepath).resolve()
        try:
            relative = filepath_abs.relative_to(current_dir_path)
            return str(relative).replace('\\', '/')
        except ValueError:
            return filepath.replace('\\', '/')

    # Case 2: filepath is repo-root-relative (from git status)
    # Construct the absolute path: repo_root + filepath
    candidate = repo_root_path / filepath
    try:
        relative = candidate.relative_to(current_dir_path)
        return str(relative).replace('\\', '/')
    except ValueError:
        # Path is not under current_dir; return as-is
        return filepath.replace('\\', '/')


def get_changed_files():
    """
    Get all changed files: staged, unstaged, and untracked.

    For renamed files, uses the destination (new) path for scope matching.

    Returns: list of file paths (relative to current working directory)
    """
    changed_files = []
    repo_root = get_repo_root()
    current_dir = Path.cwd()

    try:
        # Get all modified/staged files and untracked files
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.rstrip('\n').split('\n'):
            if not line:
                continue

            # Format: XY PATH  or  R<score> OLD_PATH -> NEW_PATH
            # First two chars are status, rest is path
            # For renames: extract destination (new) path
            status = line[:2]

            # Handle rename entries (R followed by similarity score)
            if status[0] == 'R':
                # Rename format: R<score> old -> new
                # Extract the destination (new) path
                remainder = line[3:]
                if ' -> ' in remainder:
                    # Split on ' -> ' and use the new path (after arrow)
                    parts = remainder.split(' -> ')
                    filepath = parts[-1].strip()
                else:
                    # Fallback if format differs (space-separated without arrow)
                    filepath = remainder.strip()
            else:
                # Standard format: XY PATH
                filepath = line[3:]

            # Include all non-empty paths from modified, staged, or untracked files
            if filepath:
                # Normalize to relative to current directory
                normalized = normalize_path(filepath, repo_root, current_dir)
                changed_files.append(normalized)

        return changed_files

    except subprocess.CalledProcessError as e:
        print(f"Error reading git status: {e}", file=sys.stderr)
        sys.exit(1)


def matches_pattern(filepath, patterns):
    """
    Check if filepath matches any pattern in the allowlist.

    Supports exact paths and glob patterns.
    """
    for pattern in patterns:
        # Exact match
        if filepath == pattern:
            return True

        # Glob match (fnmatch handles *, **, ?, [seq], etc.)
        if fnmatch.fnmatch(filepath, pattern):
            return True

    return False


def main():
    """Main entry point."""
    # Parse arguments
    allow_patterns = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--allow":
            if i + 1 >= len(sys.argv):
                print("Error: --allow requires a pattern argument", file=sys.stderr)
                print("Usage: python scripts/ci/check_scope.py --allow PATTERN [--allow PATTERN ...]", file=sys.stderr)
                sys.exit(1)
            allow_patterns.append(sys.argv[i + 1])
            i += 2
        else:
            print(f"Error: Unknown argument: {arg}", file=sys.stderr)
            print("Usage: python scripts/ci/check_scope.py --allow PATTERN [--allow PATTERN ...]", file=sys.stderr)
            sys.exit(1)

    if not allow_patterns:
        print("Error: At least one --allow pattern is required", file=sys.stderr)
        print("Usage: python scripts/ci/check_scope.py --allow PATTERN [--allow PATTERN ...]", file=sys.stderr)
        sys.exit(1)

    # Get changed files
    changed_files = get_changed_files()

    # Check each changed file against patterns
    unexpected_files = []
    for filepath in changed_files:
        if not matches_pattern(filepath, allow_patterns):
            unexpected_files.append(filepath)

    # Print report
    print(f"\n{'='*70}")
    print(f"Scope Guard Report")
    print(f"{'='*70}")
    print(f"Allow patterns:")
    for pattern in allow_patterns:
        print(f"  - {pattern}")

    print(f"\nChanged files ({len(changed_files)}):")
    if changed_files:
        for filepath in sorted(changed_files):
            print(f"  - {filepath}")
    else:
        print(f"  (none)")

    print(f"\nUnexpected files ({len(unexpected_files)}):")
    if unexpected_files:
        for filepath in sorted(unexpected_files):
            print(f"  - {filepath}")
    else:
        print(f"  (none)")

    status = "PASS" if not unexpected_files else "FAIL"
    print(f"\nScope matched? {'yes' if not unexpected_files else 'no'}")
    print(f"Status:        {status}")
    print(f"{'='*70}\n")

    # Exit with appropriate code
    sys.exit(0 if not unexpected_files else 1)


if __name__ == "__main__":
    main()
