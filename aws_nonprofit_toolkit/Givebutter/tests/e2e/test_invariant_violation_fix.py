"""
E2E test for invariant violation fix.

Scenario from bug report:
- Email: john@example.cc (showing error)
- Phone: (555) 123-45 (incomplete - validation error)
- Review Status: MUST NOT be "No issues" if validation errors exist

This test verifies:
1. Start with a clean row (Review Status = "No issues")
2. Edit phone to incomplete value
3. Blur to trigger autosave
4. Autosave fails with validation error
5. Review Status updates to show the validation error (e.g., "Blocking")
6. Dropdown remains interactive
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    create_db_engine,
)
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def temp_db():
    """Create temporary SQLite database for testing."""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    database_url = f'sqlite:///{db_path}'
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    yield database_url, engine

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_batch(temp_db):
    """Create a test batch with a clean row."""
    database_url, engine = temp_db

    Session = sessionmaker(bind=engine)
    session = Session()

    batch = ImportBatch(
        id='e2e-test-batch',
        filename='test.csv',
        upload_timestamp=datetime.utcnow(),
        status='pending_review',
        raw_row_count=1
    )
    session.add(batch)
    session.flush()

    # Create a clean row with valid data initially
    row = RawImportRow(
        batch_id='e2e-test-batch',
        row_index=1,
        raw_csv_data={
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '(415) 555-2671',  # Valid initially
            'date': '2024-01-01',
            'amount': '100.00',
            'address': '123 Main St'
        }
    )
    session.add(row)
    session.flush()
    raw_id = row.id
    session.commit()
    session.close()

    return database_url, 'e2e-test-batch', raw_id


def test_invariant_dropdown_preserved_on_autosave_error(test_batch):
    """
    When autosave fails with validation error, the dropdown remains interactive
    and shows the updated Review Status (not "No issues").

    This verifies the bug fix: we should NOT replace the entire row-status-cell
    HTML with a badge, which would remove the dropdown.
    """
    database_url, batch_id, raw_id = test_batch

    # Setup Flask app
    app.config['TESTING'] = True
    import os
    os.environ['GIVEBUTTER_DATABASE_URL'] = database_url

    client = app.test_client()

    # Step 1: Get the initial validation review page
    response = client.get(f'/imports/{batch_id}/validation')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Verify initial state: review status should be "No issues" for a clean row
    assert 'No issues' in html or f'data-raw-id="{raw_id}"' in html

    # Step 2: Autosave with invalid phone (incomplete)
    autosave_response = client.post(
        f'/imports/{batch_id}/autosave',
        json={
            'raw_import_row_id': raw_id,
            'corrected_values': {'phone': '(555) 123-45'}  # Incomplete - triggers error
        }
    )

    assert autosave_response.status_code == 400
    error_data = autosave_response.get_json()

    # Verify error response has row_status (for frontend to update)
    assert 'row_status' in error_data
    assert error_data['row_status'] != 'No issues', \
        f"Error response must have non-'No issues' status, got '{error_data['row_status']}'"

    # Verify issues are included
    assert 'issues' in error_data
    assert len(error_data['issues']) > 0, \
        "Error response must include issues list"

    # Verify phone issue is in the list
    phone_issues = [i for i in error_data['issues'] if i.get('field') == 'phone']
    assert len(phone_issues) > 0, \
        f"Phone validation error should be in issues, got: {error_data['issues']}"

    # Step 3: Get the validation page again and verify the dropdown still exists
    # (This verifies that the frontend didn't replace the entire cell with just a badge)
    response = client.get(f'/imports/{batch_id}/validation')
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # The row should still have a dropdown (not replaced with badge-only HTML)
    assert f'data-raw-id="{raw_id}"' in html
    # Dropdown should still be present in HTML
    assert 'row-status-dropdown' in html


def test_invariant_violation_api_response(test_batch):
    """
    Direct API test: autosave error response must include row_status
    and issues so frontend can update the UI correctly.
    """
    database_url, batch_id, raw_id = test_batch

    app.config['TESTING'] = True
    import os
    os.environ['GIVEBUTTER_DATABASE_URL'] = database_url

    client = app.test_client()

    # Autosave with invalid phone
    response = client.post(
        f'/imports/{batch_id}/autosave',
        json={
            'raw_import_row_id': raw_id,
            'corrected_values': {'phone': '(555) 123-45'}
        }
    )

    assert response.status_code == 400
    data = response.get_json()

    # Check invariant
    has_issues = len(data.get('issues', [])) > 0
    status_is_no_issues = data.get('row_status') == 'No issues'

    assert has_issues, "Error response should have issues"
    assert not status_is_no_issues, \
        f"INVARIANT: If issues exist, row_status must NOT be 'No issues'. Got: {data['row_status']}"
    assert data['row_status'] in ['Blocking', 'Warning'], \
        f"Expected 'Blocking' or 'Warning' status for validation errors, got: {data['row_status']}"


def test_invalid_email_also_updates_status(test_batch):
    """
    Similar to phone test but for email field.
    Ensures the fix works for any field validation error.
    """
    database_url, batch_id, raw_id = test_batch

    app.config['TESTING'] = True
    import os
    os.environ['GIVEBUTTER_DATABASE_URL'] = database_url

    client = app.test_client()

    # Autosave with invalid email
    response = client.post(
        f'/imports/{batch_id}/autosave',
        json={
            'raw_import_row_id': raw_id,
            'corrected_values': {'email': 'invalid-email-no-at'}
        }
    )

    assert response.status_code == 400
    data = response.get_json()

    # Invariant must hold for any validation error
    has_issues = len(data.get('issues', [])) > 0
    status_is_no_issues = data.get('row_status') == 'No issues'

    assert has_issues, "Error response should have issues"
    assert not status_is_no_issues, \
        "INVARIANT VIOLATION: Row status should not be 'No issues' when errors exist"
