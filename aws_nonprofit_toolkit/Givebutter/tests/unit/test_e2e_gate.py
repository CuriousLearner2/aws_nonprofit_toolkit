"""Unit tests for the e2e_gate.py E2E fail-fast wrapper."""

import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the script functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))
from e2e_gate import (
    parse_arguments,
    run_gate,
    format_command,
    is_e2e_pytest_command,
    is_single_test_target,
    has_fail_fast_flag,
    validate_e2e_command,
)


class TestParseArguments:
    """Test CLI argument parsing (inherited from test_gate.py pattern)."""

    def test_valid_arguments(self):
        """Valid --timeout N -- command parsing."""
        test_argv = ["e2e_gate.py", "--timeout", "120", "--", "pytest", "tests/e2e/test_file.py", "-v"]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 120
            assert command == ["pytest", "tests/e2e/test_file.py", "-v"]

    def test_timeout_as_string_integer(self):
        """Timeout can be parsed as string integer."""
        test_argv = ["e2e_gate.py", "--timeout", "90", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 90
            assert isinstance(timeout, int)

    def test_missing_timeout_flag(self):
        """Missing --timeout flag causes exit."""
        test_argv = ["e2e_gate.py", "120", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_missing_timeout_value(self):
        """Missing --timeout value causes exit."""
        test_argv = ["e2e_gate.py", "--timeout", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_invalid_timeout_value(self):
        """Non-integer timeout value causes exit."""
        test_argv = ["e2e_gate.py", "--timeout", "abc", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_negative_timeout(self):
        """Negative timeout value causes exit."""
        test_argv = ["e2e_gate.py", "--timeout", "-5", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_zero_timeout(self):
        """Zero timeout value causes exit."""
        test_argv = ["e2e_gate.py", "--timeout", "0", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_missing_separator(self):
        """Missing -- separator causes exit."""
        test_argv = ["e2e_gate.py", "--timeout", "120", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_missing_command_after_separator(self):
        """Missing command after -- causes exit."""
        test_argv = ["e2e_gate.py", "--timeout", "120", "--"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1


class TestRunGate:
    """Test gate execution with timeout enforcement."""

    def test_passing_command(self):
        """Passing command (exit 0) returns 0."""
        exit_code, elapsed, timed_out = run_gate(10, ["python3", "-c", "pass"])
        assert exit_code == 0
        assert elapsed >= 0
        assert timed_out is False

    def test_failing_command(self):
        """Failing command (exit 1) returns 1."""
        exit_code, elapsed, timed_out = run_gate(10, ["python3", "-c", "import sys; sys.exit(1)"])
        assert exit_code == 1
        assert elapsed >= 0
        assert timed_out is False

    def test_preserves_exit_code(self):
        """Nonzero exit code is preserved."""
        exit_code, elapsed, timed_out = run_gate(10, ["python3", "-c", "import sys; sys.exit(5)"])
        assert exit_code == 5
        assert timed_out is False

    def test_timeout_exceeded(self):
        """Command exceeding timeout returns 124."""
        exit_code, elapsed, timed_out = run_gate(1, ["sleep", "5"])
        assert exit_code == 124
        assert timed_out is True
        assert elapsed >= 0.9  # Allow small timing variance

    def test_elapsed_time_tracked(self):
        """Elapsed time is tracked correctly."""
        exit_code, elapsed, timed_out = run_gate(30, ["python3", "-c", "pass"])
        assert elapsed >= 0
        assert elapsed < 2  # Should be very fast

    def test_long_running_command_within_timeout(self):
        """Long-running command within timeout completes."""
        exit_code, elapsed, timed_out = run_gate(2, ["sleep", "0.5"])
        assert exit_code == 0
        assert timed_out is False
        assert elapsed >= 0.4  # Allow for timing variance


class TestFormatCommand:
    """Test command formatting."""

    def test_single_command(self):
        """Single command is formatted correctly."""
        result = format_command(["pytest"])
        assert result == "pytest"

    def test_command_with_args(self):
        """Command with arguments is formatted correctly."""
        result = format_command(["pytest", "tests/e2e/test_file.py", "-v", "--tb=short"])
        assert result == "pytest tests/e2e/test_file.py -v --tb=short"


class TestE2EPytestDetection:
    """Test detection of E2E pytest commands."""

    def test_e2e_pytest_command(self):
        """E2E pytest command is detected."""
        assert is_e2e_pytest_command(["pytest", "tests/e2e/test_file.py", "-v"])

    def test_e2e_pytest_with_target(self):
        """E2E pytest with specific target is detected."""
        assert is_e2e_pytest_command(["pytest", "tests/e2e/test_file.py::test_name", "-v"])

    def test_unit_pytest_not_e2e(self):
        """Unit pytest command is not detected as E2E."""
        assert not is_e2e_pytest_command(["pytest", "tests/unit/test_file.py", "-v"])

    def test_integration_pytest_not_e2e(self):
        """Integration pytest command is not detected as E2E."""
        assert not is_e2e_pytest_command(["pytest", "tests/integration/test_file.py", "-v"])

    def test_non_pytest_command(self):
        """Non-pytest command is not detected as E2E."""
        assert not is_e2e_pytest_command(["python", "script.py", "tests/e2e/test_file.py"])

    def test_e2e_directory_target(self):
        """E2E directory target is detected."""
        assert is_e2e_pytest_command(["pytest", "tests/e2e/", "-v"])


class TestSingleTestDetection:
    """Test detection of single-test vs multi-test E2E commands."""

    def test_single_test_with_double_colon(self):
        """Single test detected when :: present in target."""
        assert is_single_test_target(["pytest", "tests/e2e/test_file.py::test_name", "-v"])

    def test_multi_test_without_double_colon(self):
        """Multi-test detected when :: absent."""
        assert not is_single_test_target(["pytest", "tests/e2e/test_file.py", "-v"])

    def test_multi_test_directory(self):
        """Multi-test detected for directory target."""
        assert not is_single_test_target(["pytest", "tests/e2e/", "-v"])

    def test_multiple_targets_single_test(self):
        """Single test detected with :: in first target."""
        assert is_single_test_target(["pytest", "tests/e2e/test_file.py::test_name", "tests/unit/test_other.py"])


class TestFailFastFlagDetection:
    """Test detection of -x and --maxfail flags."""

    def test_has_x_flag(self):
        """Command with -x flag is detected."""
        assert has_fail_fast_flag(["pytest", "tests/e2e/test_file.py", "-x", "-v"])

    def test_has_maxfail_flag(self):
        """Command with --maxfail is detected."""
        assert has_fail_fast_flag(["pytest", "tests/e2e/test_file.py", "--maxfail=1", "-v"])

    def test_has_maxfail_with_value(self):
        """Command with --maxfail=N is detected."""
        assert has_fail_fast_flag(["pytest", "tests/e2e/test_file.py", "--maxfail=2"])

    def test_missing_fail_fast_flag(self):
        """Command without -x or --maxfail is detected as missing."""
        assert not has_fail_fast_flag(["pytest", "tests/e2e/test_file.py", "-v"])

    def test_x_in_middle_of_command(self):
        """Flag position in command doesn't affect detection."""
        assert has_fail_fast_flag(["pytest", "-x", "tests/e2e/test_file.py", "-v"])


class TestE2ECommandValidation:
    """Test E2E command validation logic."""

    def test_single_test_allows_no_x_flag(self):
        """Single test E2E command allowed without -x."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/e2e/test_file.py::test_name", "-v"])
        assert is_valid
        assert reason == "single_test_allowed"

    def test_single_test_with_x_flag(self):
        """Single test E2E command with -x is also valid."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/e2e/test_file.py::test_name", "-x", "-v"])
        assert is_valid
        assert reason == "single_test_allowed"

    def test_multi_test_requires_x_flag(self):
        """Multi-test E2E command fails if -x missing."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/e2e/test_file.py", "-v"])
        assert not is_valid
        assert reason == "multi_test_missing_flag"

    def test_multi_test_accepts_x_flag(self):
        """Multi-test E2E with -x passes validation."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/e2e/test_file.py", "-x", "-v"])
        assert is_valid
        assert reason == "multi_test_with_flag"

    def test_multi_test_accepts_maxfail_flag(self):
        """Multi-test E2E with --maxfail=1 passes validation."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/e2e/test_file.py", "--maxfail=1", "-v"])
        assert is_valid
        assert reason == "multi_test_with_flag"

    def test_unit_pytest_no_special_validation(self):
        """Unit pytest command not validated as E2E."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/unit/test_file.py", "-v"])
        assert is_valid
        assert reason == "not_e2e_pytest"

    def test_non_pytest_no_special_validation(self):
        """Non-pytest command not validated as E2E."""
        is_valid, reason = validate_e2e_command(["python", "script.py"])
        assert is_valid
        assert reason == "not_e2e_pytest"

    def test_e2e_directory_multi_test_requires_x(self):
        """E2E directory target requires -x as multi-test."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/e2e/", "-v"])
        assert not is_valid
        assert reason == "multi_test_missing_flag"

    def test_e2e_directory_with_x_flag(self):
        """E2E directory target with -x passes validation."""
        is_valid, reason = validate_e2e_command(["pytest", "tests/e2e/", "-x", "-v"])
        assert is_valid
        assert reason == "multi_test_with_flag"


class TestExitCodePreservation:
    """Test that various exit codes are preserved."""

    def test_exit_code_1(self):
        """Exit code 1 is preserved."""
        exit_code, _, _ = run_gate(10, ["python3", "-c", "import sys; sys.exit(1)"])
        assert exit_code == 1

    def test_exit_code_2(self):
        """Exit code 2 is preserved."""
        exit_code, _, _ = run_gate(10, ["python3", "-c", "import sys; sys.exit(2)"])
        assert exit_code == 2

    def test_exit_code_127(self):
        """Exit code 127 is preserved."""
        exit_code, _, _ = run_gate(10, ["python3", "-c", "import sys; sys.exit(127)"])
        assert exit_code == 127


class TestTimeoutBehavior:
    """Test timeout-specific behavior."""

    def test_timeout_flag_set(self):
        """Timeout flag is set when timeout occurs."""
        _, _, timed_out = run_gate(1, ["sleep", "5"])
        assert timed_out is True

    def test_no_timeout_flag_on_success(self):
        """Timeout flag is false on successful completion."""
        _, _, timed_out = run_gate(10, ["python3", "-c", "pass"])
        assert timed_out is False

    def test_no_timeout_flag_on_failure(self):
        """Timeout flag is false when command exits nonzero normally."""
        _, _, timed_out = run_gate(10, ["python3", "-c", "import sys; sys.exit(1)"])
        assert timed_out is False

    def test_timeout_exit_code_is_124(self):
        """Timeout always returns exit code 124."""
        exit_code, _, timed_out = run_gate(1, ["sleep", "3"])
        assert exit_code == 124
        assert timed_out is True


class TestNoExternalDependencies:
    """Verify no external dependencies are required."""

    def test_script_imports_stdlib_only(self):
        """Script uses only stdlib imports."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "ci" / "e2e_gate.py"
        script_content = script_path.read_text()

        # Extract import lines
        import_lines = [line for line in script_content.split('\n') if line.strip().startswith('import ') or line.strip().startswith('from ')]

        # Allowed stdlib modules
        allowed_modules = {'subprocess', 'sys', 'time', 'pathlib', 'unittest'}

        for line in import_lines:
            # Extract module name
            if 'import' in line and 'from' not in line:
                module = line.replace('import', '').strip().split()[0]
                assert module in allowed_modules, f"Non-stdlib module found: {module}"
            elif 'from' in line:
                module = line.replace('from', '').strip().split()[0]
                assert module in allowed_modules, f"Non-stdlib module found: {module}"


class TestIntegration:
    """Integration tests for full gate operation."""

    def test_gate_with_single_e2e_pytest_command(self):
        """Gate works with single E2E pytest command."""
        test_argv = [
            "e2e_gate.py",
            "--timeout", "90",
            "--",
            "pytest", "tests/e2e/test_file.py::test_name",
            "-v", "--tb=short"
        ]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 90
            assert len(command) == 4  # pytest, target, -v, --tb=short

            # Validate command
            is_valid, reason = validate_e2e_command(command)
            assert is_valid

    def test_gate_with_multi_e2e_pytest_command_with_x(self):
        """Gate accepts multi-test E2E pytest with -x."""
        test_argv = [
            "e2e_gate.py",
            "--timeout", "180",
            "--",
            "pytest", "tests/e2e/test_file.py",
            "-x", "-v", "--tb=short"
        ]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 180

            # Validate command
            is_valid, reason = validate_e2e_command(command)
            assert is_valid

    def test_gate_rejects_multi_e2e_pytest_without_x(self):
        """Gate rejects multi-test E2E pytest without -x."""
        test_argv = [
            "e2e_gate.py",
            "--timeout", "180",
            "--",
            "pytest", "tests/e2e/test_file.py",
            "-v", "--tb=short"
        ]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()

            # Validate command
            is_valid, reason = validate_e2e_command(command)
            assert not is_valid
            assert reason == "multi_test_missing_flag"

    def test_timeout_value_boundary(self):
        """Very large timeout value is accepted."""
        test_argv = ["e2e_gate.py", "--timeout", "999999", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 999999

    def test_command_with_equals_signs(self):
        """Command with = signs (pytest args) parsed correctly."""
        test_argv = [
            "e2e_gate.py", "--timeout", "90", "--",
            "pytest", "tests/e2e/test_file.py::test_name",
            "--tb=short", "-v"
        ]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert "--tb=short" in command
