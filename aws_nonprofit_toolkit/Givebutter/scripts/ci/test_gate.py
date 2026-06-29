#!/usr/bin/env python3
"""
Bounded pytest wrapper for non-E2E gates with guaranteed wall-clock timeout.

Wraps pytest (or any command) with enforced per-command timeout.
Exits with underlying command's exit code if it completes, or 124 if timeout.

Usage:
  python scripts/ci/test_gate.py --timeout 120 -- pytest tests/unit -q
  python scripts/ci/test_gate.py --timeout 300 -- pytest tests/integration -q

CLI format:
  --timeout N       wall-clock timeout in seconds (required)
  --                separator before wrapped command (required)
  <command> [args]  command and args to run (required)

Output:
  Prints a clear report with:
  - Exact command
  - Timeout value
  - Elapsed seconds
  - Exit code or timeout indicator
  - Pass/fail status

Exit codes:
  0-127, 255  = underlying command exit code (preserved)
  124         = timeout (standard Unix convention)
  1           = argument parsing error

No external dependencies (stdlib only).
"""

import subprocess
import sys
import time
import argparse


def parse_arguments():
    """
    Parse CLI arguments.

    Format: --timeout N -- <command> [args...]
    Returns (timeout_seconds, command_list) or exits with error.
    """
    # Manual parsing to handle the -- separator correctly
    if len(sys.argv) < 5:  # script --timeout N -- cmd (minimum 5 args)
        print("Error: Missing required arguments", file=sys.stderr)
        print("Usage: python scripts/ci/test_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] != "--timeout":
        print("Error: First argument must be --timeout", file=sys.stderr)
        print("Usage: python scripts/ci/test_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    try:
        timeout_seconds = int(sys.argv[2])
    except (ValueError, IndexError):
        print("Error: --timeout requires an integer value", file=sys.stderr)
        print("Usage: python scripts/ci/test_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if timeout_seconds <= 0:
        print("Error: timeout must be a positive integer", file=sys.stderr)
        sys.exit(1)

    if sys.argv[3] != "--":
        print("Error: -- separator is required", file=sys.stderr)
        print("Usage: python scripts/ci/test_gate.py --timeout N -- <command> [args...]", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 5:
        print("Error: No command specified after --", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[4:]
    return timeout_seconds, command


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
    return " ".join(command_list)


def main():
    """Main entry point."""
    timeout_seconds, command = parse_arguments()

    # Run the gate
    exit_code, elapsed, timed_out = run_gate(timeout_seconds, command)

    # Print report
    command_str = format_command(command)
    passed = exit_code == 0 and not timed_out

    print(f"\n{'='*70}")
    print(f"Gate Report")
    print(f"{'='*70}")
    print(f"Command:       {command_str}")
    print(f"Timeout:       {timeout_seconds} seconds")
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
