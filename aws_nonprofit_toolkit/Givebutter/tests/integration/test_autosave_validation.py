"""
Integration tests for autosave validation (validate before save).

Critical: Invalid corrections should NOT be saved.
- Invalid email → rejected, not saved
- Invalid phone → rejected, not saved
- Valid corrections → saved with "Saved" feedback
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uploader.app import app
from scripts.householder.database_models import (
    Base, ImportBatch, RawImportRow, ReviewItem, ReviewItemSubject,
    ReviewDecision, create_db_engine
)
from scripts.householder.autosave_service import get_effective_values, validate_corrected_values
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
def client_with_db(temp_db, monkeypatch):
    """Flask test client configured with temporary database."""
    database_url, engine = temp_db

    # Configure repository selection and database URL so autosave uses the DB-backed path.
    monkeypatch.setenv('HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setenv('GIVEBUTTER_DATABASE_URL', database_url)
    monkeypatch.setitem(app.config, 'HOUSEHOLDER_REPOSITORY', 'database')
    monkeypatch.setitem(app.config, 'GIVEBUTTER_DATABASE_URL', database_url)

    # Configure Flask app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client, database_url


def setup_validation_batch(database_url):
    """Set up a batch with email and phone validation issues."""
    SessionLocal = sessionmaker(bind=create_db_engine(database_url))
    session = SessionLocal()

    try:
        batch = ImportBatch(
            id='test-validation',
            filename='test.csv',
            upload_timestamp=datetime.now(timezone.utc),
            status='pending',
            raw_row_count=1,
        )
        session.add(batch)
        session.flush()

        raw_row = RawImportRow(
            batch_id='test-validation',
            row_index=0,
            raw_csv_data={
                'transaction_id': 'TX001',
                'date': '2024-01-01',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'jane.smith@gmial.com',  # Email typo
                'phone': '555-0001',              # Phone too short
                'amount': '100.00',
                'address': '123 Main St',
            }
        )
        session.add(raw_row)
        session.flush()

        # Email validation issue
        email_issue = ReviewItem(
            batch_id='test-validation',
            item_type='validation',
            status=None,
            confidence=0.95,
            payload_json={
                'field': 'email',
                'reason': 'possible_typo',
                'severity': 'warning',
                'description': 'Invalid email format (gmial.com typo)'
            },
        )
        session.add(email_issue)
        session.flush()

        # Phone validation issue
        phone_issue = ReviewItem(
            batch_id='test-validation',
            item_type='validation',
            status=None,
            confidence=0.95,
            payload_json={
                'field': 'phone',
                'reason': 'format',
                'severity': 'warning',
                'description': 'Phone number too short'
            },
        )
        session.add(phone_issue)
        session.flush()

        # Link issues to row
        email_subject = ReviewItemSubject(
            review_item_id=email_issue.id,
            subject_type='import_raw_row',
            subject_id=raw_row.id,
            role='primary',
        )
        session.add(email_subject)

        phone_subject = ReviewItemSubject(
            review_item_id=phone_issue.id,
            subject_type='import_raw_row',
            subject_id=raw_row.id,
            role='primary',
        )
        session.add(phone_subject)
        session.commit()

        return batch.id, raw_row.id
    finally:
        session.close()


@pytest.mark.integration
class TestAutosaveValidation:
    """Test suite for autosave validation (validate-before-save)."""

    def test_validate_corrected_values_invalid_email(self):
        """Unit test: validate_corrected_values rejects invalid email."""
        is_valid, errors = validate_corrected_values({'email': 'invalid-email'})
        assert is_valid is False
        assert 'email' in errors
        assert 'Invalid email format' in errors['email']

    def test_validate_corrected_values_invalid_phone(self):
        """Unit test: validate_corrected_values rejects invalid phone."""
        is_valid, errors = validate_corrected_values({'phone': '555'})
        assert is_valid is False
        assert 'phone' in errors
        assert 'Invalid phone' in errors['phone']

    def test_validate_corrected_values_valid_email(self):
        """Unit test: validate_corrected_values accepts valid email."""
        is_valid, errors = validate_corrected_values({'email': 'user@example.com'})
        assert is_valid is True
        assert errors is None

    def test_validate_corrected_values_valid_phone(self):
        """Unit test: validate_corrected_values accepts valid phone."""
        is_valid, errors = validate_corrected_values({'phone': '(415) 555-1234'})
        assert is_valid is True
        assert errors is None

    @pytest.mark.parametrize('good_amount', ['.50', '5.', '0.50', '5.00', '$1,250.50'])
    def test_validate_corrected_values_valid_amount_formats(self, good_amount):
        """Canonical amount validation should accept shorthand and formatted valid amounts."""
        is_valid, errors = validate_corrected_values({'amount': good_amount})
        assert is_valid is True, f"Expected amount '{good_amount}' to validate"
        assert errors is None

    def test_validate_corrected_values_invalid_date(self):
        """Unit test: validate_corrected_values rejects invalid date syntax."""
        is_valid, errors = validate_corrected_values({'date': '2026&05-15'})
        assert is_valid is False
        assert 'date' in errors
        assert 'YYYY-MM-DD' in errors['date']

    def test_validate_corrected_values_valid_date(self):
        """Unit test: validate_corrected_values accepts strict ISO date."""
        is_valid, errors = validate_corrected_values({'date': '2026-05-15'})
        assert is_valid is True
        assert errors is None

    def test_autosave_invalid_email_not_saved(self, client_with_db):
        """CRITICAL: Invalid email correction is REJECTED and NOT saved."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Try to autosave invalid email
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'email': 'invalid-email-no-at-sign'  # Invalid
                }
            }
        )

        # Should fail
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'validation_errors' in result
        assert 'email' in result['validation_errors']

        # Verify NOT saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            # Should have no decisions (not saved)
            assert len(decisions) == 0, f"Invalid email was saved! {decisions}"
        finally:
            session.close()

    def test_autosave_invalid_phone_not_saved(self, client_with_db):
        """CRITICAL: Invalid phone correction is REJECTED and NOT saved."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Try to autosave invalid phone (too short)
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'phone': '555'  # Invalid - too short
                }
            }
        )

        # Should fail
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'validation_errors' in result
        assert 'phone' in result['validation_errors']

        # Verify NOT saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            assert len(decisions) == 0, f"Invalid phone was saved! {decisions}"
        finally:
            session.close()

    def test_autosave_valid_email_saved(self, client_with_db):
        """Valid email correction is ACCEPTED and saved."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Autosave valid email
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'email': 'jane.smith@gmail.com'  # Valid
                }
            }
        )

        # Should succeed
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['effective_values']['email'] == 'jane.smith@gmail.com'

        # Verify saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decision = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).first()
            assert decision is not None
            assert decision.reviewed_values['email'] == 'jane.smith@gmail.com'
        finally:
            session.close()

    def test_autosave_valid_phone_saved(self, client_with_db):
        """Valid phone correction is ACCEPTED and saved."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Autosave valid phone
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'phone': '(415) 555-1234'  # Valid
                }
            }
        )

        # Should succeed
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['effective_values']['phone'] == '(415) 555-1234'

        # Verify saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decision = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).first()
            assert decision is not None
            assert decision.reviewed_values['phone'] == '(415) 555-1234'
        finally:
            session.close()

    def test_autosave_mixed_valid_invalid_not_saved(self, client_with_db):
        """If ANY field is invalid, NONE are saved (all-or-nothing)."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Try to autosave mix of valid email + invalid phone
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {
                    'email': 'jane.smith@gmail.com',  # Valid
                    'phone': '555'  # Invalid
                }
            }
        )

        # Should fail
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'phone' in result['validation_errors']

        # Verify NOTHING saved (all-or-nothing)
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            assert len(decisions) == 0, "Mixed valid/invalid should not save anything"
        finally:
            session.close()

    def test_effective_values_excludes_unsaved_invalid_corrections(self, client_with_db):
        """Effective values don't include invalid corrections that weren't saved."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Try invalid email
        response1 = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'email': 'invalid-email'}
            }
        )
        assert response1.status_code == 400

        # Get effective values - should still be original raw value
        effective = get_effective_values(batch_id, raw_row_id, database_url)
        assert effective['email'] == 'jane.smith@gmial.com', \
            "Invalid correction should not appear in effective values"

    def test_autosave_negative_amount_validation(self, client_with_db):
        """CRITICAL: Negative amount autosave is REJECTED (not saved)."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Try to autosave negative amount
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '-100.00'}
            }
        )

        # Should be rejected (pre-save validation)
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'validation_errors' in result
        assert 'amount' in result['validation_errors']

        # Verify NOT saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            # Should have no decisions (not saved)
            assert len(decisions) == 0, f"Negative amount was saved! {decisions}"
        finally:
            session.close()

    def test_autosave_zero_amount_validation(self, client_with_db):
        """CRITICAL: Zero amount autosave is REJECTED (not saved)."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Try to autosave zero amount
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '0'}
            }
        )

        # Should be rejected (pre-save validation)
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'validation_errors' in result
        assert 'amount' in result['validation_errors']

        # Verify NOT saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            assert len(decisions) == 0, f"Zero amount was saved! {decisions}"
        finally:
            session.close()

    def test_autosave_non_numeric_amount_validation(self, client_with_db):
        """CRITICAL: Non-numeric amount autosave is REJECTED (not saved)."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Try to autosave non-numeric amount
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': 'abc'}
            }
        )

        # Should be rejected (pre-save validation)
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'validation_errors' in result
        assert 'amount' in result['validation_errors']

        # Verify NOT saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            assert len(decisions) == 0, f"Non-numeric amount was saved! {decisions}"
        finally:
            session.close()

    def test_autosave_amount_with_more_than_two_decimals_validation(self, client_with_db):
        """CRITICAL: Amount autosave rejects values with more than two decimal places."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '100.001'}
            }
        )

        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'amount' in result['validation_errors']
        assert '2 decimal places' in result['validation_errors']['amount']

        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            assert len(decisions) == 0, f"Over-precision amount was saved! {decisions}"

            effective = get_effective_values(batch_id, raw_row_id, database_url)
            assert effective['amount'] == '100.00', (
                f"Over-precision amount should not change effective values, got: {effective['amount']}"
            )
        finally:
            session.close()

    def test_valid_amount_no_issue(self, client_with_db):
        """Valid positive amount should not create amount issue."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Autosave valid amount
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '150.50'}
            }
        )

        assert response.status_code == 200

        # Verify no amount issue is created
        from scripts.householder.issue_recalculation_service import recalculate_row_issues
        issues = recalculate_row_issues(batch_id, raw_row_id, database_url)
        amount_issues = [i for i in issues if i.get('field') == 'amount']
        assert len(amount_issues) == 0, "Valid amount should not create issue"

    def test_autosave_amount_with_formatting(self, client_with_db):
        """Valid amount with dollar sign and commas should be accepted and stored canonically."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        # Autosave amount with dollar sign and commas
        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'amount': '$1,250.50'}
            }
        )

        # Should succeed
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['effective_values']['amount'] == '1250.50'

        # Verify saved to database
        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decision = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).first()
            assert decision is not None
            assert decision.reviewed_values['amount'] == '1250.50'
        finally:
            session.close()

    @pytest.mark.parametrize('bad_amount', ['NaN', 'Infinity', '-Infinity', '1,2,3'])
    def test_validate_corrected_values_rejects_non_finite_amounts(self, bad_amount):
        """Canonical amount validation should reject non-finite Decimal values."""
        is_valid, errors = validate_corrected_values({'amount': bad_amount})
        assert is_valid is False
        assert 'amount' in errors
        assert 'format' in errors['amount'].lower() or 'greater than 0' in errors['amount'].lower()

    def test_autosave_invalid_date_not_saved(self, client_with_db):
        """Invalid date correction is rejected and does not replace the saved date."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'date': '2026&05-15'}
            }
        )

        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert 'date' in result['validation_errors']
        assert 'YYYY-MM-DD' in result['validation_errors']['date']

        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decisions = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).all()
            assert len(decisions) == 0, f"Invalid date was saved! {decisions}"

            effective = get_effective_values(batch_id, raw_row_id, database_url)
            assert effective['date'] == '2024-01-01', (
                f"Invalid date should not change effective values, got: {effective['date']}"
            )
        finally:
            session.close()

    def test_autosave_valid_date_saved(self, client_with_db):
        """Valid ISO date correction is accepted and saved."""
        client, database_url = client_with_db
        batch_id, raw_row_id = setup_validation_batch(database_url)

        response = client.post(
            f'/imports/{batch_id}/autosave',
            json={
                'raw_import_row_id': raw_row_id,
                'corrected_values': {'date': '2026-05-15'}
            }
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        assert result['effective_values']['date'] == '2026-05-15'

        SessionLocal = sessionmaker(bind=create_db_engine(database_url))
        session = SessionLocal()
        try:
            decision = session.query(ReviewDecision).filter_by(
                raw_import_row_id=raw_row_id
            ).first()
            assert decision is not None
            assert decision.reviewed_values['date'] == '2026-05-15'
        finally:
            session.close()
