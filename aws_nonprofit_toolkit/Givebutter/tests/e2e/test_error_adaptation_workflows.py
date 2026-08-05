import pytest


@pytest.mark.e2e
def test_error_adaptation_browser_workflows_are_exercised_by_browser_gate():
    """The real-browser gate owns server/browser setup for these journeys."""
    pytest.importorskip("playwright")
    pytest.skip("Executed by the configured real-browser E2E harness")
