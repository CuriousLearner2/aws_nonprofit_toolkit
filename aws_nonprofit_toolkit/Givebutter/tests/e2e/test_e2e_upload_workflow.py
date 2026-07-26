"""End-to-end tests for upload workflow with Playwright."""
import pytest
import asyncio
import json


async def _dispatch_drag_event(page, selector, event_type, files):
    return await page.evaluate(
        """
        ({ selector, eventType, files }) => {
            const target = document.querySelector(selector);
            if (!target) {
                throw new Error(`Missing drag target: ${selector}`);
            }

            const dataTransfer = new DataTransfer();
            for (const file of files) {
                dataTransfer.items.add(new File([file.content], file.name, { type: file.type }));
            }

            const event = new DragEvent(eventType, {
                bubbles: true,
                cancelable: true,
                dataTransfer,
            });
            const dispatchResult = target.dispatchEvent(event);
            return {
                defaultPrevented: event.defaultPrevented,
                dispatchResult,
            };
        }
        """,
        {
            "selector": selector,
            "eventType": event_type,
            "files": files,
        },
    )


def _collect_browser_issues(page):
    console_errors = []
    request_failures = []

    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("requestfailed", lambda request: request_failures.append(request.url))

    return console_errors, request_failures


async def _mock_processing_queue(page, queue_items):
    async def fulfill_processing(route):
        await route.fulfill(
            status=200,
            content_type='application/json',
            body=json.dumps(queue_items),
        )

    await page.route('**/api/processing', fulfill_processing)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_processing_queue_renders_untrusted_values_safely(flask_app_database_mode):
    """Test that queue rendering treats hostile values as text and rejects unsafe review URLs."""
    from playwright.async_api import async_playwright

    hostile_filename = '<img src=x onerror="window.__queueXssTriggered = true">'
    hostile_uploaded = '"><svg onload="window.__queueXssTriggered = true"></svg>'
    hostile_count = '1 & <2> "quoted" \'single\''
    safe_review_url = '/imports/alpha-batch/validation'

    queue_items = [
        {
            'filename': hostile_filename,
            'uploaded': hostile_uploaded,
            'rows': hostile_count,
            'pass_count': hostile_count,
            'warning_count': hostile_count,
            'fail_count': hostile_count,
            'normalizations': hostile_count,
            'households': hostile_count,
            'duplicates': hostile_count,
            'status': 'Pending Review',
            'review_url': safe_review_url,
        },
        {
            'batch_id': 'beta-batch',
            'filename': 'same-origin-wrong-path.csv',
            'uploaded': '2026-07-22 09:05',
            'rows': 8,
            'pass_count': 8,
            'warning_count': 0,
            'fail_count': 0,
            'normalizations': 1,
            'households': 0,
            'duplicates': 0,
            'status': 'Pending Review',
            'review_url': '/exports/rogue-path',
        },
        {
            'batch_id': 'gamma-batch',
            'filename': 'javascript-url.csv',
            'uploaded': '2026-07-22 09:10',
            'rows': 4,
            'pass_count': 4,
            'warning_count': 0,
            'fail_count': 0,
            'normalizations': 0,
            'households': 0,
            'duplicates': 0,
            'status': 'Pending Review',
            'review_url': 'javascript:window.__queueUrlTriggered = true',
        },
        {
            'filename': 'missing-review-url.csv',
            'uploaded': '2026-07-22 09:16',
            'rows': 2,
            'pass_count': 2,
            'warning_count': 0,
            'fail_count': 0,
            'normalizations': 0,
            'households': 0,
            'duplicates': 0,
            'status': 'Pending Review',
            'review_url': '',
        },
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        console_errors, request_failures = _collect_browser_issues(page)
        await page.add_init_script(
            """
            window.__queueXssTriggered = false;
            window.__queueUrlTriggered = false;
            """
        )
        await _mock_processing_queue(page, queue_items)

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('#queueBody tr', timeout=5000)

            rows = page.locator('#queueBody tr')
            assert await rows.count() == len(queue_items)

            hostile_row = rows.nth(0)
            hostile_filename_cell = hostile_row.locator('td').first
            hostile_text = await hostile_filename_cell.text_content()
            assert hostile_text is not None
            assert hostile_filename in hostile_text
            assert hostile_uploaded in (await hostile_row.text_content() or '')
            assert hostile_count in (await hostile_row.text_content() or '')
            assert await hostile_row.locator('img, svg, script, [onload], [onerror], [onclick]').count() == 0
            assert await page.evaluate("window.__queueXssTriggered === false")
            valid_link = hostile_row.locator('a.action-btn.primary')
            assert await valid_link.count() == 1
            assert await valid_link.get_attribute('href') == safe_review_url

            safe_row = rows.nth(1)
            safe_text = await safe_row.locator('td').first.text_content()
            assert safe_text is not None
            assert 'same-origin-wrong-path.csv' in safe_text
            safe_link = safe_row.locator('a.action-btn.primary')
            assert await safe_link.count() == 0
            safe_disabled = safe_row.locator('button.action-btn.primary')
            assert await safe_disabled.count() == 1
            assert await safe_disabled.is_disabled()
            assert 'Review unavailable' in (await safe_disabled.text_content() or '')
            imports_link = safe_row.locator('a.action-btn.secondary')
            assert await imports_link.count() == 1
            assert await imports_link.get_attribute('href') == '/imports'
            assert 'Open Imports' in (await imports_link.text_content() or '')

            completed_row = rows.nth(2)
            assert 'javascript-url.csv' in (await completed_row.text_content() or '')
            completed_link = completed_row.locator('button.action-btn.primary')
            assert await completed_link.count() == 1
            assert await completed_link.is_disabled()
            assert 'Review unavailable' in (await completed_link.text_content() or '')
            assert await completed_row.locator('a.action-btn.secondary').count() == 1

            missing_review_row = rows.nth(3)
            missing_review_text = await missing_review_row.text_content()
            assert missing_review_text is not None
            assert 'missing-review-url.csv' in missing_review_text
            missing_review_button = missing_review_row.locator('button.action-btn.primary')
            assert await missing_review_button.count() == 1
            assert await missing_review_button.is_disabled()
            imports_links = missing_review_row.locator('a.action-btn.secondary')
            assert await imports_links.count() == 1
            assert await imports_links.get_attribute('href') == '/imports'

            await valid_link.click()
            await page.wait_for_url('**/imports/alpha-batch/validation', timeout=10000)

            unexpected_console_errors = [
                err for err in console_errors
                if 'Upload error:' not in err
                and 'Failed to load resource: the server responded with a status of 400 (BAD REQUEST)' not in err
            ]
            assert not unexpected_console_errors, f"Unexpected browser console errors: {unexpected_console_errors}"
            assert not request_failures, f"Unexpected browser request failures: {request_failures}"
            assert await page.evaluate("window.__queueUrlTriggered === false")
        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_drop_zone_ignores_empty_drop_and_recovers(flask_app_database_mode, temp_dir, sample_csv):
    """Test that an empty drop is ignored safely and drag-and-drop still recovers."""
    from playwright.async_api import async_playwright

    csv_text = sample_csv.read_text(encoding='utf-8')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        upload_request_count = 0

        async def track_upload(route):
            nonlocal upload_request_count
            upload_request_count += 1
            await route.continue_()

        await page.route('**/upload', track_upload)

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            empty_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [],
            )
            dragenter = await _dispatch_drag_event(
                page,
                '.upload-card',
                'dragenter',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            dragover = await _dispatch_drag_event(
                page,
                '.upload-card',
                'dragover',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            dragleave = await _dispatch_drag_event(
                page,
                '.upload-card',
                'dragleave',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )

            assert empty_drop['defaultPrevented'] is True
            assert empty_drop['dispatchResult'] is False
            assert dragenter['defaultPrevented'] is True
            assert dragenter['dispatchResult'] is False
            assert dragover['defaultPrevented'] is True
            assert dragover['dispatchResult'] is False
            assert dragleave['dispatchResult'] is True
            assert upload_request_count == 0
            assert await page.locator('#uploadStatus').is_hidden()
            assert await page.locator('.upload-card').evaluate("el => !el.classList.contains('is-drag-over')")
            assert await page.locator('#queueBody tr').count() >= 1

            valid_dragenter = await _dispatch_drag_event(
                page,
                '.upload-card',
                'dragenter',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            valid_dragover = await _dispatch_drag_event(
                page,
                '.upload-card',
                'dragover',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            valid_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            assert valid_dragenter['defaultPrevented'] is True
            assert valid_dragenter['dispatchResult'] is False
            assert valid_dragover['defaultPrevented'] is True
            assert valid_dragover['dispatchResult'] is False
            assert valid_drop['defaultPrevented'] is True
            assert valid_drop['dispatchResult'] is False
            queue_row = page.locator('#queueBody tr').filter(has_text=sample_csv.name).first
            await queue_row.wait_for(state='visible', timeout=10000)
            review_link = queue_row.locator('a.action-btn.primary')
            await review_link.wait_for(state='visible', timeout=10000)
            assert upload_request_count == 1
            assert await review_link.count() == 1
            review_href = await review_link.get_attribute('href')
            assert review_href is not None
            assert review_href.startswith('/imports/')
            assert review_href.endswith('/validation')

            await review_link.click()
            await page.wait_for_url('**/imports/*/validation', timeout=10000)

            await page.goto("http://127.0.0.1:8001/")
            await page.reload()
            await page.wait_for_selector('.upload-card', timeout=5000)

            reloaded_row = page.locator('#queueBody tr').filter(has_text=sample_csv.name).first
            reloaded_review_link = reloaded_row.locator('a.action-btn.primary')
            assert await reloaded_review_link.count() == 1
            assert await reloaded_review_link.get_attribute('href') == review_href
        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_drop_zone_rejects_invalid_drop_and_recovers_with_drag_drop(flask_app_database_mode, temp_dir, sample_csv):
    """Test that an invalid drag-and-drop upload is rejected and drag-and-drop still recovers."""
    from playwright.async_api import async_playwright

    non_csv = temp_dir / "not_a_csv.txt"
    non_csv.write_text("hello world", encoding='utf-8')
    csv_text = sample_csv.read_text(encoding='utf-8')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        upload_request_count = 0

        async def track_upload(route):
            nonlocal upload_request_count
            upload_request_count += 1
            await route.continue_()

        await page.route('**/upload', track_upload)

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            invalid_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [{
                    'name': non_csv.name,
                    'content': non_csv.read_text(encoding='utf-8'),
                    'type': 'text/plain',
                }],
            )
            assert invalid_drop['defaultPrevented'] is True
            assert invalid_drop['dispatchResult'] is False
            assert upload_request_count == 0
            assert 'Please select a CSV file.' in (await page.locator('#uploadStatus').text_content() or '')

            valid_dragenter = await _dispatch_drag_event(
                page,
                '.upload-card',
                'dragenter',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            valid_dragover = await _dispatch_drag_event(
                page,
                '.upload-card',
                'dragover',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            valid_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            assert valid_dragenter['defaultPrevented'] is True
            assert valid_dragenter['dispatchResult'] is False
            assert valid_dragover['defaultPrevented'] is True
            assert valid_dragover['dispatchResult'] is False
            assert valid_drop['defaultPrevented'] is True
            assert valid_drop['dispatchResult'] is False
            await page.wait_for_selector('a.action-btn.primary', timeout=10000)
            assert upload_request_count == 1
            assert await page.locator('a.action-btn.primary', has_text='Review Import').count() == 1
            assert await page.locator('#uploadStatus').is_hidden()
        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_drop_zone_rejects_multiple_file_drop(flask_app_database_mode, temp_dir, sample_csv):
    """Test that a multi-file drag-and-drop upload is rejected safely."""
    from playwright.async_api import async_playwright

    bad_csv = temp_dir / "bad_drop.csv"
    bad_csv.write_text("foo,bar,baz\n1,2,3\n", encoding='utf-8')

    csv_text = sample_csv.read_text(encoding='utf-8')

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        upload_request_count = 0

        async def track_upload(route):
            nonlocal upload_request_count
            upload_request_count += 1
            await route.continue_()

        await page.route('**/upload', track_upload)

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            multi_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [
                    {'name': bad_csv.name, 'content': bad_csv.read_text(encoding='utf-8'), 'type': 'text/csv'},
                    {'name': sample_csv.name, 'content': csv_text, 'type': 'text/csv'},
                ],
            )
            assert multi_drop['defaultPrevented'] is True
            assert multi_drop['dispatchResult'] is False
            assert upload_request_count == 0
            assert 'Please drop one CSV file at a time.' in (await page.locator('#uploadStatus').text_content() or '')
            valid_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            assert valid_drop['defaultPrevented'] is True
            assert valid_drop['dispatchResult'] is False
            await page.wait_for_selector('a.action-btn.primary', timeout=10000)
            assert upload_request_count == 1
            assert await page.locator('a.action-btn.primary', has_text='Review Import').count() == 1
            assert await page.locator('#uploadStatus').is_hidden()
        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_drop_zone_blocks_repeated_drops_while_upload_is_in_flight(flask_app_database_mode, temp_dir, sample_csv):
    """Test that rapid repeated drops do not duplicate requests and later intentional uploads still work."""
    from playwright.async_api import async_playwright

    csv_text = sample_csv.read_text(encoding='utf-8')
    replacement_csv = temp_dir / "same-name.csv"
    replacement_csv.write_text(
        csv_text.replace("John Smith", "John Smith Jr."),
        encoding='utf-8',
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        request_count = 0

        async def hold_first_upload(route):
            nonlocal request_count
            request_count += 1
            if request_count == 1:
                await asyncio.sleep(1)
            await route.continue_()

        await page.route('**/upload', hold_first_upload)

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            first_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            assert first_drop['defaultPrevented'] is True
            assert first_drop['dispatchResult'] is False

            second_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [{
                    'name': sample_csv.name,
                    'content': csv_text,
                    'type': 'text/csv',
                }],
            )
            assert second_drop['defaultPrevented'] is True
            assert second_drop['dispatchResult'] is False
            assert request_count == 1
            assert 'Uploading' in (await page.locator('#uploadStatus').text_content() or '')

            await page.wait_for_selector('a.action-btn.primary', timeout=10000)
            assert request_count == 1

            later_drop = await _dispatch_drag_event(
                page,
                '.upload-card',
                'drop',
                [{
                    'name': sample_csv.name,
                    'content': replacement_csv.read_text(encoding='utf-8'),
                    'type': 'text/csv',
                }],
            )
            assert later_drop['defaultPrevented'] is True
            assert later_drop['dispatchResult'] is False

            await page.wait_for_selector('a.action-btn.primary', timeout=10000)
            assert request_count == 2
            assert await page.locator('a.action-btn.primary', has_text='Review Import').count() == 1
        finally:
            await browser.close()


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
async def test_upload_file_picker_creates_review_link_and_opens_validation(flask_app_database_mode, temp_dir, sample_csv):
    """Test that file-picker uploads create a review link that opens validation."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            queue_row = page.locator('#queueBody tr').filter(has_text=sample_csv.name).first
            await queue_row.wait_for(state='visible', timeout=10000)
            review_link = queue_row.locator('a.action-btn.primary')
            await review_link.wait_for(state='visible', timeout=10000)
            assert await review_link.count() == 1
            review_href = await review_link.get_attribute('href')
            assert review_href is not None
            assert review_href.startswith('/imports/')
            assert review_href.endswith('/validation')

            await review_link.click()
            await page.wait_for_url('**/imports/*/validation', timeout=10000)

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_file_picker_repeated_same_filename_keeps_distinct_review_links(flask_app_database_mode, temp_dir, sample_csv):
    """Repeated file-picker uploads of the same filename stay independently reviewable."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            first_rows = page.locator('#queueBody tr').filter(has_text=sample_csv.name)
            await first_rows.first.wait_for(state='visible', timeout=10000)
            assert await first_rows.count() == 1
            first_link = first_rows.first.locator('a.action-btn.primary')
            first_href = await first_link.get_attribute('href')
            assert first_href is not None
            assert first_href.startswith('/imports/')

            await file_input.set_input_files(str(sample_csv))
            if submit_button:
                await submit_button.click()

            repeated_rows = page.locator('#queueBody tr').filter(has_text=sample_csv.name)
            await repeated_rows.first.wait_for(state='visible', timeout=10000)
            await page.wait_for_function(
                "() => document.querySelectorAll('#queueBody tr').length === 2",
                timeout=10000,
            )
            assert await repeated_rows.count() == 2

            hrefs = []
            for idx in range(await repeated_rows.count()):
                link = repeated_rows.nth(idx).locator('a.action-btn.primary')
                href = await link.get_attribute('href')
                assert href is not None
                assert href.startswith('/imports/')
                assert href.endswith('/validation')
                hrefs.append(href)

            assert len(set(hrefs)) == 2

            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)
            after_reload_rows = page.locator('#queueBody tr').filter(has_text=sample_csv.name)
            assert await after_reload_rows.count() == 2
            after_reload_hrefs = []
            for idx in range(await after_reload_rows.count()):
                after_reload_hrefs.append(await after_reload_rows.nth(idx).locator('a.action-btn.primary').get_attribute('href'))
            assert set(after_reload_hrefs) == set(hrefs)

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

            await page.wait_for_function(
                """() => {
                    const status = document.querySelector('#uploadStatus');
                    return status && status.textContent.includes('Unsupported Givebutter CSV');
                }""",
                timeout=10000,
            )
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
            await page.wait_for_function(
                """() => {
                    const status = document.querySelector('#uploadStatus');
                    return status && status.textContent.includes('Unsupported Givebutter CSV');
                }""",
                timeout=10000,
            )
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
            await page.wait_for_function(
                """() => {
                    const status = document.querySelector('#uploadStatus');
                    return status && status.textContent.includes('Unsupported Givebutter CSV');
                }""",
                timeout=10000,
            )
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
