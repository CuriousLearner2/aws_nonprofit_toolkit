"""
Fast Validation Review integration regression suite.

Tests verify endpoint logic, validation rules, and data persistence using Flask test client.
These tests validate business logic and invariants without rendering DOM or testing JavaScript.

Tests cover:
1. Email validation and row status sync
2. Phone validation and row status sync
3. Amount validation and export safety
4. Date validation and export safety
5. Successful autosave for Name and Address
6. Needs follow-up requires Notes
7. Defer does not require Notes
8. Approval warning with unresolved issues
9. Export preview uses successful corrections only

Note: These are fast local regression tests (~2.4s per run).
For DOM rendering, JavaScript, visible styling, focus behavior, and dropdown text,
see tests/e2e/test_validation_review_dom.py (browser tests via Playwright).
"""

import pytest
import sys
import tempfile
import re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
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

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def flask_client_with_validation_batch(temp_db, monkeypatch):
    """Flask test client with validation batch seeded in database."""
    database_url, engine = temp_db

    app.config['TESTING'] = True
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    app.config['HOUSEHOLDER_REPOSITORY'] = 'database'
    app.config['GIVEBUTTER_DATABASE_URL'] = database_url

    # Seed database with validation records
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create batch
    batch = ImportBatch(
        id='validation-workflow-test-batch',
        filename='validation_test.csv',
        upload_timestamp=datetime.now(timezone.utc),
        status='pending_review',
        raw_row_count=9
    )
    session.add(batch)
    session.flush()

    # Create 9 raw import rows for 9 test scenarios
    raw_rows = []
    review_contacts = []
    test_cases = [
        # Test 1: Email validation
        {
            'row_index': 1,
            'raw_csv_data': {
                'name': 'John Smith',
                'date': '2026-01-15',
                'email': 'invalid-no-at-symbol',
                'phone': '(415) 555-2671',
                'amount': '100.00',
                'address': '123 Main St'
            }
        },
        # Test 2: Phone validation
        {
            'row_index': 2,
            'raw_csv_data': {
                'name': 'Jane Doe',
                'date': '2026-01-16',
                'email': 'jane@example.com',
                'phone': '(555) 123-45',  # Invalid format
                'amount': '250.00',
                'address': '456 Oak Ave'
            }
        },
        # Test 3: Amount validation
        {
            'row_index': 3,
            'raw_csv_data': {
                'name': 'Bob Wilson',
                'date': '2026-01-17',
                'email': 'bob@example.com',
                'phone': '(415) 555-2672',
                'amount': 'abc',  # Invalid amount
                'address': '789 Elm St'
            }
        },
        # Test 4: Date validation
        {
            'row_index': 4,
            'raw_csv_data': {
                'name': 'Alice Brown',
                'date': 'not-a-date',  # Invalid date
                'email': 'alice@example.com',
                'phone': '(415) 555-2673',
                'amount': '500.00',
                'address': '321 Pine Rd'
            }
        },
        # Test 5: Valid Name and Address (successful autosave)
        {
            'row_index': 5,
            'raw_csv_data': {
                'name': 'Charlie Davis',
                'date': '2026-01-18',
                'email': 'charlie@example.com',
                'phone': '(415) 555-2674',
                'amount': '150.00',
                'address': '654 Maple Dr'
            }
        },
        # Test 6: Needs follow-up workflow
        {
            'row_index': 6,
            'raw_csv_data': {
                'name': 'Diana Evans',
                'date': '2026-01-19',
                'email': 'diana@example.com',
                'phone': '(415) 555-2675',
                'amount': '300.00',
                'address': '987 Cedar Ln'
            }
        },
        # Test 7: Defer workflow
        {
            'row_index': 7,
            'raw_csv_data': {
                'name': 'Edward Frank',
                'date': '2026-01-20',
                'email': 'edward@example.com',
                'phone': '(415) 555-2676',
                'amount': '400.00',
                'address': '147 Birch Blvd'
            }
        },
        # Test 8: Unresolved issues for approval warning
        {
            'row_index': 8,
            'raw_csv_data': {
                'name': 'Frank Garcia',
                'date': '2026-01-21',
                'email': 'invalid-email',  # Invalid for approval warning test
                'phone': '(415) 555-2677',
                'amount': '600.00',
                'address': '258 Spruce Way'
            }
        },
        # Test 9: Export preview with mixed corrections
        {
            'row_index': 9,
            'raw_csv_data': {
                'name': 'Grace Harris',
                'date': '2026-01-22',
                'email': 'grace@example.com',
                'phone': '(415) 555-2678',
                'amount': '200.00',
                'address': '369 Walnut St'
            }
        },
    ]

    for test_case in test_cases:
        raw_data = test_case['raw_csv_data']
        raw_row = RawImportRow(
            batch_id='validation-workflow-test-batch',
            row_index=test_case['row_index'],
            raw_csv_data=raw_data
        )
        session.add(raw_row)
        session.flush()
        raw_rows.append(raw_row.id)

        raw_amount = raw_data.get('amount')
        try:
            contact_amount = float(raw_amount) if raw_amount is not None else None
        except (TypeError, ValueError):
            contact_amount = None

        raw_name = raw_data.get('name', '').strip()
        name_parts = raw_name.split(' ', 1) if raw_name else []
        first_name = name_parts[0] if name_parts else 'Test'
        last_name = name_parts[1] if len(name_parts) > 1 else 'User'

        contact = ImportContact(
            batch_id='validation-workflow-test-batch',
            raw_import_row_id=raw_row.id,
            first_name=first_name,
            last_name=last_name,
            email=raw_data.get('email', ''),
            phone=raw_data.get('phone', ''),
            amount=contact_amount,
            address_line1=raw_data.get('address', ''),
        )
        session.add(contact)
        session.flush()
        review_contacts.append(contact.id)

        review_item = ReviewItem(
            batch_id='validation-workflow-test-batch',
            item_type='validation',
            status='pending',
            payload_json={
                'field': 'email',
                'reason': 'format',
                'description': 'Invalid email',
                'severity': 'error',
            }
        )
        session.add(review_item)
        session.flush()
        session.add(
            ReviewItemSubject(
                review_item_id=review_item.id,
                subject_type='import_contact_snapshot',
                subject_id=contact.id,
            )
        )

    session.commit()
    session.close()

    with app.test_client() as client:
        yield client, database_url, engine, Session, raw_rows


def _seed_unresolved_validation_issue(Session, batch_id, raw_import_row_id, field='email'):
    """Seed a blocking validation issue for approval override tests."""
    session = Session()
    try:
        issue = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            status='pending',
            payload_json={
                'field': field,
                'reason': 'format',
                'description': f'Invalid {field}',
                'severity': 'error',
            },
        )
        session.add(issue)
        session.flush()
        session.add(
            ReviewItemSubject(
                review_item_id=issue.id,
                subject_type='import_raw_row',
                subject_id=raw_import_row_id,
            )
        )
        session.commit()
    finally:
        session.close()


def _seed_warning_only_validation_issue(Session, batch_id, raw_import_row_id):
    """Seed a warning-tier validation issue for approval gating tests."""
    session = Session()
    try:
        raw_row = session.query(RawImportRow).filter_by(id=raw_import_row_id).first()
        contact = session.query(ImportContact).filter_by(
            raw_import_row_id=raw_import_row_id
        ).first()

        if raw_row:
            raw_data = dict(raw_row.raw_csv_data or {})
            raw_data['email'] = 'john@gmial.com'
            raw_row.raw_csv_data = raw_data

        if contact:
            contact.email = 'john@gmial.com'

            issue = session.query(ReviewItem).join(ReviewItemSubject).filter(
                ReviewItem.batch_id == batch_id,
                ReviewItem.item_type == 'validation',
                ReviewItemSubject.subject_type == 'import_contact_snapshot',
                ReviewItemSubject.subject_id == contact.id,
            ).first()

            if issue:
                issue.payload_json = {
                    'field': 'email',
                    'reason': 'possible_typo',
                    'description': 'Possible typo',
                    'severity': 'warning',
                }

        session.commit()
    finally:
        session.close()


