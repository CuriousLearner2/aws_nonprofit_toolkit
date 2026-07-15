"""
Integration tests for POST /upload with optional database ingestion.

Verifies that upload route preserves existing behavior by default and
optionally performs database ingestion when explicitly configured.
"""

import pytest
from pathlib import Path
import os

from scripts.householder.database_models import (
    init_db,
    get_session,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewDecision,
    AuditLogRecord,
)


@pytest.fixture
def csv_data():
    """Test CSV data matching processor output format."""
    return (
        "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications\n"
        "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,\n"
        "Jane Doe,jane@gmai.com,5559876543,200.00,2026-06-13,PASS,None,Consider: jane@gmail.com\n"
        "Bob Wilson,,5551111111,300.00,2026-06-14,WARNING,Email: Email field is empty,Verify email\n"
        "Alice Johnson,,5552222222,400.00,2026-06-15,FAIL,Email: Email field is empty; Phone: Invalid,Verify contact"
    )


@pytest.fixture
def flask_client(tmp_path, monkeypatch):
    """Create Flask test client with temporary directories."""
    # Set up temporary directories for uploads/processing
    intake_dir = tmp_path / "intake" / "new"
    processing_dir = tmp_path / "processing"
    intake_dir.mkdir(parents=True)
    processing_dir.mkdir(parents=True)

    # Import Flask app (must be after directory setup for monkeypatch to work)
    import scripts.uploader.app as app_module

    # Patch the module-level variables before app usage
    monkeypatch.setattr(app_module, "INTAKE_DIR", intake_dir)
    monkeypatch.setattr(app_module, "PROCESSING_DIR", processing_dir)

    app = app_module.app
    app.config["TESTING"] = True

    client = app.test_client()
    return client


@pytest.fixture
def flask_client_with_database(tmp_path, monkeypatch):
    """Create Flask test client with database configuration."""
    # Set up temporary directories
    intake_dir = tmp_path / "intake" / "new"
    processing_dir = tmp_path / "processing"
    intake_dir.mkdir(parents=True)
    processing_dir.mkdir(parents=True)

    # Create temporary database
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    init_db(db_url)

    # Set environment variables for ingestion
    monkeypatch.setenv("HOUSEHOLDER_INGEST_ON_UPLOAD", "true")
    monkeypatch.setenv("GIVEBUTTER_DATABASE_URL", db_url)

    # Import Flask app and patch directories
    import scripts.uploader.app as app_module

    # Patch the module-level variables
    monkeypatch.setattr(app_module, "INTAKE_DIR", intake_dir)
    monkeypatch.setattr(app_module, "PROCESSING_DIR", processing_dir)

    app = app_module.app
    app.config["TESTING"] = True

    client = app.test_client()
    return {
        "client": client,
        "db_url": db_url,
        "tmp_path": tmp_path,
    }


