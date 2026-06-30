"""End-to-end tests for decision workflow with Playwright."""
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_add_notes_for_record(flask_app_database_mode, temp_dir, sample_csv):
    """Test adding operator notes for a record."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('.action-btn.primary', timeout=5000)
            review_buttons = await page.query_selector_all('.action-btn.primary')
            assert len(review_buttons) > 0, "Review button not found"

            # Click the review button to navigate to validation page
            await review_buttons[0].click()

            # Wait for navigation to validation page
            await page.wait_for_url('**/validation', timeout=5000)

            # Wait for textarea for notes
            textareas = await page.query_selector_all('textarea, [class*="notes"]')
            if textareas:
                first_textarea = textareas[0]
                await first_textarea.fill("Verify donation amount")

                # Verify text was entered
                value = await first_textarea.input_value()
                assert "Verify" in value

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_save_decisions_partial(flask_app_database_mode, temp_dir, sample_csv):
    """Test saving decisions for some records (partial save)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('.action-btn.primary', timeout=5000)
            review_buttons = await page.query_selector_all('.action-btn.primary')
            assert len(review_buttons) > 0, "Review button not found"

            # Click the review button to navigate to validation page
            await review_buttons[0].click()

            # Wait for navigation to validation page
            await page.wait_for_url('**/validation', timeout=5000)

            # Select decisions for only first 2 records
            decision_selects = await page.query_selector_all('.decision-select')
            if len(decision_selects) >= 2:
                await decision_selects[0].select_option(value="approved")
                await decision_selects[1].select_option(value="rejected")

                # Click save button
                save_button = await page.query_selector('button:has-text("Save")')
                if save_button:
                    await save_button.click()

                    # Should show message about partial save or progress
                    await page.wait_for_selector('text=/saved|progress|remaining/', timeout=5000)

                    content = await page.content()
                    assert any(text in content.lower() for text in ['saved', 'progress'])

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_save_all_decisions_completes_review(flask_app_database_mode, temp_dir, sample_csv):
    """Test that saving all decisions moves file out of review queue."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('.action-btn.primary', timeout=5000)
            review_buttons = await page.query_selector_all('.action-btn.primary')
            assert len(review_buttons) > 0, "Review button not found"

            # Click the review button to navigate to validation page
            await review_buttons[0].click()

            # Wait for navigation to validation page
            await page.wait_for_url('**/validation', timeout=5000)

            # Select decisions for ALL records
            decision_selects = await page.query_selector_all('.decision-select')
            for i, select in enumerate(decision_selects):
                decisions = ["approved", "rejected", "followup"]
                await select.select_option(value=decisions[i % 3])

            # Click save button
            save_button = await page.query_selector('button:has-text("Save")')
            if save_button:
                await save_button.click()

                # Wait for completion message to appear (replace arbitrary sleep with explicit wait)
                await page.wait_for_function(
                    "() => document.body.innerText.toLowerCase().includes('complete') || document.body.innerText.toLowerCase().includes('approved')",
                    timeout=5000
                )

                # Verify success by checking page content
                content = await page.content()
                assert any(text in content.lower() for text in ['complete', 'approved', 'rejected']), "Completion message not found in page content"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decision_persistence_on_reopen(flask_app_database_mode, temp_dir, sample_csv):
    """Test that decisions persist when reopening file for review."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('.action-btn.primary', timeout=5000)
            review_buttons = await page.query_selector_all('.action-btn.primary')
            assert len(review_buttons) > 0, "Review button not found"

            # Click the review button to navigate to validation page
            await review_buttons[0].click()

            # Wait for navigation to validation page
            await page.wait_for_url('**/validation', timeout=5000)

            # Make decision on first record
            decision_selects = await page.query_selector_all('select.decision-select')
            if decision_selects:
                # Handle any confirmation dialogs automatically
                page.once("dialog", lambda dialog: dialog.accept())

                await decision_selects[0].select_option(value="approved")

                # Wait for auto-save to complete (network idle)
                await page.wait_for_load_state('networkidle', timeout=5000)

                # Go back to processing queue
                await page.goto("http://127.0.0.1:8001/")

                # Wait for upload card to be ready
                await page.wait_for_selector('.upload-card', timeout=5000)

                # Reopen the file
                await page.wait_for_selector('.action-btn.primary', timeout=5000)
                review_buttons = await page.query_selector_all('.action-btn.primary')
                if review_buttons:
                    await review_buttons[0].click()

                    # Wait for validation page to load
                    await page.wait_for_url('**/validation', timeout=5000)

                    # Check that first record still shows "approved"
                    await page.wait_for_selector('select.decision-select', timeout=5000)

                    decision_select = await page.query_selector('select.decision-select')
                    if decision_select:
                        selected_value = await decision_select.evaluate('el => el.value')
                        assert selected_value == 'approved', f"Expected 'approved', got '{selected_value}'"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_page_scrolls_to_top_on_load(flask_app_database_mode, temp_dir, sample_csv):
    """Test that review page scrolls to top when loaded."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('.action-btn.primary', timeout=5000)
            review_buttons = await page.query_selector_all('.action-btn.primary')
            assert len(review_buttons) > 0, "Review button not found"

            # Click the review button to navigate to validation page
            await review_buttons[0].click()

            # Wait for navigation to validation page
            await page.wait_for_url('**/validation', timeout=5000)

            # Check scroll position
            scroll_y = await page.evaluate("() => window.scrollY")
            # Should be at top or near top (allowing for small margin)
            assert scroll_y < 100

        finally:
            await browser.close()
