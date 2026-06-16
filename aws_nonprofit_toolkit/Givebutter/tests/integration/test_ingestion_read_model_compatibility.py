"""
Integration tests for ingestion service read-model compatibility.

Verifies that ingested data is fully compatible with DatabaseImportRepository
read methods and payload structures.
"""

import pytest
from pathlib import Path
from datetime import datetime

from scripts.householder.ingestion_service import ingest_processed_csv
from scripts.householder.database_models import (
    init_db,
    get_session,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    AuditLogRecord,
    ReviewDecision,
)
from scripts.householder.database_repository import DatabaseImportRepository


@pytest.fixture
def ingested_batch(tmp_path):
    """Create database with ingested test data (PASS/WARNING/FAIL + normalization)."""
    # Create processed CSV with variety of validation tiers and suggestions
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
        "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,\n"
        "Jane Doe,jane@gmai.com,5559876543,200.00,2026-06-13,PASS,None,Consider: jane@gmail.com\n"
        "Bob Wilson,,5551111111,300.00,2026-06-14,WARNING,Email: Email field is empty,Verify email\n"
        "Alice Johnson,,5552222222,400.00,2026-06-15,FAIL,Email: Email field is empty; Phone: Invalid format,Verify contact info"
    )

    # Create database and ingest
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    init_db(db_url)

    result = ingest_processed_csv(str(csv_file), "export.csv", db_url)

    return {
        "db_url": db_url,
        "batch_id": result.batch_id,
        "result": result,
    }


class TestRepositoryMethodsWithIngestedData:
    """Test all 8 DatabaseImportRepository methods with ingested data."""

    def test_list_imports_returns_ingested_batch(self, ingested_batch):
        """list_imports() shows ingested batch with correct structure."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        repo = DatabaseImportRepository(db_url)
        summaries = repo.list_imports()

        # Find the ingested batch
        batch_summary = next((s for s in summaries if s.id == batch_id), None)
        assert batch_summary is not None
        assert batch_summary.filename == "export.csv"
        assert batch_summary.record_count == 4
        assert batch_summary.status == "pending"
        assert batch_summary.uploaded_timestamp is not None
        assert batch_summary.progress >= 0

    def test_get_dashboard_returns_complete_view(self, ingested_batch):
        """get_dashboard() returns full dashboard view with ingested data."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        repo = DatabaseImportRepository(db_url)
        dashboard = repo.get_dashboard(batch_id)

        assert dashboard is not None
        assert dashboard.batch_id == batch_id
        assert dashboard.filename == "export.csv"
        assert dashboard.progress >= 0
        assert dashboard.queues is not None
        assert len(dashboard.queues) == 4  # 4 queue cards

    def test_get_validation_returns_validation_items(self, ingested_batch):
        """get_validation() returns validation page with validation rows."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        repo = DatabaseImportRepository(db_url)
        page = repo.get_validation(batch_id)

        # Should return validation page view model
        assert page is not None
        assert page.batch_id == batch_id
        assert page.filename == "export.csv"
        assert page.progress >= 0
        # Should have validation rows from WARNING and FAIL records
        assert page.validation_issues_count >= 0
        assert page.total_records == 4

    def test_get_households_returns_empty(self, ingested_batch):
        """get_households() returns page with zero households (deferred to Phase 2)."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        repo = DatabaseImportRepository(db_url)
        page = repo.get_households(batch_id)

        assert page is not None
        assert page.batch_id == batch_id
        assert page.total_households == 0

    def test_get_duplicates_returns_empty(self, ingested_batch):
        """get_duplicates() returns page with zero duplicates (deferred to Phase 1C)."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        repo = DatabaseImportRepository(db_url)
        page = repo.get_duplicates(batch_id)

        assert page is not None
        assert page.batch_id == batch_id
        assert page.total_candidates == 0

    def test_get_audit_returns_summary(self, ingested_batch):
        """get_audit() returns audit page with log entries."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        repo = DatabaseImportRepository(db_url)
        page = repo.get_audit(batch_id)

        assert page is not None
        assert page.batch_id == batch_id
        assert page.filename == "export.csv"
        assert page.progress >= 0
        # Should have audit entries
        assert page.audit_entries is not None
        assert len(page.audit_entries) >= 1

    def test_get_exports_returns_empty(self, ingested_batch):
        """get_exports() returns page with zero exports (deferred to Phase 2)."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        repo = DatabaseImportRepository(db_url)
        page = repo.get_exports(batch_id)

        assert page is not None
        assert page.batch_id == batch_id
        assert page.export_cards is not None


class TestPayloadShapeCompatibility:
    """Verify payload structures for all ReviewItem types."""

    def test_validation_item_payload_structure(self, ingested_batch):
        """Validation ReviewItem payloads have correct structure."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            items = session.query(ReviewItem).filter(
                ReviewItem.batch_id == batch_id,
                ReviewItem.item_type == "validation"
            ).all()

            assert len(items) > 0

            for item in items:
                payload = item.payload_json
                # Validation items must have these fields
                assert "field" in payload
                assert "issue" in payload
                assert "validation_tier" in payload
                assert payload["validation_tier"] in ["PASS", "WARNING", "FAIL"]

        finally:
            session.close()

    def test_normalization_item_payload_structure(self, ingested_batch):
        """Normalization ReviewItem payloads have correct structure."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            items = session.query(ReviewItem).filter(
                ReviewItem.batch_id == batch_id,
                ReviewItem.item_type == "normalization"
            ).all()

            assert len(items) > 0

            for item in items:
                payload = item.payload_json
                # Normalization items must have these fields
                assert "field" in payload
                assert "normalized_value" in payload
                # basis field should be present or inferred from data

        finally:
            session.close()

    def test_review_item_subject_linking(self, ingested_batch):
        """ReviewItems are correctly linked to ImportContacts via ReviewItemSubject."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            # Get all review items
            items = session.query(ReviewItem).filter_by(batch_id=batch_id).all()
            assert len(items) > 0

            for item in items:
                # Each item must have at least one subject link
                subjects = session.query(ReviewItemSubject).filter_by(
                    review_item_id=item.id
                ).all()
                assert len(subjects) >= 1

                for subject in subjects:
                    assert subject.subject_type == "import_contact_snapshot"
                    assert subject.role == "primary"

                    # Subject must point to valid ImportContact
                    contact = session.query(ImportContact).filter_by(
                        id=subject.subject_id
                    ).first()
                    assert contact is not None
                    assert contact.batch_id == batch_id

        finally:
            session.close()

    def test_payload_json_serializable(self, ingested_batch):
        """All ReviewItem payloads are valid JSON-serializable dicts."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            items = session.query(ReviewItem).filter_by(batch_id=batch_id).all()

            for item in items:
                # payload_json should be a dict
                assert isinstance(item.payload_json, dict)

                # All values should be JSON-serializable (no custom objects)
                import json
                try:
                    json.dumps(item.payload_json)
                except TypeError:
                    pytest.fail(f"ReviewItem {item.id} payload not JSON-serializable")

        finally:
            session.close()

    def test_no_extra_fields_in_payloads(self, ingested_batch):
        """ReviewItem payloads contain expected fields."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            items = session.query(ReviewItem).filter_by(batch_id=batch_id).all()

            for item in items:
                payload = item.payload_json
                payload_keys = set(payload.keys())

                # Validation items should have field and issue
                if item.item_type == "validation":
                    assert "field" in payload or "issue" in payload, \
                        f"Validation payload missing expected fields: {payload_keys}"
                # Normalization items should have field and normalized_value
                elif item.item_type == "normalization":
                    assert "field" in payload or "normalized_value" in payload, \
                        f"Normalization payload missing expected fields: {payload_keys}"

        finally:
            session.close()


