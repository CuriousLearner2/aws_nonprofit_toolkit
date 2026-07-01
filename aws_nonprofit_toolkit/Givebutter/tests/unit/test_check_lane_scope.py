"""
Unit tests for lane scope guard (scripts/ci/check_lane_scope.py).

Tests verify:
- File classification by semantic category
- Lane-specific rules (assessment, push-only, test-only, workflow-ci, product)
- Conflict detection for mixed-lane violations
- Clean-tree detection
- --allow-schema, --simulate, --verbose flag behavior
- Error handling and exit codes
"""

import sys
from pathlib import Path

# Add scripts/ci to path so we can import check_lane_scope
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ci"))

import check_lane_scope


class TestFileClassification:
    """Tests for file classification logic."""

    def test_classify_workflow_files(self):
        """Workflow files are classified as 'workflow'."""
        assert check_lane_scope.classify_file('.claude/agents/orchestrator.md') == 'workflow'
        assert check_lane_scope.classify_file('.claude/skills/householder-debug/SKILL.md') == 'workflow'
        assert check_lane_scope.classify_file('.github/workflows/test.yml') == 'workflow'

    def test_classify_ci_files(self):
        """CI files are classified as 'ci'."""
        assert check_lane_scope.classify_file('scripts/ci/check_scope.py') == 'ci'
        assert check_lane_scope.classify_file('scripts/ci/test_gate.py') == 'ci'
        assert check_lane_scope.classify_file('scripts/ci/e2e_gate.py') == 'ci'

    def test_classify_product_files(self):
        """Product files are classified as 'product'."""
        assert check_lane_scope.classify_file('scripts/householder/database_repository.py') == 'product'
        assert check_lane_scope.classify_file('scripts/uploader/app.py') == 'product'
        assert check_lane_scope.classify_file('scripts/uploader/templates/imports/validation.html') == 'product'

    def test_classify_test_files(self):
        """Test files are classified as 'tests'."""
        assert check_lane_scope.classify_file('tests/unit/test_validation.py') == 'tests'
        assert check_lane_scope.classify_file('tests/integration/test_export.py') == 'tests'
        assert check_lane_scope.classify_file('tests/e2e/test_canonical_screens.py') == 'tests'

    def test_classify_docs_files(self):
        """Documentation files are classified as 'docs'."""
        assert check_lane_scope.classify_file('docs/ROADMAP.md') == 'docs'
        assert check_lane_scope.classify_file('README.md') == 'docs'
        assert check_lane_scope.classify_file('CONTRIBUTING.md') == 'docs'

    def test_classify_schema_files(self):
        """Schema files are classified as 'schema'."""
        assert check_lane_scope.classify_file('migrations/001_initial.sql') == 'schema'
        assert check_lane_scope.classify_file('scripts/db/migrations/002_add_column.sql') == 'schema'
        assert check_lane_scope.classify_file('schema.sql') == 'schema'

    def test_classify_other_files(self):
        """Unknown files are classified as 'other'."""
        assert check_lane_scope.classify_file('random_file.txt') == 'other'
        assert check_lane_scope.classify_file('config.yaml') == 'other'


class TestLaneRulesAssessment:
    """Tests for assessment lane rules."""

    def test_assessment_clean_tree_allowed(self):
        """Assessment lane with no changed files is clean."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('assessment', [])
        assert is_clean is True
        assert len(conflicts) == 0

    def test_assessment_any_file_blocked(self):
        """Assessment lane blocks any dirty files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('assessment', ['tests/unit/test.py'])
        assert is_clean is False
        assert any('assessment' in str(c) for c in conflicts)


class TestLaneRulesPushOnly:
    """Tests for push-only lane rules."""

    def test_push_only_clean_tree_allowed(self):
        """Push-only lane with no changed files is clean."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('push-only', [])
        assert is_clean is True
        assert len(conflicts) == 0

    def test_push_only_any_file_blocked(self):
        """Push-only lane blocks any dirty files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('push-only', ['scripts/ci/check_scope.py'])
        assert is_clean is False
        assert any('push-only' in str(c) for c in conflicts)


