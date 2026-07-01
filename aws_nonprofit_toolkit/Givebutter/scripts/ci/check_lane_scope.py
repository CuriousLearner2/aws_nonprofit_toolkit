#!/usr/bin/env python3
"""
Lane scope guard to detect incompatible dirty-tree file mixtures.

Classifies changed files by semantic workflow lane and blocks mixed-lane violations
before Reviewer. Prevents product files mixed with workflow/CI files in single task.

Lanes:
  assessment   - No edits allowed (assessment-only tasks)
  push-only    - No edits allowed (push-only tasks)
  test-only    - Tests only; blocks product/workflow/CI/schema/docs
  workflow-ci  - Workflow+CI files; blocks product and schema
  product      - Product+tests+docs; blocks workflow/CI files

Usage:
  python scripts/ci/check_lane_scope.py --lane product
  python scripts/ci/check_lane_scope.py --lane workflow-ci --verbose
  python scripts/ci/check_lane_scope.py --lane test-only --simulate
  python scripts/ci/check_lane_scope.py --lane product --allow-schema

Exit codes:
  0 = lane scope is clean
  1 = lane scope conflict detected
  2 = argument/usage error

Uses stdlib only. No external dependencies.
"""

import subprocess
import sys
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
        sys.exit(2)


def normalize_path(filepath, repo_root, current_dir):
    """
    Normalize path to be relative to current working directory.

    If filepath is relative to repo root, adjust it to be relative to cwd.
    Handles both absolute paths and repo-root-relative paths (from git status).
    """
    repo_root_path = Path(repo_root).resolve()
    current_dir_path = Path(current_dir).resolve()

    # Case 1: filepath is already absolute
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
    """Get all changed files: modified, staged, untracked."""
    changed_files = []
    repo_root = get_repo_root()
    current_dir = Path.cwd()

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )

        for line in result.stdout.rstrip('\n').split('\n'):
            if not line:
                continue

            status = line[:2]

            # Handle rename entries (R followed by similarity score)
            if status[0] == 'R':
                remainder = line[3:]
                if ' -> ' in remainder:
                    parts = remainder.split(' -> ')
                    filepath = parts[-1].strip()
                else:
                    filepath = remainder.strip()
            else:
                filepath = line[3:]

            if filepath:
                # Normalize path to handle nested repo structures
                normalized = normalize_path(filepath, repo_root, current_dir)
                changed_files.append(normalized)

        return changed_files

    except subprocess.CalledProcessError as e:
        print(f"Error reading git status: {e}", file=sys.stderr)
        sys.exit(2)


def classify_file(filepath):
    """
    Classify a file into a semantic category.

    Returns: one of 'workflow', 'ci', 'product', 'tests', 'docs', 'schema', 'other'
    """
    parts = filepath.split('/')

    # Workflow files
    if filepath.startswith('.claude/') or filepath.startswith('.github/'):
        return 'workflow'

    # CI automation files
    if filepath.startswith('scripts/ci/'):
        return 'ci'

    # Product files
    if (filepath.startswith('scripts/householder/') or
        filepath.startswith('scripts/uploader/') or
        filepath == 'scripts/uploader/app.py' or
        filepath.startswith('scripts/uploader/templates/')):
        return 'product'

    # Test files
    if filepath.startswith('tests/'):
        return 'tests'

    # Documentation files
    if filepath.startswith('docs/') or (filepath.endswith('.md') and not filepath.startswith('.claude/')):
        return 'docs'

    # Schema files
    if (filepath.startswith('migrations/') or
        'migrations/' in filepath or
        filepath == 'schema.sql' or
        filepath.endswith('.sql')):
        return 'schema'

    # Other
    return 'other'


