"""P0 reviewer-visible disposition round-trip contracts."""

import os
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))

from scripts.householder.database_models import (  # noqa: E402
    ImportBatch,
    ImportContact,
    RawImportRow,
    ReviewDecision,
    Base,
    create_db_engine,
)
from scripts.householder.export_preview_service import build_export_preview  # noqa: E402
from test_validation_review_dom import (  # noqa: E402
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


REVIEWER = 'UAT Reviewer 74291'
REASON = 'UAT audit reason 74291'


def _seed_rows(database_url, batch_id, count=3):
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch = ImportBatch(
        id=batch_id,
        filename='reviewer_p0.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=count,
    )
    session.add(batch)
    session.flush()
    raw_ids = []
    for index in range(1, count + 1):
        raw = RawImportRow(
            batch_id=batch_id,
            row_index=index,
            raw_csv_data={
                'name': f'P0 Reviewer {index}',
                'date': '2026-08-01',
                'email': f'p0-{index}@example.com',
                'phone': '+1 415-555-0100',
                'amount': '100.00',
                'address': f'{index} Review Lane',
            },
        )
        session.add(raw)
        session.flush()
        raw_ids.append(raw.id)
        session.add(ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw.id,
            first_name='P0',
            last_name=f'Reviewer {index}',
            email=f'p0-{index}@example.com',
            phone='+1 415-555-0100',
            address_line1=f'{index} Review Lane',
            amount=100.0,
        ))
    session.commit()
    session.close()
    return engine, Session, raw_ids


