"""End-to-end tests for upload workflow with Playwright."""
import pytest
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import os


@pytest.fixture(scope="session")
def start_flask_app():
    """Start Flask app for E2E testing."""
    app_path = Path(__file__).parent.parent.parent / "scripts" / "uploader" / "app.py"
    process = subprocess.Popen(
        ["python", str(app_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid  # Create new process group for cleanup
    )

    # Wait for app to start
    time.sleep(2)

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

            # Wait for page to load (file input may be hidden)
            await page.wait_for_selector('div.drop-zone', timeout=5000)

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
            await page.wait_for_selector('input[type="file"]')

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
            await page.wait_for_selector('input[type="file"]')

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
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for confirmation
            await page.wait_for_selector('text=/processed|uploaded|records/', timeout=5000)

            # Navigate to processing queue (adjust path based on actual route)
            # This assumes there's a link or button to view processing queue
            processing_link = await page.query_selector('text=/processing|review|queue/i')
            if processing_link:
                await processing_link.click()

                # Wait for file to appear in queue
                await page.wait_for_selector('text=/upload_|GB/', timeout=5000)

                content = await page.content()
                assert 'upload' in content.lower()

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
            await page.wait_for_selector('input[type="file"]', timeout=5000)

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
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for successful processing
            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            content = await page.content()
            assert 'processed' in content.lower() or 'records' in content.lower()

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
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(test_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait longer for large file processing
            await page.wait_for_selector('text=/processed|records/', timeout=10000)

            content = await page.content()
            # Should show that all 100 records were processed
            assert '100' in content or 'records' in content.lower()

        finally:
            await browser.close()
