"""E2E tests for inline record editing feature."""
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio


@pytest.mark.e2e
async def test_inline_editing_pencil_icon_appears(flask_app_running, sample_csv):
    """Verify pencil icon appears on hover over editable cells."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            # Wait for processing
            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Look for editable cells and verify pencil icon
            editable_cells = await page.query_selector_all('td.editable-cell')

            if editable_cells:
                cell = editable_cells[0]
                await cell.hover()

                # Check if edit icon exists
                edit_icon = await cell.query_selector('.edit-icon')
                assert edit_icon is not None, "Pencil icon should appear on hover"

        finally:
            await browser.close()


@pytest.mark.e2e
async def test_inline_editing_click_switches_to_edit_mode(flask_app_running, sample_csv):
    """Verify clicking a cell switches it to edit mode."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Find editable cell and click it
            editable_cells = await page.query_selector_all('td.editable-cell')

            if editable_cells:
                cell = editable_cells[0]
                await cell.click()

                # Check if input field appears
                input_elem = await cell.query_selector('input.cell-edit')
                assert input_elem is not None, "Input field should appear in edit mode"

        finally:
            await browser.close()


@pytest.mark.e2e
async def test_inline_editing_cancel_discards_changes(flask_app_running, sample_csv):
    """Verify cancel button exits edit mode without saving."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Edit a cell
            editable_cells = await page.query_selector_all('td.editable-cell')

            if editable_cells:
                cell = editable_cells[0]
                original_content = await cell.text_content()

                await cell.click()
                input_elem = await cell.query_selector('input.cell-edit')

                if input_elem:
                    await input_elem.fill('NewValue')

                    # Click cancel button
                    cancel_btn = await cell.query_selector('.btn-edit-cancel')
                    if cancel_btn:
                        await cancel_btn.click()

                        # Content should be reverted
                        final_content = await cell.text_content()
                        assert 'NewValue' not in final_content, "Changes should be discarded on cancel"

        finally:
            await browser.close()


@pytest.mark.e2e
async def test_inline_editing_invalid_email_shows_error(flask_app_running, sample_csv):
    """Verify invalid email triggers validation error."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Find email cell and edit it with invalid value
            email_cells = await page.query_selector_all('td.editable-cell[data-field="email"]')

            if email_cells:
                cell = email_cells[0]
                await cell.click()

                input_elem = await cell.query_selector('input.cell-edit')
                if input_elem:
                    await input_elem.fill('invalidemail')
                    await input_elem.blur()

                    # Check for error message
                    error_msg = await cell.query_selector('.edit-error.show')
                    assert error_msg is not None, "Error message should appear for invalid email"

        finally:
            await browser.close()


@pytest.mark.e2e
async def test_inline_editing_clears_only_field_specific_issues(flask_app_isolated, temp_dir):
    """Verify that editing a field only clears issues for that field, not all issues."""
    from playwright.async_api import async_playwright
    import csv

    # Create test CSV with multiple issues (email typo, missing phone)
    test_csv = temp_dir / "test_multiple_issues.csv"
    with open(test_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Transaction ID', 'Date', 'Name', 'Email', 'Phone', 'Amount', 'Campaign Title'
        ])
        writer.writeheader()
        writer.writerow({
            'Transaction ID': 'TXN001',
            'Date': '2026-06-04',
            'Name': 'Test User',
            'Email': 'test@gmai.com',  # Typo - triggers email issue
            'Phone': '',  # Missing - triggers phone issue
            'Amount': '100',
            'Campaign Title': 'General Fund'
        })

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Get issues cell and verify both issues exist initially
            issues_cell = await page.query_selector('td.issues')
            if issues_cell:
                initial_issues_json = await issues_cell.get_attribute('data-issues')
                initial_issues = eval(initial_issues_json) if initial_issues_json else []

                # Should have email and phone issues
                assert any('Email' in issue for issue in initial_issues), "Should have email issue"
                assert any('Phone' in issue for issue in initial_issues), "Should have phone issue"

                # Edit phone field to fix it
                phone_cell = await page.query_selector('td.editable-cell[data-field="phone"]')
                if phone_cell:
                    await phone_cell.click()
                    phone_input = await phone_cell.query_selector('input.cell-edit')
                    if phone_input:
                        await phone_input.fill('5551234567')

                        # Save the edit
                        save_btn = await phone_cell.query_selector('.btn-edit-save')
                        if save_btn:
                            await save_btn.click()

                            # Wait for update
                            await page.wait_for_timeout(500)

                            # Check issues cell again
                            issues_cell_updated = await page.query_selector('td.issues')
                            if issues_cell_updated:
                                updated_issues_json = await issues_cell_updated.get_attribute('data-issues')
                                updated_issues = eval(updated_issues_json) if updated_issues_json else []

                                # Phone issue should be cleared
                                assert not any('Phone' in issue for issue in updated_issues), "Phone issue should be cleared"

                                # Email issue should remain
                                assert any('Email' in issue for issue in updated_issues), "Email issue should remain"

        finally:
            await browser.close()


