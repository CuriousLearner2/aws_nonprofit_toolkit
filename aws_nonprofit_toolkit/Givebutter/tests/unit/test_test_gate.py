"""Unit tests for the test_gate.py pytest wrapper."""

import pytest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the script functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))
from test_gate import parse_arguments, run_gate, format_command


class TestParseArguments:
    """Test CLI argument parsing."""

    def test_valid_arguments(self):
        """Valid --timeout N -- command parsing."""
        test_argv = ["test_gate.py", "--timeout", "120", "--", "pytest", "tests/unit", "-q"]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 120
            assert command == ["pytest", "tests/unit", "-q"]

    def test_valid_arguments_with_multiple_args(self):
        """Valid arguments with many command args."""
        test_argv = ["test_gate.py", "--timeout", "300", "--", "python", "-m", "pytest", "tests/", "-v", "--tb=short"]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 300
            assert command == ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]

    def test_timeout_as_string_integer(self):
        """Timeout can be parsed as string integer."""
        test_argv = ["test_gate.py", "--timeout", "90", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 90
            assert isinstance(timeout, int)

    def test_missing_timeout_flag(self):
        """Missing --timeout flag causes exit."""
        test_argv = ["test_gate.py", "120", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_missing_timeout_value(self):
        """Missing --timeout value causes exit."""
        test_argv = ["test_gate.py", "--timeout", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_invalid_timeout_value(self):
        """Non-integer timeout value causes exit."""
        test_argv = ["test_gate.py", "--timeout", "abc", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_negative_timeout(self):
        """Negative timeout value causes exit."""
        test_argv = ["test_gate.py", "--timeout", "-5", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_zero_timeout(self):
        """Zero timeout value causes exit."""
        test_argv = ["test_gate.py", "--timeout", "0", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_missing_separator(self):
        """Missing -- separator causes exit."""
        test_argv = ["test_gate.py", "--timeout", "120", "pytest"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_missing_command_after_separator(self):
        """Missing command after -- causes exit."""
        test_argv = ["test_gate.py", "--timeout", "120", "--"]
        with patch.object(sys, "argv", test_argv):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 1

    def test_insufficient_arguments(self):
        """Too few arguments causes exit."""
        test_argv = ["test_gate.py", "--timeout"]
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
        # Use a command that exits with specific code (Python -c syntax)
        exit_code, elapsed, timed_out = run_gate(10, ["python3", "-c", "import sys; sys.exit(5)"])
        assert exit_code == 5
        assert timed_out is False

    def test_timeout_exceeded(self):
        """Command exceeding timeout returns 124."""
        # Use sleep to create a timeout scenario
        exit_code, elapsed, timed_out = run_gate(1, ["sleep", "5"])
        assert exit_code == 124
        assert timed_out is True
        # Elapsed should be approximately timeout value (1 second)
        assert elapsed >= 0.9  # Allow small timing variance

    def test_elapsed_time_tracked(self):
        """Elapsed time is tracked correctly."""
        # Quick command should have small elapsed time
        exit_code, elapsed, timed_out = run_gate(30, ["python3", "-c", "pass"])
        assert elapsed >= 0
        assert elapsed < 2  # Should be very fast

    def test_long_running_command_within_timeout(self):
        """Long-running command within timeout completes."""
        # Sleep for 0.5 seconds with 2 second timeout
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
        result = format_command(["pytest", "tests/unit", "-v", "--tb=short"])
        assert result == "pytest tests/unit -v --tb=short"

    def test_command_with_spaces_in_args(self):
        """Arguments are space-separated."""
        result = format_command(["python", "-c", "print('hello')"])
        assert "python" in result
        assert "-c" in result


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
        # Read the script and verify imports
        script_path = Path(__file__).parent.parent.parent / "scripts" / "ci" / "test_gate.py"
        script_content = script_path.read_text()

        # Extract import lines
        import_lines = [line for line in script_content.split('\n') if line.strip().startswith('import ') or line.strip().startswith('from ')]

        # Allowed stdlib modules
        allowed_modules = {'subprocess', 'sys', 'time', 'argparse', 'pathlib', 'unittest'}

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

    def test_gate_with_simple_pytest_command(self):
        """Gate works with pytest command structure."""
        # This test verifies the argument parsing with a real pytest-like command
        test_argv = [
            "test_gate.py",
            "--timeout", "120",
            "--",
            "python", "-m", "pytest",
            "tests/unit",
            "-q", "--tb=short"
        ]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 120
            assert len(command) == 6
            assert command[0:2] == ["python", "-m"]

    def test_timeout_value_boundary(self):
        """Very large timeout value is accepted."""
        test_argv = ["test_gate.py", "--timeout", "999999", "--", "pytest"]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert timeout == 999999

    def test_command_with_equals_signs(self):
        """Command with = signs (pytest args) parsed correctly."""
        test_argv = [
            "test_gate.py", "--timeout", "60", "--",
            "pytest", "tests/", "--tb=short", "-v"
        ]
        with patch.object(sys, "argv", test_argv):
            timeout, command = parse_arguments()
            assert "--tb=short" in command
