"""
E2E smoke tests for canonical desktop app screens at 1440x900 viewport.

Desktop-only screens covered (existing routable canonical screens):
1. Imports/List (upload entry)
2. Dashboard (summary view)
3. Validation Review
4. Normalizations (placeholder route with no workflow implementation)
5. Duplicates
6. Households
7. Audit Log
8. Export Console

Note: Normalizations is a placeholder route with no workflow implementation.
Smoke test verifies route is accessible and renders without error (read-only coverage only).

Template bug fix: Households progress bar had ZeroDivisionError when total_households=0.
Fixed with conditional in Jinja2 template (line 145 of households.html).

Smoke test criteria:
- Page loads successfully (no timeout/exception)
- Body element renders
- Content is meaningful (> 500 bytes)
- No error markers (Traceback, 404, 500, etc.)
- Screen-specific text/controls present
- Read-only navigation only (no mutations, no export generation)
- Desktop viewport: 1440x900 (no mobile/tablet)
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
def e2e_database_and_app_smoke():
    """Create database and start Flask server for smoke tests."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    os.environ['HOUSEHOLDER_REPOSITORY'] = 'database'
    os.environ['GIVEBUTTER_DATABASE_URL'] = database_url

    app.config['TESTING'] = True

    yield database_url, db_path, app

    Path(db_path).unlink(missing_ok=True)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_desktop_canonical_screens_smoke(e2e_database_and_app_smoke):
    """
    Verify all 8 working canonical app screens render correctly and are navigable
    at 1440x900 desktop viewport. This is a smoke test for routing and basic
    rendering; it does not test functionality or responsive behavior.

    Screens tested:
    - Imports/List, Dashboard, Validation Review, Normalizations, Duplicates, Households, Audit Log, Export Console
    """
    from playwright.async_api import async_playwright

    database_url, db_path, flask_app = e2e_database_and_app_smoke

    engine = create_db_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Seed minimal test data
        batch = ImportBatch(
            id='smoke-test-batch',
            filename='smoke_test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        raw_row_1 = RawImportRow(
            batch_id='smoke-test-batch',
            row_index=1,
            raw_csv_data={
                'name': 'Donor One',
                'date': '2026-01-15',
                'email': 'donor1@example.com',
                'phone': '(555) 111-1111',
                'amount': '100.00',
                'address': '123 Main St'
            }
        )
        session.add(raw_row_1)
        session.flush()

        raw_row_2 = RawImportRow(
            batch_id='smoke-test-batch',
            row_index=2,
            raw_csv_data={
                'name': 'Donor Two',
                'date': '2026-01-16',
                'email': 'donor2@example.com',
                'phone': '(555) 222-2222',
                'amount': '250.00',
                'address': '456 Oak Ave'
            }
        )
        session.add(raw_row_2)
        session.flush()

        contact_1 = ImportContact(
            batch_id='smoke-test-batch',
            raw_import_row_id=raw_row_1.id,
            first_name='Donor',
            last_name='One',
            email='donor1@example.com',
            phone='(555) 111-1111',
            address_line1='123 Main St',
            amount=100.00
        )
        session.add(contact_1)

        contact_2 = ImportContact(
            batch_id='smoke-test-batch',
            raw_import_row_id=raw_row_2.id,
            first_name='Donor',
            last_name='Two',
            email='donor2@example.com',
            phone='(555) 222-2222',
            address_line1='456 Oak Ave',
            amount=250.00
        )
        session.add(contact_2)
        session.commit()

        # Start Flask server
        def run_flask():
            flask_app.run(host='127.0.0.1', port=8001, debug=False, use_reloader=False)

        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Wait for server
        import requests
        max_retries = 5
        for attempt in range(max_retries):
            try:
                requests.get('http://127.0.0.1:8001/imports', timeout=2)
                break
            except (requests.ConnectionError, requests.Timeout):
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    raise RuntimeError("Flask server failed to start")

        # Launch browser at 1440x900 desktop viewport
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={'width': 1440, 'height': 900})

            try:
                screens = [
                    ('Imports/List', 'http://127.0.0.1:8001/imports', ['import', 'upload']),
                    ('Dashboard', 'http://127.0.0.1:8001/imports/smoke-test-batch/dashboard', ['dashboard', 'batch']),
                    ('Validation Review', 'http://127.0.0.1:8001/imports/smoke-test-batch/validation', ['validation', 'review']),
                    ('Normalizations', 'http://127.0.0.1:8001/imports/smoke-test-batch/normalizations', ['normalizations']),
                    ('Duplicates', 'http://127.0.0.1:8001/imports/smoke-test-batch/duplicates', ['duplicate']),
                    ('Households', 'http://127.0.0.1:8001/imports/smoke-test-batch/households', ['household']),
                    ('Audit Log', 'http://127.0.0.1:8001/imports/smoke-test-batch/audit', ['audit']),
                    ('Export Console', 'http://127.0.0.1:8001/imports/smoke-test-batch/exports', ['export']),
                ]

                print("\n=== DESKTOP CANONICAL SCREENS SMOKE TEST ===")
                print("Viewport: 1440x900 (desktop only)")
                print("Coverage: 8 canonical screens (verified working)")
                print("(Normalizations: route exists, placeholder content, no workflow impl)\n")

                for i, (screen_name, url, expected_keywords) in enumerate(screens, 1):
                    # Navigate to screen - let exceptions fail the test
                    await page.goto(url, wait_until='load')

                    # Get page content for assertions
                    page_content = await page.content()
                    content_lower = page_content.lower()

                    # Assert 1: Body element exists
                    body = await page.query_selector('body')
                    assert body is not None, f"{screen_name}: body element should exist"

                    # Assert 2: Content is meaningful (> 500 bytes)
                    assert len(page_content) > 500, \
                        f"{screen_name}: page content should be > 500 bytes, got {len(page_content)}"

                    # Assert 3: No error markers
                    error_markers = ['traceback', 'internal server error', 'not found', '<title>404', '<h1>404', '<h1>500']
                    for marker in error_markers:
                        assert marker not in content_lower, \
                            f"{screen_name}: page should not contain error marker '{marker}'"

                    # Assert 4: Screen-specific keyword(s) present
                    has_keyword = any(kw.lower() in content_lower for kw in expected_keywords)
                    assert has_keyword, \
                        f"{screen_name}: page should contain one of {expected_keywords}"

                    print(f"✓ {i}. {screen_name} renders correctly")

                # Verify viewport
                viewport = await page.evaluate('() => ({ width: window.innerWidth, height: window.innerHeight })')
                assert viewport['width'] == 1440, f"Width should be 1440, got {viewport['width']}"
                assert viewport['height'] == 900, f"Height should be 900, got {viewport['height']}"

                print(f"\n✓ All 8 canonical screens verified at {viewport['width']}x{viewport['height']}")
                print("✓ Desktop viewport confirmed")
                print("✓ No destructive actions performed")
                print("✓ No export generation triggered")

            finally:
                await browser.close()

    finally:
        session.close()
