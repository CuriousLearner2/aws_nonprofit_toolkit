"""
Repository Contracts - Abstract interface for import data repositories.

Defines the ImportRepositoryProtocol that all repository implementations
(FixtureImportRepository, DatabaseImportRepository, etc.) must satisfy.

This protocol ensures services and routes remain data-source agnostic.
Repositories can be swapped without changing service code, route handlers,
or templates.

Design principles:
- Read-only interface (no write/decision APIs in this protocol)
- Methods return frozen view models, not ORM objects
- Methods must not mutate raw import data
- Methods must not expose database sessions or connection objects
- Methods preserve template-ready data shapes
"""

from typing import Protocol, List

from .service_contracts import (
    ImportSummary,
    ImportDashboardViewModel,
    ValidationPageViewModel,
    NormalizationPageViewModel,
    HouseholdPageViewModel,
    DuplicatePageViewModel,
    AuditPageViewModel,
    ExportConsoleViewModel,
)


class ImportRepositoryProtocol(Protocol):
    """
    Abstract protocol for import data repository implementations.

    All repository implementations must define these 8 read-only methods
    with exact signatures and return types. Methods may not mutate raw
    import data or expose database/ORM internals.

    This protocol is the contract between routes/services and repository
    implementations. Swapping implementations does not require changes
    to routes, services, or templates.
    """

    def list_imports(self) -> List[ImportSummary]:
        """
        Return list of all import batches.

        Returns:
            List of ImportSummary frozen dataclasses, one per import batch.
            Each summary contains batch ID, filename, record count, status,
            and upload timestamp. Data is ready for /imports template rendering.

        Constraints:
            - Must return frozen dataclasses, not ORM objects
            - Must not mutate any raw import rows
            - Must not expose database sessions or connections
            - Return shape must match Phase 1A expectations
        """
        ...

    def get_dashboard(self, import_id: str) -> ImportDashboardViewModel:
        """
        Return import review dashboard data.

        Args:
            import_id: Import batch ID (e.g., "IMP-2025-0101-A").
                      May be used to query database in Phase 1B.
                      Fixture implementation ignores this parameter
                      and returns IMPORT_BATCH data.

        Returns:
            ImportDashboardViewModel frozen dataclass with:
            - batch metadata (id, filename, progress)
            - queue status cards (pending counts for each review queue)
            - navigation URLs (audit, exports, back to imports)
            Data is ready for /imports/<import_id>/dashboard template.

        Constraints:
            - Must return frozen dataclass, not ORM object
            - Must not mutate any raw import rows
            - Must not mutate queue status
            - Must not expose database sessions or connections
            - Return shape must match Phase 1A expectations
        """
        ...

    def get_validation(self, import_id: str) -> ValidationPageViewModel:
        """
        Return validation review page data.

        Args:
            import_id: Import batch ID.

        Returns:
            ValidationPageViewModel frozen dataclass with:
            - batch metadata
            - validation rows (one per contact record with validation issues)
            - validation issue count
            - total record count
            Data is ready for /imports/<import_id>/validation template.

        Constraints:
            - Must return frozen dataclass, not ORM objects
            - Must not mutate raw rows
            - Validation findings may be computed on-demand (Phase 1B)
              or stored in database (Phase 1B+)
            - Must not expose database sessions or connections
            - Return shape must match Phase 1A expectations
        """
        ...

    def get_normalizations(self, import_id: str) -> NormalizationPageViewModel:
        """
        Return normalization review page data.

        Args:
            import_id: Import batch ID.

        Returns:
            NormalizationPageViewModel frozen dataclass with:
            - batch metadata
            - current normalization suggestion
            - current suggestion index and total count
            Data is ready for /imports/<import_id>/normalizations template.

        Constraints:
            - Must return frozen dataclass, not ORM objects
            - Must not mutate raw rows or normalization suggestions
            - Suggestions are advisory only; reviewed values are not auto-applied
            - Must not expose database sessions or connections
            - Return shape must match Phase 1A expectations
        """
        ...

    def get_households(self, import_id: str) -> HouseholdPageViewModel:
        """
        Return household review page data.

        Args:
            import_id: Import batch ID.

        Returns:
            HouseholdPageViewModel frozen dataclass with:
            - batch metadata
            - current household suggestion
            - current household index and total count
            Data is ready for /imports/<import_id>/households template.

        Constraints:
            - Must return frozen dataclass, not ORM objects
            - Must not mutate raw rows or suggestions
            - Household suggestions are advisory; not auto-grouped
            - Current import batch only (no cross-import grouping)
            - Must not expose database sessions or connections
            - Return shape must match Phase 1A expectations
        """
        ...

    def get_duplicates(self, import_id: str, index: int = 0) -> DuplicatePageViewModel:
        """
        Return duplicate review page data.

        Args:
            import_id: Import batch ID.
            index: Zero-based index of duplicate pair to display. Clamped to valid range.
                  Defaults to 0 (first pair).

        Returns:
            DuplicatePageViewModel frozen dataclass with:
            - batch metadata
            - current duplicate candidate pair
            - current candidate index and total count
            - navigation metadata (has_previous, has_next, previous_index, next_index)
            Data is ready for /imports/<import_id>/duplicates template.

        Constraints:
            - Must return frozen dataclass, not ORM objects
            - Must not mutate raw rows or suggestions
            - Duplicate candidates are suggestions only, not auto-merged
            - Current import batch only (no cross-import deduplication)
            - Must not expose database sessions or connections
            - Must not generate export files
            - Must not write data to Givebutter or CRM
            - Return shape must match Phase 1A expectations
        """
        ...

    def get_audit(self, import_id: str) -> AuditPageViewModel:
        """
        Return audit log page data.

        Args:
            import_id: Import batch ID.

        Returns:
            AuditPageViewModel frozen dataclass with:
            - batch metadata
            - all audit log entries (append-only, immutable)
            Data is ready for /imports/<import_id>/audit template.

        Constraints:
            - Must return frozen dataclass, not ORM objects
            - Audit log is immutable (append-only in database)
            - No edits or deletions to audit entries
            - Must not expose database sessions or connections
            - Return shape must match Phase 1A expectations
        """
        ...

    def get_exports(self, import_id: str) -> ExportConsoleViewModel:
        """
        Return export console page data.

        Args:
            import_id: Import batch ID.

        Returns:
            ExportConsoleViewModel frozen dataclass with:
            - batch metadata
            - export card definitions (CSV, household, etc.)
            - export staging statistics (record counts, decision counts)
            - recent export packages (metadata-only, no files in Phase 1B)
            Data is ready for /imports/<import_id>/exports template.

        Constraints:
            - Must return frozen dataclass, not ORM objects
            - Export staging is computed from raw rows + decisions
              (not stored in Phase 1B)
            - Must not generate export files in Phase 1B
            - Must not write data to Givebutter or CRM
            - Decisions do not auto-approve exports
            - Must not expose database sessions or connections
            - Return shape must match Phase 1A expectations
        """
        ...
