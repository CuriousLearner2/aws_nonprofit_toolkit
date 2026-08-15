"""Browser-level acceptance contract for reconciled validation dispositions.

These tests intentionally exercise cross-feature state transitions rather than
isolated controls.  They encode the current product contract:

* clean row -> system Accept as-is, without a human ReviewDecision
* issue row -> No disposition until a human saves one
* only issue-bearing No disposition blocks finalization/readiness
* human Accept as-is on an issue row requires reviewer + reason/notes and
  preserves the issue
* Needs follow-up and Reject row are excluded from the current export
* clearing a saved human disposition restores the correct system default
* validation status and reviewer disposition remain separate after reload

The module reuses the current E2E database/app fixture and server helpers from
``test_validation_review_dom`` so it can be dropped directly into tests/e2e/.
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
    RawImportRow,
    ReviewDecision,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from scripts.householder.export_preview_service import build_export_preview
from scripts.householder.row_decision_service import requires_reason_for_row_decision

from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    enter_reviewer_name,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


def _seed_row(session, *, batch_id: str, row_index: int, email: str, name: str, address: str | None = None):
    address = f"{row_index} Main St" if address is None else address
    raw_row = RawImportRow(
        batch_id=batch_id,
        row_index=row_index,
        raw_csv_data={
            "Transaction ID": f"txn-{batch_id}-{row_index}",
            "name": name,
            "date": "2026-08-08",
            "email": email,
            "phone": "4155552671",
            "amount": "100.00",
            "address": address,
        },
    )
    session.add(raw_row)
    session.flush()

    first, last = (name.split(" ", 1) + ["User"])[:2]
    contact = ImportContact(
        batch_id=batch_id,
        raw_import_row_id=raw_row.id,
        first_name=first,
        last_name=last,
        email=email,
        phone="4155552671",
        address_line1=address,
        amount=100.0,
    )
    session.add(contact)
    session.flush()
    return raw_row, contact


def _seed_batch(session, *, batch_id: str, rows: list[dict]):
    session.add(
        ImportBatch(
            id=batch_id,
            filename=f"{batch_id}.csv",
            upload_timestamp=datetime.now(timezone.utc),
            status="pending_review",
            raw_row_count=len(rows),
        )
    )
    session.flush()

    seeded = []
    for index, spec in enumerate(rows, start=1):
        raw_row, contact = _seed_row(
            session,
            batch_id=batch_id,
            row_index=index,
            email=spec["email"],
            name=spec["name"],
            address=spec.get("address"),
        )
        if spec.get("issue"):
            review_item = ReviewItem(
                batch_id=batch_id,
                item_type="validation",
                confidence=1.0,
                payload_json={
                    "field": spec.get("field", "email"),
                    "reason": "invalid" if spec["email"] else "missing",
                    "description": spec["issue"],
                    "severity": spec.get("severity", "error"),
                    # Keep the ingestion-compatible keys too.  Current code has
                    # historically accepted both representations.
                    "issue": "invalid_email" if spec["email"] else "missing_email",
                    "validation_tier": "warning" if spec.get("severity") == "warning" else "critical",
                    "suggestion": None,
                },
            )
            session.add(review_item)
            session.flush()
            session.add(
                ReviewItemSubject(
                    review_item_id=review_item.id,
                    subject_type="import_contact_snapshot",
                    subject_id=contact.id,
                    role="primary",
                )
            )
        seeded.append((raw_row, contact))

    session.commit()
    return seeded


async def _save_row_disposition(page, row_index: int, value: str, *, reviewer="Contract Reviewer", notes="Contract reason"):
    row = page.locator("tr.validation-row").nth(row_index)
    dropdown = row.locator("select.row-status-dropdown")
    await dropdown.select_option(value)
    modal = page.locator("#record-modal")
    await modal.wait_for(state="visible", timeout=5000)
    reviewer_field = modal.locator(".reviewer-name-field")
    await reviewer_field.fill(reviewer)
    notes_field = modal.locator('textarea[id^="followup-notes-"]')
    await notes_field.fill(notes)
    await modal.locator('button[id^="save-followup-notes-"]').click()
    await modal.wait_for(state="hidden", timeout=5000)
    if value:
        await page.wait_for_function(
            "([index, expected]) => document.querySelectorAll('select.row-status-dropdown')[index]?.value === expected",
            arg=[row_index, value],
            timeout=5000,
        )
    else:
        await page.wait_for_function(
            "([index]) => document.querySelectorAll('.row-disposition-meta')[index]?.textContent.includes('Decision cleared by reviewer')",
            arg=[row_index],
            timeout=5000,
        )
    return row


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_clean_row_uses_system_accept_as_is_without_human_decision(e2e_database_and_app):
    """A clean row is implicitly accepted without creating review/audit state."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-clean-default"
    server = flask_thread = None

    try:
        [(raw_row, _)] = _seed_batch(
            session,
            batch_id=batch_id,
            rows=[{"name": "Clean Donor", "email": "clean@example.com"}],
        )
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                await row.wait_for()

                assert await row.locator(".validation-status-label").inner_text() == "No issues"
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"

                # Opening a human Accept-as-is review on a clean row keeps the
                # reason optional; the system projection itself creates no review.
                await page.evaluate(
                    """async () => {
                        const row = document.querySelector('tr.validation-row');
                        await openRowReviewModal(
                            row.dataset.recordId,
                            row.querySelector('.row-status-dropdown'),
                            'accept_as_is',
                        );
                    }"""
                )
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                assert await modal.locator('textarea[id^="followup-notes-"]').get_attribute("aria-required") == "false"
                assert await modal.locator(".notes-optional-marker").is_visible()
                await modal.locator('button[id^="cancel-row-review-"]').click()
                await modal.wait_for(state="hidden")

                session.expire_all()
                assert session.query(ReviewDecision).filter_by(
                    batch_id=batch_id,
                    raw_import_row_id=raw_row.id,
                ).count() == 0

                await page.reload()
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_issue_row_defaults_to_no_disposition_and_blocks_readiness(e2e_database_and_app):
    """An issue row has no system disposition and remains a readiness blocker."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-issue-default"
    server = flask_thread = None

    try:
        [(raw_row, _)] = _seed_batch(
            session,
            batch_id=batch_id,
            rows=[{"name": "Issue Donor", "email": "", "issue": "Missing email address"}],
        )
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator(".validation-status-label").inner_text() == "Blocking"

                dropdown = row.locator(".row-status-dropdown")
                assert await dropdown.input_value() in ("", "no_disposition")
                option_text = (await dropdown.locator("option").first.inner_text()).lower()
                assert "no disposition" in option_text

                assert session.query(ReviewDecision).filter_by(
                    batch_id=batch_id,
                    raw_import_row_id=raw_row.id,
                ).count() == 0

                await page.goto(f"{base_url}/imports/{batch_id}/readiness")
                await page.locator("h2", has_text="Export Blocked").wait_for(state="visible", timeout=5000)
                assert "Export Blocked" in await page.inner_text("body")
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_issue_accept_as_is_requires_reviewer_and_reason_and_preserves_issue(e2e_database_and_app):
    """Human Accept as-is is metadata-gated and never erases the validation issue."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-issue-accept"
    server = flask_thread = None

    try:
        [(raw_row, _)] = _seed_batch(
            session,
            batch_id=batch_id,
            rows=[{"name": "Accepted Issue", "email": "bad-email", "issue": "Invalid email address"}],
        )
        original_raw = dict(raw_row.raw_csv_data)
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                dropdown = row.locator(".row-status-dropdown")
                await dropdown.select_option("accept_as_is")
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible", timeout=5000)

                # Empty metadata must not save.
                await modal.locator('button[id^="save-followup-notes-"]').click()
                assert await modal.is_visible()
                assert session.query(ReviewDecision).filter_by(batch_id=batch_id).count() == 0

                # Reviewer alone is still insufficient: Reason / notes is mandatory.
                await modal.locator(".reviewer-name-field").fill("Contract Reviewer")
                await modal.locator('button[id^="save-followup-notes-"]').click()
                assert await modal.is_visible()
                assert session.query(ReviewDecision).filter_by(batch_id=batch_id).count() == 0

                notes = "Accept source value as-is; issue remains visible for audit."
                await modal.locator('textarea[id^="followup-notes-"]').fill(notes)
                await modal.locator('button[id^="save-followup-notes-"]').click()
                await modal.wait_for(state="hidden", timeout=5000)
                await page.wait_for_function(
                    "() => document.querySelector('tr.validation-row .row-status-dropdown')?.value === 'accept_as_is'"
                )

                # Validation and disposition remain separate.
                assert await row.locator(".validation-status-label").inner_text() == "Blocking"
                assert await dropdown.input_value() == "accept_as_is"

                session.expire_all()
                latest = session.query(ReviewDecision).filter_by(
                    batch_id=batch_id,
                    raw_import_row_id=raw_row.id,
                ).order_by(ReviewDecision.id.desc()).first()
                assert latest is not None
                assert latest.decision == "row_status:accept_as_is"
                assert latest.reviewer == "Contract Reviewer"
                assert notes in str(latest.reviewed_values)
                assert session.query(RawImportRow).filter_by(id=raw_row.id).one().raw_csv_data == original_raw

                await page.reload()
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator(".validation-status-label").inner_text() == "Blocking"
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_warning_accept_as_is_requires_reviewer_and_reason(e2e_database_and_app):
    """A warning is still an issue and requires an auditable Accept-as-is reason."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-warning-accept"
    server = flask_thread = None

    try:
        [(raw_row, _)] = _seed_batch(
            session,
            batch_id=batch_id,
            rows=[{
                "name": "Warning Accept",
                "email": "warning@example.com",
                "issue": "Address missing",
                "severity": "warning",
            }],
        )
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                assert await row.locator(".validation-status-label").inner_text() == "Warning"
                await row.locator(".row-status-dropdown").select_option("accept_as_is")
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                notes = modal.locator('textarea[id^="followup-notes-"]')
                assert await notes.get_attribute("aria-required") == "true"
                assert await modal.locator(".notes-required-marker").is_visible()
                await modal.locator(".reviewer-name-field").fill("Warning Reviewer")
                await modal.locator('button[id^="save-followup-notes-"]').click()
                assert await modal.is_visible()
                assert "Reason / notes required for Accept as-is" in await modal.inner_text()
                assert session.query(ReviewDecision).filter_by(
                    batch_id=batch_id, raw_import_row_id=raw_row.id,
                ).count() == 0
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reason_requirement_frontend_backend_parity_matrix(e2e_database_and_app):
    """Browser requirement state matches the backend rule for every row state."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-reason-parity-matrix"
    server = flask_thread = None
    rows = [
        {"name": "Clean", "email": "clean@example.com"},
        {
            "name": "Warning",
            "email": "warning@example.com",
            "address": "",
            "field": "address",
            "issue": "Address missing",
            "severity": "warning",
        },
        {
            "name": "Blocking",
            "email": "not-an-email",
            "field": "email",
            "issue": "Invalid email",
            "severity": "error",
        },
    ]
    expected_states = {0: "clean", 1: "warning", 2: "blocking"}
    decisions = [None, "accept_as_is", "needs_follow_up", "reject_row"]

    try:
        _seed_batch(session, batch_id=batch_id, rows=rows)
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                all_rows = page.locator("tr.validation-row")
                assert await all_rows.count() == 3

                for row_index, state in expected_states.items():
                    row = all_rows.nth(row_index)
                    status = await row.locator(".validation-status-label").inner_text()
                    assert status == {"clean": "No issues", "warning": "Warning", "blocking": "Blocking"}[state]
                    for decision in decisions:
                        has_active_issues = state != "clean"
                        backend_required = requires_reason_for_row_decision(
                            decision,
                            has_active_issues=has_active_issues,
                        )
                        frontend_required = await page.evaluate(
                            """([rowIndex, decision]) => {
                                const row = document.querySelectorAll('tr.validation-row')[rowIndex];
                                return requiresReviewNotes(decision, row);
                            }""",
                            arg=[row_index, decision or ""],
                        )
                        assert frontend_required is backend_required, (
                            f"frontend/backend mismatch for {state}/{decision}: "
                            f"frontend={frontend_required}, backend={backend_required}"
                        )
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "notes"),
    [
        ("needs_follow_up", "Hold this row for follow-up."),
        ("reject_row", "Exclude this row from the current export."),
    ],
)
async def test_non_export_dispositions_exclude_row_but_keep_batch(
    e2e_database_and_app,
    decision,
    notes,
):
    """Needs follow-up and Reject row remove only the row from the current export."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = f"contract-export-exclusion-{decision}"
    server = flask_thread = None

    try:
        _seed_batch(
            session,
            batch_id=batch_id,
            rows=[{"name": "Excluded Donor", "email": "excluded@example.com"}],
        )
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                await _save_row_disposition(page, 0, decision, notes=notes)

                preview = build_export_preview(batch_id, {"GIVEBUTTER_DATABASE_URL": database_url})
                assert len(preview.export_rows) == 0, (
                    f"{decision} must exclude the row from the current export; "
                    f"got {len(preview.export_rows)} export rows"
                )

                # Exclusion must not delete the batch or its raw import row.
                assert session.query(ImportBatch).filter_by(id=batch_id).one() is not None
                assert session.query(RawImportRow).filter_by(batch_id=batch_id).count() == 1

                await page.reload()
                await page.wait_for_function(
                    "expected => document.querySelector('tr.validation-row .row-status-dropdown')?.value === expected",
                    arg=decision,
                    timeout=5000,
                )
                assert await page.locator("tr.validation-row .row-status-dropdown").input_value() == decision
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_reject_row_requires_reviewer_and_reason_without_persisting(e2e_database_and_app):
    """Reject requires auditable identity/reason and failed saves create no decision."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-reject-required-fields"
    try:
        [(raw_row, _)] = _seed_batch(
            session,
            batch_id=batch_id,
            rows=[{"name": "Reject Me", "email": "reject@example.com"}],
        )
        session.commit()
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                await row.locator("select.row-status-dropdown").select_option("reject_row")
                modal = page.locator("#record-modal")
                await modal.wait_for(state="visible")
                await modal.locator(".reviewer-name-field").fill("UAT Reviewer")
                await modal.locator('button[id^="save-followup-notes-"]').click()
                assert await modal.is_visible()
                assert "Reason / notes required for Reject row decision" in await modal.inner_text()

                check = Session()
                try:
                    assert check.query(ReviewDecision).filter_by(
                        batch_id=batch_id, raw_import_row_id=raw_row.id,
                    ).count() == 0
                finally:
                    check.close()
            finally:
                await browser.close()
    finally:
        stop_flask_server(locals().get("server"), locals().get("flask_thread"))
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_clearing_saved_human_dispositions_restores_system_defaults(e2e_database_and_app):
    """Clear decision returns clean/issue rows to their distinct authoritative defaults."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-clear-disposition"
    server = flask_thread = None

    try:
        _seed_batch(
            session,
            batch_id=batch_id,
            rows=[
                {"name": "Clean Clear", "email": "clean.clear@example.com"},
                {"name": "Issue Clear", "email": "", "issue": "Missing email address"},
            ],
        )
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                await page.wait_for_selector("tr.validation-row", timeout=5000)

                # Give both rows an explicit saved human disposition first.
                await _save_row_disposition(page, 0, "reject_row", notes="Temporary clean-row decision")
                await _save_row_disposition(page, 1, "reject_row", notes="Temporary issue-row decision")

                for index in (0, 1):
                    # No disposition is the current reviewer-facing reset path;
                    # internal clear_decision audit events remain compatibility data.
                    await _save_row_disposition(
                        page,
                        index,
                        "",
                        reviewer="Contract Reviewer",
                        notes="Reset through No disposition",
                    )

                await page.reload()
                rows = page.locator("tr.validation-row")
                assert await rows.nth(0).locator(".row-status-dropdown").input_value() == "accept_as_is"
                assert await rows.nth(0).locator(".validation-status-label").inner_text() == "No issues"

                issue_value = await rows.nth(1).locator(".row-status-dropdown").input_value()
                assert issue_value in ("", "no_disposition")
                assert await rows.nth(1).locator(".validation-status-label").inner_text() == "Blocking"

                # Clearing is itself an auditable action; it must not mutate raw rows.
                assert session.query(RawImportRow).filter_by(batch_id=batch_id).count() == 2
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_fixing_issue_recomputes_default_readiness_and_export_after_reload(e2e_database_and_app):
    """Editing away the issue transitions the entire workflow back to the clean default."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    batch_id = "contract-recompute-after-edit"
    server = flask_thread = None

    try:
        [(raw_row, _)] = _seed_batch(
            session,
            batch_id=batch_id,
            rows=[{"name": "Repair Donor", "email": "bad-email", "issue": "Invalid email address"}],
        )
        original_raw_email = raw_row.raw_csv_data["email"]
        server, flask_thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                row = page.locator("tr.validation-row").first
                assert await row.locator(".validation-status-label").inner_text() == "Blocking"
                assert await row.locator(".row-status-dropdown").input_value() in ("", "no_disposition")

                email = row.locator('input[data-field="email"]')
                await email.fill("repair.donor@example.com")
                await email.evaluate("el => el.blur()")
                await page.wait_for_function(
                    "() => document.querySelector('tr.validation-row .validation-status-label')?.textContent.trim() === 'No issues'",
                    timeout=5000,
                )
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"

                # System default must not create a human review decision.
                session.expire_all()
                human_dispositions = session.query(ReviewDecision).filter(
                    ReviewDecision.batch_id == batch_id,
                    ReviewDecision.raw_import_row_id == raw_row.id,
                    ReviewDecision.decision.like('row_status:%'),
                ).all()
                assert human_dispositions == []
                correction_history = session.query(ReviewDecision).filter_by(
                    batch_id=batch_id,
                    raw_import_row_id=raw_row.id,
                    decision='accept_issue',
                ).all()
                assert correction_history, 'Append-only autosave correction history must remain'
                assert session.query(RawImportRow).filter_by(id=raw_row.id).one().raw_csv_data["email"] == original_raw_email

                await page.reload()
                row = page.locator("tr.validation-row").first
                await row.wait_for()
                assert await row.locator(".validation-status-label").inner_text() == "No issues"
                assert await row.locator(".row-status-dropdown").input_value() == "accept_as_is"

                preview = build_export_preview(batch_id, {"GIVEBUTTER_DATABASE_URL": database_url})
                assert preview.blocked_count == 0
                assert len(preview.export_rows) == 1

                await page.goto(f"{base_url}/imports/{batch_id}/readiness")
                await page.wait_for_selector("h1", timeout=5000)
                body = await page.inner_text("body")
                assert "Export Blocked" not in body
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, flask_thread)
        session.close()
