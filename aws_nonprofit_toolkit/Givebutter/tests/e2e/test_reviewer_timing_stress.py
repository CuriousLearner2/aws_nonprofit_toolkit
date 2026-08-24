"""Short deterministic timing stress for reviewer-visible state."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.orm import sessionmaker

from scripts.householder import autosave_service
import householder.autosave_service as runtime_autosave_service
from scripts.householder.database_models import ReviewDecision, create_db_engine
from tests.e2e.test_reviewer_transition_fuzz import (
    _complete_visible_projection,
    _history_snapshot,
    _save_decision,
)
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def test_bounded_timing_stress_preserves_newest_review_state(e2e_database_and_app, monkeypatch):
    """Rapid edits, delayed responses, reload, and nearby review changes stay coherent."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    batch_id = "reviewer-timing-stress"
    session = sessionmaker(bind=create_db_engine(database_url))()
    seeded = _seed_batch(
        session,
        batch_id=batch_id,
        rows=[
            {"name": "Stress Clean", "email": "clean@example.com"},
            {"name": "Stress Warning", "email": "warning@gmai.com", "issue": "Email typo", "severity": "warning"},
        ],
    )
    clean_id, warning_id = [item[0].id for item in seeded]
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
                await warning.wait_for()

                autosave_requests = 0
                older_response_arrived = asyncio.Event()
                reload_response_arrived = asyncio.Event()
                in_flight_started = asyncio.Event()
                in_flight_response_arrived = asyncio.Event()

                async def delayed_autosave(route):
                    nonlocal autosave_requests
                    autosave_requests += 1
                    payload = route.request.post_data_json or {}
                    value = next(iter(payload.get("corrected_values", {}).values()), "")
                    response = await route.fetch()
                    if value == "Stress older value":
                        await asyncio.sleep(0.25)
                        older_response_arrived.set()
                    elif value == "Stress in-flight value":
                        in_flight_started.set()
                        await asyncio.sleep(0.25)
                        in_flight_response_arrived.set()
                    elif value == "Stress reload value":
                        await asyncio.sleep(0.25)
                        reload_response_arrived.set()
                    try:
                        await route.fulfill(response=response)
                    except Exception:
                        # Reload may abort the delayed browser response after
                        # the server has already persisted the edit.
                        return

                await page.route("**/autosave", delayed_autosave)
                name = clean.locator('.autosave-field[data-field="name"]')
                for value in ("Stress older value", "Stress newest value", "Stress newest value"):
                    await name.fill(value)
                    await name.press("Tab")
                await page.wait_for_function(
                    "([id]) => document.querySelector(`#validation-row-${id} input[data-field=\\\"name\\\"]`)?.value === 'Stress newest value'",
                    arg=[clean_id],
                )
                await asyncio.wait_for(older_response_arrived.wait(), timeout=5)
                assert autosave_requests >= 3
                assert await name.input_value() == "Stress newest value"

                # A disposition change made while a persisted edit response is
                # still in flight must survive both completions.
                await name.fill("Stress in-flight value")
                await name.press("Tab")
                await asyncio.wait_for(in_flight_started.wait(), timeout=5)
                await _save_decision(page, warning, "needs_follow_up", "Stress in-flight review")
                await asyncio.wait_for(in_flight_response_arrived.wait(), timeout=5)
                assert await name.input_value() == "Stress in-flight value"
                assert await warning.locator(".row-status-dropdown").input_value() == "needs_follow_up"

                # A save response delayed around a reload must not lose the
                # server-persisted value or its reviewer-visible projection.
                await name.fill("Stress reload value")
                await name.press("Tab")
                await page.wait_for_function(
                    "([id]) => document.querySelector(`#validation-row-${id} input[data-field=\\\"name\\\"]`)?.value === 'Stress reload value'",
                    arg=[clean_id],
                )
                await page.reload(wait_until="domcontentloaded")
                await clean.wait_for()
                await asyncio.wait_for(reload_response_arrived.wait(), timeout=5)
                await page.unroute("**/autosave", delayed_autosave)
                clean = page.locator(f"#validation-row-{clean_id}")
                durable = await _complete_visible_projection(page, base_url, batch_id, clean)
                assert durable["fields"]["name"] == "Stress reload value"
                assert durable["status"] == "No issues"
                assert durable["disposition"] == "accept_as_is"
                assert durable["readiness"]
                assert durable["export"]

                # A delayed persistence failure must leave every visible and
                # durable projection unchanged.
                before_failure = await _complete_visible_projection(
                    page, base_url, batch_id, page.locator(f"#validation-row-{clean_id}")
                )

                def fail_autosave(*args, **kwargs):
                    raise ValueError("injected timing persistence failure")

                monkeypatch.setattr(autosave_service, "autosave_row_corrections", fail_autosave)
                monkeypatch.setattr(runtime_autosave_service, "autosave_row_corrections", fail_autosave)
                failed_name = page.locator(f"#validation-row-{clean_id} input[data-field=\"name\"]")
                await failed_name.fill("Stress failed value")
                await failed_name.press("Tab")
                assert await failed_name.input_value() == "Stress failed value"
                await page.locator(f"#validation-row-{clean_id} .autosave-status").filter(
                    has_text="Error"
                ).first.wait_for(state="visible", timeout=10000)
                after_failure = await _complete_visible_projection(
                    page, base_url, batch_id, page.locator(f"#validation-row-{clean_id}")
                )
                assert after_failure == before_failure
                monkeypatch.undo()
                await page.reload()
                await page.locator(f"#validation-row-{clean_id}").wait_for()
                after_failure_reload = await _complete_visible_projection(
                    page, base_url, batch_id, page.locator(f"#validation-row-{clean_id}")
                )
                assert after_failure_reload == before_failure

                # Two distinct nearby review changes are retained once each;
                # the repeated edit above must not create review history.
                await _save_decision(page, warning, "needs_follow_up", "Stress follow-up")
                await _save_decision(page, warning, "reject_row", "Stress reject")
                visible_history = await _history_snapshot(page, warning)
                assert len(visible_history) == 3
                assert "Reject row" in visible_history[0]
                assert "Stress reject" in visible_history[0]
                assert "Needs follow-up" in visible_history[1]
                assert "Stress follow-up" in visible_history[1] or "Stress in-flight review" in visible_history[1]
                assert len(visible_history) == len(set(visible_history))
                await page.reload()
                warning = page.locator(f"#validation-row-{warning_id}")
                await warning.wait_for()
                reloaded_visible_history = await _history_snapshot(page, warning)
                assert reloaded_visible_history == visible_history
                state = await page.request.get(f"{base_url}/imports/{batch_id}/row-decision/{warning_id}")
                payload = await state.json()
                assert payload["decision"] == "reject_row"
                assert [entry["decision"] for entry in payload["history"][:3]] == [
                    "reject_row",
                    "needs_follow_up",
                    "needs_follow_up",
                ]
                assert len(payload["history"]) == 3
                assert len(payload["history"]) == len({entry["decision_id"] for entry in payload["history"]})
                session = sessionmaker(bind=create_db_engine(database_url))()
                try:
                    decisions = session.query(ReviewDecision).filter(
                        ReviewDecision.raw_import_row_id == warning_id,
                        ReviewDecision.decision.like("row_status:%"),
                    ).all()
                    assert len(decisions) == 3
                finally:
                    session.close()
            finally:
                await browser.close()
    finally:
        stop_flask_server(server, thread)
