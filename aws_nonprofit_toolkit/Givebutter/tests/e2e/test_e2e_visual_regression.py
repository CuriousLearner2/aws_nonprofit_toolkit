"""Visual regression tests using Playwright screenshots."""
import pytest
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import os


@pytest.fixture(scope="session")
def flask_app_for_visual():
    """Start Flask app for visual tests."""
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


@pytest.fixture
def screenshots_dir(temp_dir):
    """Create screenshots directory for baseline and actual."""
    baseline_dir = temp_dir / "screenshots" / "baseline"
    actual_dir = temp_dir / "screenshots" / "actual"
    diff_dir = temp_dir / "screenshots" / "diff"

    baseline_dir.mkdir(parents=True, exist_ok=True)
    actual_dir.mkdir(parents=True, exist_ok=True)
    diff_dir.mkdir(parents=True, exist_ok=True)

    return {
        'baseline': baseline_dir,
        'actual': actual_dir,
        'diff': diff_dir
    }


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_page_visual(flask_app_for_visual, screenshots_dir):
    """Capture screenshot of upload page."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            # Take screenshot
            screenshot_path = screenshots_dir['actual'] / "upload_page.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            # Verify screenshot was taken
            assert screenshot_path.exists()
            assert screenshot_path.stat().st_size > 0

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_processing_queue_visual(flask_app_for_visual, temp_dir, sample_csv, screenshots_dir):
    """Capture screenshot of processing queue after upload."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})

        try:
            # Upload file
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            # Wait for results
            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Take screenshot of results page
            screenshot_path = screenshots_dir['actual'] / "processing_queue.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            assert screenshot_path.exists()
            assert screenshot_path.stat().st_size > 0

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_table_visual(flask_app_for_visual, temp_dir, sample_csv, screenshots_dir):
    """Capture screenshot of review table with records."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1400, 'height': 900})

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

                # Wait for table to load
                await page.wait_for_selector('table, tbody', timeout=5000)

                # Take screenshot of review table
                screenshot_path = screenshots_dir['actual'] / "review_table.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                assert screenshot_path.exists()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decision_dropdown_visual(flask_app_for_visual, temp_dir, sample_csv, screenshots_dir):
    """Capture screenshot of decision dropdown."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})

        try:
            # Navigate to review
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

                # Wait for dropdown
                await page.wait_for_selector('select, [class*="decision"]', timeout=5000)

                # Click dropdown to open
                selects = await page.query_selector_all('select, [class*="decision"]')
                if selects:
                    await selects[0].click()

                    # Take screenshot with dropdown open
                    screenshot_path = screenshots_dir['actual'] / "decision_dropdown.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)

                    assert screenshot_path.exists()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_notes_textarea_visual(flask_app_for_visual, temp_dir, sample_csv, screenshots_dir):
    """Capture screenshot of notes textarea."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})

        try:
            # Navigate to review
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

                # Wait for textarea
                textareas = await page.query_selector_all('textarea, [class*="notes"]')
                if textareas:
                    # Add some text to textarea
                    await textareas[0].fill("Sample note for verification")

                    # Take screenshot with text
                    screenshot_path = screenshots_dir['actual'] / "notes_textarea.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)

                    assert screenshot_path.exists()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_error_message_visual(flask_app_for_visual, temp_dir, screenshots_dir):
    """Capture screenshot of error message (if invalid file uploaded)."""
    from playwright.async_api import async_playwright

    # Create invalid file
    invalid_file = temp_dir / "invalid.txt"
    invalid_file.write_text("Not a CSV file")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(invalid_file))

            # Look for error message (may appear before or after submit)
            # Some browsers show error inline
            screenshot_path = screenshots_dir['actual'] / "error_message.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            assert screenshot_path.exists()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mobile_viewport_upload(flask_app_for_visual, screenshots_dir):
    """Test upload page on mobile viewport (375px)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 375, 'height': 667})

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('input[type="file"]')

            # Take screenshot of mobile view
            screenshot_path = screenshots_dir['actual'] / "mobile_upload_page.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            assert screenshot_path.exists()
            assert screenshot_path.stat().st_size > 0

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tablet_viewport_review(flask_app_for_visual, temp_dir, sample_csv, screenshots_dir):
    """Test review page on tablet viewport (768px)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 768, 'height': 1024})

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

                # Wait for table
                await page.wait_for_selector('table, tbody', timeout=5000)

                # Take screenshot of tablet view
                screenshot_path = screenshots_dir['actual'] / "tablet_review_page.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                assert screenshot_path.exists()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_desktop_review_wide(flask_app_for_visual, temp_dir, sample_csv, screenshots_dir):
    """Test review page on wide desktop viewport (1920px)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})

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

                # Wait for table
                await page.wait_for_selector('table, tbody', timeout=5000)

                # Take screenshot of wide desktop view
                screenshot_path = screenshots_dir['actual'] / "desktop_wide_review.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                assert screenshot_path.exists()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_success_message_visual(flask_app_for_visual, temp_dir, sample_csv, screenshots_dir):
    """Capture screenshot of success message after saving decisions."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 720})

        try:
            # Upload and make decisions
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

                # Make decisions for all records
                decision_selects = await page.query_selector_all('select, [class*="decision"]')
                for i, select in enumerate(decision_selects):
                    decisions = ["approved", "rejected", "followup"]
                    await select.select_option(value=decisions[i % 3])

                # Save
                save_button = await page.query_selector('button:has-text("Save")')
                if save_button:
                    await save_button.click()

                    # Wait for success message
                    await page.wait_for_selector('text=/complete|approved|rejected/', timeout=5000)

                    # Take screenshot of success
                    screenshot_path = screenshots_dir['actual'] / "success_message.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)

                    assert screenshot_path.exists()

        finally:
            await browser.close()


def compare_screenshots(baseline_path, actual_path, diff_path, threshold=0.01):
    """
    Compare two screenshots and generate diff image.

    threshold: Allowed difference ratio (0.01 = 1%)
    Returns: (matches, difference_ratio)
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        pytest.skip("PIL not installed - screenshot comparison skipped")

    if not baseline_path.exists():
        # First time - save as baseline
        return None, None

    baseline_img = Image.open(baseline_path)
    actual_img = Image.open(actual_path)

    # Resize actual to match baseline if needed
    if baseline_img.size != actual_img.size:
        actual_img = actual_img.resize(baseline_img.size)

    # Compare images
    diff = ImageChops.difference(baseline_img, actual_img)

    # Calculate difference ratio
    bbox = diff.getbbox()
    if bbox is None:
        return True, 0.0  # No difference

    diff_pixels = sum(diff.crop(bbox).getdata())
    total_pixels = bbox[2] * bbox[3] * 3  # RGB channels
    difference_ratio = diff_pixels / (total_pixels * 255)

    # Save diff image
    diff.save(diff_path)

    matches = difference_ratio < threshold
    return matches, difference_ratio


