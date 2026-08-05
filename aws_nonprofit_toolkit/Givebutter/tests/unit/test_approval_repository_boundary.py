"""Contract and transaction tests for the approval persistence boundary."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.householder.approval_repository import DatabaseApprovalRepository
from scripts.householder.approval_service import approve_batch
from scripts.householder.database_models import Base, AuditLogRecord, ImportBatch, RawImportRow


@pytest.fixture
def approval_db(tmp_path):
    url = f"sqlite:///{tmp_path / 'approval.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(ImportBatch(
        id="approval-boundary",
        filename="approval.csv",
        upload_timestamp=datetime.now(timezone.utc),
    ))
    session.flush()
    row = RawImportRow(
        batch_id="approval-boundary",
        row_index=1,
        raw_csv_data={"email": "person@example.com"},
    )
    session.add(row)
    session.commit()
    row_id = row.id
    session.close()
    return url, engine, row_id


def test_service_delegates_persistence_and_serializes_canonical_override(approval_db):
    url, _engine, row_id = approval_db
    repo = DatabaseApprovalRepository(url)

    result = approve_batch(
        "approval-boundary",
        "approved_with_overrides",
        rows_with_overrides=[{
            "raw_import_row_id": row_id,
            "row_index": 1,
            "issues": [{"field": " Email ", "reason": "invalid"}],
        }],
        repository=repo,
    )

    assert result["approval_status"] == "approved_with_overrides"
    batch = repo.get_batch("approval-boundary")
    assert batch.override_details["overrides"][0]["field"] == "email"


def test_repository_rolls_back_status_override_and_audit_on_commit_failure(approval_db):
    url, engine, row_id = approval_db

    def failing_session(database_url):
        session = sessionmaker(bind=create_engine(database_url))()
        original_commit = session.commit

        def fail_commit():
            original_commit.__self__.flush()
            raise RuntimeError("injected approval commit failure")

        session.commit = fail_commit
        return session

    repo = DatabaseApprovalRepository(url, session_factory=failing_session)
    with pytest.raises(RuntimeError, match="injected"):
        repo.persist_approval(
            "approval-boundary",
            "approved_with_overrides",
            {"overrides": [{"raw_import_row_id": row_id, "row_index": 1, "issues": []}]},
            "tester",
        )

    session = sessionmaker(bind=engine)()
    batch = session.get(ImportBatch, "approval-boundary")
    assert batch.approval_status is None
    assert batch.override_details is None
    assert session.query(AuditLogRecord).filter_by(batch_id="approval-boundary").count() == 0
    session.close()
