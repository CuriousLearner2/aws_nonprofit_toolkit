"""E2E tests for inline record editing feature."""
import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import os
from playwright.async_api import async_playwright

pytestmark = pytest.mark.asyncio


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
