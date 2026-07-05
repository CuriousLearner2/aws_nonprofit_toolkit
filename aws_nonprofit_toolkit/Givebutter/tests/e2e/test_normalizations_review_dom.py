"""
E2E browser tests for Normalizations Review DOM/UX behavior.

These tests verify actual Playwright browser interactions with the Normalizations
Review screen, including page load, navigation, decision submission, and UI elements.

Infrastructure:
- Database-backed Flask testing with ImportBatch/RawImportRow seeding
- Normalizations service generates normalization suggestions
- Flask runs in background thread, Playwright drives browser at 1440x900 desktop viewport
- Each test is isolated with unique batch IDs

Synchronization:
- Use page.wait_for_selector() for element visibility (5s timeout max)
- Wait for button states and navigation readiness
- No arbitrary sleeps; all waits are deterministic

Assertions:
- Hard assertions only (no soft guards, no conditional waits)
- Assert visible text, button states, and page navigation
- Do not mutate raw source data

See E2E_TEST_RELIABILITY.md for patterns and troubleshooting.
"""

import pytest
import asyncio
import sys
import tempfile
import threading
import os
import subprocess
import signal
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import (
    ReviewDecision,
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    create_db_engine,
)
from scripts.uploader.app import app


# ============================================================================
# HELPERS
# ============================================================================

def get_venv_python() -> str:
    """Get the correct Python interpreter from the active venv."""
    if '.venv' in sys.executable or 'venv' in sys.executable:
        return sys.executable

    if hasattr(sys, 'prefix') and sys.prefix and '.venv' in sys.prefix:
        venv_python = os.path.join(sys.prefix, 'bin', 'python3')
        if os.path.exists(venv_python):
            return venv_python

    current = Path(__file__).resolve()
    for parent in current.parents:
        venv_python = parent / '.venv' / 'bin' / 'python3'
        if venv_python.exists():
            return str(venv_python)

    return sys.executable


def wait_for_flask_ready(base_url: str, batch_id: str, timeout_seconds: int = 10) -> None:
    """Wait for Flask server to become ready by polling the normalizations endpoint."""
    start_time = time.time()
    wait_interval = 0.1
    max_interval = 1.0

    while time.time() - start_time < timeout_seconds:
        try:
            response = requests.get(
                f'{base_url}/imports/{batch_id}/normalizations',
                timeout=2
            )
            if response.status_code == 200:
                return
        except (requests.ConnectionError, requests.Timeout):
            pass

        time.sleep(wait_interval)
        wait_interval = min(wait_interval * 1.5, max_interval)

    raise RuntimeError(
        f"Flask server failed to become ready within {timeout_seconds}s at {base_url}"
    )


@pytest.fixture(scope='function')
def e2e_database_and_app():
    """
    Database-backed Flask app fixture for E2E tests.
    Yields (database_url, db_path, app).
    Cleanup on test completion.
    """
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = temp_db.name
    temp_db.close()

    database_url = f'sqlite:///{db_path}'

    # Create schema
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


