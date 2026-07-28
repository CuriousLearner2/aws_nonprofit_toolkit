"""Browser regression for the Export Console recent exports panel."""

from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest
from playwright.async_api import async_playwright
from sqlalchemy.orm import sessionmaker
from werkzeug.serving import make_server

from scripts.householder.database_models import (
    AuditLogRecord,
    Base,
    ImportBatch,
    ImportContact,
    RawImportRow,
    create_db_engine,
)
from scripts.uploader.app import app


async def wait_for_server_ready(url: str, timeout_seconds: int = 10) -> None:
    """Poll a route until the Flask server responds successfully."""
    import requests

    start = asyncio.get_event_loop().time()
    delay = 0.1

    while asyncio.get_event_loop().time() - start < timeout_seconds:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code < 500:
                return
        except (requests.ConnectionError, requests.Timeout):
            pass
        await asyncio.sleep(delay)
        delay = min(delay * 1.5, 1.0)

    raise RuntimeError(f"Server did not become ready at {url}")


@pytest.fixture
def export_console_db():
    """Create a temporary database and export directory for the browser regression."""
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = db_file.name
    db_file.close()

    export_dir = Path(tempfile.mkdtemp(prefix="recent-exports-"))
    database_url = f"sqlite:///{db_path}"

    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    original_repo_mode = os.environ.get("HOUSEHOLDER_REPOSITORY")
    original_db_url = os.environ.get("GIVEBUTTER_DATABASE_URL")
    original_export_dir = app.config.get("EXPORT_OUTPUT_DIR")
    original_repo_config = app.config.get("HOUSEHOLDER_REPOSITORY")
    original_db_config = app.config.get("GIVEBUTTER_DATABASE_URL")

    os.environ["HOUSEHOLDER_REPOSITORY"] = "database"
    os.environ["GIVEBUTTER_DATABASE_URL"] = database_url
    app.config["TESTING"] = True
    app.config["HOUSEHOLDER_REPOSITORY"] = "database"
    app.config["GIVEBUTTER_DATABASE_URL"] = database_url
    app.config["EXPORT_OUTPUT_DIR"] = str(export_dir)

    try:
        yield database_url, engine, str(export_dir), db_path
    finally:
        if original_repo_mode is None:
            os.environ.pop("HOUSEHOLDER_REPOSITORY", None)
        else:
            os.environ["HOUSEHOLDER_REPOSITORY"] = original_repo_mode

        if original_db_url is None:
            os.environ.pop("GIVEBUTTER_DATABASE_URL", None)
        else:
            os.environ["GIVEBUTTER_DATABASE_URL"] = original_db_url

        if original_repo_config is None:
            app.config.pop("HOUSEHOLDER_REPOSITORY", None)
        else:
            app.config["HOUSEHOLDER_REPOSITORY"] = original_repo_config

        if original_db_config is None:
            app.config.pop("GIVEBUTTER_DATABASE_URL", None)
        else:
            app.config["GIVEBUTTER_DATABASE_URL"] = original_db_config

        if original_export_dir is None:
            app.config.pop("EXPORT_OUTPUT_DIR", None)
        else:
            app.config["EXPORT_OUTPUT_DIR"] = original_export_dir

        Path(db_path).unlink(missing_ok=True)
        import shutil

        shutil.rmtree(export_dir, ignore_errors=True)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_recent_exports_appears_after_generation_and_reload(export_console_db):
    """Generate an export, then prove Recent Exports appears and survives reload."""
    database_url, engine, export_dir, db_path = export_console_db
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    batch_id = "IMP-RECENT-001"

    try:
        batch = ImportBatch(
            id=batch_id,
            filename="recent_exports.csv",
            upload_timestamp=datetime.now(timezone.utc),
            status="pending_review",
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id=batch_id,
            row_index=1,
            raw_csv_data={
                "transaction_id": "GB900",
                "date": "2026-07-27",
                "name": "Recent Export Test",
                "email": "recent@example.com",
                "phone": "(555) 222-2222",
                "amount": "125.00",
                "address": "123 Export Lane",
            },
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw_row.id,
            first_name="Recent",
            last_name="Export",
            email="recent@example.com",
            phone="(555) 222-2222",
            address_line1="123 Export Lane",
            amount=125.0,
        )
        session.add(contact)

        foreign_batch = ImportBatch(
            id="IMP-RECENT-OTHER",
            filename="other_recent_exports.csv",
            upload_timestamp=datetime.now(timezone.utc),
            status="pending_review",
            raw_row_count=1,
        )
        session.add(foreign_batch)
        session.flush()
        foreign_export = AuditLogRecord(
            batch_id="IMP-RECENT-OTHER",
            action_type="export_generated",
            action_timestamp=datetime(2026, 7, 27, 12, 10, 1, tzinfo=timezone.utc),
            actor="tester",
            details={
                "filename": "IMP-RECENT-OTHER_export_20260727_121001.csv",
                "export_type": "csv",
                "row_count": 3,
                "warning_count": 0,
            },
        )
        session.add(foreign_export)
        session.commit()

        server = make_server("127.0.0.1", 8001, app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        base_url = "http://127.0.0.1:8001"
        page_url = f"{base_url}/imports/{batch_id}/exports"

        try:
            await wait_for_server_ready(page_url, timeout_seconds=10)

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                page = await browser.new_page(viewport={"width": 1440, "height": 900})

                try:
                    await page.goto(page_url, wait_until="load")
                    await page.wait_for_selector("h1", timeout=5000)

                    initial_text = await page.inner_text("body")
                    assert "No exports generated yet" in initial_text

                    export_button = page.locator("#generate-export-btn")
                    assert await export_button.is_enabled()

                    async with page.expect_response(
                        lambda response: response.url.endswith("/exports/generate")
                        and response.request.method == "POST"
                    ) as generate_response_info:
                        await export_button.click()

                    generate_response = await generate_response_info.value
                    assert generate_response.status == 200
                    generate_payload = await generate_response.json()
                    assert generate_payload["status"] == "success"

                    generated_filename = generate_payload["file"]["filename"]
                    generated_audit_log_id = generate_payload["file"]["audit_log_id"]

                    await page.reload(wait_until="load")
                    await page.wait_for_selector('a[data-action="download-export"]', timeout=10000)

                    download_links = page.locator('a[data-action="download-export"]')
                    assert await download_links.count() == 1

                    page_content = await page.content()
                    export_text = await page.inner_text("body")
                    assert generated_filename in export_text
                    assert "No exports generated yet" not in export_text
                    assert f"data-audit-log-id=\"{generated_audit_log_id}\"" in page_content
                    assert f"/imports/{batch_id}/exports/download/{generated_audit_log_id}" in page_content
                    assert "IMP-RECENT-OTHER_export_20260727_121001.csv" not in page_content

                    print(
                        f"Verified recent export {generated_filename} with audit_log_id={generated_audit_log_id}"
                    )
                finally:
                    await browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
    finally:
        session.close()