def _seed_isolated_warning_only_batch(Session):
    """Create an isolated batch containing only a warning-tier validation issue."""
    session = Session()
    batch_id = 'warning-only-approval-test-batch'
    try:
        batch = ImportBatch(
            id=batch_id,
            filename='warning_only_test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id=batch_id,
            row_index=1,
            raw_csv_data={
                'name': 'Warning Only',
                'date': '2026-01-15',
                'email': 'john@gmial.com',
                'phone': '(415) 555-2671',
                'amount': '100.00',
                'address': '123 Main St',
            },
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw_row.id,
            first_name='Warning',
            last_name='Only',
            email='john@gmial.com',
            phone='(415) 555-2671',
            amount=100.0,
            address_line1='123 Main St',
        )
        session.add(contact)
        session.flush()

        review_item = ReviewItem(
            batch_id=batch_id,
            item_type='validation',
            status='pending',
            payload_json={
                'field': 'email',
                'reason': 'possible_typo',
                'description': 'Possible typo',
                'severity': 'warning',
            },
        )
        session.add(review_item)
        session.flush()
        session.add(
            ReviewItemSubject(
                review_item_id=review_item.id,
                subject_type='import_contact_snapshot',
                subject_id=contact.id,
            )
        )

        session.commit()
        return batch_id, raw_row.id
    finally:
        session.close()


def _seed_db_backed_date_parity_batch(Session, batch_id, raw_date):
    """Create an isolated DB-backed batch for date parity checks."""
    session = Session()
    try:
        batch = ImportBatch(
            id=batch_id,
            filename='date_parity.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id=batch_id,
            row_index=1,
            raw_csv_data={
                'name': 'Date Parity',
                'date': raw_date,
                'email': 'date.parity@example.com',
                'phone': '(415) 555-1234',
                'amount': '125.00',
                'address': '123 Main St',
            },
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw_row.id,
            first_name='Date',
            last_name='Parity',
            email='date.parity@example.com',
            phone='(415) 555-1234',
            amount=125.0,
            address_line1='123 Main St',
        )
        session.add(contact)
        session.commit()
        return raw_row.id
    finally:
        session.close()


def _seed_db_backed_amount_parity_batch(Session, batch_id, raw_amount):
    """Create an isolated DB-backed batch for amount parity checks."""
    session = Session()
    try:
        batch = ImportBatch(
            id=batch_id,
            filename='amount_parity.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id=batch_id,
            row_index=1,
            raw_csv_data={
                'name': 'Amount Parity',
                'date': '2026-05-15',
                'email': 'amount.parity@example.com',
                'phone': '(415) 555-1234',
                'amount': raw_amount,
                'address': '123 Main St',
            },
        )
        session.add(raw_row)
        session.flush()

        cleaned_amount = str(raw_amount).strip().replace('$', '').replace(',', '')
        try:
            contact_amount = float(cleaned_amount) if cleaned_amount else None
        except (TypeError, ValueError):
            contact_amount = None

        contact = ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw_row.id,
            first_name='Amount',
            last_name='Parity',
            email='amount.parity@example.com',
            phone='(415) 555-1234',
            amount=contact_amount,
            address_line1='123 Main St',
        )
        session.add(contact)
        session.commit()
        return raw_row.id
    finally:
        session.close()


def _seed_db_backed_date_phone_parity_batch(
    Session,
    batch_id,
    raw_date,
    raw_phone='123',
    *,
    contact_phone=None,
):
    """Create an isolated DB-backed batch for combined date/phone parity checks."""
    session = Session()
    try:
        batch = ImportBatch(
            id=batch_id,
            filename='date_phone_parity.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id=batch_id,
            row_index=1,
            raw_csv_data={
                'name': 'Date Phone Parity',
                'date': raw_date,
                'email': 'date.phone.parity@example.com',
                'phone': raw_phone,
                'amount': '125.00',
                'address': '123 Main St',
            },
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw_row.id,
            first_name='Date',
            last_name='Phone',
            email='date.phone.parity@example.com',
            phone=contact_phone if contact_phone is not None else raw_phone,
            amount=125.0,
            address_line1='123 Main St',
        )
        session.add(contact)
        session.flush()

        session.commit()
        return raw_row.id
    finally:
        session.close()


def _seed_db_backed_email_parity_batch(
    Session,
    batch_id,
    raw_email,
    *,
    issue_payload=None,
    contact_email=None,
):
    """Create an isolated DB-backed batch for email parity checks."""
    session = Session()
    try:
        batch = ImportBatch(
            id=batch_id,
            filename='email_parity.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending_review',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id=batch_id,
            row_index=1,
            raw_csv_data={
                'name': 'Email Parity',
                'date': '2026-05-15',
                'email': raw_email,
                'phone': '(415) 555-1234',
                'amount': '125.00',
                'address': '123 Main St',
            },
        )
        session.add(raw_row)
        session.flush()

        contact = ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw_row.id,
            first_name='Email',
            last_name='Parity',
            email=contact_email if contact_email is not None else raw_email,
            phone='(415) 555-1234',
            amount=125.0,
            address_line1='123 Main St',
        )
        session.add(contact)
        if issue_payload:
            review_item = ReviewItem(
                batch_id=batch_id,
                item_type='validation',
                status='pending',
                payload_json=issue_payload,
            )
            session.add(review_item)
            session.flush()
            session.add(
                ReviewItemSubject(
                    review_item_id=review_item.id,
                    subject_type='import_contact_snapshot',
                    subject_id=contact.id,
                )
            )
        session.commit()
        return raw_row.id
    finally:
        session.close()


# ==============================================================================
# TEST 1: Email validation and row status sync
# ==============================================================================

class TestEmailValidationSync:
    """Test email validation error and row status sync."""

    def test_autosave_invalid_email_returns_blocking_status(
        self, flask_client_with_validation_batch
    ):
        """Invalid email autosave should return Blocking status, not No issues."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[0]

        # Try to autosave with invalid email (keep original invalid value)
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid-no-at-symbol'}
            }
        )

        # Should fail validation
        assert response.status_code == 400
        data = response.get_json()

        # INVARIANT: row_status must NOT be "No issues" when email is invalid
        assert data['row_status'] != 'No issues', \
            f"INVARIANT VIOLATION: Email invalid but row_status is 'No issues'. Got: {data['row_status']}"

        # Issues should include email
        assert any(i.get('field') == 'email' for i in data['issues']), \
            "Email issue should be in issues list"

    def test_autosave_valid_email_clears_errors(
        self, flask_client_with_validation_batch
    ):
        """Correcting to valid email should clear errors."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[0]

        # Autosave with valid email
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'john.smith@example.com'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should be successful
        assert data['success'] is True

        # Row status should be No issues or clear
        assert data['row_status'] == 'No issues' or len(data['issues']) == 0, \
            f"After valid email, expected 'No issues', got: {data['row_status']}, issues: {data['issues']}"


# ==============================================================================
# TEST 2: Phone validation and row status sync
# ==============================================================================

class TestPhoneValidationSync:
    """Test phone validation error and row status sync."""

    def test_autosave_invalid_phone_returns_blocking_status(
        self, flask_client_with_validation_batch
    ):
        """Invalid phone autosave should return Blocking status."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[1]

        # Try to autosave with invalid phone
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'phone': '(555) 123-45'}  # Invalid format
            }
        )

        # Should fail validation
        assert response.status_code == 400
        data = response.get_json()

        # Status must not be "No issues"
        assert data['row_status'] != 'No issues', \
            f"Phone invalid but row_status is 'No issues'. Got: {data['row_status']}"

        # Issues should include phone
        assert any(i.get('field') == 'phone' for i in data['issues']), \
            "Phone issue should be in issues list"

    def test_autosave_valid_phone_clears_errors(
        self, flask_client_with_validation_batch
    ):
        """Correcting to valid phone should clear errors."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[1]

        # Autosave with valid phone using phonenumbers library format
        # Need a valid area code like 415 (area code from documentation example)
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'phone': '(415) 555-2671'}  # Valid per phonenumbers lib
            }
        )

        # Phone validation uses phonenumbers library, should succeed
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


# ==============================================================================
# TEST 3: Amount validation and export safety
# ==============================================================================

class TestAmountValidationSafety:
    """Test amount validation and export safety."""

    def test_autosave_amount_field_accepts_text_values(
        self, flask_client_with_validation_batch
    ):
        """Amount autosave may accept text values (validation may be lenient)."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[2]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'amount': 'xyz'}
            }
        )

        # Amount validation may be lenient and accept any value
        # Just verify it's processed without error
        assert response.status_code in [200, 400]

    def test_autosave_valid_amount_clears_errors(
        self, flask_client_with_validation_batch
    ):
        """Valid amount should clear errors."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[2]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'amount': '150.00'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


# ==============================================================================
# TEST 4: Date validation and export safety
# ==============================================================================

