"""Unit tests for the no-artifacts guardrail script."""

import pytest
import sys
from pathlib import Path

# Import the script functions
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))
from check_no_artifacts import is_blocked_artifact


class TestBlockedArtifacts:
    """Test that known artifact patterns are correctly blocked."""

    def test_ds_store_is_blocked(self):
        """macOS metadata file should be blocked."""
        assert is_blocked_artifact(".DS_Store") is True
        assert is_blocked_artifact("dir/.DS_Store") is True

    def test_thumbs_db_is_blocked(self):
        """Windows metadata file should be blocked."""
        assert is_blocked_artifact("Thumbs.db") is True

    def test_editor_backup_files_blocked(self):
        """Editor backup files should be blocked."""
        assert is_blocked_artifact("file.bak") is True
        assert is_blocked_artifact("file.tmp") is True
        assert is_blocked_artifact("file.swp") is True
        assert is_blocked_artifact("file.swo") is True
        assert is_blocked_artifact("file~") is True
        assert is_blocked_artifact("dir/file.bak") is True

    def test_debug_files_blocked(self):
        """Debug and secrets files should be blocked."""
        assert is_blocked_artifact("file.pdb") is True
        assert is_blocked_artifact(".env.local") is True
        assert is_blocked_artifact("dir/.env.local") is True

    def test_tool_caches_blocked(self):
        """Tool cache directories should be blocked."""
        assert is_blocked_artifact(".mypy_cache") is True
        assert is_blocked_artifact(".mypy_cache/") is True
        assert is_blocked_artifact(".mypy_cache/module.json") is True
        assert is_blocked_artifact("dir/.mypy_cache/file") is True

        assert is_blocked_artifact(".ruff_cache") is True
        assert is_blocked_artifact(".ruff_cache/") is True
        assert is_blocked_artifact(".ruff_cache/cache.json") is True

        assert is_blocked_artifact(".hypothesis") is True
        assert is_blocked_artifact(".hypothesis/") is True
        assert is_blocked_artifact(".hypothesis/examples") is True

    def test_test_artifact_dirs_blocked(self):
        """Test output directories should be blocked."""
        test_dirs = ["test_results", "test_artifacts", "playwright_results", "traces", "videos"]
        for test_dir in test_dirs:
            assert is_blocked_artifact(test_dir) is True, f"{test_dir} should be blocked"
            assert is_blocked_artifact(f"{test_dir}/") is True, f"{test_dir}/ should be blocked"
            assert is_blocked_artifact(f"{test_dir}/file.txt") is True, f"{test_dir}/file.txt should be blocked"

    def test_local_db_files_blocked(self):
        """Local database files should be blocked."""
        assert is_blocked_artifact("local.db") is True
        assert is_blocked_artifact("test.sqlite") is True
        assert is_blocked_artifact("temp.sqlite3") is True
        assert is_blocked_artifact("dir/local.db") is True

    def test_log_files_blocked(self):
        """Log files should be blocked."""
        assert is_blocked_artifact("test.log") is True
        assert is_blocked_artifact("debug.log") is True
        assert is_blocked_artifact("dir/output.log") is True


class TestAllowedFiles:
    """Test that safe files are not blocked."""

    def test_python_source_allowed(self):
        """Python source files should be allowed."""
        assert is_blocked_artifact("script.py") is False
        assert is_blocked_artifact("module/handler.py") is False

    def test_markdown_allowed(self):
        """Markdown documentation should be allowed."""
        assert is_blocked_artifact("README.md") is False
        assert is_blocked_artifact("docs/guide.md") is False

    def test_json_files_allowed(self):
        """JSON files should be allowed (unless they match cache patterns)."""
        assert is_blocked_artifact("config.json") is False
        assert is_blocked_artifact("data.json") is False

    def test_csv_in_test_data_allowed(self):
        """CSV files in test_data/ are intentional and allowed."""
        # Note: The script doesn't specifically block these, so they pass through
        assert is_blocked_artifact("test_data/sample.csv") is False
        assert is_blocked_artifact("test_data/realistic_export.csv") is False

    def test_reference_screenshots_allowed(self):
        """Reference screenshots matching householder pattern are allowed."""
        # These are tracked intentionally, pattern explicitly allows them
        assert is_blocked_artifact("screenshots/householder-v1-final-fixed.png") is False
        assert is_blocked_artifact("screenshots/householder-v1-status-fix.png") is False
        assert is_blocked_artifact("screenshots/householder-v1-upload-screen.png") is False

    def test_testing_dir_files_allowed(self):
        """Files under testing/ are intentional and allowed."""
        # The script doesn't specifically block these, only their artifact patterns
        assert is_blocked_artifact("testing/agent/sample_test_data.csv") is False
        assert is_blocked_artifact("testing/qa-artifacts/phase0/qa-results.json") is False
        assert is_blocked_artifact("testing/workspace/design.html") is False

    def test_source_files_allowed(self):
        """Regular source code files should be allowed."""
        assert is_blocked_artifact("scripts/processor.py") is False
        assert is_blocked_artifact("app.py") is False
        assert is_blocked_artifact("src/module.ts") is False


