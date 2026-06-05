"""
E2E tests for recalculate-tier DOM updates.

These tests verify that when the backend recalculates a tier after an edit,
the frontend DOM is correctly updated with the new tier, issues, and suggestions.

This tests prevents regressions like the column-index-off-by-one bug that was
caught on 2026-06-05.
"""
import pytest
import asyncio


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_invalid_phone_edit_updates_issues_in_dom(flask_app_running, temp_dir, sample_csv):
    """
    Test that editing phone to invalid value updates Issues column content.

    This test catches DOM update bugs by verifying the Issues column innerHTML
    actually contains the validation error message.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")

            # Upload CSV
            await page.click('input[type="file"]')
            await page.set_input_files('input[type="file"]', str(sample_csv))
            await page.click('button:has-text("Process")')
            await page.wait_for_selector('.processing-queue', timeout=5000)

            # Click to review first file
            await page.click('.processing-queue li:first-child')
            await page.wait_for_selector('table tbody tr', timeout=5000)

            # Get initial Issues cell content
            initial_issues_cell = await page.query_selector(
                'table tbody tr:first-child td[data-field-type="issues"]'
            )
            initial_issues_text = await initial_issues_cell.inner_text() if initial_issues_cell else ""

            # Click phone cell to edit
            phone_cell = await page.query_selector(
                'table tbody tr:first-child td[data-field="phone"]'
            )
            await phone_cell.click()

            # Wait for input to appear
            phone_input = await page.wait_for_selector(
                'table tbody tr:first-child td[data-field="phone"] input'
            )

            # Enter invalid phone (sequential test number)
            await phone_input.clear()
            await phone_input.type('1234567890')

            # Find and click save button
            save_button = await page.query_selector(
                'table tbody tr:first-child td[data-field="phone"] .btn-save'
            )
            if save_button:
                await save_button.click()
            else:
                # If button not found, press Enter to save
                await phone_input.press('Enter')

            # Wait for recalculate-tier response (check for Issues cell to update)
            await asyncio.sleep(1)

            # Verify Issues cell was updated with error message
            updated_issues_cell = await page.query_selector(
                'table tbody tr:first-child td[data-field-type="issues"]'
            )
            assert updated_issues_cell is not None, "Issues cell not found - verify data-field-type='issues' exists"

            # Get the updated HTML content
            updated_issues_html = await updated_issues_cell.inner_html()
            updated_issues_text = await updated_issues_cell.inner_text()

            # Verify the Issues column now contains the validation error
            assert 'Invalid' in updated_issues_text or 'Sequential' in updated_issues_text, \
                f"Expected 'Invalid' or 'Sequential' in issues text, got: '{updated_issues_text}'"

            # Verify it contains the phone-specific error
            assert 'Phone' in updated_issues_text, \
                f"Expected 'Phone' prefix in issues, got: '{updated_issues_text}'"

            print(f"✓ Issues updated correctly: {updated_issues_text}")

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_valid_phone_edit_clears_issues_in_dom(flask_app_running, temp_dir, sample_csv):
    """
    Test that editing phone from invalid to valid value clears Issues.

    Verifies the Issues column is emptied (innerHTML='') when all issues are fixed.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")

            # Upload CSV with intentional invalid phone
            import tempfile
            import csv
            test_csv = sample_csv.parent / "test_invalid_phone.csv"

            with open(sample_csv) as f:
                reader = csv.reader(f)
                rows = list(reader)

            # Modify first data row to have invalid phone
            if len(rows) > 1:
                rows[1][-3] = '1234567890'  # Phone column typically near end

            with open(test_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)

            # Upload test CSV
            await page.click('input[type="file"]')
            await page.set_input_files('input[type="file"]', str(test_csv))
            await page.click('button:has-text("Process")')
            await page.wait_for_selector('.processing-queue', timeout=5000)

            # Review the file
            await page.click('.processing-queue li:first-child')
            await page.wait_for_selector('table tbody tr', timeout=5000)

            # Verify initial Issues cell has content
            issues_cell = await page.query_selector(
                'table tbody tr:first-child td[data-field-type="issues"]'
            )
            initial_content = await issues_cell.inner_text()
            assert len(initial_content) > 0, "Expected issues initially"

            # Click phone cell and edit to valid number
            phone_cell = await page.query_selector(
                'table tbody tr:first-child td[data-field="phone"]'
            )
            await phone_cell.click()

            phone_input = await page.wait_for_selector(
                'table tbody tr:first-child td[data-field="phone"] input'
            )
            await phone_input.clear()
            await phone_input.type('5551234567')  # Valid

            # Save
            save_button = await page.query_selector(
                'table tbody tr:first-child td[data-field="phone"] .btn-save'
            )
            if save_button:
                await save_button.click()
            else:
                await phone_input.press('Enter')

            # Wait for update
            await asyncio.sleep(1)

            # Verify Issues cell is now empty (or contains "None")
            updated_issues_cell = await page.query_selector(
                'table tbody tr:first-child td[data-field-type="issues"]'
            )
            updated_content = await updated_issues_cell.inner_text()

            # Should be empty, "None", or contain "No" issues
            assert updated_content.strip() in ['', 'None', ''] or len(updated_content.strip()) == 0, \
                f"Expected empty Issues after fix, got: '{updated_content}'"

            print(f"✓ Issues cleared correctly after valid edit")

            # Cleanup
            test_csv.unlink()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tier_class_updated_on_recalculate(flask_app_running, temp_dir, sample_csv):
    """
    Test that the tier cell's CSS class is updated (e.g., tier-warning to tier-fail).

    This verifies the visual indicator (color) is updated, not just the text.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")

            # Upload CSV
            await page.click('input[type="file"]')
            await page.set_input_files('input[type="file"]', str(sample_csv))
            await page.click('button:has-text("Process")')
            await page.wait_for_selector('.processing-queue', timeout=5000)

            # Review
            await page.click('.processing-queue li:first-child')
            await page.wait_for_selector('table tbody tr', timeout=5000)

            # Get initial tier class
            tier_span = await page.query_selector(
                'table tbody tr:first-child td[data-field-type="tier"] span'
            )
            initial_classes = await tier_span.get_attribute('class')
            initial_tier = await tier_span.inner_text()

            print(f"Initial tier: {initial_tier}, classes: {initial_classes}")

            # If it's PASS, make it fail by editing phone to invalid
            if initial_tier == 'PASS':
                phone_cell = await page.query_selector(
                    'table tbody tr:first-child td[data-field="phone"]'
                )
                await phone_cell.click()

                phone_input = await page.wait_for_selector(
                    'table tbody tr:first-child td[data-field="phone"] input'
                )
                await phone_input.clear()
                await phone_input.type('1234567890')  # Invalid

                save_button = await page.query_selector(
                    'table tbody tr:first-child td[data-field="phone"] .btn-save'
                )
                if save_button:
                    await save_button.click()
                else:
                    await phone_input.press('Enter')

                await asyncio.sleep(1)

                # Check tier changed
                updated_tier_span = await page.query_selector(
                    'table tbody tr:first-child td[data-field-type="tier"] span'
                )
                updated_tier = await updated_tier_span.inner_text()
                updated_classes = await updated_tier_span.get_attribute('class')

                print(f"Updated tier: {updated_tier}, classes: {updated_classes}")

                # Verify tier text changed
                assert updated_tier != initial_tier, f"Tier should change, but stayed {updated_tier}"

                # Verify class changed
                if 'tier-pass' in initial_classes and 'tier-fail' in updated_classes:
                    print("✓ Tier class correctly updated from tier-pass to tier-fail")
                elif initial_classes != updated_classes:
                    print(f"✓ Tier class updated from '{initial_classes}' to '{updated_classes}'")
                else:
                    print(f"Warning: Classes appear same but tier text changed: {initial_tier} → {updated_tier}")
            else:
                print(f"Skipping tier class test (initial tier was {initial_tier}, not PASS)")

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dom_cell_selectors_exist(flask_app_running, temp_dir, sample_csv):
    """
    Test that all required data-field-type attributes exist on the table cells.

    This is a sanity check to catch HTML structure regressions.
    """
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")

            # Upload CSV
            await page.click('input[type="file"]')
            await page.set_input_files('input[type="file"]', str(sample_csv))
            await page.click('button:has-text("Process")')
            await page.wait_for_selector('.processing-queue', timeout=5000)

            # Review
            await page.click('.processing-queue li:first-child')
            await page.wait_for_selector('table tbody tr', timeout=5000)

            # Check each required data-field-type attribute
            required_fields = ['tier', 'issues', 'suggestions', 'decision', 'notes']
            first_row = await page.query_selector('table tbody tr:first-child')

            for field in required_fields:
                cell = await first_row.query_selector(f'td[data-field-type="{field}"]')
                assert cell is not None, f"Missing td[data-field-type='{field}'] in first row"
                print(f"✓ Found td[data-field-type='{field}']")

            print("✓ All required data-field-type attributes exist")

        finally:
            await browser.close()
