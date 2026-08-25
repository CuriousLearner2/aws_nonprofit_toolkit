"""Pre-UAT reviewer journey gate.

This is intentionally one browser-driven journey.  It checks the rendered
review surface after each state-changing action rather than treating API
responses as sufficient evidence.
"""

from __future__ import annotations

import asyncio
import csv
import io
import re

import pytest
from playwright.async_api import expect


pytestmark = pytest.mark.asyncio


REVIEWER = "Pre-UAT Reviewer"
REASON = "Pre-UAT journey verification"

CSV_WITH_ADDRESS = """Transaction ID,Date,Name,Email,Phone,Amount,Address
CLEAN-001,2026-08-01,Ada Lovelace,ada@example.com,(415) 555-2671,100.00,1 Main St
WARN-001,2026-08-02,Grace Hopper,grace@example.com,12345,200.00,2 Main St
BLOCK-001,2026-08-03,Alan Turing,alan@, +44 20 7946 0958,300.00,3 Main St
MULTI-001,2026-08-04,Katherine Johnson,,(415) 555-2672,400.00,4 Main St
"""

CSV_WITHOUT_ADDRESS = """Transaction ID,Date,Name,Email,Phone,Amount
NO-ADDRESS-001,2026-08-05,Source Without Address,no-address@example.com,(415) 555-2673,50.00
"""


def _row(page, transaction_id: str):
    return page.locator("tr.validation-row").filter(has_text=transaction_id)


async def _visible_transaction_ids(page) -> list[str]:
    rows = page.locator("tr.validation-row")
    visible = []
    for index in range(await rows.count()):
        row = rows.nth(index)
        if await row.is_visible():
            visible.append((await row.locator("td").first.inner_text()).strip())
    return visible


async def _visible_export_transaction_ids(page) -> set[str]:
    """Derive eligibility from the visible status/disposition controls."""
    rows = page.locator("tr.validation-row")
    eligible = set()
    for index in range(await rows.count()):
        row = rows.nth(index)
        if not await row.is_visible():
            continue
        status = (await row.locator(".validation-status-label").inner_text()).strip()
        disposition = await row.locator(".row-status-dropdown").input_value()
        if disposition in {"needs_follow_up", "reject_row"}:
            continue
        if status == "Blocking" and not disposition:
            continue
        eligible.add((await row.locator("td").first.inner_text()).strip())
    return eligible


async def _assert_projection(row, *, status: str, disposition: str) -> None:
    await expect(row.locator(".validation-status-label")).to_have_text(status)
    dropdown = row.locator(".row-status-dropdown")
    await expect(dropdown).to_have_value(disposition)
    assert await row.get_attribute("data-disposition") == disposition
    issues = (await row.locator(".issues-cell").inner_text()).strip()
    if status == "No issues":
        assert issues == "None", f"clean row still shows issues: {issues}"
    else:
        assert issues != "None", f"{status} row has no visible issue: {issues}"


async def _assert_full_projection(
    page,
    row,
    *,
    status: str,
    disposition: str,
    export_eligible: bool,
    approval_blocked: bool | None = None,
    require_gating: bool = True,
    reviewer: str | None = None,
    reason: str | None = None,
) -> None:
    """Assert the rendered row projection and its filter/gating projections."""
    await _assert_projection(row, status=status, disposition=disposition)
    assert await row.is_visible()
    if require_gating:
        assert await row.get_attribute("data-export-eligible") == str(export_eligible).lower()
        expected_approval_blocked = approval_blocked if approval_blocked is not None else (status == "Blocking" and not disposition)
        assert await row.get_attribute("data-approval-blocked") == str(expected_approval_blocked).lower()

    if reviewer is None:
        # System and unresolved states are represented by the dropdown only;
        # secondary reviewer metadata is reserved for saved human decisions.
        assert await row.locator(".row-disposition-meta").inner_text() == ""
    else:
        meta = await row.locator(".row-disposition-meta").inner_text()
        assert reviewer in meta
        assert reason not in meta

    filter_value = disposition or "none"
    disposition_filter = page.locator("#disposition-filter")
    previous_filter = await disposition_filter.input_value()
    await disposition_filter.select_option(filter_value)
    assert await row.is_visible(), f"row left effective-disposition filter {filter_value}"
    await disposition_filter.select_option(previous_filter)

    status_filter = page.locator(f'[data-row-status-filter="{status}"]')
    await status_filter.click()
    assert await row.is_visible(), f"row left Validation Status filter {status}"
    await page.locator('[data-row-status-filter="all"]').click()


