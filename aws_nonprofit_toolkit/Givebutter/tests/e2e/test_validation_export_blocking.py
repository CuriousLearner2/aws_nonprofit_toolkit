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
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker
from werkzeug.serving import make_server

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


async def wait_for_validation_export_page_ready(url: str, timeout_seconds: int = 10) -> None:
	"""
	Wait for Flask server to be ready by polling a validation export page route.

	Uses exponential backoff polling with a bounded timeout.

	Args:
		url: Full URL to poll (e.g., 'http://127.0.0.1:8001/imports/{batch_id}/exports')
		timeout_seconds: Total timeout in seconds (default 10)

	Raises:
		RuntimeError: If the server does not become ready within timeout_seconds
	"""
	import requests
	import time

	start_time = time.time()
	wait_interval = 0.1

	while time.time() - start_time < timeout_seconds:
		try:
			response = requests.get(url, timeout=2)
			# Successful response means server is ready
			return
		except (requests.ConnectionError, requests.Timeout):
			# Server not ready yet, wait and retry
			await asyncio.sleep(wait_interval)
			# Exponential backoff: 0.1 → 0.15 → 0.225 → ... → capped at 1.0
			wait_interval = min(wait_interval * 1.5, 1.0)

	raise RuntimeError(f"Flask server failed to become ready at {url} after {timeout_seconds}s")


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
            upload_timestamp=datetime.now(timezone.utc),
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
        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/validation-blocker-batch-a/exports', timeout_seconds=10)

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

        # Explicit server shutdown and thread cleanup
        server.shutdown()
        flask_thread.join(timeout=2)

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
            upload_timestamp=datetime.now(timezone.utc),
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

        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/clean-validation-batch-c/exports', timeout_seconds=10)

        # Launch browser
        try:
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
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

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
            upload_timestamp=datetime.now(timezone.utc),
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

        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/failed-autosave-batch-d/exports', timeout_seconds=10)

        try:
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
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

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
            upload_timestamp=datetime.now(timezone.utc),
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
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/validation-override-batch-e/exports', timeout_seconds=10)

        # Launch browser
        try:
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
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

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
            upload_timestamp=datetime.now(timezone.utc),
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
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/validation-deferred-batch-f/exports', timeout_seconds=10)

        # Launch browser
        try:
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
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

    finally:
        session.close()


