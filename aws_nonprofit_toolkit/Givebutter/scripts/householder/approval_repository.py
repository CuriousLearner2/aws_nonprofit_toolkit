"""Persistence boundary for batch approval state and audit records."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional, Protocol

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .database_models import AuditLogRecord, ImportBatch, RawImportRow


@dataclass(frozen=True)
class ApprovalBatch:
    batch_id: str
    approval_status: Optional[str]
    override_details: Optional[dict[str, Any]]


@dataclass(frozen=True)
class ApprovalRow:
    raw_import_row_id: int
    batch_id: str
    row_index: int

    @property
    def id(self) -> int:
        return self.raw_import_row_id


@dataclass(frozen=True)
class ApprovalWriteResult:
    audit_log_id: int
    timestamp: datetime


class ApprovalRepositoryProtocol(Protocol):
    def get_batch(self, batch_id: str) -> ApprovalBatch: ...
    def list_rows(self, batch_id: str) -> list[ApprovalRow]: ...
    def persist_approval(
        self,
        batch_id: str,
        approval_status: str,
        override_details: Optional[dict[str, Any]],
        reviewer: Optional[str],
    ) -> ApprovalWriteResult: ...


def get_approval_session(database_url: str) -> Session:
    engine = create_engine(database_url, echo=False)
    return sessionmaker(bind=engine)()


class DatabaseApprovalRepository:
    """Database implementation with one session and one atomic write."""

    def __init__(self, database_url: str, session_factory: Callable[[str], Session] = get_approval_session):
        self.database_url = database_url
        self._session_factory = session_factory

    def get_batch(self, batch_id: str) -> ApprovalBatch:
        session = self._session_factory(self.database_url)
        try:
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()
            if not batch:
                raise ValueError(f"Import batch '{batch_id}' not found")
            return ApprovalBatch(batch.id, batch.approval_status, batch.override_details)
        finally:
            session.close()

    def list_rows(self, batch_id: str) -> list[ApprovalRow]:
        session = self._session_factory(self.database_url)
        try:
            if not session.query(ImportBatch).filter_by(id=batch_id).first():
                raise ValueError(f"Import batch '{batch_id}' not found")
            return [
                ApprovalRow(row.id, row.batch_id, row.row_index)
                for row in session.query(RawImportRow)
                .filter_by(batch_id=batch_id)
                .order_by(RawImportRow.row_index, RawImportRow.id)
                .all()
            ]
        finally:
            session.close()

    def persist_approval(self, batch_id, approval_status, override_details, reviewer):
        session = self._session_factory(self.database_url)
        timestamp = datetime.now(timezone.utc)
        try:
            batch = session.query(ImportBatch).filter_by(id=batch_id).first()
            if not batch:
                raise ValueError(f"Import batch '{batch_id}' not found")
            if batch.approval_status in ('approved', 'approved_with_overrides'):
                raise ValueError(f"Batch '{batch_id}' is already {batch.approval_status}")

            for override in (override_details or {}).get('overrides', []):
                row = session.query(RawImportRow).filter_by(
                    id=override.get('raw_import_row_id'), batch_id=batch_id
                ).first()
                if not row:
                    raise ValueError(f"Raw import row {override.get('raw_import_row_id')} not found")

            batch.approval_status = approval_status
            if override_details is not None:
                batch.override_details = override_details
            batch.updated_at = timestamp
            audit_record = AuditLogRecord(
                batch_id=batch_id,
                action_type='batch_approved',
                action_timestamp=timestamp,
                actor=reviewer,
                details={
                    'approval_status': approval_status,
                    'override_count': len((override_details or {}).get('overrides', [])),
                    'override_details': override_details,
                },
            )
            session.add(audit_record)
            session.flush()
            session.commit()
            return ApprovalWriteResult(audit_record.id, timestamp)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


__all__ = [
    'ApprovalBatch', 'ApprovalRow', 'ApprovalWriteResult',
    'ApprovalRepositoryProtocol', 'DatabaseApprovalRepository',
    'get_approval_session',
]
