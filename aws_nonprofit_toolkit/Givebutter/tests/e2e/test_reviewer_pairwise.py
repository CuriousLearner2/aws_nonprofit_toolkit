"""Compact pairwise reviewer-projection coverage on real application paths."""

from __future__ import annotations

import csv
import io
import re

import pytest
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import create_db_engine
from tests.e2e.test_pre_uat_reviewer_journey import (
    CSV_WITH_ADDRESS,
    CSV_WITHOUT_ADDRESS,
    _visible_export_transaction_ids,
    _visible_transaction_ids,
)
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)
from tests.unit.test_row_state_transition_matrix import (
    _assert_visible_projection,
    _edit,
    _history_snapshot,
    _reset_decision,
    _save_decision,
)


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

# This is the covering set: every editable field, status, human disposition,
# address capability, severity filter, disposition filter, reload state, and
# gating state appears in at least one real browser scenario.
PAIRWISE_CASES = (
    ("clean-name", "name", "No issues", "accept_as_is", "all", "accept_as_is", True, "address-present"),
    ("warning-email", "email", "Warning", "needs_follow_up", "Warning", "needs_follow_up", False, "address-present"),
    ("blocking-phone", "phone", "Blocking", "reject_row", "Blocking", "reject_row", False, "address-present"),
    ("warning-amount", "amount", "Warning", "accept_as_is", "Blocking+Warning", "accept_as_is", True, "address-present"),
    ("blocking-address", "address", "Blocking", "", "Blocking", "none", False, "address-present"),
    ("clean-date", "date", "No issues", "accept_as_is", "No issues", "accept_as_is", True, "address-present"),
)

PAIRWISE_SOURCE_CASES = (
    ("address-present", CSV_WITH_ADDRESS, True),
    ("address-absent", CSV_WITHOUT_ADDRESS, False),
)


def _row(page, row_id: int):
    return page.locator(f"#validation-row-{row_id}")


async def _assert_visible_set(page, expected: set[str]) -> None:
    assert set(await _visible_transaction_ids(page)) == expected


async def _upload_csv(page, base_url, tmp_path, content: str, filename: str) -> str:
    csv_path = tmp_path / filename
    csv_path.write_text(content, encoding="utf-8")
    await page.goto(base_url)
    previous_review_href = await page.locator("#topReviewNav").get_attribute("href")
    await page.locator('input[type="file"]').set_input_files(str(csv_path))
    await page.wait_for_function(
        "({ previous }) => { const href = document.querySelector('#topReviewNav')?.getAttribute('href') || ''; return href.includes('/imports/') && href !== previous; }",
        arg={"previous": previous_review_href},
        timeout=15000,
    )
    review_href = await page.locator("#topReviewNav").get_attribute("href")
    assert review_href and "/validation" in review_href
    await page.goto(f"{base_url}{review_href}")
    await page.wait_for_selector("tr.validation-row", timeout=10000)
    return review_href.split("/imports/", 1)[1].split("/", 1)[0]


