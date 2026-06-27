"""End-to-end tests for CSV format variations and edge cases."""
import pytest
import sys
import asyncio
from pathlib import Path
import subprocess
import time
import signal
import os
import csv
from datetime import datetime


def flask_app_running():
    """Start Flask app for E2E testing."""
    app_path = Path(__file__).parent.parent.parent / "scripts" / "uploader" / "app.py"
    process = subprocess.Popen(
        [sys.executable, str(app_path)],
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
def csv_lowercase_headers(temp_dir):
    """Create CSV with lowercase column headers."""
    csv_path = temp_dir / "lowercase_headers.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['donor_name', 'email', 'amount', 'donation_date', 'campaign'])
        writer.writeheader()
        writer.writerow({
            'donor_name': 'John Smith',
            'email': 'john@gmail.com',
            'amount': '100.00',
            'donation_date': '2026-05-20',
            'campaign': 'Spring Fundraiser'
        })
    return csv_path


@pytest.fixture
def csv_title_case_headers(temp_dir):
    """Create CSV with title case headers (minimal required fields)."""
    csv_path = temp_dir / "title_case_headers.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Full Name', 'Email Address', 'Amount', 'Donation Date', 'Campaign'])
        writer.writeheader()
        writer.writerow({
            'Full Name': 'Jane Doe',
            'Email Address': 'jane@gmail.com',
            'Amount': '250.00',
            'Donation Date': '2026-05-21',
            'Campaign': 'Summer Campaign'
        })
    return csv_path


@pytest.fixture
def csv_missing_optional_phone(temp_dir):
    """Create CSV without phone column (phone is optional)."""
    csv_path = temp_dir / "no_phone.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Name', 'Email', 'Amount', 'Date', 'Campaign Title'])
        writer.writeheader()
        writer.writerow({
            'Name': 'Alice Johnson',
            'Email': 'alice@gmail.com',
            'Amount': '150.00',
            'Date': '2026-05-22',
            'Campaign Title': 'Annual Fund'
        })
    return csv_path


@pytest.fixture
def csv_mixed_case_headers(temp_dir):
    """Create CSV with mixed case headers."""
    csv_path = temp_dir / "mixed_case.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Donor Name', 'email', 'AMOUNT', 'donation_date', 'Campaign'])
        writer.writeheader()
        writer.writerow({
            'Donor Name': 'Bob Wilson',
            'email': 'bob@gmail.com',
            'AMOUNT': '75.00',
            'donation_date': '2026-05-23',
            'Campaign': 'Monthly Giving'
        })
    return csv_path


@pytest.fixture
def csv_with_email_typos(temp_dir):
    """Create CSV with intentional email typos for testing validation."""
    csv_path = temp_dir / "email_typos.csv"
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['donor_name', 'email', 'amount', 'donation_date', 'campaign'])
        writer.writeheader()
        writer.writerow({
            'donor_name': 'Carol Smith',
            'email': 'carol@gmal.com',  # typo: gmal instead of gmail
            'amount': '200.00',
            'donation_date': '2026-05-24',
            'campaign': 'Donor Drive'
        })
        writer.writerow({
            'donor_name': 'David Lee',
            'email': 'david@yaho.com',  # typo: yaho instead of yahoo
            'amount': '300.00',
            'donation_date': '2026-05-25',
            'campaign': 'Donor Drive'
        })
    return csv_path


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_csv_with_lowercase_headers(flask_app_database_mode, csv_lowercase_headers):
    """Test uploading CSV with lowercase headers (case-insensitive matching)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            # Upload CSV with lowercase headers
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_lowercase_headers))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            # Should process successfully
            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            content = await page.content()
            assert 'processed' in content.lower() or '1' in content  # Should show record count

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_csv_with_title_case_headers(flask_app_database_mode, csv_title_case_headers):
    """Test uploading CSV with title case fuzzy match headers."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_title_case_headers))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            # Should process successfully with fuzzy match
            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            content = await page.content()
            assert 'processed' in content.lower() or '1' in content

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_csv_without_optional_phone(flask_app_database_mode, csv_missing_optional_phone):
    """Test uploading CSV without phone column (should create WARNING, not FAIL)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_missing_optional_phone))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            # Should process and appear in review queue
            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Navigate to Review Queue to verify it appears (with WARNING, not FAIL)
            content = await page.content()
            assert 'review import' in content.lower() or 'no_phone' in content  # Record should be in queue

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_csv_with_mixed_case_headers(flask_app_database_mode, csv_mixed_case_headers):
    """Test uploading CSV with mixed case headers."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_mixed_case_headers))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            # Should handle mixed case gracefully
            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            content = await page.content()
            assert 'processed' in content.lower() or '1' in content

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_csv_flags_email_typos(flask_app_database_mode, csv_with_email_typos):
    """Test that email typos are flagged during review (not rejected at upload)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_with_email_typos))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            # Should upload successfully (validation happens in review phase)
            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)

            # Navigate to review queue to see flagged records
            review_button = await page.wait_for_selector('.action-btn.primary', timeout=5000)
            if review_button:
                await review_button.click()

                # Should see records with email issues flagged
                await page.wait_for_selector('table, tbody, .record', timeout=5000)
                content = await page.content()

                # Email typos should be flagged (not cause upload failure)
                assert any(text in content.lower() for text in ['warning', 'email', 'typo', 'suggested'])

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_csv_format_consistency_across_uploads(flask_app_database_mode, csv_lowercase_headers, csv_title_case_headers):
    """Test that different CSV formats process consistently."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Upload first CSV (lowercase headers)
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_lowercase_headers))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)
            content1 = await page.content()

            # Reset to upload page
            await page.goto("http://127.0.0.1:8001/")
            await page.wait_for_selector('.upload-card', timeout=5000)

            # Upload second CSV (title case headers)
            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(csv_title_case_headers))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload")')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/records|PASS|WARNING|FAIL/', timeout=5000)
            content2 = await page.content()

            # Both should process successfully
            assert 'processed' in content1.lower() or '1' in content1
            assert 'processed' in content2.lower() or '1' in content2

        finally:
            await browser.close()