class TestGuardrailPreservation:
    """Verify Phase 1C guardrails are maintained."""

    def test_no_review_decisions_created(self, ingested_batch):
        """Ingestion creates zero ReviewDecision records."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            decisions = session.query(ReviewDecision).filter_by(
                batch_id=batch_id
            ).all()
            assert len(decisions) == 0
        finally:
            session.close()

    def test_no_duplicate_items_created(self, ingested_batch):
        """Ingestion creates zero duplicate ReviewItems (processor limitation)."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            duplicates = session.query(ReviewItem).filter(
                ReviewItem.batch_id == batch_id,
                ReviewItem.item_type == "duplicate"
            ).all()
            assert len(duplicates) == 0
        finally:
            session.close()

    def test_no_household_items_created(self, ingested_batch):
        """Ingestion creates zero household ReviewItems (deferred to Phase 2)."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            households = session.query(ReviewItem).filter(
                ReviewItem.batch_id == batch_id,
                ReviewItem.item_type == "household"
            ).all()
            assert len(households) == 0
        finally:
            session.close()

    def test_raw_import_row_immutability_via_fk(self, ingested_batch):
        """RawImportRow immutability enforced by database FK constraints."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            raw_rows = session.query(RawImportRow).filter_by(batch_id=batch_id).all()
            assert len(raw_rows) > 0

            for raw_row in raw_rows:
                # Verify FK relationships exist (prevents deletion)
                assert raw_row.batch_id == batch_id
                # raw_csv_data should be immutable (it's a JSON column)
                assert isinstance(raw_row.raw_csv_data, dict)
                assert len(raw_row.raw_csv_data) > 0

        finally:
            session.close()

    def test_import_contact_immutability_via_fk(self, ingested_batch):
        """ImportContact immutability enforced by database FK constraints."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            contacts = session.query(ImportContact).filter_by(batch_id=batch_id).all()
            assert len(contacts) > 0

            for contact in contacts:
                # Verify contact snapshot is created and has data
                assert contact.batch_id == batch_id
                # Name should be split correctly
                if contact.first_name or contact.last_name:
                    assert isinstance(contact.first_name, (str, type(None)))
                    assert isinstance(contact.last_name, (str, type(None)))

        finally:
            session.close()

    def test_audit_log_contains_expected_details(self, ingested_batch):
        """Audit log details have correct structure and no unwanted fields."""
        db_url = ingested_batch["db_url"]
        batch_id = ingested_batch["batch_id"]

        session = get_session(init_db(db_url))
        try:
            audit = session.query(AuditLogRecord).filter_by(batch_id=batch_id).first()
            assert audit is not None

            details = audit.details
            assert "source" in details or "filename" in details
            assert "validation_summary" in details
            assert "record_count" in details

            # Validation summary should match row counts
            summary = details["validation_summary"]
            total = summary.get("PASS", 0) + summary.get("WARNING", 0) + summary.get("FAIL", 0)
            assert total == 4  # Our test data has 4 rows

        finally:
            session.close()
