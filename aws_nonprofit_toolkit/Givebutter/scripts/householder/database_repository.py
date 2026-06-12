"""
Database Repository - Read-only database-backed implementation of ImportRepositoryProtocol.

Phase 1B-Step 5A: Initial read-only implementation with list_imports() only.

This repository queries the SQLite database (via SQLAlchemy ORM) and converts
database records to frozen Phase 1A view models, maintaining parity with
FixtureImportRepository for all returned data shapes.

Design principles:
- Returns frozen dataclasses (view models), never ORM instances
- ORM models do not leak into services or templates
- Session management is isolated within this module
- No mutations to database state
- Immutable records (raw_import_rows, import_contacts) are never modified
"""

from typing import List, Optional
from datetime import datetime

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from .database_models import Base, ImportBatch, ImportContact, ReviewItem, ReviewDecision
from .service_contracts import ImportSummary


def get_db_session(database_url: str = 'sqlite:///./givebutter.db') -> Session:
    """
    Create a new database session.

    Args:
        database_url: Database connection string. Defaults to SQLite in current directory.

    Returns:
        SQLAlchemy Session instance.
    """
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


class DatabaseImportRepository:
    """
    Read-only database repository implementing ImportRepositoryProtocol.

    Phase 1B-Step 5A: Implements list_imports() only.
    Other protocol methods raise NotImplementedError.
    """

    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        """
        Initialize repository with database connection string.

        Args:
            database_url: Database connection URL. Defaults to local SQLite.
        """
        self.database_url = database_url

    def list_imports(self) -> List[ImportSummary]:
        """
        Return list of all import batches as ImportSummary view models.

        Queries ImportBatch records and converts to frozen view models.
        Computes record_count and progress from database state.

        Returns:
            List of ImportSummary objects ready for template rendering.
            Data shape matches FixtureImportRepository.list_imports() output.

        Raises:
            Exception: If database connection fails.
        """
        session = get_db_session(self.database_url)
        try:
            summaries = []

            # Query all ImportBatch records, ordered by most recent first
            batches = session.query(ImportBatch).order_by(ImportBatch.upload_timestamp.desc()).all()

            for batch in batches:
                # Compute record_count: count of import_contacts for this batch
                record_count = session.query(func.count(ImportContact.id)).filter(
                    ImportContact.batch_id == batch.id
                ).scalar() or 0

                # Compute progress: percentage of review_items with decisions
                # If no review_items exist, progress is 0
                total_items = session.query(func.count(ReviewItem.id)).filter(
                    ReviewItem.batch_id == batch.id
                ).scalar() or 0

                if total_items > 0:
                    decided_items = session.query(func.count(ReviewDecision.id)).filter(
                        ReviewDecision.batch_id == batch.id
                    ).scalar() or 0
                    progress = int((decided_items / total_items) * 100)
                else:
                    progress = 0

                # Format upload timestamp as relative time string
                uploaded_str = self._format_relative_time(batch.upload_timestamp) if batch.upload_timestamp else None

                # Create view model (frozen dataclass)
                summary = ImportSummary(
                    id=batch.id,
                    filename=batch.filename,
                    record_count=record_count,
                    status=batch.status,
                    progress=progress,
                    uploaded_timestamp=uploaded_str,
                )
                summaries.append(summary)

            return summaries

        finally:
            session.close()

    @staticmethod
    def _format_relative_time(dt: datetime) -> str:
        """
        Format datetime as relative time string (e.g., '2h ago').

        Consistent with FixtureImportRepository and existing app.py formatting.

        Args:
            dt: Datetime to format.

        Returns:
            Relative time string (e.g., 'just now', '5m ago', '2h ago', '3d ago').
        """
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f'{minutes}m ago'
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f'{hours}h ago'
        else:
            days = int(seconds // 86400)
            return f'{days}d ago'

    def get_dashboard(self, import_id: str):
        """Not implemented in Phase 1B-Step 5A."""
        raise NotImplementedError("get_dashboard() not yet implemented in DatabaseImportRepository")

    def get_validation(self, import_id: str):
        """Not implemented in Phase 1B-Step 5A."""
        raise NotImplementedError("get_validation() not yet implemented in DatabaseImportRepository")

    def get_normalizations(self, import_id: str):
        """Not implemented in Phase 1B-Step 5A."""
        raise NotImplementedError("get_normalizations() not yet implemented in DatabaseImportRepository")

    def get_households(self, import_id: str):
        """Not implemented in Phase 1B-Step 5A."""
        raise NotImplementedError("get_households() not yet implemented in DatabaseImportRepository")

    def get_duplicates(self, import_id: str):
        """Not implemented in Phase 1B-Step 5A."""
        raise NotImplementedError("get_duplicates() not yet implemented in DatabaseImportRepository")

    def get_audit(self, import_id: str):
        """Not implemented in Phase 1B-Step 5A."""
        raise NotImplementedError("get_audit() not yet implemented in DatabaseImportRepository")

    def get_exports(self, import_id: str):
        """Not implemented in Phase 1B-Step 5A."""
        raise NotImplementedError("get_exports() not yet implemented in DatabaseImportRepository")
