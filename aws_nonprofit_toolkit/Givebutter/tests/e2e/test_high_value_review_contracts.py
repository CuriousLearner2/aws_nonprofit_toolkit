"""Focused browser contracts for the remaining reviewer workflow gaps."""

from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import ReviewDecision, create_db_engine
from scripts.householder.row_decision_service import record_row_decision
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


async def _save(page, row_index, decision, reviewer, reason):
    row = page.locator("tr.validation-row").nth(row_index)
    await row.locator("select.row-status-dropdown").select_option(decision)
    modal = page.locator("#record-modal")
    await modal.wait_for(state="visible")
    await modal.locator(".reviewer-name-field").fill(reviewer)
    await modal.locator('textarea[id^="followup-notes-"]').fill(reason)
    await modal.locator('button[id^="save-followup-notes-"]').click()
    await modal.wait_for(state="hidden")
    await page.wait_for_function(
        "([index, value]) => document.querySelectorAll('select.row-status-dropdown')[index]?.value === value",
        arg=[row_index, decision],
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_history_sequence_is_complete_after_fresh_session(e2e_database_and_app):
    """Every browser-saved transition remains newest-first after navigation/reload."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    batch_id = "high-value-history-sequence"
    [(raw, _)] = _seed_batch(
        session,
        batch_id=batch_id,
        rows=[{"name": "History Donor", "email": "bad-email", "issue": "Invalid email"}],
    )
    raw_id = raw.id
    session.close()
    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                transitions = [
                    ("accept_as_is", "History Reviewer 1", "Accept reason"),
                    ("needs_follow_up", "History Reviewer 2", "Follow-up reason"),
                    ("reject_row", "History Reviewer 3", "Reject reason"),
                    ("", "History Reviewer 4", "Reset reason"),
                ]
                for decision, reviewer, reason in transitions:
                    await _save(page, 0, decision, reviewer, reason)

                state = await (await page.request.get(
                    f"{base_url}/imports/{batch_id}/row-decision/{raw_id}"
                )).json()
                assert state["has_decision"] is False
                assert [entry["decision"] for entry in state["history"][:3]] == [
                    "clear_decision", "reject_row", "needs_follow_up"
                ]
                assert [entry["reviewer"] for entry in state["history"][:4]] == [
                    "History Reviewer 4", "History Reviewer 3",
                    "History Reviewer 2", "History Reviewer 1",
                ]
                assert [entry["notes"] for entry in state["history"][:4]] == [
                    None, "Reject reason", "Follow-up reason", "Accept reason"
                ]

                await page.goto(f"{base_url}/imports/{batch_id}/dashboard")
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                fresh = await (await page.request.get(
                    f"{base_url}/imports/{batch_id}/row-decision/{raw_id}"
                )).json()
                assert fresh["history"] == state["history"]
                assert await page.locator(".row-status-dropdown").input_value() == ""
                assert await page.locator(".row-disposition-meta").inner_text() == "Decision cleared by reviewer"
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cross_import_search_browser_contract_preserves_source_and_filters(
    e2e_database_and_app,
):
    """The browser search index identifies the source row and composes disposition filtering."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    seeded_a = _seed_batch(
        session,
        batch_id="high-value-search-a",
        rows=[{"name": "Cross Import Smith", "email": "smith-a@example.com"}],
    )
    seeded_b = _seed_batch(
        session,
        batch_id="high-value-search-b",
        rows=[{"name": "Cross Import Smith", "email": "smith-b@example.com"}],
    )
    session.commit()
    row_b_id = seeded_b[0][0].id
    session.close()
    record_row_decision(
        "high-value-search-b", row_b_id, "needs_follow_up",
        notes="Search follow-up", reviewer_name="Search Reviewer",
        interaction_sequence=1, database_url=database_url,
    )
    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, "high-value-search-a")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/search?q=Cross+Import+Smith")
                results = page.locator('table tbody tr[data-testid^="global-search-result-"]')
                assert await results.count() == 2
                assert all("Cross Import Smith" in text for text in await results.all_inner_texts())
                source_row = page.locator('tr[data-testid^="global-search-result-high-value-search-b-"]')
                assert await source_row.count() == 1
                source_link = source_row.locator('a:has-text("Open original row")')
                assert "/imports/high-value-search-b/validation#validation-row-" in await source_link.get_attribute("href")

                await page.goto(
                    f"{base_url}/search?q=Cross+Import+Smith&disposition=needs_follow_up"
                )
                filtered = page.locator('table tbody tr[data-testid^="global-search-result-"]')
                assert await filtered.count() == 1
                assert "high-value-search-b" in await filtered.first.inner_text()
                assert "Needs follow-up" in await filtered.first.inner_text()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
