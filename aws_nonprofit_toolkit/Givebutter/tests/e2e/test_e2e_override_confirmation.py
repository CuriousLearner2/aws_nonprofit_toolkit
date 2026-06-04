"""End-to-end tests for approval override confirmation feature."""
import pytest
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import os
import csv
import tempfile


@pytest.fixture
def fail_records_csv():
    """Create CSV with FAIL tier records (missing required fields)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'Transaction ID', 'Date', 'Name', 'Email', 'Phone', 'Amount', 'Campaign Title'
        ])
        writer.writeheader()

        # Record 1: Valid (PASS)
        writer.writerow({
            'Transaction ID': 'TXN001',
            'Date': '2026-06-01',
            'Name': 'John Smith',
            'Email': 'john@gmail.com',
            'Phone': '5551234567',
            'Amount': '100',
            'Campaign Title': 'Annual Giving'
        })

        # Record 2: Missing email (FAIL)
        writer.writerow({
            'Transaction ID': 'TXN002',
            'Date': '2026-06-01',
            'Name': 'Jane Doe',
            'Email': '',
            'Phone': '5559876543',
            'Amount': '250',
            'Campaign Title': 'Annual Giving'
        })

        # Record 3: Missing amount (FAIL)
        writer.writerow({
            'Transaction ID': 'TXN003',
            'Date': '2026-06-01',
            'Name': 'Bob Wilson',
            'Email': 'bob@example.com',
            'Phone': '5551112222',
            'Amount': '',
            'Campaign Title': 'Campaign X'
        })

        # Record 4: Invalid amount (FAIL)
        writer.writerow({
            'Transaction ID': 'TXN004',
            'Date': '2026-06-01',
            'Name': 'Alice Brown',
            'Email': 'alice@test.com',
            'Phone': '',
            'Amount': '0',
            'Campaign Title': 'Campaign X'
        })

        return f.name


@pytest.mark.skip(reason="Deprecated - flaky due to multi-step navigation; use test_override_dialog_ui.py instead")
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pass_record_no_confirmation(flask_app_isolated, fail_records_csv):
    """Test that PASS tier record approval does NOT show confirmation."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Track dialog events
        dialogs_shown = []
        page.on("dialog", lambda dialog: dialogs_shown.append(dialog))

        try:
            # Upload CSV with FAIL records
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(fail_records_csv)

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for processing to complete (longer timeout for isolated Flask startup)
            await page.wait_for_selector('text=/processed|records/', timeout=15000)

            # Wait a bit for page to fully render
            await page.wait_for_timeout(500)

            # Review the file
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()

                # Wait for review table
                await page.wait_for_selector('table', timeout=5000)

                # Get all decision selects
                decision_selects = await page.query_selector_all('select.decision-select')

                # Select "Approved" for first record (PASS tier)
                if decision_selects:
                    await decision_selects[0].select_option(value="approved")

                    # Click Save - should NOT show confirmation for PASS record
                    dialogs_shown.clear()
                    save_button = await page.query_selector('button:has-text("Save")')
                    if save_button:
                        await save_button.click()

                        # Brief wait to allow any dialog to appear
                        await asyncio.sleep(0.5)

                        # No dialog should be shown for PASS tier record
                        assert len(dialogs_shown) == 0, "Confirmation dialog shown for PASS tier record"

        finally:
            await browser.close()


@pytest.mark.skip(reason="Deprecated - flaky due to multi-step navigation; use test_override_dialog_ui.py instead")
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_fail_record_shows_tier(flask_app_isolated, fail_records_csv):
    """Test that records with missing required fields show FAIL tier."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload CSV with FAIL records
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(fail_records_csv)

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for processing to complete (longer timeout for isolated Flask startup)
            await page.wait_for_selector('text=/processed|records/', timeout=15000)

            # Wait a bit for page to fully render
            await page.wait_for_timeout(500)

            # Review the file
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()

                # Wait for review table
                await page.wait_for_selector('table', timeout=5000)

                # Get all tier badges
                content = await page.content()

                # Should see FAIL tier badges for records with missing required fields
                assert 'tier-fail' in content or 'FAIL' in content, \
                    "No FAIL tier records found in review table"

                # Should also see at least one PASS record (first record is valid)
                assert 'tier-pass' in content or 'PASS' in content, \
                    "No PASS tier records found in review table"

        finally:
            await browser.close()


@pytest.mark.skip(reason="Deprecated - flaky due to multi-step navigation; use test_override_dialog_ui.py instead")
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_confirm_override_allows_approval(flask_app_isolated, fail_records_csv):
    """Test that confirming override dialog allows FAIL record approval."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Auto-confirm dialogs
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        try:
            # Upload CSV with FAIL records
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(fail_records_csv)

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for processing to complete (longer timeout for isolated Flask startup)
            await page.wait_for_selector('text=/processed|records/', timeout=15000)

            # Wait a bit for page to fully render
            await page.wait_for_timeout(500)

            # Review the file
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()

                # Wait for review table
                await page.wait_for_selector('table', timeout=5000)

                # Get all decision selects
                decision_selects = await page.query_selector_all('select.decision-select')

                # Select "Approved" for second record (FAIL)
                if len(decision_selects) >= 2:
                    await decision_selects[1].select_option(value="approved")

                    # Click Save and confirm override
                    save_button = await page.query_selector('button:has-text("Save")')
                    if save_button:
                        await save_button.click()

                        # Wait for save to complete
                        await asyncio.sleep(1)

                        # Should see success message or progress saved
                        content = await page.content()
                        assert any(text in content.lower() for text in ['saved', 'progress', 'complete']), \
                            "No success message shown after confirming override"

        finally:
            await browser.close()


@pytest.mark.skip(reason="Deprecated - flaky due to multi-step navigation; use test_override_dialog_ui.py instead")
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cancel_override_prevents_approval(flask_app_isolated, fail_records_csv):
    """Test that canceling override dialog prevents FAIL record approval."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Auto-dismiss dialogs (click Cancel)
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.dismiss()))

        try:
            # Upload CSV with FAIL records
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(fail_records_csv)

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for processing to complete (longer timeout for isolated Flask startup)
            await page.wait_for_selector('text=/processed|records/', timeout=15000)

            # Wait a bit for page to fully render
            await page.wait_for_timeout(500)

            # Review the file
            review_button = await page.query_selector('button:has-text("Review")')
            if review_button:
                await review_button.click()

                # Wait for review table
                await page.wait_for_selector('table', timeout=5000)

                # Get all decision selects
                decision_selects = await page.query_selector_all('select.decision-select')

                # Select "Approved" for second record (FAIL)
                if len(decision_selects) >= 2:
                    await decision_selects[1].select_option(value="approved")

                    # Click Save and cancel override
                    save_button = await page.query_selector('button:has-text("Save")')
                    if save_button:
                        await save_button.click()

                        # Wait for dialog to be dismissed
                        await asyncio.sleep(1)

                        # Decision should still show as "approved" but not saved
                        selected_value = await decision_selects[1].input_value()
                        assert selected_value == "approved", "Decision was cleared after canceling override"

                        # Should still see review page (not saved)
                        content = await page.content()
                        assert 'review' in content.lower() or 'table' in content.lower(), \
                            "Should still be on review page after canceling"

        finally:
            await browser.close()