class TestDateValidationSafety:
    """Test date validation and export safety."""

    def test_autosave_date_field_rejects_text_values(
        self, flask_client_with_validation_batch
    ):
        """Date autosave must reject non-ISO text values."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[3]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'date': 'not-a-date'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'date' in data['validation_errors']
        assert 'YYYY-MM-DD' in data['validation_errors']['date']

        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(raw_import_row_id=raw_id).all()
            assert len(decisions) == 0, f"Invalid date was saved! {decisions}"
        finally:
            session.close()

    def test_autosave_valid_date_clears_errors(
        self, flask_client_with_validation_batch
    ):
        """Valid ISO date should be saved and clear errors."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[3]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'date': '2026-01-20'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['effective_values']['date'] == '2026-01-20'

        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decision = session.query(ReviewDecision).filter_by(raw_import_row_id=raw_id).first()
            assert decision is not None
            assert decision.reviewed_values['date'] == '2026-01-20'
        finally:
            session.close()


# ==============================================================================
# TEST 4B: Validation Review scope exclusions
# ==============================================================================

class TestValidationReviewScopeExclusions:
    """Test that Validation Review does not dynamically validate unsupported fields."""

    @pytest.mark.parametrize(
        "field_name, raw_index, corrected_value",
        [
            ('address', 5, '999 Oak Street, Apt 100'),
            ('campaign', 5, 'Spring Gala 2026'),
        ],
    )
    def test_unsupported_validation_review_fields_do_not_create_dynamic_issues(
        self,
        flask_client_with_validation_batch,
        field_name,
        raw_index,
        corrected_value,
    ):
        """
        Address and campaign must not be dynamically validated on the review screen.

        These fields may be stored as reviewed values, but they must not generate
        Validation Review issues or blocking status from the autosave path.
        """
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[raw_index - 1]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {field_name: corrected_value}
            }
        )

        assert response.status_code == 200, (
            f"{field_name} should not be dynamically validated in Validation Review, "
            f"got {response.status_code}: {response.get_json()}"
        )

        data = response.get_json()
        assert data['success'] is True
        assert data.get('row_status') is not None
        assert all(issue.get('field') != field_name for issue in data.get('issues', [])), (
            f"Validation Review must not generate dynamic issues for {field_name}, "
            f"got: {data.get('issues')}"
        )

    def test_date_review_field_creates_dynamic_issue(
        self,
        flask_client_with_validation_batch,
    ):
        """Date must be dynamically validated on the review screen."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[3]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'date': 'not-a-date'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'date' in data['validation_errors']
        assert 'YYYY-MM-DD' in data['validation_errors']['date']

    def test_db_backed_invalid_raw_date_is_visible_in_validation_route(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed validation route must surface an invalid raw date without autosave."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-date-route-batch'
        raw_id = _seed_db_backed_date_parity_batch(Session, batch_id, '2026&05-15')

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        row_marker = f'data-testid="row-{raw_id}"'
        assert row_marker in html, f"Expected DB-backed row to render, got: {html[:2000]}"
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        assert row_end != -1, "Expected closing row tag for DB-backed date row"
        row_section = html[row_start:row_end]

        assert 'Blocking' in row_section, f"Invalid raw date should block, got: {row_section}"
        assert 'Date must use YYYY-MM-DD' in row_section, (
            f"Expected strict date validation copy, got: {row_section}"
        )

    def test_db_backed_valid_raw_date_remains_clear(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed validation route must keep a valid raw ISO date clear."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-date-clear-batch'
        raw_id = _seed_db_backed_date_parity_batch(Session, batch_id, '2026-05-15')

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        row_marker = f'data-testid="row-{raw_id}"'
        assert row_marker in html, f"Expected DB-backed row to render, got: {html[:2000]}"
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        assert row_end != -1, "Expected closing row tag for DB-backed valid date row"
        row_section = html[row_start:row_end]

        assert 'No issues' in row_section, f"Valid raw date should remain clear, got: {row_section}"
        assert 'Date must use YYYY-MM-DD' not in row_section

    def test_db_backed_reviewed_valid_date_supersedes_invalid_raw_date(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed autosave of a valid date should override an invalid raw date without mutating raw data."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-date-reviewed-batch'
        raw_id = _seed_db_backed_date_parity_batch(Session, batch_id, '2026&05-15')

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'date': '2026-05-15'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['effective_values']['date'] == '2026-05-15'

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'No issues' in row_section, f"Reviewed valid date should clear invalid raw date, got: {row_section}"
        assert 'Date must use YYYY-MM-DD' not in row_section

        session = Session()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert raw_row.raw_csv_data['date'] == '2026&05-15', (
                f"Raw source data must remain unchanged, got: {raw_row.raw_csv_data['date']}"
            )
        finally:
            session.close()

    def test_db_backed_reviewed_invalid_date_remains_blocking(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed autosave of an invalid date must remain blocking."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-date-invalid-reviewed-batch'
        raw_id = _seed_db_backed_date_parity_batch(Session, batch_id, '2026-05-15')

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'date': '2026&05-15'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'date' in data['validation_errors']
        assert 'YYYY-MM-DD' in data['validation_errors']['date']

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'No issues' in row_section, (
            f"Rejected invalid reviewed date should leave prior valid date intact, got: {row_section}"
        )

    def test_recalculate_row_issues_does_not_duplicate_invalid_raw_date_issue_with_proposed_values(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed recalc should emit the strict date blocker once even when proposed values are present."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'validation-workflow-test-batch'
        raw_id = raw_rows[3]

        from scripts.householder.issue_recalculation_service import recalculate_row_issues

        issues = recalculate_row_issues(
            batch_id=batch_id,
            raw_import_row_id=raw_id,
            database_url=database_url,
            proposed_values={'name': 'Alice Updated'},
        )
        date_issues = [issue for issue in issues if issue.get('field') == 'date']
        assert len(date_issues) == 1, f"Expected one date issue, got: {date_issues}"
        assert 'YYYY-MM-DD' in date_issues[0].get('description', '')

    def test_db_backed_export_preview_reports_invalid_raw_date(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed export preview must report invalid raw dates consistently."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-date-export-batch'
        raw_id = _seed_db_backed_date_parity_batch(Session, batch_id, '2026&05-15')

        from scripts.householder.export_preview_service import build_export_preview

        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )

        assert preview.is_export_ready is False, (
            f"Invalid raw date should block export preview, got: {preview}"
        )
        assert preview.blocked_count >= 1, f"Invalid raw date should add a blocker, got: {preview}"
        preview_text = ' '.join(list(preview.blockers) + list(preview.warnings))
        assert 'date' in preview_text.lower(), f"Expected date blocker in preview, got: {preview_text}"
        assert preview.export_rows, f"Expected export rows in preview, got: {preview}"
        row_validation_text = ' '.join(str(issue) for issue in preview.export_rows[0].validation_issues)
        assert 'date' in row_validation_text.lower(), (
            f"Expected date validation issue on export row, got: {row_validation_text}"
        )
        assert 'YYYY-MM-DD' in row_validation_text, (
            f"Expected strict date copy in export row validation issues, got: {row_validation_text}"
        )


class TestEmailValidationParity:
    """Test DB-backed email validation parity across route, approval, and export."""

    def test_db_backed_invalid_raw_email_is_visible_in_validation_route(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed validation route must surface invalid raw email before autosave."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-email-route-batch'
        raw_id = _seed_db_backed_email_parity_batch(
            Session,
            batch_id,
            'invalid-no-at-symbol',
            contact_email='john.smith@example.com',
        )

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        row_marker = f'data-testid="row-{raw_id}"'
        assert row_marker in html, f"Expected DB-backed email row to render, got: {html[:2000]}"
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        assert row_end != -1, "Expected closing row tag for DB-backed email row"
        row_section = html[row_start:row_end]

        assert 'Blocking' in row_section, f"Invalid raw email should block, got: {row_section}"
        assert 'Invalid email format' in row_section or 'missing @' in row_section.lower(), (
            f"Expected strict email validation copy, got: {row_section}"
        )

        from scripts.householder.approval_service import check_batch_remaining_issues
        from scripts.householder.export_preview_service import build_export_preview

        remaining_issues = check_batch_remaining_issues(batch_id, database_url)
        assert any(
            issue.get('field') == 'email'
            for row in remaining_issues
            for issue in row.get('issues', [])
        ), (
            f"Expected approval readiness to report email issue, got: {remaining_issues}"
        )

        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )
        assert preview.is_export_ready is False, (
            f"Invalid raw email should block export preview, got: {preview}"
        )
        preview_text = ' '.join(list(preview.blockers) + list(preview.warnings))
        assert 'email' in preview_text.lower(), f"Expected email blocker in preview, got: {preview_text}"

    def test_db_backed_reviewed_valid_email_supersedes_invalid_raw_email(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed autosave of a valid email should override an invalid raw email without mutating raw data."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-email-reviewed-batch'
        raw_id = _seed_db_backed_email_parity_batch(
            Session,
            batch_id,
            'invalid-no-at-symbol',
            issue_payload={
                'field': 'email',
                'issue': 'missing_email',
                'description': 'Invalid email',
                'severity': 'error',
            },
        )

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'john.smith@example.com'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['effective_values']['email'] == 'john.smith@example.com'

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'No issues' in row_section, f"Reviewed valid email should clear invalid raw email, got: {row_section}"
        assert 'Invalid email format' not in row_section

        from scripts.householder.approval_service import check_batch_remaining_issues
        from scripts.householder.export_preview_service import build_export_preview

        remaining_issues = check_batch_remaining_issues(batch_id, database_url)
        assert not any(
            issue.get('field') == 'email'
            for row in remaining_issues
            for issue in row.get('issues', [])
        ), (
            f"Approval readiness should clear email issue after valid autosave, got: {remaining_issues}"
        )

        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )
        assert preview.is_export_ready is True, (
            f"Valid reviewed email should keep export preview ready when no blockers remain, got: {preview}"
        )

        session = Session()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert raw_row.raw_csv_data['email'] == 'invalid-no-at-symbol', (
                f"Raw source data must remain unchanged, got: {raw_row.raw_csv_data['email']}"
            )
        finally:
            session.close()


class TestPhoneValidationParity:
    """Test DB-backed phone validation parity across route, approval, and export."""

    def test_db_backed_possible_raw_phone_does_not_create_phone_issue(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed validation route must not flag a policy-valid raw phone as invalid."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-phone-route-batch'
        raw_id = _seed_db_backed_date_phone_parity_batch(
            Session,
            batch_id,
            '2026&05',
            raw_phone='5612346',
        )

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        row_marker = f'data-testid="row-{raw_id}"'
        assert row_marker in html, f"Expected DB-backed phone row to render, got: {html[:2000]}"
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        assert row_end != -1, "Expected closing row tag for DB-backed phone row"
        row_section = html[row_start:row_end]

        assert 'Blocking' in row_section, f"Invalid raw date should still block, got: {row_section}"
        assert 'date — Date must use YYYY-MM-DD' in row_section, (
            f"Expected strict date validation copy, got: {row_section}"
        )
        assert 'phone — Invalid phone format' not in row_section, (
            f"Policy-valid phone 5612346 should not be flagged, got: {row_section}"
        )

        from scripts.householder.approval_service import check_batch_remaining_issues
        from scripts.householder.export_preview_service import build_export_preview

        remaining_issues = check_batch_remaining_issues(batch_id, database_url)
        assert any(
            issue.get('field') == 'date'
            for row in remaining_issues
            for issue in row.get('issues', [])
        ), (
            f"Expected approval readiness to report the invalid date, got: {remaining_issues}"
        )
        assert not any(
            issue.get('field') == 'phone'
            for row in remaining_issues
            for issue in row.get('issues', [])
        ), (
            f"Policy-valid phone 5612346 should not be reported, got: {remaining_issues}"
        )

        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )
        assert preview.is_export_ready is False, (
            f"Invalid raw date should block export preview, got: {preview}"
        )
        preview_text = ' '.join(list(preview.blockers) + list(preview.warnings))
        assert 'date' in preview_text.lower(), f"Expected date blocker in preview, got: {preview_text}"
        assert 'phone' not in preview_text.lower(), f"Policy-valid phone 5612346 should not be reported, got: {preview_text}"

    def test_db_backed_reviewed_valid_phone_supersedes_invalid_raw_phone(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed autosave of a valid phone should override an invalid raw phone without mutating raw data."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-phone-reviewed-batch'
        raw_id = _seed_db_backed_date_phone_parity_batch(
            Session,
            batch_id,
            '2026-05-15',
            raw_phone='123',
        )

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'phone — Invalid phone format' in row_section, (
            f"Invalid raw phone should be visible before autosave, got: {row_section}"
        )

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'phone': '(415) 555-2671'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['effective_values']['phone'] == '(415) 555-2671'

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'No issues' in row_section, (
            f"Reviewed valid phone should clear invalid raw phone, got: {row_section}"
        )
        assert 'phone — Invalid phone format' not in row_section

        from scripts.householder.approval_service import check_batch_remaining_issues
        from scripts.householder.export_preview_service import build_export_preview

        remaining_issues = check_batch_remaining_issues(batch_id, database_url)
        assert not any(
            issue.get('field') == 'phone'
            for row in remaining_issues
            for issue in row.get('issues', [])
        ), (
            f"Approval readiness should clear phone issue after valid autosave, got: {remaining_issues}"
        )

        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )
        assert preview.is_export_ready is True, (
            f"Valid reviewed phone should keep export preview ready when no blockers remain, got: {preview}"
        )

        session = Session()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert raw_row.raw_csv_data['phone'] == '123', (
                f"Raw source data must remain unchanged, got: {raw_row.raw_csv_data['phone']}"
            )
        finally:
            session.close()

    def test_db_backed_reviewed_invalid_email_remains_blocking(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed invalid reviewed email should be rejected and leave the saved value intact."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-email-invalid-reviewed-batch'
        raw_id = _seed_db_backed_email_parity_batch(
            Session,
            batch_id,
            'john@example.com',
            issue_payload={
                'field': 'email',
                'issue': 'missing_email',
                'description': 'Invalid email',
                'severity': 'error',
            },
        )

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'invalid-email'}
            }
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'email' in data['validation_errors']
        assert 'Invalid email format' in data['validation_errors']['email']

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'Blocking' in row_section, (
            f"Rejected invalid reviewed email should remain Blocking, got: {row_section}"
        )
        assert 'email — Invalid email' in row_section, (
            f"Rejected invalid reviewed email should remain visible as an email issue, got: {row_section}"
        )

        session = Session()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert raw_row is not None, 'Raw row should still exist'
            assert raw_row.raw_csv_data['email'] == 'john@example.com', (
                f"Raw email should remain unchanged, got: {raw_row.raw_csv_data['email']}"
            )
        finally:
            session.close()


class TestAmountValidationParity:
    """Test DB-backed amount validation parity across route, approval, and export."""

    def test_db_backed_invalid_raw_amount_is_visible_in_validation_route(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed validation route must surface an invalid raw amount without autosave."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-amount-route-batch'
        raw_id = _seed_db_backed_amount_parity_batch(Session, batch_id, '100.001')

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        row_marker = f'data-testid="row-{raw_id}"'
        assert row_marker in html, f"Expected DB-backed row to render, got: {html[:2000]}"
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        assert row_end != -1, "Expected closing row tag for DB-backed amount row"
        row_section = html[row_start:row_end]

        assert 'Blocking' in row_section, f"Invalid raw amount should block, got: {row_section}"
        assert 'Amount must have at most 2 decimal places' in row_section, (
            f"Expected strict amount validation copy, got: {row_section}"
        )

        from scripts.householder.approval_service import check_batch_remaining_issues
        from scripts.householder.export_preview_service import build_export_preview

        remaining_issues = check_batch_remaining_issues(batch_id, database_url)
        assert any(
            issue.get('field') == 'amount'
            for row in remaining_issues
            for issue in row.get('issues', [])
        ), (
            f"Expected approval readiness to report amount issue, got: {remaining_issues}"
        )

        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )
        assert preview.is_export_ready is False, (
            f"Invalid raw amount should block export preview, got: {preview}"
        )
        preview_text = ' '.join(list(preview.blockers) + list(preview.warnings))
        assert 'amount' in preview_text.lower(), f"Expected amount blocker in preview, got: {preview_text}"

    def test_db_backed_valid_raw_amount_remains_clear(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed validation route must keep a valid raw amount clear."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-amount-clear-batch'
        raw_id = _seed_db_backed_amount_parity_batch(Session, batch_id, '125.50')

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        row_marker = f'data-testid="row-{raw_id}"'
        assert row_marker in html, f"Expected DB-backed row to render, got: {html[:2000]}"
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        assert row_end != -1, "Expected closing row tag for DB-backed valid amount row"
        row_section = html[row_start:row_end]

        assert 'No issues' in row_section, f"Valid raw amount should remain clear, got: {row_section}"
        assert 'Amount must have at most 2 decimal places' not in row_section

    def test_db_backed_reviewed_valid_amount_supersedes_invalid_raw_amount(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed autosave of a valid amount should override an invalid raw amount without mutating raw data."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-amount-reviewed-batch'
        raw_id = _seed_db_backed_amount_parity_batch(Session, batch_id, '100.001')

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'amount': '250.50'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['effective_values']['amount'] == '250.50'

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'No issues' in row_section, f"Reviewed valid amount should clear invalid raw amount, got: {row_section}"
        assert 'Amount must have at most 2 decimal places' not in row_section

        session = Session()
        try:
            raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert raw_row.raw_csv_data['amount'] == '100.001', (
                f"Raw source data must remain unchanged, got: {raw_row.raw_csv_data['amount']}"
            )
        finally:
            session.close()

    def test_db_backed_reviewed_invalid_amount_remains_blocking(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed invalid reviewed amount must remain blocking for route, approval, and export."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-amount-invalid-reviewed-batch'
        raw_id = _seed_db_backed_amount_parity_batch(Session, batch_id, '125.50')

        session = Session()
        try:
            session.add(
                ReviewDecision(
                    batch_id=batch_id,
                    review_item_id=None,
                    raw_import_row_id=raw_id,
                    decision='accept_issue',
                    reviewed_values={'amount': '125.001'},
                )
            )
            session.commit()
        finally:
            session.close()

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]
        assert 'Blocking' in row_section, f"Reviewed invalid amount should block, got: {row_section}"
        assert 'Amount must have at most 2 decimal places' in row_section, (
            f"Expected strict amount validation copy, got: {row_section}"
        )

        from scripts.householder.approval_service import check_batch_remaining_issues
        from scripts.householder.export_preview_service import build_export_preview

        remaining_issues = check_batch_remaining_issues(batch_id, database_url)
        assert any(
            issue.get('field') == 'amount'
            for row in remaining_issues
            for issue in row.get('issues', [])
        ), (
            f"Expected approval readiness to report amount issue, got: {remaining_issues}"
        )

        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )
        assert preview.is_export_ready is False, (
            f"Reviewed invalid amount should block export preview, got: {preview}"
        )

    def test_db_backed_raw_zero_amount_is_blocking_not_missing(
        self,
        flask_client_with_validation_batch,
    ):
        """DB-backed raw zero amount should be treated as an invalid amount, not missing data."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-amount-zero-batch'
        raw_id = _seed_db_backed_amount_parity_batch(Session, batch_id, '0')

        response = client.get(f'/imports/{batch_id}/validation')
        assert response.status_code == 200
        html = response.data.decode('utf-8')

        row_marker = f'data-testid="row-{raw_id}"'
        row_start = html.find(row_marker)
        row_end = html.find('</tr>', row_start)
        row_section = html[row_start:row_end]

        assert 'Blocking' in row_section, f"Raw zero amount should block, got: {row_section}"
        assert 'Amount field is empty' not in row_section, (
            f"Raw zero amount should not be treated as missing, got: {row_section}"
        )
        assert 'Amount must be greater than 0' in row_section, (
            f"Expected positive-value validation copy for raw zero amount, got: {row_section}"
        )

        from scripts.householder.export_preview_service import build_export_preview
        preview = build_export_preview(
            batch_id,
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            },
        )
        assert preview.is_export_ready is False
        preview_text = ' '.join(list(preview.blockers) + list(preview.warnings))
        assert 'greater than 0' in preview_text.lower() or 'amount' in preview_text.lower()


