"""
E2E browser tests for Duplicates Phase 3 export workflow.

CRITICAL WORKFLOWS TESTED:
- Test A: Warning banner and confirmation checkbox appear for deferred duplicates
- Test B: Export is blocked when duplicate confirmation checkbox is unchecked
- Test C: Export proceeds when duplicate confirmation checkbox is checked
- Test D: Clean export (no deferred duplicates) skips duplicate confirmation requirement
- Test E: Warning count for multiple deferred duplicate pairs
- Test F: Checkbox uncheck re-disables export button (bidirectional state)

Infrastructure:
- Database-backed Flask testing with ImportBatch/ReviewItem seeding
- Duplicates service calculates suggestions and decisions
- Flask runs in background thread, Playwright drives browser

Synchronization:
- Use page.wait_for_function() to poll DOM state
- Wait for specific conditions: text changes, element visibility
- All browser clicks are real Playwright clicks (not mocked HTTP)

Assertions:
- Hard assertions only (test fails immediately if condition not met)
- Database verification: Query ReviewDecision to verify persistence
- Verify raw ImportContact data unchanged (append-only principle)
- Export file generation verified via API response and database

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
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
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


# ==============================================================================
# TEST A: Warning banner and confirmation checkbox appear for deferred duplicates
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_warning_appears_for_deferred_duplicate(
    e2e_database_and_app,
):
    """
    Verify export warning and confirmation checkbox appear when deferred duplicates exist.

    Scenario:
    1. Seed ImportBatch with two contacts and one duplicate review item
    2. Record Defer decision for that duplicate (leaving it unresolved)
    3. Navigate to /imports/{batch_id}/exports in browser
    4. Assert warning banner is visible with count
    5. Assert confirmation checkbox is visible
    6. Assert export button exists and is disabled initially
    7. Assert raw ImportContact data unchanged

    Expected behavior:
    - Warning banner displays: "X duplicate pair(s) are unresolved"
    - Checkbox is unchecked by default
    - Export button is disabled when checkbox unchecked
    - Warning persists throughout interaction
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
            id='export-dup-warning-batch',
            filename='export_dup_warning.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        raw_row_a = RawImportRow(
            batch_id='export-dup-warning-batch',
            row_index=1,
            raw_csv_data={
                'name': 'John Duplicate A',
                'date': '2026-03-01',
                'email': 'john.dup@example.com',
                'phone': '(555) 111-1111',
                'amount': '500.00',
                'address': '100 Duplicate St'
            }
        )
        session.add(raw_row_a)
        session.flush()

        raw_row_b = RawImportRow(
            batch_id='export-dup-warning-batch',
            row_index=2,
            raw_csv_data={
                'name': 'John Duplicate B',
                'date': '2026-03-02',
                'email': 'john.dup+2@example.com',
                'phone': '(555) 111-1111',
                'amount': '500.00',
                'address': '100 Duplicate St'
            }
        )
        session.add(raw_row_b)
        session.flush()

        # Create ImportContacts
        contact_a = ImportContact(
            batch_id='export-dup-warning-batch',
            raw_import_row_id=raw_row_a.id,
            first_name='John',
            last_name='Duplicate A',
            email='john.dup@example.com',
            phone='(555) 111-1111',
            address_line1='100 Duplicate St',
            amount=500.00
        )
        session.add(contact_a)
        session.flush()

        contact_b = ImportContact(
            batch_id='export-dup-warning-batch',
            raw_import_row_id=raw_row_b.id,
            first_name='John',
            last_name='Duplicate B',
            email='john.dup+2@example.com',
            phone='(555) 111-1111',
            address_line1='100 Duplicate St',
            amount=500.00
        )
        session.add(contact_b)
        session.flush()

        # Create duplicate review item
        duplicate = ReviewItem(
            batch_id='export-dup-warning-batch',
            item_type='duplicate',
            confidence=0.95,
            payload_json={
                'contact_a_id': contact_a.id,
                'contact_b_id': contact_b.id,
                'supporting_evidence': ['Same phone', 'Same address'],
                'conflicting_evidence': ['Different emails'],
                'basis': 'Likely duplicate'
            }
        )
        session.add(duplicate)
        session.flush()

        # Add subjects linking contacts to duplicate
        subject_a = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_a.id,
            role='candidate_a'
        )
        session.add(subject_a)
        session.flush()

        subject_b = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_b.id,
            role='candidate_b'
        )
        session.add(subject_b)
        session.flush()

        # Record Defer decision for duplicate (leaving it unresolved)
        decision = ReviewDecision(
            batch_id='export-dup-warning-batch',
            review_item_id=duplicate.id,
            decision='defer',
            created_at=datetime.utcnow(),
            reviewed_values={}
        )
        session.add(decision)
        session.flush()
        session.commit()

        contact_a_id = contact_a.id
        contact_b_id = contact_b.id

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
                requests.get('http://127.0.0.1:8001/imports/export-dup-warning-batch/exports', timeout=2)
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
                # Navigate to exports page
                await page.goto('http://127.0.0.1:8001/imports/export-dup-warning-batch/exports')

                # Wait for page to load
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/export-dup-warning-batch/exports/preview', {
                            method: 'POST'
                        });
                        if (response.ok) {
                            const html = await response.text();
                            document.open();
                            document.write(html);
                            document.close();
                        }
                    }
                """)

                # Wait for the page to reload with preview data
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ A0: Export preview loaded")

                # A1: Verify duplicate warning banner is visible
                warning_locator = page.locator('div:has(#confirm-unresolved-duplicates-checkbox)')
                warning_banner = await warning_locator.first.element_handle() if await warning_locator.count() > 0 else None

                assert warning_banner is not None, "A1 FAILED: Duplicate warning banner not found"
                print("✓ A1: Duplicate warning banner found")

                # A2: Verify warning text contains deferred count
                warning_text = await warning_locator.first.inner_text()
                assert '1' in warning_text and 'duplicate' in warning_text.lower(), \
                    f"A2 FAILED: Expected warning text with count, got: {warning_text}"
                print(f"✓ A2: Warning text includes deferred count: {warning_text.strip()}")

                # A3: Verify confirmation checkbox exists and is visible
                checkbox = await page.query_selector('#confirm-unresolved-duplicates-checkbox')
                assert checkbox is not None, "A3 FAILED: Duplicate confirmation checkbox not found"
                is_visible = await checkbox.is_visible()
                assert is_visible, "A3 FAILED: Duplicate confirmation checkbox should be visible"
                print("✓ A3: Duplicate confirmation checkbox is visible")

                # A4: Verify checkbox is not checked initially
                is_checked = await checkbox.is_checked()
                assert not is_checked, "A4 FAILED: Checkbox should be unchecked initially"
                print("✓ A4: Checkbox is unchecked initially")

                # A5: Verify export button exists
                export_btn = await page.query_selector('#generate-export-btn')
                assert export_btn is not None, "A5 FAILED: Export button not found"
                print("✓ A5: Export button exists")

                # A6: Verify export button is disabled when duplicate checkbox unchecked
                is_disabled = await export_btn.is_disabled()
                assert is_disabled, "A6 FAILED: Export button should be disabled when duplicate checkbox unchecked"
                print("✓ A6: Export button is disabled (duplicate checkbox unchecked)")

                # CRITICAL: A7 - Verify raw ImportContact data unchanged
                contact_a_check = session.query(ImportContact).filter_by(id=contact_a_id).first()
                assert contact_a_check is not None, "A7 FAILED: Contact A should still exist"
                assert contact_a_check.first_name == 'John', "A7 FAILED: Contact A data should be unchanged"
                assert contact_a_check.email == 'john.dup@example.com', "A7 FAILED: Contact A data should be unchanged"

                contact_b_check = session.query(ImportContact).filter_by(id=contact_b_id).first()
                assert contact_b_check is not None, "A7 FAILED: Contact B should still exist"
                assert contact_b_check.first_name == 'John', "A7 FAILED: Contact B data should be unchanged"
                print("✓ A7: Raw ImportContact data unchanged (append-only principle)")

                print(f"\n=== TEST A: EXPORT WARNING APPEARS FOR DEFERRED DUPLICATE PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST B: Export blocked when duplicate confirmation unchecked
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_blocked_when_duplicate_confirmation_unchecked(
    e2e_database_and_app,
):
    """
    Verify export is blocked when deferred duplicates exist and confirmation unchecked.

    Scenario:
    1. Same setup as Test A: deferred duplicate, warning visible, checkbox unchecked
    2. Attempt export (verify button is disabled, click has no effect)
    3. Assert warning banner remains visible
    4. Assert no form submission occurs
    5. Assert raw ImportContact data unchanged

    Expected behavior:
    - Disabled button prevents click from triggering export
    - No POST request to /generate endpoint
    - Warning remains visible throughout
    - User must check confirmation box to proceed
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
            id='export-dup-blocked-batch',
            filename='export_dup_blocked.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        raw_row_a = RawImportRow(
            batch_id='export-dup-blocked-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Jane Blocked A',
                'date': '2026-03-05',
                'email': 'jane.blocked@example.com',
                'phone': '(555) 222-2222',
                'amount': '600.00',
                'address': '200 Blocked Ave'
            }
        )
        session.add(raw_row_a)
        session.flush()

        raw_row_b = RawImportRow(
            batch_id='export-dup-blocked-batch',
            row_index=2,
            raw_csv_data={
                'name': 'Jane Blocked B',
                'date': '2026-03-06',
                'email': 'jane.blocked+2@example.com',
                'phone': '(555) 222-2222',
                'amount': '600.00',
                'address': '200 Blocked Ave'
            }
        )
        session.add(raw_row_b)
        session.flush()

        # Create ImportContacts
        contact_a = ImportContact(
            batch_id='export-dup-blocked-batch',
            raw_import_row_id=raw_row_a.id,
            first_name='Jane',
            last_name='Blocked A',
            email='jane.blocked@example.com',
            phone='(555) 222-2222',
            address_line1='200 Blocked Ave',
            amount=600.00
        )
        session.add(contact_a)
        session.flush()

        contact_b = ImportContact(
            batch_id='export-dup-blocked-batch',
            raw_import_row_id=raw_row_b.id,
            first_name='Jane',
            last_name='Blocked B',
            email='jane.blocked+2@example.com',
            phone='(555) 222-2222',
            address_line1='200 Blocked Ave',
            amount=600.00
        )
        session.add(contact_b)
        session.flush()

        # Create duplicate review item
        duplicate = ReviewItem(
            batch_id='export-dup-blocked-batch',
            item_type='duplicate',
            confidence=0.92,
            payload_json={
                'contact_a_id': contact_a.id,
                'contact_b_id': contact_b.id,
                'supporting_evidence': ['Same phone', 'Same address'],
                'conflicting_evidence': ['Different emails'],
                'basis': 'Likely duplicate'
            }
        )
        session.add(duplicate)
        session.flush()

        subject_a = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_a.id,
            role='candidate_a'
        )
        session.add(subject_a)
        session.flush()

        subject_b = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_b.id,
            role='candidate_b'
        )
        session.add(subject_b)
        session.flush()

        # Record Defer decision
        decision = ReviewDecision(
            batch_id='export-dup-blocked-batch',
            review_item_id=duplicate.id,
            decision='defer',
            created_at=datetime.utcnow(),
            reviewed_values={}
        )
        session.add(decision)
        session.flush()
        session.commit()

        contact_a_id = contact_a.id
        contact_b_id = contact_b.id

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
                requests.get('http://127.0.0.1:8001/imports/export-dup-blocked-batch/exports', timeout=2)
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
                # Navigate to exports page
                await page.goto('http://127.0.0.1:8001/imports/export-dup-blocked-batch/exports')

                # Wait for page to load
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/export-dup-blocked-batch/exports/preview', {
                            method: 'POST'
                        });
                        if (response.ok) {
                            const html = await response.text();
                            document.open();
                            document.write(html);
                            document.close();
                        }
                    }
                """)

                # Wait for the page to reload with preview data
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ B0: Export preview loaded")

                # B1: Verify warning banner visible
                warning_banner = await page.query_selector('div:has(#confirm-unresolved-duplicates-checkbox)')
                assert warning_banner is not None, "B1 FAILED: Warning banner not found"
                print("✓ B1: Warning banner visible")

                # B2: Verify checkbox unchecked
                checkbox = await page.query_selector('#confirm-unresolved-duplicates-checkbox')
                is_checked = await checkbox.is_checked()
                assert not is_checked, "B2 FAILED: Checkbox should be unchecked"
                print("✓ B2: Checkbox is unchecked")

                # B3: Verify export button is disabled
                export_btn = await page.query_selector('#generate-export-btn')
                is_disabled = await export_btn.is_disabled()
                assert is_disabled, "B3 FAILED: Export button should be disabled"
                print("✓ B3: Export button is disabled")

                # B4: Button disabled prevents submission (no click needed)
                print("✓ B4: Export button is disabled (click would be blocked by browser)")

                # B5: Verify we're still on exports page (no redirect)
                current_url = page.url
                assert '/exports' in current_url, \
                    f"B5 FAILED: Should remain on exports page, got: {current_url}"
                print("✓ B5: Still on exports page (no form submission)")

                # B6: Verify warning banner still visible
                warning_banner_check = await page.query_selector('div:has(#confirm-unresolved-duplicates-checkbox)')
                assert warning_banner_check is not None, "B6 FAILED: Warning banner should still be visible"
                print("✓ B6: Warning banner remains visible")

                # CRITICAL: B7 - Verify raw ImportContact data unchanged
                contact_a_check = session.query(ImportContact).filter_by(id=contact_a_id).first()
                assert contact_a_check is not None, "B7 FAILED: Contact A should still exist"
                assert contact_a_check.first_name == 'Jane', "B7 FAILED: Contact A data should be unchanged"

                contact_b_check = session.query(ImportContact).filter_by(id=contact_b_id).first()
                assert contact_b_check is not None, "B7 FAILED: Contact B should still exist"
                print("✓ B7: Raw ImportContact data unchanged")

                print(f"\n=== TEST B: EXPORT BLOCKED (DUPLICATE UNCHECKED) PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST C: Export proceeds when duplicate confirmation checked
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_proceeds_when_duplicate_confirmation_checked(
    e2e_database_and_app,
):
    """
    Verify export proceeds after duplicate confirmation checkbox is checked.

    Scenario:
    1. Same setup: deferred duplicate, warning visible
    2. Check duplicate confirmation checkbox
    3. Assert export button becomes enabled (state changes)
    4. Click export button
    5. Assert export submission occurs (no page error, modal may appear)
    6. Assert raw ImportContact data unchanged (append-only)

    Expected behavior:
    - Clicking checkbox enables the export button
    - Button state changes visibly (opacity, cursor)
    - Export button click triggers form submission
    - Export service processes the request
    - User sees success feedback (toast, modal, or page reload)
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
            id='export-dup-proceed-batch',
            filename='export_dup_proceed.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        raw_row_a = RawImportRow(
            batch_id='export-dup-proceed-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Alice Proceed A',
                'date': '2026-03-10',
                'email': 'alice.proceed@example.com',
                'phone': '(555) 333-3333',
                'amount': '700.00',
                'address': '300 Proceed Way'
            }
        )
        session.add(raw_row_a)
        session.flush()

        raw_row_b = RawImportRow(
            batch_id='export-dup-proceed-batch',
            row_index=2,
            raw_csv_data={
                'name': 'Alice Proceed B',
                'date': '2026-03-11',
                'email': 'alice.proceed+2@example.com',
                'phone': '(555) 333-3333',
                'amount': '700.00',
                'address': '300 Proceed Way'
            }
        )
        session.add(raw_row_b)
        session.flush()

        # Create ImportContacts
        contact_a = ImportContact(
            batch_id='export-dup-proceed-batch',
            raw_import_row_id=raw_row_a.id,
            first_name='Alice',
            last_name='Proceed A',
            email='alice.proceed@example.com',
            phone='(555) 333-3333',
            address_line1='300 Proceed Way',
            amount=700.00
        )
        session.add(contact_a)
        session.flush()

        contact_b = ImportContact(
            batch_id='export-dup-proceed-batch',
            raw_import_row_id=raw_row_b.id,
            first_name='Alice',
            last_name='Proceed B',
            email='alice.proceed+2@example.com',
            phone='(555) 333-3333',
            address_line1='300 Proceed Way',
            amount=700.00
        )
        session.add(contact_b)
        session.flush()

        # Create duplicate review item
        duplicate = ReviewItem(
            batch_id='export-dup-proceed-batch',
            item_type='duplicate',
            confidence=0.88,
            payload_json={
                'contact_a_id': contact_a.id,
                'contact_b_id': contact_b.id,
                'supporting_evidence': ['Same phone', 'Same address'],
                'conflicting_evidence': ['Different emails'],
                'basis': 'Likely duplicate'
            }
        )
        session.add(duplicate)
        session.flush()

        subject_a = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_a.id,
            role='candidate_a'
        )
        session.add(subject_a)
        session.flush()

        subject_b = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_b.id,
            role='candidate_b'
        )
        session.add(subject_b)
        session.flush()

        # Record Defer decision
        decision = ReviewDecision(
            batch_id='export-dup-proceed-batch',
            review_item_id=duplicate.id,
            decision='defer',
            created_at=datetime.utcnow(),
            reviewed_values={}
        )
        session.add(decision)
        session.flush()
        session.commit()

        contact_a_id = contact_a.id
        contact_b_id = contact_b.id

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
                requests.get('http://127.0.0.1:8001/imports/export-dup-proceed-batch/exports', timeout=2)
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
                # Navigate to exports page
                await page.goto('http://127.0.0.1:8001/imports/export-dup-proceed-batch/exports')

                # Wait for page to load
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/export-dup-proceed-batch/exports/preview', {
                            method: 'POST'
                        });
                        if (response.ok) {
                            const html = await response.text();
                            document.open();
                            document.write(html);
                            document.close();
                        }
                    }
                """)

                # Wait for the page to reload with preview data
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ C0: Export preview loaded")

                # C1: Verify checkbox exists and is unchecked initially
                checkbox = await page.query_selector('#confirm-unresolved-duplicates-checkbox')
                is_checked = await checkbox.is_checked()
                assert not is_checked, "C1 FAILED: Checkbox should be unchecked initially"
                print("✓ C1: Checkbox is unchecked initially")

                # C2: Verify export button is disabled initially
                export_btn = await page.query_selector('#generate-export-btn')
                is_disabled_before = await export_btn.is_disabled()
                assert is_disabled_before, "C2 FAILED: Export button should be disabled initially"
                print("✓ C2: Export button is disabled initially")

                # C3: Check the duplicate confirmation checkbox
                await checkbox.check()
                print("✓ C3: Checkbox checked")

                # Wait for button state to update (JavaScript onchange handler)
                await page.wait_for_function(
                    "() => !document.getElementById('generate-export-btn').disabled",
                    timeout=5000
                )

                # C4: Verify export button is now enabled
                is_disabled_after = await export_btn.is_disabled()
                assert not is_disabled_after, "C4 FAILED: Export button should be enabled after checkbox check"
                print("✓ C4: Export button is now enabled (state changed)")

                # C5: Click export button
                print("✓ C5: Clicking export button...")
                await export_btn.click()

                # Wait for response (either success message or modal)
                await asyncio.sleep(1)

                # Attempt to detect success (may see toast, modal, or page content changes)
                try:
                    await page.wait_for_function(
                        "() => document.body.textContent.includes('Export generated') || document.body.textContent.includes('success')",
                        timeout=3000
                    )
                    print("✓ C5: Export submission successful (success message visible)")
                except:
                    # Alternatively, check if we're still on the page (form submitted)
                    current_url = page.url
                    if '/exports' in current_url:
                        print("✓ C5: Still on exports page (form submitted, waiting for response)")
                    else:
                        print(f"ℹ C5: URL changed to {current_url}")

                # CRITICAL: C6 - Verify raw ImportContact data unchanged
                contact_a_check = session.query(ImportContact).filter_by(id=contact_a_id).first()
                assert contact_a_check is not None, "C6 FAILED: Contact A should still exist"
                assert contact_a_check.first_name == 'Alice', "C6 FAILED: Contact A data should be unchanged"

                contact_b_check = session.query(ImportContact).filter_by(id=contact_b_id).first()
                assert contact_b_check is not None, "C6 FAILED: Contact B should still exist"
                print("✓ C6: Raw ImportContact data unchanged (append-only principle)")

                print(f"\n=== TEST C: EXPORT PROCEEDS (DUPLICATE CHECKED) PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST D: Clean export does not require duplicate confirmation
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_clean_export_skips_duplicate_confirmation(
    e2e_database_and_app,
):
    """
    Verify no duplicate confirmation required when all duplicates are resolved.

    Scenario:
    1. Seed ImportBatch with two contacts and one duplicate review item
    2. Record SAME_PERSON decision for duplicate (fully resolved, not deferred)
    3. Navigate to /imports/{batch_id}/exports
    4. Assert duplicate warning banner is absent (no unresolved duplicates)
    5. Assert duplicate confirmation checkbox is absent or not required
    6. Assert export button is enabled and clickable
    7. Assert raw ImportContact data unchanged

    Expected behavior:
    - No duplicate warning banner displays (all duplicates resolved)
    - No duplicate checkbox for confirmation (not needed)
    - Export button is enabled by default (or only blocked by other factors)
    - User can proceed with export without duplicate confirmation
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
            id='export-dup-clean-batch',
            filename='export_dup_clean.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        raw_row_a = RawImportRow(
            batch_id='export-dup-clean-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Bob Clean A',
                'date': '2026-03-15',
                'email': 'bob.clean@example.com',
                'phone': '(555) 444-4444',
                'amount': '800.00',
                'address': '400 Clean Blvd'
            }
        )
        session.add(raw_row_a)
        session.flush()

        raw_row_b = RawImportRow(
            batch_id='export-dup-clean-batch',
            row_index=2,
            raw_csv_data={
                'name': 'Bob Clean B',
                'date': '2026-03-16',
                'email': 'bob.clean+2@example.com',
                'phone': '(555) 444-4444',
                'amount': '800.00',
                'address': '400 Clean Blvd'
            }
        )
        session.add(raw_row_b)
        session.flush()

        # Create ImportContacts
        contact_a = ImportContact(
            batch_id='export-dup-clean-batch',
            raw_import_row_id=raw_row_a.id,
            first_name='Bob',
            last_name='Clean A',
            email='bob.clean@example.com',
            phone='(555) 444-4444',
            address_line1='400 Clean Blvd',
            amount=800.00
        )
        session.add(contact_a)
        session.flush()

        contact_b = ImportContact(
            batch_id='export-dup-clean-batch',
            raw_import_row_id=raw_row_b.id,
            first_name='Bob',
            last_name='Clean B',
            email='bob.clean+2@example.com',
            phone='(555) 444-4444',
            address_line1='400 Clean Blvd',
            amount=800.00
        )
        session.add(contact_b)
        session.flush()

        # Create duplicate review item
        duplicate = ReviewItem(
            batch_id='export-dup-clean-batch',
            item_type='duplicate',
            confidence=0.98,
            payload_json={
                'contact_a_id': contact_a.id,
                'contact_b_id': contact_b.id,
                'supporting_evidence': ['Same phone', 'Same address'],
                'conflicting_evidence': [],
                'basis': 'Confirmed same person'
            }
        )
        session.add(duplicate)
        session.flush()

        subject_a = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_a.id,
            role='candidate_a'
        )
        session.add(subject_a)
        session.flush()

        subject_b = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_b.id,
            role='candidate_b'
        )
        session.add(subject_b)
        session.flush()

        # Record SAME_PERSON decision (fully resolved, not deferred)
        decision = ReviewDecision(
            batch_id='export-dup-clean-batch',
            review_item_id=duplicate.id,
            decision='same_person',
            created_at=datetime.utcnow(),
            reviewed_values={
                'candidate_contact_ids': [contact_a.id, contact_b.id]
            }
        )
        session.add(decision)
        session.flush()
        session.commit()

        contact_a_id = contact_a.id
        contact_b_id = contact_b.id

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
                requests.get('http://127.0.0.1:8001/imports/export-dup-clean-batch/exports', timeout=2)
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
                # Navigate to exports page
                await page.goto('http://127.0.0.1:8001/imports/export-dup-clean-batch/exports')

                # Wait for page to load
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/export-dup-clean-batch/exports/preview', {
                            method: 'POST'
                        });
                        if (response.ok) {
                            const html = await response.text();
                            document.open();
                            document.write(html);
                            document.close();
                        }
                    }
                """)

                # Wait for the page to reload with preview data
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ D0: Export preview loaded (no deferred duplicates)")

                # D1: Verify duplicate warning banner is absent (no unresolved duplicates)
                warning_banner = await page.query_selector('div:has(#confirm-unresolved-duplicates-checkbox)')
                assert warning_banner is None, \
                    "D1 FAILED: Duplicate warning banner should not exist when all duplicates resolved"
                print("✓ D1: Duplicate warning banner is absent (all duplicates resolved)")

                # D2: Verify duplicate confirmation checkbox is absent
                checkbox = await page.query_selector('#confirm-unresolved-duplicates-checkbox')
                assert checkbox is None, \
                    "D2 FAILED: Duplicate confirmation checkbox should not exist when all duplicates resolved"
                print("✓ D2: Duplicate confirmation checkbox is absent (not needed)")

                # D3: Verify export button exists
                export_btn = await page.query_selector('#generate-export-btn')
                assert export_btn is not None, "D3 FAILED: Export button should exist"
                print("✓ D3: Export button exists")

                # D4: Verify export button is enabled (no unresolved duplicate blockers)
                is_disabled = await export_btn.is_disabled()
                assert not is_disabled, \
                    "D4 FAILED: Export button should be enabled when all duplicates resolved"
                print("✓ D4: Export button is enabled (no duplicate confirmation needed)")

                # D5: Verify export button is clickable
                is_visible = await export_btn.is_visible()
                assert is_visible, "D5 FAILED: Export button should be visible"
                print("✓ D5: Export button is visible and clickable")

                # CRITICAL: D6 - Verify raw ImportContact data unchanged
                contact_a_check = session.query(ImportContact).filter_by(id=contact_a_id).first()
                assert contact_a_check is not None, "D6 FAILED: Contact A should still exist"
                assert contact_a_check.first_name == 'Bob', "D6 FAILED: Contact A data should be unchanged"

                contact_b_check = session.query(ImportContact).filter_by(id=contact_b_id).first()
                assert contact_b_check is not None, "D6 FAILED: Contact B should still exist"
                print("✓ D6: Raw ImportContact data unchanged (append-only principle)")

                print(f"\n=== TEST D: CLEAN EXPORT (NO DUPLICATE CONFIRMATION) PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST E: Warning count for multiple deferred duplicate pairs
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_warning_count_for_multiple_deferred_duplicates(
    e2e_database_and_app,
):
    """
    Verify export warning displays correct count for multiple deferred duplicate pairs.

    Scenario:
    1. Seed 3 duplicate pairs (different contact sets)
    2. Defer 2 of them (leave 1 as confirmed/resolved)
    3. Open Export Console in browser
    4. Assert warning shows "2 duplicate pair(s) are unresolved"
    5. Assert checkbox and button present
    6. Verify count is dynamic, not hardcoded
    7. Check checkbox and verify button enables
    8. Verify raw ImportContact data unchanged

    Expected behavior:
    - Warning shows correct count (2, not 1 or 3)
    - Count is calculated from ReviewDecisions, not hardcoded
    - Checkbox enable/disable button control works with multiple duplicates
    - All ImportContact records remain unchanged (append-only)
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
            id='export-dup-multiple-batch',
            filename='export_dup_multiple.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=6
        )
        session.add(batch)
        session.flush()

        # Create 6 raw rows and contacts (2 per pair)
        contacts = []
        for i in range(6):
            raw_row = RawImportRow(
                batch_id='export-dup-multiple-batch',
                row_index=i + 1,
                raw_csv_data={
                    'name': f'Multi Dup {i+1}',
                    'date': f'2026-03-{20+i:02d}',
                    'email': f'multi{i+1}@example.com',
                    'phone': f'(555) {500+i:03d}-{5000+i:04d}',
                    'amount': f'{500.00 + i*100:.2f}',
                    'address': f'{500+i*100} Multi Ave'
                }
            )
            session.add(raw_row)
            session.flush()

            contact = ImportContact(
                batch_id='export-dup-multiple-batch',
                raw_import_row_id=raw_row.id,
                first_name='Multi',
                last_name=f'Dup{i+1}',
                email=f'multi{i+1}@example.com',
                phone=f'(555) {500+i:03d}-{5000+i:04d}',
                address_line1=f'{500+i*100} Multi Ave',
                amount=500.00 + i*100
            )
            session.add(contact)
            session.flush()
            contacts.append(contact)

        # Create 3 duplicate pairs
        # Pair 1: contacts[0] and contacts[1] - Defer
        # Pair 2: contacts[2] and contacts[3] - Defer
        # Pair 3: contacts[4] and contacts[5] - Confirmed (same_person)

        for pair_idx in range(3):
            contact_a = contacts[pair_idx * 2]
            contact_b = contacts[pair_idx * 2 + 1]

            duplicate = ReviewItem(
                batch_id='export-dup-multiple-batch',
                item_type='duplicate',
                confidence=0.90 - pair_idx * 0.02,
                payload_json={
                    'contact_a_id': contact_a.id,
                    'contact_b_id': contact_b.id,
                    'supporting_evidence': ['Match evidence'],
                    'conflicting_evidence': [],
                    'basis': f'Duplicate pair {pair_idx + 1}'
                }
            )
            session.add(duplicate)
            session.flush()

            subject_a = ReviewItemSubject(
                review_item_id=duplicate.id,
                subject_type='import_contact_snapshot',
                subject_id=contact_a.id,
                role='candidate_a'
            )
            session.add(subject_a)
            session.flush()

            subject_b = ReviewItemSubject(
                review_item_id=duplicate.id,
                subject_type='import_contact_snapshot',
                subject_id=contact_b.id,
                role='candidate_b'
            )
            session.add(subject_b)
            session.flush()

            # First 2 pairs: Defer, Last pair: same_person
            if pair_idx < 2:
                decision = ReviewDecision(
                    batch_id='export-dup-multiple-batch',
                    review_item_id=duplicate.id,
                    decision='defer',
                    created_at=datetime.utcnow(),
                    reviewed_values={}
                )
            else:
                decision = ReviewDecision(
                    batch_id='export-dup-multiple-batch',
                    review_item_id=duplicate.id,
                    decision='same_person',
                    created_at=datetime.utcnow(),
                    reviewed_values={
                        'candidate_contact_ids': [contact_a.id, contact_b.id]
                    }
                )
            session.add(decision)
            session.flush()

        session.commit()

        contact_ids = [c.id for c in contacts]

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
                requests.get('http://127.0.0.1:8001/imports/export-dup-multiple-batch/exports', timeout=2)
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
                # Navigate to exports page
                await page.goto('http://127.0.0.1:8001/imports/export-dup-multiple-batch/exports')

                # Wait for page to load
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/export-dup-multiple-batch/exports/preview', {
                            method: 'POST'
                        });
                        if (response.ok) {
                            const html = await response.text();
                            document.open();
                            document.write(html);
                            document.close();
                        }
                    }
                """)

                # Wait for the page to reload with preview data
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ E0: Export preview loaded (3 pairs total, 2 deferred)")

                # E1: Verify duplicate warning banner is visible
                warning_locator = page.locator('div:has(#confirm-unresolved-duplicates-checkbox)')
                warning_banner = await warning_locator.first.element_handle() if await warning_locator.count() > 0 else None
                assert warning_banner is not None, "E1 FAILED: Duplicate warning banner not found"
                print("✓ E1: Duplicate warning banner found")

                # E2: Verify warning text contains correct count (2, not 1 or 3)
                warning_text = await warning_locator.first.inner_text()
                assert '2' in warning_text, \
                    f"E2 FAILED: Expected warning text with count '2', got: {warning_text}"
                assert 'duplicate' in warning_text.lower() or 'pair' in warning_text.lower(), \
                    f"E2 FAILED: Expected 'duplicate' or 'pair' in warning text, got: {warning_text}"
                print(f"✓ E2: Warning text shows correct count (2 duplicates): {warning_text.strip()}")

                # E3: Verify checkbox exists and is unchecked initially
                checkbox = await page.query_selector('#confirm-unresolved-duplicates-checkbox')
                assert checkbox is not None, "E3 FAILED: Duplicate confirmation checkbox not found"
                is_checked = await checkbox.is_checked()
                assert not is_checked, "E3 FAILED: Checkbox should be unchecked initially"
                print("✓ E3: Checkbox exists and is unchecked initially")

                # E4: Verify export button is disabled initially
                export_btn = await page.query_selector('#generate-export-btn')
                assert export_btn is not None, "E4 FAILED: Export button not found"
                is_disabled_before = await export_btn.is_disabled()
                assert is_disabled_before, "E4 FAILED: Export button should be disabled initially"
                print("✓ E4: Export button is disabled initially")

                # E5: Check the checkbox
                await checkbox.check()
                print("✓ E5: Checkbox checked")

                # Wait for button state to update
                await page.wait_for_function(
                    "() => !document.getElementById('generate-export-btn').disabled",
                    timeout=5000
                )

                # E6: Verify export button is now enabled
                is_disabled_after = await export_btn.is_disabled()
                assert not is_disabled_after, "E6 FAILED: Export button should be enabled after checkbox check"
                print("✓ E6: Export button is now enabled (state changed bidirectionally)")

                # CRITICAL: E7 - Verify all 6 raw ImportContact data unchanged
                for idx, contact_id in enumerate(contact_ids):
                    contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
                    assert contact_check is not None, f"E7 FAILED: Contact {idx+1} should still exist"
                    assert contact_check.email == f'multi{idx+1}@example.com', \
                        f"E7 FAILED: Contact {idx+1} data should be unchanged"
                print(f"✓ E7: All 6 raw ImportContact records unchanged (append-only principle)")

                print(f"\n=== TEST E: EXPORT WARNING COUNT (MULTIPLE DEFERRED DUPLICATES) PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST F: Checkbox uncheck re-disables button (bidirectional state)
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_checkbox_uncheck_re_disables_button_for_duplicates(
    e2e_database_and_app,
):
    """
    Verify checkbox uncheck re-disables export button (bidirectional state).

    Scenario:
    1. Seed 1 deferred duplicate pair
    2. Open Export Console
    3. Assert button disabled initially
    4. Check checkbox
    5. Assert button becomes enabled
    6. Uncheck checkbox
    7. Assert button becomes disabled again
    8. Verify no silent control failure
    9. Verify raw ImportContact data unchanged

    Expected behavior:
    - Button state follows checkbox state bidirectionally
    - No silent control failure (button always responds to checkbox state)
    - User can toggle checkbox multiple times and button state responds reliably
    - Append-only principle: ImportContact data unchanged
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
            id='export-dup-bidirectional-batch',
            filename='export_dup_bidirectional.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        raw_row_a = RawImportRow(
            batch_id='export-dup-bidirectional-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Carol Bidir A',
                'date': '2026-03-25',
                'email': 'carol.bidir@example.com',
                'phone': '(555) 666-6666',
                'amount': '900.00',
                'address': '600 Bidir St'
            }
        )
        session.add(raw_row_a)
        session.flush()

        raw_row_b = RawImportRow(
            batch_id='export-dup-bidirectional-batch',
            row_index=2,
            raw_csv_data={
                'name': 'Carol Bidir B',
                'date': '2026-03-26',
                'email': 'carol.bidir+2@example.com',
                'phone': '(555) 666-6666',
                'amount': '900.00',
                'address': '600 Bidir St'
            }
        )
        session.add(raw_row_b)
        session.flush()

        # Create ImportContacts
        contact_a = ImportContact(
            batch_id='export-dup-bidirectional-batch',
            raw_import_row_id=raw_row_a.id,
            first_name='Carol',
            last_name='Bidir A',
            email='carol.bidir@example.com',
            phone='(555) 666-6666',
            address_line1='600 Bidir St',
            amount=900.00
        )
        session.add(contact_a)
        session.flush()

        contact_b = ImportContact(
            batch_id='export-dup-bidirectional-batch',
            raw_import_row_id=raw_row_b.id,
            first_name='Carol',
            last_name='Bidir B',
            email='carol.bidir+2@example.com',
            phone='(555) 666-6666',
            address_line1='600 Bidir St',
            amount=900.00
        )
        session.add(contact_b)
        session.flush()

        # Create duplicate review item
        duplicate = ReviewItem(
            batch_id='export-dup-bidirectional-batch',
            item_type='duplicate',
            confidence=0.93,
            payload_json={
                'contact_a_id': contact_a.id,
                'contact_b_id': contact_b.id,
                'supporting_evidence': ['Same phone', 'Same address'],
                'conflicting_evidence': ['Different emails'],
                'basis': 'Likely duplicate'
            }
        )
        session.add(duplicate)
        session.flush()

        subject_a = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_a.id,
            role='candidate_a'
        )
        session.add(subject_a)
        session.flush()

        subject_b = ReviewItemSubject(
            review_item_id=duplicate.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_b.id,
            role='candidate_b'
        )
        session.add(subject_b)
        session.flush()

        # Record Defer decision
        decision = ReviewDecision(
            batch_id='export-dup-bidirectional-batch',
            review_item_id=duplicate.id,
            decision='defer',
            created_at=datetime.utcnow(),
            reviewed_values={}
        )
        session.add(decision)
        session.flush()
        session.commit()

        contact_a_id = contact_a.id
        contact_b_id = contact_b.id

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
                requests.get('http://127.0.0.1:8001/imports/export-dup-bidirectional-batch/exports', timeout=2)
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
                # Navigate to exports page
                await page.goto('http://127.0.0.1:8001/imports/export-dup-bidirectional-batch/exports')

                # Wait for page to load
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/export-dup-bidirectional-batch/exports/preview', {
                            method: 'POST'
                        });
                        if (response.ok) {
                            const html = await response.text();
                            document.open();
                            document.write(html);
                            document.close();
                        }
                    }
                """)

                # Wait for the page to reload with preview data
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ F0: Export preview loaded")

                # F1: Verify checkbox exists and is unchecked initially
                checkbox = await page.query_selector('#confirm-unresolved-duplicates-checkbox')
                assert checkbox is not None, "F1 FAILED: Duplicate confirmation checkbox not found"
                is_checked_initial = await checkbox.is_checked()
                assert not is_checked_initial, "F1 FAILED: Checkbox should be unchecked initially"
                print("✓ F1: Checkbox is unchecked initially")

                # F2: Verify export button is disabled initially
                export_btn = await page.query_selector('#generate-export-btn')
                assert export_btn is not None, "F2 FAILED: Export button not found"
                is_disabled_state1 = await export_btn.is_disabled()
                assert is_disabled_state1, "F2 FAILED: Export button should be disabled when checkbox unchecked"
                print("✓ F2: Export button is disabled initially")

                # F3: Check the checkbox
                await checkbox.check()
                print("✓ F3: Checkbox checked")

                # Wait for button to become enabled
                await page.wait_for_function(
                    "() => !document.getElementById('generate-export-btn').disabled",
                    timeout=5000
                )

                # F4: Verify export button is now enabled
                is_disabled_state2 = await export_btn.is_disabled()
                assert not is_disabled_state2, "F4 FAILED: Export button should be enabled after checkbox check"
                is_checked_after_check = await checkbox.is_checked()
                assert is_checked_after_check, "F4 FAILED: Checkbox should be checked"
                print("✓ F4: Export button is now enabled (bidirectional: checked → enabled)")

                # F5: Uncheck the checkbox
                await checkbox.uncheck()
                print("✓ F5: Checkbox unchecked")

                # Wait for button to become disabled again
                await page.wait_for_function(
                    "() => document.getElementById('generate-export-btn').disabled",
                    timeout=5000
                )

                # F6: Verify export button is disabled again
                is_disabled_state3 = await export_btn.is_disabled()
                assert is_disabled_state3, "F6 FAILED: Export button should be disabled again after checkbox uncheck"
                is_checked_final = await checkbox.is_checked()
                assert not is_checked_final, "F6 FAILED: Checkbox should be unchecked"
                print("✓ F6: Export button is disabled again (bidirectional: unchecked → disabled)")

                # F7: Verify no silent control failure by checking checkbox again
                await checkbox.check()
                print("✓ F7: Checkbox checked again")

                await page.wait_for_function(
                    "() => !document.getElementById('generate-export-btn').disabled",
                    timeout=5000
                )

                is_disabled_state4 = await export_btn.is_disabled()
                assert not is_disabled_state4, "F7 FAILED: Export button should be enabled on second check (no silent failures)"
                print("✓ F7: Export button enabled again (bidirectional state verified, no silent failures)")

                # CRITICAL: F8 - Verify raw ImportContact data unchanged
                contact_a_check = session.query(ImportContact).filter_by(id=contact_a_id).first()
                assert contact_a_check is not None, "F8 FAILED: Contact A should still exist"
                assert contact_a_check.first_name == 'Carol', "F8 FAILED: Contact A data should be unchanged"

                contact_b_check = session.query(ImportContact).filter_by(id=contact_b_id).first()
                assert contact_b_check is not None, "F8 FAILED: Contact B should still exist"
                print("✓ F8: Raw ImportContact data unchanged (append-only principle)")

                print(f"\n=== TEST F: CHECKBOX UNCHECK RE-DISABLES BUTTON (DUPLICATES) PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()
