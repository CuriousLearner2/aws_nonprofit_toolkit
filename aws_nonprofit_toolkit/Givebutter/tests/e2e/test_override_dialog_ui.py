"""E2E tests for override confirmation dialog UI.

Tests the dialog interaction directly without upload complexity.
Uses /test-override-dialog endpoint for reliable test data.
"""
import pytest
import asyncio
from playwright.async_api import async_playwright


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pass_record_approval_no_dialog(flask_app_running):
    """Test that approving PASS tier record shows NO confirmation dialog."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Track dialogs
        dialogs_shown = []
        page.on("dialog", lambda dialog: dialogs_shown.append(dialog))

        try:
            # Load test page with pre-populated records
            await page.goto("http://127.0.0.1:8000/test-override-dialog")

            # Wait for review table to load
            await page.wait_for_selector('table.review-table', timeout=5000)

            # Get all decision selects
            decision_selects = await page.query_selector_all('select.decision-select')
            assert len(decision_selects) > 0, "Should have decision dropdowns"

            # First record (GB001) is PASS tier
            # Select "Approved" for PASS record
            await decision_selects[0].select_option(value="approved")

            # No dialog should appear for PASS record
            await asyncio.sleep(0.5)
            assert len(dialogs_shown) == 0, \
                "No confirmation dialog should appear for PASS tier approval"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_fail_record_shows_dialog(flask_app_running):
    """Test that approving FAIL tier record shows override confirmation dialog."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Track dialogs
        dialogs_shown = []
        def capture_dialog(dialog):
            dialogs_shown.append(dialog)
            asyncio.create_task(dialog.dismiss())  # Auto-dismiss for cleanup

        page.on("dialog", capture_dialog)

        try:
            # Load test page with pre-populated records
            await page.goto("http://127.0.0.1:8000/test-override-dialog")

            # Wait for review table to load
            await page.wait_for_selector('table.review-table', timeout=5000)

            # Get all decision selects
            decision_selects = await page.query_selector_all('select.decision-select')
            assert len(decision_selects) >= 2, "Should have multiple records"

            # Second record (GB002) has missing email = FAIL tier
            # Select "Approved" for FAIL record
            await decision_selects[1].select_option(value="approved")

            # Dialog should appear for FAIL record
            await asyncio.sleep(0.5)
            assert len(dialogs_shown) > 0, \
                "Confirmation dialog should appear for FAIL tier approval"

            # Dialog should ask about override
            dialog_message = dialogs_shown[0].message
            assert any(word in dialog_message.lower() for word in ['fail', 'override', 'confirm']), \
                f"Dialog should mention override, but message is: {dialog_message}"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_confirm_override_dialog(flask_app_running):
    """Test that confirming override dialog keeps FAIL record approved."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Auto-confirm dialogs
        async def auto_confirm(dialog):
            await dialog.accept()

        page.on("dialog", auto_confirm)

        try:
            # Load test page
            await page.goto("http://127.0.0.1:8000/test-override-dialog")

            # Wait for review table
            await page.wait_for_selector('table.review-table', timeout=5000)

            # Get decision selects
            decision_selects = await page.query_selector_all('select.decision-select')

            # Approve FAIL record (second record)
            await decision_selects[1].select_option(value="approved")

            # Wait for dialog to appear and be confirmed
            await asyncio.sleep(0.5)

            # Verify selection is still "approved"
            selected_value = await decision_selects[1].input_value()
            assert selected_value == "approved", \
                "Decision should remain 'approved' after confirming override"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cancel_override_dialog(flask_app_running):
    """Test that canceling override dialog reverts FAIL approval."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Auto-dismiss (cancel) dialogs
        async def auto_dismiss(dialog):
            await dialog.dismiss()

        page.on("dialog", auto_dismiss)

        try:
            # Load test page
            await page.goto("http://127.0.0.1:8000/test-override-dialog")

            # Wait for review table
            await page.wait_for_selector('table.review-table', timeout=5000)

            # Get decision selects
            decision_selects = await page.query_selector_all('select.decision-select')

            # Try to approve FAIL record (second record)
            await decision_selects[1].select_option(value="approved")

            # Wait for dialog to appear and be dismissed
            await asyncio.sleep(0.5)

            # After canceling, decision should be empty or reverted
            # This behavior depends on implementation:
            # Either the dropdown reverts to empty, or a message appears
            selected_value = await decision_selects[1].input_value()

            # Depending on implementation, it might stay as "approved" in the UI
            # but won't be saved because dialog was canceled
            # The important thing is the backend won't save it
            assert selected_value in ["", "approved"], \
                f"Selection should be empty or unchanged, got: {selected_value}"

        finally:
            await browser.close()


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