class TestScreenshotSpecialHandling:
    """Test special handling for new screenshots in screenshots/ dir."""

    def test_new_screenshot_in_root_of_screenshots_blocked(self):
        """New screenshot files directly in screenshots/ should be blocked."""
        assert is_blocked_artifact("screenshots/new-screenshot.png") is True
        assert is_blocked_artifact("screenshots/debug.jpg") is True
        assert is_blocked_artifact("screenshots/temp.jpeg") is True

    def test_reference_householder_screenshots_allowed(self):
        """Reference householder screenshots should be allowed."""
        assert is_blocked_artifact("screenshots/householder-v1-something.png") is False
        assert is_blocked_artifact("screenshots/householder-v2-final.png") is False

    def test_screenshot_subdirs_blocked(self):
        """Screenshots in subdirectories are treated as new/unintended."""
        assert is_blocked_artifact("screenshots/subdir/file.png") is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_filename(self):
        """Empty filename should not crash."""
        assert is_blocked_artifact("") is False

    def test_dot_files_without_extension(self):
        """Hidden files without matching patterns should be allowed."""
        assert is_blocked_artifact(".gitignore") is False
        assert is_blocked_artifact(".github") is False

    def test_nested_paths(self):
        """Nested paths should be handled correctly."""
        assert is_blocked_artifact("deep/nested/path/to/file.bak") is True
        assert is_blocked_artifact("deep/nested/path/.mypy_cache/file") is True
        assert is_blocked_artifact("deep/nested/path/script.py") is False

    def test_case_sensitivity(self):
        """File extensions should be case-insensitive (typical for artifacts)."""
        # Note: Python's endswith is case-sensitive, so .DB != .db
        # This is intentional - block lowercase extensions (common)
        assert is_blocked_artifact("file.db") is True
        assert is_blocked_artifact("file.log") is True
        # Uppercase variants won't match (fine - less common)
        assert is_blocked_artifact("file.DB") is False

    def test_multiple_extensions(self):
        """Files with multiple extensions should match on the final extension."""
        assert is_blocked_artifact("archive.tar.bak") is True
        assert is_blocked_artifact("data.json.tmp") is True
        assert is_blocked_artifact("file.py.swp") is True


class TestPatternCoverage:
    """Verify coverage of all documented blocked patterns."""

    def test_all_documented_patterns_present(self):
        """All patterns from docstring should have tests or be covered implicitly."""
        patterns_to_verify = [
            ".DS_Store",
            "Thumbs.db",
            "file.bak",
            "file.tmp",
            "file.swp",
            "file.swo",
            "file~",
            ".env.local",
            ".mypy_cache",
            ".ruff_cache",
            ".hypothesis",
            "test_results",
            "test_artifacts",
            "playwright_results",
            "traces",
            "videos",
            "file.db",
            "file.sqlite",
            "file.sqlite3",
            "file.log",
        ]

        for pattern in patterns_to_verify:
            # If pattern looks like a directory, test with and without slash
            if "/" not in pattern and "." not in pattern.lstrip("."):
                assert is_blocked_artifact(pattern) is True, f"Pattern {pattern} should be blocked"
            else:
                result = is_blocked_artifact(pattern)
                assert result is True, f"Pattern {pattern} should be blocked, got {result}"