async def test_pairwise_reviewer_projection_case(e2e_database_and_app):
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = "pairwise-reviewer-projection"
    seeded = _seed_batch(
        session,
        batch_id=batch_id,
        rows=[
            {"name": "Pair Clean Name", "email": "pair-clean-name@example.com"},
            {"name": "Pair Warning Email", "email": "pair-warning-email@gmai.com", "issue": "Email typo", "severity": "warning"},
            {"name": "Pair Blocking Phone", "email": "pair-blocking-phone@", "issue": "Invalid email", "severity": "error"},
            {"name": "Pair Warning Amount", "email": "pair-warning-amount@gmai.com", "issue": "Email typo", "severity": "warning"},
            {"name": "Pair Blocking Address", "email": "pair-blocking-address@", "issue": "Invalid email", "severity": "error"},
            {"name": "Pair Clean Date", "email": "pair-clean-date@example.com"},
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
                await page.locator("tr.validation-row").first.wait_for()
                rows = {
                    "clean-name": _row(page, row_ids[0]),
                    "clean-date": _row(page, row_ids[5]),
                    "warning-email": _row(page, row_ids[1]),
                    "warning-amount": _row(page, row_ids[3]),
                    "blocking-phone": _row(page, row_ids[2]),
                    "blocking-address": _row(page, row_ids[4]),
                }
                values = {
                    "name": "Pairwise Name",
                    "email": "pairwise@gmal.com",
                    "phone": "+1 415 555 2671",
                    "amount": "125.00",
                    "address": "25 Pairwise Street",
                    "date": "2026-09-15",
                }

                for current in PAIRWISE_CASES:
                    current_label, current_field, current_status, current_disposition, _, _, _, source_capability = current
                    assert source_capability == "address-present"
                    assert await page.locator("th", has_text="Address").count() == 1
                    await _edit(page, rows[current_label], current_field, values[current_field])
                    await _assert_visible_projection(
                        page, base_url, batch_id, rows[current_label],
                        status=current_status,
                        disposition="accept_as_is" if current_status == "No issues" else "",
                        ready=False,
                    )

                await _assert_visible_projection(
                    page, base_url, batch_id, rows["clean-name"],
                    status="No issues", disposition="accept_as_is", ready=False,
                )
                await _assert_visible_projection(
                    page, base_url, batch_id, rows["clean-date"],
                    status="No issues", disposition="accept_as_is", ready=False,
                )
                await _save_decision(page, rows["warning-email"], "needs_follow_up", "Pairwise follow-up")
                await _assert_visible_projection(
                    page, base_url, batch_id, rows["warning-email"],
                    status="Warning", disposition="needs_follow_up", ready=False,
                )
                await _save_decision(page, rows["warning-amount"], "accept_as_is", "Pairwise accepted")
                await _assert_visible_projection(
                    page, base_url, batch_id, rows["warning-amount"],
                    status="Warning", disposition="accept_as_is", ready=False,
                )
                await _save_decision(page, rows["blocking-phone"], "reject_row", "Pairwise rejected")
                await _assert_visible_projection(
                    page, base_url, batch_id, rows["blocking-phone"],
                    status="Blocking", disposition="reject_row", ready=False,
                )
                await _assert_visible_projection(
                    page, base_url, batch_id, rows["blocking-address"],
                    status="Blocking", disposition="", ready=False,
                )

                expected_reviewed = {
                    "clean-name": ("No issues", "accept_as_is"),
                    "warning-email": ("Warning", "needs_follow_up"),
                    "blocking-phone": ("Blocking", "reject_row"),
                    "warning-amount": ("Warning", "accept_as_is"),
                    "blocking-address": ("Blocking", ""),
                    "clean-date": ("No issues", "accept_as_is"),
                }
                for current_label, (current_status, current_disposition) in expected_reviewed.items():
                    await _assert_visible_projection(
                        page, base_url, batch_id, rows[current_label],
                        status=current_status,
                        disposition=current_disposition,
                        ready=False,
                    )

                expected_all = {
                    f"txn-{batch_id}-1", f"txn-{batch_id}-2", f"txn-{batch_id}-3",
                    f"txn-{batch_id}-4", f"txn-{batch_id}-5", f"txn-{batch_id}-6",
                }
                await page.locator('[data-row-status-filter="all"]').click()
                await _assert_visible_set(page, expected_all)
                await page.locator('[data-row-status-filter="Blocking"]').click()
                await _assert_visible_set(page, {f"txn-{batch_id}-3", f"txn-{batch_id}-5"})
                await page.locator('[data-row-status-filter="all"]').click()
                await page.locator('[data-row-status-filter="Warning"]').click()
                await _assert_visible_set(page, {f"txn-{batch_id}-2", f"txn-{batch_id}-4"})
                await page.locator('[data-row-status-filter="Blocking"]').click()
                await _assert_visible_set(page, {f"txn-{batch_id}-2", f"txn-{batch_id}-3", f"txn-{batch_id}-4", f"txn-{batch_id}-5"})
                await page.locator('[data-row-status-filter="all"]').click()
                await page.locator('[data-row-status-filter="No issues"]').click()
                await _assert_visible_set(page, {f"txn-{batch_id}-1", f"txn-{batch_id}-6"})
                await page.locator('[data-row-status-filter="all"]').click()

                for value, expected in {
                    "none": {f"txn-{batch_id}-5"},
                    "accept_as_is": {f"txn-{batch_id}-1", f"txn-{batch_id}-4", f"txn-{batch_id}-6"},
                    "needs_follow_up": {f"txn-{batch_id}-2"},
                    "reject_row": {f"txn-{batch_id}-3"},
                }.items():
                    await page.locator("#disposition-filter").select_option(value)
                    await _assert_visible_set(page, expected)
                await page.locator("#disposition-filter").select_option("all")

                status_sets = {
                    "all": {f"txn-{batch_id}-{index}" for index in range(1, 7)},
                    "Blocking": {f"txn-{batch_id}-3", f"txn-{batch_id}-5"},
                    "Warning": {f"txn-{batch_id}-2", f"txn-{batch_id}-4"},
                    "Blocking+Warning": {f"txn-{batch_id}-2", f"txn-{batch_id}-3", f"txn-{batch_id}-4", f"txn-{batch_id}-5"},
                    "No issues": {f"txn-{batch_id}-1", f"txn-{batch_id}-6"},
                }
                disposition_sets = {
                    "none": {f"txn-{batch_id}-5"},
                    "accept_as_is": {f"txn-{batch_id}-1", f"txn-{batch_id}-4", f"txn-{batch_id}-6"},
                    "needs_follow_up": {f"txn-{batch_id}-2"},
                    "reject_row": {f"txn-{batch_id}-3"},
                }
                row_transaction_ids = {
                    label: (await row.locator("td").first.inner_text()).strip()
                    for label, row in rows.items()
                }
                expected_export_ids = {
                    row_transaction_ids[label]
                    for label, _, _, _, _, _, export_eligible, _ in PAIRWISE_CASES
                    if export_eligible
                }
                expected_excluded_export_ids = set(row_transaction_ids.values()) - expected_export_ids

                # Bind every declared case's filter pair to the row assertion
                # that proves it; these are the same visible controls above.
                for current_label, _, _, _, current_status_filter, current_disposition_filter, export_eligible, source_capability in PAIRWISE_CASES:
                    assert source_capability == "address-present"
                    assert await page.locator("th", has_text="Address").count() == 1
                    await page.locator('[data-row-status-filter="all"]').click()
                    await page.locator("#disposition-filter").select_option("all")
                    if current_status_filter == "Blocking+Warning":
                        await page.locator('[data-row-status-filter="Warning"]').click()
                        await page.locator('[data-row-status-filter="Blocking"]').click()
                    elif current_status_filter != "all":
                        await page.locator(f'[data-row-status-filter="{current_status_filter}"]').click()
                    included = set(await _visible_transaction_ids(page))
                    assert included == status_sets[current_status_filter]
                    assert status_sets["all"] - included == status_sets["all"] - status_sets[current_status_filter]
                    assert await rows[current_label].is_visible()
                    await page.locator('[data-row-status-filter="all"]').click()
                    await page.locator("#disposition-filter").select_option(current_disposition_filter)
                    included = set(await _visible_transaction_ids(page))
                    assert included == disposition_sets[current_disposition_filter]
                    assert status_sets["all"] - included == status_sets["all"] - disposition_sets[current_disposition_filter]
                    assert await rows[current_label].is_visible()
                    await page.locator("#disposition-filter").select_option("all")
                    visible_export_ids = set(await _visible_export_transaction_ids(page))
                    assert visible_export_ids == expected_export_ids
                    assert set(row_transaction_ids.values()) - visible_export_ids == expected_excluded_export_ids
                    assert (row_transaction_ids[current_label] in visible_export_ids) is export_eligible
                await page.locator("#disposition-filter").select_option("all")

                review_expectations = {
                    "warning-email": "Pairwise follow-up",
                    "warning-amount": "Pairwise accepted",
                    "blocking-phone": "Pairwise rejected",
                    "blocking-address": None,
                    "clean-name": None,
                    "clean-date": None,
                }
                history_before_reload = {}
                for current_label, expected_reason in review_expectations.items():
                    history = await _history_snapshot(page, rows[current_label])
                    assert len(history) == (1 if expected_reason else 0)
                    assert len(history) == len(set(history))
                    if expected_reason:
                        lines = history[0].splitlines()
                        assert lines[0] == {
                            "warning-email": "Needs follow-up",
                            "warning-amount": "Accept as-is",
                            "blocking-phone": "Reject row",
                        }[current_label]
                        assert lines[1] == expected_reason
                        reviewer, timestamp = lines[2].split(" · ", 1)
                        assert reviewer == "Matrix Reviewer"
                        assert re.fullmatch(r"20\d\d-\d\d-\d\dT[^ ]+", timestamp)
                    timestamps = [event.splitlines()[-1].split(" · ", 1)[1] for event in history]
                    assert timestamps == sorted(timestamps, reverse=True)
                    history_before_reload[current_label] = history

                await page.goto(f"{base_url}/imports/{batch_id}/readiness")
                assert "Export Blocked" in await page.locator("body").inner_text()
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                await page.locator("tr.validation-row").first.wait_for()
                await _save_decision(page, rows["blocking-address"], "accept_as_is", "Pairwise resolved")
                await _assert_visible_projection(
                    page, base_url, batch_id, rows["blocking-address"],
                    status="Blocking", disposition="accept_as_is", ready=True,
                )
                history = await _history_snapshot(page, rows["blocking-address"])
                assert len(history) == 1
                assert len(history) == len(set(history))
                assert history[0].splitlines()[0] == "Accept as-is"
                assert history[0].splitlines()[1] == "Pairwise resolved"
                reviewer, timestamp = history[0].splitlines()[2].split(" · ", 1)
                assert reviewer == "Matrix Reviewer"
                assert re.fullmatch(r"20\d\d-\d\d-\d\dT[^ ]+", timestamp)
                await _reset_decision(page, rows["blocking-address"])
                await _assert_visible_projection(
                    page, base_url, batch_id, rows["blocking-address"],
                    status="Blocking", disposition="", ready=False,
                )
                await _save_decision(page, rows["blocking-address"], "accept_as_is", "Pairwise resolved again")
                history = await _history_snapshot(page, rows["blocking-address"])
                assert len(history) == 3
                assert len(history) == len(set(history))
                assert history[0].splitlines()[:2] == ["Accept as-is", "Pairwise resolved again"]
                assert history[1].splitlines()[:2] == [
                    "Decision cleared by reviewer",
                    "The prior human disposition was reset; the current state follows validation.",
                ]
                assert history[2].splitlines()[:2] == ["Accept as-is", "Pairwise resolved"]
                for event in history:
                    reviewer, timestamp = event.splitlines()[-1].split(" · ", 1)
                    assert reviewer == "Matrix Reviewer"
                    assert re.fullmatch(r"20\d\d-\d\d-\d\dT[^ ]+", timestamp)
                timestamps = [event.splitlines()[-1].split(" · ", 1)[1] for event in history]
                assert timestamps == sorted(timestamps, reverse=True)
                history_before_reload["blocking-address"] = history
                visible_eligible_ids = await _visible_export_transaction_ids(page)
                assert visible_eligible_ids == {
                    f"txn-{batch_id}-1", f"txn-{batch_id}-4",
                    f"txn-{batch_id}-5", f"txn-{batch_id}-6",
                }
                await page.locator("#approve-file-btn").click()
                await page.wait_for_url("**/dashboard", timeout=15000)
                await page.goto(f"{base_url}/imports/{batch_id}/exports")
                await page.locator("#generate-export-btn").click()
                export_link = page.locator('[data-action="download-export"]').last
                await export_link.wait_for(state="visible", timeout=15000)
                export_response = await page.request.get(f"{base_url}{await export_link.get_attribute('href')}")
                assert export_response.ok
                exported_ids = {
                    row["transaction_id"]
                    for row in csv.DictReader(io.StringIO(await export_response.text()))
                }
                assert exported_ids == visible_eligible_ids
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                await page.locator("tr.validation-row").first.wait_for()
                await page.reload()
                display_values = {
                    "name": values["name"],
                    "email": values["email"],
                    "phone": "+1 (415) 555-2671",
                    "amount": "$125.00",
                    "address": values["address"],
                    "date": values["date"],
                }
                for current_label, current_field, current_status, current_disposition, _, _, _, source_capability in PAIRWISE_CASES:
                    assert source_capability == "address-present"
                    assert await page.locator("th", has_text="Address").count() == 1
                    expected_disposition = current_disposition or "accept_as_is"
                    expected_ready = True
                    row = rows[current_label]
                    await _assert_visible_projection(
                        page, base_url, batch_id, row,
                        status=current_status,
                        disposition=expected_disposition,
                        ready=expected_ready,
                    )
                    assert await row.locator(f'.autosave-field[data-field="{current_field}"]').input_value() == display_values[current_field]
                    if expected_disposition in {"needs_follow_up", "reject_row", "accept_as_is"} and current_status != "No issues":
                        meta = await row.locator(".row-disposition-meta").inner_text()
                        expected_reason = review_expectations[current_label]
                        if current_label == "blocking-address":
                            expected_reason = "Pairwise resolved again"
                        reviewer, reason, _timestamp = meta.split(" · ", 2)
                        assert reviewer == "Matrix Reviewer"
                        assert reason == expected_reason
                    history_after_reload = await _history_snapshot(page, row)
                    assert history_after_reload == history_before_reload[current_label]
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)


async def test_pairwise_source_without_address_is_hidden(e2e_database_and_app, tmp_path):
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    _seed_batch(
        session,
        batch_id="pairwise-readiness-probe",
        rows=[{"name": "Readiness Probe", "email": "probe@example.com"}],
    )
    session.close()
    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, "pairwise-readiness-probe")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1440, "height": 1000})
            try:
                for source_label, content, address_visible in PAIRWISE_SOURCE_CASES:
                    await _upload_csv(page, base_url, tmp_path, content, f"pairwise-{source_label}.csv")
                    assert (await page.locator("th", has_text="Address").count() == 1) is address_visible
                    assert (await page.locator('input[data-field="address"]').count() == 0) is (not address_visible)
                    await page.reload()
                    assert (await page.locator("th", has_text="Address").count() == 1) is address_visible
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