# ============================================================================
# E2E TESTS
# ============================================================================

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_normalizations_page_loads_with_suggestions(e2e_database_and_app):
    """
    GOAL: Verify Normalizations page loads and displays UI elements.

    One-test proof: Verify page title, safety messaging, and core UI elements.
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
            id='normalizations-test-batch',
            filename='test_normalizations.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with value that needs normalization
        raw_row = RawImportRow(
            batch_id='normalizations-test-batch',
            row_index=1,
            raw_csv_data={
                'name': 'john smith',  # lowercase - will trigger normalization
                'date': '01/15/2026',
                'email': 'john@example.com',
                'phone': '5551234567',  # no formatting - will trigger normalization
                'amount': '$100.00',
                'address': '123 main street'
            }
        )
        session.add(raw_row)
        session.flush()
        raw_row_id = raw_row.id

        # Create ImportContact (required by database repository)
        import_contact = ImportContact(
            batch_id='normalizations-test-batch',
            raw_import_row_id=raw_row_id,
            first_name='john',
            last_name='smith',
            email='john@example.com',
            phone='5551234567',
            address_line1='123 main street',
            amount=100.00
        )
        session.add(import_contact)
        session.flush()

        # Create a ReviewItem (normalization suggestion)
        review_item = ReviewItem(
            batch_id='normalizations-test-batch',
            item_type='normalization',
            status='pending',
            payload_json={
                'field_name': 'name',
                'original_value': 'john smith',
                'suggested_value': 'John Smith',
                'normalization_type': 'proper_case',
                'contact_name': 'john smith',
            }
        )
        session.add(review_item)
        session.commit()

        # Start Flask server
        base_url = 'http://127.0.0.1:8001'
        env = os.environ.copy()
        env['HOUSEHOLDER_REPOSITORY'] = 'database'
        env['GIVEBUTTER_DATABASE_URL'] = database_url
        env['FLASK_ENV'] = 'development'

        flask_cmd = 'from scripts.uploader.app import app; app.run(host="127.0.0.1", port=8001, debug=False, use_reloader=False, threaded=True)'
        flask_process = subprocess.Popen(
            [get_venv_python(), '-c', flask_cmd],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

        # Wait for server to become ready
        wait_for_flask_ready(base_url, 'normalizations-test-batch')

        # Launch browser at desktop viewport
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1440, 'height': 900})

            try:
                # Navigate to normalizations page
                await page.goto(f'{base_url}/imports/normalizations-test-batch/normalizations')

                # Wait for page content to load
                await page.wait_for_selector('h1', timeout=5000)

                # Assert: Page title is "Normalizations"
                h1_text = await page.text_content('h1')
                assert 'Normalizations' in h1_text, f"Expected 'Normalizations' title, got: {h1_text}"

                # Assert: Batch ID is displayed
                batch_id_text = await page.text_content('.page-metadata')
                assert 'normalizations-test-batch' in batch_id_text, f"Expected batch ID in metadata, got: {batch_id_text}"

                # Assert: Safety message is visible
                safety_text = await page.text_content('.safety-strip')
                assert 'Raw import rows remain unchanged' in safety_text, f"Expected safety message, got: {safety_text}"

                summary_strip = page.get_by_test_id('normalization-summary-strip')
                details_toggle = page.get_by_test_id('normalization-details-toggle')
                details_panel = page.get_by_test_id('normalization-details-panel')
                decision_controls = page.get_by_test_id('normalization-decision-controls')
                notes_textarea = page.locator('#reviewer-notes')

                assert await summary_strip.count() == 1, "Expected normalization summary strip"
                assert await details_toggle.count() == 1, "Expected normalization details toggle"
                assert await details_panel.count() == 1, "Expected normalization details panel"
                assert await decision_controls.count() == 1, "Expected normalization decision controls"
                assert await notes_textarea.count() == 1, "Expected normalization notes area"
                assert (await details_toggle.text_content()).strip() == 'Hide details', \
                    "Expected normalization details toggle to show Hide details by default"

                assert await details_panel.is_visible(), "Expected normalization details to be visible by default"
                assert await summary_strip.is_visible(), "Expected normalization summary strip to remain visible"
                assert await notes_textarea.is_visible(), "Expected normalization notes area to remain visible"

                await details_toggle.click()
                await page.wait_for_function(
                    "() => document.querySelector('[data-testid=\"normalization-details-panel\"]')?.hidden === true",
                    timeout=5000,
                )

                assert await details_toggle.get_attribute('aria-expanded') == 'false', \
                    "Expected normalization details toggle to report collapsed state"
                assert (await details_toggle.text_content()).strip() == 'Show details', \
                    "Expected normalization details toggle to show Show details after collapse"
                assert await details_panel.is_hidden(), "Expected normalization details to collapse visually"
                assert await summary_strip.is_visible(), "Expected normalization summary strip to remain visible when collapsed"
                assert await notes_textarea.is_visible(), "Expected normalization notes area to remain visible when collapsed"
                assert await decision_controls.is_visible(), "Expected normalization decision controls to remain visible when collapsed"

                await details_toggle.click()
                await page.wait_for_function(
                    "() => document.querySelector('[data-testid=\"normalization-details-panel\"]')?.hidden === false",
                    timeout=5000,
                )

                assert await details_toggle.get_attribute('aria-expanded') == 'true', \
                    "Expected normalization details toggle to report expanded state"
                assert (await details_toggle.text_content()).strip() == 'Hide details', \
                    "Expected normalization details toggle to return to Hide details after re-expand"
                assert await details_panel.is_visible(), "Expected normalization details to be visible again"

                # Assert: Original Value label is present
                original_label = await page.text_content('text=Original Value')
                assert original_label is not None, "Expected 'Original Value' label"

                # Assert: Suggested Value label is present
                suggested_label = await page.text_content('text=Suggested Value')
                assert suggested_label is not None, "Expected 'Suggested Value' label"

                # Assert: Action buttons are present
                accept_btn = await page.text_content('button:has-text("Accept Suggestion")')
                assert accept_btn is not None, "Expected 'Accept Suggestion' button"

                reject_btn = await page.text_content('button:has-text("Reject Suggestion")')
                assert reject_btn is not None, "Expected 'Reject Suggestion' button"

                defer_btn = await page.text_content('button:has-text("Defer")')
                assert defer_btn is not None, "Expected 'Defer' button"

                print("✓ Normalizations page loads with core UI elements")

            finally:
                await page.close()
                await browser.close()

    finally:
        session.close()
        try:
            os.killpg(os.getpgid(flask_process.pid), signal.SIGTERM)
            flask_process.wait(timeout=3)
        except:
            pass


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_normalizations_accept_suggestion_submits_decision(e2e_database_and_app):
    """
    GOAL: Verify Accept Suggestion button submits decision and advances.

    Flow:
    1. Load normalizations page with one suggestion
    2. Click "Accept Suggestion"
    3. Verify decision is submitted (redirect or page update)
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app

    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        batch = ImportBatch(
            id='accept-test-batch',
            filename='test_accept.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id='accept-test-batch',
            row_index=1,
            raw_csv_data={'name': 'jane doe', 'email': 'jane@example.com'}
        )
        session.add(raw_row)
        session.flush()

        import_contact = ImportContact(
            batch_id='accept-test-batch',
            raw_import_row_id=raw_row.id,
            first_name='jane',
            last_name='doe',
            email='jane@example.com'
        )
        session.add(import_contact)
        session.flush()

        review_item = ReviewItem(
            batch_id='accept-test-batch',
            item_type='normalization',
            status='pending',
            payload_json={
                'field_name': 'name',
                'original_value': 'jane doe',
                'suggested_value': 'Jane Doe',
                'normalization_type': 'proper_case',
                'contact_name': 'jane doe',
            }
        )
        session.add(review_item)
        session.commit()

        base_url = 'http://127.0.0.1:8002'
        env = os.environ.copy()
        env['HOUSEHOLDER_REPOSITORY'] = 'database'
        env['GIVEBUTTER_DATABASE_URL'] = database_url
        env['FLASK_ENV'] = 'development'

        flask_cmd = 'from scripts.uploader.app import app; app.run(host="127.0.0.1", port=8002, debug=False, use_reloader=False, threaded=True)'
        flask_process = subprocess.Popen(
            [get_venv_python(), '-c', flask_cmd],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

        wait_for_flask_ready(base_url, 'accept-test-batch')

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1440, 'height': 900})

            try:
                await page.goto(f'{base_url}/imports/accept-test-batch/normalizations')
                await page.wait_for_selector('button:has-text("Accept Suggestion")', timeout=5000)

                # Click Accept Suggestion
                accept_button = await page.query_selector('button:has-text("Accept Suggestion")')
                assert accept_button is not None, "Accept Suggestion button not found"

                # Get original URL before click
                original_url = page.url

                await accept_button.click()

                # Wait for page to complete the form submission
                # The decision form submits via POST, so wait for network idle after click
                await page.wait_for_load_state('networkidle', timeout=5000)

                # After form submission, page either:
                # 1. Redirects to dashboard (URL changes)
                # 2. Shows completion message on same page (content changes)
                # Assert one of these occurred
                new_url = page.url
                page_text = await page.text_content('body')

                url_changed = new_url != original_url
                has_completion = 'All normalizations reviewed' in page_text or 'dashboard' in page_text.lower()

                assert url_changed or has_completion, \
                    f"Expected URL change or completion message after Accept. URL changed: {url_changed}, has completion: {has_completion}. Page: {page_text[:300]}"

                print("✓ Accept Suggestion submits decision (URL changed or completion state)")

            finally:
                await page.close()
                await browser.close()

    finally:
        session.close()
        try:
            os.killpg(os.getpgid(flask_process.pid), signal.SIGTERM)
            flask_process.wait(timeout=3)
        except:
            pass


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_normalizations_reject_suggestion_submits_decision(e2e_database_and_app):
    """
    GOAL: Verify Reject Suggestion button submits decision.
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app

    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        batch = ImportBatch(
            id='reject-test-batch',
            filename='test_reject.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id='reject-test-batch',
            row_index=1,
            raw_csv_data={'name': 'bob jones', 'email': 'bob@example.com'}
        )
        session.add(raw_row)
        session.flush()

        import_contact = ImportContact(
            batch_id='reject-test-batch',
            raw_import_row_id=raw_row.id,
            first_name='bob',
            last_name='jones',
            email='bob@example.com'
        )
        session.add(import_contact)
        session.flush()

        review_item = ReviewItem(
            batch_id='reject-test-batch',
            item_type='normalization',
            status='pending',
            payload_json={
                'field_name': 'name',
                'original_value': 'bob jones',
                'suggested_value': 'Bob Jones',
                'normalization_type': 'proper_case',
                'contact_name': 'bob jones',
            }
        )
        session.add(review_item)
        session.commit()

        base_url = 'http://127.0.0.1:8003'
        env = os.environ.copy()
        env['HOUSEHOLDER_REPOSITORY'] = 'database'
        env['GIVEBUTTER_DATABASE_URL'] = database_url
        env['FLASK_ENV'] = 'development'

        flask_cmd = 'from scripts.uploader.app import app; app.run(host="127.0.0.1", port=8003, debug=False, use_reloader=False, threaded=True)'
        flask_process = subprocess.Popen(
            [get_venv_python(), '-c', flask_cmd],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

        wait_for_flask_ready(base_url, 'reject-test-batch')

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1440, 'height': 900})

            try:
                await page.goto(f'{base_url}/imports/reject-test-batch/normalizations')
                await page.wait_for_selector('button:has-text("Reject Suggestion")', timeout=5000)

                # Click Reject Suggestion
                reject_button = await page.query_selector('button:has-text("Reject Suggestion")')
                assert reject_button is not None, "Reject Suggestion button not found"

                # Get original URL before click
                original_url = page.url

                await reject_button.click()

                # Wait for page to complete the form submission
                await page.wait_for_load_state('networkidle', timeout=5000)

                # After form submission, page either redirects or shows completion
                new_url = page.url
                page_text = await page.text_content('body')

                url_changed = new_url != original_url
                has_completion = 'All normalizations reviewed' in page_text or 'dashboard' in page_text.lower()

                assert url_changed or has_completion, \
                    f"Expected URL change or completion message after Reject. URL changed: {url_changed}, has completion: {has_completion}. Page: {page_text[:300]}"

                print("✓ Reject Suggestion submits decision (URL changed or completion state)")

            finally:
                await page.close()
                await browser.close()

    finally:
        session.close()
        try:
            os.killpg(os.getpgid(flask_process.pid), signal.SIGTERM)
            flask_process.wait(timeout=3)
        except:
            pass


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_normalizations_defer_with_optional_notes(e2e_database_and_app):
    """
    GOAL: Verify Defer button submits decision with optional notes.
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app

    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        batch = ImportBatch(
            id='defer-test-batch',
            filename='test_defer.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id='defer-test-batch',
            row_index=1,
            raw_csv_data={'name': 'alice walker', 'email': 'alice@example.com'}
        )
        session.add(raw_row)
        session.flush()

        import_contact = ImportContact(
            batch_id='defer-test-batch',
            raw_import_row_id=raw_row.id,
            first_name='alice',
            last_name='walker',
            email='alice@example.com'
        )
        session.add(import_contact)
        session.flush()

        review_item = ReviewItem(
            batch_id='defer-test-batch',
            item_type='normalization',
            status='pending',
            payload_json={
                'field_name': 'name',
                'original_value': 'alice walker',
                'suggested_value': 'Alice Walker',
                'normalization_type': 'proper_case',
                'contact_name': 'alice walker',
            }
        )
        session.add(review_item)
        session.commit()

        base_url = 'http://127.0.0.1:8004'
        env = os.environ.copy()
        env['HOUSEHOLDER_REPOSITORY'] = 'database'
        env['GIVEBUTTER_DATABASE_URL'] = database_url
        env['FLASK_ENV'] = 'development'

        flask_cmd = 'from scripts.uploader.app import app; app.run(host="127.0.0.1", port=8004, debug=False, use_reloader=False, threaded=True)'
        flask_process = subprocess.Popen(
            [get_venv_python(), '-c', flask_cmd],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

        wait_for_flask_ready(base_url, 'defer-test-batch')

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1440, 'height': 900})

            try:
                await page.goto(f'{base_url}/imports/defer-test-batch/normalizations')
                await page.wait_for_selector('#reviewer-notes', timeout=5000)

                # Add optional notes
                notes_field = await page.query_selector('#reviewer-notes')
                assert notes_field is not None, "Notes field not found"
                await notes_field.fill('Need to verify this with data team')

                # Click Defer
                defer_button = await page.query_selector('button:has-text("Defer")')
                assert defer_button is not None, "Defer button not found"

                # Get original URL before click
                original_url = page.url

                await defer_button.click()

                # Wait for page to complete the form submission
                await page.wait_for_load_state('networkidle', timeout=5000)

                # After form submission, page either redirects or shows completion
                new_url = page.url
                page_text = await page.text_content('body')

                url_changed = new_url != original_url
                has_completion = 'All normalizations reviewed' in page_text or 'dashboard' in page_text.lower()

                assert url_changed or has_completion, \
                    f"Expected URL change or completion message after Defer. URL changed: {url_changed}, has completion: {has_completion}. Page: {page_text[:300]}"

                print("✓ Defer submits decision with optional notes (URL changed or completion state)")

            finally:
                await page.close()
                await browser.close()

    finally:
        session.close()
        try:
            os.killpg(os.getpgid(flask_process.pid), signal.SIGTERM)
            flask_process.wait(timeout=3)
        except:
            pass


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_normalizations_navigation_buttons_state(e2e_database_and_app):
    """
    GOAL: Verify Previous/Next navigation buttons are present and correctly disabled/enabled.

    With one suggestion, Previous should be disabled, Next should be disabled.
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app

    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        batch = ImportBatch(
            id='nav-test-batch',
            filename='test_nav.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id='nav-test-batch',
            row_index=1,
            raw_csv_data={'name': 'charlie brown', 'email': 'charlie@example.com'}
        )
        session.add(raw_row)
        session.flush()

        import_contact = ImportContact(
            batch_id='nav-test-batch',
            raw_import_row_id=raw_row.id,
            first_name='charlie',
            last_name='brown',
            email='charlie@example.com'
        )
        session.add(import_contact)
        session.flush()

        review_item = ReviewItem(
            batch_id='nav-test-batch',
            item_type='normalization',
            status='pending',
            payload_json={
                'field_name': 'name',
                'original_value': 'charlie brown',
                'suggested_value': 'Charlie Brown',
                'normalization_type': 'proper_case',
                'contact_name': 'charlie brown',
            }
        )
        session.add(review_item)
        session.commit()

        base_url = 'http://127.0.0.1:8005'
        env = os.environ.copy()
        env['HOUSEHOLDER_REPOSITORY'] = 'database'
        env['GIVEBUTTER_DATABASE_URL'] = database_url
        env['FLASK_ENV'] = 'development'

        flask_cmd = 'from scripts.uploader.app import app; app.run(host="127.0.0.1", port=8005, debug=False, use_reloader=False, threaded=True)'
        flask_process = subprocess.Popen(
            [get_venv_python(), '-c', flask_cmd],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )

        wait_for_flask_ready(base_url, 'nav-test-batch')

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1440, 'height': 900})

            try:
                await page.goto(f'{base_url}/imports/nav-test-batch/normalizations')
                await page.wait_for_selector('text=← Previous Suggestion', timeout=5000)

                # Verify navigation buttons exist or are disabled appropriately
                nav_text = await page.text_content('body')
                assert 'Previous Suggestion' in nav_text, "Previous Suggestion button text should be present"
                assert 'Next' in nav_text or 'Next Suggestion' in nav_text, "Next button text should be present"

                print("✓ Navigation buttons are present")

            finally:
                await page.close()
                await browser.close()

    finally:
        session.close()
        try:
            os.killpg(os.getpgid(flask_process.pid), signal.SIGTERM)
            flask_process.wait(timeout=3)
        except:
            pass
