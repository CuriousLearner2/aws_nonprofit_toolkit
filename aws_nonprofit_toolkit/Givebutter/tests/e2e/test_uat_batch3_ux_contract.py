"""Focused UAT Batch 3 user-visible UX contracts."""

from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import create_db_engine  # noqa: E402
from scripts.householder.row_decision_service import record_row_decision  # noqa: E402
from tests.e2e.test_validation_disposition_contract import _seed_batch  # noqa: E402
from tests.e2e.test_validation_review_dom import (  # noqa: E402
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_success_and_failure_feedback_are_distinct(e2e_database_and_app, tmp_path):
    from playwright.async_api import async_playwright

    _, _, flask_app = e2e_database_and_app
    csv_path = tmp_path / "uat-batch-3.csv"
    csv_path.write_text("Name,Email\nUAT User,uat@example.com\n", encoding="utf-8")
    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(base_url)
                outcome = {"ok": True}

                async def upload_route(route):
                    if outcome["ok"]:
                        await route.fulfill(json={"status": "processed", "filename": "uat-batch-3.csv", "batch_id": "BATCH-UAT-3"})
                    else:
                        await route.fulfill(status=400, json={"title": "Upload failed", "message": "No data was imported."})

                await page.route("**/upload", upload_route)
                await page.locator("#fileInput").set_input_files(str(csv_path))
                status = page.locator("#uploadStatus")
                await page.wait_for_function(
                    "() => document.querySelector('#uploadStatus')?.textContent.includes('uploaded successfully')"
                )
                assert "uat-batch-3.csv uploaded successfully" in await status.inner_text()
                assert "BATCH-UAT-3" in await status.inner_text()

                outcome["ok"] = False
                await page.locator("#fileInput").set_input_files(str(csv_path))
                await page.wait_for_function("() => document.querySelector('#uploadStatus')?.textContent.includes('Upload failed')")
                assert "Upload complete" not in await status.inner_text()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_help_modal_and_filters_are_compact_and_composable(e2e_database_and_app):
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = "uat-batch-3-validation-ux"
    seeded = _seed_batch(session, batch_id=batch_id, rows=[
        {"name": "Clean Search", "email": "clean-ux@example.com"},
        {"name": "Warning Search", "email": "warn@gmai.com", "issue": "Email typo", "severity": "warning"},
        {"name": "Blocking Search", "email": "bad-email", "issue": "Invalid email", "severity": "error"},
    ])
    decision_row_id = seeded[0][0].id
    session.close()
    record_row_decision(
        batch_id,
        decision_row_id,
        "needs_follow_up",
        notes="Search composition check",
        interaction_sequence=1,
        reviewer_name="UAT Search Reviewer",
        database_url=database_url,
    )
    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1024, "height": 768})
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                assert await page.locator("#validation-status-filter").count() == 0
                assert await page.locator("[data-row-status-filter]").count() == 4
                search = page.locator("#search-records")
                assert (await search.bounding_box())["width"] >= 400
                search_help = (await search.get_attribute("aria-label")) + " " + (await search.get_attribute("placeholder"))
                for field in ("Name", "Email", "Phone", "Amount", "Address", "Date", "Transaction ID"):
                    assert field.lower() in search_help.lower()
                for term in ("Clean Search", "clean-ux@example.com", "415", "txn-uat-batch-3-validation-ux-1"):
                    await search.fill(term)
                    assert await page.locator("tr.validation-row:not([hidden])").count() >= 1, term
                await search.fill("")
                await page.locator("[data-testid='validation-status-filter-blocking']").click()
                assert await page.locator("tr.validation-row:not([hidden])").count() == 1
                await search.fill("Blocking Search")
                assert await page.locator("tr.validation-row:not([hidden])").count() == 1
                await page.locator("[data-testid='validation-status-filter-all']").click()
                await search.fill("")
                await page.locator("#disposition-filter").select_option("needs_follow_up")
                assert await page.locator("tr.validation-row:not([hidden])").count() == 1
                await page.locator("[data-testid='validation-status-filter-no-issues']").click()
                assert await page.locator("tr.validation-row:not([hidden])").count() == 1
                await search.fill("Clean Search")
                assert await page.locator("tr.validation-row:not([hidden])").count() == 1
                assert await page.locator("[data-testid='validation-scope-banner']").evaluate(
                    "element => element.scrollWidth <= element.clientWidth"
                )
                await page.locator("a[data-action='inspect-record']").first.click()
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                assert await modal.locator(".reviewer-name-field").get_attribute("aria-required") == "true"
                assert await modal.locator("textarea[id^='followup-notes-']").get_attribute("aria-required") == "true"
                assert "Reason / notes *" in await modal.inner_text()
                await modal.locator("select[id^='row-review-decision-']").select_option("needs_follow_up")
                assert await modal.locator("textarea[id^='followup-notes-']").get_attribute("aria-required") == "true"
                assert await modal.locator(".notes-required-marker").is_visible()
                assert "audit history" in await modal.inner_text()
                assert (await modal.locator(".modal-content").bounding_box())["width"] <= 640
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ambiguous_phone_warning_uses_compact_reviewer_copy(e2e_database_and_app):
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = "uat-batch-3-phone-copy"
    _seed_batch(session, batch_id=batch_id, rows=[
        {
            "name": "Phone Warning",
            "email": "phone-copy@example.com",
            "issue": "Could not verify format",
            "field": "phone",
            "severity": "warning",
        },
    ])
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
                assert "phone — Could not verify format" in await page.locator(".issues-cell").inner_text()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