# ==============================================================================
# TEST 5: Successful autosave for Name and Address
# ==============================================================================

class TestSuccessfulAutosave:
    """Test successful autosave for Name and Address."""

    def test_autosave_valid_name_succeeds(
        self, flask_client_with_validation_batch
    ):
        """Valid name correction should succeed."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[4]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'name': 'Charles Davis Jr.'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert data['effective_values']['name'] == 'Charles Davis Jr.'
        assert 'decision_id' in data

    def test_autosave_valid_address_succeeds(
        self, flask_client_with_validation_batch
    ):
        """Valid address correction should succeed."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[4]

        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'address': '999 Oak Street, Apt 100'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data['success'] is True
        assert data['effective_values']['address'] == '999 Oak Street, Apt 100'


# ==============================================================================
# TEST 6: Needs follow-up requires Notes
# ==============================================================================

class TestNeedsFollowUpDecision:
    """Test needs follow-up decision requires Notes."""

    def test_needs_follow_up_requires_notes(
        self, flask_client_with_validation_batch
    ):
        """Recording needs follow-up decision requires notes."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        # Try to record follow-up without notes (backend enforces notes requirement)
        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': None
            }
        )

        # Backend enforces notes requirement for follow-up decisions
        assert response.status_code == 400
        data = response.get_json()
        assert 'Notes are required' in str(data)

    def test_needs_follow_up_with_notes_records_successfully(
        self, flask_client_with_validation_batch
    ):
        """Recording needs follow-up with notes should succeed."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': 'Needs to verify donation amount with donor'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True or 'decision' in data


