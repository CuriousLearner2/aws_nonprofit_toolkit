"""
Test that the review table renders with correct DOM structure and column alignment.

This test verifies that:
1. All expected header columns are present
2. Table data rows have the correct number of cells matching headers
3. No extra columns are rendered that would cause misalignment
4. Date field is always present
"""

import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_table_has_correct_header_columns(start_flask_app):
    """Verify review table has all expected header columns in correct order."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Use test endpoint to load review table directly (bypasses upload complexity)
            await page.goto("http://127.0.0.1:8000/test-override-dialog", timeout=10000)

            # Wait for table to load
            await page.wait_for_selector('thead th', timeout=5000)

            # Get all header cells
            headers = await page.locator('thead th').all_text_contents()

            # Define expected headers
            expected_headers = [
                'Transaction ID', 'Date', 'Name', 'Email', 'Phone', 'Amount',
                'Address 1', 'City', 'State', 'Campaign', 'Tier', 'Issues',
                'Suggested Fixes', 'Decision', 'Notes'
            ]

            assert len(headers) == len(expected_headers), \
                f"Header count mismatch. Got {len(headers)}, expected {len(expected_headers)}. Headers: {headers}"

            for i, (actual, expected) in enumerate(zip(headers, expected_headers)):
                assert actual.strip() == expected, \
                    f"Header mismatch at position {i}: got '{actual}', expected '{expected}'"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_review_table_data_rows_have_correct_cell_count(start_flask_app):
    """Verify each data row has exactly as many cells as there are headers."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Use test endpoint to load review table directly
            await page.goto("http://127.0.0.1:8000/test-override-dialog", timeout=10000)

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


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_date_column_is_present(start_flask_app):
    """Verify that Date column is always rendered in the table."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Use test endpoint to load review table directly
            await page.goto("http://127.0.0.1:8000/test-override-dialog", timeout=10000)

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
                date_text = await date_cell.text_content()
                assert date_text.strip() != '', \
                    f"Row {row_idx}: Date cell is empty"

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_no_extra_columns_in_table(start_flask_app):
    """Verify table doesn't render extra columns that would cause misalignment."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Use test endpoint to load review table directly
            await page.goto("http://127.0.0.1:8000/test-override-dialog", timeout=10000)

            # Wait for table
            await page.wait_for_selector('thead th', timeout=5000)

            # Expected header count (15 columns)
            expected_count = 15
            actual_count = await page.locator('thead th').count()

            assert actual_count == expected_count, \
                f"Header column count mismatch. Got {actual_count}, expected {expected_count}"

            # Verify no data rows have extra cells
            rows = await page.locator('tbody tr').all()
            for idx, row in enumerate(rows):
                cell_count = await row.locator('td').count()
                assert cell_count == expected_count, \
                    f"Row {idx}: extra cells found. Got {cell_count}, expected {expected_count}"

        finally:
            await browser.close()
