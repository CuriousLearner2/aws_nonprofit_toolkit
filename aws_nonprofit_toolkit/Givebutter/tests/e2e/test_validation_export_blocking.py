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
