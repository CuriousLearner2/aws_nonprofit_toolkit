"""E2E tests for tier identification in review interface.

Tests that PASS and FAIL tier records are correctly identified and displayed
in the validation review table.
"""
import pytest
from playwright.async_api import async_playwright


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_fail_tier_records_identified_in_ui(flask_app_database_mode):
    """Test that FAIL tier records are visually marked in the review table."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Load test page with mixed PASS/FAIL records
            await page.goto("http://127.0.0.1:8001/test-override-dialog")

            # Wait for review table
            await page.wait_for_selector('table.queue-table', timeout=5000)

            # Get page content to verify FAIL tiers are shown
            content = await page.content()

            # Should have FAIL tier markers
            assert 'FAIL' in content or 'tier-fail' in content, \
                "FAIL tier records should be visible in the table"

            # Should have PASS tier markers
            assert 'PASS' in content or 'tier-pass' in content, \
                "PASS tier records should be visible in the table"

        finally:
            await browser.close()
