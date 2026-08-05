"""
Repository Provider - Configurable repository selection.

Phase 1B-Step 5I: Infrastructure boundary for repository selection.

Provides a single entry point to select between FixtureImportRepository and
DatabaseImportRepository based on configuration. Default is fixture-backed.

Does not perform service swapping. Routes and services remain unchanged.
Future service refactoring will use this provider.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional, Protocol

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .repository_contracts import ImportRepositoryProtocol
from .fixture_repository import FixtureImportRepository
from .database_repository import DatabaseImportRepository
from .database_models import (
    AuditLogRecord,
    ImportBatch,
    ImportContact,
    RawImportRow,
    ReviewItem,
    ReviewItemSubject,
)
from .ingestion_plan_policy import IngestionPlan
from .approval_repository import ApprovalRepositoryProtocol, DatabaseApprovalRepository


@dataclass(frozen=True)
class IngestionWriteResult:
    """Database-generated values returned after an ingestion transaction."""

    contacts_created: int
    audit_log_id: int
    audit_timestamp: datetime


class IngestionWriter(Protocol):
    """Persist one immutable ingestion plan atomically."""

    def persist_ingestion_plan(self, plan: IngestionPlan) -> IngestionWriteResult:
        ...


def _default_ingestion_session(database_url: str) -> Session:
    engine = create_engine(database_url, echo=False)
    return sessionmaker(bind=engine)()


def get_ingestion_session(database_url: str) -> Session:
    """Compatibility session factory used by ingestion characterization tests."""
    return _default_ingestion_session(database_url)


class DatabaseIngestionWriter:
    """Persist an ingestion plan without exposing ORM objects to services."""

    def __init__(self, database_url: str, session_factory: Callable[[str], Session] = get_ingestion_session):
        self.database_url = database_url
        self._session_factory = session_factory

    def persist_ingestion_plan(self, plan: IngestionPlan) -> IngestionWriteResult:
        session = self._session_factory(self.database_url)
        try:
            batch = ImportBatch(
                id=plan.batch_id,
                filename=plan.original_filename,
                upload_timestamp=plan.imported_at,
                uploader=plan.uploader,
                status="pending",
                raw_row_count=len(plan.rows),
            )
            session.add(batch)
            session.flush()

            contact_count = 0
            for row_plan in plan.rows:
                raw_row = RawImportRow(
                    batch_id=plan.batch_id,
                    row_index=row_plan.row_index,
                    raw_csv_data=dict(row_plan.raw_csv_data),
                )
                session.add(raw_row)
                session.flush()

                contact = ImportContact(
                    batch_id=plan.batch_id,
                    raw_import_row_id=raw_row.id,
                    **dict(row_plan.contact_values),
                )
                session.add(contact)
                session.flush()
                contact_count += 1

                for payload in row_plan.validation_items:
                    item = ReviewItem(
                        batch_id=plan.batch_id,
                        item_type="validation",
                        status="pending",
                        confidence=1.0,
                        payload_json=dict(payload),
                    )
                    session.add(item)
                    session.flush()
                    session.add(ReviewItemSubject(
                        review_item_id=item.id,
                        subject_type="import_contact_snapshot",
                        subject_id=contact.id,
                        role="primary",
                    ))

                for payload in row_plan.normalization_items:
                    item = ReviewItem(
                        batch_id=plan.batch_id,
                        item_type="normalization",
                        status="pending",
                        confidence=0.85,
                        payload_json=dict(payload),
                    )
                    session.add(item)
                    session.flush()
                    session.add(ReviewItemSubject(
                        review_item_id=item.id,
                        subject_type="import_contact_snapshot",
                        subject_id=contact.id,
                        role="primary",
                    ))

            audit_timestamp = datetime.now(timezone.utc)
            audit_record = AuditLogRecord(
                batch_id=plan.batch_id,
                action_type="batch_imported",
                action_timestamp=audit_timestamp,
                actor=plan.uploader,
                details=dict(plan.audit_details),
            )
            session.add(audit_record)
            session.flush()
            session.commit()
            return IngestionWriteResult(contact_count, audit_record.id, audit_timestamp)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def get_ingestion_writer(
    database_url: str,
    session_factory: Optional[Callable[[str], Session]] = None,
) -> IngestionWriter:
    """Create the configured database ingestion writer."""
    return DatabaseIngestionWriter(database_url, session_factory or get_ingestion_session)


def find_ingestion_batch_by_filename(filename: str, database_url: str) -> Optional[str]:
    """Return an unambiguous batch ID for a legacy filename lookup."""
    session = get_ingestion_session(database_url)
    try:
        batches = session.query(ImportBatch).filter_by(filename=filename).all()
        return batches[0].id if len(batches) == 1 else None
    finally:
        session.close()


def get_import_repository(
    config: Optional[Mapping[str, Any]] = None,
) -> ImportRepositoryProtocol:
    """
    Get a repository instance based on configuration.

    Default behavior: returns FixtureImportRepository (Phase 0 fixtures).

    Database behavior: returns DatabaseImportRepository when explicitly
    configured via HOUSEHOLDER_REPOSITORY=database environment variable
    or config dict.

    Args:
        config: Optional configuration mapping. Keys checked:
                - 'HOUSEHOLDER_REPOSITORY': 'fixture' (default) or 'database'

    Returns:
        ImportRepositoryProtocol: Either FixtureImportRepository or
                                 DatabaseImportRepository.

    Raises:
        ValueError: If repository mode is invalid or database mode is
                   selected without required configuration.

    Environment Variables:
        HOUSEHOLDER_REPOSITORY: 'fixture' (default) or 'database'
        GIVEBUTTER_DATABASE_URL: For database mode (optional, uses default if not set)
    """
    # Determine which repository to use
    repository_mode = _get_repository_mode(config)

    if repository_mode == "fixture":
        return FixtureImportRepository()

    elif repository_mode == "database":
        return _create_database_repository(config)

    else:
        raise ValueError(
            f"Invalid HOUSEHOLDER_REPOSITORY mode: {repository_mode}. "
            f"Valid modes: 'fixture' (default), 'database'."
        )


def get_approval_repository(
    config: Optional[Mapping[str, Any]] = None,
) -> ApprovalRepositoryProtocol:
    """Return the provider-selected persistence adapter for batch approval."""
    database_url = _get_database_url(config)
    if not database_url:
        raise ValueError("Approval requires database configuration")
    return DatabaseApprovalRepository(database_url)


def _get_repository_mode(config: Optional[Mapping[str, Any]] = None) -> str:
    """
    Determine repository mode from config or environment.

    Priority:
    1. config['HOUSEHOLDER_REPOSITORY'] if provided
    2. HOUSEHOLDER_REPOSITORY environment variable if set
    3. Default: 'fixture'

    Args:
        config: Optional configuration mapping.

    Returns:
        str: 'fixture' or 'database'
    """
    # Check config dict first (highest priority)
    if config and "HOUSEHOLDER_REPOSITORY" in config:
        return config["HOUSEHOLDER_REPOSITORY"].lower()

    # Check environment variable (medium priority)
    env_mode = os.getenv("HOUSEHOLDER_REPOSITORY", "").lower()
    if env_mode:
        return env_mode

    # Default to fixture (lowest priority)
    return "fixture"


def _create_database_repository(
    config: Optional[Mapping[str, Any]] = None,
) -> DatabaseImportRepository:
    """
    Create a DatabaseImportRepository instance.

    Requires explicit database URL configuration.
    Looks for database URL in order:
    1. config['GIVEBUTTER_DATABASE_URL'] if provided
    2. GIVEBUTTER_DATABASE_URL environment variable if set
    3. Raises error if not configured

    Args:
        config: Optional configuration mapping.

    Returns:
        DatabaseImportRepository: Database-backed repository instance.

    Raises:
        ValueError: If database URL is not explicitly configured.
    """
    database_url = _get_database_url(config)

    if not database_url:
        raise ValueError(
            "Database mode requested but no database URL configured. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or "
            "pass config with 'GIVEBUTTER_DATABASE_URL' key."
        )

    return DatabaseImportRepository(database_url=database_url)


def _get_database_url(config: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    """
    Get database URL from config or environment.

    Database mode requires explicit URL configuration.
    No implicit defaults are used.

    Priority:
    1. config['GIVEBUTTER_DATABASE_URL'] if provided
    2. GIVEBUTTER_DATABASE_URL environment variable if set
    3. None (no default)

    Args:
        config: Optional configuration mapping.

    Returns:
        str: Database URL for SQLAlchemy, or None if not configured.
    """
    # Check config dict first
    if config and "GIVEBUTTER_DATABASE_URL" in config:
        return config["GIVEBUTTER_DATABASE_URL"]

    # Check environment variable
    env_url = os.getenv("GIVEBUTTER_DATABASE_URL", "")
    if env_url:
        return env_url

    # No default - database mode requires explicit configuration
    return None
