"""Small independent UI/API/database/export consistency proof."""

from __future__ import annotations

import csv
import io

import pytest
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import RawImportRow, ReviewDecision, create_db_engine
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def test_three_state_oracles_agree_through_reload_and_export(e2e_database_and_app):
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    batch_id = "oracle-three-state"
    session = sessionmaker(bind=create_db_engine(database_url))()
    seeded = _seed_batch(
        session,
        batch_id=batch_id,
        rows=[
            {"name": "Oracle Clean", "email": "clean@example.com"},
            {"name": "Oracle Human", "email": "human@gmai.com", "issue": "Email typo", "severity": "warning"},
            {"name": "Oracle Unresolved", "email": "unresolved@", "issue": "Invalid email", "severity": "error"},
        ],
    )
    row_ids = [row[0].id for row in seeded]
    session.close()

    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 1000})
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                rows = page.locator("tr.validation-row")
                await rows.nth(2).wait_for()

                human = rows.nth(1)
                await human.locator(".row-status-dropdown").select_option("accept_as_is")
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                await modal.locator(".reviewer-name-field").fill("Oracle Reviewer")
                await modal.locator('textarea[id^="followup-notes-"]').fill("Oracle reason")
                await modal.locator('button[id^="save-followup-notes-"]').click()
                await modal.wait_for(state="hidden")

                # Oracle 1: rendered reviewer-visible state.
                assert await rows.nth(0).locator(".validation-status-label").inner_text() == "No issues"
                assert await rows.nth(0).locator(".row-status-dropdown").input_value() == "accept_as_is"
                assert await rows.nth(1).locator(".validation-status-label").inner_text() == "Warning"
                assert await human.locator(".row-status-dropdown").input_value() == "accept_as_is"
                assert "Oracle Reviewer" in await human.locator(".row-disposition-meta").inner_text()
                assert "Oracle reason" in await human.locator(".row-disposition-meta").inner_text()
                assert await rows.nth(2).locator(".validation-status-label").inner_text() == "Blocking"
                assert await rows.nth(2).locator(".row-status-dropdown").input_value() == ""

                # Oracle 2: independent API and database persistence state.
                api = await page.request.get(f"{base_url}/imports/{batch_id}/row-decision/{row_ids[1]}")
                assert api.ok
                api_state = await api.json()
                assert api_state["has_decision"] is True
                assert api_state["decision"] == "accept_as_is"
                assert api_state["reviewer"] == "Oracle Reviewer"
                assert api_state["notes"] == "Oracle reason"
                assert api_state["timestamp"]
                session = sessionmaker(bind=create_db_engine(database_url))()
                try:
                    clean_human_decisions = session.query(ReviewDecision).filter(
                        ReviewDecision.raw_import_row_id == row_ids[0],
                        ReviewDecision.decision.like("row_status:%"),
                    ).all()
                    assert clean_human_decisions == []
                    decision = session.query(ReviewDecision).filter(
                        ReviewDecision.raw_import_row_id == row_ids[1],
                        ReviewDecision.decision == "row_status:accept_as_is",
                    ).one()
                    assert decision.reviewer == "Oracle Reviewer"
                    assert decision.reviewed_values["notes"] == "Oracle reason"
                finally:
                    session.close()

                await page.goto(f"{base_url}/imports/{batch_id}/readiness")
                readiness = await page.locator("body").inner_text()
                assert "Export Blocked" in readiness
                assert "blocker(s) prevent export" in readiness

                # Successful correction and one fresh-render proof.
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                # The unresolved row is excluded from the independently observed
                # reviewer-visible eligible set before it is corrected.
                pre_resolution_eligible = set()
                for index in range(await rows.count()):
                    row = rows.nth(index)
                    transaction_id = (await row.locator("td").first.inner_text()).strip()
                    status = (await row.locator(".validation-status-label").inner_text()).strip()
                    disposition = await row.locator(".row-status-dropdown").input_value()
                    if not (status == "Blocking" and not disposition):
                        pre_resolution_eligible.add(transaction_id)
                assert "txn-oracle-three-state-3" not in pre_resolution_eligible

                unresolved = rows.nth(2).locator('input[data-field="email"]')
                await unresolved.fill("unresolved@example.com")
                await unresolved.press("Tab")
                await page.wait_for_function(
                    "() => document.querySelectorAll('tr.validation-row')[2]?.querySelector('.validation-status-label')?.textContent.trim() === 'No issues'"
                )
                await page.reload()
                rows = page.locator("tr.validation-row")
                assert await rows.nth(2).locator('input[data-field="email"]').input_value() == "unresolved@example.com"
                assert await rows.nth(2).locator(".validation-status-label").inner_text() == "No issues"
                assert await rows.nth(2).locator(".row-status-dropdown").input_value() == "accept_as_is"
                fresh_api = await page.request.get(f"{base_url}/imports/{batch_id}/row-decision/{row_ids[2]}")
                assert (await fresh_api.json())["has_decision"] is False

                # Oracle 3: actual generated export, compared to the visible
                # eligible set observed after the persisted correction.
                visible_export_ids = set()
                for index in range(await rows.count()):
                    row = rows.nth(index)
                    transaction_id = (await row.locator("td").first.inner_text()).strip()
                    status = (await row.locator(".validation-status-label").inner_text()).strip()
                    disposition = await row.locator(".row-status-dropdown").input_value()
                    if status == "Blocking" and not disposition:
                        continue
                    if disposition in {"needs_follow_up", "reject_row"}:
                        continue
                    visible_export_ids.add(transaction_id)

                async def accept_dialog(dialog):
                    await dialog.accept()

                page.once("dialog", accept_dialog)
                await page.locator("#approve-file-btn").click()
                await page.wait_for_timeout(250)
                await page.goto(f"{base_url}/imports/{batch_id}/exports")
                generated = await page.request.post(f"{base_url}/imports/{batch_id}/exports/generate")
                assert generated.ok
                audit_id = (await generated.json())["file"]["audit_log_id"]
                download = await page.request.get(
                    f"{base_url}/imports/{batch_id}/exports/download/{audit_id}"
                )
                assert download.ok
                exported_ids = {
                    row["transaction_id"]
                    for row in csv.DictReader(io.StringIO(await download.text()))
                }
                assert exported_ids == visible_export_ids

                session = sessionmaker(bind=create_db_engine(database_url))()
                try:
                    raw = session.query(RawImportRow).filter_by(id=row_ids[2]).one()
                    assert raw.raw_csv_data["email"] == "unresolved@"
                finally:
                    session.close()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