@pytest.mark.e2e
def test_screenshot_regression_upload_page(screenshots_dir):
    """Compare upload page screenshot against baseline."""
    actual = screenshots_dir['actual'] / "upload_page.png"
    baseline = screenshots_dir['baseline'] / "upload_page.png"
    diff = screenshots_dir['diff'] / "upload_page_diff.png"

    if not actual.exists():
        pytest.skip("Actual screenshot not found - run visual test first")

    matches, ratio = compare_screenshots(baseline, actual, diff)

    if matches is None:
        # First run - save as baseline
        import shutil
        shutil.copy(actual, baseline)
        pytest.skip("Baseline saved - run test again to compare")
    else:
        assert matches, f"Screenshot differs by {ratio*100:.2f}% - see {diff}"


@pytest.mark.e2e
def test_screenshot_regression_review_table(screenshots_dir):
    """Compare review table screenshot against baseline."""
    actual = screenshots_dir['actual'] / "review_table.png"
    baseline = screenshots_dir['baseline'] / "review_table.png"
    diff = screenshots_dir['diff'] / "review_table_diff.png"

    if not actual.exists():
        pytest.skip("Actual screenshot not found")

    matches, ratio = compare_screenshots(baseline, actual, diff)

    if matches is None:
        import shutil
        shutil.copy(actual, baseline)
        pytest.skip("Baseline saved")
    else:
        assert matches, f"Screenshot differs by {ratio*100:.2f}%"