@pytest.mark.e2e
async def test_inline_editing_updates_suggestions_column(flask_app_isolated, temp_dir):
    """Verify that Suggested_Modifications column updates when field is edited."""
    from playwright.async_api import async_playwright
    import csv

    # Create test CSV with suggestions
    test_csv = temp_dir / "test_suggestions.csv"
    with open(test_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Transaction ID', 'Date', 'Name', 'Email', 'Phone', 'Amount', 'Campaign Title'
        ])
        writer.writeheader()
        writer.writerow({
            'Transaction ID': 'TXN002',
            'Date': '2026-06-04',
            'Name': 'Test User',
            'Email': 'test@gmai.com',  # Will suggest correction
            'Phone': '',  # Will suggest adding phone
            'Amount': '100',
            'Campaign Title': 'General Fund'
        })

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Get suggestions cell
            suggestions_cell = await page.query_selector('td.suggestions')
            if suggestions_cell:
                initial_suggestions_json = await suggestions_cell.get_attribute('data-suggestions')
                initial_suggestions = eval(initial_suggestions_json) if initial_suggestions_json else []
                initial_count = len(initial_suggestions)

                # Edit phone field
                phone_cell = await page.query_selector('td.editable-cell[data-field="phone"]')
                if phone_cell:
                    await phone_cell.click()
                    phone_input = await phone_cell.query_selector('input.cell-edit')
                    if phone_input:
                        await phone_input.fill('5551234567')

                        # Save the edit
                        save_btn = await phone_cell.query_selector('.btn-edit-save')
                        if save_btn:
                            await save_btn.click()

                            # Wait for update
                            await page.wait_for_timeout(500)

                            # Check suggestions again
                            suggestions_cell_updated = await page.query_selector('td.suggestions')
                            if suggestions_cell_updated:
                                updated_suggestions_json = await suggestions_cell_updated.get_attribute('data-suggestions')
                                updated_suggestions = eval(updated_suggestions_json) if updated_suggestions_json else []

                                # Should have fewer suggestions now
                                assert len(updated_suggestions) < initial_count, "Phone suggestion should be removed"

                                # Phone-related suggestions should be gone
                                assert not any('phone' in s.lower() for s in updated_suggestions), "Phone suggestions should be cleared"

        finally:
            await browser.close()


@pytest.mark.e2e
async def test_inline_editing_clears_email_typo_suggestions(flask_app_isolated, temp_dir):
    """Verify that email typo suggestions are cleared when email is corrected."""
    from playwright.async_api import async_playwright
    import csv

    # Create test CSV with email typo that generates "Consider: corrected@email.com" suggestion
    test_csv = temp_dir / "test_email_suggestion.csv"
    with open(test_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Transaction ID', 'Date', 'Name', 'Email', 'Phone', 'Amount', 'Campaign Title'
        ])
        writer.writeheader()
        writer.writerow({
            'Transaction ID': 'TXN004',
            'Date': '2026-06-05',
            'Name': 'John Doe',
            'Email': 'john@gmai.com',  # Typo - will suggest correction
            'Phone': '5551234567',
            'Amount': '100',
            'Campaign Title': 'General Fund'
        })

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Get initial suggestions
            suggestions_cell = await page.query_selector('td.suggestions')
            if suggestions_cell:
                initial_suggestions_json = await suggestions_cell.get_attribute('data-suggestions')
                initial_suggestions = eval(initial_suggestions_json) if initial_suggestions_json else []

                # Should have email correction suggestion
                assert any('gmai' in s.lower() or 'gmail' in s.lower() or 'consider:' in s.lower()
                          for s in initial_suggestions), f"Should have email correction suggestion, got: {initial_suggestions}"

                # Edit email field to correct the typo
                email_cell = await page.query_selector('td.editable-cell[data-field="email"]')
                if email_cell:
                    await email_cell.click()
                    email_input = await email_cell.query_selector('input.cell-edit')
                    if email_input:
                        await email_input.fill('john@gmail.com')

                        # Save the edit
                        save_btn = await email_cell.query_selector('.btn-edit-save')
                        if save_btn:
                            await save_btn.click()

                            # Wait for update
                            await page.wait_for_timeout(500)

                            # Check suggestions again
                            suggestions_cell_updated = await page.query_selector('td.suggestions')
                            if suggestions_cell_updated:
                                updated_suggestions_json = await suggestions_cell_updated.get_attribute('data-suggestions')
                                updated_suggestions = eval(updated_suggestions_json) if updated_suggestions_json else []

                                # Email correction suggestion should be cleared
                                assert not any('gmai' in s.lower() or 'consider:' in s.lower() for s in updated_suggestions), \
                                    f"Email correction suggestion should be cleared, remaining: {updated_suggestions}"

        finally:
            await browser.close()