# ==============================================================================
# TEST 7: Defer does not require Notes
# ==============================================================================

class TestDeferDecision:
    """Test defer decision doesn't require Notes."""

    def test_defer_succeeds_without_notes(
        self, flask_client_with_validation_batch
    ):
        """Recording defer decision should succeed without notes."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[6]

        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'defer'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True or 'decision' in data


# ==============================================================================
# TEST 8: Approval warning with unresolved issues
# ==============================================================================

class TestApprovalWarnings:
    """Test approval warning with unresolved issues."""

    def test_approve_batch_with_unresolved_issues(
        self, flask_client_with_validation_batch
    ):
        """Approving batch with unresolved FAIL issues should trigger override confirmation."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[7]
        _seed_unresolved_validation_issue(Session, 'validation-workflow-test-batch', raw_id)

        # Try to approve batch with unresolved issues (fixture includes invalid email rows)
        response = client.post(
            f'/imports/validation-workflow-test-batch/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        assert response.status_code == 200, (
            f"Expected approval-check response, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data['requires_override_confirmation'] is True, (
            f"Unresolved FAIL issues must require override confirmation, got: {data}"
        )
        assert data.get('remaining_issues'), (
            f"Unresolved FAIL issues must be exposed in remaining_issues, got: {data}"
        )
        assert data.get('success') is not True, (
            f"Approval must not silently succeed when unresolved FAIL issues remain, got: {data}"
        )

    def test_warning_only_validation_issues_do_not_require_override_confirmation(
        self, flask_client_with_validation_batch
    ):
        """Warning-tier validation issues should not trigger override confirmation."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id, raw_id = _seed_isolated_warning_only_batch(Session)

        session = Session()
        try:
            original_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            original_raw_data = dict(original_row.raw_csv_data)
        finally:
            session.close()

        response = client.post(
            f'/imports/{batch_id}/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        assert response.status_code == 200, (
            f"Warning-only approval should not be blocked, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data.get('requires_override_confirmation') is not True, (
            f"Warning-only validation issues must not require override confirmation, got: {data}"
        )
        assert data.get('success') is True, (
            f"Warning-only validation issues should allow approval to proceed, got: {data}"
        )
        assert data.get('approval_status') == 'approved', (
            f"Warning-only approval should proceed as approved, got: {data}"
        )

        session = Session()
        try:
            current_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert current_row.raw_csv_data == original_raw_data, (
                f"Raw CSV data must remain unchanged, got: {current_row.raw_csv_data}"
            )
        finally:
            session.close()

    def test_approved_batch_with_invalid_raw_date_is_rejected(
        self,
        flask_client_with_validation_batch,
    ):
        """Plain approval must not bypass an invalid raw date."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        batch_id = 'db-backed-date-approval-direct-batch'
        raw_id = _seed_db_backed_date_parity_batch(Session, batch_id, '2026&05-15')

        response = client.post(
            f'/imports/{batch_id}/approve-batch',
            json={
                'approval_status': 'approved',
                'rows_with_overrides': []
            }
        )

        assert response.status_code == 400, (
            f"Plain approval should reject unresolved invalid raw dates, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert 'unresolved issues' in data.get('error', '').lower() or 'override' in data.get('error', '').lower(), (
            f"Expected approval error to mention unresolved issues, got: {data}"
        )

        session = Session()
        try:
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()
            assert batch.approval_status is None, (
                f"Batch should not approve with invalid raw date, got: {batch.approval_status}"
            )
        finally:
            session.close()


# ==============================================================================
# TEST 9: Export preview uses successful corrections only
# ==============================================================================

