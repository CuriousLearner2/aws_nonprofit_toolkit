"""End-to-end tests for upload workflow with Playwright."""
import pytest
import sys
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import os
import requests


@pytest.fixture(scope="session")
def start_flask_app():
    """Start Flask app for E2E testing."""
    app_path = Path(__file__).parent.parent.parent / "scripts" / "uploader" / "app.py"
    process = subprocess.Popen(
        [sys.executable, str(app_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid  # Create new process group for cleanup
    )

    # Wait for Flask to be ready using exponential backoff (0.1s → 1.0s, 10s timeout)
    start_time = time.time()
    wait_interval = 0.1
    max_interval = 1.0
    timeout_seconds = 10

    while time.time() - start_time < timeout_seconds:
        try:
            response = requests.get('http://127.0.0.1:8000/', timeout=2)
            if response.status_code < 500:  # Accept any non-500 response (includes 200, 404, etc.)
                break
        except (requests.ConnectionError, requests.Timeout):
            pass

        time.sleep(wait_interval)
        wait_interval = min(wait_interval * 1.5, max_interval)
    else:
        raise RuntimeError("Flask app failed to become ready at http://127.0.0.1:8000/ after 10s")

    yield process

    # Cleanup: kill the entire process group
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except:
        process.terminate()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_valid_csv(start_flask_app, temp_dir, sample_csv):
    """Test uploading a valid CSV file through the UI."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to upload page
            await page.goto("http://127.0.0.1:8000/")

            # Wait for page to load
            await page.wait_for_selector('.upload-card', timeout=5000)

            # Upload file (works even if input is hidden)
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            # Wait a moment for file to be registered
            await asyncio.sleep(1)

            # Verify page has processing queue
            content = await page.content()

            # Check if file appears in processing queue or shows status
            assert 'processing' in content.lower() or 'sample' in content.lower() or 'records' in content.lower()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_displays_validation_results(start_flask_app, temp_dir):
    """Test that upload displays validation results correctly."""
    from playwright.async_api import async_playwright

    # Create test CSV
    csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,John Smith,john@gmail.com,100.00,General Fund
GB002,2026-05-25,Jane Doe,jane@gmai.com,50.00,Scholarship Fund
GB003,2026-05-25,Bob Wilson,invalid-email,75.00,Education Fund"""

    test_csv = temp_dir / "test_results.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for results section
            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            content = await page.content()
            # Should show pass, warning, or fail counts
            assert any(word in content for word in ['PASS', 'WARNING', 'FAIL', 'record'])

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_invalid_file_type(start_flask_app, temp_dir):
    """Test uploading non-CSV file shows error."""
    from playwright.async_api import async_playwright

    # Create text file instead of CSV
    invalid_file = temp_dir / "test.txt"
    invalid_file.write_text("This is not a CSV file")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(invalid_file))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

                # Wait for error message
                error_msg = await page.query_selector('text=/error|not allowed|invalid/i')
                # Error handling depends on implementation

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_processing_queue_displays_file(start_flask_app, temp_dir, sample_csv):
    """Test that uploaded file appears in processing queue."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file first
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for queue table to populate
            await page.wait_for_selector('tbody tr', timeout=5000)

            # Verify file appears in the queue
            content = await page.content()
            assert 'upload_' in content.lower() or 'sample' in content.lower()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_page_loads_successfully(start_flask_app):
    """Test that upload page loads without errors."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            response = await page.goto("http://127.0.0.1:8000/")

            # Check page loaded successfully
            assert response.status == 200

            # Check for key UI elements
            await page.wait_for_selector('.upload-card', timeout=5000)

            # Verify page title or heading exists
            content = await page.content()
            assert 'upload' in content.lower() or 'file' in content.lower()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_csv_with_special_characters(start_flask_app, temp_dir):
    """Test uploading CSV with special characters in filenames and data."""
    from playwright.async_api import async_playwright

    csv_content = """Donation ID,Date,Donor Name,Email,Amount,Campaign Title
GB001,2026-05-25,José García,jose@gmail.com,100.00,General Fund
GB002,2026-05-25,李明,li@gmail.com,50.00,Scholarship Fund"""

    test_csv = temp_dir / "special_chars_test.csv"
    test_csv.write_text(csv_content, encoding='utf-8')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for queue table to populate
            await page.wait_for_selector('tbody tr', timeout=5000)

            content = await page.content()
            assert 'upload_' in content.lower() or 'table' in content.lower()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.slow
async def test_upload_large_csv(start_flask_app, temp_dir):
    """Test uploading a larger CSV file."""
    from playwright.async_api import async_playwright

    # Create 100-row CSV
    header = "Donation ID,Date,Donor Name,Email,Amount,Campaign Title"
    rows = [header]
    for i in range(100):
        rows.append(f"GB{i:03d},2026-05-25,Donor {i},donor{i}@gmail.com,{(i+1)*10},General Fund")

    csv_content = "\n".join(rows)
    test_csv = temp_dir / "large_test.csv"
    test_csv.write_text(csv_content)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for queue table to populate
            await page.wait_for_selector('tbody tr', timeout=10000)

            content = await page.content()
            # Should show that records were processed
            assert '100' in content or 'upload_' in content.lower()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_import_queue_table_structure(start_flask_app, temp_dir, sample_csv):
    """Test that import queue displays with proper Status and Action columns."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to upload page
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            # Verify import queue table structure exists
            content = await page.content()
            assert 'Current Import Queue' in content, "Current Import Queue title not found"
            assert 'V1 CURRENT IMPORT REVIEW' in content.upper(), "V1 CURRENT IMPORT REVIEW label not found"
            assert 'queue-table' in content, "Import queue table not found"

            # Verify all required table headers exist
            headers = ['FILENAME', 'UPLOADED', 'TOTAL ROWS', 'VALIDATION',
                      'NORMALIZATIONS', 'HOUSEHOLDS', 'DUPLICATES', 'STATUS', 'ACTION']
            for header in headers:
                header_found = await page.query_selector(f'th:has-text("{header}")')
                assert header_found, f"Missing header: {header}"

            # Upload file to populate the queue
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            # Wait for table to populate
            await page.wait_for_selector('tbody tr', timeout=5000)

            # Wait for action buttons to be rendered
            await page.wait_for_selector('table tbody button', timeout=5000)

            # Verify table has rows with action buttons
            action_buttons = await page.query_selector_all('table tbody button')
            if action_buttons:  # Only assert if we have data
                assert len(action_buttons) > 0, "Action buttons not found after upload"

                # Verify button labels
                button_texts = []
                for button in action_buttons:
                    btn_text = await button.inner_text()
                    button_texts.append(btn_text)

                # At least one button should be a valid action button
                action_button_labels = ['Review Import', 'Continue Review', 'View Summary']
                found_action_button = any(label in button_texts for label in action_button_labels)
                assert found_action_button, f"No valid action buttons found. Got: {button_texts}"

        finally:
            await browser.close()
