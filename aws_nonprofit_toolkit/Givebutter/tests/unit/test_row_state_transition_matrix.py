"""Small production-path mutation matrix for reviewer-visible row state."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker
import re
import csv
import io

from scripts.householder.database_models import ReviewDecision, create_db_engine
from scripts.householder.row_decision_service import get_row_decision_state
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def _wait_saved(row):
    await row.locator(".autosave-status").filter(has_text="Saved").first.wait_for(
        state="visible", timeout=10000
    )


async def _row_snapshot(row):
    return {
        "fields": {
            await row.locator(".autosave-field").nth(index).get_attribute("data-field"):
            await row.locator(".autosave-field").nth(index).input_value()
            for index in range(await row.locator(".autosave-field").count())
        },
        "issues": (await row.locator(".issues-cell").inner_text()).strip(),
        "status": (await row.locator(".validation-status-label").inner_text()).strip(),
        "disposition": await row.locator(".row-status-dropdown").input_value(),
    }


async def _history_snapshot(page, row):
    await row.locator('[data-action="inspect-record"]').click()
    modal = page.locator("#record-modal")
    await modal.wait_for(state="visible")
    entries = modal.locator("section").filter(has_text="Review history").last.locator("article")
    values = [await entries.nth(i).inner_text() for i in range(await entries.count())]
    await modal.locator("#modal-record-footer button").first.click()
    return values


async def _complete_visible_projection(page, base_url, batch_id, row):
    """Capture only reviewer-visible state, including the current filters/history."""
    snapshot = await _row_snapshot(row)
    snapshot["history"] = await _history_snapshot(page, row)
    await page.goto(f"{base_url}/imports/{batch_id}/validation")
    await page.locator("tr.validation-row").first.wait_for()
    snapshot["filters"] = {"all": await _visible_ids(page)}
    for status in ("Blocking", "Warning", "No issues"):
        await page.locator('[data-row-status-filter="all"]').click()
        await page.locator(f'[data-row-status-filter="{status}"]').click()
        snapshot["filters"][status] = await _visible_ids(page)
    await page.locator('[data-row-status-filter="all"]').click()
    for disposition in ("none", "accept_as_is", "needs_follow_up", "reject_row"):
        await page.locator("#disposition-filter").select_option(disposition)
        snapshot["filters"][f"disposition:{disposition}"] = await _visible_ids(page)
    await page.locator("#disposition-filter").select_option("all")
    await page.goto(f"{base_url}/imports/{batch_id}/readiness")
    snapshot["readiness"] = (await page.locator("body").inner_text()).strip()
    await page.goto(f"{base_url}/imports/{batch_id}/exports")
    snapshot["export"] = (await page.locator('[data-testid="export-readiness-summary"]').inner_text()).strip()
    await page.goto(f"{base_url}/imports/{batch_id}/validation")
    await page.locator("tr.validation-row").first.wait_for()
    snapshot["filters_after_surfaces"] = await _visible_ids(page)
    return snapshot


async def _visible_ids(page):
    rows = page.locator("tr.validation-row")
    ids = set()
    for index in range(await rows.count()):
        row = rows.nth(index)
        if await row.is_visible():
            ids.add((await row.locator("td").first.inner_text()).strip())
    return ids


async def _assert_review_surfaces(page, base_url, batch_id, *, ready):
    """Use only reviewer-visible readiness/export surfaces, never row data attrs."""
    await page.goto(f"{base_url}/imports/{batch_id}/readiness")
    heading = page.locator("h2")
    await heading.wait_for()
    heading_text = await heading.inner_text()
    if ready is None:
        assert heading_text in {"⚠️ Export Blocked", "✓ Export Ready"}
    else:
        assert ("Export Ready" if ready else "Export Blocked") in heading_text, await page.locator("body").inner_text()
    if ready is True:
        assert "Ready to generate CSV export" in await page.locator("body").inner_text()
    elif ready is False:
        body = await page.locator("body").inner_text()
        assert "blocker(s) prevent export" in body
        assert "Blockers:" in body
    await page.goto(f"{base_url}/imports/{batch_id}/exports")
    strip = page.locator('[data-testid="export-readiness-summary"]')
    await strip.wait_for()
    strip_text = await strip.inner_text()
    if ready is None:
        assert "Export readiness" in strip_text
    elif ready:
        assert "Export Blocked" not in strip_text
        assert "generate a preview first" in strip_text or "Export Ready" in strip_text
    else:
        # Before a preview is generated the export console intentionally shows
        # its neutral "preview needed" state; readiness is the visible blocker
        # surface for this pre-preview assertion.
        assert "Export Ready" not in strip_text
    await page.goto(f"{base_url}/imports/{batch_id}/validation")
    await page.locator("tr.validation-row").first.wait_for()


async def _assert_visible_projection(page, base_url, batch_id, row, *, status, disposition, ready):
    assert await row.locator(".validation-status-label").inner_text() == status
    assert await row.locator(".row-status-dropdown").input_value() == disposition
    issues = (await row.locator(".issues-cell").inner_text()).strip()
    assert (issues == "None") is (status == "No issues")
    await _assert_review_surfaces(page, base_url, batch_id, ready=ready)

    await page.locator('[data-row-status-filter="all"]').click()
    await page.locator("#disposition-filter").select_option("all")


async def _edit(page, row, field, value):
    editor = row.locator(f'.autosave-field[data-field="{field}"]')
    await editor.fill(value)
    await editor.press("Tab")
    await _wait_saved(row)


async def _save_decision(page, row, decision, reason):
    await row.locator(".row-status-dropdown").select_option(decision)
    modal = page.locator("#record-modal")
    await modal.wait_for(state="visible", timeout=5000)
    await modal.locator(".reviewer-name-field").fill("Matrix Reviewer")
    await modal.locator('textarea[id^="followup-notes-"]').fill(reason)
    await modal.locator('button[id^="save-followup-notes-"]').click()
    await modal.wait_for(state="hidden", timeout=10000)


async def _reset_decision(page, row):
    await row.locator(".row-status-dropdown").select_option("")
    modal = page.locator("#record-modal")
    await modal.wait_for(state="visible", timeout=5000)
    await modal.locator(".reviewer-name-field").fill("Matrix Reviewer")
    await modal.locator('select[id^="row-review-decision-"]').select_option("")
    await modal.locator('button[id^="save-followup-notes-"]').click()
    await modal.wait_for(state="hidden", timeout=10000)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "Matrix Name"),
        ("email", "matrix@example.com"),
        ("phone", "+1 415 555 2671"),
        ("amount", "125.50"),
        ("address", "25 Matrix Street"),
        ("date", "2026-09-01"),
    ],
)
async def test_real_successful_reviewed_field_edit_projects_and_reloads(
    e2e_database_and_app, field, value
):
    """Each editable field uses the real autosave and fresh-render path."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = f"matrix-field-{field}"
    seeded = _seed_batch(
        session,
        batch_id=batch_id,
        rows=[{"name": "Matrix User", "email": "matrix-user@example.com"}],
    )
    raw_id = seeded[0][0].id
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
                row = page.locator(f"#validation-row-{raw_id}")
                await row.wait_for()
                await _edit(page, row, field, value)
                await _assert_visible_projection(
                    page, base_url, batch_id, row, status="No issues", disposition="accept_as_is", ready=True,
                )
                await page.reload()
                row = page.locator(f"#validation-row-{raw_id}")
                await row.wait_for()
                await _assert_visible_projection(
                    page, base_url, batch_id, row, status="No issues", disposition="accept_as_is", ready=True,
                )
                actual_value = await row.locator(f'.autosave-field[data-field="{field}"]').input_value()
                expected_values = {value, "$125.50" if field == "amount" else value}
                if field == "phone":
                    expected_values.add("+1 (415) 555-2671")
                assert actual_value in expected_values
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


