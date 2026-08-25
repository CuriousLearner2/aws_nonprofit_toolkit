"""One end-to-end upload-to-export smoke contract."""

import csv
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import RawImportRow, create_db_engine


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_review_fresh_session_approval_and_export_smoke(
    flask_app_database_mode, temp_dir,
):
    """A small real upload survives review, a fresh page, approval, and export."""
    from playwright.async_api import async_playwright

    Path("/tmp/givebutter/exports").mkdir(parents=True, exist_ok=True)
    csv_file = Path(temp_dir) / "final-product-smoke.csv"
    original_csv = (
        "Donation ID,Date,Donor Name,Email,Phone,Amount,Address 1,Campaign Title\n"
        "TX-CLEAN,2026-08-15,Clean User,clean@example.com,4155550101,100.00,1 Main St,General\n"
        "TX-WARN,2026-08-15,Warning User,warn@gmai.com,4155550102,110.00,2 Main St,General\n"
        "TX-BLOCK,2026-08-15,Blocking User,bad-email,4155550103,120.00,3 Main St,General\n"
        "TX-FOLLOW,2026-08-15,Follow User,follow@example.com,4155550104,130.00,4 Main St,General\n"
        "TX-REJECT,2026-08-15,Reject User,reject@example.com,4155550105,140.00,5 Main St,General\n"
    )
    csv_file.write_text(original_csv)

    async def save_disposition(page, row_index, decision, reviewer, reason):
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

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("http://127.0.0.1:8001/")
            await page.locator('input[type="file"]').set_input_files(str(csv_file))
            submit = page.locator('button[type="submit"]')
            if await submit.count():
                await submit.click()

            queue_link = page.locator("#queueBody tr a.action-btn.primary").first
            await queue_link.wait_for(state="visible", timeout=15000)
            review_url = await queue_link.get_attribute("href")
            assert review_url and review_url.endswith("/validation")
            batch_id = urlparse(review_url).path.split("/")[2]
            await queue_link.click()
            await page.wait_for_url("**/imports/*/validation", timeout=10000)

            rows = page.locator("tr.validation-row")
            await rows.nth(4).wait_for()
            assert await rows.count() == 5
            assert await rows.nth(0).locator('input[data-field="transaction_id"]').count() == 0
            assert "TX-CLEAN" in await rows.nth(0).inner_text()

            statuses = await rows.locator(".validation-status-label").all_inner_texts()
            assert statuses == ["No issues", "Warning", "Blocking", "No issues", "No issues"]
            assert await rows.nth(2).locator("select.row-status-dropdown").input_value() == ""

            await save_disposition(page, 1, "accept_as_is", "Smoke Accept Reviewer", "Accept warning")
            await save_disposition(page, 3, "needs_follow_up", "Smoke Follow Reviewer", "Follow up later")
            await save_disposition(page, 4, "reject_row", "Smoke Reject Reviewer", "Reject from export")

            # The unresolved blocking row prevents approval.
            approval_message = None

            async def capture_block(dialog):
                nonlocal approval_message
                approval_message = dialog.message
                await dialog.accept()

            page.once("dialog", capture_block)
            await page.locator("#approve-file-btn").click()
            await page.wait_for_timeout(200)
            assert approval_message and "resolve" in approval_message.lower()

            blocker = rows.nth(2).locator('input[data-field="email"]')
            await blocker.fill("blocking.resolved@example.com")
            await blocker.evaluate("element => element.blur()")
            await page.wait_for_function(
                "() => document.querySelectorAll('tr.validation-row')[2]?.querySelector('.validation-status-label')?.textContent.trim() === 'No issues'"
            )
            assert await rows.nth(2).locator("select.row-status-dropdown").input_value() == "accept_as_is"

            # Leave the page, then use a fresh page/request for all durable assertions.
            await page.goto(f"http://127.0.0.1:8001/imports/{batch_id}/dashboard")
            fresh = await browser.new_page()
            try:
                await fresh.goto(f"http://127.0.0.1:8001/imports/{batch_id}/validation")
                fresh_rows = fresh.locator("tr.validation-row")
                await fresh_rows.nth(4).wait_for()
                assert await fresh_rows.nth(2).locator('input[data-field="email"]').input_value() == "blocking.resolved@example.com"
                await fresh.wait_for_function(
                    "expected => Array.from(document.querySelectorAll('select.row-status-dropdown')).map(select => select.value).join('|') === expected.join('|')",
                    arg=["accept_as_is", "accept_as_is", "accept_as_is", "needs_follow_up", "reject_row"],
                )
                assert [await fresh_rows.nth(i).locator("select.row-status-dropdown").input_value() for i in range(5)] == [
                    "accept_as_is", "accept_as_is", "accept_as_is", "needs_follow_up", "reject_row"
                ]
                assert "Smoke Accept Reviewer" in await fresh_rows.nth(1).locator(".row-disposition-meta").inner_text()
                assert "Smoke Follow Reviewer" in await fresh_rows.nth(3).locator(".row-disposition-meta").inner_text()
                assert "Smoke Reject Reviewer" in await fresh_rows.nth(4).locator(".row-disposition-meta").inner_text()

                readiness = await fresh.goto(f"http://127.0.0.1:8001/imports/{batch_id}/readiness")
                assert readiness and "Export Ready" in await fresh.inner_text("body")

                approval_success = None

                async def capture_success(dialog):
                    nonlocal approval_success
                    approval_success = dialog.message
                    await dialog.accept()

                fresh.once("dialog", capture_success)
                await fresh.goto(f"http://127.0.0.1:8001/imports/{batch_id}/validation")
                await fresh.locator("#approve-file-btn").click()
                await fresh.wait_for_timeout(200)
                assert approval_success == "File approved successfully!"

                await fresh.goto(f"http://127.0.0.1:8001/imports/{batch_id}/exports")
                preview_response = await fresh.request.post(
                    f"http://127.0.0.1:8001/imports/{batch_id}/exports/preview"
                )
                assert preview_response.status == 200
                preview_html = await preview_response.text()
                assert "Export Ready" in preview_html

                generated = await fresh.request.post(
                    f"http://127.0.0.1:8001/imports/{batch_id}/exports/generate"
                )
                assert generated.status == 200
                generated_data = await generated.json()
                download = await fresh.request.get(
                    f"http://127.0.0.1:8001/imports/{batch_id}/exports/download/"
                    f"{generated_data['file']['audit_log_id']}"
                )
                assert download.status == 200
                exported_ids = {
                    row["transaction_id"]
                    for row in csv.DictReader(StringIO(await download.text()))
                }
                assert exported_ids == {"TX-CLEAN", "TX-WARN", "TX-BLOCK"}

                engine = create_db_engine(flask_app_database_mode[1])
                session = sessionmaker(bind=engine)()
                try:
                    raw_rows = session.query(RawImportRow).filter_by(batch_id=batch_id).all()
                    raw_by_txn = {row.raw_csv_data.get("Donation ID"): row.raw_csv_data for row in raw_rows}
                    assert raw_by_txn["TX-BLOCK"]["Email"] == "bad-email"
                    assert raw_by_txn["TX-WARN"]["Email"] == "warn@gmai.com"
                finally:
                    session.close()
            finally:
                await fresh.close()
        finally:
            await browser.close()
