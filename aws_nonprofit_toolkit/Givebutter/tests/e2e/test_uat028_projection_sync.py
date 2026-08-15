"""Focused UAT-028 post-edit projection synchronization contract."""

from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import create_db_engine  # noqa: E402
from tests.e2e.test_validation_disposition_contract import _seed_batch  # noqa: E402
from tests.e2e.test_validation_review_dom import (  # noqa: E402
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_uat028_blank_amount_updates_issue_status_before_reload(e2e_database_and_app):
    """A rejected blank amount edit must immediately show canonical Blocking."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = 'uat028-projection-sync'
    seeded = _seed_batch(session, batch_id=batch_id, rows=[
        {'name': 'Amount Sync', 'email': 'amount-sync@example.com'},
    ])
    record_id = seeded[0][1].id
    session.close()

    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1280, 'height': 900})
            try:
                await page.goto(f'{base_url}/imports/{batch_id}/validation')
                row = page.locator(f'#validation-row-{record_id}')
                amount = row.locator('input[data-field="amount"]')
                await amount.fill('')
                await amount.blur()

                await page.wait_for_function(
                    """() => {
                        const row = document.querySelector('tr.validation-row');
                        return row?.querySelector('.validation-status-label')?.textContent.trim() === 'Blocking'
                            && row?.getAttribute('data-row-status') === 'Blocking'
                            && row?.querySelector('.issues-cell')?.textContent.includes('amount');
                    }"""
                )
                assert await row.locator('.validation-status-label').inner_text() == 'Blocking'
                assert await row.get_attribute('data-row-status') == 'Blocking'
                assert await row.get_attribute('data-approval-blocked') == 'true'
                assert await row.get_attribute('data-export-eligible') == 'false'
                assert await row.locator('.row-status-dropdown').input_value() == ''
                await page.locator('[data-testid="validation-status-filter-blocking"]').click()
                assert await page.locator('tr.validation-row:not([hidden])').count() == 1
                await page.locator('#disposition-filter').select_option('none')
                assert await page.locator('tr.validation-row:not([hidden])').count() == 1

                await page.reload()
                await page.wait_for_selector(f'#validation-row-{record_id}')
                assert await row.locator('.validation-status-label').inner_text() == 'No issues'
                assert await amount.input_value() == '$100.00'
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_successful_reviewed_field_edits_refresh_shared_projection(e2e_database_and_app):
    """All editable reviewed fields refresh status, disposition, and gating together."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = 'uat028-all-fields'
    seeded = _seed_batch(session, batch_id=batch_id, rows=[
        {'name': 'Projection User', 'email': 'projection@example.com'},
    ])
    record_id = seeded[0][1].id
    session.close()

    edits = (
        ('name', 'Updated Projection User', 'Updated Projection User'),
        ('email', 'updated-projection@example.com', 'updated-projection@example.com'),
        ('phone', '(415) 555-2671', '+1 (415) 555-2671'),
        ('amount', '125.50', '$125.50'),
        ('address', '456 Projection St', '456 Projection St'),
        ('date', '2026-09-01', '2026-09-01'),
    )
    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': 1280, 'height': 900})
            try:
                await page.goto(f'{base_url}/imports/{batch_id}/validation')
                row = page.locator(f'#validation-row-{record_id}')
                for field, value, persisted_expected in edits:
                    input_locator = row.locator(f'input[data-field="{field}"]')
                    await input_locator.fill(value)
                    await input_locator.blur()
                    await page.wait_for_function(
                        """() => {
                            const row = document.querySelector('tr.validation-row');
                            return row?.getAttribute('data-row-status') === 'No issues'
                                && row?.getAttribute('data-export-eligible') === 'true'
                                && row?.getAttribute('data-approval-blocked') === 'false';
                        }"""
                    )
                    assert await row.locator('.issues-cell').inner_text() == 'None'
                    assert await row.locator('.validation-status-label').inner_text() == 'No issues'
                    assert await row.locator('.row-status-dropdown').input_value() == 'accept_as_is'
                    assert await row.get_attribute('data-disposition') == 'accept_as_is'
                    immediate_expected = value if field != 'amount' else '$125.50'
                    assert await input_locator.input_value() == immediate_expected

                await page.reload()
                await page.wait_for_selector(f'#validation-row-{record_id}')
                for field, _, persisted_expected in edits:
                    assert await row.locator(f'input[data-field="{field}"]').input_value() == persisted_expected
                assert await row.locator('.validation-status-label').inner_text() == 'No issues'
                assert await row.locator('.row-status-dropdown').input_value() == 'accept_as_is'
                assert await row.get_attribute('data-row-status') == 'No issues'
                await page.locator('[data-testid="validation-status-filter-no-issues"]').click()
                await page.locator('#disposition-filter').select_option('accept_as_is')
                assert await page.locator('tr.validation-row:not([hidden])').count() == 1
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
