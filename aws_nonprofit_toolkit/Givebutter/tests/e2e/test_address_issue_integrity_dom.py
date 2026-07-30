from __future__ import annotations

from datetime import datetime, timezone

import pytest
from playwright.async_api import async_playwright
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import (
    Base,
    ImportBatch,
    ImportContact,
    RawImportRow,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)


def _seed_duplicate_address_batch(database_url: str) -> tuple[int, int]:
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        batch = ImportBatch(
            id="address-dom-batch",
            filename="address_dom.csv",
            upload_timestamp=datetime.now(timezone.utc),
            status="pending_review",
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id=batch.id,
            row_index=1,
            raw_csv_data={"Address 1": "", "Name": "Address Row"},
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id=batch.id,
            raw_import_row_id=raw_row.id,
            first_name="Address",
            last_name="Row",
            address_line1="",
        )
        session.add(contact)
        session.flush()

        for field in ("ADDRESS 1", "street address"):
            review_item = ReviewItem(
                batch_id=batch.id,
                item_type="validation",
                status="pending",
                confidence=1.0,
                payload_json={
                    "field": field,
                    "reason": "missing",
                    "severity": "warning",
                    "description": "Missing address",
                },
            )
            session.add(review_item)
            session.flush()
            session.add(
                ReviewItemSubject(
                    review_item_id=review_item.id,
                    subject_type="import_raw_row",
                    subject_id=raw_row.id,
                    role="primary",
                )
            )

        session.commit()
        return raw_row.id, contact.id
    finally:
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_duplicate_missing_address_issue_is_deduped_in_browser_and_clears_on_edit(
    flask_app_database_mode,
):
    _process, database_url, _db_path = flask_app_database_mode
    raw_row_id, contact_id = _seed_duplicate_address_batch(database_url)
    batch_id = "address-dom-batch"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            await page.goto(f"http://127.0.0.1:8001/imports/{batch_id}/validation")
            await page.wait_for_selector(f"#validation-row-{contact_id}", timeout=10000)

            row = page.locator(f"#validation-row-{contact_id}")
            issues_cell = row.locator('td[data-testid^="issues-cell-"]')
            issue_spans = issues_cell.locator("span")
            assert await issue_spans.count() == 1
            assert "Missing address" in await issue_spans.nth(0).inner_text()
            assert (await row.locator("select.row-status-dropdown option:first-child").text_content() or "").strip() == "Warning"

            details_button = row.locator('a[data-action="inspect-record"]')
            await details_button.click()
            await page.wait_for_selector("#record-modal", timeout=5000)
            modal_text = await page.locator("#modal-record-content").inner_text()
            assert modal_text.count("Missing address") == 1
            assert "Missing address" in modal_text
            await page.locator("#record-modal button:has-text(\"Close\")").click()
            await page.wait_for_function(
                "() => !document.querySelector('#record-modal')?.classList.contains('show')",
                timeout=5000,
            )

            address_input = row.locator('input[data-field="address"]')
            await address_input.fill("456 New St")
            await address_input.evaluate("el => el.blur()")

            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_selector(f"#validation-row-{contact_id}", timeout=10000)
            reloaded_row = page.locator(f"#validation-row-{contact_id}")
            reloaded_issues = reloaded_row.locator('td[data-testid^="issues-cell-"]')
            assert (await reloaded_issues.inner_text() or "").strip() == "None"
            assert (await reloaded_row.locator("select.row-status-dropdown option:first-child").text_content() or "").strip() == "No issues"

            from sqlalchemy import create_engine

            verify_session = sessionmaker(bind=create_engine(database_url))()
            try:
                persisted_row = verify_session.query(RawImportRow).filter_by(id=raw_row_id).one()
                assert persisted_row.raw_csv_data["Address 1"] == ""
                assert persisted_row.raw_csv_data["Name"] == "Address Row"
            finally:
                verify_session.close()

        finally:
            await browser.close()
