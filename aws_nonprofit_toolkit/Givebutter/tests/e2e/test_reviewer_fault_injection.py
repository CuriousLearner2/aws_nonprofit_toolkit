"""Minimal deterministic fault-injection coverage for reviewer state."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.orm import sessionmaker

from scripts.householder import autosave_service, export_file_service
import householder.autosave_service as runtime_autosave_service
from scripts.householder.database_models import AuditLogRecord, ReviewDecision, create_db_engine
from tests.e2e.test_reviewer_transition_fuzz import _complete_visible_projection
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def test_autosave_faults_preserve_latest_and_durable_projection(e2e_database_and_app, monkeypatch):
    """Delayed responses, reload during save, duplicate review, and failure stay coherent."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    batch_id = "fault-injection-reviewer"
    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        seeded = _seed_batch(
            session,
            batch_id=batch_id,
            rows=[
                {"name": "Fault Clean", "email": "clean@example.com"},
                {
                    "name": "Fault Warning",
                    "email": "warning@gmai.com",
                    "issue": "Email typo",
                    "severity": "warning",
                },
            ],
        )
        clean_id, warning_id = [item[0].id for item in seeded]
    finally:
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
                clean = page.locator(f"#validation-row-{clean_id}")
                warning = page.locator(f"#validation-row-{warning_id}")
                await clean.wait_for()
                older_response_arrived = asyncio.Event()

                async def delayed_autosave(route):
                    response = await route.fetch()
                    payload = route.request.post_data_json
                    submitted = next(iter(payload.get("corrected_values", {}).values()), "")
                    if submitted == "Older clean value":
                        await asyncio.sleep(0.35)
                    try:
                        await route.fulfill(response=response)
                    except Exception:
                        # The browser may abort an older request when the
                        # newer edit supersedes it.
                        return
                    if submitted == "Older clean value":
                        older_response_arrived.set()

                await page.route("**/autosave", delayed_autosave)
                name = clean.locator('.autosave-field[data-field="name"]')
                await name.fill("Older clean value")
                await name.press("Tab")
                await name.fill("Newest clean value")
                await name.press("Tab")
                await page.wait_for_function(
                    "() => document.querySelector('#validation-row-%s input[data-field=\\\"name\\\"]')?.value === 'Newest clean value'"
                    % clean_id
                )
                await asyncio.wait_for(older_response_arrived.wait(), timeout=5)
                assert await name.input_value() == "Newest clean value"
                after_out_of_order = await _complete_visible_projection(page, base_url, batch_id, clean)
                assert after_out_of_order["fields"]["name"] == "Newest clean value"
                before_reload = await _complete_visible_projection(page, base_url, batch_id, clean)
                await page.unroute("**/autosave", delayed_autosave)
                await page.reload()
                await page.locator(f"#validation-row-{clean_id}").wait_for()
                after_reload = await _complete_visible_projection(
                    page, base_url, batch_id, page.locator(f"#validation-row-{clean_id}")
                )
                assert after_reload["fields"]["name"] == "Newest clean value"
                assert after_reload == before_reload

                # Persistence failure: the attempted value is rejected and no
                # projected/readiness/export state changes.
                before_failure = await _complete_visible_projection(
                    page, base_url, batch_id, page.locator(f"#validation-row-{clean_id}")
                )

                def fail_autosave(*args, **kwargs):
                    raise ValueError("injected persistence failure")

                monkeypatch.setattr(autosave_service, "autosave_row_corrections", fail_autosave)
                monkeypatch.setattr(runtime_autosave_service, "autosave_row_corrections", fail_autosave)
                failed = await page.request.post(
                    f"{base_url}/imports/{batch_id}/autosave",
                    data={"raw_import_row_id": clean_id, "corrected_values": {"name": "Rejected value"}},
                )
                assert not failed.ok
                after_failure = await _complete_visible_projection(
                    page, base_url, batch_id, page.locator(f"#validation-row-{clean_id}")
                )
                assert after_failure == before_failure
                monkeypatch.undo()

                # Duplicate review submission is idempotent at the production
                # endpoint and creates one durable human event.
                review_payload = {
                    "raw_import_row_id": warning_id,
                    "decision": "needs_follow_up",
                    "notes": "Retry-safe reviewer note",
                    "reviewer_name": "Fault Reviewer",
                    "interaction_sequence": 1,
                }
                first = await page.request.post(
                    f"{base_url}/imports/{batch_id}/row-decision", data=review_payload
                )
                second = await page.request.post(
                    f"{base_url}/imports/{batch_id}/row-decision", data=review_payload
                )
                assert first.ok and second.ok
                assert (await second.json())["idempotent"] is True
                session = sessionmaker(bind=create_db_engine(database_url))()
                try:
                    decisions = session.query(ReviewDecision).filter(
                        ReviewDecision.raw_import_row_id == warning_id,
                        ReviewDecision.decision == "row_status:needs_follow_up",
                    ).all()
                    assert len(decisions) == 1
                finally:
                    session.close()

                # Reload during a delayed review response still restores the
                # durable decision from a fresh request.
                async def delayed_review(route):
                    response = await route.fetch()
                    await asyncio.sleep(0.25)
                    await route.fulfill(response=response)

                await page.route("**/row-decision", delayed_review)
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                warning = page.locator(f"#validation-row-{warning_id}")
                await warning.locator(".row-status-dropdown").select_option("reject_row")
                modal = page.locator("#record-modal")
                await modal.locator(".reviewer-name-field").fill("Fault Reviewer 2")
                await modal.locator('textarea[id^="followup-notes-"]').fill("Reload during save")
                await modal.locator('button[id^="save-followup-notes-"]').click()
                await page.reload()
                await page.locator(f"#validation-row-{warning_id}").wait_for()
                await page.unroute("**/row-decision", delayed_review)
                state = await page.request.get(
                    f"{base_url}/imports/{batch_id}/row-decision/{warning_id}"
                )
                assert (await state.json())["decision"] == "reject_row"

                # Export failure must not create an export audit record or alter
                # the visible readiness/export state.
                await page.goto(f"{base_url}/imports/{batch_id}/readiness")
                readiness_before = await page.locator("body").inner_text()
                monkeypatch.setattr(
                    export_file_service,
                    "generate_export_file",
                    lambda *args, **kwargs: (_ for _ in ()).throw(
                        export_file_service.ExportError("injected export failure")
                    ),
                )
                failed_export = await page.request.post(
                    f"{base_url}/imports/{batch_id}/exports/generate"
                )
                assert failed_export.status == 500
                await page.reload()
                assert await page.locator("body").inner_text() == readiness_before
                session = sessionmaker(bind=create_db_engine(database_url))()
                try:
                    assert session.query(AuditLogRecord).filter_by(
                        batch_id=batch_id, action_type="export_generated"
                    ).count() == 0
                finally:
                    session.close()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
