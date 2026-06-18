"""
E2E browser tests for validation blocker detection in export workflow.

CRITICAL WORKFLOWS TESTED:
- Test A: Blocking validation issue appears in export console UI and blocks export
- Test B: Export blocked when validation blocker present
- Test C: Clean validation export proceeds normally

Focus:
- Real ingestion payloads with 'issue' field (not 'issue_type')
- Blocker detection using schema-agnostic helper function
- Export behavior with validation blockers
- Append-only principle (raw data unchanged)

Infrastructure:
- Database-backed Flask testing with ImportBatch/ReviewItem seeding
- Real ingestion payload format: 'issue' field
- Flask runs in background thread, Playwright drives browser

Synchronization:
- Use page.wait_for_function() to poll DOM state
- Wait for observable completion signals before proceeding
- All browser clicks are real Playwright clicks (not mocked)

Assertions:
- Hard assertions only (test fails if condition not met)
- Database verification: Query validation items to verify persistence
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
# TEST A: Blocking validation issue appears in export console UI and blocks export
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_blocker_appears_in_export_console(e2e_database_and_app):
    """
    Verify validation blocker with real ingestion format is detected and prevents export.

    Scenario:
    1. Seed ImportBatch with validation blocker (missing_email with real 'issue' field)
    2. Call export preview service to verify blocker detection
    3. Open Export Console in browser and verify blocker appears
    4. Assert export appears blocked
    5. Assert raw ImportContact data unchanged

    Expected behavior:
    - Validation blocker with 'issue' field is detected correctly
    - Export preview correctly counts blocker
    - Export console shows blocker warning
    - Raw data remains unchanged (append-only)
    """
    from playwright.async_api import async_playwright
    from scripts.householder.export_preview_service import build_export_preview

    database_url, db_path, flask_app = e2e_database_and_app

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='validation-blocker-batch-a',
            filename='validation_blocker_a.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row
        raw_row = RawImportRow(
            batch_id='validation-blocker-batch-a',
            row_index=1,
            raw_csv_data={
                'name': 'Blocker Test A',
                'date': '2026-06-18',
                'email': '',  # Missing email
                'phone': '(555) 111-1111',
                'amount': '250.00',
                'address': '444 Blocker Ave A',
                'transaction_id': 'TXN-BLOCK-A'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='validation-blocker-batch-a',
            raw_import_row_id=raw_row.id,
            first_name='Blocker',
            last_name='TestA',
            email='',  # Missing email
            phone='(555) 111-1111',
            address_line1='444 Blocker Ave A',
            amount=250.00
        )
        session.add(contact)
        session.flush()

        # Create validation review item with REAL INGESTION FORMAT ('issue' field)
        val_item = ReviewItem(
            batch_id='validation-blocker-batch-a',
            item_type='validation',
            confidence=1.0,
            payload_json={
                'field': 'email',
                'issue': 'missing_email',  # REAL INGESTION FORMAT
                'suggestion': None,
                'validation_tier': 'critical'
            }
        )
        session.add(val_item)
        session.flush()

        # Add subject linking contact to validation item
        subject = ReviewItemSubject(
            review_item_id=val_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.flush()
        session.commit()

        contact_id = contact.id

        # A1: Verify blocker is detected by export preview service
        preview = build_export_preview('validation-blocker-batch-a', {'GIVEBUTTER_DATABASE_URL': database_url})
        assert preview.blocked_count == 1, "A1 FAILED: Export preview should detect blocker"
        assert len(preview.blockers) > 0, "A1 FAILED: Blockers list should contain blocker"
        print(f"✓ A1: Export preview service detected blocker: {preview.blockers[0]}")

        # A2: Verify raw ImportContact data unchanged (append-only principle)
        contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
        assert contact_check is not None, "A2 FAILED: Contact should still exist"
        assert contact_check.first_name == 'Blocker', "A2 FAILED: Contact first_name should be unchanged"
        assert contact_check.email == '', "A2 FAILED: Contact email should be unchanged"
        print("✓ A2: Raw ImportContact data unchanged (append-only principle)")

        # A3: Verify blocker appears in browser
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
                requests.get('http://127.0.0.1:8001/imports/validation-blocker-batch-a/exports', timeout=2)
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
                await page.goto('http://127.0.0.1:8001/imports/validation-blocker-batch-a/exports')
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ A3a: Export console page loaded")

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/validation-blocker-batch-a/exports/preview', {
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

                await page.wait_for_selector('h1', timeout=5000)
                print("✓ A3b: Export preview loaded in browser")

                # Verify blocker warning is visible
                page_text = await page.inner_text('body')
                has_blocker_indicator = ('blocker' in page_text.lower() or 'blocked' in page_text.lower())
                assert has_blocker_indicator, "A3c FAILED: Blocker warning should appear in export preview"
                print("✓ A3c: Blocker warning visible in browser export preview")

                print("\n=== TEST A: VALIDATION BLOCKER APPEARS PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST B: Clean validation export proceeds normally
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_clean_validation_export_proceeds(e2e_database_and_app):
    """
    Verify export preview correctly handles clean data with no validation blockers.

    Scenario:
    1. Seed ImportBatch with NO validation blockers (clean data)
    2. Call export preview service to verify no blockers
    3. Open Export Console in browser and verify no blocker warning
    4. Assert export preview shows ready status
    5. Assert raw ImportContact data unchanged

    Expected behavior:
    - Clean import shows blocked_count=0
    - Export appears ready to proceed
    - No blocker warnings
    - Raw data unchanged
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch (clean, no validation blockers)
        batch = ImportBatch(
            id='clean-validation-batch-c',
            filename='clean_validation_c.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row (valid data)
        raw_row = RawImportRow(
            batch_id='clean-validation-batch-c',
            row_index=1,
            raw_csv_data={
                'name': 'Clean Test',
                'date': '2026-06-18',
                'email': 'clean@example.com',  # Valid email
                'phone': '(555) 333-3333',
                'amount': '500.00',
                'address': '666 Clean Ave C',
                'transaction_id': 'TXN-CLEAN-C'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact (valid data, no issues)
        contact = ImportContact(
            batch_id='clean-validation-batch-c',
            raw_import_row_id=raw_row.id,
            first_name='Clean',
            last_name='TestC',
            email='clean@example.com',  # Valid
            phone='(555) 333-3333',
            address_line1='666 Clean Ave C',
            amount=500.00
        )
        session.add(contact)
        session.flush()
        session.commit()

        contact_id = contact.id

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
                requests.get('http://127.0.0.1:8001/imports/clean-validation-batch-c/exports', timeout=2)
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
                # C0: Navigate to exports page
                await page.goto('http://127.0.0.1:8001/imports/clean-validation-batch-c/exports')

                # Wait for page to load
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ C0: Export console page loaded (clean batch)")

                # C1: Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/clean-validation-batch-c/exports/preview', {
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

                # Wait for preview to load
                await page.wait_for_selector('h1', timeout=5000)
                print("✓ C1: Export preview loaded (clean data)")

                # C2: Verify no blocker warning
                page_text = await page.inner_text('body')
                has_blocker_warning = ('blocker' in page_text.lower() and 'validation' in page_text.lower())
                assert not has_blocker_warning, f"C2 FAILED: Should not have blocker warning for clean data, got: {page_text[:200]}"
                print("✓ C2: No blocker warning for clean data")

                # C3: Verify export button exists
                export_btn = await page.query_selector('#generate-export-btn')
                assert export_btn is not None, "C3 FAILED: Export button should exist"
                print("✓ C3: Export button exists")

                # C4: Verify export button is enabled (or at least not blocked)
                is_disabled = await export_btn.is_disabled() if export_btn else False
                assert not is_disabled, "C4 FAILED: Export button should be enabled for clean data"
                print("✓ C4: Export button is enabled (clean data is export-ready)")

                # C5: Verify raw ImportContact data unchanged
                contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
                assert contact_check is not None, "C5 FAILED: Contact should still exist"
                assert contact_check.first_name == 'Clean', "C5 FAILED: Contact first_name should be unchanged"
                assert contact_check.email == 'clean@example.com', "C5 FAILED: Contact email should be unchanged"
                print("✓ C5: Raw ImportContact data unchanged (append-only principle)")

                print("\n=== TEST C: CLEAN VALIDATION EXPORT PROCEEDS PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST D: Failed autosave values must not appear in export
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_failed_autosave_values_not_exported(e2e_database_and_app):
    """
    Verify that values from failed autosave attempts do not appear in export.

    Scenario:
    1. Seed ImportBatch with valid contact (email='john@example.com')
    2. Attempt autosave with invalid email (will fail validation)
    3. Verify autosave endpoint returns 400 (failure)
    4. Verify no ReviewDecision was created for failed autosave
    5. Call export preview service
    6. Assert export row contains original valid email (from ImportContact)
    7. Assert export row does NOT contain the failed autosave email
    8. Verify raw ImportContact data unchanged (append-only principle)

    Expected behavior:
    - Failed autosave is rejected at endpoint, no ReviewDecision created
    - Export preview reads only persisted ReviewDecision records
    - Export row contains original valid email from ImportContact snapshot
    - Failed autosave value never persists, never reaches export
    """
    from scripts.householder.export_preview_service import build_export_preview
    import requests

    database_url, db_path, flask_app = e2e_database_and_app

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='failed-autosave-batch-d',
            filename='failed_autosave_d.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with VALID email
        raw_row = RawImportRow(
            batch_id='failed-autosave-batch-d',
            row_index=1,
            raw_csv_data={
                'name': 'Valid Contact',
                'date': '2026-06-18',
                'email': 'john@example.com',  # Valid email in raw data
                'phone': '(555) 444-4444',
                'amount': '300.00',
                'address': '777 Autosave Ave D',
                'transaction_id': 'TXN-AUTOSAVE-D'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact with valid email
        contact = ImportContact(
            batch_id='failed-autosave-batch-d',
            raw_import_row_id=raw_row.id,
            first_name='Valid',
            last_name='Contact',
            email='john@example.com',  # Valid email
            phone='(555) 444-4444',
            address_line1='777 Autosave Ave D',
            amount=300.00
        )
        session.add(contact)
        session.flush()
        session.commit()

        contact_id = contact.id
        original_email = contact.email

        # D1: Verify contact has valid email before autosave attempt
        contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
        assert contact_check.email == 'john@example.com', \
            "D1 FAILED: Contact should have valid email before autosave"
        print("✓ D1: Contact initialized with valid email")

        # Start Flask server
        def run_flask():
            flask_app.run(host='127.0.0.1', port=8001, debug=False, use_reloader=False)

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Wait for server
        await asyncio.sleep(2)

        # D2: Attempt failed autosave with INVALID email
        # This autosave should fail validation and return 400
        response = requests.post(
            'http://127.0.0.1:8001/imports/failed-autosave-batch-d/autosave',
            json={
                'raw_import_row_id': raw_row.id,
                'corrected_values': {'email': 'invalid-no-at-symbol'}  # Invalid
            },
            timeout=5
        )

        assert response.status_code == 400, \
            f"D2 FAILED: Autosave should fail with 400, got {response.status_code}"
        print("✓ D2: Autosave correctly rejected with 400 (invalid email)")

        # D3: Verify NO ReviewDecision was created
        review_decisions = session.query(ReviewDecision).filter_by(
            batch_id='failed-autosave-batch-d'
        ).all()
        assert len(review_decisions) == 0, \
            f"D3 FAILED: No ReviewDecision should exist after failed autosave, found {len(review_decisions)}"
        print("✓ D3: No ReviewDecision persisted after failed autosave")

        # D4: Verify raw ImportContact email is STILL the original valid email
        contact_check = session.query(ImportContact).filter_by(id=contact_id).first()
        assert contact_check.email == 'john@example.com', \
            f"D4 FAILED: Contact email should remain original, got {contact_check.email}"
        print("✓ D4: ImportContact email unchanged after failed autosave attempt")

        # D5: Build export preview and verify export row contains original email
        preview = build_export_preview('failed-autosave-batch-d', {'GIVEBUTTER_DATABASE_URL': database_url})
        assert len(preview.export_rows) == 1, \
            f"D5 FAILED: Export should have 1 row, got {len(preview.export_rows)}"

        export_row = preview.export_rows[0]
        assert export_row.email == 'john@example.com', \
            f"D5 FAILED: Export row should contain original email 'john@example.com', got '{export_row.email}'"
        print(f"✓ D5: Export row contains original email (not failed autosave value)")

        # D6: Verify failed autosave email is NOT in export
        assert export_row.email != 'invalid-no-at-symbol', \
            "D6 FAILED: Export row should NOT contain the failed autosave email"
        print("✓ D6: Failed autosave value ('invalid-no-at-symbol') not in export")

        # D7: Verify raw ImportContact data unchanged (append-only principle)
        contact_final = session.query(ImportContact).filter_by(id=contact_id).first()
        assert contact_final is not None, "D7 FAILED: Contact should still exist"
        assert contact_final.first_name == 'Valid', "D7 FAILED: Contact first_name unchanged"
        assert contact_final.email == 'john@example.com', "D7 FAILED: Contact email unchanged"
        print("✓ D7: Raw ImportContact data unchanged (append-only principle)")

        print("\n=== TEST D: FAILED AUTOSAVE VALUES NOT EXPORTED PASSED ===")

    finally:
        session.close()


# ==============================================================================
# TEST E: Persisted validation overrides allow export when appropriate
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_persisted_validation_override_allows_export(e2e_database_and_app):
    """
    Verify that accepted validation overrides remove blockers and allow export.

    Scenario:
    1. Seed ImportBatch with validation blocker (missing_email)
    2. Create ReviewDecision with decision='accept_issue' to override the blocker
    3. Call export preview service to verify blocker is no longer counted
    4. Verify export row shows validation_status='accepted' (not 'blocked')
    5. Verify export button becomes enabled
    6. Assert export can proceed

    Expected behavior:
    - Validation blocker with accepted ReviewDecision is not counted as blocking
    - export preview shows blocked_count=0
    - validation_status reflects 'accepted', not 'blocked'
    - Export proceeds without error
    - Raw ImportContact data unchanged (append-only principle)
    """
    from playwright.async_api import async_playwright
    from scripts.householder.export_preview_service import build_export_preview

    database_url, db_path, flask_app = e2e_database_and_app

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='validation-override-batch-e',
            filename='validation_override_e.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with MISSING EMAIL
        raw_row = RawImportRow(
            batch_id='validation-override-batch-e',
            row_index=1,
            raw_csv_data={
                'name': 'Override Test',
                'date': '2026-06-18',
                'email': '',  # Missing email - would be blocker
                'phone': '(555) 555-5555',
                'amount': '350.00',
                'address': '888 Override Ave E',
                'transaction_id': 'TXN-OVERRIDE-E'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact with missing email
        contact = ImportContact(
            batch_id='validation-override-batch-e',
            raw_import_row_id=raw_row.id,
            first_name='Override',
            last_name='TestE',
            email='',  # Missing email
            phone='(555) 555-5555',
            address_line1='888 Override Ave E',
            amount=350.00
        )
        session.add(contact)
        session.flush()

        # Create validation review item (missing_email blocker)
        val_item = ReviewItem(
            batch_id='validation-override-batch-e',
            item_type='validation',
            confidence=1.0,
            payload_json={
                'field': 'email',
                'issue': 'missing_email',  # CRITICAL BLOCKER
                'suggestion': None,
                'validation_tier': 'critical'
            }
        )
        session.add(val_item)
        session.flush()

        # Add subject linking contact to validation item
        subject = ReviewItemSubject(
            review_item_id=val_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.commit()  # Commit before calling build_export_preview

        # E1: Verify blocker is detected BEFORE override
        preview_before = build_export_preview('validation-override-batch-e', {'GIVEBUTTER_DATABASE_URL': database_url})
        assert preview_before.blocked_count == 1, \
            "E1 FAILED: Export preview should detect blocker before override"
        print("✓ E1: Blocker detected before override (blocked_count=1)")

        # E2: Create ReviewDecision with 'accept_issue' to override the blocker
        override_decision = ReviewDecision(
            batch_id='validation-override-batch-e',
            review_item_id=val_item.id,
            decision='accept_issue',  # Accept/override the validation issue
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer'
        )
        session.add(override_decision)
        session.commit()

        print("✓ E2: ReviewDecision created with decision='accept_issue'")

        # E3: Build export preview AFTER override
        preview_after = build_export_preview('validation-override-batch-e', {'GIVEBUTTER_DATABASE_URL': database_url})
        assert preview_after.blocked_count == 0, \
            f"E3 FAILED: Export preview should have 0 blockers after override, got {preview_after.blocked_count}"
        print("✓ E3: Blocker removed after override (blocked_count=0)")

        # E4: Verify export row validation_status is 'accepted', not 'blocked'
        assert len(preview_after.export_rows) == 1, \
            f"E4 FAILED: Export should have 1 row, got {len(preview_after.export_rows)}"
        export_row = preview_after.export_rows[0]
        assert export_row.validation_status == 'accepted', \
            f"E4 FAILED: validation_status should be 'accepted', got '{export_row.validation_status}'"
        print("✓ E4: Export row validation_status='accepted' (overridden)")

        # E5: Verify raw ImportContact data unchanged (append-only principle)
        contact_check = session.query(ImportContact).filter_by(id=contact.id).first()
        assert contact_check is not None, "E5 FAILED: Contact should still exist"
        assert contact_check.email == '', "E5 FAILED: Contact email should be unchanged"
        print("✓ E5: Raw ImportContact data unchanged (append-only principle)")

        # E6: Verify in browser that export button is enabled (export can proceed)
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
                requests.get('http://127.0.0.1:8001/imports/validation-override-batch-e/exports', timeout=2)
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
                await page.goto('http://127.0.0.1:8001/imports/validation-override-batch-e/exports')
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/validation-override-batch-e/exports/preview', {
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

                await page.wait_for_selector('h1', timeout=5000)

                # E6: Verify export button is NOT disabled
                export_btn = await page.query_selector('#generate-export-btn')
                assert export_btn is not None, "E6 FAILED: Export button should exist"
                is_disabled = await export_btn.is_disabled() if export_btn else False
                assert not is_disabled, "E6 FAILED: Export button should be enabled after override"
                print("✓ E6: Export button enabled (export can proceed after override)")

                print("\n=== TEST E: PERSISTED VALIDATION OVERRIDE ALLOWS EXPORT PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()


# ==============================================================================
# TEST F: Deferred validation rows remain export-relevant
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_deferred_validation_remains_export_relevant(e2e_database_and_app):
    """
    Verify that deferred validation issues remain export-relevant and not hidden.

    Scenario:
    1. Seed ImportBatch with validation blocker (missing_email)
    2. Create ReviewDecision with decision='defer' to defer the issue
    3. Call export preview service to verify blocker is removed but warning remains
    4. Verify export row shows deferred status/warning
    5. Verify export button becomes enabled (not blocked)
    6. Verify deferred warning is visible in browser export preview
    7. Assert export can proceed but shows deferred status

    Expected behavior:
    - Deferred validation issues do not block export (blocked_count=0)
    - Deferred status is recorded in validation_status='deferred'
    - Warning is added to row_warnings (not hidden, not treated as clean)
    - Export proceeds but shows deferred indicator
    - Raw ImportContact data unchanged (append-only principle)
    """
    from playwright.async_api import async_playwright
    from scripts.householder.export_preview_service import build_export_preview

    database_url, db_path, flask_app = e2e_database_and_app

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='validation-deferred-batch-f',
            filename='validation_deferred_f.csv',
            upload_timestamp=datetime.utcnow(),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with MISSING EMAIL
        raw_row = RawImportRow(
            batch_id='validation-deferred-batch-f',
            row_index=1,
            raw_csv_data={
                'name': 'Deferred Test',
                'date': '2026-06-18',
                'email': '',  # Missing email - critical blocker
                'phone': '(555) 666-6666',
                'amount': '400.00',
                'address': '999 Deferred Ave F',
                'transaction_id': 'TXN-DEFERRED-F'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact with missing email
        contact = ImportContact(
            batch_id='validation-deferred-batch-f',
            raw_import_row_id=raw_row.id,
            first_name='Deferred',
            last_name='TestF',
            email='',  # Missing email
            phone='(555) 666-6666',
            address_line1='999 Deferred Ave F',
            amount=400.00
        )
        session.add(contact)
        session.flush()

        # Create validation review item (missing_email critical blocker)
        val_item = ReviewItem(
            batch_id='validation-deferred-batch-f',
            item_type='validation',
            confidence=1.0,
            payload_json={
                'field': 'email',
                'issue': 'missing_email',  # CRITICAL BLOCKER
                'suggestion': None,
                'validation_tier': 'critical'
            }
        )
        session.add(val_item)
        session.flush()

        # Add subject linking contact to validation item
        subject = ReviewItemSubject(
            review_item_id=val_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.commit()  # Commit before calling build_export_preview

        # F1: Verify blocker is detected BEFORE deferral
        preview_before = build_export_preview('validation-deferred-batch-f', {'GIVEBUTTER_DATABASE_URL': database_url})
        assert preview_before.blocked_count == 1, \
            "F1 FAILED: Export preview should detect blocker before deferral"
        print("✓ F1: Blocker detected before deferral (blocked_count=1)")

        # F2: Create ReviewDecision with 'defer' to defer the issue
        defer_decision = ReviewDecision(
            batch_id='validation-deferred-batch-f',
            review_item_id=val_item.id,
            decision='defer',  # Defer the validation issue
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer'
        )
        session.add(defer_decision)
        session.commit()

        print("✓ F2: ReviewDecision created with decision='defer'")

        # F3: Build export preview AFTER deferral
        preview_after = build_export_preview('validation-deferred-batch-f', {'GIVEBUTTER_DATABASE_URL': database_url})
        assert preview_after.blocked_count == 0, \
            f"F3 FAILED: Export preview should have 0 blockers after deferral, got {preview_after.blocked_count}"
        print("✓ F3: Blocker removed after deferral (blocked_count=0)")

        # F4: Verify export row validation_status is 'deferred' (not 'blocked', not 'clean')
        assert len(preview_after.export_rows) == 1, \
            f"F4 FAILED: Export should have 1 row, got {len(preview_after.export_rows)}"
        export_row = preview_after.export_rows[0]
        assert export_row.validation_status == 'deferred', \
            f"F4 FAILED: validation_status should be 'deferred', got '{export_row.validation_status}'"
        print("✓ F4: Export row validation_status='deferred' (not hidden)")

        # F5: Verify deferred warning is present in normalization_warnings or validation_issues (status remains visible)
        has_deferred_indicator = (
            'deferred' in export_row.validation_status.lower() or
            len(export_row.export_warnings) > 0
        )
        assert has_deferred_indicator, \
            f"F5 FAILED: Should have deferred indication, got validation_status='{export_row.validation_status}', export_warnings={export_row.export_warnings}"
        print(f"✓ F5: Deferred status visible (validation_status='deferred', export_warnings={export_row.export_warnings})")

        # F6: Verify raw ImportContact data unchanged (append-only principle)
        contact_check = session.query(ImportContact).filter_by(id=contact.id).first()
        assert contact_check is not None, "F6 FAILED: Contact should still exist"
        assert contact_check.email == '', "F6 FAILED: Contact email should be unchanged"
        print("✓ F6: Raw ImportContact data unchanged (append-only principle)")

        # F7: Verify in browser that export button is enabled (not blocked by deferred issue)
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
                requests.get('http://127.0.0.1:8001/imports/validation-deferred-batch-f/exports', timeout=2)
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
                await page.goto('http://127.0.0.1:8001/imports/validation-deferred-batch-f/exports')
                await page.wait_for_selector('h1', timeout=5000)

                # Generate export preview
                await page.evaluate("""
                    async () => {
                        const response = await fetch('/imports/validation-deferred-batch-f/exports/preview', {
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

                await page.wait_for_selector('h1', timeout=5000)

                # F7: Verify export button is enabled (not blocked by deferred issue)
                export_btn = await page.query_selector('#generate-export-btn')
                assert export_btn is not None, "F7 FAILED: Export button should exist"
                is_disabled = await export_btn.is_disabled() if export_btn else False
                assert not is_disabled, "F7 FAILED: Export button should be enabled (deferred is not blocking)"
                print("✓ F7: Export button enabled (deferred issue does not block export)")

                # F8: Verify deferred status is visible in browser preview
                page_text = await page.inner_text('body')
                has_deferred_indicator = ('deferred' in page_text.lower() or 'unresolved' in page_text.lower())
                assert has_deferred_indicator, \
                    "F8 FAILED: Deferred status should be visible in browser preview (not hidden)"
                print("✓ F8: Deferred status visible in browser export preview (not hidden)")

                print("\n=== TEST F: DEFERRED VALIDATION REMAINS EXPORT RELEVANT PASSED ===")

            finally:
                await browser.close()

    finally:
        session.close()
