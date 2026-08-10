"""Focused browser contract for explicit international phone corrections."""

from pathlib import Path
import sys

import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.householder.database_models import RawImportRow, create_db_engine  # noqa: E402
from tests.e2e.test_validation_disposition_contract import _seed_batch  # noqa: E402
from tests.e2e.test_validation_review_dom import (  # noqa: E402
    e2e_database_and_app,
    start_flask_server,
    stop_flask_server,
    wait_for_flask_ready,
)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_explicit_international_phone_is_readable_and_persists(e2e_database_and_app):
    """International phone corrections display readably and reload from E.164."""
    from playwright.async_api import async_playwright

    database_url, _, flask_app = e2e_database_and_app
    session = sessionmaker(bind=create_db_engine(database_url))()
    batch_id = "international-phone-contract"
    seeded = _seed_batch(session, batch_id=batch_id, rows=[
        {"name": "International Donor", "email": "intl@example.com"},
    ])
    raw = seeded[0][0]
    raw_before = dict(raw.raw_csv_data)
    session.commit()

    server = thread = None
    try:
        server, thread, base_url = start_flask_server(flask_app)
        wait_for_flask_ready(base_url, batch_id)
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(f"{base_url}/imports/{batch_id}/validation")
                phone = page.locator('input[data-field="phone"]').first
                await phone.fill("+44 20 7946 0958")
                await phone.evaluate("element => element.blur()")
                await page.wait_for_function(
                    "() => document.querySelector('input[data-field=phone]')?.value.includes('+44 20 7946 0958')",
                    timeout=5000,
                )
                assert await phone.input_value() == "+44 20 7946 0958"

                session.expire_all()
                persisted = session.query(RawImportRow).filter_by(id=raw.id).one()
                assert persisted.raw_csv_data == raw_before

                await page.reload()
                await page.wait_for_function(
                    "() => document.querySelector('input[data-field=phone]')?.value.includes('+44 20 7946 0958')",
                    timeout=5000,
                )
                assert await phone.input_value() == "+44 20 7946 0958"
            finally:
                await browser.close()
    finally:
        session.close()
        stop_flask_server(server, thread)