def check_lane_scope(lane, changed_files, allow_schema=False, simulate=False, verbose=False):
    """
    Check if changed files conform to lane scope rules.

    Returns: (is_clean: bool, conflicts: list of (category, reason))
    """
    conflicts = []
    categorized = {}

    # Get repo root for normalization
    repo_root = get_repo_root()
    current_dir = Path.cwd()

    # Categorize all files (normalize nested paths first)
    for filepath in changed_files:
        normalized = normalize_path(filepath, repo_root, current_dir)
        category = classify_file(normalized)
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(normalized)

    if verbose and changed_files:
        print("\nFile categorization:")
        for category in sorted(categorized.keys()):
            print(f"  {category}: {len(categorized[category])} file(s)")

    # Apply lane-specific rules
    if lane == 'assessment' or lane == 'push-only':
        # No edits allowed
        if any(changed_files):
            conflicts.append(('any', f'{lane} tasks do not allow edits'))

    elif lane == 'test-only':
        # Allow tests only
        for category in categorized.keys():
            if category != 'tests':
                conflicts.append((category, f'test-only allows tests/** only, not {category} files'))

    elif lane == 'workflow-ci':
        # Allow workflow, ci, and CI-script tests
        for category in categorized.keys():
            if category == 'product':
                conflicts.append(('product', 'workflow-ci does not allow product files; split into separate product task'))
            elif category == 'schema':
                conflicts.append(('schema', 'workflow-ci does not allow schema/migration files'))
            elif category == 'docs' and not categorized[category][0].startswith('.claude/'):
                conflicts.append(('docs', 'workflow-ci allows .claude/* docs only, not general docs/'))
            elif category == 'other':
                conflicts.append(('other', 'workflow-ci does not allow miscellaneous files'))

    elif lane == 'product':
        # Allow product, tests, docs; block workflow, ci, schema (unless --allow-schema)
        for category in categorized.keys():
            if category == 'workflow':
                conflicts.append(('workflow', 'product does not allow .claude/* workflow files; split into separate workflow task'))
            elif category == 'ci':
                conflicts.append(('ci', 'product does not allow scripts/ci/* files; split into separate workflow-ci task'))
            elif category == 'schema' and not allow_schema:
                conflicts.append(('schema', 'product does not allow schema/migration files without --allow-schema'))
            elif category == 'other':
                conflicts.append(('other', 'product does not allow miscellaneous files'))

    is_clean = len(conflicts) == 0
    return is_clean, conflicts, categorized


def main():
    """Main entry point."""
    # Parse arguments
    lane = None
    allow_schema = False
    simulate = False
    verbose = False

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--lane':
            if i + 1 >= len(sys.argv):
                print("Error: --lane requires a value", file=sys.stderr)
                print("Usage: python scripts/ci/check_lane_scope.py --lane {assessment|test-only|workflow-ci|product|push-only}", file=sys.stderr)
                sys.exit(2)
            lane = sys.argv[i + 1]
            i += 2
        elif arg == '--allow-schema':
            allow_schema = True
            i += 1
        elif arg == '--simulate':
            simulate = True
            i += 1
        elif arg == '--verbose':
            verbose = True
            i += 1
        else:
            print(f"Error: Unknown argument: {arg}", file=sys.stderr)
            print("Usage: python scripts/ci/check_lane_scope.py --lane LANE [--allow-schema] [--simulate] [--verbose]", file=sys.stderr)
            sys.exit(2)

    if not lane:
        print("Error: --lane is required", file=sys.stderr)
        print("Usage: python scripts/ci/check_lane_scope.py --lane {assessment|test-only|workflow-ci|product|push-only}", file=sys.stderr)
        sys.exit(2)

    valid_lanes = {'assessment', 'test-only', 'workflow-ci', 'product', 'push-only'}
    if lane not in valid_lanes:
        print(f"Error: Unknown lane '{lane}'. Valid lanes: {', '.join(sorted(valid_lanes))}", file=sys.stderr)
        sys.exit(2)

    # Get changed files and check lane scope
    changed_files = get_changed_files()
    is_clean, conflicts, categorized = check_lane_scope(lane, changed_files, allow_schema, simulate, verbose)

    # Print report
    print(f"\n{'='*70}")
    print(f"Lane Scope Guard")
    print(f"{'='*70}")
    print(f"Lane:           {lane}")
    print(f"Changed files:  {len(changed_files)}")

    if changed_files and verbose:
        print(f"\nFiles by category:")
        for category in sorted(categorized.keys()):
            files = categorized[category]
            print(f"  {category}: {len(files)} file(s)")
            if verbose and len(files) <= 3:
                for f in files:
                    print(f"    - {f}")

    if conflicts:
        print(f"\nConflicts detected ({len(conflicts)}):")
        for category, reason in conflicts:
            print(f"  [{category}] {reason}")
    else:
        print(f"\n✓ Lane scope is clean")

    status = "PASS" if is_clean else "CONFLICT"
    print(f"\nStatus:        {status}")
    print(f"{'='*70}\n")

    # Exit code
    if simulate:
        sys.exit(0)
    elif is_clean:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
