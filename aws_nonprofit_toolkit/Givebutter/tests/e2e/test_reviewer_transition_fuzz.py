"""Bounded, deterministic reviewer-transition fuzzing on real browser paths."""

from __future__ import annotations

import random

import pytest
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import create_db_engine
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)
from tests.unit.test_row_state_transition_matrix import (
    _complete_visible_projection,
    _edit,
    _assert_visible_projection,
    _history_snapshot,
    _reset_decision,
    _save_decision,
)


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]

SEEDS = (17, 31)
FIELDS = ("name", "email", "phone", "amount", "address", "date")


async def _names(page) -> set[str]:
    rows = page.locator("tr.validation-row")
    names = set()
    for index in range(await rows.count()):
        row = rows.nth(index)
        if await row.is_visible():
            names.add((await row.locator('.autosave-field[data-field="name"]').input_value()).strip())
    return names


async def _assert_filters(page, *, expected: dict[str, set[str]]) -> None:
    async def check_filter(expected_names):
        assert await _names(page) == expected_names

    await page.locator('[data-row-status-filter="all"]').click()
    await check_filter(expected["all"])
    await page.locator("#disposition-filter").select_option("all")
    await check_filter(expected["all"])

    await page.locator('[data-row-status-filter="Blocking"]').click()
    await check_filter(expected["Blocking"])
    await page.locator('[data-row-status-filter="all"]').click()
    await check_filter(expected["all"])
    await page.locator('[data-row-status-filter="Warning"]').click()
    await check_filter(expected["Warning"])
    await page.locator('[data-row-status-filter="Blocking"]').click()
    await check_filter(expected["Blocking+Warning"])
    await page.locator('[data-row-status-filter="all"]').click()
    await check_filter(expected["all"])
    await page.locator('[data-row-status-filter="No issues"]').click()
    await check_filter(expected["No issues"])

    await page.locator('[data-row-status-filter="all"]').click()
    await check_filter(expected["all"])
    await page.locator("#disposition-filter").select_option("none")
    await check_filter(expected["No disposition"])
    await page.locator("#disposition-filter").select_option("accept_as_is")
    await check_filter(expected["Accept as-is"])
    await page.locator("#disposition-filter").select_option("needs_follow_up")
    await check_filter(expected["Needs follow-up"])
    await page.locator("#disposition-filter").select_option("reject_row")
    await check_filter(expected["Reject row"])
    await page.locator("#disposition-filter").select_option("all")
    await check_filter(expected["all"])


async def _assert_search(page, expected_name: str, expected_after_clear: set[str]) -> None:
    search = page.locator("#search-records")
    await search.fill(expected_name.split()[1])
    assert await _names(page) == {expected_name}
    await search.fill("")
    assert await _names(page) == expected_after_clear


async def _assert_after_mutation(page, base_url, batch_id, row, *, status, disposition, ready):
    """Run the accepted full row/readiness projection helper after a mutation."""
    await _assert_visible_projection(
        page, base_url, batch_id, row,
        status=status, disposition=disposition, ready=ready,
    )
    snapshot = await _complete_visible_projection(page, base_url, batch_id, row)
    filter_key = f"disposition:{disposition or 'none'}"
    row_transaction_id = (await row.locator("td").first.inner_text()).strip()
    assert row_transaction_id in snapshot["filters"][filter_key]
    return snapshot


async def _assert_complete_history(page, row, *, expected_fragments):
    history = await _history_snapshot(page, row)
    assert len(history) >= len(expected_fragments)
    assert len(history) == len(set(history)), "visible history contains duplicate events"
    for fragment in expected_fragments:
        assert any(fragment in entry for entry in history), f"missing history event: {fragment}"
    import re

    timestamps = []
    for entry in history:
        match = re.search(r"20\d\d-\d\d-\d\dT[^\s]+", entry)
        assert match, f"history entry has no timestamp: {entry}"
        timestamps.append(match.group(0))
    assert timestamps == sorted(timestamps, reverse=True)
    return history


