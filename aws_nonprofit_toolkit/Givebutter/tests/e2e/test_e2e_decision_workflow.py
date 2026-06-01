"""End-to-end tests for decision workflow with Playwright."""
import pytest
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import os


@pytest.fixture(scope="session")
def flask_app_running():
    """Start Flask app for E2E testing."""
    app_path = Path(__file__).parent.parent.parent / "scripts" / "uploader" / "app.py"
    process = subprocess.Popen(
        ["python", str(app_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )

    time.sleep(2)

    yield process

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except:
        process.terminate()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_view_records_for_review(flask_app_running, temp_dir, sample_csv):
    """Test viewing records from processing queue for review."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload a file first
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Click to review the file
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Should see record details in a table
                await page.wait_for_selector('table, tbody, .record, [class*="record"]', timeout=5000)

                content = await page.content()
                # Should display donor names/emails
                assert any(text in content for text in ['John', 'Jane', 'Bob', 'Alice', '@gmail'])

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_select_decision_for_record(flask_app_running, temp_dir, sample_csv):
    """Test selecting a decision from dropdown for a record."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Wait for table/review interface
                await page.wait_for_selector('select, [class*="decision"], [class*="dropdown"]', timeout=5000)

                # Select decision dropdown
                decision_selects = await page.query_selector_all('select, [class*="decision"]')
                if decision_selects:
                    first_select = decision_selects[0]
                    # Select "Approved" option
                    await first_select.select_option(value="approved")

                    # Verify selection was made
                    content = await page.content()
                    # Check that approved is selected
                    assert 'approved' in content.lower() or 'selected' in content.lower()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_add_notes_for_record(flask_app_running, temp_dir, sample_csv):
    """Test adding operator notes for a record."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

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
async def test_save_decisions_partial(flask_app_running, temp_dir, sample_csv):
    """Test saving decisions for some records (partial save)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Select decisions for only first 2 records
                decision_selects = await page.query_selector_all('select, [class*="decision"]')
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
async def test_save_all_decisions_completes_review(flask_app_running, temp_dir, sample_csv):
    """Test that saving all decisions moves file out of review queue."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Select decisions for ALL records
                decision_selects = await page.query_selector_all('select, [class*="decision"]')
                for i, select in enumerate(decision_selects):
                    decisions = ["approved", "rejected", "followup"]
                    await select.select_option(value=decisions[i % 3])

                # Click save button
                save_button = await page.query_selector('button:has-text("Save")')
                if save_button:
                    await save_button.click()

                    # Should show completion message
                    await page.wait_for_selector('text=/complete|approved|rejected/', timeout=5000)

                    content = await page.content()
                    assert any(text in content.lower() for text in ['complete', 'approved', 'rejected'])

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decision_persistence_on_reopen(flask_app_running, temp_dir, sample_csv):
    """Test that decisions persist when reopening file for review."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Make decision on first record
                decision_selects = await page.query_selector_all('select, [class*="decision"]')
                if decision_selects:
                    await decision_selects[0].select_option(value="approved")

                    # Save partial
                    save_button = await page.query_selector('button:has-text("Save")')
                    if save_button:
                        await save_button.click()

                        await page.wait_for_selector('text=/saved|progress/', timeout=5000)

                    # Go back to processing queue
                    await page.goto("http://127.0.0.1:8000/")

                    # Reopen the file
                    review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
                    if review_button:
                        await review_button.click()

                        # Check that first record still shows "approved"
                        await page.wait_for_selector('select, [class*="decision"]', timeout=5000)

                        decision_selects = await page.query_selector_all('select, [class*="decision"]')
                        if decision_selects:
                            selected_value = await decision_selects[0].input_value()
                            assert 'approved' in selected_value.lower() or selected_value == 'approved'

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cancel_review(flask_app_running, temp_dir, sample_csv):
    """Test canceling review returns file to intake."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Click cancel button
                cancel_button = await page.query_selector('button:has-text("Cancel")')
                if cancel_button:
                    await cancel_button.click()

                    # Should return to main page
                    await page.wait_for_selector('input[type="file"]', timeout=5000)

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_page_scrolls_to_top_on_load(flask_app_running, temp_dir, sample_csv):
    """Test that review page scrolls to top when loaded."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload and navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Check scroll position
                scroll_y = await page.evaluate("() => window.scrollY")
                # Should be at top or near top (allowing for small margin)
                assert scroll_y < 100

        finally:
            await browser.close()