async def test_real_failed_edit_and_review_lifecycle_are_durable(e2e_database_and_app):
    """Failed persistence, human transitions, reset, filters, and history use production paths."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = "matrix-lifecycle"
    seeded = _seed_batch(
        session,
        batch_id=batch_id,
        rows=[
            {"name": "Clean Matrix", "email": "clean-matrix@example.com"},
            {"name": "Issue Matrix", "email": "bad-email", "issue": "Invalid email", "severity": "error"},
            {"name": "Warning Matrix", "email": "warning-matrix@example.com", "issue": "Review warning", "severity": "warning"},
        ],
    )
    export_batch_id = "matrix-export"
    export_seeded = _seed_batch(
        session,
        batch_id=export_batch_id,
        rows=[
            {"name": "Export Clean", "email": "export-clean@example.com"},
            {"name": "Export Followup", "email": "export-followup@example.com"},
            {"name": "Export Reject", "email": "export-reject@example.com"},
        ],
    )
    export_followup_id = export_seeded[1][0].id
    export_reject_id = export_seeded[2][0].id
    issue_id = seeded[1][0].id
    warning_id = seeded[2][0].id
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
                issue = page.locator(f"#validation-row-{issue_id}")
                warning = page.locator(f"#validation-row-{warning_id}")
                await issue.wait_for()
                await warning.wait_for()

                before_failed = await _complete_visible_projection(page, base_url, batch_id, issue)
                editor = issue.locator('.autosave-field[data-field="email"]')
                await editor.fill("not-an-email")
                await editor.press("Tab")
                # Capture the attempted value before the failed response
                # restores the last persisted value.
                assert await editor.input_value() == "not-an-email"
                await issue.locator(".autosave-status").filter(has_text="Error").first.wait_for(
                    state="visible", timeout=10000
                )
                after_failed = await _complete_visible_projection(page, base_url, batch_id, issue)
                assert after_failed == before_failed
                await page.reload()
                issue = page.locator(f"#validation-row-{issue_id}")
                await issue.wait_for()
                assert await _complete_visible_projection(page, base_url, batch_id, issue) == before_failed

                # Full human lifecycle: save, change, reset, then reload.
                await _save_decision(page, issue, "needs_follow_up", "Follow up matrix")
                await _assert_visible_projection(
                    page, base_url, batch_id, issue, status="Blocking", disposition="needs_follow_up", ready=None
                )
                await _edit(page, issue, "name", "Issue Matrix Updated")
                await _assert_visible_projection(
                    page, base_url, batch_id, issue, status="Blocking", disposition="", ready=False
                )
                await _save_decision(page, issue, "reject_row", "Reject matrix")
                await _assert_visible_projection(
                    page, base_url, batch_id, issue, status="Blocking", disposition="reject_row", ready=None
                )
                # Reject row -> successful edit invalidates the current human
                # decision while retaining the prior review in history.
                await _edit(page, issue, "amount", "140.00")
                await _assert_visible_projection(
                    page, base_url, batch_id, issue, status="Blocking", disposition="", ready=False
                )
                await _save_decision(page, issue, "reject_row", "Reject matrix again")
                await _reset_decision(page, issue)
                await _assert_visible_projection(
                    page, base_url, batch_id, issue, status="Blocking", disposition="", ready=False
                )

                # Actual severity and disposition filters compose on rendered rows.
                await page.locator('[data-row-status-filter="all"]').click()
                all_ids = await _visible_ids(page)
                clean_id = (await page.locator("tr.validation-row").nth(0).locator("td").first.inner_text()).strip()
                issue_txn = (await issue.locator("td").first.inner_text()).strip()
                warning_txn = (await warning.locator("td").first.inner_text()).strip()
                assert all_ids == {clean_id, issue_txn, warning_txn}
                await page.locator('[data-row-status-filter="Blocking"]').click()
                assert await _visible_ids(page) == {issue_txn}
                await page.locator('[data-row-status-filter="all"]').click()
                await page.locator('[data-row-status-filter="Warning"]').click()
                assert await _visible_ids(page) == {warning_txn}
                await page.locator('[data-row-status-filter="Blocking"]').click()
                assert await _visible_ids(page) == {issue_txn, warning_txn}
                await page.locator('[data-row-status-filter="all"]').click()
                await page.locator('[data-row-status-filter="No issues"]').click()
                assert await _visible_ids(page) == {clean_id}
                assert all_ids - await _visible_ids(page) == {issue_txn, warning_txn}
                await page.locator('[data-row-status-filter="all"]').click()
                await page.locator("#disposition-filter").select_option("none")
                assert await _visible_ids(page) == {issue_txn, warning_txn}
                await page.locator("#disposition-filter").select_option("accept_as_is")
                assert await _visible_ids(page) == {clean_id}
                assert all_ids - await _visible_ids(page) == {issue_txn, warning_txn}
                await page.locator('[data-row-status-filter="all"]').click()
                await page.locator("#disposition-filter").select_option("needs_follow_up")
                assert await _visible_ids(page) == set()
                await page.locator("#disposition-filter").select_option("all")
                await _save_decision(page, warning, "needs_follow_up", "Warning follow-up")
                await page.locator("#disposition-filter").select_option("needs_follow_up")
                assert await _visible_ids(page) == {warning_txn}
                assert await _visible_ids(page) != {issue_txn}
                await _reset_decision(page, warning)
                await page.locator("#disposition-filter").select_option("all")

                # Full rendered history, newest first, survives a fresh request.
                await page.locator("#disposition-filter").select_option("all")
                await issue.locator('[data-action="inspect-record"]').click()
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                entries = modal.locator("section").filter(has_text="Review history").last.locator("article")
                history = [await entries.nth(i).inner_text() for i in range(await entries.count())]
                assert len(history) == 6
                assert "Decision cleared" in history[0]
                assert "Reject matrix" in history[1] or "Reject matrix again" in history[1]
                # The successful edit invalidates the prior human decision via
                # an append-only correction event; the original review remains
                # the oldest event.
                assert "Amount updated from" in history[2]
                assert "Current disposition:" in history[2]
                assert "Reject matrix" in history[3]
                assert "updated from" in history[4]
                assert "Follow up matrix" in history[5]
                assert all(re.search(r"\d{1,2}/\d{1,2}/20\d\d", entry) for entry in history)
                assert all(
                    ("Matrix Reviewer" in entry and "matrix" in entry.lower())
                    or "updated from" in entry
                    for entry in history
                )
                assert len(history) == len(set(history))
                assert "Reject matrix again" in history[1]
                assert "Reject matrix" in history[3]
                assert "Follow up matrix" in history[5]
                assert all(
                    "Matrix Reviewer" in entry
                    for entry in history
                    if "Decision cleared" not in entry and "updated from" not in entry
                )
                await modal.locator("#modal-record-footer button").first.click()
                await page.reload()
                issue = page.locator(f"#validation-row-{issue_id}")
                await issue.wait_for()
                await issue.locator('[data-action="inspect-record"]').click()
                entries = page.locator("#record-modal section").filter(has_text="Review history").last.locator("article")
                await entries.first.wait_for(state="visible")
                reloaded = [await entries.nth(i).inner_text() for i in range(await entries.count())]
                assert reloaded == history

                # Resolve the remaining blocking row through the normal reviewed
                # field path before exercising the real export endpoint.
                await modal.locator("#modal-record-footer button").first.click() if await modal.is_visible() else None
                await page.goto(f"{base_url}/imports/{export_batch_id}/validation")
                await page.locator("tr.validation-row").first.wait_for()
                export_followup = page.locator(f"#validation-row-{export_followup_id}")
                export_reject = page.locator(f"#validation-row-{export_reject_id}")
                await _save_decision(page, export_followup, "needs_follow_up", "Exclude follow-up")
                await _save_decision(page, export_reject, "reject_row", "Exclude reject")
                # Derive the expected export set from the currently rendered,
                # reviewer-visible rows and compare it with the real CSV output.
                visible_rows = page.locator("tr.validation-row")
                for index in range(await visible_rows.count()):
                    visible_row = visible_rows.nth(index)
                    assert await visible_row.is_visible()
                    if await visible_row.locator(".row-status-dropdown").input_value() in {"needs_follow_up", "reject_row"}:
                        continue
                    assert await visible_row.locator(".validation-status-label").inner_text() == "No issues"
                    assert await visible_row.locator(".row-status-dropdown").input_value() == "accept_as_is"
                visible_eligible = set()
                visible_ineligible = set()
                for index in range(await visible_rows.count()):
                    visible_row = visible_rows.nth(index)
                    name = (await visible_row.locator('.autosave-field[data-field="name"]').input_value()).strip()
                    if await visible_row.locator(".row-status-dropdown").input_value() in {"needs_follow_up", "reject_row"}:
                        visible_ineligible.add(name)
                    else:
                        visible_eligible.add(name)
                assert visible_eligible == {"Export Clean"}
                assert visible_ineligible == {"Export Followup", "Export Reject"}
                preview = await page.request.post(f"{base_url}/imports/{export_batch_id}/exports/preview")
                assert preview.ok
                generated = await page.request.post(
                    f"{base_url}/imports/{export_batch_id}/exports/generate",
                    form={
                        "confirmed_unresolved_households": "false",
                        "confirmed_unresolved_duplicates": "false",
                        "confirmed_unresolved_validations": "false",
                        "confirmed_unresolved_normalizations": "false",
                    },
                )
                assert generated.ok
                payload = await generated.json()
                assert payload["status"] == "success"
                audit_id = payload["file"]["audit_log_id"]
                download = await page.request.get(
                    f"{base_url}/imports/{export_batch_id}/exports/download/{audit_id}"
                )
                assert download.ok
                exported_rows = list(csv.DictReader(io.StringIO(await download.text())))
                exported_ids = {
                    f"{str(row.get('first_name', '')).strip()} {str(row.get('last_name', '')).strip()}".strip()
                    for row in exported_rows
                }
                assert exported_ids == visible_eligible
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)

    state = get_row_decision_state(batch_id, issue_id, database_url)
    assert state["has_decision"] is False
    assert [entry["decision"] for entry in state["history"]] == [
        "clear_decision", "reject_row", "clear_decision", "reject_row", "clear_decision", "needs_follow_up"
    ]
    session = sessionmaker(bind=create_db_engine(database_url))()
    try:
        human_records = session.query(ReviewDecision).filter(
            ReviewDecision.raw_import_row_id == issue_id,
            ReviewDecision.decision.like("row_status:%"),
        ).count()
        assert human_records == 6
    finally:
        session.close()