@pytest.mark.parametrize("seed", SEEDS)
async def test_bounded_reviewer_transition_fuzz(e2e_database_and_app, seed: int):
    """Run a reproducible bounded sequence and report seed/actions on failure."""
    from playwright.async_api import async_playwright

    rng = random.Random(seed)
    actions: list[str] = []
    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = f"reviewer-fuzz-{seed}"
    seeded = _seed_batch(
        session,
        batch_id=batch_id,
        rows=[
            {"name": "Fuzz Clean", "email": "clean@example.com"},
            {
                "name": "Fuzz Warning",
                "email": "warning@gmai.com",
                "issue": "Email typo",
                "severity": "warning",
            },
            {
                "name": "Fuzz Blocking",
                "email": "blocking@",
                "issue": "Invalid email",
                "severity": "error",
            },
        ],
    )
    clean_id, warning_id, blocking_id = (item[0].id for item in seeded)
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
                clean = page.locator(f"#validation-row-{clean_id}")
                warning = page.locator(f"#validation-row-{warning_id}")
                blocking = page.locator(f"#validation-row-{blocking_id}")

                # Randomize only the safe order of the six real edit paths.
                field_values = {
                    "name": f"Fuzz Clean {seed}",
                    "email": f"fuzz{seed}@example.com",
                    "phone": "+1 415 555 2671",
                    "amount": "125.00",
                    "address": f"{seed} Fuzz Street",
                    "date": "2026-09-15",
                }
                fields = list(FIELDS)
                rng.shuffle(fields)
                for field in fields:
                    actions.append(f"edit clean {field}")
                    await _edit(page, clean, field, field_values[field])
                    await _assert_after_mutation(
                        page, base_url, batch_id, clean,
                        status="No issues", disposition="accept_as_is", ready=False,
                    )

                async def warning_lifecycle():
                    actions.append("save warning Needs follow-up")
                    await _save_decision(page, warning, "needs_follow_up", f"Fuzz follow-up {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, warning, status="Warning", disposition="needs_follow_up", ready=None)
                    actions.append("change warning Needs follow-up -> Reject row")
                    await _save_decision(page, warning, "reject_row", f"Fuzz reject warning {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, warning, status="Warning", disposition="reject_row", ready=None)
                    actions.append("reset warning to No disposition")
                    await _reset_decision(page, warning)
                    await _assert_after_mutation(page, base_url, batch_id, warning, status="Warning", disposition="", ready=None)
                    actions.append("save warning Accept as-is")
                    await _save_decision(page, warning, "accept_as_is", f"Fuzz accept warning {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, warning, status="Warning", disposition="accept_as_is", ready=None)
                    actions.append("edit warning name; invalidate human disposition")
                    await _edit(page, warning, "name", f"Fuzz Warning Edited {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, warning, status="Warning", disposition="", ready=None)

                async def blocking_lifecycle():
                    actions.append("save blocking Reject row")
                    await _save_decision(page, blocking, "reject_row", f"Fuzz reject {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, blocking, status="Blocking", disposition="reject_row", ready=None)
                    actions.append("change blocking Reject row -> Needs follow-up")
                    await _save_decision(page, blocking, "needs_follow_up", f"Fuzz follow-up blocking {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, blocking, status="Blocking", disposition="needs_follow_up", ready=None)
                    actions.append("reset blocking to No disposition")
                    await _reset_decision(page, blocking)
                    await _assert_after_mutation(page, base_url, batch_id, blocking, status="Blocking", disposition="", ready=False)
                    actions.append("save blocking Reject row again")
                    await _save_decision(page, blocking, "reject_row", f"Fuzz reject again {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, blocking, status="Blocking", disposition="reject_row", ready=None)
                    actions.append("edit blocking name; invalidate human disposition")
                    await _edit(page, blocking, "name", f"Fuzz Blocking Edited {seed}")
                    await _assert_after_mutation(page, base_url, batch_id, blocking, status="Blocking", disposition="", ready=False)

                if seed == 17:
                    await warning_lifecycle()
                    await blocking_lifecycle()
                else:
                    await blocking_lifecycle()
                    await warning_lifecycle()

                actions.append("failed blocking email edit")
                before_failure = await _complete_visible_projection(page, base_url, batch_id, blocking)
                email = blocking.locator('.autosave-field[data-field="email"]')
                await email.fill("not-an-email")
                await email.press("Tab")
                assert await email.input_value() == "not-an-email"
                await blocking.locator(".autosave-status").filter(has_text="Error").first.wait_for(
                    state="visible", timeout=10000
                )
                after_failure = await _complete_visible_projection(page, base_url, batch_id, blocking)
                assert after_failure == before_failure
                assert after_failure["fields"] == before_failure["fields"]
                assert after_failure["issues"] == before_failure["issues"]
                assert after_failure["status"] == before_failure["status"]
                assert after_failure["disposition"] == before_failure["disposition"]
                assert after_failure["readiness"] == before_failure["readiness"]
                assert after_failure["export"] == before_failure["export"]
                assert after_failure["filters"] == before_failure["filters"]
                assert after_failure["history"] == before_failure["history"]

                actions.append("search Fuzz Warning")
                await _assert_search(
                    page,
                    f"Fuzz Warning Edited {seed}",
                    {
                        f"Fuzz Clean {seed}",
                        f"Fuzz Warning Edited {seed}",
                        f"Fuzz Blocking Edited {seed}",
                    },
                )
                actions.append("filter Blocking/Warning/No issues/dispositions")
                await _assert_filters(
                    page,
                    expected={
                        "all": {"Fuzz Clean %s" % seed, "Fuzz Warning Edited %s" % seed, "Fuzz Blocking Edited %s" % seed},
                        "Blocking": {"Fuzz Blocking Edited %s" % seed},
                        "Warning": {"Fuzz Warning Edited %s" % seed},
                        "Blocking+Warning": {"Fuzz Blocking Edited %s" % seed, "Fuzz Warning Edited %s" % seed},
                        "No issues": {"Fuzz Clean %s" % seed},
                        "No disposition": {"Fuzz Warning Edited %s" % seed, "Fuzz Blocking Edited %s" % seed},
                        "Accept as-is": {"Fuzz Clean %s" % seed},
                        "Needs follow-up": set(),
                        "Reject row": set(),
                    },
                )

                await _assert_complete_history(
                    page, warning,
                    expected_fragments=["Fuzz follow-up", "Fuzz reject warning", "Decision cleared"],
                )
                await _assert_complete_history(
                    page, blocking,
                    expected_fragments=["Fuzz reject", "Fuzz follow-up blocking", "Decision cleared"],
                )

                before_reload_warning = await _complete_visible_projection(
                    page, base_url, batch_id, warning,
                )
                before_reload_blocking = await _complete_visible_projection(
                    page, base_url, batch_id, blocking,
                )

                actions.append("reload/fresh request")
                await page.reload()
                await rows.nth(2).wait_for()
                warning = page.locator(f"#validation-row-{warning_id}")
                blocking = page.locator(f"#validation-row-{blocking_id}")
                after_reload_warning = await _complete_visible_projection(
                    page, base_url, batch_id, warning,
                )
                after_reload_blocking = await _complete_visible_projection(
                    page, base_url, batch_id, blocking,
                )
                assert after_reload_warning == before_reload_warning
                assert after_reload_blocking == before_reload_blocking
                await _assert_complete_history(
                    page, warning,
                    expected_fragments=["Fuzz follow-up", "Fuzz reject warning", "Decision cleared"],
                )
            except Exception as error:
                raise AssertionError(f"seed={seed}; actions={actions}; failure={error}") from error
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