async def _save_review(page, row, decision, notes=REASON):
    await row.locator('a[data-action="inspect-record"]').click()
    modal = page.locator('#record-modal')
    await modal.wait_for(state='visible')
    await modal.locator('.reviewer-name-field').fill(REVIEWER)
    await modal.locator('select[id^="row-review-decision-"]').select_option(decision)
    notes_field = modal.locator('textarea[id^="followup-notes-"]')
    await notes_field.fill(notes)
    await modal.locator('button[id^="save-record-review-"]').click()
    await modal.wait_for(state='hidden')


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize('decision,expected_exported', [
    ('accept_as_is', True),
    ('needs_follow_up', False),
    ('reject_row', False),
])
async def test_human_disposition_browser_round_trip_and_export(
    e2e_database_and_app, decision, expected_exported,
):
    """Save each human disposition and verify UI, API, DB, history, and export."""
    from playwright.async_api import async_playwright

    database_url, _db_path, flask_app = e2e_database_and_app
    batch_id = f'reviewer-p0-{decision}'
    engine, Session, raw_ids = _seed_rows(database_url, batch_id)
    server = flask_thread = None
    try:
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            try:
                await page.goto(f'{base_url}/imports/{batch_id}/validation')
                rows = page.locator('tr.validation-row')
                row = rows.nth(0)
                await row.wait_for()
                await _save_review(page, row, decision)

                dropdown = row.locator('select.row-status-dropdown')
                assert await dropdown.input_value() == decision
                assert REVIEWER in await row.locator('.row-disposition-meta').inner_text()

                api = await page.request.get(f'{base_url}/imports/{batch_id}/row-decision/{raw_ids[0]}')
                state = await api.json()
                assert state['has_decision'] is True
                assert state['decision'] == decision
                assert state['reviewer'] == REVIEWER
                assert state['notes'] == REASON
                assert state['timestamp']

                session = Session()
                persisted = session.query(ReviewDecision).filter(
                    ReviewDecision.raw_import_row_id == raw_ids[0],
                    ReviewDecision.decision == f'row_status:{decision}',
                ).one()
                assert persisted.reviewer == REVIEWER
                assert persisted.reviewed_values['notes'] == REASON
                session.close()

                await row.locator('a[data-action="inspect-record"]').click()
                await page.locator('#record-modal').wait_for(state='visible')
                modal_text = await page.locator('#modal-record-content').inner_text()
                assert REVIEWER in modal_text
                assert REASON in modal_text
                assert state['timestamp'] in modal_text
                await page.locator('#record-modal button:has-text("Cancel")').click()

                await page.reload()
                row = page.locator('tr.validation-row').nth(0)
                await page.wait_for_function(
                    "([decision, reviewer]) => { const row = document.querySelector('tr.validation-row'); const dropdown = row?.querySelector('select.row-status-dropdown'); const meta = row?.querySelector('.row-disposition-meta'); return dropdown?.value === decision && (meta?.innerText || '').includes(reviewer); }",
                    arg=[decision, REVIEWER],
                )
                assert await row.locator('select.row-status-dropdown').input_value() == decision
                assert REVIEWER in await row.locator('.row-disposition-meta').inner_text()
                await row.locator('a[data-action="inspect-record"]').click()
                await page.locator('#record-modal').wait_for(state='visible')
                reloaded_text = await page.locator('#modal-record-content').inner_text()
                assert REVIEWER in reloaded_text and REASON in reloaded_text

                preview = build_export_preview(
                    batch_id, {'GIVEBUTTER_DATABASE_URL': database_url}
                )
                exported_ids = {item.source_row_index for item in preview.export_rows}
                assert (1 in exported_ids) is expected_exported
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_clear_human_disposition_preserves_history_and_projection(e2e_database_and_app):
    """Clear returns to system projection while retaining append-only history."""
    from playwright.async_api import async_playwright

    database_url, _db_path, flask_app = e2e_database_and_app
    batch_id = 'reviewer-p0-clear'
    engine, Session, raw_ids = _seed_rows(database_url, batch_id, count=1)
    server = flask_thread = None
    try:
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            try:
                await page.goto(f'{base_url}/imports/{batch_id}/validation')
                row = page.locator('tr.validation-row').first
                await _save_review(page, row, 'reject_row')
                before = await page.request.get(f'{base_url}/imports/{batch_id}/row-decision/{raw_ids[0]}')
                before_state = await before.json()
                async def accept_dialog(dialog):
                    await dialog.accept()
                page.once('dialog', accept_dialog)
                await row.locator('select.row-status-dropdown').select_option('')
                modal = page.locator('#record-modal')
                await modal.wait_for(state='visible')
                await modal.locator('.reviewer-name-field').fill(REVIEWER)
                await modal.locator('button[id^="save-followup-notes-"]').click()
                await modal.wait_for(state='hidden')
                await page.wait_for_function(
                    "() => document.querySelector('.row-status-dropdown')?.dataset.hasDecision === 'false'"
                )
                assert await page.locator('.row-disposition-meta').inner_text() == ''
                after = await page.request.get(f'{base_url}/imports/{batch_id}/row-decision/{raw_ids[0]}')
                after_state = await after.json()
                assert after_state['has_decision'] is False
                assert any(entry['decision'] == 'reject_row' for entry in after_state['history'])
                assert before_state['timestamp']
                preview = build_export_preview(batch_id, {'GIVEBUTTER_DATABASE_URL': database_url})
                assert any(item.source_row_index == 1 for item in preview.export_rows)
                session = Session()
                assert session.query(ReviewDecision).filter_by(raw_import_row_id=raw_ids[0]).count() == 2
                session.close()
                await page.reload()
                await page.wait_for_function(
                    "() => ['', 'no_disposition', 'accept_as_is'].includes(document.querySelector('.row-status-dropdown')?.value) && document.querySelector('.row-disposition-meta')?.innerText.trim() === ''"
                )
                assert await page.locator('.row-disposition-meta').inner_text() == ''
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_failed_review_save_preserves_previous_state_and_human_projection(e2e_database_and_app):
    """A failed save cannot create a visible or durable new disposition."""
    from playwright.async_api import async_playwright

    database_url, _db_path, flask_app = e2e_database_and_app
    batch_id = 'reviewer-p0-failed-save'
    engine, Session, raw_ids = _seed_rows(database_url, batch_id, count=1)
    server = flask_thread = None
    try:
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            page = await browser.new_page()
            try:
                await page.goto(f'{base_url}/imports/{batch_id}/validation')
                row = page.locator('tr.validation-row').first
                await _save_review(page, row, 'accept_as_is')
                baseline = await page.request.get(f'{base_url}/imports/{batch_id}/row-decision/{raw_ids[0]}')
                baseline_state = await baseline.json()
                session = Session()
                baseline_count = session.query(ReviewDecision).filter_by(raw_import_row_id=raw_ids[0]).count()
                session.close()

                await page.route(
                    f'**/imports/{batch_id}/row-decision',
                    lambda route: route.fulfill(status=400, content_type='application/json', body='{"error":"forced failure"}'),
                )
                await row.locator('a[data-action="inspect-record"]').click()
                modal = page.locator('#record-modal')
                await modal.locator('.reviewer-name-field').fill('UAT Reviewer Failed')
                await modal.locator('select[id^="row-review-decision-"]').select_option('reject_row')
                await modal.locator('textarea[id^="followup-notes-"]').fill('Should not persist')
                await modal.locator('button[id^="save-record-review-"]').click()
                await page.wait_for_timeout(100)
                assert await modal.is_visible()
                assert REVIEWER in await row.locator('.row-disposition-meta').inner_text()
                current = await page.request.get(f'{base_url}/imports/{batch_id}/row-decision/{raw_ids[0]}')
                assert await current.json() == baseline_state
                session = Session()
                assert session.query(ReviewDecision).filter_by(raw_import_row_id=raw_ids[0]).count() == baseline_count
                session.close()
                await page.reload()
                await page.wait_for_function(
                    "(reviewer) => document.querySelector('.row-disposition-meta')?.innerText.includes(reviewer)",
                    arg=REVIEWER,
                )
                assert REVIEWER in await page.locator('.row-disposition-meta').inner_text()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
