#!/usr/bin/env python3
"""
Guard script to block untracked artifact files from being committed.

Uses git as source of truth:
- Allows all tracked files (even if they match artifact patterns)
- Blocks untracked files that match conservative artifact patterns
- Exits 0 if no blocking artifacts; exits 1 with list if blocking artifacts found

Conservative patterns blocked:
- OS metadata (.DS_Store, Thumbs.db)
- Editor artifacts (*.bak, *.swp, *.swo, *~)
- Debug files (*.pdb, .env.local)
- Tool caches (.mypy_cache, .ruff_cache, .hypothesis)
- Test artifacts (test_results/, test_artifacts/, playwright_results/, traces/, videos/)
- Local DB files (*.db, *.sqlite, *.sqlite3)
- Log files (*.log)
- New untracked screenshots in screenshots/ directory

Allows:
- All tracked files in git (reference screenshots, test_data, testing/)
- Safe untracked files not matching patterns
"""

import subprocess
import sys
import re
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


def get_tracked_files():
    """Get set of all tracked files in git."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=True
        )
        return set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
    except subprocess.CalledProcessError as e:
        print(f"Error reading tracked files: {e}", file=sys.stderr)
        sys.exit(1)


def get_untracked_files():
    """Get list of untracked files from git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
            check=True
        )
        untracked = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            # Untracked files start with '?? '
            if line.startswith('?? '):
                untracked.append(line[3:])
        return untracked
    except subprocess.CalledProcessError as e:
        print(f"Error reading untracked files: {e}", file=sys.stderr)
        sys.exit(1)


def is_blocked_artifact(filepath):
    """
    Check if filepath matches a blocked artifact pattern.

    Returns True if it's a junk artifact, False if it's safe to commit.
    """
    # OS metadata
    if filepath == ".DS_Store" or filepath.endswith("/.DS_Store"):
        return True
    if filepath == "Thumbs.db":
        return True

    # Editor artifacts
    if re.search(r'\.(bak|tmp|swp|swo)$', filepath):
        return True
    if filepath.endswith('~'):
        return True

    # Debug and secrets
    if filepath.endswith('.pdb'):
        return True
    if filepath == ".env.local" or filepath.endswith("/.env.local"):
        return True

    # Tool caches
    if re.search(r'(^|\/)(\.(mypy_cache|ruff_cache|hypothesis))(/|$)', filepath):
        return True
    if filepath in [".mypy_cache", ".ruff_cache", ".hypothesis"]:
        return True
    # Handle trailing slashes
    if filepath.rstrip('/') in [".mypy_cache", ".ruff_cache", ".hypothesis"]:
        return True

    # Test output directories
    test_dirs = ["test_results", "test_artifacts", "playwright_results", "traces", "videos"]
    for test_dir in test_dirs:
        if filepath == test_dir or filepath.startswith(f"{test_dir}/"):
            return True

    # Local database files
    if re.search(r'\.(db|sqlite|sqlite3)$', filepath):
        return True

    # Log files (conservative: block all .log files)
    if filepath.endswith('.log'):
        return True

    # New screenshots in screenshots/ directory
    if filepath.startswith("screenshots/"):
        # Allow if it looks like reference file (householder-v1-*.png pattern)
        if re.search(r'householder-v\d+-.*\.png$', filepath):
            return False
        # Block other new screenshot files (including in subdirectories)
        if filepath.endswith(('.png', '.jpg', '.jpeg')):
            return True

    return False


def main():
    """Main guard function."""
    repo_root = get_repo_root()
    tracked_files = get_tracked_files()
    untracked_files = get_untracked_files()

    blocking_artifacts = []

    for filepath in untracked_files:
        # Skip if this file is already tracked (shouldn't happen with git status --untracked-files=all)
        if filepath in tracked_files:
            continue

        # Check if it's a blocked artifact
        if is_blocked_artifact(filepath):
            blocking_artifacts.append(filepath)

    if blocking_artifacts:
        print("❌ Found untracked artifact files that must not be committed:", file=sys.stderr)
        for artifact in sorted(blocking_artifacts):
            print(f"  - {artifact}", file=sys.stderr)
        print("\nPlease remove these files or add them to .gitignore if intentional.", file=sys.stderr)
        sys.exit(1)

    print("✅ No blocking artifacts found", file=sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