async def _visible_row_snapshot(row) -> dict:
    fields = {}
    inputs = row.locator(".autosave-field")
    for index in range(await inputs.count()):
        field = inputs.nth(index)
        fields[await field.get_attribute("data-field")] = await field.input_value()
    return {
        "fields": fields,
        "issues": (await row.locator(".issues-cell").inner_text()).strip(),
        "status": (await row.locator(".validation-status-label").inner_text()).strip(),
        "disposition": await row.locator(".row-status-dropdown").input_value(),
        "meta": (await row.locator(".row-disposition-meta").inner_text()).strip(),
        "visible": await row.is_visible(),
        "export": await row.get_attribute("data-export-eligible"),
        "approval": await row.get_attribute("data-approval-blocked"),
    }


async def _wait_for_loaded_row_decision(row, has_decision: bool = False) -> None:
    await expect(row.locator(".row-status-dropdown")).to_have_attribute(
        "data-has-decision", "true" if has_decision else "false", timeout=10000
    )


async def _assert_readiness(page, *, ready: bool) -> None:
    batch_id = page.url.split("/imports/")[1].split("/")[0]
    review_url = page.url
    await page.goto(f"http://127.0.0.1:8001/imports/{batch_id}/readiness")
    try:
        heading = page.locator("h2")
        await expect(heading).to_be_visible()
        await expect(heading).to_contain_text("Export Ready" if ready else "Export Blocked")
        if ready:
            await expect(page.locator("body")).to_contain_text("Ready to generate CSV export")
        else:
            await expect(page.locator("body")).to_contain_text("blocker(s) prevent export")
            await expect(page.locator("body")).to_contain_text("Blockers:")
            await expect(page.locator("body")).to_contain_text("Next step:")
            assert await page.locator("li").count() > 0
    finally:
        await page.goto(review_url)
        await page.wait_for_selector("tr.validation-row", timeout=10000)


async def _save_edit(page, row, field: str, value: str, *, status: str, disposition: str, export_eligible: bool) -> None:
    field_input = row.locator(f'.autosave-field[data-field="{field}"]')
    await field_input.fill(value)
    await field_input.press("Tab")
    await expect(row.locator(".autosave-status").filter(has_text="Saved").first).to_be_visible(timeout=10000)
    await _assert_full_projection(page, row, status=status, disposition=disposition, export_eligible=export_eligible)


async def _save_human_decision(page, row, decision: str, reason: str = REASON, *, status: str, export_eligible: bool) -> None:
    dropdown = row.locator(".row-status-dropdown")
    await dropdown.select_option(decision)
    modal = page.locator("#record-modal")
    await expect(modal).to_be_visible()
    await modal.locator(".reviewer-name-field").fill(REVIEWER)
    await modal.locator('textarea[id^="followup-notes-"]').fill(reason)
    await modal.locator('button[id^="save-followup-notes-"]').click()
    await expect(modal).to_be_hidden(timeout=10000)
    await expect(dropdown).to_have_value(decision)
    meta = await row.locator(".row-disposition-meta").inner_text()
    assert REVIEWER in meta
    assert reason not in meta
    await _assert_full_projection(page, row, status=status, disposition=decision, export_eligible=export_eligible, reviewer=REVIEWER, reason=reason)


async def _reset_human_decision(page, row, *, status: str, export_eligible: bool) -> None:
    dropdown = row.locator(".row-status-dropdown")
    await dropdown.select_option("")
    modal = page.locator("#record-modal")
    await expect(modal).to_be_visible()
    await modal.locator(".reviewer-name-field").fill(REVIEWER)
    await modal.locator('select[id^="row-review-decision-"]').select_option("")
    await modal.locator('button[id^="save-followup-notes-"]').click()
    await expect(modal).to_be_hidden(timeout=10000)
    await _assert_full_projection(page, row, status=status, disposition="", export_eligible=export_eligible)


