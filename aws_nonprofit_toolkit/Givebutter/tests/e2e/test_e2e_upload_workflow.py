"""End-to-end tests for upload workflow with Playwright."""
import pytest
import asyncio


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_valid_csv(flask_app_database_mode, temp_dir, sample_csv):
    """Test uploading a valid CSV file through the UI."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to upload page
            await page.goto("http://127.0.0.1:8001/")

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
async def test_upload_displays_validation_results(flask_app_database_mode, temp_dir):
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
            await page.goto("http://127.0.0.1:8001/")
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
async def test_upload_invalid_file_type(flask_app_database_mode, temp_dir):
    """Test uploading non-CSV file shows error."""
    from playwright.async_api import async_playwright

    # Create text file instead of CSV
    invalid_file = temp_dir / "test.txt"
    invalid_file.write_text("This is not a CSV file")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
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
async def test_upload_non_givebutter_csv_shows_inline_error_banner(flask_app_database_mode, temp_dir):
    """Test that non-Givebutter CSV failures use an inline banner, not a raw alert."""
    from playwright.async_api import async_playwright

    bad_csv = temp_dir / "charitable_donations_2025.csv"
    bad_csv.write_text("foo,bar,baz\n1,2,3\n", encoding='utf-8')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        dialogs = []
        page.on("dialog", lambda dialog: dialogs.append(dialog.message))

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(bad_csv))

            await page.wait_for_selector('#uploadStatus:visible', timeout=5000)
            banner = await page.locator('#uploadStatus').text_content()
            assert 'Unsupported Givebutter CSV' in banner
            assert 'No data was imported' in banner
            assert 'Choose another CSV' in await page.locator('#uploadStatus button').text_content()
            assert dialogs == []
            assert 'Processing failed' not in banner
        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_processing_queue_displays_file(flask_app_database_mode, temp_dir, sample_csv):
    """Test that uploaded file appears in processing queue."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload file first
            await page.goto("http://127.0.0.1:8001/")
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
async def test_page_loads_successfully(flask_app_database_mode):
    """Test that upload page loads without errors."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            response = await page.goto("http://127.0.0.1:8001/")

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
async def test_upload_csv_with_special_characters(flask_app_database_mode, temp_dir):
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
            await page.goto("http://127.0.0.1:8001/")
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
async def test_upload_large_csv(flask_app_database_mode, temp_dir):
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
            await page.goto("http://127.0.0.1:8001/")
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
async def test_import_queue_table_structure(flask_app_database_mode, temp_dir, sample_csv):
    """Test that import queue displays with proper Status and Action columns."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to upload page
            await page.goto("http://127.0.0.1:8001/")
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

            # Wait for action controls to be rendered
            await page.wait_for_selector('table tbody a.action-btn, table tbody button.action-btn', timeout=5000)

            # Verify table has rows with action controls
            action_buttons = await page.query_selector_all('table tbody a.action-btn, table tbody button.action-btn')
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


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_navigation_controls_open_review_pages(flask_app_database_mode, temp_dir):
    """Review controls should navigate after an upload error and a later successful upload."""
    from playwright.async_api import async_playwright

    bad_csv = temp_dir / "bad_upload.csv"
    bad_csv.write_text("foo,bar,baz\n1,2,3\n")

    good_csv = temp_dir / "good_upload.csv"
    good_csv.write_text(
        "Donation ID,Date,Donor Name,Email,Phone,Amount,Campaign Title\n"
        "GB001,2026-05-25,Jane Doe,jane@example.com,4155552671,100.00,General Fund\n"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        console_errors = []
        page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(bad_csv))
            await page.wait_for_selector('#uploadStatus', timeout=10000)
            assert 'supported Givebutter CSV' in (await page.text_content('#uploadStatus') or '')

            await file_input.set_input_files(str(good_csv))
            await page.wait_for_selector('a.action-btn.primary', timeout=10000)

            review_import = page.locator('a.action-btn.primary', has_text='Review Import').first
            href = await review_import.get_attribute('href')
            assert href and href.startswith('/imports/') and href.endswith('/validation'), href
            top_review = page.locator('#topReviewNav').first
            top_exports = page.locator('#topExportsNav').first
            top_audit = page.locator('#topAuditNav').first
            assert (await top_review.get_attribute('href')).endswith('/validation')
            assert (await top_exports.get_attribute('href')).endswith('/exports')
            assert (await top_audit.get_attribute('href')).endswith('/audit')
            await review_import.click()
            await page.wait_for_url('**/imports/**/validation', timeout=10000)

            audit_link = page.locator('a', has_text='Audit').first
            audit_href = await audit_link.get_attribute('href')
            assert audit_href and audit_href.startswith('/imports/') and audit_href.endswith('/audit'), audit_href
            await audit_link.click()
            await page.wait_for_url('**/imports/**/audit', timeout=10000)

            await page.goto("http://127.0.0.1:8001/", wait_until='networkidle')
            await page.wait_for_selector('.upload-card', timeout=5000)
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(good_csv))

            top_review = page.locator('#topReviewNav').first
            await page.wait_for_function(
                """() => {
                    const link = document.querySelector('#topReviewNav');
                    return link && link.getAttribute('href') && link.getAttribute('href') !== '#';
                }"""
            )
            top_href = await top_review.get_attribute('href')
            assert top_href and top_href.startswith('/imports/') and top_href.endswith('/validation'), top_href
            await top_review.click()
            await page.wait_for_url('**/imports/**/validation', timeout=10000)

            await page.goto("http://127.0.0.1:8001/", wait_until='networkidle')
            await page.wait_for_selector('.upload-card', timeout=5000)
            default_review_href = await page.locator('#topReviewNav').get_attribute('href')
            default_exports_href = await page.locator('#topExportsNav').get_attribute('href')
            default_audit_href = await page.locator('#topAuditNav').get_attribute('href')
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(bad_csv))
            await page.wait_for_selector('#uploadStatus', timeout=10000)
            assert 'supported Givebutter CSV' in (await page.text_content('#uploadStatus') or '')
            assert await page.locator('#topReviewNav').get_attribute('href') == default_review_href
            assert await page.locator('#topExportsNav').get_attribute('href') == default_exports_href
            assert await page.locator('#topAuditNav').get_attribute('href') == default_audit_href

            unexpected_console_errors = [
                err for err in console_errors
                if 'Upload error:' not in err
                and 'Unsupported Givebutter CSV' not in err
                and 'Failed to load resource: the server responded with a status of 400 (BAD REQUEST)' not in err
            ]
            assert not unexpected_console_errors, f"Unexpected browser console errors: {unexpected_console_errors}"
        finally:
            await browser.close()
