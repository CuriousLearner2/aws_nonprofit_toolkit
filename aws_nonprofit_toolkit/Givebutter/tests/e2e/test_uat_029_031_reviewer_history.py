"""Focused reviewer-facing contracts for disposition metadata and edit history."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e.test_validation_disposition_contract import _save_row_disposition, _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reviewer_metadata_and_edit_history_survive_reload(e2e_database_and_app):
    """The row control stays compact while Details exposes durable audit context."""
    from playwright.async_api import async_playwright
    from sqlalchemy.orm import sessionmaker
    from scripts.householder.database_models import create_db_engine

    database_url, _, flask_app = e2e_database_and_app
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    batch_id = "uat-029-031-reviewer-history"
    _seed_batch(session, batch_id=batch_id, rows=[
        {"name": "History Clean", "email": "history.clean@example.com"},
        {"name": "History Unresolved", "email": "", "issue": "Missing email address"},
    ])
    session.close()
    server = thread = None

    async def edit_and_assert_history(page, row, field, value, label, visible_value=None):
        row_index = await row.evaluate("element => Array.from(document.querySelectorAll('tr.validation-row')).indexOf(element)")
        field_input = row.locator(f'input[data-field="{field}"]')
        await field_input.fill(value)
        await field_input.evaluate("element => element.blur()")
        await page.wait_for_function(
            "([index, field, value]) => { const row = document.querySelectorAll('tr.validation-row')[index]; const input = row?.querySelector(`input[data-field=\"${field}\"]`); return input && input.value.includes(value); }",
            arg=[row_index, field, visible_value or value],
            timeout=5000,
        )
        await row.locator('a[data-action="inspect-record"]').click()
        modal = page.locator("#record-modal")
        await modal.wait_for(state="visible")
        history = modal.locator("#modal-record-content article")
        texts = await history.all_inner_texts()
        assert any(label in text and "Current disposition:" in text for text in texts)
        await modal.locator("button[id^='cancel-record-review-']").click()
        await modal.wait_for(state="hidden")

    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                rows = page.locator("tr.validation-row")
                await rows.first.wait_for()

                # System Accept and unresolved No disposition have no secondary row text.
                assert await rows.nth(0).locator(".row-status-dropdown").input_value() == "accept_as_is"
                assert await rows.nth(0).locator(".row-disposition-meta").inner_text() == ""
                assert await rows.nth(1).locator(".row-status-dropdown").input_value() in ("", "no_disposition")
                assert await rows.nth(1).locator(".row-disposition-meta").inner_text() == ""

                await _save_row_disposition(
                    page, 1, "accept_as_is", reviewer="UAT History Reviewer", notes="Keep the corrected value"
                )
                assert "UAT History Reviewer" in await rows.nth(1).locator(".row-disposition-meta").inner_text()
                assert "Keep the corrected value" not in await rows.nth(1).locator(".row-disposition-meta").inner_text()

                await edit_and_assert_history(page, rows.nth(1), "amount", "200", "Amount updated from")
                await _save_row_disposition(page, 1, "accept_as_is", reviewer="UAT History Reviewer 2", notes="Review phone")
                await edit_and_assert_history(page, rows.nth(1), "phone", "4155552672", "Phone updated from", "2672")
                await _save_row_disposition(page, 1, "accept_as_is", reviewer="UAT History Reviewer 3", notes="Review email")
                await edit_and_assert_history(page, rows.nth(1), "email", "history.updated@example.com", "Email updated from")

                await page.reload()
                row = page.locator("tr.validation-row").nth(1)
                await row.wait_for()
                assert await row.locator(".row-disposition-meta").inner_text() == ""
                await row.locator('a[data-action="inspect-record"]').click()
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                history_text = "\n".join(await modal.locator("#modal-record-content article").all_inner_texts())
                for expected in ("Amount updated from", "Phone updated from", "Email updated from", "UAT History Reviewer 3"):
                    assert expected in history_text
                assert "Decision cleared by reviewer" not in history_text
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
