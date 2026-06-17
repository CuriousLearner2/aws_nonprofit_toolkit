"""
E2E browser tests for Validation Review DOM/UX behavior.

IMPORTANT: These tests verify actual Playwright browser interactions with the DOM,
not API responses. They must assert visible behavior: error borders, status badges,
issues cells.

Infrastructure:
- Database-backed Flask testing with ImportBatch/RawImportRow seeding
- Validation service calculates row_status and issues on-the-fly
- No explicit ReviewItem seeding needed (service-generated)
- Flask runs in background thread, Playwright drives browser

Synchronization:
- Use page.wait_for_function() to poll DOM state (not arbitrary sleeps)
- Wait for specific condition: status badge text, error border color, issues cell text
- Each wait has explicit timeout (5000ms default)

Assertions:
- Hard assertions only (test fails immediately if condition not met)
- Assert both "email" AND "invalid" terms in Issues cell (not either/or)
- Assert exact status text ('Blocking' not just 'not No issues')

See E2E_TEST_RELIABILITY.md for patterns and troubleshooting.
"""

import pytest
import asyncio
import sys
import tempfile
import threading
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    create_db_engine,
)
from scripts.uploader.app import app


@pytest.fixture
def e2e_database_and_app():
    """
    Create a database, seed it with test data, start Flask server in thread.

    Returns:
        Tuple of (database_url, db_path, app_instance)
    """
    # Create temporary database
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    # Set environment for Flask
    os.environ['HOUSEHOLDER_REPOSITORY'] = 'database'
    os.environ['GIVEBUTTER_DATABASE_URL'] = database_url

    # Configure Flask for testing
    app.config['TESTING'] = True

    yield database_url, db_path, app

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_invalid_email_updates_visible_row_status_and_issues(
    e2e_database_and_app,
):
    """
    GOAL: Verify the Review Status invariant through actual browser DOM behavior.

    Invariant: No visible field-level Error may coexist with Review Status = No issues.

    When email field has an error (red border), the review status must NOT say "No issues".
    When email is corrected, both the error styling and blocking status should clear.

    Flow:
    1. Seed database with valid email
    2. Load validation page in browser
    3. Change email to invalid ('john@example' - missing domain)
    4. Blur field to trigger autosave
    5. Assert error styling (red border) AND status shows 'Blocking'
    6. Change email back to valid ('john@example.com')
    7. Blur field to trigger autosave
    8. Assert error styling clears AND status recalculates to 'No issues' or drops the blocking badge
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='email-test-batch',
            filename='email_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with valid email
        raw_row = RawImportRow(
            batch_id='email-test-batch',
            row_index=1,
            raw_csv_data={
                'name': 'John Smith',
                'date': '2026-01-15',
                'email': 'john@example.com',
                'phone': '(555) 123-4567',
                'amount': '100.00',
                'address': '123 Main St'
            }
        )
        session.add(raw_row)
        session.flush()
        raw_row_id = raw_row.id

        # Create ImportContact (required by database repository)
        import_contact = ImportContact(
            batch_id='email-test-batch',
            raw_import_row_id=raw_row_id,
            first_name='John',
            last_name='Smith',
            email='john@example.com',
            phone='(555) 123-4567',
            address_line1='123 Main St',
            amount=100.00
        )
        session.add(import_contact)
        session.flush()
        session.commit()

        # Start Flask server
        def run_flask():
            flask_app.run(host='127.0.0.1', port=8001, debug=False, use_reloader=False)

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Wait for server
        await asyncio.sleep(2)

        # Verify server is accessible
        import requests
        max_retries = 5
        for attempt in range(max_retries):
            try:
                requests.get('http://127.0.0.1:8001/imports/email-test-batch/validation', timeout=2)
                break
            except (requests.ConnectionError, requests.Timeout):
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise RuntimeError("Flask server failed to start")

        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to validation page
                await page.goto('http://127.0.0.1:8001/imports/email-test-batch/validation')

                # Wait for table to load
                await page.wait_for_selector('table tbody tr', timeout=5000)

                # Find email input
                email_input = await page.query_selector('input[data-testid="email-input-1"]')
                assert email_input is not None, "Email input not found"

                # ===== PART 1: Invalid email triggers error state =====
                print(f"\n=== TEST PART 1: Invalid Email ===")

                await email_input.fill('john@example')  # Invalid: missing domain
                await email_input.evaluate("el => el.blur()")  # Trigger autosave
                # Wait for row status to show 'Blocking' badge (indication of error)
                await page.wait_for_function(
                    "() => document.querySelector('.row-status-badge')?.textContent?.trim() === 'Blocking'",
                    timeout=5000
                )

                # A1: Red error border
                border_color = await email_input.evaluate(
                    "el => window.getComputedStyle(el).borderColor"
                )
                is_red = any(
                    pattern in str(border_color)
                    for pattern in ['rgb(239', 'ef4444', '239, 68, 68']
                )
                assert is_red, f"A1 FAILED: Email should have red border, got: {border_color}"
                print("✓ A1: Email field shows red error border")

                # A2 & A3: Status shows 'Blocking' (not 'No issues')
                status_badge = await page.query_selector('.row-status-badge')
                assert status_badge is not None, "A2 FAILED: Status badge should appear after error"

                badge_text = await status_badge.inner_text()
                assert badge_text == 'Blocking', f"A3 FAILED: Status should be 'Blocking', got: {badge_text}"
                print(f"✓ A2: Review Status changed to badge")
                print(f"✓ A3: Review Status is 'Blocking' (not 'No issues')")

                # A4: Issues show email error
                issues_cell = await page.query_selector('td.issues-cell')
                assert issues_cell is not None, "Issues cell not found"

                issues_text = await issues_cell.inner_text()
                # Both 'email' and 'invalid' should appear together (format: "email — Invalid email format")
                issues_lower = issues_text.lower()
                has_email = 'email' in issues_lower
                has_invalid = 'invalid' in issues_lower
                assert has_email and has_invalid, f"A4 FAILED: Issues should contain both 'email' and 'invalid', got: {issues_text}"
                print(f"✓ A4: Issues cell shows email error: {issues_text.strip()}")

                # ===== PART 2: Valid email clears error state =====
                print(f"\n=== TEST PART 2: Valid Email ===")

                await email_input.fill('john@example.com')  # Valid
                await email_input.evaluate("el => el.blur()")  # Trigger autosave
                # Wait for row status to NOT be 'Blocking' (error cleared)
                await page.wait_for_function(
                    "() => document.querySelector('.row-status-badge')?.textContent?.trim() !== 'Blocking'",
                    timeout=5000
                )

                # A5: Red border clears
                border_color_after = await email_input.evaluate(
                    "el => window.getComputedStyle(el).borderColor"
                )
                is_red_after = any(
                    pattern in str(border_color_after)
                    for pattern in ['rgb(239', 'ef4444', '239, 68, 68']
                )
                assert not is_red_after, f"A5 FAILED: Error border should clear, got: {border_color_after}"
                print(f"✓ A5: Email error styling cleared")

                # A6: Status recalculates (blocking badge gone or status changed)
                status_badge_after = await page.query_selector('.row-status-badge')
                if status_badge_after:
                    badge_text_after = await status_badge_after.inner_text()
                    assert badge_text_after != 'Blocking', f"A6 FAILED: Status should change from Blocking, got: {badge_text_after}"
                else:
                    # Dropdown should reappear if badge is gone
                    dropdown = await page.query_selector('.row-status-dropdown')
                    # It's OK if dropdown doesn't exist - the important thing is the badge is gone

                print(f"✓ A6: Review Status recalculated after correction")

                print(f"\n=== ALL TESTS PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()
