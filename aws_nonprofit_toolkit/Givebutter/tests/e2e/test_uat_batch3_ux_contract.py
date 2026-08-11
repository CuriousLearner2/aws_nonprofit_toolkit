"""Focused UAT Batch 3 user-visible UX contracts."""

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
                await status.wait_for(state="visible")
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
    _seed_batch(session, batch_id=batch_id, rows=[
        {"name": "UAT Reviewer", "email": "uat@example.com"},
    ])
    session.close()
    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1024, "height": 768})
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                assert await page.locator("#issue-filter option[value='length-exceeded']").count() == 0
                assert await page.locator("[data-testid='validation-scope-banner']").evaluate(
                    "element => element.scrollWidth <= element.clientWidth"
                )
                await page.locator("a[data-action='inspect-record']").click()
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                assert await modal.locator(".reviewer-name-field").get_attribute("aria-required") == "true"
                assert await modal.locator("textarea[id^='followup-notes-']").get_attribute("aria-required") == "false"
                assert "(optional)" in await modal.inner_text()
                await modal.locator("select[id^='row-review-decision-']").select_option("needs_follow_up")
                assert await modal.locator("textarea[id^='followup-notes-']").get_attribute("aria-required") == "true"
                assert await modal.locator(".notes-required-marker").is_visible()
                assert "audit history" in await modal.inner_text()
                assert (await modal.locator(".modal-content").bounding_box())["width"] <= 640
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
