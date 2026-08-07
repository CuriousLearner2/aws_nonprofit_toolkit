"""End-to-end tests for decision workflow with Playwright."""
import csv
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


def _write_dense_decision_csv(temp_dir):
    csv_path = temp_dir / "dense_decision_workflow.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Donation ID",
                "Date",
                "Donor Name",
                "Email",
                "Amount",
                "Phone",
                "Address",
                "Campaign",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Donation ID": "GB201",
                "Date": "2026-05-20",
                "Donor Name": (
                    "Alexandria Montgomery-Wentworth the Third With a Very Long "
                    "Display Name for Decision Workflow Stress Coverage"
                ),
                "Email": (
                    "alexandria.montgomery.wentworth.the.third.with.a.very.long.name@gmal.com"
                ),
                "Amount": "125.00",
                "Phone": "",
                "Address": (
                    "9876 Extremely Long Example Avenue, Suite 12345, Very Long City Name, CA 94107"
                ),
                "Campaign": (
                    "Annual Campaign With An Exceptionally Long Title That Must Stay Readable "
                    "In Dense Validation Rows"
                ),
            }
        )
        writer.writerow(
            {
                "Donation ID": "GB202",
                "Date": "2026-05-21",
                "Donor Name": "Taylor Reed",
                "Email": "taylor.reed@gmail.com",
                "Amount": "75.00",
                "Phone": "(415) 555-1212",
                "Address": "200 Main St",
                "Campaign": "Spring Fundraiser",
            }
        )
    return csv_path


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dense_row_decision_controls_stay_visible_and_persist_after_reload(
    flask_app_database_mode, temp_dir
):
    """Dense validation rows should keep decision controls usable and persist after reload."""
    from playwright.async_api import async_playwright

    csv_path = _write_dense_decision_csv(temp_dir)
    long_name = (
        "Alexandria Montgomery-Wentworth the Third With a Very Long "
        "Display Name for Decision Workflow Stress Coverage"
    )
    long_email = (
        "alexandria.montgomery.wentworth.the.third.with.a.very.long.name@gmal.com"
    )
    long_address = (
        "9876 Extremely Long Example Avenue, Suite 12345, Very Long City Name, CA 94107"
    )
    long_campaign = (
        "Annual Campaign With An Exceptionally Long Title That Must Stay Readable "
        "In Dense Validation Rows"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector(".upload-card", timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_path))

            submit_button = await page.query_selector(
                'button[type="submit"], button:has-text("Upload"), input[type="submit"]'
            )
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector("a.action-btn.primary", timeout=10000)
            review_button = page.locator("a.action-btn.primary").first
            await review_button.click()
            await page.wait_for_url("**/validation", timeout=10000)

            row = page.locator("tr.validation-row").first
            await row.wait_for(state="visible", timeout=10000)
            await row.scroll_into_view_if_needed()

            row_text = await row.text_content()
            assert row_text is not None
            assert "GB201" in row_text
            assert "GB202" not in row_text
            assert await row.locator('input[data-field="date"]').input_value() == "2026-05-20"

            row_box = await row.bounding_box()
            assert row_box is not None
            assert row_box["height"] < 260, (
                f"Dense decision row should stay compact, got height={row_box['height']}"
            )

            decision_dropdown = row.locator("select.row-status-dropdown")
            inspect_button = row.locator('a[data-action="inspect-record"]')
            assert await decision_dropdown.is_visible(), "Decision control should be visible"
            assert await inspect_button.is_visible(), "Details control should be visible"

            await inspect_button.click()
            await page.locator("#record-modal").wait_for(state="visible", timeout=5000)
            modal_text = await page.locator("#modal-record-content").inner_text()
            assert "GB201" in modal_text
            assert "Current issues" in modal_text
            assert "Current review" in modal_text
            assert await page.locator('#record-modal input.autosave-field').count() == 0
            assert await page.locator('#record-modal input.reviewer-name-field').count() == 1

            assert await row.locator('input.autosave-field[data-field="name"]').input_value() == long_name
            assert await row.locator('input.autosave-field[data-field="email"]').input_value() == long_email
            assert await row.locator('input.autosave-field[data-field="date"]').input_value() == "2026-05-20"

            await page.locator('#modal-record-footer button.btn-secondary').click()
            await page.wait_for_function(
                "() => !document.querySelector('#record-modal')?.classList.contains('show')",
                timeout=5000,
            )

            await inspect_button.click()
            await page.locator("#record-modal").wait_for(state="visible", timeout=5000)
            reopened_text = await page.locator("#modal-record-content").inner_text()
            assert "GB201" in reopened_text
            assert "Current issues" in reopened_text
            assert "Current review" in reopened_text
            assert await page.locator('#record-modal input.autosave-field').count() == 0
            await page.locator('#modal-record-footer button.btn-secondary').click()
            await page.wait_for_function(
                "() => !document.querySelector('#record-modal')?.classList.contains('show')",
                timeout=5000,
            )

            await decision_dropdown.select_option(value="needs_follow_up")
            await page.locator("#record-modal").wait_for(state="visible", timeout=5000)
            followup_notes = page.locator('#record-modal textarea[id^="followup-notes-"]')
            assert await followup_notes.is_visible(), "Follow-up notes field should be visible"
            await followup_notes.fill("Please verify the long-value dense row before export.")
            await page.locator('#record-modal .reviewer-name-field').fill('UAT Reviewer')

            save_followup = page.locator('#record-modal button[id^="save-followup-notes-"]')
            assert await save_followup.is_visible(), "Save Follow-up button should be visible"
            await save_followup.click()
            await page.wait_for_function(
                "() => !document.querySelector('#record-modal')?.classList.contains('show')",
                timeout=5000,
            )

            await page.wait_for_function(
                "() => document.querySelector('select.row-status-dropdown')?.value === 'needs_follow_up'",
                timeout=5000,
            )
            assert await decision_dropdown.evaluate("el => el.value") == "needs_follow_up"
            assert await decision_dropdown.get_attribute("data-has-decision") == "true"

            await page.reload()
            await page.wait_for_selector("tr.validation-row", timeout=10000)
            reloaded_row = page.locator("tr.validation-row").first
            await reloaded_row.wait_for(state="visible", timeout=10000)
            await reloaded_row.scroll_into_view_if_needed()

            reloaded_text = await reloaded_row.text_content()
            assert reloaded_text is not None
            assert "GB201" in reloaded_text
            assert "GB202" not in reloaded_text
            assert await reloaded_row.locator('input[data-field="date"]').input_value() == "2026-05-20"

            reloaded_box = await reloaded_row.bounding_box()
            assert reloaded_box is not None
            assert reloaded_box["height"] < 260, (
                f"Reloaded dense decision row should stay compact, got height={reloaded_box['height']}"
            )

            reloaded_dropdown = reloaded_row.locator("select.row-status-dropdown")
            reloaded_inspect = reloaded_row.locator('a[data-action="inspect-record"]')
            assert await reloaded_dropdown.is_visible(), "Decision control should remain visible"
            assert await reloaded_inspect.is_visible(), "Details control should remain visible"
            assert await reloaded_dropdown.evaluate("el => el.value") == "needs_follow_up"
            assert await reloaded_dropdown.get_attribute("data-has-decision") == "true"

            await reloaded_inspect.click()
            await page.locator("#record-modal").wait_for(state="visible", timeout=5000)
            reloaded_modal = await page.locator("#modal-record-content").inner_text()
            assert "GB201" in reloaded_modal
            assert long_name in reloaded_modal
            assert long_email in reloaded_modal
            assert "Current issues" in reloaded_modal
            assert await reloaded_row.locator('input.autosave-field[data-field="name"]').input_value() == long_name
            assert await reloaded_row.locator('input.autosave-field[data-field="email"]').input_value() == long_email
            assert await reloaded_row.locator('input.autosave-field[data-field="date"]').input_value() == "2026-05-20"

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
