"""Small Hypothesis state-machine coverage over real reviewer browser paths."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from hypothesis import HealthCheck, settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, precondition, rule
from sqlalchemy.orm import sessionmaker

from scripts.householder.database_models import create_db_engine
from tests.e2e.test_reviewer_transition_fuzz import (
    _assert_after_mutation,
    _complete_visible_projection,
    _edit,
    _reset_decision,
    _save_decision,
)
from tests.e2e.test_validation_disposition_contract import _seed_batch
from tests.e2e.test_validation_review_dom import (
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)

pytestmark = [pytest.mark.e2e]

FIELDS = ("name", "email", "phone", "amount", "address", "date")
DECISIONS = ("accept_as_is", "needs_follow_up", "reject_row")


class ReviewerStateMachine(RuleBasedStateMachine):
    """Hypothesis shrinks real UI action sequences to a minimal failure."""

    database_url = None
    flask_app = None

    def __init__(self):
        super().__init__()
        from playwright.async_api import async_playwright

        self.loop = asyncio.new_event_loop()
        self.batch_id = f"hypothesis-reviewer-{uuid.uuid4().hex[:10]}"
        self.server = self.thread = None
        session = sessionmaker(bind=create_db_engine(self.database_url))()
        try:
            seeded = _seed_batch(
                session,
                batch_id=self.batch_id,
                rows=[
                    {"name": "Property Clean", "email": "clean@example.com"},
                    {
                        "name": "Property Warning",
                        "email": "warning@gmai.com",
                        "issue": "Email typo",
                        "severity": "warning",
                    },
                    {
                        "name": "Property Blocking",
                        "email": "blocking@",
                        "issue": "Invalid email",
                        "severity": "error",
                    },
                ],
            )
            self.row_ids = [item[0].id for item in seeded]
        finally:
            session.close()

        self.server, self.thread, self.base_url = start_flask_server(self.flask_app)
        wait_for_flask_ready(self.base_url, self.batch_id)
        self.loop.run_until_complete(self._open_browser(async_playwright))
        self.warning_decision = None
        self.blocking_decision = None
        self.last_projection = None

    async def _open_browser(self, async_playwright):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page(viewport={"width": 1440, "height": 1000})
        await self.page.goto(f"{self.base_url}/imports/{self.batch_id}/validation")
        await self.page.locator("tr.validation-row").nth(2).wait_for()

    def _run(self, awaitable):
        return self.loop.run_until_complete(awaitable)

    def _row(self, index):
        return self.page.locator(f"#validation-row-{self.row_ids[index]}")

    async def _assert_row(self, index, *, status, disposition):
        row = self._row(index)
        ready = False if index == 2 and not disposition else None
        self.last_projection = await _assert_after_mutation(
            self.page,
            self.base_url,
            self.batch_id,
            row,
            status=status,
            disposition=disposition,
            ready=ready,
        )

    @initialize()
    def initial_projection(self):
        self._run(self._assert_row(0, status="No issues", disposition="accept_as_is"))

    @rule(field=st.sampled_from(FIELDS))
    def edit_clean_field(self, field):
        values = {
            "name": "Property Clean Edited",
            "email": "property-clean@example.com",
            "phone": "+1 415 555 2671",
            "amount": "125.00",
            "address": "25 Property Street",
            "date": "2026-09-15",
        }
        self._run(_edit(self.page, self._row(0), field, values[field]))
        self._run(self._assert_row(0, status="No issues", disposition="accept_as_is"))

    @rule(decision=st.sampled_from(DECISIONS))
    def save_warning_disposition(self, decision):
        self._run(_save_decision(self.page, self._row(1), decision, f"Hypothesis {decision}"))
        self.warning_decision = decision
        self._run(self._assert_row(1, status="Warning", disposition=decision))

    @precondition(lambda self: self.warning_decision is not None)
    @rule(decision=st.sampled_from(DECISIONS))
    def change_warning_disposition(self, decision):
        self._run(_save_decision(self.page, self._row(1), decision, f"Hypothesis changed {decision}"))
        self.warning_decision = decision
        self._run(self._assert_row(1, status="Warning", disposition=decision))

    @precondition(lambda self: self.warning_decision is not None)
    @rule()
    def reset_warning_disposition(self):
        self._run(_reset_decision(self.page, self._row(1)))
        self.warning_decision = None
        self._run(self._assert_row(1, status="Warning", disposition=""))

    @rule(decision=st.sampled_from(DECISIONS))
    def save_blocking_disposition(self, decision):
        self._run(_save_decision(self.page, self._row(2), decision, f"Hypothesis {decision}"))
        self.blocking_decision = decision
        self._run(self._assert_row(2, status="Blocking", disposition=decision))

    @precondition(lambda self: self.blocking_decision is not None)
    @rule()
    def reset_blocking_disposition(self):
        self._run(_reset_decision(self.page, self._row(2)))
        self.blocking_decision = None
        self._run(self._assert_row(2, status="Blocking", disposition=""))

    @rule()
    def failed_blocking_edit_preserves_projection(self):
        row = self._row(2)
        before = self._run(_complete_visible_projection(self.page, self.base_url, self.batch_id, row))
        email = row.locator('.autosave-field[data-field="email"]')
        self._run(email.fill("not-an-email"))
        self._run(email.press("Tab"))
        self._run(row.locator(".autosave-status").filter(has_text="Error").first.wait_for(state="visible", timeout=10000))
        after = self._run(_complete_visible_projection(self.page, self.base_url, self.batch_id, row))
        assert after == before

    @rule()
    def search_clear_and_reload(self):
        search = self.page.locator("#search-records")
        self._run(search.fill("Warning"))
        visible = self.page.locator("tr.validation-row:visible")
        assert self._run(visible.count()) == 1
        assert self._run(visible.first.locator('.autosave-field[data-field="name"]').input_value()) == "Property Warning"
        self._run(search.fill(""))
        assert self._run(self.page.locator("tr.validation-row:visible").count()) == 3
        before = self._run(_complete_visible_projection(self.page, self.base_url, self.batch_id, self._row(1)))
        self._run(self.page.reload())
        self._run(self.page.locator("tr.validation-row").nth(2).wait_for())
        after = self._run(_complete_visible_projection(self.page, self.base_url, self.batch_id, self._row(1)))
        assert after == before

    @rule(status=st.sampled_from(("Blocking", "Warning", "No issues")))
    def severity_filter(self, status):
        async def apply_and_assert():
            await self.page.locator('[data-row-status-filter="all"]').click()
            await self.page.locator(f'[data-row-status-filter="{status}"]').click()
            visible = self.page.locator("tr.validation-row:visible")
            for index in range(await visible.count()):
                assert (await visible.nth(index).locator(".validation-status-label").inner_text()).strip() == status

        self._run(apply_and_assert())
        self._run(self.page.locator('[data-row-status-filter="all"]').click())

    @rule(disposition=st.sampled_from(("none", "accept_as_is", "needs_follow_up", "reject_row")))
    def disposition_filter(self, disposition):
        async def apply_and_assert():
            await self.page.locator('[data-row-status-filter="all"]').click()
            await self.page.locator("#disposition-filter").select_option(disposition)
            visible = self.page.locator("tr.validation-row:visible")
            for index in range(await visible.count()):
                value = await visible.nth(index).locator(".row-status-dropdown").input_value()
                if disposition == "none":
                    assert value == ""
                else:
                    assert value == disposition

        self._run(apply_and_assert())
        self._run(self.page.locator("#disposition-filter").select_option("all"))

    @invariant()
    def visible_rows_have_status_and_disposition(self):
        rows = self.page.locator("tr.validation-row")
        assert self._run(rows.count()) == 3
        for index in range(3):
            row = self._row(index)
            assert self._run(row.locator(".validation-status-label").count()) == 1
            assert self._run(row.locator(".row-status-dropdown").count()) == 1

    def teardown(self):
        try:
            self.loop.run_until_complete(self.browser.close())
            self.loop.run_until_complete(self.playwright.stop())
        finally:
            self.loop.close()
            stop_flask_server(self.server, self.thread)


@pytest.mark.parametrize("_run", [0])
def test_hypothesis_reviewer_state_machine(e2e_database_and_app, _run):
    """Run a bounded, reproducible, shrinkable state machine on real UI paths."""
    database_url, _, flask_app = e2e_database_and_app
    ReviewerStateMachine.database_url = database_url
    ReviewerStateMachine.flask_app = flask_app
    ReviewerStateMachine.TestCase.settings = settings(
        max_examples=2,
        stateful_step_count=6,
        derandomize=True,
        deadline=None,
        database=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    ReviewerStateMachine.TestCase().runTest()
