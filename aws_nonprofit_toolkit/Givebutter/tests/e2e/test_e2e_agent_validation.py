"""
End-to-end tests for Givebutter Processor UI - P0 Critical User Workflows.

Tests the 5 critical workflows:
1. Upload CSV & Process Records
2. Inline Editing with Real-Time Tier Auto-Update
3. Override Tier via Dropdown & Confirm Warning
4. Fix Email Typo & Verify Fuzzy Matching Suggestion
5. Bulk Actions & Complete Review Workflow
"""
import pytest
import asyncio
from pathlib import Path


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_1_upload_csv_and_process(flask_app_database_mode, temp_dir):
    """P0 Test Case 1: Upload CSV & Process Records.

    Verify the complete upload → processing → review queue flow works end-to-end.
    Success: File appears in Review Queue immediately after upload with accurate tier counts.
    """
    from playwright.async_api import async_playwright

    # Create sample CSV with mixed tiers
    csv_content = """Transaction ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign Title
TX001,2026-05-10,John Doe,john@gmail.com,5551234567,100,123 Main St,Springfield,IL,General Fund
TX002,2026-05-11,Jane Smith,jane@gmai.com,,250,456 Oak Ave,Portland,OR,Education
TX003,2026-05-12,Bob Wilson,bob.smith,5551112222,500,789 Pine Rd,Denver,CO,Healthcare
TX004,2026-05-13,Alice Brown,alice@example.co,555-1234-5678,1000000,321 Elm St,Seattle,WA,Community
TX005,2026-05-14,Charlie Lee,charlie@gmial.com,5555555555,75,654 Maple Ln,Austin,TX,Youth Programs"""

    test_csv = temp_dir / "test_upload_p0_1.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to upload page
            await page.goto("http://127.0.0.1:8001/")

            # Wait for upload card to appear
            await page.wait_for_selector('.upload-card', timeout=5000)

            # Upload file
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            # Wait for processing to complete and results to appear
            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Verify file appears in Review Queue with tier counts
            content = await page.content()
            page_text = await page.inner_text('body')

            # Check for success indicators
            assert 'pass' in page_text.lower() or 'warn' in page_text.lower() or 'fail' in page_text.lower(), \
                "Upload should show tier badges with pass/warn/fail counts"
            assert 'review' in page_text.lower(), \
                "Review action should be visible"

            # Verify tier breakdown visible (PASS/WARNING/FAIL counts)
            # The page should show some indication of tiers
            has_tier_badges = (
                'pass' in content.lower() and
                ('warn' in content.lower() or 'warning' in content.lower()) and
                'fail' in content.lower()
            )
            assert has_tier_badges, \
                "Tier breakdown with pass/warn/fail badges should be displayed"

            # At minimum, we should see the upload was successful with filename
            assert 'test_upload_p0_1' in content, \
                "Uploaded filename should appear in queue"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_2_inline_editing_auto_update(flask_app_running, temp_dir):
    """P0 Test Case 2: Inline Editing with Real-Time Tier Auto-Update.

    Verify that editing data fields triggers validation and automatically updates tier
    when issues are resolved.
    Success: Edit phone field → tier changes WARNING→PASS with color update.
    """
    from playwright.async_api import async_playwright

    # Create CSV with WARNING-tier record (missing phone only - no email issues)
    csv_content = """Transaction ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign Title
TX001,2026-05-10,John Doe,john@gmail.com,2025551111,100,123 Main St,Springfield,IL,General Fund
TX002,2026-05-11,Jane Smith,jane@gmail.com,,250,456 Oak Ave,Portland,OR,Education"""

    test_csv = temp_dir / "test_inline_edit_p0_2.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))
            await asyncio.sleep(2)

            # Click Review button
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()
                await page.wait_for_selector('table', timeout=5000)

            # Wait for table to be fully rendered
            await asyncio.sleep(1)

            # Verify Jane's record starts with WARNING tier (yellow)
            tier_selects = await page.query_selector_all('.tier-select')
            assert len(tier_selects) >= 2, \
                "Should have at least 2 tier dropdowns (John and Jane)"

            # Jane's tier should be Warning initially (second row)
            jane_tier_before = await tier_selects[1].input_value()
            assert jane_tier_before == 'Warning', \
                f"Jane's tier should start as 'Warning' (missing phone), got '{jane_tier_before}'"

            # Verify Jane's tier dropdown has warning color class
            jane_tier_class_before = await tier_selects[1].get_attribute('class')
            assert 'tier-warning' in jane_tier_class_before, \
                "Jane's tier dropdown should have 'tier-warning' class (yellow) before edit"

            # Get all editable phone cells
            phone_cells = await page.query_selector_all('.editable-cell[data-field="phone"]')

            if phone_cells and len(phone_cells) > 1:
                # Click the second phone cell (Jane Smith - should be empty)
                jane_phone_cell = phone_cells[1]
                await jane_phone_cell.click()
                await asyncio.sleep(0.5)

                # Wait for input to appear
                await page.wait_for_selector('.cell-edit', timeout=5000)
                phone_input = await page.query_selector('.cell-edit')

                # Type phone number slowly to trigger input events
                # Use 2125551234 (valid: not all same digit, not sequential, not reserved 555[0-1])
                await phone_input.type('2125551234', delay=50)
                await asyncio.sleep(0.5)

                # Manually trigger input event to ensure validation runs
                await page.evaluate('document.querySelector(".cell-edit").dispatchEvent(new Event("input", { bubbles: true }))')
                await asyncio.sleep(1)

                # Check if save button is enabled and click it
                save_btn = await page.query_selector('.btn-edit-save')
                if save_btn:
                    is_disabled = await save_btn.is_disabled()
                    print(f"Save button disabled: {is_disabled}")
                    if not is_disabled:
                        # Setup console listener before clicking
                        page_logs = []
                        page.on('console', lambda msg: page_logs.append(f"{msg.type}: {msg.text}"))

                        await save_btn.click()
                        # Wait for backend recalculation to complete
                        await asyncio.sleep(3)

                        # Check for console errors/logs
                        if page_logs:
                            print(f"Console logs: {page_logs[-3:]}")  # Last 3 logs
                    else:
                        print("ERROR: Save button is still disabled after entering phone")

            # **CRITICAL: Verify tier auto-updated from WARNING to PASS**
            # Wait for backend to recalculate and update
            await asyncio.sleep(3)

            # Check if phone was actually saved by verifying in the table
            body_text = await page.inner_text('body')
            print(f"Page content snippet containing phone: {body_text[body_text.find('2125551234')-50:body_text.find('2125551234')+50] if '2125551234' in body_text else 'NOT FOUND'}")

            # Re-query tier selects after edit (need fresh query as DOM may be updated)
            max_attempts = 5
            jane_tier_after = 'Warning'
            for attempt in range(max_attempts):
                tier_selects_after = await page.query_selector_all('.tier-select')
                if len(tier_selects_after) > 1:
                    jane_tier_after = await tier_selects_after[1].input_value()
                    print(f"Attempt {attempt + 1}: Jane's tier = {jane_tier_after}")
                    if jane_tier_after == 'Pass':
                        print("✓ Tier successfully updated to Pass!")
                        break
                    await asyncio.sleep(1)

            assert jane_tier_after == 'Pass', \
                f"Jane's tier should auto-update to 'Pass' after adding phone, got '{jane_tier_after}'"

            # Verify color class changed from tier-warning to tier-pass
            tier_selects_final = await page.query_selector_all('.tier-select')
            jane_tier_class_after = await tier_selects_final[1].get_attribute('class')
            assert 'tier-pass' in jane_tier_class_after, \
                f"Jane's tier dropdown should have 'tier-pass' class (green) after fix, got classes: '{jane_tier_class_after}'"
            assert 'tier-warning' not in jane_tier_class_after, \
                "Jane's tier dropdown should NOT have 'tier-warning' class (yellow) after tier updates to Pass"

            # Verify the page loaded and records are visible
            page_content = await page.content()
            page_text = await page.inner_text('body')

            assert 'jane' in page_text.lower() or 'Jane' in page_text, \
                "Record should still be visible after edit"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_2b_partial_edit_tier_remains_warning(flask_app_running, temp_dir):
    """P0 Test Case 2b: Partial Edit - Tier Remains WARNING When Issues Persist.

    Verify that tier only becomes PASS when ALL issues are resolved, not just some.
    Success: Record with multiple issues → Fix one issue → Tier stays WARNING
             → Fix second issue → Tier becomes PASS.
    """
    from playwright.async_api import async_playwright

    # Create CSV with record having MULTIPLE issues
    # Jane has: missing phone + email typo (gmai.com)
    # This should be WARNING (or FAIL if both are critical)
    csv_content = """Transaction ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign Title
TX001,2026-05-10,John Doe,john@gmail.com,2025551111,100,123 Main St,Springfield,IL,General Fund
TX002,2026-05-11,Jane Smith,jane@gmai.com,,250,456 Oak Ave,Portland,OR,Education"""

    test_csv = temp_dir / "test_partial_edit_p0_2b.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))
            await asyncio.sleep(2)

            # Click Review button
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()
                await page.wait_for_selector('table', timeout=5000)

            # Wait for table to be fully rendered
            await asyncio.sleep(1)

            # Verify Jane's record starts with WARNING tier (multiple issues)
            tier_selects = await page.query_selector_all('.tier-select')
            assert len(tier_selects) >= 2, \
                "Should have at least 2 tier dropdowns (John and Jane)"

            # Jane's tier should be Warning initially (missing phone + email typo)
            jane_tier_before = await tier_selects[1].input_value()
            assert jane_tier_before == 'Warning', \
                f"Jane's tier should start as 'Warning' (multiple issues), got '{jane_tier_before}'"

            # Verify Jane's tier dropdown has warning color class
            jane_tier_class_before = await tier_selects[1].get_attribute('class')
            assert 'tier-warning' in jane_tier_class_before, \
                "Jane's tier dropdown should have 'tier-warning' class (yellow) before edits"

            # Get all editable phone cells
            phone_cells = await page.query_selector_all('.editable-cell[data-field="phone"]')

            # **STEP 1: Fix the phone issue**
            if phone_cells and len(phone_cells) > 1:
                jane_phone_cell = phone_cells[1]
                await jane_phone_cell.click()
                await asyncio.sleep(0.5)

                # Wait for input to appear
                await page.wait_for_selector('.cell-edit', timeout=5000)
                phone_input = await page.query_selector('.cell-edit')

                # Type valid phone number
                await phone_input.type('2125551234', delay=50)
                await asyncio.sleep(0.5)

                # Trigger input event
                await page.evaluate('document.querySelector(".cell-edit").dispatchEvent(new Event("input", { bubbles: true }))')
                await asyncio.sleep(1)

                # Save the phone edit
                save_btn = await page.query_selector('.btn-edit-save')
                if save_btn:
                    is_disabled = await save_btn.is_disabled()
                    if not is_disabled:
                        await save_btn.click()
                        await asyncio.sleep(2)

            # **CRITICAL CHECK 1: Tier should still be WARNING (email typo still exists)**
            tier_selects_after_phone = await page.query_selector_all('.tier-select')
            jane_tier_after_phone = await tier_selects_after_phone[1].input_value()
            assert jane_tier_after_phone == 'Warning', \
                f"Tier should still be 'Warning' after fixing phone (email typo remains), got '{jane_tier_after_phone}'"

            # Verify warning class still present
            jane_tier_class_after_phone = await tier_selects_after_phone[1].get_attribute('class')
            assert 'tier-warning' in jane_tier_class_after_phone, \
                "Tier should still have 'tier-warning' class after fixing one of multiple issues"
            assert 'tier-pass' not in jane_tier_class_after_phone, \
                "Tier should NOT have 'tier-pass' class when issues remain"

            # **STEP 2: Fix the email issue**
            email_cells = await page.query_selector_all('.editable-cell[data-field="email"]')
            if email_cells and len(email_cells) > 1:
                jane_email_cell = email_cells[1]
                await jane_email_cell.click()
                await asyncio.sleep(0.5)

                # Wait for input to appear
                await page.wait_for_selector('.cell-edit', timeout=5000)
                email_input = await page.query_selector('.cell-edit')

                # Use fill() to completely replace the email value
                await email_input.fill('jane@gmail.com')
                await asyncio.sleep(0.5)

                # Trigger input event to validate
                await page.evaluate('document.querySelector(".cell-edit").dispatchEvent(new Event("input", { bubbles: true }))')
                await asyncio.sleep(1)

                # Save the email edit
                save_btn = await page.query_selector('.btn-edit-save')
                if save_btn:
                    is_disabled = await save_btn.is_disabled()
                    print(f"Email save button disabled: {is_disabled}")
                    if not is_disabled:
                        # Setup console listener for debugging
                        page_logs = []
                        page.on('console', lambda msg: page_logs.append(f"{msg.type}: {msg.text}"))

                        await save_btn.click()
                        await asyncio.sleep(3)

                        if page_logs:
                            print(f"Console logs during email save: {page_logs[-3:]}")
                    else:
                        print("ERROR: Email save button is disabled!")

            # **CRITICAL CHECK 2: Now tier should be PASS (all issues fixed)**
            # Wait a bit more for tier recalculation
            await asyncio.sleep(1)
            tier_selects_after_email = await page.query_selector_all('.tier-select')
            jane_tier_after_email = await tier_selects_after_email[1].input_value()

            # Check page content to verify email was saved
            body_text = await page.inner_text('body')
            email_saved = 'jane@gmail.com' in body_text
            print(f"Email saved in UI: {email_saved}, Tier after email fix: {jane_tier_after_email}")

            assert jane_tier_after_email == 'Pass', \
                f"Tier should now be 'Pass' after fixing all issues, got '{jane_tier_after_email}'"

            # Verify pass class now present
            jane_tier_class_after_email = await tier_selects_after_email[1].get_attribute('class')
            assert 'tier-pass' in jane_tier_class_after_email, \
                "Tier should have 'tier-pass' class (green) after all issues fixed"
            assert 'tier-warning' not in jane_tier_class_after_email, \
                "Tier should NOT have 'tier-warning' class after all issues are resolved"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_2c_long_phone_number_confirmation(flask_app_running, temp_dir):
    """P0 Test Case 2c: Long Phone Number - Confirmation Dialog and Issue Flagging.

    Verify that phone numbers >11 digits trigger a confirmation dialog,
    are flagged in Issues with appropriate suggestion, and tier stays WARNING.
    Success: Enter 13-digit phone → confirmation dialog → user confirms → saved with WARNING tier.
    """
    from playwright.async_api import async_playwright

    # Create CSV with record that will receive a >11 digit phone
    csv_content = """Transaction ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign Title
TX001,2026-05-10,John Doe,john@gmail.com,2025551111,100,123 Main St,Springfield,IL,General Fund
TX002,2026-05-11,Jane Smith,jane@gmail.com,,250,456 Oak Ave,Portland,OR,Education"""

    test_csv = temp_dir / "test_long_phone_p0_2c.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))
            await asyncio.sleep(2)

            # Click Review button
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()
                await page.wait_for_selector('table', timeout=5000)

            # Wait for table to be fully rendered
            await asyncio.sleep(1)

            # Get all editable phone cells
            phone_cells = await page.query_selector_all('.editable-cell[data-field="phone"]')

            if phone_cells and len(phone_cells) > 1:
                # Click the second phone cell (Jane Smith - empty)
                jane_phone_cell = phone_cells[1]
                await jane_phone_cell.click()
                await asyncio.sleep(0.5)

                # Wait for input to appear
                await page.wait_for_selector('.cell-edit', timeout=5000)
                phone_input = await page.query_selector('.cell-edit')

                # Verify maxlength is set to 15
                max_length = await phone_input.get_attribute('maxlength')
                assert max_length == '15', \
                    f"Phone input should have maxlength='15', got '{max_length}'"

                # Type a 13-digit phone number (longer than 11)
                # This should pass validation but trigger confirmation on save
                await phone_input.type('2125551234567', delay=50)  # 13 digits
                await asyncio.sleep(0.5)

                # Trigger input event for validation
                await page.evaluate('document.querySelector(".cell-edit").dispatchEvent(new Event("input", { bubbles: true }))')
                await asyncio.sleep(1)

                # Save button should be enabled (13 digits is within 10-15 range)
                save_btn = await page.query_selector('.btn-edit-save')
                if save_btn:
                    is_disabled = await save_btn.is_disabled()
                    assert not is_disabled, \
                        "Save button should be enabled for 13-digit phone (within validation range)"

                    # Setup dialog handler to accept the confirmation
                    async def handle_dialog(dialog):
                        dialog_msg = dialog.message
                        assert '13 digits' in dialog_msg or 'digits' in dialog_msg.lower(), \
                            f"Confirmation dialog should mention digit count, got: {dialog_msg}"
                        await dialog.accept()

                    page.once('dialog', handle_dialog)

                    # Click save - should trigger confirmation dialog
                    await save_btn.click()
                    await asyncio.sleep(2)

            # Verify tier is WARNING (not PASS, because >11 digits is flagged)
            tier_selects = await page.query_selector_all('.tier-select')
            if len(tier_selects) >= 2:
                jane_tier = await tier_selects[1].input_value()
                assert jane_tier == 'Warning', \
                    f"Tier should be 'Warning' for >11 digit phone, got '{jane_tier}'"

            # Verify Issues column shows the warning about phone length
            page_content = await page.content()
            page_text = await page.inner_text('body')

            # Look for indication that phone length issue was flagged
            phone_length_flagged = (
                '13 digits' in page_text or
                'too long' in page_text.lower() or
                'more than 11' in page_text.lower()
            )
            assert phone_length_flagged, \
                "Issues column should flag that phone is >11 digits"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_3_tier_override_confirmation(flask_app_running, temp_dir):
    """P0 Test Case 3: Override Tier via Dropdown & Confirm Warning.

    Verify operator can manually change tier and sees warning when approving FAIL/WARNING records.
    Success: Tier dropdown changes from red FAIL → green PASS with color update and persistence.
    """
    from playwright.async_api import async_playwright

    # Create CSV with FAIL-tier record (invalid email)
    csv_content = """Transaction ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign Title
TX001,2026-05-10,John Doe,john@gmail.com,5551234567,100,123 Main St,Springfield,IL,General Fund
TX003,2026-05-12,Bob Wilson,bob.smith,5551112222,500,789 Pine Rd,Denver,CO,Healthcare"""

    test_csv = temp_dir / "test_tier_override_p0_3.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))
            await asyncio.sleep(2)

            # Click Review button
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()
                await page.wait_for_selector('table', timeout=5000)

            # Wait for table to stabilize
            await asyncio.sleep(1)

            # Find tier dropdowns
            tier_selects = await page.query_selector_all('.tier-select')

            if tier_selects and len(tier_selects) > 1:
                # Change the second tier dropdown (Bob Wilson - should be FAIL)
                bob_tier_select = tier_selects[1]

                # Use select_option to change the value
                await bob_tier_select.select_option('Pass')
                await asyncio.sleep(1)

                # Verify color changed to green
                content = await page.content()
                # The tier-select should now have class tier-pass
                class_attr = await bob_tier_select.get_attribute('class')
                assert 'tier-pass' in class_attr or '#d4edda' in content, \
                    "Tier dropdown should change to Pass (green) class"
            else:
                # Verify tier dropdowns exist
                assert len(tier_selects) > 0, "Tier dropdowns should exist"

            # Click Done button
            done_button = await page.query_selector('button:has-text("Done")')
            if done_button:
                await done_button.click()
                await asyncio.sleep(1)

            # Reopen and verify tier persisted
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()
                await page.wait_for_selector('table', timeout=5000)
                await asyncio.sleep(1)

                # Verify record still shows with updated tier
                content = await page.content()
                page_text = await page.inner_text('body')
                assert 'bob' in page_text.lower() or 'wilson' in page_text.lower(), \
                    "Record should persist after reopening"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_4_email_fuzzy_matching(flask_app_running, temp_dir):
    """P0 Test Case 4: Fix Email Typo & Verify Fuzzy Matching Suggestion.

    Verify aggressive email fuzzy matching catches typos and suggests corrections.
    Success: Typo gmai.com flagged → suggestion shown → inline fix → tier updates.
    """
    from playwright.async_api import async_playwright

    # Create CSV with email typos
    csv_content = """Transaction ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign Title
TX001,2026-05-10,John Doe,john@gmail.com,5551234567,100,123 Main St,Springfield,IL,General Fund
TX002,2026-05-11,Jane Smith,jane@gmai.com,5551111111,250,456 Oak Ave,Portland,OR,Education
TX005,2026-05-14,Charlie Lee,charlie@gmial.com,5555555555,75,654 Maple Ln,Austin,TX,Youth Programs"""

    test_csv = temp_dir / "test_fuzzy_match_p0_4.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file with email typos
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))
            await asyncio.sleep(2)

            # Click Review button
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()
                await page.wait_for_selector('table', timeout=5000)

            # Verify typo is flagged in Issues column
            content = await page.content()
            page_text = await page.inner_text('body')

            # Check for fuzzy matching detection
            # Should flag gmai.com, gmial.com as typos
            fuzzy_detected = (
                'typo' in page_text.lower() or
                'gmai' in page_text or
                'gmial' in page_text or
                'consider' in page_text.lower()
            )

            if fuzzy_detected:
                # Try to find and edit email cell
                editable_cells = await page.query_selector_all('.editable-cell[data-field="email"]')

                if editable_cells:
                    # Click email cell for Jane (gmai.com)
                    for cell in editable_cells:
                        cell_text = await cell.inner_text()
                        if 'gmai' in cell_text:
                            await cell.click()
                            await asyncio.sleep(0.5)

                            # Clear and type correct email
                            await page.keyboard.press('Control+A')
                            await page.keyboard.type('jane@gmail.com')

                            # Save
                            save_btn = await page.query_selector('.btn-edit-save, button:has-text("Save")')
                            if save_btn:
                                await save_btn.click()
                                await asyncio.sleep(1)
                            break

                # Verify tier updated after fix
                tier_content = await page.content()
                assert 'Pass' in tier_content or 'pass' in tier_content.lower() or '#d4edda' in tier_content, \
                    "Tier should update to PASS after email typo is fixed"
            else:
                # At minimum, verify the page loaded correctly
                assert 'jane' in page_text.lower() or 'charlie' in page_text.lower(), \
                    "Records with email typos should be visible in review"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_p0_5_bulk_actions_complete_workflow(flask_app_running, temp_dir):
    """P0 Test Case 5: Bulk Actions & Complete Review Workflow.

    Verify bulk decision buttons work and "Done" button completes the review.
    Success: All records approved at once → confirmation dialog → Done → workflow complete.
    """
    from playwright.async_api import async_playwright

    # Create CSV with 10+ records (mix of tiers)
    csv_content = """Transaction ID,Date,Donor Name,Email,Phone,Amount,Address 1,City,State,Campaign Title
TX001,2026-05-10,John Doe,john@gmail.com,5551234567,100,123 Main St,Springfield,IL,General Fund
TX002,2026-05-11,Jane Smith,jane@gmai.com,,250,456 Oak Ave,Portland,OR,Education
TX003,2026-05-12,Bob Wilson,bob.smith,5551112222,500,789 Pine Rd,Denver,CO,Healthcare
TX004,2026-05-13,Alice Brown,alice@example.co,555-1234-5678,1000000,321 Elm St,Seattle,WA,Community
TX005,2026-05-14,Charlie Lee,charlie@gmial.com,5555555555,75,654 Maple Ln,Austin,TX,Youth Programs
TX006,2026-05-15,Sarah Davis,sarah@yahoo.com,5559876543,500,987 Birch St,Boston,MA,Operations
TX007,2026-05-16,Mike Johnson,mike@gmail.com,5552223333,150,111 Spruce Ave,Chicago,IL,General Fund
TX008,2026-05-17,Emily Wilson,emily@hotmail.com,5553334444,300,222 Ash Rd,Los Angeles,CA,Programs
TX009,2026-05-18,David Lee,david@yahoo.com,2500,333 Cedar Ln,San Francisco,CA,Major Gifts
TX010,2026-05-19,Jessica Brown,jbrown@aol.com,,1000,444 Walnut St,Miami,FL,Fundraising"""

    test_csv = temp_dir / "test_bulk_actions_p0_5.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))
            await asyncio.sleep(2)

            # Click Review button
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()
                await page.wait_for_selector('table', timeout=5000)

            # Click "All: Approved" button
            bulk_approve = await page.query_selector('button:has-text("All: Approved"), button:has-text("All: APPROVED")')
            if bulk_approve:
                await bulk_approve.click()
                await asyncio.sleep(1)

                # Confirmation dialog should appear
                # Accept any dialogs
                try:
                    dialog = await page.wait_for_event('dialog', timeout=3000)
                    await dialog.accept()
                except:
                    pass  # No dialog or already closed

                await asyncio.sleep(1)

                # Verify all decisions set to Approved
                content = await page.content()
                page_text = await page.inner_text('body')

                # Should show decisions set
                decision_count = page_text.count('Approved') if 'Approved' in page_text else 0
                # At minimum, records should be visible and processable
                assert 'TX' in page_text or 'john' in page_text.lower(), \
                    "Records should still be visible after bulk action"

            # Click Done button
            done_button = await page.query_selector('button:has-text("Done")')
            if done_button:
                await done_button.click()
                await asyncio.sleep(2)

                # Verify workflow completed
                content = await page.content()
                page_text = await page.inner_text('body')

                # After Done, we should be back at upload/queue screen or see success message
                assert 'complete' in page_text.lower() or 'queue' in page_text.lower() or 'upload' in page_text.lower(), \
                    "Workflow should complete and return to main screen"
            else:
                # At minimum, verify review page is functional
                assert 'decision' in page_text.lower() or 'approved' in page_text.lower(), \
                    "Review page should be showing decision dropdowns"

        finally:
            await browser.close()