async def _upload(page, tmp_path, content: str, filename: str) -> None:
    csv_path = tmp_path / filename
    csv_path.write_text(content, encoding="utf-8")
    await page.goto("http://127.0.0.1:8001/")
    previous_review_href = await page.locator("#topReviewNav").get_attribute("href")
    await page.locator('input[type="file"]').set_input_files(str(csv_path))
    await page.wait_for_function(
        "({ previous }) => { const href = document.querySelector('#topReviewNav')?.getAttribute('href') || ''; return href.includes('/imports/') && href !== previous; }",
        arg={"previous": previous_review_href},
        timeout=15000,
    )
    review_href = await page.locator("#topReviewNav").get_attribute("href")
    assert review_href and "/validation" in review_href
    await page.goto(f"http://127.0.0.1:8001{review_href}")
    await page.wait_for_url("**/validation", timeout=15000)
    await page.wait_for_selector("tr.validation-row", timeout=10000)


@pytest.mark.e2e
async def test_pre_uat_reviewer_journey(flask_app_database_mode, tmp_path):
    """Run the minimum reviewer journey required before human UAT."""
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        dialog_messages = []

        async def accept_dialog(dialog):
            dialog_messages.append(dialog.message)
            await dialog.accept()

        page.on("dialog", accept_dialog)

        try:
            await _upload(page, tmp_path, CSV_WITH_ADDRESS, "pre-uat-reviewer-journey.csv")
            rows = page.locator("tr.validation-row")
            await expect(rows).to_have_count(4)

            clean = _row(page, "CLEAN-001")
            warning = _row(page, "WARN-001")
            blocking = _row(page, "BLOCK-001")
            multi = _row(page, "MULTI-001")
            for row in (clean, warning, blocking, multi):
                await expect(row).to_have_count(1)

            await _assert_full_projection(page, clean, status="No issues", disposition="accept_as_is", export_eligible=True, require_gating=False)
            await _assert_full_projection(page, warning, status="Warning", disposition="", export_eligible=True, require_gating=False)
            await _assert_full_projection(page, blocking, status="Blocking", disposition="", export_eligible=False, require_gating=False)
            await _assert_full_projection(page, multi, status="Blocking", disposition="", export_eligible=False, require_gating=False)
            assert await clean.locator('input[data-field="transaction_id"]').count() == 0
            assert await clean.locator("td").first.get_attribute("title") == "CLEAN-001"

            # Exercise every editable reviewed field with successful saves.
            for field, value in (
                ("name", "Ada Lovelace Updated"),
                ("email", "ada.updated@example.com"),
                ("phone", "+1 415 555 2671"),
                ("amount", "125.00"),
                ("address", "10 Main St, London, KY 40741"),
                ("date", "2026-08-06"),
            ):
                await _save_edit(page, clean, field, value, status="No issues", disposition="accept_as_is", export_eligible=True)

            # Successful issue transitions: warning -> clean -> warning and
            # blocking -> clean.  A failed edit is checked after reload.
            await _save_edit(page, warning, "phone", "(415) 555-9876", status="No issues", disposition="accept_as_is", export_eligible=True)
            # Warning-only rows remain exportable; only unresolved blocking
            # rows block approval/export.
            await _save_edit(page, warning, "phone", "12345", status="Warning", disposition="", export_eligible=True)
            await _save_edit(page, blocking, "email", "alan.turing@example.com", status="No issues", disposition="accept_as_is", export_eligible=True)

            amount = clean.locator('input[data-field="amount"]')
            saved_amount = await amount.input_value()
            await _wait_for_loaded_row_decision(clean)
            before_failed = await _visible_row_snapshot(clean)
            await _assert_readiness(page, ready=False)
            await amount.fill("not-an-amount")
            await amount.press("Tab")
            await expect(clean.locator(".autosave-status").filter(has_text="Error").first).to_be_visible(timeout=10000)
            await _wait_for_loaded_row_decision(clean)
            after_failed = await _visible_row_snapshot(clean)
            assert after_failed == before_failed, (before_failed, after_failed)
            await _assert_full_projection(page, clean, status="No issues", disposition="accept_as_is", export_eligible=True)
            assert await amount.input_value() == saved_amount
            await _assert_readiness(page, ready=False)
            await page.reload()
            await page.wait_for_selector("tr.validation-row", timeout=10000)
            clean = _row(page, "CLEAN-001")
            await _assert_projection(clean, status="No issues", disposition="accept_as_is")
            assert "$125.00" in await clean.locator('input[data-field="amount"]').input_value()
            # Re-establish the client-side gating attributes after the fresh
            # render before collecting the visible eligible-row set.
            await _save_edit(page, clean, "amount", "125.00", status="No issues", disposition="accept_as_is", export_eligible=True)

            # Save, reset, and save again to prove the human-decision flow.
            warning = _row(page, "WARN-001")
            await _save_human_decision(page, warning, "accept_as_is", "Accepted after warning review", status="Warning", export_eligible=True)
            await _reset_human_decision(page, warning, status="Warning", export_eligible=True)
            await _save_human_decision(page, warning, "needs_follow_up", "Follow up after warning", status="Warning", export_eligible=False)
            await _save_human_decision(page, warning, "reject_row", "Reject warning row", status="Warning", export_eligible=False)
            await _reset_human_decision(page, warning, status="Warning", export_eligible=True)
            await _save_human_decision(page, warning, "accept_as_is", "Accepted after warning review", status="Warning", export_eligible=True)

            multi = _row(page, "MULTI-001")
            blocking = _row(page, "BLOCK-001")
            await _save_human_decision(page, blocking, "reject_row", "Reject duplicate source row", status="No issues", export_eligible=False)
            visible_eligible_ids = await _visible_export_transaction_ids(page)
            assert visible_eligible_ids

            # Leave the remaining blocking row unresolved and prove approval is
            # visibly refused before resolving it.
            approve_button = page.locator("#approve-file-btn")
            if await approve_button.is_disabled():
                assert await approve_button.get_attribute("aria-disabled") in {"true", None}
                await _assert_readiness(page, ready=False)
            else:
                dialog_count_before = len(dialog_messages)
                async with page.expect_response("**/approve-batch") as approval_response_info:
                    await approve_button.evaluate("element => element.click()")
                approval_response = await approval_response_info.value
                assert approval_response.status == 400
                approval_body = await approval_response.json()
                assert "unresolved" in approval_body.get("error", "").lower()
                new_dialogs = dialog_messages[dialog_count_before:]
                assert any("unresolved" in message.lower() or "resolve" in message.lower() for message in new_dialogs), dialog_messages
                await _assert_readiness(page, ready=False)
            assert "/validation" in page.url
            await _assert_projection(multi, status="Blocking", disposition="")

            # Exercise Needs follow-up to resolve the final blocker and verify
            # readiness/export exclusion; Accept-as-is is exercised on warning.
            await _save_human_decision(page, multi, "needs_follow_up", "Follow up with donor", status="Blocking", export_eligible=False)
            await _assert_readiness(page, ready=True)
            await page.locator(f'tr[data-record-id="{await warning.get_attribute("data-record-id")}"] [data-action="inspect-record"]').click()
            modal = page.locator("#record-modal")
            await expect(modal).to_be_visible()
            await expect(modal).to_contain_text("Review history")
            history_text = await modal.inner_text()
            history_entries = modal.locator("section").filter(has_text="Review history").last.locator("article")
            assert await history_entries.count() == 6
            history_entry_text = [await history_entries.nth(index).inner_text() for index in range(await history_entries.count())]
            assert "Accept as-is" in history_entry_text[0]
            assert "Accepted after warning review" in history_entry_text[0]
            assert "Decision cleared by reviewer" in history_entry_text[1]
            assert "Reject row" in history_entry_text[2]
            assert "Reject warning row" in history_entry_text[2]
            assert "Needs follow-up" in history_entry_text[3]
            assert "Follow up after warning" in history_entry_text[3]
            assert "Decision cleared by reviewer" in history_entry_text[4]
            assert "Accept as-is" in history_entry_text[5]
            assert "Accepted after warning review" in history_entry_text[5]
            assert all("Reviewer not identified" not in entry for entry in history_entry_text[:6])
            assert all(re.search(r"\d{1,2}/\d{1,2}/20\d\d", entry) for entry in history_entry_text[:6])
            assert len(history_entry_text) == len(set(history_entry_text))
            await modal.locator("#modal-record-footer button").first.click()
            await expect(modal).to_be_hidden()

            # Severity and disposition filters, including composition.
            await page.locator('[data-row-status-filter="Blocking"]').click()
            await page.locator('[data-row-status-filter="Warning"]').click()
            visible = await _visible_transaction_ids(page)
            assert set(visible) == {"WARN-001", "MULTI-001"}
            await page.locator('[data-row-status-filter="No issues"]').click()
            assert set(await _visible_transaction_ids(page)) == {"CLEAN-001", "BLOCK-001"}
            await page.locator('[data-row-status-filter="all"]').click()
            await page.locator("#disposition-filter").select_option("accept_as_is")
            await page.locator('[data-row-status-filter="Warning"]').click()
            await page.locator("#search-records").fill("WARN-001")
            assert await _visible_transaction_ids(page) == ["WARN-001"]
            await page.locator("#disposition-filter").select_option("needs_follow_up")
            assert await _visible_transaction_ids(page) == []
            await page.locator("#search-records").fill("")
            await page.locator("#disposition-filter").select_option("accept_as_is")
            await page.locator('[data-row-status-filter="all"]').click()

            # Fresh request preserves visible state and history context.
            await page.reload()
            await page.wait_for_selector("tr.validation-row", timeout=10000)
            warning = _row(page, "WARN-001")
            multi = _row(page, "MULTI-001")
            await _assert_full_projection(page, warning, status="Warning", disposition="accept_as_is", export_eligible=True, reviewer=REVIEWER, reason="Accepted after warning review", require_gating=False)
            await _assert_full_projection(page, multi, status="Blocking", disposition="needs_follow_up", export_eligible=False, reviewer=REVIEWER, reason="Follow up with donor", require_gating=False)
            await warning.locator('[data-action="inspect-record"]').click()
            await expect(page.locator("#record-modal")).to_contain_text("Review history", timeout=10000)
            reloaded_history = await page.locator("#record-modal").inner_text()
            reloaded_entries = page.locator("#record-modal section").filter(has_text="Review history").last.locator("article")
            reloaded_entry_text = [await reloaded_entries.nth(index).inner_text() for index in range(await reloaded_entries.count())]
            assert reloaded_entry_text == history_entry_text
            await page.locator("#modal-record-footer button").first.click()

            # Approval and export are exercised through the browser surface.
            await page.locator("#approve-file-btn").click()
            await page.wait_for_url("**/dashboard", timeout=15000)
            batch_id = page.url.split("/imports/")[1].split("/")[0]
            await page.goto(f"http://127.0.0.1:8001/imports/{batch_id}/exports")
            await expect(page.locator("#generate-export-btn")).to_be_enabled(timeout=10000)
            await page.locator("#generate-export-btn").click()
            export_link = page.locator('[data-action="download-export"]').last
            await expect(export_link).to_be_visible(timeout=15000)
            export_href = await export_link.get_attribute("href")
            assert export_href
            export_response = await page.request.get(f"http://127.0.0.1:8001{export_href}")
            assert export_response.ok
            export_text = await export_response.text()
            exported_ids = {
                row["transaction_id"]
                for row in csv.DictReader(io.StringIO(export_text))
            }
            assert visible_eligible_ids
            assert exported_ids == visible_eligible_ids

            # Verify the source-without-address visibility contract in the
            # same browser session using a second small real upload.
            await _upload(page, tmp_path, CSV_WITHOUT_ADDRESS, "pre-uat-no-address.csv")
            assert await page.locator("th", has_text="Address").count() == 0
            assert await page.locator('input[data-field="address"]').count() == 0
        finally:
            await browser.close()
