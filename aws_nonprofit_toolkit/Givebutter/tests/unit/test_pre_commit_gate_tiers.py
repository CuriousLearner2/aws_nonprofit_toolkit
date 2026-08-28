"""Tests for the simplified three-tier commit gate."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.pre_commit_gate import detect_change_tier, get_relevant_e2e_tests_for_tier3


class TestTierDetection:
    """Test tier classification based on changed files."""

    def test_tier1_docs_only(self):
        """Docs-only changes are Tier 1."""
        assert detect_change_tier(["docs/README.md", "docs/OPERATORS.md"]) == 1

    def test_tier1_tests_only(self):
        """Tests-only changes are Tier 1."""
        assert detect_change_tier([
            "tests/unit/test_foo.py",
            "tests/integration/test_bar.py",
            "tests/e2e/test_baz.py",
        ]) == 1

    def test_tier1_tooling_only(self):
        """Tooling-only changes are Tier 1."""
        assert detect_change_tier([
            ".claude/skills/householder-debug/SKILL.md",
            ".github/workflows/ci.yml",
        ]) == 1

    def test_tier1_markdown_outside_scripts(self):
        """Markdown files outside scripts/ are Tier 1."""
        assert detect_change_tier(["README.md", "CHANGELOG.md"]) == 1

    def test_tier2_normal_product(self):
        """Normal product changes are Tier 2."""
        assert detect_change_tier([
            "scripts/householder/normalizations_service.py",
            "tests/unit/test_normalizations_service.py",
        ]) == 2

    def test_tier2_ci_tooling(self):
        """CI/tooling changes are Tier 2."""
        assert detect_change_tier(["scripts/ci/check_lane_scope.py"]) == 2

    def test_tier3_export_service(self):
        """Export service changes are Tier 3."""
        assert detect_change_tier([
            "scripts/householder/export_preview_service.py",
            "tests/unit/test_export_preview_service.py",
        ]) == 3

    def test_tier3_readiness_service(self):
        """Readiness service changes are Tier 3."""
        assert detect_change_tier(["scripts/householder/readiness_service.py"]) == 3

    def test_tier3_database_models(self):
        """Database model changes are Tier 3."""
        assert detect_change_tier(["scripts/householder/database_models.py"]) == 3

    def test_tier3_write_repository(self):
        """Database write repository changes are Tier 3."""
        assert detect_change_tier(["scripts/householder/database_write_repository.py"]) == 3

    def test_tier3_approval_service(self):
        """Approval service changes are Tier 3."""
        assert detect_change_tier(["scripts/householder/approval_service.py"]) == 3

    def test_tier3_service_contracts(self):
        """Service contracts changes are Tier 3."""
        assert detect_change_tier(["scripts/householder/service_contracts.py"]) == 3

    def test_tier3_migration_files(self):
        """Migration files are Tier 3."""
        assert detect_change_tier(["migrations/0042_add_column.sql"]) == 3

    def test_mixed_files_inherit_highest_tier(self):
        """Mixed files inherit the highest tier."""
        assert detect_change_tier([
            "docs/README.md",  # Tier 1
            "tests/unit/test_foo.py",  # Tier 1
            "scripts/householder/export_preview_service.py",  # Tier 3
        ]) == 3

    def test_unknown_script_files_conservative(self):
        """Unknown script files default to Tier 2 (conservative)."""
        assert detect_change_tier([
            "scripts/householder/unknown_new_service.py"
        ]) == 2

    def test_tier2_with_tier1_stays_tier2(self):
        """Mixed Tier 2 + Tier 1 → Tier 2."""
        assert detect_change_tier([
            "docs/README.md",  # Tier 1
            "scripts/uploader/app.py",  # Tier 2
        ]) == 2


class TestE2EMappingForTier3:
    """Test E2E lane selection for Tier 3 changes."""

    def test_export_preview_service_maps_to_export_tests(self):
        """export_preview_service.py maps to relevant E2E tests."""
        e2e_tests = get_relevant_e2e_tests_for_tier3(["scripts/householder/export_preview_service.py"])
        assert "tests/e2e/test_validation_export_blocking.py" in e2e_tests
        assert "tests/e2e/test_export_recent_exports_refresh.py" in e2e_tests

    def test_readiness_service_maps_to_readiness_tests(self):
        """readiness_service.py maps to relevant E2E tests."""
        e2e_tests = get_relevant_e2e_tests_for_tier3(["scripts/householder/readiness_service.py"])
        assert "tests/e2e/test_validation_export_blocking.py" in e2e_tests

    def test_database_models_uses_full_e2e(self):
        """database_models.py has no safe mapping; use full E2E."""
        e2e_tests = get_relevant_e2e_tests_for_tier3(["scripts/householder/database_models.py"])
        assert e2e_tests == []  # Empty list signals full E2E suite

    def test_database_write_repository_uses_full_e2e(self):
        """database_write_repository.py has no safe mapping; use full E2E."""
        e2e_tests = get_relevant_e2e_tests_for_tier3(["scripts/householder/database_write_repository.py"])
        assert e2e_tests == []  # Empty list signals full E2E suite

    def test_mixed_tier3_with_unmapped_uses_full_e2e(self):
        """If any Tier 3 file has no mapping, use full E2E (conservative)."""
        e2e_tests = get_relevant_e2e_tests_for_tier3([
            "scripts/householder/export_preview_service.py",  # Has mapping
            "scripts/householder/database_models.py",  # No mapping
        ])
        assert e2e_tests == []  # Conservative: full E2E

    def test_multiple_mapped_files_union_tests(self):
        """Multiple mapped files union their E2E test files."""
        e2e_tests = get_relevant_e2e_tests_for_tier3([
            "scripts/householder/export_preview_service.py",
            "scripts/householder/readiness_service.py",
        ])
        assert "tests/e2e/test_validation_export_blocking.py" in e2e_tests
        assert "tests/e2e/test_export_recent_exports_refresh.py" in e2e_tests

    def test_no_tier3_files_returns_empty(self):
        """Non-Tier3 files return empty E2E list."""
        e2e_tests = get_relevant_e2e_tests_for_tier3([
            "docs/README.md",
            "scripts/householder/normalizations_service.py",
        ])
        assert e2e_tests == []


class TestTierBehavior:
    """Test that tier detection affects gate behavior correctly."""

    def test_tier1_prints_no_reviewer_required_message(self):
        """Tier 1 should print that no reviewer is required."""
        from scripts.ci.pre_commit_gate import print_tier_requirements
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            print_tier_requirements(1)
            output = buffer.getvalue()
            assert "no reviewer required" in output
            assert "Tier 1" in output
        finally:
            sys.stdout = old_stdout

    def test_tier2_prints_reviewer_workflow_message(self):
        """Tier 2 should print that Reviewer must be run."""
        from scripts.ci.pre_commit_gate import print_tier_requirements
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            print_tier_requirements(2)
            output = buffer.getvalue()
            assert "Tier 2" in output
            assert "Reviewer must be run" in output
            assert "Breaker" not in output
        finally:
            sys.stdout = old_stdout

    def test_tier3_prints_reviewer_and_breaker_workflow_message(self):
        """Tier 3 should print that both Reviewer and Breaker must be run."""
        from scripts.ci.pre_commit_gate import print_tier_requirements
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            print_tier_requirements(3)
            output = buffer.getvalue()
            assert "Tier 3" in output
            assert "Reviewer" in output
            assert "Breaker" in output
            assert "before pushing" in output
        finally:
            sys.stdout = old_stdout