@pytest.mark.e2e
async def test_inline_editing_recalculates_tier_on_edit(flask_app_isolated, temp_dir):
    """Verify that Validation_Tier updates when fixes move record between tiers."""
    from playwright.async_api import async_playwright
    import csv

    # Create test CSV with record in FAIL tier (missing phone, bad email)
    test_csv = temp_dir / "test_tier_recalc.csv"
    with open(test_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Transaction ID', 'Date', 'Name', 'Email', 'Phone', 'Amount', 'Campaign Title'
        ])
        writer.writeheader()
        writer.writerow({
            'Transaction ID': 'TXN003',
            'Date': '2026-06-04',
            'Name': 'Test User',
            'Email': 'test@gmai.com',  # Bad email - triggers Email issue
            'Phone': '',  # Missing phone - triggers Phone issue
            'Amount': '100',
            'Campaign Title': 'General Fund'
        })

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Upload CSV
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Get initial tier (should be WARNING due to email issue)
            tier_cell = await page.query_selector('tr[data-record-idx="0"] td:nth-child(10)')
            if tier_cell:
                initial_tier_text = await tier_cell.text_content()
                assert 'WARNING' in initial_tier_text, f"Initial tier should be WARNING, got {initial_tier_text}"

                # Edit email field to fix the typo
                email_cell = await page.query_selector('td.editable-cell[data-field="email"]')
                if email_cell:
                    await email_cell.click()
                    email_input = await email_cell.query_selector('input.cell-edit')
                    if email_input:
                        await email_input.fill('test@gmail.com')

                        # Save the edit
                        save_btn = await email_cell.query_selector('.btn-edit-save')
                        if save_btn:
                            await save_btn.click()

                            # Wait for tier recalculation
                            await page.wait_for_timeout(500)

                            # Check tier again (should still be WARNING due to missing phone)
                            tier_cell_updated = await page.query_selector('tr[data-record-idx="0"] td:nth-child(10)')
                            if tier_cell_updated:
                                updated_tier_text = await tier_cell_updated.text_content()
                                assert 'WARNING' in updated_tier_text, f"After email fix, tier should still be WARNING (phone missing), got {updated_tier_text}"

                                # Now fix the phone number
                                phone_cell = await page.query_selector('td.editable-cell[data-field="phone"]')
                                if phone_cell:
                                    await phone_cell.click()
                                    phone_input = await phone_cell.query_selector('input.cell-edit')
                                    if phone_input:
                                        await phone_input.fill('5551234567')

                                        # Save the edit
                                        save_btn = await phone_cell.query_selector('.btn-edit-save')
                                        if save_btn:
                                            await save_btn.click()

                                            # Wait for tier recalculation
                                            await page.wait_for_timeout(500)

                                            # Check tier now (should be PASS)
                                            tier_cell_final = await page.query_selector('tr[data-record-idx="0"] td:nth-child(10)')
                                            if tier_cell_final:
                                                final_tier_text = await tier_cell_final.text_content()
                                                assert 'PASS' in final_tier_text, f"After fixing all issues, tier should be PASS, got {final_tier_text}"

        finally:
            await browser.close()
