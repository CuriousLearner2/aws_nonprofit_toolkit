#!/usr/bin/env python3
"""
E2E-specific pytest wrapper enforcing fail-fast discipline.

Wraps pytest E2E commands with:
1. Enforced explicit wall-clock timeout (required)
2. Validation that multi-test E2E pytest commands include -x or --maxfail=1
3. Single-test E2E commands allowed without -x
4. Guaranteed exit-code preservation or 124 on timeout

Prevents 20-30 minute hangs by mechanically enforcing fail-fast rules.

Usage:
  Single test (no -x required):
    python scripts/ci/e2e_gate.py --timeout 90 -- pytest tests/e2e/test_file.py::test_name -v

  Multi-test (must include -x):
    python scripts/ci/e2e_gate.py --timeout 180 -- pytest tests/e2e/test_file.py -x -v

CLI format:
  --timeout N       wall-clock timeout in seconds (required)
  --                separator before wrapped command (required)
  <command> [args]  command and args to run (required)

E2E-specific validation:
  - Detects single-test E2E pytest by presence of :: in target
  - Requires -x or --maxfail=1 for multi-test E2E pytest commands
  - Single-test E2E commands may omit -x
  - Fails before running if -x is missing for multi-test
  - Does not inject -x (requires explicit flag)

Output:
  Prints a clear report with:
  - Exact command
  - Timeout value
  - Single-test? (yes/no)
  - Multi-test -x requirement and validation result
  - Elapsed seconds
  - Exit code or timeout indicator
  - Pass/fail status

Exit codes:
  0-127, 255  = underlying command exit code (preserved)
  124         = timeout (standard Unix convention)
  1           = validation/argument parsing error

No external dependencies (stdlib only).
"""

import subprocess
import sys
import time


def parse_arguments():
    """
    Parse CLI arguments.

    Format: --timeout N -- <command> [args...]
    Returns (timeout_seconds, command_list) or exits with error.
    """
    # Manual parsing to handle the -- separator correctly
    if len(sys.argv) < 5:  # script --timeout N -- cmd (minimum 5 args)
        print("Error: Missing required arguments", file=sys.stderr)
        print("Usage: python scripts/ci/e2e_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] != "--timeout":
        print("Error: First argument must be --timeout", file=sys.stderr)
        print("Usage: python scripts/ci/e2e_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    try:
        timeout_seconds = int(sys.argv[2])
    except (ValueError, IndexError):
        print("Error: --timeout requires an integer value", file=sys.stderr)
        print("Usage: python scripts/ci/e2e_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if timeout_seconds <= 0:
        print("Error: timeout must be a positive integer", file=sys.stderr)
        sys.exit(1)

    if sys.argv[3] != "--":
        print("Error: -- separator is required", file=sys.stderr)
        print("Usage: python scripts/ci/e2e_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 5:
        print("Error: No command specified after --", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[4:]
    return timeout_seconds, command


def is_e2e_pytest_command(command_list):
    """
    Check if command is a pytest command targeting tests/e2e/.

    Returns True if command appears to be pytest targeting E2E tests.
    """
    if not command_list or 'pytest' not in command_list[0] and 'pytest' not in command_list:
        return False

    # Check for pytest in command
    has_pytest = any('pytest' in str(arg) for arg in command_list)
    if not has_pytest:
        return False

    # Check for tests/e2e/ or tests/e2e in arguments
    has_e2e_target = any('tests/e2e' in str(arg) for arg in command_list)
    return has_e2e_target


def is_single_test_target(command_list):
    """
    Check if pytest command targets a single test.

    Single-test targets contain :: (e.g., test_file.py::test_name).
    Multi-test targets do not have :: (e.g., test_file.py or tests/e2e/).

    Returns True if any argument contains :: and tests/e2e.
    """
    for arg in command_list:
        if '::' in str(arg) and 'tests' in str(arg):
            return True
    return False


def has_fail_fast_flag(command_list):
    """
    Check if command includes -x or --maxfail flag.

    Recognized fail-fast patterns:
    - -x
    - --maxfail
    - --maxfail=N
    """
    for arg in command_list:
        arg_str = str(arg)
        if arg_str == '-x':
            return True
        if arg_str.startswith('--maxfail'):
            return True
    return False


def validate_e2e_command(command_list):
    """
    Validate E2E pytest command for fail-fast compliance.

    Rules:
    - Single-test E2E commands may omit -x
    - Multi-test E2E commands must include -x or --maxfail

    Returns (is_valid, reason).
    """
    if not is_e2e_pytest_command(command_list):
        # Not an E2E pytest command, no special validation needed
        return True, "not_e2e_pytest"

    is_single = is_single_test_target(command_list)
    has_flag = has_fail_fast_flag(command_list)

    if is_single:
        # Single-test: always OK whether or not -x is present
        return True, "single_test_allowed"
    else:
        # Multi-test: must have -x or --maxfail
        if has_flag:
            return True, "multi_test_with_flag"
        else:
            return False, "multi_test_missing_flag"


def run_gate(timeout_seconds, command):
    """
    Run the wrapped command with timeout enforcement.

    Returns (exit_code, elapsed_seconds, timed_out).
    """
    start_time = time.time()

    try:
        result = subprocess.run(
            command,
            timeout=timeout_seconds
        )
        elapsed = time.time() - start_time
        return result.returncode, elapsed, False

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return 124, elapsed, True


def format_command(command_list):
    """Format command list into a readable string."""
    return " ".join(str(arg) for arg in command_list)


def main():
    """Main entry point."""
    timeout_seconds, command = parse_arguments()

    # Validate E2E command before running
    is_valid, reason = validate_e2e_command(command)

    if not is_valid:
        print(f"\n{'='*70}")
        print(f"E2E Gate Validation Error")
        print(f"{'='*70}")
        print(f"Command:       {format_command(command)}")
        print(f"Error:         Multi-test E2E pytest command missing -x or --maxfail=1")
        print(f"Required:      Include -x or --maxfail=1 to enforce fail-fast discipline")
        print(f"               This prevents 20-30 minute hangs on first test failure")
        print(f"\nExample (add -x flag):")
        print(f"  pytest tests/e2e/test_file.py -x -v --tb=short")
        print(f"{'='*70}\n")
        sys.exit(1)

    # Run the gate
    exit_code, elapsed, timed_out = run_gate(timeout_seconds, command)

    # Determine test type and validation status
    is_e2e = is_e2e_pytest_command(command)
    is_single = is_single_test_target(command) if is_e2e else None
    has_flag = has_fail_fast_flag(command) if is_e2e else None

    # Print report
    command_str = format_command(command)
    passed = exit_code == 0 and not timed_out

    print(f"\n{'='*70}")
    print(f"E2E Gate Report")
    print(f"{'='*70}")
    print(f"Command:       {command_str}")
    print(f"Timeout:       {timeout_seconds} seconds")

    if is_e2e:
        print(f"Single test?   {'yes' if is_single else 'no'}")
        if not is_single:
            print(f"Has -x flag?   {'yes' if has_flag else 'no'}")

    print(f"Elapsed:       {elapsed:.2f} seconds")

    if timed_out:
        print(f"Status:        TIMEOUT")
        print(f"Exit code:     124 (timeout)")
    else:
        print(f"Exit code:     {exit_code}")
        status = "PASS" if exit_code == 0 else "FAIL"
        print(f"Status:        {status}")

    print(f"Gate passed?   {'yes' if passed else 'no'}")
    print(f"{'='*70}\n")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