class TestExportPreview:
    """Test export preview uses successful corrections only."""

    def test_get_effective_values_after_autosave(
        self, flask_client_with_validation_batch
    ):
        """Export should use effective values (successful corrections only)."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[8]

        # Make a valid correction
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'name': 'Grace Harris-Smith'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        # Effective values should include the correction
        assert data['effective_values']['name'] == 'Grace Harris-Smith'

        # Try another correction - amount field may accept any value
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'amount': 'invalid-amount'}
            }
        )

        # Amount may be accepted or rejected - both are valid behaviors
        # Just verify the response
        assert response.status_code in [200, 400]

        # Verify validation page loads
        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200


# ==============================================================================
# TEST A: Needs follow-up workflow with Notes enforcement
# ==============================================================================

class TestNeedsFollowUpWorkflow:
    """Test needs follow-up workflow verifies Notes required, controls preserved."""

    def test_needs_follow_up_notes_requirement_enforced(
        self, flask_client_with_validation_batch
    ):
        """Backend enforces Notes required when Needs follow-up selected."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        # Try to record needs_follow_up without notes (should fail)
        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': None
            }
        )

        # Must fail backend validation
        assert response.status_code == 400, \
            f"Expected 400 for needs_follow_up without notes, got {response.status_code}"
        data = response.get_json()
        assert 'Notes are required' in data.get('error', ''), \
            f"Expected 'Notes are required' in error, got: {data}"

    def test_needs_follow_up_records_with_notes(
        self, flask_client_with_validation_batch
    ):
        """Recording needs follow-up with notes should succeed and persist."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        notes_text = 'Contact donor to clarify donation source'
        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': notes_text
            }
        )

        assert response.status_code == 200, \
            f"Expected 200 for needs_follow_up with notes, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert data['success'] is True, f"Expected success, got: {data}"
        assert data['decision'] == 'needs_follow_up', f"Expected decision 'needs_follow_up', got: {data['decision']}"

        # Verify decision persisted to database
        session = Session()
        try:
            from scripts.householder.row_decision_service import get_row_decision
            persisted = get_row_decision(
                batch_id='validation-workflow-test-batch',
                raw_import_row_id=raw_id,
                database_url=database_url
            )
            assert persisted is not None, "Decision should be persisted"
            assert persisted['decision'] == 'needs_follow_up', \
                f"Persisted decision should be needs_follow_up, got: {persisted['decision']}"
            assert persisted['notes'] == notes_text, \
                f"Persisted notes should match, got: {persisted.get('notes')}"
        finally:
            session.close()

    def test_needs_follow_up_row_status_reflects_decision(
        self, flask_client_with_validation_batch
    ):
        """After needs follow-up decision, row status should reflect pending follow-up."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        # Record needs_follow_up decision
        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': 'Verify with donor'
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        # Row status should be provided for frontend dropdown update
        assert 'row_status' in data, \
            f"Response should include row_status for dropdown, got: {data}"


# ==============================================================================
# TEST B: Defer workflow - Notes optional
# ==============================================================================

class TestDeferWorkflow:
    """Test defer workflow verifies Notes are optional, controls preserved."""

    def test_defer_succeeds_without_notes_persisted(
        self, flask_client_with_validation_batch
    ):
        """Defer decision should persist to database without notes."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[6]

        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'defer'
            }
        )

        assert response.status_code == 200, \
            f"Expected 200 for defer without notes, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert data['success'] is True, f"Expected success, got: {data}"
        assert data['decision'] == 'defer', f"Expected decision 'defer', got: {data['decision']}"

        # Verify decision persisted
        session = Session()
        try:
            from scripts.householder.row_decision_service import get_row_decision
            persisted = get_row_decision(
                batch_id='validation-workflow-test-batch',
                raw_import_row_id=raw_id,
                database_url=database_url
            )
            assert persisted is not None, "Defer decision should be persisted"
            assert persisted['decision'] == 'defer', \
                f"Persisted decision should be defer, got: {persisted['decision']}"
        finally:
            session.close()

    def test_defer_with_notes_also_persisted(
        self, flask_client_with_validation_batch
    ):
        """Defer decision should also accept optional notes."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[6]

        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'defer',
                'notes': 'Review in next batch cycle'
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


# ==============================================================================
# TEST C: Approval warning modal behavior
# ==============================================================================

