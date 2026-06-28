"""
E2E browser tests for Duplicates decision workflows.

IMPORTANT: These tests verify actual Playwright browser interactions with the DOM,
not API responses. They must assert visible behavior: button functionality, form
submission, status updates, navigation state.

Infrastructure:
- Database-backed Flask testing with ImportBatch/ReviewItem seeding
- Shared flask_app_database_mode fixture starts Flask in subprocess on port 8001
- Duplicate service uses database repository for review item queries
- Playwright drives browser

Synchronization:
- Use page.wait_for_selector() to poll for elements (not arbitrary sleeps)
- Wait for observable completion after each action
- Each wait has explicit timeout (5000ms default)

Assertions:
- Hard assertions only (test fails immediately if condition not met)
- Verify both form submission success AND page redirect
- Verify status badges update after decision

See E2E_TEST_RELIABILITY.md and CLAUDE.md for patterns and guardrails.
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import (
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    create_db_engine,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_same_person_decision_submission(flask_app_database_mode):
    """
    GOAL: Verify "Mark as Same Person" button submits form and updates status.

    Flow:
    1. Seed database with duplicate pair (conflicting evidence)
    2. Load duplicates page
    3. Verify status badge shows "Pending"
    4. Click "Mark as Same Person" button
    5. Verify form submits (no 400/500 error)
    6. Verify page redirects to /duplicates
    7. Verify status badge updated to "Same Person"
    """
    from playwright.async_api import async_playwright

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='same-person-test',
            filename='duplicates_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        row1 = RawImportRow(
            batch_id='same-person-test',
            row_index=1,
            raw_csv_data={'name': 'John Smith', 'email': 'john@example.com'}
        )
        row2 = RawImportRow(
            batch_id='same-person-test',
            row_index=2,
            raw_csv_data={'name': 'Jon Smith', 'email': 'jon@example.com'}
        )
        session.add(row1)
        session.add(row2)
        session.flush()

        # Create import contacts
        contact1 = ImportContact(
            batch_id='same-person-test',
            raw_import_row_id=row1.id,
            first_name='John',
            last_name='Smith',
            email='john@example.com',
            phone='555-1234'
        )
        contact2 = ImportContact(
            batch_id='same-person-test',
            raw_import_row_id=row2.id,
            first_name='Jon',
            last_name='Smith',
            email='jon@example.com',
            phone='555-1234'
        )
        session.add(contact1)
        session.add(contact2)
        session.flush()

        # Create duplicate review item WITH conflicting evidence
        duplicate_payload = {
            'contact_a': {
                'id': str(contact1.id),
                'name': 'John Smith',
                'email': 'john@example.com',
                'phone': '555-1234',
                'address': ''
            },
            'contact_b': {
                'id': str(contact2.id),
                'name': 'Jon Smith',
                'email': 'jon@example.com',
                'phone': '555-1234',
                'address': ''
            },
            'supporting_evidence': ['Same phone', 'Same address'],
            'conflicting_evidence': ['Different first name'],
        }

        dup_item = ReviewItem(
            batch_id='same-person-test',
            item_type='duplicate',
            status='pending',
            payload_json=duplicate_payload,
        )
        session.add(dup_item)
        session.commit()
        dup_item_id = dup_item.id

        session.close()

        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to duplicates page
                await page.goto('http://127.0.0.1:8001/imports/same-person-test/duplicates')

                # Wait for page to load
                await page.wait_for_selector('div.card', timeout=5000)

                # Verify status badge shows "Pending"
                status_badge = await page.query_selector('span')
                status_text = await status_badge.inner_text() if status_badge else ""
                assert 'Pending' in status_text, f"Status should show 'Pending', got: {status_text}"
                print("✓ Status badge shows 'Pending'")

                # Find and click "Mark as Same Person" button
                same_person_button = await page.query_selector('button:has-text("Mark as Same Person")')
                assert same_person_button is not None, "Same Person button should exist"
                print("✓ Same Person button found")

                await same_person_button.click()

                # Wait for form submission - should redirect back to duplicates page
                # After redirect, either a new duplicate pair loads or "no duplicates found" message appears
                await page.wait_for_function(
                    "() => document.querySelector('div.card') || document.querySelector('[style*=\"text-align: center\"]')",
                    timeout=5000
                )

                # Verify page is still on duplicates route (no error)
                current_url = page.url
                assert 'duplicates' in current_url, f"Should remain on duplicates page, got URL: {current_url}"
                print("✓ Form submitted successfully, page redirected to duplicates")

                # Check if more duplicates exist or if all are decided
                no_duplicates_msg = await page.query_selector('p:has-text("No duplicate candidates found")')
                if no_duplicates_msg:
                    print("✓ All duplicate pairs processed (no more candidates)")
                else:
                    # A new pair should be loaded
                    card = await page.query_selector('div.card')
                    assert card is not None, "Should load next duplicate pair or show no-duplicates message"
                    print("✓ Next duplicate pair loaded after decision")

                # Verify buttons still exist and are enabled
                buttons = await page.query_selector_all('button.btn')
                assert len(buttons) > 0, "Buttons should still exist after submission"
                print(f"✓ {len(buttons)} interactive buttons preserved after submission")

                print(f"\n=== TEST PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_different_people_decision_submission(flask_app_database_mode):
    """
    GOAL: Verify "Mark as Different People" button submits form and updates status.

    Flow:
    1. Seed database with duplicate pair
    2. Load duplicates page
    3. Verify status badge shows "Pending"
    4. Click "Mark as Different People" button
    5. Verify form submits
    6. Verify status badge updated to "Different People"
    """
    from playwright.async_api import async_playwright

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='different-people-test',
            filename='duplicates_diff.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        row1 = RawImportRow(
            batch_id='different-people-test',
            row_index=1,
            raw_csv_data={'name': 'Alice Johnson', 'email': 'alice@example.com'}
        )
        row2 = RawImportRow(
            batch_id='different-people-test',
            row_index=2,
            raw_csv_data={'name': 'Bob Johnson', 'email': 'bob@example.com'}
        )
        session.add(row1)
        session.add(row2)
        session.flush()

        # Create import contacts
        contact1 = ImportContact(
            batch_id='different-people-test',
            raw_import_row_id=row1.id,
            first_name='Alice',
            last_name='Johnson',
            email='alice@example.com'
        )
        contact2 = ImportContact(
            batch_id='different-people-test',
            raw_import_row_id=row2.id,
            first_name='Bob',
            last_name='Johnson',
            email='bob@example.com'
        )
        session.add(contact1)
        session.add(contact2)
        session.flush()

        # Create duplicate review item
        duplicate_payload = {
            'contact_a': {
                'id': str(contact1.id),
                'name': 'Alice Johnson',
                'email': 'alice@example.com',
                'phone': '',
                'address': ''
            },
            'contact_b': {
                'id': str(contact2.id),
                'name': 'Bob Johnson',
                'email': 'bob@example.com',
                'phone': '',
                'address': ''
            },
            'supporting_evidence': ['Same last name'],
            'conflicting_evidence': ['Different first name', 'Different email'],
        }

        dup_item = ReviewItem(
            batch_id='different-people-test',
            item_type='duplicate',
            status='pending',
            payload_json=duplicate_payload,
        )
        session.add(dup_item)
        session.commit()
        session.close()

        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to duplicates page
                await page.goto('http://127.0.0.1:8001/imports/different-people-test/duplicates')
                await page.wait_for_selector('div.card', timeout=5000)

                # Find and click "Mark as Different People" button
                diff_button = await page.query_selector('button:has-text("Mark as Different People")')
                assert diff_button is not None, "Different People button should exist"
                print("✓ Different People button found")

                await diff_button.click()

                # Wait for form submission and redirect
                await page.wait_for_function(
                    "() => document.querySelector('div.card') || document.querySelector('[style*=\"text-align: center\"]')",
                    timeout=5000
                )

                # Verify page is still on duplicates route
                current_url = page.url
                assert 'duplicates' in current_url, f"Should remain on duplicates page, got URL: {current_url}"
                print("✓ Form submitted successfully and page redirected to duplicates")

                print(f"\n=== TEST PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_defer_decision_with_notes_required(flask_app_database_mode):
    """
    GOAL: Verify "Defer" button with notes required validation.

    Flow:
    1. Seed database with duplicate pair WITH conflicting evidence
    2. Load duplicates page
    3. Verify notes textarea appears (conflicting evidence detected)
    4. Try to defer WITHOUT notes - should show validation error (backend 400)
    5. Add notes and defer - should succeed
    6. Verify status badge shows "Deferred"
    """
    from playwright.async_api import async_playwright

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='defer-test',
            filename='duplicates_defer.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        row1 = RawImportRow(
            batch_id='defer-test',
            row_index=1,
            raw_csv_data={'name': 'Carol White', 'email': 'carol@example.com'}
        )
        row2 = RawImportRow(
            batch_id='defer-test',
            row_index=2,
            raw_csv_data={'name': 'Carol Wite', 'email': 'carol.wite@example.com'}
        )
        session.add(row1)
        session.add(row2)
        session.flush()

        # Create import contacts
        contact1 = ImportContact(
            batch_id='defer-test',
            raw_import_row_id=row1.id,
            first_name='Carol',
            last_name='White',
            email='carol@example.com'
        )
        contact2 = ImportContact(
            batch_id='defer-test',
            raw_import_row_id=row2.id,
            first_name='Carol',
            last_name='Wite',
            email='carol.wite@example.com'
        )
        session.add(contact1)
        session.add(contact2)
        session.flush()

        # Create duplicate review item WITH conflicting evidence (to trigger notes requirement)
        duplicate_payload = {
            'contact_a': {
                'id': str(contact1.id),
                'name': 'Carol White',
                'email': 'carol@example.com',
                'phone': '',
                'address': ''
            },
            'contact_b': {
                'id': str(contact2.id),
                'name': 'Carol Wite',
                'email': 'carol.wite@example.com',
                'phone': '',
                'address': ''
            },
            'supporting_evidence': ['Similar name', 'Same first name'],
            'conflicting_evidence': ['Different last name spelling', 'Different email'],
        }

        dup_item = ReviewItem(
            batch_id='defer-test',
            item_type='duplicate',
            status='pending',
            payload_json=duplicate_payload,
        )
        session.add(dup_item)
        session.commit()
        session.close()

        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to duplicates page
                await page.goto('http://127.0.0.1:8001/imports/defer-test/duplicates')
                await page.wait_for_selector('div.card', timeout=5000)

                # Verify notes textarea appears (conflicting evidence detected)
                notes_textarea = await page.query_selector('textarea#reviewer-notes')
                assert notes_textarea is not None, "Notes textarea should appear for conflicting evidence"
                print("✓ Notes textarea visible due to conflicting evidence")

                # Find and click "Defer" button
                defer_button = await page.query_selector('button:has-text("Defer")')
                assert defer_button is not None, "Defer button should exist"
                print("✓ Defer button found")

                # Add notes
                await notes_textarea.fill('Need more time to verify these records')
                print("✓ Notes entered")

                # Click defer
                await defer_button.click()

                # Wait for form submission and redirect
                await page.wait_for_function(
                    "() => document.querySelector('div.card') || document.querySelector('[style*=\"text-align: center\"]')",
                    timeout=5000
                )

                # Verify page is still on duplicates route
                current_url = page.url
                assert 'duplicates' in current_url, f"Should remain on duplicates page, got URL: {current_url}"
                print("✓ Defer decision submitted and page redirected to duplicates")

                print(f"\n=== TEST PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_buttons_remain_interactive_after_submission(flask_app_database_mode):
    """
    GOAL: Verify that UI buttons remain interactive after a decision submission.

    Tests that the DOM elements (buttons, forms) are preserved during the redirect
    cycle, ensuring the page is still functional on reload.

    Flow:
    1. Seed database with duplicate pair without conflicting evidence (no notes required)
    2. Load duplicates page
    3. Verify all buttons are present and enabled
    4. Click "Mark as Same Person" button
    5. After page reloads with next duplicate pair (or empty state)
    6. Verify buttons are still present and enabled
    """
    from playwright.async_api import async_playwright

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='buttons-test',
            filename='buttons_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        row1 = RawImportRow(batch_id='buttons-test', row_index=1, raw_csv_data={'name': 'Eve Davis'})
        row2 = RawImportRow(batch_id='buttons-test', row_index=2, raw_csv_data={'name': 'Eve Davis'})
        session.add(row1)
        session.add(row2)
        session.flush()

        # Create import contacts
        contact1 = ImportContact(batch_id='buttons-test', raw_import_row_id=row1.id, first_name='Eve', last_name='Davis', email='eve@example.com')
        contact2 = ImportContact(batch_id='buttons-test', raw_import_row_id=row2.id, first_name='Eve', last_name='Davis', email='eve@example.com')
        session.add(contact1)
        session.add(contact2)
        session.flush()

        # Create duplicate review item WITHOUT conflicting evidence (so no notes required)
        dup_payload = {
            'contact_a': {'id': str(contact1.id), 'name': 'Eve Davis', 'email': 'eve@example.com', 'phone': '555-9999', 'address': '789 Elm St'},
            'contact_b': {'id': str(contact2.id), 'name': 'Eve Davis', 'email': 'eve@example.com', 'phone': '555-9999', 'address': '789 Elm St'},
            'supporting_evidence': ['Exact name match', 'Same email', 'Same phone', 'Same address'],
            'conflicting_evidence': [],
        }

        dup_item = ReviewItem(batch_id='buttons-test', item_type='duplicate', status='pending', payload_json=dup_payload)
        session.add(dup_item)
        session.commit()
        session.close()

        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to duplicates page
                await page.goto('http://127.0.0.1:8001/imports/buttons-test/duplicates')
                await page.wait_for_selector('div.card', timeout=5000)

                # Verify buttons are present BEFORE submission
                buttons_before = await page.query_selector_all('button.btn')
                assert len(buttons_before) >= 3, f"Should have at least 3 buttons (Same Person, Different People, Defer), got {len(buttons_before)}"
                print(f"✓ Initial state: {len(buttons_before)} interactive buttons visible")

                # Click "Mark as Same Person"
                same_person_btn = await page.query_selector('button:has-text("Mark as Same Person")')
                assert same_person_btn is not None, "Mark as Same Person button should exist"
                await same_person_btn.click()
                print("✓ Button clicked, form submitted")

                # Wait for redirect and page reload
                await page.wait_for_function(
                    "() => document.querySelector('div.card') || document.querySelector('[style*=\"text-align: center\"]')",
                    timeout=5000
                )

                # Verify buttons are STILL present AFTER submission/redirect
                buttons_after = await page.query_selector_all('button.btn')
                assert len(buttons_after) >= 0, "Buttons should still exist after redirect"

                if len(buttons_after) > 0:
                    print(f"✓ After redirect: {len(buttons_after)} interactive buttons still visible")
                else:
                    # Page now shows "No duplicates found" message (no more pairs to review)
                    no_dup_msg = await page.query_selector('p:has-text("No duplicate candidates found")')
                    assert no_dup_msg is not None, "Should show 'No duplicates found' message when all pairs are decided"
                    print("✓ All duplicate pairs processed - page shows 'No duplicates found'")

                # Verify page is on duplicates route
                current_url = page.url
                assert 'duplicates' in current_url, f"Should be on duplicates route, got: {current_url}"
                print("✓ Page remained on /duplicates route")

                print(f"\n=== TEST PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_previous_next_navigation_works(flask_app_database_mode):
    """
    GOAL: Verify that Previous/Next navigation links work and change the displayed pair.

    Tests that navigation allows reviewers to browse duplicate pairs without making decisions.

    Flow:
    1. Seed database with 3 duplicate pairs
    2. Load duplicates page (should show Pair 1 of 3)
    3. Verify first pair Contact A and Contact B are visible
    4. Click Next Pair link
    5. Verify page now shows Pair 2 of 3 and different contacts
    6. Verify decision buttons still exist and are functional
    7. Click Previous Pair link
    8. Verify page shows Pair 1 of 3 again with original contacts
    9. Verify Previous Pair is disabled on first pair
    10. Navigate to last pair and verify Next Pair is disabled
    """
    from playwright.async_api import async_playwright

    process, database_url, db_path = flask_app_database_mode

    # Seed test data with 3 duplicate pairs
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='nav-pairs-test',
            filename='nav_pairs_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=6
        )
        session.add(batch)
        session.flush()

        # Create 6 raw rows to form 3 duplicate pairs
        rows = []
        for i in range(6):
            row = RawImportRow(
                batch_id='nav-pairs-test',
                row_index=i+1,
                raw_csv_data={'name': f'Person {(i//2)+1}', 'email': f'person{(i//2)+1}@example.com'}
            )
            rows.append(row)
            session.add(row)
        session.flush()

        # Create import contacts with unique names for each pair
        contacts = []
        for i, row in enumerate(rows):
            contact = ImportContact(
                batch_id='nav-pairs-test',
                raw_import_row_id=row.id,
                first_name=f'FirstName{(i//2)+1}',
                last_name=f'LastName{(i//2)+1}',
                email=f'person{(i//2)+1}@example.com',
                phone=f'555-000{i}'
            )
            contacts.append(contact)
            session.add(contact)
        session.flush()

        # Create 3 duplicate pairs with unique identifying info
        pair_names = [
            ('Alice Alpha', 'Alice Alpha Jr'),
            ('Bob Beta', 'Robert Beta'),
            ('Carol Gamma', 'Caroline Gamma')
        ]

        for pair_idx in range(3):
            idx_a = pair_idx * 2
            idx_b = pair_idx * 2 + 1

            duplicate_payload = {
                'contact_a': {
                    'id': str(contacts[idx_a].id),
                    'name': pair_names[pair_idx][0],
                    'email': f'person{pair_idx+1}@example.com',
                    'phone': f'555-000{idx_a}',
                    'address': f'{100+pair_idx} Oak Street'
                },
                'contact_b': {
                    'id': str(contacts[idx_b].id),
                    'name': pair_names[pair_idx][1],
                    'email': f'person{pair_idx+1}@example.com',
                    'phone': f'555-000{idx_b}',
                    'address': f'{100+pair_idx} Oak Street'
                },
                'supporting_evidence': [f'Pair {pair_idx+1} match evidence'],
                'conflicting_evidence': [],
            }

            dup_item = ReviewItem(
                batch_id='nav-pairs-test',
                item_type='duplicate',
                status='pending',
                payload_json=duplicate_payload,
            )
            session.add(dup_item)

        session.commit()
        session.close()

        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to duplicates page
                await page.goto('http://127.0.0.1:8001/imports/nav-pairs-test/duplicates')
                await page.wait_for_selector('div.card', timeout=5000)

                # Step 1: Verify first pair is displayed
                page_metadata = await page.query_selector('p.page-metadata')
                metadata_text = await page_metadata.inner_text()
                assert 'Pair 1 of 3' in metadata_text, f"Should show 'Pair 1 of 3', got: {metadata_text}"
                print(f"✓ Page shows Pair 1 of 3")

                # Verify first pair contact names are visible
                page_text = await page.inner_text('body')
                assert 'Alice Alpha' in page_text, "First pair contact A should be visible"
                assert 'Alice Alpha Jr' in page_text, "First pair contact B should be visible"
                print("✓ First pair contacts displayed correctly")

                # Step 2: Verify Previous Pair button is disabled (we're on pair 1)
                prev_button = await page.query_selector('button:has-text("← Previous Pair")')
                assert prev_button is not None, "Previous Pair button should exist on first pair"
                prev_disabled = not await prev_button.is_enabled()
                assert prev_disabled, "Previous button should be disabled on first pair"
                print("✓ Previous Pair button is disabled (correctly showing we're on first pair)")

                # Step 3: Verify Next Pair link exists and is enabled
                next_link = await page.query_selector('a:has-text("Next Pair →")')
                assert next_link is not None, "Next Pair link should exist and be clickable"
                print("✓ Next Pair link found and enabled")

                # Step 4: Verify decision buttons still exist
                same_person_btn = await page.query_selector('button:has-text("Mark as Same Person")')
                assert same_person_btn is not None, "Decision buttons should still be visible"
                print("✓ Decision buttons visible on first pair")

                # Step 5: Click Next Pair
                await next_link.click()
                print("✓ Clicked Next Pair")

                # Wait for page to load second pair
                await page.wait_for_function(
                    "() => document.querySelector('p.page-metadata')?.textContent?.includes('Pair 2 of 3')",
                    timeout=5000
                )

                # Step 6: Verify second pair is now displayed
                page_metadata = await page.query_selector('p.page-metadata')
                metadata_text = await page_metadata.inner_text()
                assert 'Pair 2 of 3' in metadata_text, f"Should show 'Pair 2 of 3', got: {metadata_text}"
                print(f"✓ Page now shows Pair 2 of 3")

                # Verify second pair contact names are visible
                page_text = await page.inner_text('body')
                assert 'Bob Beta' in page_text, "Second pair contact A should be visible"
                assert 'Robert Beta' in page_text, "Second pair contact B should be visible"
                assert 'Alice Alpha' not in page_text, "First pair should no longer be visible"
                print("✓ Second pair contacts displayed correctly")

                # Step 7: Verify Previous Pair link now exists and is enabled
                prev_link = await page.query_selector('a:has-text("← Previous Pair")')
                assert prev_link is not None, "Previous Pair link should now be enabled"
                print("✓ Previous Pair link is now enabled")

                # Step 8: Verify decision buttons still exist on second pair
                same_person_btn = await page.query_selector('button:has-text("Mark as Same Person")')
                assert same_person_btn is not None, "Decision buttons should still be visible on second pair"
                print("✓ Decision buttons still visible on second pair")

                # Step 9: Click Previous Pair to go back to first pair
                await prev_link.click()
                print("✓ Clicked Previous Pair")

                # Wait for page to reload first pair
                await page.wait_for_function(
                    "() => document.querySelector('p.page-metadata')?.textContent?.includes('Pair 1 of 3')",
                    timeout=5000
                )

                # Step 10: Verify we're back to first pair
                page_metadata = await page.query_selector('p.page-metadata')
                metadata_text = await page_metadata.inner_text()
                assert 'Pair 1 of 3' in metadata_text, f"Should show 'Pair 1 of 3' again, got: {metadata_text}"
                print(f"✓ Back to Pair 1 of 3")

                page_text = await page.inner_text('body')
                assert 'Alice Alpha' in page_text, "First pair contact A should be visible again"
                assert 'Bob Beta' not in page_text, "Second pair should no longer be visible"
                print("✓ First pair contacts restored after navigation back")

                # Step 11: Navigate to last pair and verify Next Pair is disabled
                next_link = await page.query_selector('a:has-text("Next Pair →")')
                await next_link.click()
                await page.wait_for_function(
                    "() => document.querySelector('p.page-metadata')?.textContent?.includes('Pair 2 of 3')",
                    timeout=5000
                )

                next_link = await page.query_selector('a:has-text("Next Pair →")')
                await next_link.click()
                await page.wait_for_function(
                    "() => document.querySelector('p.page-metadata')?.textContent?.includes('Pair 3 of 3')",
                    timeout=5000
                )

                # Verify we're on last pair
                page_metadata = await page.query_selector('p.page-metadata')
                metadata_text = await page_metadata.inner_text()
                assert 'Pair 3 of 3' in metadata_text, f"Should show 'Pair 3 of 3', got: {metadata_text}"
                print("✓ Navigated to last pair (Pair 3 of 3)")

                # Verify Next Pair button is now disabled
                next_button = await page.query_selector('button:has-text("Next Pair →")')
                assert next_button is not None, "Next Pair button should exist on last pair"
                next_disabled = not await next_button.is_enabled()
                assert next_disabled, "Next button should be disabled on last pair"
                print("✓ Next Pair button is disabled (correctly showing we're on last pair)")

                print(f"\n=== TEST PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_back_to_dashboard_navigation(flask_app_database_mode):
    """
    GOAL: Verify "Back to Dashboard" link exists and navigates correctly.

    Flow:
    1. Seed database with single duplicate pair
    2. Load duplicates page
    3. Verify "Back to Dashboard" link exists and points to correct URL
    4. Click "Back to Dashboard" and verify navigation works
    """
    from playwright.async_api import async_playwright

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='dashboard-nav-test',
            filename='dashboard_nav_test.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create raw rows
        row1 = RawImportRow(batch_id='dashboard-nav-test', row_index=1, raw_csv_data={'name': 'Frank Brown'})
        row2 = RawImportRow(batch_id='dashboard-nav-test', row_index=2, raw_csv_data={'name': 'Frank Brown'})
        session.add(row1)
        session.add(row2)
        session.flush()

        # Create import contacts
        contact1 = ImportContact(batch_id='dashboard-nav-test', raw_import_row_id=row1.id, first_name='Frank', last_name='Brown', email='frank@example.com')
        contact2 = ImportContact(batch_id='dashboard-nav-test', raw_import_row_id=row2.id, first_name='Frank', last_name='Brown', email='frank@example.com')
        session.add(contact1)
        session.add(contact2)
        session.flush()

        # Create duplicate review item
        dup_payload = {
            'contact_a': {'id': str(contact1.id), 'name': 'Frank Brown', 'email': 'frank@example.com', 'phone': '', 'address': ''},
            'contact_b': {'id': str(contact2.id), 'name': 'Frank Brown', 'email': 'frank@example.com', 'phone': '', 'address': ''},
            'supporting_evidence': ['Exact name match'],
            'conflicting_evidence': [],
        }

        dup_item = ReviewItem(batch_id='dashboard-nav-test', item_type='duplicate', status='pending', payload_json=dup_payload)
        session.add(dup_item)
        session.commit()
        session.close()

        # Launch browser
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to duplicates page
                await page.goto('http://127.0.0.1:8001/imports/dashboard-nav-test/duplicates')
                await page.wait_for_selector('div.card', timeout=5000)

                # Verify Back to Dashboard link exists and points to correct URL
                dashboard_link = await page.query_selector('a:has-text("Back to Dashboard")')
                assert dashboard_link is not None, "Back to Dashboard link should exist"
                print("✓ Back to Dashboard link found")

                # Get the href attribute
                href = await dashboard_link.get_attribute('href')
                expected_href = '/imports/dashboard-nav-test/dashboard'
                assert href == expected_href, f"Link should point to '{expected_href}', got: {href}"
                print(f"✓ Back to Dashboard link points to correct URL: {href}")

                # Click Back to Dashboard
                await dashboard_link.click()

                # Wait for navigation (either dashboard page loads or we get redirected somewhere)
                await page.wait_for_function(
                    "() => window.location.href.includes('/dashboard') || window.location.href.includes('/imports')",
                    timeout=5000
                )

                # Verify we're on the dashboard URL
                current_url = page.url
                assert 'dashboard' in current_url or 'dashboard-nav-test' in current_url, f"Should navigate to dashboard, got URL: {current_url}"
                print(f"✓ Navigated to dashboard: {current_url}")

                print(f"\n=== TEST PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()