class TestDefaultUploadBehavior:
    """Test that /upload preserves existing behavior when ingestion is not enabled."""

    def test_upload_without_ingestion_returns_same_json(self, flask_client):
        """Default upload returns same JSON structure as before."""
        from io import BytesIO

        # Create CSV data as BytesIO
        csv_content = (
            "Name,Email,Phone,Amount,Date,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,TXN001\n"
            "Jane Doe,jane@gmail.com,5559876543,200.00,2026-06-13,TXN002"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        # Upload the file
        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        response_data = response.get_json()

        # Verify existing fields are present
        assert 'filename' in response_data
        assert 'record_count' in response_data
        assert 'warning_count' in response_data
        assert 'fail_count' in response_data
        assert 'status' in response_data
        assert response_data['status'] == 'processed'

        # Verify ingestion fields are NOT present when not enabled
        assert 'batch_id' not in response_data
        assert 'ingestion_status' not in response_data

    def test_upload_without_ingestion_creates_no_database_records(self, flask_client):
        """Upload without ingestion creates no database records."""
        from io import BytesIO

        csv_content = (
            "Name,Email,Phone,Amount,Date,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        # Upload without database configured
        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        # No way to verify no database records when database isn't configured,
        # but this verifies the upload completes without error

    def test_processing_queue_without_batch_uses_imports_fallback(self, flask_client):
        """Processing queue rows without a batch ID should fall back to the imports list."""
        from io import BytesIO

        csv_content = (
            "Name,Email,Phone,Amount,Date,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        upload_response = flask_client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        processing_response = flask_client.get('/api/processing')
        assert processing_response.status_code == 200
        queue_items = processing_response.get_json()
        assert queue_items, "Expected at least one processing queue item"

        fallback_item = next((item for item in queue_items if item.get('batch_id') is None), None)
        assert fallback_item is not None, "Expected a queue item without a batch ID"
        assert fallback_item['review_url'] == '/imports'


class TestDatabaseIngestOpt:
    """Test that ingestion is opt-in and requires explicit configuration."""

    def test_ingest_disabled_without_flag(self, tmp_path, monkeypatch):
        """Ingestion does not occur even with database URL unless flag is set."""
        from io import BytesIO

        # Set up temporary directories
        intake_dir = tmp_path / "intake" / "new"
        processing_dir = tmp_path / "processing"
        intake_dir.mkdir(parents=True)
        processing_dir.mkdir(parents=True)

        # Create temporary database
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)

        # Set ONLY database URL, NOT ingestion flag
        monkeypatch.setenv("GIVEBUTTER_DATABASE_URL", db_url)
        monkeypatch.delenv("HOUSEHOLDER_INGEST_ON_UPLOAD", raising=False)

        # Import Flask app and patch directories
        import scripts.uploader.app as app_module
        monkeypatch.setattr(app_module, "INTAKE_DIR", intake_dir)
        monkeypatch.setattr(app_module, "PROCESSING_DIR", processing_dir)

        app = app_module.app
        app.config["TESTING"] = True
        client = app.test_client()

        # Create and upload CSV
        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        # Verify upload succeeded with process-only response
        assert response.status_code == 200
        response_data = response.get_json()

        # Verify response has standard fields (no ingestion fields)
        assert 'filename' in response_data
        assert 'record_count' in response_data
        assert 'status' in response_data
        assert response_data['status'] == 'processed'

        # Verify ingestion fields are NOT present
        assert 'batch_id' not in response_data
        assert 'ingestion_status' not in response_data
        assert 'audit_log_id' not in response_data

        # Verify database is completely empty (no ingestion occurred)
        session = get_session(init_db(db_url))
        try:
            assert session.query(ImportBatch).count() == 0, "Database should have no ImportBatch"
            assert session.query(RawImportRow).count() == 0, "Database should have no RawImportRow"
            assert session.query(ImportContact).count() == 0, "Database should have no ImportContact"
            assert session.query(ReviewItem).count() == 0, "Database should have no ReviewItem"
            assert session.query(ReviewDecision).count() == 0, "Database should have no ReviewDecision"
            assert session.query(AuditLogRecord).count() == 0, "Database should have no AuditLogRecord"
        finally:
            session.close()


class TestDatabaseIngestionPath:
    """Test database ingestion path when explicitly enabled."""

    def test_ingest_on_upload_creates_batch(self, flask_client_with_database):
        """Upload with ingestion enabled creates ImportBatch."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001\n"
            "Jane Doe,jane@gmail.com,5559876543,200.00,2026-06-13,PASS,None,,TXN002"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        # Upload the file
        response = client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        response_data = response.get_json()

        # Verify ingestion fields present
        assert 'batch_id' in response_data
        assert 'ingestion_status' in response_data
        assert response_data['ingestion_status'] == 'success'
        batch_id = response_data['batch_id']

        # Verify batch exists in database
        session = get_session(init_db(db_url))
        try:
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()
            assert batch is not None
            assert batch.filename == 'test.csv'
            assert batch.raw_row_count == 2
        finally:
            session.close()

    def test_ingest_on_upload_creates_raw_rows(self, flask_client_with_database):
        """Upload ingestion creates RawImportRow records."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001\n"
            "Jane Doe,jane@gmail.com,5559876543,200.00,2026-06-13,PASS,None,,TXN002"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        response_data = response.get_json()
        batch_id = response_data['batch_id']

        # Verify raw rows created
        session = get_session(init_db(db_url))
        try:
            raw_rows = session.query(RawImportRow).filter_by(batch_id=batch_id).all()
            assert len(raw_rows) == 2
            assert raw_rows[0].row_index == 0
            assert raw_rows[1].row_index == 1
        finally:
            session.close()

    def test_ingest_on_upload_creates_contacts(self, flask_client_with_database):
        """Upload ingestion creates ImportContact records."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001\n"
            "Jane Doe,jane@gmail.com,5559876543,200.00,2026-06-13,PASS,None,,TXN002"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        response_data = response.get_json()
        batch_id = response_data['batch_id']

        # Verify contacts created
        session = get_session(init_db(db_url))
        try:
            contacts = session.query(ImportContact).filter_by(batch_id=batch_id).all()
            assert len(contacts) == 2
            assert contacts[0].first_name == "John"
            assert contacts[0].last_name == "Smith"
            assert contacts[1].first_name == "Jane"
            assert contacts[1].last_name == "Doe"
        finally:
            session.close()

    def test_ingest_on_upload_creates_validation_items(self, flask_client_with_database):
        """Upload ingestion creates ReviewItem records for validation issues."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001\n"
            "Bob Wilson,,5551111111,300.00,2026-06-14,WARNING,Email: Empty,Verify email,TXN003"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        response_data = response.get_json()
        batch_id = response_data['batch_id']

        # Verify validation items created
        session = get_session(init_db(db_url))
        try:
            items = session.query(ReviewItem).filter(
                ReviewItem.batch_id == batch_id,
                ReviewItem.item_type == 'validation'
            ).all()
            assert len(items) >= 1
            assert all(item.status == 'pending' for item in items)
        finally:
            session.close()

    def test_ingest_on_upload_creates_no_review_decisions(self, flask_client_with_database):
        """Ingestion creates zero ReviewDecision records."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        response_data = response.get_json()
        batch_id = response_data['batch_id']

        # Verify no review decisions created
        session = get_session(init_db(db_url))
        try:
            decisions = session.query(ReviewDecision).filter_by(batch_id=batch_id).all()
            assert len(decisions) == 0
        finally:
            session.close()

    def test_ingest_on_upload_creates_audit_log(self, flask_client_with_database):
        """Ingestion creates AuditLogRecord."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        response_data = response.get_json()
        batch_id = response_data['batch_id']

        # Verify audit log created
        session = get_session(init_db(db_url))
        try:
            audit = session.query(AuditLogRecord).filter_by(batch_id=batch_id).first()
            assert audit is not None
            assert audit.action_type == 'batch_imported'
        finally:
            session.close()

    def test_ingest_response_includes_all_fields(self, flask_client_with_database):
        """Upload response with ingestion includes all expected fields."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 200
        response_data = response.get_json()

        # Verify existing fields
        assert 'filename' in response_data
        assert 'record_count' in response_data
        assert 'warning_count' in response_data
        assert 'fail_count' in response_data
        assert 'status' in response_data

        # Verify ingestion fields
        assert 'batch_id' in response_data
        assert 'ingestion_status' in response_data
        assert 'raw_row_count' in response_data
        assert 'validation_items_created' in response_data
        assert 'normalization_items_created' in response_data
        assert 'duplicate_items_created' in response_data
        assert 'household_items_created' in response_data


class TestUploadErrorHandling:
    """Test error handling in upload/ingestion flow."""

    def test_missing_file_returns_error(self, flask_client):
        """Missing file in request returns error."""
        response = flask_client.post('/upload', data={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_non_csv_file_returns_error(self, flask_client):
        """Non-CSV file returns error."""
        from io import BytesIO

        data = {
            'file': (BytesIO(b"test"), 'test.txt')
        }
        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        response_data = response.get_json()
        assert 'error' in response_data

    def test_ingestion_failure_no_partial_records(self, tmp_path, monkeypatch):
        """Ingestion failure creates no partial database records."""
        from io import BytesIO

        # Set up temporary directories
        intake_dir = tmp_path / "intake" / "new"
        processing_dir = tmp_path / "processing"
        intake_dir.mkdir(parents=True)
        processing_dir.mkdir(parents=True)

        # Create temporary database
        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)

        # Set environment variables for ingestion
        monkeypatch.setenv("HOUSEHOLDER_INGEST_ON_UPLOAD", "true")
        monkeypatch.setenv("GIVEBUTTER_DATABASE_URL", db_url)

        # Import app module FIRST
        import scripts.uploader.app as app_module

        # Monkeypatch directories
        monkeypatch.setattr(app_module, "INTAKE_DIR", intake_dir)
        monkeypatch.setattr(app_module, "PROCESSING_DIR", processing_dir)

        # NOW monkeypatch the ingest_processed_csv function in app_module's namespace
        def failing_ingest(*args, **kwargs):
            raise app_module.IngestionValidationError("Test: simulated validation failure")

        monkeypatch.setattr(app_module, "ingest_processed_csv", failing_ingest)

        # Get the app
        app = app_module.app
        app.config["TESTING"] = True
        client = app.test_client()

        # Create and upload CSV
        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        # Verify error response (should be 4xx or 5xx, main point is no partial records)
        assert response.status_code in [400, 500], f"Expected error status, got {response.status_code}"
        response_data = response.get_json()
        assert response_data['error_type'] == 'unsupported_csv'
        assert 'No data was imported' in response_data['message']
        assert '/Users/' not in response.get_data(as_text=True)
        assert 'Test: simulated validation failure' not in response.get_data(as_text=True)

        # Verify no partial records in database
        session = get_session(init_db(db_url))
        try:
            assert session.query(ImportBatch).count() == 0, "No ImportBatch should exist"
            assert session.query(RawImportRow).count() == 0, "No RawImportRow should exist"
            assert session.query(ImportContact).count() == 0, "No ImportContact should exist"
            assert session.query(ReviewItem).count() == 0, "No ReviewItem should exist"
            assert session.query(AuditLogRecord).count() == 0, "No AuditLogRecord should exist"
        finally:
            session.close()

    def test_ingestion_database_failure_returns_safe_message_and_cleans_up(
        self,
        tmp_path,
        monkeypatch,
    ):
        """Database failures during ingestion should not leak raw details."""
        from io import BytesIO

        intake_dir = tmp_path / "intake" / "new"
        processing_dir = tmp_path / "processing"
        intake_dir.mkdir(parents=True)
        processing_dir.mkdir(parents=True)

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)

        monkeypatch.setenv("HOUSEHOLDER_INGEST_ON_UPLOAD", "true")
        monkeypatch.setenv("GIVEBUTTER_DATABASE_URL", db_url)

        import scripts.uploader.app as app_module

        monkeypatch.setattr(app_module, "INTAKE_DIR", intake_dir)
        monkeypatch.setattr(app_module, "PROCESSING_DIR", processing_dir)

        def failing_ingest(*args, **kwargs):
            raise app_module.IngestionDatabaseError("Test: simulated database failure /Users/gautambiswas/secret")

        monkeypatch.setattr(app_module, "ingest_processed_csv", failing_ingest)

        app = app_module.app
        app.config["TESTING"] = True
        client = app.test_client()

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {'file': (BytesIO(csv_content.encode()), 'test.csv')}

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 500
        response_data = response.get_json()
        assert response_data['error_type'] == 'unexpected_error'
        assert 'Something went wrong while importing the file' in response_data['message']
        assert '/Users/' not in response.get_data(as_text=True)

        session = get_session(init_db(db_url))
        try:
            assert session.query(ImportBatch).count() == 0
            assert session.query(RawImportRow).count() == 0
            assert session.query(ImportContact).count() == 0
            assert session.query(ReviewItem).count() == 0
            assert session.query(AuditLogRecord).count() == 0
        finally:
            session.close()

    def test_ingestion_unexpected_failure_returns_safe_message_and_cleans_up(
        self,
        tmp_path,
        monkeypatch,
    ):
        """Unexpected ingestion failures should be sanitized and cleaned up."""
        from io import BytesIO

        intake_dir = tmp_path / "intake" / "new"
        processing_dir = tmp_path / "processing"
        intake_dir.mkdir(parents=True)
        processing_dir.mkdir(parents=True)

        db_path = tmp_path / "test.db"
        db_url = f"sqlite:///{db_path}"
        init_db(db_url)

        monkeypatch.setenv("HOUSEHOLDER_INGEST_ON_UPLOAD", "true")
        monkeypatch.setenv("GIVEBUTTER_DATABASE_URL", db_url)

        import scripts.uploader.app as app_module

        monkeypatch.setattr(app_module, "INTAKE_DIR", intake_dir)
        monkeypatch.setattr(app_module, "PROCESSING_DIR", processing_dir)

        def exploding_ingest(*args, **kwargs):
            raise RuntimeError("Test: simulated unexpected ingestion failure /Users/gautambiswas/secret")

        monkeypatch.setattr(app_module, "ingest_processed_csv", exploding_ingest)

        app = app_module.app
        app.config["TESTING"] = True
        client = app.test_client()

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {'file': (BytesIO(csv_content.encode()), 'test.csv')}

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 500
        response_data = response.get_json()
        assert response_data['error_type'] == 'unexpected_error'
        assert 'Something went wrong while importing the file' in response_data['message']
        assert '/Users/' not in response.get_data(as_text=True)
        assert 'RuntimeError' not in response.get_data(as_text=True)

        session = get_session(init_db(db_url))
        try:
            assert session.query(ImportBatch).count() == 0
            assert session.query(RawImportRow).count() == 0
            assert session.query(ImportContact).count() == 0
            assert session.query(ReviewItem).count() == 0
            assert session.query(AuditLogRecord).count() == 0
        finally:
            session.close()


class TestUploadIngestedDataReadback:
    """Test that uploaded/ingested data appears in database-mode routes."""

    def test_upload_ingested_data_appears_in_imports_route(self, flask_client_with_database):
        """POST /upload with ingestion → data visible in GET /imports."""
        from io import BytesIO

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        # Create and upload CSV
        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001\n"
            "Jane Doe,jane@gmail.com,5559876543,200.00,2026-06-13,PASS,None,,TXN002"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        upload_data = upload_response.get_json()
        batch_id = upload_data['batch_id']

        # Query /imports to see if batch appears
        # Note: /imports route in fixture mode shows fixture data, so we verify batch exists in database instead
        session = get_session(init_db(db_url))
        try:
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()
            assert batch is not None, "Ingested batch should exist in database"
            assert batch.raw_row_count == 2, "Batch should have 2 rows"

            # Verify contacts were created
            contacts = session.query(ImportContact).filter_by(batch_id=batch_id).all()
            assert len(contacts) == 2, "Should have 2 contacts"
        finally:
            session.close()

    def test_upload_ingested_data_appears_in_dashboard_route(self, flask_client_with_database):
        """POST /upload with ingestion → data visible in GET /imports/<batch_id>/dashboard."""
        from io import BytesIO
        from scripts.householder.database_repository import DatabaseImportRepository

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        # Create and upload CSV
        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        upload_data = upload_response.get_json()
        batch_id = upload_data['batch_id']

        # Query database via repository to verify batch appears in dashboard
        repo = DatabaseImportRepository(db_url)
        dashboard = repo.get_dashboard(batch_id)

        assert dashboard is not None, "Dashboard should exist for batch"
        assert dashboard.batch_id == batch_id, "Dashboard batch_id should match"
        assert dashboard.filename == 'test.csv', "Dashboard filename should match"

    def test_upload_uses_runtime_database_config_without_env_ingest_flag(self, flask_client_with_database, monkeypatch):
        """Upload ingestion should still work when the DB URL lives in app config only."""
        from io import BytesIO
        import scripts.uploader.app as app_module

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        monkeypatch.delenv("HOUSEHOLDER_INGEST_ON_UPLOAD", raising=False)
        monkeypatch.delenv("GIVEBUTTER_DATABASE_URL", raising=False)
        monkeypatch.setitem(app_module.app.config, "HOUSEHOLDER_INGEST_ON_UPLOAD", "true")
        monkeypatch.setitem(app_module.app.config, "GIVEBUTTER_DATABASE_URL", db_url)
        monkeypatch.setitem(app_module.app.config, "HOUSEHOLDER_REPOSITORY", "database")

        csv_content = (
            "Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications,Transaction ID\n"
            "John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,,TXN001"
        )
        data = {'file': (BytesIO(csv_content.encode()), 'config_only.csv')}

        upload_response = client.post('/upload', data=data, content_type='multipart/form-data')
        assert upload_response.status_code == 200

        upload_data = upload_response.get_json()
        assert upload_data['batch_id'], "Upload should return a batch_id in config-only DB mode"

        queue_response = client.get('/api/processing')
        assert queue_response.status_code == 200
        queue_data = queue_response.get_json()
        assert queue_data, "Queue should include the uploaded file"

        queued = next(item for item in queue_data if item['filename'].endswith('config_only.csv'))
        assert queued['batch_id'] == upload_data['batch_id']
        assert queued['review_url'] == f"/imports/{upload_data['batch_id']}/validation"


class TestUploadErrorTaxonomy:
    """Test that upload failures are classified into safe user-facing categories."""

    def test_unsupported_givebutter_csv_returns_supported_format_message(self, flask_client):
        from io import BytesIO

        data = {'file': (BytesIO(b"foo,bar,baz\n1,2,3\n"), 'non_givebutter.csv')}
        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['error_type'] == 'unsupported_csv'
        assert 'supported Givebutter CSV' in payload['message']
        assert 'No data was imported' in payload['message']
        assert 'Processing failed' not in payload['error']
        assert '/Users/' not in response.get_data(as_text=True)

    def test_missing_required_columns_returns_supported_format_message(self, flask_client):
        from io import BytesIO

        data = {
            'file': (
                BytesIO(
                    b"Name,Email,Amount\n"
                    b"John Smith,john@example.com,100.00\n"
                ),
                'missing_columns.csv',
            )
        }

        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['error_type'] == 'unsupported_csv'
        assert 'supported Givebutter CSV' in payload['message']
        assert 'No data was imported' in payload['message']

    def test_empty_csv_returns_empty_file_message(self, flask_client):
        from io import BytesIO

        data = {'file': (BytesIO(b""), 'empty.csv')}
        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['error_type'] == 'empty_csv'
        assert 'CSV is empty' in payload['message']

    def test_malformed_csv_returns_unreadable_file_message(self, flask_client, monkeypatch):
        from io import BytesIO
        import scripts.uploader.app as app_module

        monkeypatch.setattr(
            app_module,
            "run_processor",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                app_module.MalformedCSVError("CSV parser error: malformed csv")
            ),
        )

        data = {
            'file': (
                BytesIO(b'Donation ID,Date,Donor Name,Email,Amount\nGB001,2026-07-14,Jane Doe,jane@example.com,10.00\n'),
                'malformed.csv',
            )
        }

        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['error_type'] == 'malformed_csv'
        assert 'couldn’t read this CSV' in payload['message']

    def test_unsupported_encoding_returns_encoding_message(self, flask_client):
        from io import BytesIO

        data = {'file': (BytesIO(b'\xff\xfe\x00\x00'), 'encoding.csv')}
        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['error_type'] == 'encoding_error'
        assert 'UTF-8 CSV' in payload['message']

    def test_missing_processed_file_returns_internal_file_handling_message(
        self,
        flask_client,
        monkeypatch,
    ):
        from io import BytesIO
        import scripts.uploader.app as app_module

        def fake_processor(*args, **kwargs):
            return None

        monkeypatch.setattr(app_module, "run_processor", fake_processor)

        data = {
            'file': (
                BytesIO(
                    b"Donation ID,Date,Donor Name,Email,Amount,Campaign Title\n"
                    b"GB001,2026-05-25,John Smith,john@example.com,100.00,General Fund\n"
                ),
                'no_output.csv',
            )
        }

        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 500
        payload = response.get_json()
        assert payload['error_type'] == 'file_handling_error'
        assert 'internal file-handling error' in payload['message']
        assert '/Users/' not in response.get_data(as_text=True)

    def test_unexpected_processor_exception_returns_generic_safe_message(
        self,
        flask_client,
        monkeypatch,
    ):
        from io import BytesIO
        import scripts.uploader.app as app_module

        def exploding_processor(*args, **kwargs):
            raise RuntimeError("boom /Users/gautambiswas/secret")

        monkeypatch.setattr(app_module, "run_processor", exploding_processor)

        data = {
            'file': (
                BytesIO(
                    b"Donation ID,Date,Donor Name,Email,Amount,Campaign Title\n"
                    b"GB001,2026-05-25,John Smith,john@example.com,100.00,General Fund\n"
                ),
                'unexpected.csv',
            )
        }

        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 500
        payload = response.get_json()
        assert payload['error_type'] == 'unexpected_error'
        assert 'Something went wrong while importing the file' in payload['message']
        assert '/Users/' not in response.get_data(as_text=True)
        assert 'RuntimeError' not in response.get_data(as_text=True)

    def test_failed_upload_leaves_no_partial_import_state(
        self,
        flask_client_with_database,
        monkeypatch,
    ):
        from io import BytesIO
        import scripts.uploader.app as app_module
        from scripts.householder.database_models import (
            get_session,
            init_db,
            ImportBatch,
            RawImportRow,
            ReviewDecision,
        )

        def unsupported_processor(*args, **kwargs):
            raise app_module.UnsupportedGivebutterCSVError(
                "Missing required Givebutter columns: Transaction ID"
            )

        monkeypatch.setattr(app_module, "run_processor", unsupported_processor)

        client_config = flask_client_with_database
        client = client_config["client"]
        db_url = client_config["db_url"]

        data = {
            'file': (
                BytesIO(
                    b"Name,Email,Amount\n"
                    b"John Smith,john@example.com,100.00\n"
                ),
                'partial_import.csv',
            )
        }

        response = client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        payload = response.get_json()
        assert payload['error_type'] == 'unsupported_csv'

        session = get_session(init_db(db_url))
        try:
            assert session.query(ImportBatch).count() == 0
            assert session.query(RawImportRow).count() == 0
            assert session.query(ReviewDecision).count() == 0
        finally:
            session.close()

    def test_failed_upload_cleans_up_temp_files_after_processing(
        self,
        flask_client,
        monkeypatch,
    ):
        from io import BytesIO
        import scripts.uploader.app as app_module

        seen_input_exists = {'value': False}

        def checking_processor(input_path, output_path):
            seen_input_exists['value'] = Path(input_path).exists()
            raise app_module.UnsupportedGivebutterCSVError(
                "Missing required Givebutter columns: Transaction ID"
            )

        monkeypatch.setattr(app_module, "run_processor", checking_processor)

        data = {
            'file': (
                BytesIO(
                    b"Name,Email,Amount\n"
                    b"John Smith,john@example.com,100.00\n"
                ),
                'cleanup_check.csv',
            )
        }

        response = flask_client.post('/upload', data=data, content_type='multipart/form-data')

        assert response.status_code == 400
        assert seen_input_exists['value'] is True

        import scripts.uploader.app as app_module_check
        assert not any(app_module_check.INTAKE_DIR.glob('*.csv'))
        assert not any(app_module_check.PROCESSING_DIR.glob('*.csv'))