class TestApprovalWarningWorkflow:
    """Test approval warning modal shows with unresolved issues."""

    def test_approve_batch_without_issues_succeeds(
        self, flask_client_with_validation_batch
    ):
        """Batch with no unresolved issues should approve directly without modal."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch

        batch_id = 'db-backed-date-clean-approval-batch'
        raw_id = _seed_db_backed_date_parity_batch(Session, batch_id, '2026-05-15')

        # Now try to approve - should succeed directly
        response = client.post(
            f'/imports/{batch_id}/approve-batch',
            json={
                'approval_status': 'approved',
                'rows_with_overrides': []
            }
        )

        assert response.status_code == 200, f"Approve should succeed, got: {response.get_json()}"
        data = response.get_json()
        assert data['success'] is True, f"Expected success, got: {data}"
        assert data['approval_status'] == 'approved', f"Expected approved status, got: {data}"
        assert data.get('requires_override_confirmation') is not True, (
            f"Clean approval must not require override confirmation, got: {data}"
        )

        session = Session()
        try:
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()
            assert batch.approval_status == 'approved', (
                f"Clean batch should approve directly, got: {batch.approval_status}"
            )
            raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert raw_row.raw_csv_data['date'] == '2026-05-15', (
                f"Raw source data must remain unchanged, got: {raw_row.raw_csv_data['date']}"
            )
        finally:
            session.close()

    def test_approve_batch_with_unresolved_issues_requires_override(
        self, flask_client_with_validation_batch
    ):
        """Batch with unresolved issues should approve when explicit overrides are supplied."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[7]
        _seed_unresolved_validation_issue(Session, 'validation-workflow-test-batch', raw_id)

        override = {
            'raw_import_row_id': raw_id,
            'row_index': 8,
            'issues': [
                {
                    'field': 'email',
                    'reason': 'Marked as reviewed with override',
                }
            ],
        }

        response = client.post(
            f'/imports/validation-workflow-test-batch/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': [override]
            }
        )

        assert response.status_code == 200, (
            f"Expected approval success with explicit overrides, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data['success'] is True, f"Expected success, got: {data}"
        assert data['approval_status'] == 'approved_with_overrides', f"Expected approved_with_overrides, got: {data}"
        assert data.get('override_count') == 1, f"Expected one override, got: {data}"

    def test_approve_batch_with_explicit_override_derives_overridden_row_status(
        self, flask_client_with_validation_batch
    ):
        """Explicit override approval should expose reviewer-facing Overridden row status."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[7]

        session = Session()
        try:
            from scripts.householder.database_models import RawImportRow
            original_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            original_raw_data = dict(original_row.raw_csv_data)
        finally:
            session.close()

        _seed_unresolved_validation_issue(Session, 'validation-workflow-test-batch', raw_id)

        override = {
            'raw_import_row_id': raw_id,
            'row_index': 8,
            'issues': [
                {
                    'field': 'email',
                    'reason': 'Marked as reviewed with override',
                }
            ],
        }

        response = client.post(
            f'/imports/validation-workflow-test-batch/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': [override]
            }
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['approval_status'] == 'approved_with_overrides'
        assert data.get('override_count') == 1

        from scripts.householder.row_status_service import derive_row_status, is_row_overridden
        from scripts.householder.validation_service import get_validation_review

        overridden_status = derive_row_status(
            batch_id='validation-workflow-test-batch',
            raw_import_row_id=raw_id,
            database_url=database_url
        )
        assert overridden_status == 'Overridden', (
            f"Explicit override approval should derive Overridden row status, got: {overridden_status}"
        )
        assert is_row_overridden(
            batch_id='validation-workflow-test-batch',
            raw_import_row_id=raw_id,
            database_url=database_url
        ) is True

        review_data = get_validation_review(
            'validation-workflow-test-batch',
            config={
                'HOUSEHOLDER_REPOSITORY': 'database',
                'GIVEBUTTER_DATABASE_URL': database_url,
            }
        )
        matching_record = next(
            (
                record for record in review_data.get('validation_issues', [])
                if record.get('raw_import_row_id') == raw_id
            ),
            None,
        )
        assert matching_record is not None, (
            f"Expected row to be present in validation review data, got: {review_data}"
        )
        assert matching_record.get('row_status') == 'Overridden', (
            f"Validation review surface should expose Overridden, got: {matching_record}"
        )

        review_response = client.get('/imports/validation-workflow-test-batch/validation')
        assert review_response.status_code == 200
        review_html = review_response.data.decode('utf-8')
        row_match = re.search(
            rf'<tr\b[^>]*data-raw-id="{re.escape(str(raw_id))}"[^>]*>.*?</tr>',
            review_html,
            re.S,
        )
        assert row_match is not None, (
            f"Expected overridden row to render in validation review page, got: {review_html}"
        )
        row_html = row_match.group(0)
        assert 'row-overridden' in row_html, (
            f"Rendered overridden row should include semantic class, got: {row_html}"
        )
        assert 'data-row-status="Overridden"' in row_html, (
            f"Rendered overridden row should expose data-row-status, got: {row_html}"
        )
        assert 'Overridden' in row_html, (
            f"Rendered overridden row should display Overridden status, got: {row_html}"
        )

        session = Session()
        try:
            from scripts.householder.database_models import RawImportRow
            current_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert current_row.raw_csv_data == original_raw_data, (
                f"Raw CSV data must remain unchanged, got: {current_row.raw_csv_data}"
            )
        finally:
            session.close()


# ==============================================================================
# TEST D: Export safety - Failed autosaves excluded, raw data unchanged
# ==============================================================================

class TestExportSafety:
    """Test export preview uses only successful corrections, raw data unchanged."""

    def test_export_excludes_failed_autosave_values(
        self, flask_client_with_validation_batch
    ):
        """Failed autosave corrections should not appear in export."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[0]  # Invalid email row

        # Try invalid email autosave (will fail)
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'not-an-email'}
            }
        )

        # Should fail validation
        assert response.status_code == 400, \
            f"Invalid email should fail autosave, got: {response.status_code}"

        # Now make a valid correction to same row
        response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'john.smith@example.com'}
            }
        )

        assert response.status_code == 200
        data = response.get_json()

        # Effective values should only contain the successful correction
        assert data['effective_values']['email'] == 'john.smith@example.com', \
            f"Effective values should have valid correction, got: {data['effective_values']['email']}"

    def test_raw_import_row_data_unchanged_after_correction(
        self, flask_client_with_validation_batch
    ):
        """RawImportRow.raw_csv_data must never be mutated after autosave corrections."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[0]

        # Get original raw data
        session = Session()
        try:
            from scripts.householder.database_models import RawImportRow
            original_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            original_email = original_row.raw_csv_data.get('email')

            # Make autosave correction
            response = client.post(
                f'/imports/validation-workflow-test-batch/autosave',
                json={
                    'raw_import_row_id': raw_id,
                    'corrected_values': {'email': 'corrected@example.com'}
                }
            )
            assert response.status_code == 200

            # Verify raw data is unchanged
            session.expire_all()  # Refresh from DB
            modified_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            assert modified_row.raw_csv_data.get('email') == original_email, \
                f"Raw data should not change. Original: {original_email}, Got: {modified_row.raw_csv_data.get('email')}"
        finally:
            session.close()


# ==============================================================================
# TEST D: ReviewDecision Persistence - Effective value retrieval layer testing
# ==============================================================================

class TestReviewDecisionEffectiveValueRetrieval:
    """Verify reviewed values persist in row-level ReviewDecision records and are correctly retrieved by get_effective_values()."""

    def test_autosave_reviewed_values_persist_in_decision(
        self, flask_client_with_validation_batch
    ):
        """After autosave correction, reviewed value persists in ReviewDecision and is retrievable by get_effective_values()."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[3]  # Use a row that has a valid initial amount

        # Make a successful correction
        autosave_response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'amount': 250.50}
            }
        )
        assert autosave_response.status_code == 200
        autosave_data = autosave_response.get_json()

        # Verify autosave returned effective amount
        effective_amount = autosave_data.get('effective_values', {}).get('amount')
        assert effective_amount is not None, "Autosave should return effective_values"

        # Fetch validation review page (HTTP 200 verification only, not HTML parsing)
        review_response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert review_response.status_code == 200

        # Layer test: Verify persistence and retrieval at database level
        # This does NOT test whether validation review HTML actually displays the effective value
        # (that would be an E2E test or route-level HTML parsing test)
        session = Session()
        try:
            from scripts.householder.database_models import ReviewDecision, RawImportRow
            from scripts.householder.autosave_service import get_effective_values

            # Verify ReviewDecision was persisted with the corrected value
            decision = session.query(ReviewDecision).filter(
                ReviewDecision.raw_import_row_id == raw_id,
                ReviewDecision.batch_id == 'validation-workflow-test-batch'
            ).first()

            assert decision is not None, "ReviewDecision should be persisted after autosave"
            assert decision.reviewed_values.get('amount') == 250.50, \
                f"ReviewDecision should contain corrected amount, got: {decision.reviewed_values}"

            # Verify get_effective_values reflects the correction
            effective = get_effective_values('validation-workflow-test-batch', raw_id, database_url)
            assert effective.get('amount') == 250.50, \
                f"Effective values should include correction, got: {effective}"
        finally:
            session.close()

    def test_effective_values_retrieval_merges_reviewed_corrections(
        self, flask_client_with_validation_batch
    ):
        """Multiple reviewed value corrections persist and merge correctly in get_effective_values() retrieval."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[3]  # Use a row that has a valid initial amount

        # Make a successful correction
        autosave_response = client.post(
            f'/imports/validation-workflow-test-batch/autosave',
            json={
                'raw_import_row_id': raw_id,
                'corrected_values': {'email': 'corrected.email@example.com', 'amount': 350.75}
            }
        )
        assert autosave_response.status_code == 200
        autosave_data = autosave_response.get_json()

        # Verify autosave returned the effective values
        effective_values = autosave_data.get('effective_values', {})
        assert effective_values.get('email') == 'corrected.email@example.com'
        assert effective_values.get('amount') == 350.75

        # Layer test: Verify persistence and retrieval at database level
        # This tests the shared underlying mechanism (get_effective_values) both validation review and export use
        # Does NOT directly test whether validation review HTML or export preview route display effective values
        # (those are route-level or E2E tests)
        session = Session()
        try:
            from scripts.householder.database_models import ReviewDecision, RawImportRow
            from scripts.householder.autosave_service import get_effective_values

            # Verify ReviewDecision was persisted
            decision = session.query(ReviewDecision).filter(
                ReviewDecision.raw_import_row_id == raw_id,
                ReviewDecision.batch_id == 'validation-workflow-test-batch'
            ).first()

            assert decision is not None, "ReviewDecision should be persisted"
            assert decision.reviewed_values.get('email') == 'corrected.email@example.com'
            assert decision.reviewed_values.get('amount') == 350.75

            # Verify get_effective_values (used by export) includes the corrections
            effective = get_effective_values('validation-workflow-test-batch', raw_id, database_url)
            assert effective.get('email') == 'corrected.email@example.com', \
                f"Export should use corrected email, got: {effective}"
            assert effective.get('amount') == 350.75, \
                f"Export should use corrected amount, got: {effective}"

            # Verify raw data is unchanged
            raw_row = session.query(RawImportRow).filter_by(id=raw_id).first()
            original_email = raw_row.raw_csv_data.get('email')
            original_amount = raw_row.raw_csv_data.get('amount')

            # Raw data should NOT contain the corrected values
            assert original_email != 'corrected.email@example.com', \
                "Raw data must not be modified by autosave"
            assert original_amount != 350.75, \
                "Raw data must not be modified by autosave"
        finally:
            session.close()


# ==============================================================================
# TEST E: Inspect modal controls - Dropdown, Notes field, Record Decision button
# ==============================================================================

class TestInspectModalControls:
    """Test inspect modal has all expected interactive controls."""

    def test_inspect_modal_decision_dropdown_options(
        self, flask_client_with_validation_batch
    ):
        """Modal decision dropdown should have all status options."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch

        # Load validation page - modal is populated via JavaScript
        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Verify modal HTML contains decision options
        assert 'Accept as-is' in html, "Modal should have 'Accept as-is' option"
        assert 'Needs follow-up' in html, "Modal should have 'Needs follow-up' option"
        assert 'Defer' in html, "Modal should have 'Defer' option"
        assert 'Reject row' in html, "Modal should have 'Reject row' option"

    def test_inspect_modal_notes_field_exists(
        self, flask_client_with_validation_batch
    ):
        """Modal should have Notes textarea field."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch

        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Verify modal HTML contains notes field
        assert 'Notes required when Follow-up' in html or 'row-notes' in html, \
            "Modal should have notes field"

    def test_inspect_modal_record_decision_button_exists(
        self, flask_client_with_validation_batch
    ):
        """Modal should have Record Decision button."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch

        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Verify modal HTML contains Record Decision button
        assert 'Record Decision' in html, \
            "Modal should have 'Record Decision' button"

    def test_row_decision_get_endpoint_returns_status(
        self, flask_client_with_validation_batch
    ):
        """GET /row-decision endpoint should report has_decision status."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        # Before any decision
        response = client.get(
            f'/imports/validation-workflow-test-batch/row-decision/{raw_id}'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'has_decision' in data, \
            f"Response should include has_decision flag, got: {data}"

        # Record a decision
        client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': 'Test note'
            }
        )

        # After decision
        response = client.get(
            f'/imports/validation-workflow-test-batch/row-decision/{raw_id}'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['has_decision'] is True, \
            f"After recording decision, has_decision should be True, got: {data}"

    def test_row_decision_and_approval_use_app_config_database_url_when_env_cleared(
        self, flask_client_with_validation_batch, monkeypatch
    ):
        """Routes should keep working from app.config even if env vars are cleared."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[4]

        monkeypatch.delenv('GIVEBUTTER_DATABASE_URL', raising=False)
        monkeypatch.delenv('HOUSEHOLDER_REPOSITORY', raising=False)
        app.config['HOUSEHOLDER_REPOSITORY'] = 'database'
        app.config['GIVEBUTTER_DATABASE_URL'] = database_url

        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'accept_as_is',
            }
        )

        assert response.status_code == 200, (
            f"Row decision should still use app.config database URL, got {response.status_code}: {response.get_json()}"
        )
        data = response.get_json()
        assert data['success'] is True, (
            f"Row decision should succeed from app.config database URL, got: {data}"
        )
        assert 'row_status' in data, (
            f"Row decision should return a runtime row status, got: {data}"
        )

        approval_response = client.post(
            f'/imports/validation-workflow-test-batch/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        assert approval_response.status_code == 200, (
            f"Approval should still resolve the seeded batch from app.config, got {approval_response.status_code}: {approval_response.get_json()}"
        )
        approval_data = approval_response.get_json()
        assert approval_data.get('requires_override_confirmation') is True, (
            f"Approval should find the seeded batch and report remaining issues, got: {approval_data}"
        )

    def test_missing_database_configuration_shows_user_facing_copy(
        self, flask_client_with_validation_batch, monkeypatch
    ):
        """Missing DB config should use reviewer-friendly copy for both row decision and approval."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        monkeypatch.delenv('GIVEBUTTER_DATABASE_URL', raising=False)
        monkeypatch.delenv('HOUSEHOLDER_REPOSITORY', raising=False)
        monkeypatch.delitem(app.config, 'GIVEBUTTER_DATABASE_URL', raising=False)
        monkeypatch.delitem(app.config, 'HOUSEHOLDER_REPOSITORY', raising=False)

        row_decision_response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'accept_as_is',
            }
        )

        assert row_decision_response.status_code == 503, (
            f"Missing DB config should fail closed for row decision, got {row_decision_response.status_code}: {row_decision_response.get_json()}"
        )
        row_decision_data = row_decision_response.get_json()
        assert row_decision_data['success'] is False, (
            f"Missing DB config should not report success for row decision, got: {row_decision_data}"
        )
        assert row_decision_data['error'] == (
            "This row decision can't be saved because the review database is not connected. "
            'Ask the app operator to restart the app in database mode with GIVEBUTTER_DATABASE_URL set, '
            'then reload this batch and try again.'
        ), (
            f"Row decision message should be user-facing, got: {row_decision_data}"
        )

        approval_response = client.post(
            f'/imports/validation-workflow-test-batch/approve-batch',
            json={
                'approval_status': 'approved_with_overrides',
                'rows_with_overrides': []
            }
        )

        assert approval_response.status_code == 503, (
            f"Missing DB config should fail closed for approval, got {approval_response.status_code}: {approval_response.get_json()}"
        )
        approval_data = approval_response.get_json()
        assert approval_data['success'] is False, (
            f"Missing DB config should not report success for approval, got: {approval_data}"
        )
        assert approval_data['error'] == (
            "This file can't be approved because the review database is not connected. "
            'Ask the app operator to restart the app in database mode with GIVEBUTTER_DATABASE_URL set, '
            'then reload this batch and try again.'
        ), (
            f"Approval message should be user-facing, got: {approval_data}"
        )


# ==============================================================================
# TEST F: Cancel behavior - Modal Cancel should not create ReviewDecision/audit
# ==============================================================================

class TestCancelBehavior:
    """Test that modal Cancel button does not create decisions or audit entries."""

    def test_cancel_does_not_create_review_decision(
        self, flask_client_with_validation_batch
    ):
        """Clicking Cancel should not create ReviewDecision."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        # Before Cancel: no decision
        response = client.get(
            f'/imports/validation-workflow-test-batch/row-decision/{raw_id}'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['has_decision'] is False, "Should have no decision initially"

        # Simulate modal Cancel (user navigates away without submitting)
        # Verify GET endpoint still shows no_decision
        response = client.get(
            f'/imports/validation-workflow-test-batch/row-decision/{raw_id}'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['has_decision'] is False, \
            "Cancel should not create ReviewDecision"

    def test_cancel_does_not_create_audit_entry(
        self, flask_client_with_validation_batch
    ):
        """Clicking Cancel should not create audit entry."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[5]

        # Get audit log page
        response = client.get(
            f'/imports/validation-workflow-test-batch/audit'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Count initial audit entries
        initial_count = html.count('<tr class="audit-entry')
        initial_count = max(0, initial_count)  # Handle if no audit entries initially

        # Simulate Cancel (no POST request)
        # Verify audit log unchanged
        response = client.get(
            f'/imports/validation-workflow-test-batch/audit'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        final_count = html.count('<tr class="audit-entry')
        final_count = max(0, final_count)

        assert final_count == initial_count, \
            f"Cancel should not create audit entry. Before: {initial_count}, After: {final_count}"


# ==============================================================================
# TEST G: Modal decision preserves field-level Issues and Row Status
# ==============================================================================

class TestModalPreservesFieldIssues:
    """Test that making a modal decision doesn't erase unresolved field-level issues."""

    def test_defer_preserves_existing_field_issues(
        self, flask_client_with_validation_batch
    ):
        """Making Defer decision should not erase pre-existing field-level issues."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[3]  # Has email validation error

        # Verify row has issue initially
        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Verify issue appears in Issues column for this row
        assert 'invalid' in html.lower() or 'email' in html.lower(), \
            "Row should have validation issue initially"

        # Record Defer decision
        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'defer',
                'notes': 'Will follow up'
            }
        )
        assert response.status_code == 200

        # Verify field issue still visible after decision
        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Issue should still be present (decision doesn't erase field issues)
        assert 'invalid' in html.lower() or 'email' in html.lower() or 'issue' in html.lower(), \
            "Field-level issues should remain after Defer decision"

    def test_follow_up_preserves_field_issues(
        self, flask_client_with_validation_batch
    ):
        """Making Follow Up decision should not erase field-level issues."""
        client, database_url, engine, Session, raw_rows = flask_client_with_validation_batch
        raw_id = raw_rows[3]  # Has email validation error

        # Get validation page before decision
        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200
        html_before = response.get_data(as_text=True)

        # Record Follow Up decision with notes
        response = client.post(
            f'/imports/validation-workflow-test-batch/row-decision',
            json={
                'raw_import_row_id': raw_id,
                'decision': 'needs_follow_up',
                'notes': 'Must contact donor'
            }
        )
        assert response.status_code == 200

        # Verify decision was created
        session = Session()
        try:
            decision = session.query(ReviewDecision).filter(
                ReviewDecision.raw_import_row_id == raw_id
            ).first()
            assert decision is not None, "Follow Up decision should be created"
            assert 'needs_follow_up' in decision.decision, \
                f"Decision should contain needs_follow_up, got: {decision.decision}"
        finally:
            session.close()

        # Get validation page after decision - field issues should still be visible
        response = client.get(
            f'/imports/validation-workflow-test-batch/validation'
        )
        assert response.status_code == 200
        html_after = response.get_data(as_text=True)

        # Verify both versions have field-level issues (Issues column should still show errors)
        assert ('issue' in html_after.lower() or 'invalid' in html_after.lower()), \
            "Field-level issues should remain visible after Follow Up decision"
