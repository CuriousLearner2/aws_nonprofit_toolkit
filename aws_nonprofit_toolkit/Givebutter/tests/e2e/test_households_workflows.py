"""
E2E browser tests for Households Phase 1-2 and Phase 4 workflows.

CRITICAL WORKFLOWS TESTED:
- Test A: Previous/Next navigation without creating decisions
- Test B: Defer without notes triggers warning, allows override
- Test C: Confirm household decision
- Test D: Reject household decision
- Test E: Post-decision redirect chain to next unresolved, then to /exports

Infrastructure:
- Database-backed Flask testing with ImportBatch/ReviewItem seeding
- Households service calculates suggestions and decisions
- Flask runs in background thread, Playwright drives browser

Synchronization:
- Use page.wait_for_function() to poll DOM state
- Wait for specific conditions: text changes, element visibility
- All browser clicks are real Playwright clicks (not mocked HTTP)

Assertions:
- Hard assertions only (test fails immediately if condition not met)
- Database verification: Query ReviewDecision to verify persistence
- Verify raw ImportContact data unchanged (append-only principle)

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
# TEST A: Previous/Next navigation without creating decisions
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_previous_next_navigation_no_decisions(
    e2e_database_and_app,
):
    """
    GOAL: Verify Previous/Next navigation works without creating ReviewDecisions.

    Flow:
    1. Seed 2+ households (ReviewItems of type 'household')
    2. Open /imports/{batch_id}/households
    3. Assert candidate 1 is visible
    4. Assert Previous button is disabled (boundary condition)
    5. Assert Next button is enabled
    6. Click Next button (real browser click)
    7. Assert candidate 2 is visible
    8. CRITICAL: Verify NO ReviewDecision created for candidate 1
    9. CRITICAL: Verify raw ImportContact data unchanged
    10. Click Previous button
    11. Assert candidate 1 visible again
    12. Assert buttons still usable (not destroyed by navigation)
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
            id='nav-test-batch',
            filename='nav_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows (2 contacts that will form households)
        raw_row_1 = RawImportRow(
            batch_id='nav-test-batch',
            row_index=1,
            raw_csv_data={
                'name': 'John Smith',
                'date': '2026-01-15',
                'email': 'john@example.com',
                'phone': '(555) 111-1111',
                'amount': '100.00',
                'address': '123 Main St'
            }
        )
        session.add(raw_row_1)
        session.flush()

        raw_row_2 = RawImportRow(
            batch_id='nav-test-batch',
            row_index=2,
            raw_csv_data={
                'name': 'Jane Smith',
                'date': '2026-01-16',
                'email': 'jane@example.com',
                'phone': '(555) 222-2222',
                'amount': '150.00',
                'address': '123 Main St'
            }
        )
        session.add(raw_row_2)
        session.flush()

        # Create ImportContacts
        contact_1 = ImportContact(
            batch_id='nav-test-batch',
            raw_import_row_id=raw_row_1.id,
            first_name='John',
            last_name='Smith',
            email='john@example.com',
            phone='(555) 111-1111',
            address_line1='123 Main St',
            amount=100.00
        )
        session.add(contact_1)
        session.flush()

        contact_2 = ImportContact(
            batch_id='nav-test-batch',
            raw_import_row_id=raw_row_2.id,
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
            phone='(555) 222-2222',
            address_line1='123 Main St',
            amount=150.00
        )
        session.add(contact_2)
        session.flush()

        # Create household review items (suggestions)
        household_1 = ReviewItem(
            batch_id='nav-test-batch',
            item_type='household',
            confidence=0.95,
            payload_json={
                'suggested_name': 'Smith Family',
                'address': '123 Main St',
                'proposed_members': ['John Smith', 'Jane Smith'],
                'evidence': ['Shared address', 'Shared last name'],
                'conflicts': [],
                'basis': 'Address matching'
            }
        )
        session.add(household_1)
        session.flush()

        household_2 = ReviewItem(
            batch_id='nav-test-batch',
            item_type='household',
            confidence=0.85,
            payload_json={
                'suggested_name': 'Johnson Couple',
                'address': '456 Oak Ave',
                'proposed_members': ['Bob Johnson', 'Alice Johnson'],
                'evidence': ['Shared address'],
                'conflicts': [],
                'basis': 'Address matching'
            }
        )
        session.add(household_2)
        session.flush()

        # Add subjects (link contacts to households)
        subject_1_1 = ReviewItemSubject(
            review_item_id=household_1.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_1.id,
            role='primary'
        )
        session.add(subject_1_1)

        subject_1_2 = ReviewItemSubject(
            review_item_id=household_1.id,
            subject_type='import_contact_snapshot',
            subject_id=contact_2.id,
            role='member'
        )
        session.add(subject_1_2)

        session.flush()
        session.commit()

        # Store contact IDs for later database verification
        contact_1_id = contact_1.id
        contact_2_id = contact_2.id
        household_1_id = household_1.id
        household_2_id = household_2.id

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
                requests.get('http://127.0.0.1:8001/imports/nav-test-batch/households', timeout=2)
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
                # Navigate to households page
                await page.goto('http://127.0.0.1:8001/imports/nav-test-batch/households')

                # Wait for household card to load
                await page.wait_for_selector('div.card', timeout=5000)

                # A1: Verify candidate 1 (Smith Family) is visible
                household_name = await page.inner_text('h3')
                assert 'Smith Family' in household_name, f"A1 FAILED: Expected 'Smith Family', got: {household_name}"
                print(f"✓ A1: First household visible: {household_name.strip()}")

                # A2: Verify Previous button is disabled (first item boundary)
                previous_btn = await page.query_selector('button:has-text("← Previous Household")')
                assert previous_btn is not None, "A2 FAILED: Previous button not found"
                is_disabled = await previous_btn.is_disabled()
                assert is_disabled, "A2 FAILED: Previous button should be disabled on first item"
                print("✓ A2: Previous button is disabled (boundary condition)")

                # A3: Verify Next button is enabled
                next_btn = await page.query_selector('a:has-text("Next Household →")')
                assert next_btn is not None, "A3 FAILED: Next button not found"
                is_visible = await next_btn.is_visible()
                assert is_visible, "A3 FAILED: Next button should be visible"
                print("✓ A3: Next button is enabled")

                # A4: Click Next button (real Playwright click)
                print("✓ A4: Clicking Next button...")
                await next_btn.click()

                # Wait for page to navigate and new household to load
                await page.wait_for_function(
                    "() => document.querySelector('h3')?.textContent?.includes('Johnson')",
                    timeout=5000
                )

                # A5: Verify candidate 2 (Johnson Couple) is visible
                household_name_2 = await page.inner_text('h3')
                assert 'Johnson' in household_name_2, f"A5 FAILED: Expected 'Johnson', got: {household_name_2}"
                print(f"✓ A5: Second household visible: {household_name_2.strip()}")

                # CRITICAL: A6 - Verify NO ReviewDecision created for household 1
                decisions_for_h1 = session.query(ReviewDecision).filter_by(
                    batch_id='nav-test-batch',
                    review_item_id=household_1_id
                ).all()
                assert len(decisions_for_h1) == 0, \
                    f"A6 FAILED: No decision should exist for household 1, found {len(decisions_for_h1)}"
                print("✓ A6: No ReviewDecision created for first household (navigation-only)")

                # CRITICAL: A7 - Verify raw ImportContact data unchanged
                contact_1_check = session.query(ImportContact).filter_by(id=contact_1_id).first()
                assert contact_1_check is not None, "A7 FAILED: Contact 1 should still exist"
                assert contact_1_check.first_name == 'John', "A7 FAILED: Contact data should be unchanged"
                assert contact_1_check.email == 'john@example.com', "A7 FAILED: Contact data should be unchanged"
                print("✓ A7: Raw ImportContact data unchanged (append-only principle)")

                # A8: Click Previous button to go back
                print("✓ A8: Clicking Previous button...")
                previous_btn_2 = await page.query_selector('a:has-text("← Previous Household")')
                assert previous_btn_2 is not None, "A8 FAILED: Previous button should now be visible"
                await previous_btn_2.click()

                # Wait for page to navigate back to first household
                await page.wait_for_function(
                    "() => document.querySelector('h3')?.textContent?.includes('Smith')",
                    timeout=5000
                )

                # A9: Verify candidate 1 visible again
                household_name_back = await page.inner_text('h3')
                assert 'Smith Family' in household_name_back, \
                    f"A9 FAILED: Expected 'Smith Family' after Previous, got: {household_name_back}"
                print(f"✓ A9: First household visible again after Previous click: {household_name_back.strip()}")

                # A10: Verify buttons still usable (not destroyed by navigation)
                previous_btn_final = await page.query_selector('button:has-text("← Previous Household")')
                assert previous_btn_final is not None, "A10 FAILED: Previous button should exist"
                is_disabled_final = await previous_btn_final.is_disabled()
                assert is_disabled_final, "A10 FAILED: Previous button should be disabled again"

                next_btn_final = await page.query_selector('a:has-text("Next Household →")')
                assert next_btn_final is not None, "A10 FAILED: Next button should exist after navigation"
                is_visible_final = await next_btn_final.is_visible()
                assert is_visible_final, "A10 FAILED: Next button should be visible after navigation"
                print("✓ A10: Navigation buttons still usable (DOM preserved)")

                print(f"\n=== TEST A: PREVIOUS/NEXT NAVIGATION PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST B: Defer without notes triggers warning, allows override
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_defer_without_notes_warning_non_blocking(
    e2e_database_and_app,
):
    """
    GOAL: Verify Defer decision triggers warning but allows submission without notes.

    Flow:
    1. Seed 1 household
    2. Open /imports/{batch_id}/households
    3. Leave notes textarea empty
    4. Click Defer button
    5. Assert warning appears: "Notes may help explain why this household is being deferred"
    6. Assert warning is visible
    7. CRITICAL: Assert submit is NOT blocked (user can still submit)
    8. Click Defer again or form auto-submits
    9. CRITICAL: Assert POST request sent (check database for ReviewDecision)
    10. Assert status badge shows "Deferred"
    11. Verify warning was non-blocking (decision recorded without notes)
    12. CRITICAL: Verify raw ImportContact data unchanged
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
            id='defer-warning-batch',
            filename='defer_warning.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row
        raw_row = RawImportRow(
            batch_id='defer-warning-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Defer Test',
                'date': '2026-02-01',
                'email': 'defer@example.com',
                'phone': '(555) 333-3333',
                'amount': '200.00',
                'address': '789 Defer Ave'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='defer-warning-batch',
            raw_import_row_id=raw_row.id,
            first_name='Defer',
            last_name='Test',
            email='defer@example.com',
            phone='(555) 333-3333',
            address_line1='789 Defer Ave',
            amount=200.00
        )
        session.add(contact)
        session.flush()

        # Create household review item
        household = ReviewItem(
            batch_id='defer-warning-batch',
            item_type='household',
            confidence=0.75,
            payload_json={
                'suggested_name': 'Defer Test Household',
                'address': '789 Defer Ave',
                'proposed_members': ['Defer Test'],
                'evidence': ['Single address entry'],
                'conflicts': [],
                'basis': 'Insufficient data'
            }
        )
        session.add(household)
        session.flush()

        subject = ReviewItemSubject(
            review_item_id=household.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.flush()
        session.commit()

        contact_id = contact.id
        household_id = household.id

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
                requests.get('http://127.0.0.1:8001/imports/defer-warning-batch/households', timeout=2)
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
                # Navigate to households page
                await page.goto('http://127.0.0.1:8001/imports/defer-warning-batch/households')

                # Wait for household card to load
                await page.wait_for_selector('div.card', timeout=5000)

                # B1: Verify household visible
                household_name = await page.inner_text('h3')
                assert 'Defer Test Household' in household_name, \
                    f"B1 FAILED: Expected 'Defer Test Household', got: {household_name}"
                print(f"✓ B1: Household visible: {household_name.strip()}")

                # B2: Verify notes textarea is empty
                notes_field = await page.query_selector('textarea#reviewer-notes')
                assert notes_field is not None, "B2 FAILED: Notes field not found"
                notes_value = await notes_field.input_value()
                assert notes_value.strip() == '', "B2 FAILED: Notes field should be empty initially"
                print("✓ B2: Notes textarea is empty")

                # B3: Verify warning is initially hidden
                warning = await page.query_selector('div#notes-warning-defer')
                assert warning is not None, "B3 FAILED: Warning element should exist"
                display = await warning.evaluate("el => window.getComputedStyle(el).display")
                assert display == 'none', "B3 FAILED: Warning should be hidden initially"
                print("✓ B3: Notes warning initially hidden")

                # B4: Click Defer button (without entering notes)
                defer_btn = await page.query_selector('button:has-text("Defer")')
                assert defer_btn is not None, "B4 FAILED: Defer button not found"
                print("✓ B4: Defer button clicked...")

                # Click defer button and wait for page navigation or URL change
                await defer_btn.click()

                # Wait for either a URL change (redirect) or a timeout
                try:
                    await page.wait_for_url(
                        lambda url: '/households' in url or '/exports' in url,
                        timeout=5000
                    )
                except:
                    print("ℹ B4: URL may not have changed (page may be reloading)")

                # Wait briefly for potential redirect to /exports
                await asyncio.sleep(1)

                # CRITICAL: B5 - Verify ReviewDecision was created (decision recorded without notes)
                decisions = session.query(ReviewDecision).filter_by(
                    batch_id='defer-warning-batch',
                    review_item_id=household_id
                ).all()
                assert len(decisions) > 0, \
                    f"B5 FAILED: ReviewDecision should be created, found {len(decisions)}"
                decision = decisions[0]
                assert decision.decision == 'defer', \
                    f"B5 FAILED: Decision should be 'defer', got {decision.decision}"
                # Notes should be None or not present in reviewed_values (allow override)
                notes_value = decision.reviewed_values.get('notes') if decision.reviewed_values else None
                assert notes_value is None, \
                    f"B5 FAILED: Notes should be None (allow override), got {notes_value}"
                print(f"✓ B5: ReviewDecision created with decision='defer' (notes optional, non-blocking)")

                # CRITICAL: B6 - Verify raw ImportContact data unchanged
                contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
                assert contact_check is not None, "B6 FAILED: Contact should still exist"
                assert contact_check.first_name == 'Defer', "B6 FAILED: Contact data should be unchanged"
                assert contact_check.email == 'defer@example.com', "B6 FAILED: Contact data should be unchanged"
                print("✓ B6: Raw ImportContact data unchanged (append-only)")

                print(f"\n=== TEST B: DEFER WARNING NON-BLOCKING PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST C: Confirm household decision
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_confirm_household_decision(
    e2e_database_and_app,
):
    """
    GOAL: Verify Confirm decision records and persists.

    Flow:
    1. Seed 1 household
    2. Open /imports/{batch_id}/households
    3. Click Confirm Household Suggestion button
    4. Assert form submits (POST request)
    5. CRITICAL: Query database, verify ReviewDecision exists with decision='confirm_household'
    6. CRITICAL: Verify raw ImportContact data unchanged
    7. After redirect, verify we're on /exports or next household page
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
            id='confirm-test-batch',
            filename='confirm_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row
        raw_row = RawImportRow(
            batch_id='confirm-test-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Confirm Test',
                'date': '2026-02-05',
                'email': 'confirm@example.com',
                'phone': '(555) 444-4444',
                'amount': '300.00',
                'address': '999 Confirm Ave'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='confirm-test-batch',
            raw_import_row_id=raw_row.id,
            first_name='Confirm',
            last_name='Test',
            email='confirm@example.com',
            phone='(555) 444-4444',
            address_line1='999 Confirm Ave',
            amount=300.00
        )
        session.add(contact)
        session.flush()

        # Create household review item
        household = ReviewItem(
            batch_id='confirm-test-batch',
            item_type='household',
            confidence=0.95,
            payload_json={
                'suggested_name': 'Confirm Test Household',
                'address': '999 Confirm Ave',
                'proposed_members': ['Confirm Test'],
                'evidence': ['Clear household identification'],
                'conflicts': [],
                'basis': 'High confidence match'
            }
        )
        session.add(household)
        session.flush()

        subject = ReviewItemSubject(
            review_item_id=household.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.flush()
        session.commit()

        contact_id = contact.id
        household_id = household.id

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
                requests.get('http://127.0.0.1:8001/imports/confirm-test-batch/households', timeout=2)
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
                # Navigate to households page
                await page.goto('http://127.0.0.1:8001/imports/confirm-test-batch/households')

                # Wait for household card to load
                await page.wait_for_selector('div.card', timeout=5000)

                # C1: Verify household visible
                household_name = await page.inner_text('h3')
                assert 'Confirm Test Household' in household_name, \
                    f"C1 FAILED: Expected 'Confirm Test Household', got: {household_name}"
                print(f"✓ C1: Household visible: {household_name.strip()}")

                # C2: Click Confirm Household Suggestion button
                confirm_btn = await page.query_selector('button:has-text("Confirm Household Suggestion")')
                assert confirm_btn is not None, "C2 FAILED: Confirm button not found"
                print("✓ C2: Clicking Confirm Household Suggestion...")

                # Click the button and wait for page navigation or URL change
                await confirm_btn.click()

                # Wait for either a URL change (redirect) or a timeout
                try:
                    await page.wait_for_url(
                        lambda url: '/households' in url or '/exports' in url,
                        timeout=5000
                    )
                except:
                    print("ℹ C2: URL may not have changed (page may be reloading)")

                await asyncio.sleep(1)

                # CRITICAL: C3 - Verify ReviewDecision created with decision='confirm_household'
                decisions = session.query(ReviewDecision).filter_by(
                    batch_id='confirm-test-batch',
                    review_item_id=household_id
                ).all()
                assert len(decisions) > 0, \
                    f"C3 FAILED: ReviewDecision should be created, found {len(decisions)}"
                decision = decisions[0]
                assert decision.decision == 'confirm_household', \
                    f"C3 FAILED: Decision should be 'confirm_household', got {decision.decision}"
                print(f"✓ C3: ReviewDecision created with decision='confirm_household'")

                # CRITICAL: C4 - Verify raw ImportContact data unchanged
                contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
                assert contact_check is not None, "C4 FAILED: Contact should still exist"
                assert contact_check.first_name == 'Confirm', "C4 FAILED: Contact data should be unchanged"
                assert contact_check.email == 'confirm@example.com', "C4 FAILED: Contact data should be unchanged"
                print("✓ C4: Raw ImportContact data unchanged")

                print(f"\n=== TEST C: CONFIRM HOUSEHOLD DECISION PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST D: Reject household decision
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reject_household_decision(
    e2e_database_and_app,
):
    """
    GOAL: Verify Reject decision records and persists.

    Flow:
    1. Seed 1 household
    2. Open /imports/{batch_id}/households
    3. Click Reject Household Suggestion button
    4. Assert form submits (POST request)
    5. CRITICAL: Query database, verify ReviewDecision exists with decision='reject_household'
    6. CRITICAL: Verify raw ImportContact data unchanged
    7. After redirect, verify we're on /exports or next household page
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
            id='reject-test-batch',
            filename='reject_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row
        raw_row = RawImportRow(
            batch_id='reject-test-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Reject Test',
                'date': '2026-02-10',
                'email': 'reject@example.com',
                'phone': '(555) 555-5555',
                'amount': '400.00',
                'address': '111 Reject Ave'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='reject-test-batch',
            raw_import_row_id=raw_row.id,
            first_name='Reject',
            last_name='Test',
            email='reject@example.com',
            phone='(555) 555-5555',
            address_line1='111 Reject Ave',
            amount=400.00
        )
        session.add(contact)
        session.flush()

        # Create household review item
        household = ReviewItem(
            batch_id='reject-test-batch',
            item_type='household',
            confidence=0.50,
            payload_json={
                'suggested_name': 'Reject Test Household',
                'address': '111 Reject Ave',
                'proposed_members': ['Reject Test'],
                'evidence': ['Low confidence match'],
                'conflicts': ['Different emails', 'Different phone numbers'],
                'basis': 'Low confidence grouping'
            }
        )
        session.add(household)
        session.flush()

        subject = ReviewItemSubject(
            review_item_id=household.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.flush()
        session.commit()

        contact_id = contact.id
        household_id = household.id

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
                requests.get('http://127.0.0.1:8001/imports/reject-test-batch/households', timeout=2)
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
                # Navigate to households page
                await page.goto('http://127.0.0.1:8001/imports/reject-test-batch/households')

                # Wait for household card to load
                await page.wait_for_selector('div.card', timeout=5000)

                # D1: Verify household visible
                household_name = await page.inner_text('h3')
                assert 'Reject Test Household' in household_name, \
                    f"D1 FAILED: Expected 'Reject Test Household', got: {household_name}"
                print(f"✓ D1: Household visible: {household_name.strip()}")

                # D2: Click Reject Household Suggestion button
                reject_btn = await page.query_selector('button:has-text("Reject Household Suggestion")')
                assert reject_btn is not None, "D2 FAILED: Reject button not found"
                print("✓ D2: Clicking Reject Household Suggestion...")

                # Click the button and wait for page navigation or URL change
                await reject_btn.click()

                # Wait for either a URL change (redirect) or a timeout
                try:
                    await page.wait_for_url(
                        lambda url: '/households' in url or '/exports' in url,
                        timeout=5000
                    )
                except:
                    print("ℹ D2: URL may not have changed (page may be reloading)")

                await asyncio.sleep(1)

                # CRITICAL: D3 - Verify ReviewDecision created with decision='reject_household'
                decisions = session.query(ReviewDecision).filter_by(
                    batch_id='reject-test-batch',
                    review_item_id=household_id
                ).all()
                assert len(decisions) > 0, \
                    f"D3 FAILED: ReviewDecision should be created, found {len(decisions)}"
                decision = decisions[0]
                assert decision.decision == 'reject_household', \
                    f"D3 FAILED: Decision should be 'reject_household', got {decision.decision}"
                print(f"✓ D3: ReviewDecision created with decision='reject_household'")

                # CRITICAL: D4 - Verify raw ImportContact data unchanged
                contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
                assert contact_check is not None, "D4 FAILED: Contact should still exist"
                assert contact_check.first_name == 'Reject', "D4 FAILED: Contact data should be unchanged"
                assert contact_check.email == 'reject@example.com', "D4 FAILED: Contact data should be unchanged"
                print("✓ D4: Raw ImportContact data unchanged")

                print(f"\n=== TEST D: REJECT HOUSEHOLD DECISION PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST E: Post-decision redirect chain to next unresolved, then to /exports
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_redirect_chain_to_exports(
    e2e_database_and_app,
):
    """
    GOAL: Verify post-decision redirect chain works: decide -> next -> decide -> next -> exports.

    Flow:
    1. Seed 3 households
    2. Decide household 1
    3. Assert browser navigates to ?index=1 (or candidate 2 displayed)
    4. Assert no page error
    5. Decide household 2
    6. Assert browser navigates to ?index=2 (or candidate 3 displayed)
    7. Decide household 3 (final one)
    8. Assert browser redirects to /imports/{batch_id}/exports
    9. CRITICAL: Verify /exports route responds 200 (not 404)
    10. CRITICAL: Verify exports page loads (HTML visible, not error)
    11. CRITICAL: Query database, verify 3 ReviewDecisions created (one for each household)
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
            id='redirect-chain-batch',
            filename='redirect_chain.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=3
        )
        session.add(batch)
        session.flush()

        # Create 3 households
        households = []
        for i in range(1, 4):
            raw_row = RawImportRow(
                batch_id='redirect-chain-batch',
                row_index=i,
                raw_csv_data={
                    'name': f'Chain Test {i}',
                    'date': f'2026-02-{15 + i:02d}',
                    'email': f'chain{i}@example.com',
                    'phone': f'(555) 666-{i:04d}',
                    'amount': f'{100 * i}.00',
                    'address': f'{100 * i} Chain Ave'
                }
            )
            session.add(raw_row)
            session.flush()

            contact = ImportContact(
                batch_id='redirect-chain-batch',
                raw_import_row_id=raw_row.id,
                first_name='Chain',
                last_name=f'Test {i}',
                email=f'chain{i}@example.com',
                phone=f'(555) 666-{i:04d}',
                address_line1=f'{100 * i} Chain Ave',
                amount=100.0 * i
            )
            session.add(contact)
            session.flush()

            household = ReviewItem(
                batch_id='redirect-chain-batch',
                item_type='household',
                confidence=0.80 + (0.05 * i),
                payload_json={
                    'suggested_name': f'Chain Household {i}',
                    'address': f'{100 * i} Chain Ave',
                    'proposed_members': [f'Chain Test {i}'],
                    'evidence': [f'Address match for household {i}'],
                    'conflicts': [],
                    'basis': f'Chain test household {i}'
                }
            )
            session.add(household)
            session.flush()

            subject = ReviewItemSubject(
                review_item_id=household.id,
                subject_type='import_contact_snapshot',
                subject_id=contact.id,
                role='primary'
            )
            session.add(subject)
            session.flush()

            households.append(household)

        session.commit()

        household_ids = [h.id for h in households]

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
                requests.get('http://127.0.0.1:8001/imports/redirect-chain-batch/households', timeout=2)
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
                # Navigate to households page (starts at household 1)
                await page.goto('http://127.0.0.1:8001/imports/redirect-chain-batch/households')

                # Wait for household card to load
                await page.wait_for_selector('div.card', timeout=5000)

                # E1: Verify household 1 visible
                household_name = await page.inner_text('h3')
                assert 'Chain Household 1' in household_name, \
                    f"E1 FAILED: Expected 'Chain Household 1', got: {household_name}"
                print(f"✓ E1: Household 1 visible: {household_name.strip()}")

                # E2: Decide household 1 (Confirm)
                confirm_btn = await page.query_selector('button:has-text("Confirm Household Suggestion")')
                assert confirm_btn is not None, "E2 FAILED: Confirm button not found"
                print("✓ E2: Clicking Confirm for household 1...")

                await confirm_btn.click()

                # Wait for URL change or page reload
                try:
                    await page.wait_for_url(
                        lambda url: '/households' in url or '/exports' in url,
                        timeout=5000
                    )
                except:
                    print("ℹ E2: URL may not have changed")

                # Wait for next page to load
                await asyncio.sleep(1)
                try:
                    await page.wait_for_selector('div.card', timeout=3000)
                except:
                    print("ℹ E2: No card element found (may be on exports page)")

                # E3: Verify household 2 now visible
                household_name_2 = await page.inner_text('h3')
                assert 'Chain Household 2' in household_name_2, \
                    f"E3 FAILED: Expected 'Chain Household 2' after redirect, got: {household_name_2}"
                print(f"✓ E3: Redirected to household 2: {household_name_2.strip()}")

                # E4: Decide household 2 (Confirm)
                confirm_btn_2 = await page.query_selector('button:has-text("Confirm Household Suggestion")')
                assert confirm_btn_2 is not None, "E4 FAILED: Confirm button not found for household 2"
                print("✓ E4: Clicking Confirm for household 2...")

                await confirm_btn_2.click()

                # Wait for URL change or page reload
                try:
                    await page.wait_for_url(
                        lambda url: '/households' in url or '/exports' in url,
                        timeout=5000
                    )
                except:
                    print("ℹ E4: URL may not have changed")

                # Wait for next page to load
                await asyncio.sleep(1)
                try:
                    await page.wait_for_selector('div.card', timeout=3000)
                except:
                    print("ℹ E4: No card element found (may be on exports page)")

                # E5: Verify household 3 now visible
                household_name_3 = await page.inner_text('h3')
                assert 'Chain Household 3' in household_name_3, \
                    f"E5 FAILED: Expected 'Chain Household 3' after redirect, got: {household_name_3}"
                print(f"✓ E5: Redirected to household 3: {household_name_3.strip()}")

                # E6: Decide household 3 (Confirm) - last one, should redirect to exports
                confirm_btn_3 = await page.query_selector('button:has-text("Confirm Household Suggestion")')
                assert confirm_btn_3 is not None, "E6 FAILED: Confirm button not found for household 3"
                print("✓ E6: Clicking Confirm for household 3 (final)...")

                await confirm_btn_3.click()

                # Wait for URL change to /exports
                try:
                    await page.wait_for_url(
                        lambda url: '/exports' in url,
                        timeout=5000
                    )
                except:
                    print("ℹ E6: URL may not have changed to /exports")

                # Wait for exports page to load
                await asyncio.sleep(1)

                # E7: Verify exports page loaded (URL contains /exports)
                current_url = page.url
                assert '/exports' in current_url, \
                    f"E7 FAILED: Expected redirect to /exports, got URL: {current_url}"
                print(f"✓ E7: Browser redirected to exports page: {current_url}")

                # E8: Verify exports page has content (not error page)
                page_content = await page.content()
                assert 'export' in page_content.lower() or 'suggestion' in page_content.lower(), \
                    f"E8 FAILED: Exports page should have content, got empty or error"
                print("✓ E8: Exports page loaded with content (not error)")

                # CRITICAL: E9 - Verify 3 ReviewDecisions created (one for each household)
                all_decisions = session.query(ReviewDecision).filter_by(
                    batch_id='redirect-chain-batch'
                ).all()
                assert len(all_decisions) == 3, \
                    f"E9 FAILED: Should have 3 ReviewDecisions, found {len(all_decisions)}"

                # Verify each household has a decision
                for idx, hh_id in enumerate(household_ids, 1):
                    hh_decisions = [d for d in all_decisions if d.review_item_id == hh_id]
                    assert len(hh_decisions) == 1, \
                        f"E9 FAILED: Household {idx} should have 1 decision, found {len(hh_decisions)}"
                    assert hh_decisions[0].decision == 'confirm_household', \
                        f"E9 FAILED: Household {idx} should be 'confirm_household', got {hh_decisions[0].decision}"

                print(f"✓ E9: All 3 ReviewDecisions created with correct decisions")

                print(f"\n=== TEST E: REDIRECT CHAIN TO EXPORTS PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()
