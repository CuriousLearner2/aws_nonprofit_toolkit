#!/bin/bash
# Quality gate for Validation Review screen - fast integration tests only
#
# Runs the 15 integration tests from test_validation_review_workflows.py
# Expected runtime: ~2.4 seconds
#
# Exit codes:
#   0 = All tests passed
#   1 = One or more tests failed
#
# Usage:
#   ./scripts/dev/quality_gate_review_screen.sh

set -e

cd "$(dirname "$0")/../.."

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

echo "=================================="
echo "Quality Gate: Validation Review Screen"
echo "Running fast integration tests..."
echo "=================================="
echo

pytest tests/integration/test_validation_review_workflows.py -v --tb=short

echo
echo "✓ Quality gate passed"
exit 0
