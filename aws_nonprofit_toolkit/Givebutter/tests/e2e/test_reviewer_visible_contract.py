"""Focused reviewer-visible P0/P1 contract coverage.

These tests intentionally assert what a reviewer can read, select, and act on
in the validation, readiness, and export screens.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import (
    ImportBatch,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


def _attach_issue(session, *, batch_id, contact_id, field, description, severity="warning"):
    item = ReviewItem(
        batch_id=batch_id,
        item_type="validation",
        status="pending",
        payload_json={
            "field": field,
            "reason": "missing",
            "description": description,
            "severity": severity,
            "issue": f"missing_{field}",
        },
    )
    session.add(item)
    session.flush()
    session.add(ReviewItemSubject(
        review_item_id=item.id,
        subject_type="import_contact_snapshot",
        subject_id=contact_id,
        role="primary",
    ))


def _batch(session, batch_id, rows):
    seeded = _seed_batch(session, batch_id=batch_id, rows=rows)
    return seeded


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reviewer_sees_source_warnings_and_placeholder_is_not_data(e2e_database_and_app):
    """Phone/address warnings and empty-field guidance are visible to reviewers."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    batch_id = "reviewer-visible-source-warnings"
    seeded = _batch(session, batch_id, [
        {"name": "Phone Donor", "email": "phone@example.com"},
        {"name": "Address Donor", "email": "address@example.com"},
    ])
    phone_raw, phone_contact = seeded[0]
    address_raw, address_contact = seeded[1]
    phone_contact.phone = None
    phone_raw.raw_csv_data = {**phone_raw.raw_csv_data, "phone": ""}
    address_contact.address_line1 = None
    address_raw.raw_csv_data = {**address_raw.raw_csv_data, "address": "", "Address 1": ""}
    session.commit()
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
                rows = page.locator("tr.validation-row")
                assert await rows.count() == 2
                text = await page.locator(".issues-cell").all_inner_texts()
                assert any("phone" in value.lower() for value in text), text
                assert any("address" in value.lower() for value in text), text
                assert await page.locator("#search-records").get_attribute("placeholder")
                empty_email = page.locator('input[data-field="email"]').nth(0)
                assert await empty_email.input_value() == "phone@example.com"
                assert await empty_email.get_attribute("placeholder") == "email@example.com"
                assert "email@example.com" not in await rows.nth(0).inner_text()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reviewer_search_and_issue_filter_have_visible_accessible_scope(e2e_database_and_app):
    """Search and issue filters communicate their purpose and hide non-matches."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    batch_id = "reviewer-visible-filters"
    seeded = _batch(session, batch_id, [
        {"name": "Smith Donor", "email": "smith@example.com"},
        {"name": "Jones Donor", "email": "jones@example.com", "issue": "Invalid email"},
    ])
    session.commit()
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
                search = page.locator("#search-records")
                issue_filter = page.locator("#issue-filter")
                assert await page.get_by_label("Search records").count() == 1
                assert await page.get_by_label("Filter by issue").count() == 1
                await search.fill("smith")
                await page.wait_for_timeout(200)
                visible_count = await page.locator("tr.validation-row:not([hidden])").count()
                assert visible_count == 1, await page.evaluate("""() => ({
                    visible: Array.from(document.querySelectorAll('tr.validation-row:not([hidden])')).map(row => row.innerText),
                    values: Array.from(document.querySelectorAll('tr.validation-row')).map(row => Array.from(row.querySelectorAll('input, textarea, select')).map(field => field.value || field.textContent)),
                    search: document.querySelector('#search-records')?.value,
                    source: document.documentElement.innerHTML.includes('matchesSearch'),
                })""")
                visible_values = await page.locator("tr.validation-row:not([hidden]) input").evaluate_all(
                    "fields => fields.map(field => field.value)"
                )
                assert any("Smith" in value for value in visible_values)
                assert not any("Jones" in value for value in visible_values)
                await search.fill("")
                await issue_filter.select_option("format-invalid")
                assert await page.locator("tr.validation-row:not([hidden])").count() == 1
                assert "Invalid email" in await page.locator("tr.validation-row:not([hidden])").inner_text()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reviewer_sees_disposition_validation_and_no_fake_save(e2e_database_and_app):
    """Visible disposition errors explain required notes/identity and do not save."""
    from playwright.async_api import async_playwright
    from scripts.householder.database_models import ReviewDecision

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "reviewer-visible-dispositions"
    [(raw_row, contact)] = _batch(session, batch_id, [
        {"name": "Issue Donor", "email": "invalid-email", "issue": "Invalid email"},
    ])
    session.commit()
    raw_row_id = raw_row.id
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
                row = page.locator("tr.validation-row").first
                assert await row.locator(".validation-status-label").inner_text() == "Blocking"
                assert await row.locator(".row-status-dropdown").input_value() in ("", "no_disposition")
                dropdown = row.locator(".row-status-dropdown")
                await dropdown.select_option("needs_follow_up")
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                await modal.locator('button[id^="save-followup-notes-"]').click()
                assert await modal.is_visible()
                assert "required" in (await modal.inner_text()).lower()
                await dropdown.select_option("accept_as_is")
                await modal.locator('button[id^="save-followup-notes-"]').click()
                assert await modal.is_visible()
                assert "reviewer" in (await modal.inner_text()).lower()
                check = Session()
                try:
                    assert check.query(ReviewDecision).filter_by(
                        batch_id=batch_id, raw_import_row_id=raw_row_id,
                    ).count() == 0
                finally:
                    check.close()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reviewer_sees_correction_update_and_reload_preserve_state(e2e_database_and_app):
    """A visible correction updates status/disposition and survives reload."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    batch_id = "reviewer-visible-correction"
    _batch(session, batch_id, [{"name": "Correct Me", "email": "invalid-email", "issue": "Invalid email"}])
    session.commit()
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
                row = page.locator("tr.validation-row").first
                email = row.locator('input[data-field="email"]')
                await email.fill("correct@example.com")
                await email.blur()
                await page.wait_for_function(
                    "() => document.querySelector('tr.validation-row .validation-status-label')?.textContent.trim() === 'No issues'"
                )
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"
                await page.reload()
                row = page.locator("tr.validation-row").first
                assert await row.locator(".validation-status-label").inner_text() == "No issues"
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reviewer_sees_blockers_and_export_eligible_rows(e2e_database_and_app):
    """Readiness names blockers and export preview counts only eligible rows."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    Session = sessionmaker(bind=create_db_engine(database_url))
    session = Session()
    batch_id = "reviewer-visible-readiness-export"
    _batch(session, batch_id, [
        {"name": "Eligible Donor", "email": "eligible@example.com"},
        {"name": "Blocked Donor", "email": "invalid-email", "issue": "Invalid email"},
    ])
    session.commit()
    session.close()

    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/readiness")
                assert "Export Blocked" in await page.locator("body").inner_text()
                assert "blocker" in (await page.locator("body").inner_text()).lower()
                await page.goto(f"{base_url}/imports/{batch_id}/exports")
                await page.evaluate(
                    """async (url) => {
                        const response = await fetch(url, {method: 'POST'});
                        if (!response.ok) throw new Error('preview failed');
                        document.open();
                        document.write(await response.text());
                        document.close();
                    }""",
                    f"/imports/{batch_id}/exports/preview",
                )
                await page.wait_for_selector('[data-testid="export-readiness-summary"]')
                summary = page.locator('[data-testid="export-readiness-summary"]')
                assert await summary.get_attribute("data-readiness-state") == "blocked"
                assert await page.locator('[data-testid="export-summary-exported"]').inner_text() == "2"
                assert await page.locator('[data-testid="export-summary-exported"]').inner_text() != "0"
                assert "Export Blocked" in await page.locator("body").inner_text()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