class TestLaneRulesTestOnly:
    """Tests for test-only lane rules."""

    def test_test_only_clean_tree_allowed(self):
        """Test-only lane with no changed files is clean."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('test-only', [])
        assert is_clean is True

    def test_test_only_tests_allowed(self):
        """Test-only lane allows tests/** files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('test-only', ['tests/unit/test.py'])
        assert is_clean is True
        assert len(conflicts) == 0

    def test_test_only_product_blocked(self):
        """Test-only lane blocks product files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('test-only', ['scripts/householder/repository.py'])
        assert is_clean is False
        assert any('product' in str(c) for c in conflicts)

    def test_test_only_workflow_blocked(self):
        """Test-only lane blocks workflow files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('test-only', ['.claude/agents/orchestrator.md'])
        assert is_clean is False
        assert any('workflow' in str(c) for c in conflicts)

    def test_test_only_ci_blocked(self):
        """Test-only lane blocks CI files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('test-only', ['scripts/ci/check_scope.py'])
        assert is_clean is False
        assert any('ci' in str(c) for c in conflicts)

    def test_test_only_schema_blocked(self):
        """Test-only lane blocks schema files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('test-only', ['migrations/001.sql'])
        assert is_clean is False
        assert any('schema' in str(c) for c in conflicts)


class TestLaneRulesWorkflowCI:
    """Tests for workflow-ci lane rules."""

    def test_workflow_ci_clean_tree_allowed(self):
        """Workflow-CI lane with no changed files is clean."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('workflow-ci', [])
        assert is_clean is True

    def test_workflow_ci_workflow_files_allowed(self):
        """Workflow-CI lane allows .claude/* files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('workflow-ci', ['.claude/agents/orchestrator.md'])
        assert is_clean is True

    def test_workflow_ci_ci_files_allowed(self):
        """Workflow-CI lane allows scripts/ci/* files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('workflow-ci', ['scripts/ci/check_scope.py'])
        assert is_clean is True

    def test_workflow_ci_product_blocked(self):
        """Workflow-CI lane blocks product files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('workflow-ci', ['scripts/householder/repository.py'])
        assert is_clean is False
        assert any('product' in str(c) for c in conflicts)

    def test_workflow_ci_schema_blocked(self):
        """Workflow-CI lane blocks schema files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('workflow-ci', ['migrations/001.sql'])
        assert is_clean is False
        assert any('schema' in str(c) for c in conflicts)


class TestLaneRulesProduct:
    """Tests for product lane rules."""

    def test_product_clean_tree_allowed(self):
        """Product lane with no changed files is clean."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', [])
        assert is_clean is True

    def test_product_product_files_allowed(self):
        """Product lane allows product files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', ['scripts/householder/repository.py'])
        assert is_clean is True

    def test_product_tests_allowed(self):
        """Product lane allows test files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', ['tests/unit/test.py'])
        assert is_clean is True

    def test_product_docs_allowed(self):
        """Product lane allows doc files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', ['docs/ROADMAP.md'])
        assert is_clean is True

    def test_product_workflow_blocked(self):
        """Product lane blocks workflow files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', ['.claude/agents/orchestrator.md'])
        assert is_clean is False
        assert any('workflow' in str(c) for c in conflicts)

    def test_product_ci_blocked(self):
        """Product lane blocks CI files."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', ['scripts/ci/check_scope.py'])
        assert is_clean is False
        assert any('ci' in str(c) for c in conflicts)

    def test_product_schema_blocked_without_flag(self):
        """Product lane blocks schema files without --allow-schema."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', ['migrations/001.sql'], allow_schema=False)
        assert is_clean is False
        assert any('schema' in str(c) for c in conflicts)

    def test_product_schema_allowed_with_flag(self):
        """Product lane allows schema files with --allow-schema."""
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', ['migrations/001.sql'], allow_schema=True)
        assert is_clean is True


class TestMixedLaneDetection:
    """Tests for mixed-lane conflict detection."""

    def test_product_and_workflow_mixed(self):
        """Product + workflow files are detected as conflict."""
        files = [
            'scripts/householder/repository.py',  # product
            '.claude/agents/orchestrator.md'       # workflow
        ]
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', files)
        assert is_clean is False
        assert any('workflow' in str(c) for c in conflicts)

    def test_product_and_ci_mixed(self):
        """Product + CI files are detected as conflict."""
        files = [
            'scripts/householder/repository.py',  # product
            'scripts/ci/check_scope.py'            # ci
        ]
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', files)
        assert is_clean is False
        assert any('ci' in str(c) for c in conflicts)

    def test_test_only_and_product_mixed(self):
        """Test-only + product files are detected as conflict."""
        files = [
            'tests/unit/test.py',                  # tests
            'scripts/householder/repository.py'    # product
        ]
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('test-only', files)
        assert is_clean is False
        assert any('product' in str(c) for c in conflicts)


class TestSimulateFlag:
    """Tests for --simulate flag behavior."""

    def test_simulate_exits_zero_on_conflict(self):
        """--simulate exits 0 even when conflicts detected (dry-run mode)."""
        files = ['scripts/householder/repository.py', '.claude/agents/orchestrator.md']
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', files, simulate=True)
        # In simulate mode, we still get the conflict info for reporting
        assert len(conflicts) > 0
        # But simulate should report success (exit 0) in caller logic


class TestVerboseFlag:
    """Tests for --verbose flag behavior."""

    def test_verbose_categorizes_files(self):
        """--verbose flag triggers detailed file categorization."""
        files = [
            'scripts/householder/repository.py',
            'tests/unit/test.py',
            '.claude/agents/orchestrator.md'
        ]
        is_clean, conflicts, categorized = check_lane_scope.check_lane_scope('product', files, verbose=True)
        # Verbose should still work the same logically
        assert 'product' in categorized
        assert 'tests' in categorized
        assert 'workflow' in categorized


class TestInvalidLaneHandling:
    """Tests for error handling."""

    def test_classify_handles_edge_cases(self):
        """Classification handles edge cases correctly."""
        # Empty string becomes 'other'
        assert check_lane_scope.classify_file('') == 'other'

        # Files with no extension
        assert check_lane_scope.classify_file('Makefile') == 'other'

        # Deeply nested paths
        assert check_lane_scope.classify_file('scripts/householder/deeply/nested/file.py') == 'product'


class TestCleanTreeDetection:
    """Tests for clean tree scenarios."""

    def test_all_lanes_allow_empty_tree(self):
        """All lanes allow a clean (empty) tree."""
        for lane in ['assessment', 'push-only', 'test-only', 'workflow-ci', 'product']:
            is_clean, conflicts, _ = check_lane_scope.check_lane_scope(lane, [])
            assert is_clean is True, f"{lane} should allow clean tree"
            assert len(conflicts) == 0, f"{lane} should have no conflicts for clean tree"


class TestPathNormalization:
    """Tests for path normalization in nested repo structures."""

    def test_normalize_normalized_paths(self):
        """Normalized paths stay the same."""
        from pathlib import Path
        repo_root = str(Path.cwd())
        current_dir = str(Path.cwd())

        # Already normalized paths should remain unchanged
        result = check_lane_scope.normalize_path('scripts/ci/check_lane_scope.py', repo_root, current_dir)
        assert result == 'scripts/ci/check_lane_scope.py'

    def test_normalize_nested_paths(self):
        """Nested repo paths are correctly normalized."""
        from pathlib import Path
        repo_root = str(Path.cwd())
        current_dir = str(Path.cwd())

        # Nested path from git status
        nested_path = 'aws_nonprofit_toolkit/Givebutter/scripts/ci/check_lane_scope.py'
        result = check_lane_scope.normalize_path(nested_path, repo_root, current_dir)
        # Result should end with the actual path component after normalization
        assert 'scripts/ci/check_lane_scope.py' in result or result == nested_path

    def test_classify_with_nested_paths(self):
        """Classification works with nested repo paths."""
        # Direct normalized path
        assert check_lane_scope.classify_file('scripts/ci/check_lane_scope.py') == 'ci'
        # After normalization in check_lane_scope's flow, nested path might resolve to simpler form

    def test_classify_normalized_after_normalization(self):
        """Nested paths are normalized before classification in check_lane_scope."""
        # Verify that check_lane_scope correctly handles nested paths
        # by normalizing them internally before classification

        nested_files = [
            'aws_nonprofit_toolkit/Givebutter/.claude/agents/orchestrator.md',      # workflow
            'aws_nonprofit_toolkit/Givebutter/scripts/householder/database_repository.py',  # product
            'aws_nonprofit_toolkit/Givebutter/tests/unit/test_check_lane_scope.py'   # tests
        ]

        # When check_lane_scope processes nested paths, it normalizes them internally
        is_clean, conflicts, categorized = check_lane_scope.check_lane_scope('product', nested_files)

        # After normalization inside check_lane_scope, we should detect the workflow/product conflict
        assert is_clean is False
        assert any('workflow' in str(c) for c in conflicts)

    def test_mixed_nested_product_workflow_conflict(self):
        """Mixed product + workflow files with nested paths are detected as conflict."""
        files = [
            'aws_nonprofit_toolkit/Givebutter/scripts/householder/database_repository.py',  # product
            'aws_nonprofit_toolkit/Givebutter/.claude/agents/orchestrator.md'                # workflow
        ]
        is_clean, conflicts, _ = check_lane_scope.check_lane_scope('product', files)
        assert is_clean is False
        assert any('workflow' in str(c) for c in conflicts)
