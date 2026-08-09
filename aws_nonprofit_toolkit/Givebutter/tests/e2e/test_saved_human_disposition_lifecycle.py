"""P1 contract: saved human dispositions survive validation changes."""

from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import (  # noqa: E402
    AuditLogRecord,
    ImportBatch,
    ImportContact,
    RawImportRow,
    ReviewDecision,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from scripts.householder.export_preview_service import build_export_preview  # noqa: E402
from tests.e2e.test_validation_review_dom import (  # noqa: E402
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


def _seed_issue(session, batch_id):
    session.add(ImportBatch(
        id=batch_id,
        filename=f"{batch_id}.csv",
        upload_timestamp=datetime.now(timezone.utc),
        status="pending_review",
        raw_row_count=1,
    ))
    session.flush()
    raw = RawImportRow(
        batch_id=batch_id,
        row_index=1,
        raw_csv_data={
            "Transaction ID": "p1-contract-1",
            "name": "P1 Donor",
            "date": "2026-08-08",
            "email": "bad-email",
            "phone": "4155552671",
            "amount": "100.00",
            "address": "1 Main St",
        },
    )
    session.add(raw)
    session.flush()
    contact = ImportContact(
        batch_id=batch_id,
        raw_import_row_id=raw.id,
        first_name="P1",
        last_name="Donor",
        email="bad-email",
        phone="4155552671",
        address_line1="1 Main St",
        amount=100.0,
    )
    session.add(contact)
    session.flush()
    issue = ReviewItem(
        batch_id=batch_id,
        item_type="validation",
        confidence=1.0,
        payload_json={
            "field": "email",
            "reason": "invalid",
            "description": "Invalid email address",
            "severity": "error",
            "issue": "invalid_email",
            "validation_tier": "critical",
        },
    )
    session.add(issue)
    session.flush()
    session.add(ReviewItemSubject(
        review_item_id=issue.id,
        subject_type="import_contact_snapshot",
        subject_id=contact.id,
        role="primary",
    ))
    session.commit()
    return raw


def _seed_clean(session, batch_id):
    session.add(ImportBatch(
        id=batch_id,
        filename=f"{batch_id}.csv",
        upload_timestamp=datetime.now(timezone.utc),
        status="pending_review",
        raw_row_count=1,
    ))
    session.flush()
    raw = RawImportRow(
        batch_id=batch_id,
        row_index=1,
        raw_csv_data={
            "Transaction ID": "p1-contract-clean-1",
            "name": "Clean Donor",
            "date": "2026-08-08",
            "email": "clean@example.com",
            "phone": "4155552671",
            "amount": "100.00",
            "address": "1 Main St",
        },
    )
    session.add(raw)
    session.flush()
    session.add(ImportContact(
        batch_id=batch_id,
        raw_import_row_id=raw.id,
        first_name="Clean",
        last_name="Donor",
        email="clean@example.com",
        phone="4155552671",
        address_line1="1 Main St",
        amount=100.0,
    ))
    session.commit()
    return raw


async def _save_human_accept(page):
    row = page.locator("tr.validation-row").first
    await row.locator("select.row-status-dropdown").select_option("accept_as_is")
    modal = page.locator("#record-modal")
    await modal.wait_for(state="visible", timeout=5000)
    await modal.locator(".reviewer-name-field").fill("P1 Contract Reviewer")
    await modal.locator('textarea[id^="followup-notes-"]').fill(
        "The source value is accepted for this review."
    )
    await modal.locator('button[id^="save-followup-notes-"]').click()
    await modal.wait_for(state="hidden", timeout=5000)
    await page.wait_for_function(
        "() => document.querySelector('tr.validation-row .row-status-dropdown')?.value === 'accept_as_is'",
        timeout=5000,
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_saved_human_disposition_survives_validation_changes(e2e_database_and_app):
    """Human acceptance remains effective while validation status changes independently."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "p1-saved-disposition-lifecycle"
    server = flask_thread = None

    try:
        raw = _seed_issue(session, batch_id)
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator(".validation-status-label").inner_text() == "Blocking"
                assert await row.locator(".row-status-dropdown").input_value() == ""

                await _save_human_accept(page)
                session.expire_all()
                human = session.query(ReviewDecision).filter_by(
                    batch_id=batch_id,
                    raw_import_row_id=raw.id,
                    decision="row_status:accept_as_is",
                ).all()
                assert len(human) == 1
                assert human[0].reviewer == "P1 Contract Reviewer"
                audit_count_after_save = session.query(AuditLogRecord).filter_by(batch_id=batch_id).count()

                # The issue remains visible, but human Accept-as-is makes the row export-eligible.
                assert await row.locator(".validation-status-label").inner_text() == "Blocking"
                preview = build_export_preview(batch_id, {"GIVEBUTTER_DATABASE_URL": database_url})
                assert preview.blocked_count == 0
                assert len(preview.export_rows) == 1

                email = row.locator('input[data-field="email"]')
                await email.fill("p1.clean@example.com")
                await email.evaluate("element => element.blur()")
                await page.wait_for_function(
                    "() => document.querySelector('tr.validation-row .validation-status-label')?.textContent.trim() === 'No issues'",
                    timeout=5000,
                )
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"

                session.expire_all()
                assert session.query(ReviewDecision).filter_by(
                    batch_id=batch_id,
                    raw_import_row_id=raw.id,
                    decision="row_status:accept_as_is",
                ).count() == 1
                assert session.query(AuditLogRecord).filter_by(batch_id=batch_id).count() >= audit_count_after_save
                assert session.query(RawImportRow).filter_by(id=raw.id).one().raw_csv_data["email"] == "bad-email"
                preview = build_export_preview(batch_id, {"GIVEBUTTER_DATABASE_URL": database_url})
                assert preview.blocked_count == 0
                assert len(preview.export_rows) == 1
                await page.goto(f"{base_url}/imports/{batch_id}/readiness")
                assert "Export Blocked" not in await page.inner_text("body")

                # Reload preserves both the saved human projection and clean readiness.
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator(".validation-status-label").inner_text() == "No issues"
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"

                # Reintroducing the issue changes validation only; the saved human disposition remains effective.
                email = row.locator('input[data-field="email"]')
                await email.fill("again-invalid")
                await email.evaluate("element => element.blur()")
                await page.wait_for_function(
                    "() => document.querySelector('tr.validation-row .validation-status-label')?.textContent.trim() === 'Blocking'",
                    timeout=5000,
                )
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"
                session.expire_all()
                assert session.query(ReviewDecision).filter_by(
                    batch_id=batch_id,
                    raw_import_row_id=raw.id,
                    decision="row_status:accept_as_is",
                ).count() == 1
                assert session.query(AuditLogRecord).filter_by(batch_id=batch_id).count() >= audit_count_after_save
                preview = build_export_preview(batch_id, {"GIVEBUTTER_DATABASE_URL": database_url})
                assert preview.blocked_count == 0
                assert len(preview.export_rows) == 1
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_transient_invalid_edit_restores_persisted_clean_projection(e2e_database_and_app):
    """Invalid browser edits block transiently but cannot change persisted clean state."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "p1-transient-invalid-clean"
    server = flask_thread = None

    try:
        raw = _seed_clean(session, batch_id)
        original_email = raw.raw_csv_data["email"]
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator(".validation-status-label").inner_text() == "No issues"
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"
                assert session.query(ReviewDecision).filter_by(batch_id=batch_id).count() == 0

                email = row.locator('input[data-field="email"]')
                await email.fill("transient-invalid")
                await email.evaluate("element => element.blur()")
                await page.wait_for_function(
                    "() => document.querySelector('tr.validation-row .validation-status-label')?.textContent.trim() === 'Blocking'",
                    timeout=5000,
                )
                assert await row.locator(".row-status-dropdown").input_value() == ""
                assert session.query(ReviewDecision).filter_by(batch_id=batch_id).count() == 0

                # The rejected invalid correction is not part of persisted export/readiness state.
                session.expire_all()
                assert session.query(RawImportRow).filter_by(id=raw.id).one().raw_csv_data["email"] == original_email
                preview = build_export_preview(batch_id, {"GIVEBUTTER_DATABASE_URL": database_url})
                assert preview.blocked_count == 0
                assert len(preview.export_rows) == 1

                await page.reload()
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator('input[data-field="email"]').input_value() == original_email
                assert await row.locator(".validation-status-label").inner_text() == "No issues"
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"
                assert session.query(ReviewDecision).filter_by(batch_id=batch_id).count() == 0
                preview = build_export_preview(batch_id, {"GIVEBUTTER_DATABASE_URL": database_url})
                assert preview.blocked_count == 0
                assert len(preview.export_rows) == 1
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()
