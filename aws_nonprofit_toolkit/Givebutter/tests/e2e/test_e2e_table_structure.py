"""
Test that the validation review table renders with correct DOM structure and column alignment.

This test verifies that:
1. All expected header columns are present in the real validation review route
2. Table data rows have the correct number of cells matching headers
3. No extra columns are rendered that would cause misalignment
4. Date field is always present and populated
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_table_has_correct_header_columns(flask_app_database_mode):
    """Verify validation review table has all expected header columns in correct order."""
    from playwright.async_api import async_playwright
    from scripts.householder.database_models import (
        ImportBatch,
        RawImportRow,
        ImportContact,
        create_db_engine,
    )

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='validation-table-test',
            filename='validation_test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row with validation issues
        raw_row = RawImportRow(
            batch_id='validation-table-test',
            row_index=1,
            raw_csv_data={
                'name': 'Test User',
                'date': '2026-03-01',
                'email': 'invalid-email',  # Invalid format - will trigger validation issue
                'phone': '(555) 111-1111',
                'amount': '500.00',
                'address': '123 Test St'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='validation-table-test',
            raw_import_row_id=raw_row.id,
            first_name='Test',
            last_name='User',
            email='invalid-email',
            phone='(555) 111-1111',
            address_line1='123 Test St',
            amount=500.00
        )
        session.add(contact)
        session.commit()

        contact_id = contact.id

        session.close()

        # Launch browser and navigate to validation review
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                # Navigate to real validation review route
                await page.goto(f'http://127.0.0.1:8001/imports/validation-table-test/validation', timeout=10000)

                # Wait for table to load
                await page.wait_for_selector('thead th', timeout=5000)

                # Get all header cells
                headers = await page.locator('thead th').all_text_contents()

                # Define expected headers from actual validation.html template
                # The actual validation review has these columns:
                # Txn ID, Date, Name, Email, Phone, Amount, Address, Row Status, Issues, Actions
                expected_headers = [
                    'Txn ID', 'Date', 'Name', 'Email', 'Phone', 'Amount',
                    'Address', 'Row Status', 'Issues', 'Actions'
                ]

                assert len(headers) == len(expected_headers), \
                    f"Header count mismatch. Got {len(headers)}, expected {len(expected_headers)}. Headers: {headers}"

                for i, (actual, expected) in enumerate(zip(headers, expected_headers)):
                    assert actual.strip() == expected, \
                        f"Header mismatch at position {i}: got '{actual}', expected '{expected}'"

            finally:
                await browser.close()

    finally:
        if session:
            session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_table_data_rows_have_correct_cell_count(flask_app_database_mode):
    """Verify each data row has exactly as many cells as there are headers."""
    from playwright.async_api import async_playwright
    from scripts.householder.database_models import (
        ImportBatch,
        RawImportRow,
        ImportContact,
        create_db_engine,
    )

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch with multiple rows
        batch = ImportBatch(
            id='validation-rows-test',
            filename='validation_rows_test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=3
        )
        session.add(batch)
        session.flush()

        # Create multiple raw rows
        for idx in range(3):
            raw_row = RawImportRow(
                batch_id='validation-rows-test',
                row_index=idx + 1,
                raw_csv_data={
                    'name': f'Test User {idx + 1}',
                    'date': '2026-03-01',
                    'email': f'user{idx}@invalid',  # Invalid email
                    'phone': f'(555) {idx:03d}-1111',
                    'amount': '100.00',
                    'address': f'{idx + 100} Test St'
                }
            )
            session.add(raw_row)
            session.flush()

            contact = ImportContact(
                batch_id='validation-rows-test',
                raw_import_row_id=raw_row.id,
                first_name=f'Test{idx}',
                last_name=f'User{idx}',
                email=f'user{idx}@invalid',
                phone=f'(555) {idx:03d}-1111',
                address_line1=f'{idx + 100} Test St',
                amount=100.00
            )
            session.add(contact)

        session.commit()
        session.close()

        # Launch browser and navigate to validation review
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto('http://127.0.0.1:8001/imports/validation-rows-test/validation', timeout=10000)

                # Wait for table
                await page.wait_for_selector('tbody tr', timeout=5000)

                # Get header count
                header_count = await page.locator('thead th').count()

                # Get all body rows
                rows = await page.locator('tbody tr').all()

                assert len(rows) > 0, "No data rows found in table"

                # Verify each row has exactly header_count cells
                for idx, row in enumerate(rows):
                    cells = await row.locator('td').count()
                    assert cells == header_count, \
                        f"Row {idx}: cell count mismatch. Got {cells}, expected {header_count}"

            finally:
                await browser.close()

    finally:
        if session:
            session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_date_column_is_present(flask_app_database_mode):
    """Verify that Date column is always rendered in the validation review table."""
    from playwright.async_api import async_playwright
    from scripts.householder.database_models import (
        ImportBatch,
        RawImportRow,
        ImportContact,
        create_db_engine,
    )

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='validation-date-test',
            filename='validation_date_test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1
        )
        session.add(batch)
        session.flush()

        # Create raw row
        raw_row = RawImportRow(
            batch_id='validation-date-test',
            row_index=1,
            raw_csv_data={
                'name': 'Date Test',
                'date': '2026-05-15',  # Important test data
                'email': 'invalid',
                'phone': '(555) 222-2222',
                'amount': '250.00',
                'address': '456 Date St'
            }
        )
        session.add(raw_row)
        session.flush()

        # Create ImportContact
        contact = ImportContact(
            batch_id='validation-date-test',
            raw_import_row_id=raw_row.id,
            first_name='Date',
            last_name='Test',
            email='invalid',
            phone='(555) 222-2222',
            address_line1='456 Date St',
            amount=250.00
        )
        session.add(contact)
        session.commit()
        session.close()

        # Launch browser and navigate to validation review
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto('http://127.0.0.1:8001/imports/validation-date-test/validation', timeout=10000)

                # Wait for table
                await page.wait_for_selector('thead th', timeout=5000)

                # Check that Date header exists
                date_header = page.locator('thead th:has-text("Date")')
                assert await date_header.count() == 1, "Date column header not found"

                # Get Date column index
                all_headers = await page.locator('thead th').all_text_contents()
                date_index = None
                for i, h in enumerate(all_headers):
                    if h.strip() == 'Date':
                        date_index = i
                        break

                assert date_index is not None, "Date column not found in headers"

                # Verify date data is populated in each row
                rows = await page.locator('tbody tr').all()
                for row_idx, row in enumerate(rows):
                    cells = await row.locator('td').all()
                    assert date_index < len(cells), \
                        f"Row {row_idx}: Date cell index {date_index} out of bounds ({len(cells)} cells)"

                    date_cell = cells[date_index]
                    # Date field is an input element, get its value
                    date_input = date_cell.locator('input')
                    if await date_input.count() > 0:
                        date_value = await date_input.input_value()
                        assert date_value.strip() != '', \
                            f"Row {row_idx}: Date input field is empty"
                    else:
                        # Fallback to text content if not an input
                        date_text = await date_cell.text_content()
                        assert date_text.strip() != '', \
                            f"Row {row_idx}: Date cell is empty"

            finally:
                await browser.close()

    finally:
        if session:
            session.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_table_column_count_consistency(flask_app_database_mode):
    """Verify validation table doesn't render extra columns that would cause misalignment."""
    from playwright.async_api import async_playwright
    from scripts.householder.database_models import (
        ImportBatch,
        RawImportRow,
        ImportContact,
        create_db_engine,
    )

    process, database_url, db_path = flask_app_database_mode

    # Seed test data
    engine = create_db_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create batch
        batch = ImportBatch(
            id='validation-consistency-test',
            filename='validation_consistency_test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=2
        )
        session.add(batch)
        session.flush()

        # Create multiple rows to verify consistency
        for idx in range(2):
            raw_row = RawImportRow(
                batch_id='validation-consistency-test',
                row_index=idx + 1,
                raw_csv_data={
                    'name': f'Consistency Test {idx + 1}',
                    'date': '2026-04-01',
                    'email': f'invalid{idx}',
                    'phone': '(555) 333-3333',
                    'amount': '350.00',
                    'address': '789 Consistency Ave'
                }
            )
            session.add(raw_row)
            session.flush()

            contact = ImportContact(
                batch_id='validation-consistency-test',
                raw_import_row_id=raw_row.id,
                first_name=f'Consistency{idx}',
                last_name=f'Test{idx}',
                email=f'invalid{idx}',
                phone='(555) 333-3333',
                address_line1='789 Consistency Ave',
                amount=350.00
            )
            session.add(contact)

        session.commit()
        session.close()

        # Launch browser and navigate to validation review
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            try:
                await page.goto('http://127.0.0.1:8001/imports/validation-consistency-test/validation', timeout=10000)

                # Wait for table
                await page.wait_for_selector('thead th', timeout=5000)

                # Expected header count (10 columns from actual validation.html)
                expected_count = 10
                actual_count = await page.locator('thead th').count()

                assert actual_count == expected_count, \
                    f"Header column count mismatch. Got {actual_count}, expected {expected_count}"

                # Verify no data rows have extra cells
                rows = await page.locator('tbody tr').all()
                for idx, row in enumerate(rows):
                    cell_count = await row.locator('td').count()
                    assert cell_count == expected_count, \
                        f"Row {idx}: cell count mismatch. Got {cell_count}, expected {expected_count}"

            finally:
                await browser.close()

    finally:
        if session:
            session.close()