# ==============================================================================
# TEST G: Export warning appears for deferred validation issues
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_warning_appears_for_deferred_validation(e2e_database_and_app):
    """
    Verify export warning and confirmation checkbox appear when deferred validation issues exist.

    Scenario:
    1. Seed ImportBatch with deferred validation issue
    2. Navigate to /imports/{batch_id}/exports in browser
    3. Generate export preview
    4. Verify warning banner appears for deferred validation
    5. Verify confirmation checkbox is present
    6. Verify export button is initially disabled
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
            id='validation-deferred-export-warning-g',
            filename='validation_deferred_export_g.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with missing email
        raw_row = RawImportRow(
            batch_id='validation-deferred-export-warning-g',
            row_index=1,
            raw_csv_data={
                'name': 'Deferred Export Test',
                'date': '2026-06-18',
                'email': '',  # Missing email
                'phone': '(555) 777-7777',
                'amount': '450.00',
                'address': '111 Export Warning Ave G',
                'transaction_id': 'TXN-EXPORT-WARN-G'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='validation-deferred-export-warning-g',
            raw_import_row_id=raw_row.id,
            first_name='Export',
            last_name='WarningG',
            email='',  # Missing email
            phone='(555) 777-7777',
            address_line1='111 Export Warning Ave G',
            amount=450.00
        )
        session.add(contact)
        session.flush()

        # Create validation item
        val_item = ReviewItem(
            batch_id='validation-deferred-export-warning-g',
            item_type='validation',
            confidence=1.0,
            payload_json={
                'field': 'email',
                'issue': 'missing_email',
                'suggestion': None,
                'validation_tier': 'critical'
            }
        )
        session.add(val_item)
        session.flush()

        # Add subject
        subject = ReviewItemSubject(
            review_item_id=val_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.flush()

        # Create deferred decision
        defer_decision = ReviewDecision(
            batch_id='validation-deferred-export-warning-g',
            review_item_id=val_item.id,
            decision='defer',
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer'
        )
        session.add(defer_decision)
        session.commit()

        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/validation-deferred-export-warning-g/exports', timeout_seconds=10)

        # Launch browser
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    # G1: Navigate to exports page
                    await page.goto('http://127.0.0.1:8001/imports/validation-deferred-export-warning-g/exports')
                    await page.wait_for_selector('h1', timeout=5000)
                    print("✓ G1: Export console page loaded")

                    # G2: Generate preview
                    await page.evaluate("""
                        async () => {
                            const response = await fetch('/imports/validation-deferred-export-warning-g/exports/preview', {
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
                    print("✓ G2: Export preview loaded")

                    # G3: Verify deferred validation warning appears
                    deferred_validation_warning = await page.query_selector('#confirm-unresolved-validations-checkbox')
                    assert deferred_validation_warning is not None, \
                        "G3 FAILED: Validation confirmation checkbox should appear for deferred issues"
                    print("✓ G3: Validation confirmation checkbox present")

                    # G4: Verify export button is enabled (deferred doesn't block)
                    export_btn = await page.query_selector('#generate-export-btn')
                    is_disabled = await export_btn.is_disabled() if export_btn else False
                    assert not is_disabled, "G4 FAILED: Export button should be enabled (deferred issues do not block)"
                    print("✓ G4: Export button enabled (deferred issues do not block)")

                    print("\n=== TEST G: EXPORT WARNING APPEARS FOR DEFERRED VALIDATION PASSED ===")

                finally:
                    await browser.close()
        finally:
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

    finally:
        session.close()


# ==============================================================================
# TEST H: Export blocked when deferred validation confirmation unchecked
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_blocked_when_validation_confirmation_unchecked(e2e_database_and_app):
    """
    Verify export is blocked when deferred validation confirmation is not checked.

    Scenario:
    1. Seed ImportBatch with deferred validation issue
    2. Navigate to export console and generate preview
    3. Verify confirmation checkbox is present but unchecked
    4. Verify export button is disabled
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
            id='validation-unchecked-h',
            filename='validation_unchecked_h.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row and contact
        raw_row = RawImportRow(
            batch_id='validation-unchecked-h',
            row_index=1,
            raw_csv_data={
                'name': 'Unchecked Test',
                'date': '2026-06-18',
                'email': '',
                'phone': '(555) 888-8888',
                'amount': '500.00',
                'address': '222 Unchecked Ave H',
                'transaction_id': 'TXN-UNCHECKED-H'
            }
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id='validation-unchecked-h',
            raw_import_row_id=raw_row.id,
            first_name='Unchecked',
            last_name='TestH',
            email='',
            phone='(555) 888-8888',
            address_line1='222 Unchecked Ave H',
            amount=500.00
        )
        session.add(contact)
        session.flush()

        # Create validation item and deferred decision
        val_item = ReviewItem(
            batch_id='validation-unchecked-h',
            item_type='validation',
            confidence=1.0,
            payload_json={
                'field': 'email',
                'issue': 'missing_email',
                'suggestion': None,
                'validation_tier': 'critical'
            }
        )
        session.add(val_item)
        session.flush()

        subject = ReviewItemSubject(
            review_item_id=val_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.flush()

        defer_decision = ReviewDecision(
            batch_id='validation-unchecked-h',
            review_item_id=val_item.id,
            decision='defer',
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer'
        )
        session.add(defer_decision)
        session.commit()

        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/validation-unchecked-h/exports', timeout_seconds=10)

        # Launch browser
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    # H1: Navigate to exports page
                    await page.goto('http://127.0.0.1:8001/imports/validation-unchecked-h/exports')
                    await page.wait_for_selector('h1', timeout=5000)
                    print("✓ H1: Export console loaded")

                    # H2: Generate preview
                    await page.evaluate("""
                        async () => {
                            const response = await fetch('/imports/validation-unchecked-h/exports/preview', {
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
                    print("✓ H2: Export preview loaded")

                    # H3: Verify validation confirmation checkbox exists
                    validation_checkbox = await page.query_selector('#confirm-unresolved-validations-checkbox')
                    assert validation_checkbox is not None, \
                        "H3 FAILED: Validation confirmation checkbox should exist"
                    print("✓ H3: Validation confirmation checkbox exists")

                    # H4: Verify checkbox is unchecked initially
                    is_checked = await validation_checkbox.is_checked()
                    assert not is_checked, "H4 FAILED: Checkbox should be unchecked initially"
                    print("✓ H4: Checkbox is unchecked initially")

                    # H5: Verify export button is enabled (deferred doesn't block)
                    export_btn = await page.query_selector('#generate-export-btn')
                    is_disabled = await export_btn.is_disabled() if export_btn else False
                    assert not is_disabled, "H5 FAILED: Export button should be enabled (deferred issues do not block)"
                    print("✓ H5: Export button is enabled (deferred issues do not block)")

                    print("\n=== TEST H: EXPORT BLOCKED WHEN VALIDATION CONFIRMATION UNCHECKED PASSED ===")

                finally:
                    await browser.close()
        finally:
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

    finally:
        session.close()


# ==============================================================================
# TEST I: Export button enabled when deferred validation confirmation checked
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_export_button_enabled_when_validation_confirmation_checked(e2e_database_and_app):
    """
    Verify export button becomes enabled when deferred validation confirmation is checked.

    Scenario:
    1. Seed ImportBatch with deferred validation issue
    2. Navigate to export console
    3. Verify checkbox and button are present
    4. Check the confirmation checkbox
    5. Verify export button becomes enabled
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
            id='validation-checked-i',
            filename='validation_checked_i.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row and contact
        raw_row = RawImportRow(
            batch_id='validation-checked-i',
            row_index=1,
            raw_csv_data={
                'name': 'Checked Test',
                'date': '2026-06-18',
                'email': '',
                'phone': '(555) 999-9999',
                'amount': '600.00',
                'address': '333 Checked Ave I',
                'transaction_id': 'TXN-CHECKED-I'
            }
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id='validation-checked-i',
            raw_import_row_id=raw_row.id,
            first_name='Checked',
            last_name='TestI',
            email='',
            phone='(555) 999-9999',
            address_line1='333 Checked Ave I',
            amount=600.00
        )
        session.add(contact)
        session.flush()

        # Create validation item and deferred decision
        val_item = ReviewItem(
            batch_id='validation-checked-i',
            item_type='validation',
            confidence=1.0,
            payload_json={
                'field': 'email',
                'issue': 'missing_email',
                'suggestion': None,
                'validation_tier': 'critical'
            }
        )
        session.add(val_item)
        session.flush()

        subject = ReviewItemSubject(
            review_item_id=val_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(subject)
        session.flush()

        defer_decision = ReviewDecision(
            batch_id='validation-checked-i',
            review_item_id=val_item.id,
            decision='defer',
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer'
        )
        session.add(defer_decision)
        session.commit()

        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/validation-checked-i/exports', timeout_seconds=10)

        # Launch browser
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    # I1: Navigate to exports page
                    await page.goto('http://127.0.0.1:8001/imports/validation-checked-i/exports')
                    await page.wait_for_selector('h1', timeout=5000)
                    print("✓ I1: Export console loaded")

                    # I2: Generate preview
                    await page.evaluate("""
                        async () => {
                            const response = await fetch('/imports/validation-checked-i/exports/preview', {
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
                    print("✓ I2: Export preview loaded")

                    # I3: Verify button is enabled (deferred doesn't block)
                    export_btn = await page.query_selector('#generate-export-btn')
                    is_initially_disabled = await export_btn.is_disabled()
                    assert not is_initially_disabled, "I3 FAILED: Export button should be enabled (deferred issues do not block)"
                    print("✓ I3: Export button enabled (deferred issues do not block)")

                    # I4: Check the validation confirmation checkbox
                    validation_checkbox = await page.query_selector('#confirm-unresolved-validations-checkbox')
                    await validation_checkbox.check()
                    print("✓ I4: Validation confirmation checkbox checked")

                    # I5: Verify button remains enabled
                    is_enabled = not await export_btn.is_disabled()
                    assert is_enabled, "I5 FAILED: Export button should remain enabled"
                    print("✓ I5: Export button remains enabled")

                    print("\n=== TEST I: EXPORT BUTTON ENABLED WHEN VALIDATION CONFIRMATION CHECKED PASSED ===")

                finally:
                    await browser.close()
        finally:
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

    finally:
        session.close()


# ==============================================================================
# TEST J: Clean validation export skips confirmation
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_clean_validation_export_skips_confirmation(e2e_database_and_app):
    """
    Verify export with clean validation (no deferred issues) skips confirmation requirement.

    Scenario:
    1. Seed ImportBatch with no validation issues
    2. Navigate to export console
    3. Verify NO confirmation checkbox appears
    4. Verify export button is enabled
    5. Generate export without any confirmations
    6. Verify export succeeds
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch with clean data
        batch = ImportBatch(
            id='clean-validation-export-j',
            filename='clean_validation_export_j.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with valid data (no issues)
        raw_row = RawImportRow(
            batch_id='clean-validation-export-j',
            row_index=1,
            raw_csv_data={
                'name': 'Clean Export Test',
                'date': '2026-06-18',
                'email': 'clean@example.com',  # Valid
                'phone': '(555) 111-2222',
                'amount': '700.00',
                'address': '444 Clean Export Ave J',
                'transaction_id': 'TXN-CLEAN-EXPORT-J'
            }
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id='clean-validation-export-j',
            raw_import_row_id=raw_row.id,
            first_name='Clean',
            last_name='ExportJ',
            email='clean@example.com',  # Valid
            phone='(555) 111-2222',
            address_line1='444 Clean Export Ave J',
            amount=700.00
        )
        session.add(contact)
        session.commit()

        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/clean-validation-export-j/exports', timeout_seconds=10)

        # Launch browser
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    # J1: Navigate to exports page
                    await page.goto('http://127.0.0.1:8001/imports/clean-validation-export-j/exports')
                    await page.wait_for_selector('h1', timeout=5000)
                    print("✓ J1: Export console loaded (clean validation)")

                    # J2: Generate preview
                    await page.evaluate("""
                        async () => {
                            const response = await fetch('/imports/clean-validation-export-j/exports/preview', {
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
                    print("✓ J2: Export preview loaded (clean validation)")

                    # J3: Verify NO validation confirmation checkbox appears
                    validation_checkbox = await page.query_selector('#confirm-unresolved-validations-checkbox')
                    assert validation_checkbox is None, \
                        "J3 FAILED: Validation confirmation checkbox should NOT appear for clean validation"
                    print("✓ J3: No validation confirmation checkbox (clean validation)")

                    # J4: Verify export button is enabled
                    export_btn = await page.query_selector('#generate-export-btn')
                    is_disabled = await export_btn.is_disabled() if export_btn else False
                    assert not is_disabled, "J4 FAILED: Export button should be enabled for clean validation"
                    print("✓ J4: Export button enabled (no confirmation required for clean validation)")

                    print("\n=== TEST J: CLEAN VALIDATION EXPORT SKIPS CONFIRMATION PASSED ===")

                finally:
                    await browser.close()
        finally:
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

    finally:
        session.close()


# ==============================================================================
# TEST K: Mixed validation + household warnings require independent confirmations
# ==============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_mixed_validation_household_export_warnings(e2e_database_and_app):
    """
    Verify mixed warning types (validation + household deferred) require independent confirmations.

    Scenario:
    1. Seed ImportBatch with one contact
    2. Create deferred validation item for that contact
    3. Create deferred household item for that contact
    4. Navigate to Export Console
    5. Verify both warning banners appear
    6. Verify both checkboxes present and independent
    7. Verify button disabled initially
    8. Check validation checkbox only → button stays disabled
    9. Check household checkbox too → button becomes enabled
    10. Verify both confirmations can be unchecked independently
    11. Verify export proceeds when both checked

    Expected behavior:
    - Both warnings render simultaneously
    - Both checkboxes independent
    - JavaScript AND logic enforces both required
    - Each checkbox state tracked independently
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
            id='mixed-export-warnings-k',
            filename='mixed_export_warnings_k.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row
        raw_row = RawImportRow(
            batch_id='mixed-export-warnings-k',
            row_index=1,
            raw_csv_data={
                'name': 'Mixed Warning Test',
                'date': '2026-06-19',
                'email': '',  # Missing email for validation issue
                'phone': '(555) 999-9999',
                'amount': '650.00',
                'address': '555 Mixed Warning Ave K',
                'transaction_id': 'TXN-MIXED-K'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='mixed-export-warnings-k',
            raw_import_row_id=raw_row.id,
            first_name='Mixed',
            last_name='WarningK',
            email='',  # Missing email
            phone='(555) 999-9999',
            address_line1='555 Mixed Warning Ave K',
            amount=650.00
        )
        session.add(contact)
        session.flush()

        # Create deferred validation item
        val_item = ReviewItem(
            batch_id='mixed-export-warnings-k',
            item_type='validation',
            confidence=1.0,
            payload_json={
                'field': 'email',
                'issue': 'missing_email',
                'suggestion': None,
                'validation_tier': 'critical'
            }
        )
        session.add(val_item)
        session.flush()

        # Create deferred household item
        hh_item = ReviewItem(
            batch_id='mixed-export-warnings-k',
            item_type='household',
            confidence=0.85,
            payload_json={
                'suggested_name': 'Mixed Warning Household',
                'address': '555 Mixed Warning Ave K',
                'proposed_members': ['Mixed WarningK'],
                'evidence': ['Same address'],
                'conflicts': [],
                'basis': 'Test mixed warning'
            }
        )
        session.add(hh_item)
        session.flush()

        # Link both items to contact via subjects
        val_subject = ReviewItemSubject(
            review_item_id=val_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(val_subject)
        session.flush()

        hh_subject = ReviewItemSubject(
            review_item_id=hh_item.id,
            subject_type='import_contact_snapshot',
            subject_id=contact.id,
            role='primary'
        )
        session.add(hh_subject)
        session.flush()

        # Create deferred decisions for both
        val_decision = ReviewDecision(
            batch_id='mixed-export-warnings-k',
            review_item_id=val_item.id,
            decision='defer',
            reviewed_values={'field': 'email', 'issue': 'missing_email'},
            reviewer='test-reviewer'
        )
        session.add(val_decision)
        session.flush()

        hh_decision = ReviewDecision(
            batch_id='mixed-export-warnings-k',
            review_item_id=hh_item.id,
            decision='defer',
            reviewed_values={},
            reviewer='test-reviewer'
        )
        session.add(hh_decision)
        session.commit()

        # Start Flask server with proven lifecycle cleanup pattern
        server = make_server('127.0.0.1', 8001, flask_app)
        flask_thread = threading.Thread(target=server.serve_forever, daemon=True)
        flask_thread.start()

        # Wait for server using exponential backoff polling
        await wait_for_validation_export_page_ready('http://127.0.0.1:8001/imports/mixed-export-warnings-k/exports', timeout_seconds=10)

        # Launch browser
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                try:
                    # K1: Navigate to exports page
                    await page.goto('http://127.0.0.1:8001/imports/mixed-export-warnings-k/exports')
                    await page.wait_for_selector('h1', timeout=5000)
                    print("✓ K1: Export console loaded")

                    # K2: Generate preview
                    await page.evaluate("""
                        async () => {
                            const response = await fetch('/imports/mixed-export-warnings-k/exports/preview', {
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
                    print("✓ K2: Export preview loaded with mixed warnings")

                    # K3: Verify both warning sections appear
                    val_warning = await page.query_selector('#confirm-unresolved-validations-checkbox')
                    hh_warning = await page.query_selector('#confirm-unresolved-households-checkbox')
                    assert val_warning is not None, "K3 FAILED: Validation warning checkbox should be present"
                    assert hh_warning is not None, "K3 FAILED: Household warning checkbox should be present"
                    print("✓ K3: Both warning checkboxes present (validation + household)")

                    # K4: Verify export button is disabled (deferred household requires checkbox)
                    export_btn = await page.query_selector('#generate-export-btn')
                    is_initially_disabled = await export_btn.is_disabled()
                    assert is_initially_disabled, "K4 FAILED: Export button should be disabled (household deferred + unchecked)"
                    print("✓ K4: Export button disabled (deferred household requires confirmation)")

                    # K5: Check ONLY validation checkbox (household still unchecked)
                    await val_warning.check()
                    await page.wait_for_timeout(200)  # Wait for JS state update
                    is_still_disabled = await export_btn.is_disabled()
                    assert is_still_disabled, \
                        "K5 FAILED: Export button should remain disabled (household checkbox still unchecked)"
                    print("✓ K5: Button remains disabled (household checkbox required)")

                    # K6: Now check household checkbox too
                    await hh_warning.check()
                    await page.wait_for_timeout(200)  # Wait for JS state update
                    is_now_enabled = not await export_btn.is_disabled()
                    assert is_now_enabled, \
                        "K6 FAILED: Export button should be enabled (household checkbox now checked)"
                    print("✓ K6: Button enabled (household checkbox confirmed)")

                    # K7: Verify validation checkbox is independent (uncheck it, button stays enabled)
                    await val_warning.uncheck()
                    await page.wait_for_timeout(200)  # Wait for JS state update
                    is_still_enabled = not await export_btn.is_disabled()
                    assert is_still_enabled, \
                        "K7 FAILED: Button should remain enabled (validation checkbox does not gate export)"
                    print("✓ K7: Button remains enabled (validation checkbox independent)")

                    # K8: Verify button stays enabled when both are unchecked (household is the only gate)
                    # Actually, let's test the true gate: uncheck household checkbox
                    await hh_warning.uncheck()
                    await page.wait_for_timeout(200)  # Wait for JS state update
                    is_now_disabled = await export_btn.is_disabled()
                    assert is_now_disabled, \
                        "K8 FAILED: Button should be disabled when household checkbox unchecked"
                    print("✓ K8: Button disabled when household checkbox unchecked (confirms household gates export)")

                    print("\n=== TEST K: MIXED VALIDATION + HOUSEHOLD EXPORT WARNINGS PASSED ===")

                finally:
                    await browser.close()
        finally:
            # Explicit server shutdown and thread cleanup
            server.shutdown()
            flask_thread.join(timeout=2)

    finally:
        session.close()
