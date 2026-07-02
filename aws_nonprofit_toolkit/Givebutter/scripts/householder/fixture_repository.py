"""
Fixture Repository - Serves Phase 0 fixture data through service interface.

This adapter allows screens to be backed by fixtures during Phase 1A while
maintaining the service boundary. Later, this can be swapped for SQLiteRepository
or other implementations without changing routes or templates.

Does not mutate fixtures. Provides read-only access only.
"""

from typing import List
from datetime import datetime

try:
    from scripts.uploader.fixtures import (
        IMPORTS_LIST,
        IMPORT_BATCH,
        QUEUE_STATUS,
        CONTACTS,
        HOUSEHOLD_SUGGESTIONS,
        DUPLICATE_CANDIDATES,
        AUDIT_LOG_ENTRIES,
        EXPORT_CARDS,
    )
except ImportError:
    # Fallback for direct script execution
    from uploader.fixtures import (
        IMPORTS_LIST,
        IMPORT_BATCH,
        QUEUE_STATUS,
        CONTACTS,
        HOUSEHOLD_SUGGESTIONS,
        DUPLICATE_CANDIDATES,
        AUDIT_LOG_ENTRIES,
        EXPORT_CARDS,
    )

from .service_contracts import (
    ImportSummary,
    DashboardQueueCard,
    ImportDashboardViewModel,
    ValidationRow,
    ValidationPageViewModel,
    NormalizationRow,
    NormalizationPageViewModel,
    HouseholdRow,
    HouseholdPageViewModel,
    DuplicateContact,
    DuplicateCandidate,
    DuplicatePageViewModel,
    AuditLogEntry,
    AuditPageViewModel,
    ExportCard,
    ExportConsoleViewModel,
)


class FixtureImportRepository:
    """
    Provides fixture import data through service interface.

    This repository adapts Phase 0 fixture data into service-contract
    view models. It can be swapped for other implementations (e.g.,
    SQLiteRepository) without changing routes or templates.
    """

    @staticmethod
    def list_imports() -> List[ImportSummary]:
        """
        Return list of all imports as ImportSummary view models.

        Returns:
            List of ImportSummary objects ready for template rendering.
            Data is shaped to match what /imports template expects.
        """
        summaries = []

        for import_item in IMPORTS_LIST:
            # Format timestamp as relative time string
            uploaded_str = None
            if 'uploaded_at' in import_item:
                dt_value = import_item['uploaded_at']
                if isinstance(dt_value, datetime):
                    uploaded_str = FixtureImportRepository._format_relative_time(dt_value)
                else:
                    uploaded_str = str(dt_value)

            summary = ImportSummary(
                id=import_item['id'],
                filename=import_item['filename'],
                record_count=import_item['record_count'],
                status=import_item['status'],
                progress=import_item['progress'],
                uploaded_timestamp=uploaded_str,
            )
            summaries.append(summary)

        return summaries

    @staticmethod
    def get_dashboard(import_id: str) -> ImportDashboardViewModel:
        """
        Return import dashboard data as ImportDashboardViewModel.

        Adapts IMPORT_BATCH and QUEUE_STATUS fixtures into dashboard
        view model. Returns data ready for template rendering.

        Args:
            import_id: Import ID (unused for fixture data, preserved for API consistency)

        Returns:
            ImportDashboardViewModel with batch and queue status.
        """
        # Build queue cards in order: Duplicates, Validation, Normalizations, Households
        queue_cards = (
            DashboardQueueCard(
                name="Possible Duplicates",
                description="Side-by-side comparison: mark records as the same person",
                pending_count=QUEUE_STATUS.get('duplicates_pending', 0),
                badge_color="badge-amber",
                action_label="Review Duplicates",
                action_url=f"/imports/{IMPORT_BATCH['id']}/duplicates",
            ),
            DashboardQueueCard(
                name="Validation Review",
                description="Inspect all records, identify validation issues",
                pending_count=QUEUE_STATUS.get('validation_issues', 0),
                badge_color="badge-red",
                action_label="Review Records",
                action_url=f"/imports/{IMPORT_BATCH['id']}/validation",
            ),
            DashboardQueueCard(
                name="Normalizations",
                description="Review field cleanup suggestions",
                pending_count=QUEUE_STATUS.get('normalizations_pending', 0),
                badge_color="badge-blue",
                action_label="Review Normalizations",
                action_url=f"/imports/{IMPORT_BATCH['id']}/normalizations",
            ),
            DashboardQueueCard(
                name="Households",
                description="Confirm/defer household groupings",
                pending_count=QUEUE_STATUS.get('households_pending', 0),
                badge_color="badge-green",
                action_label="Review Households",
                action_url=f"/imports/{IMPORT_BATCH['id']}/households",
            ),
        )

        return ImportDashboardViewModel(
            batch_id=IMPORT_BATCH['id'],
            filename=IMPORT_BATCH['filename'],
            progress=IMPORT_BATCH['progress'],
            queues=queue_cards,
            audit_log_url=f"/imports/{IMPORT_BATCH['id']}/audit",
            export_console_url=f"/imports/{IMPORT_BATCH['id']}/exports",
            back_to_imports_url="/imports",
        )

    @staticmethod
    def get_validation(import_id: str) -> ValidationPageViewModel:
        """
        Return validation review page data as ValidationPageViewModel.

        Adapts IMPORT_BATCH and CONTACTS fixtures into validation page
        view model. Returns data ready for template rendering.

        Args:
            import_id: Import ID (unused for fixture data, preserved for API consistency)

        Returns:
            ValidationPageViewModel with batch, validation records, and queue status.
        """
        validation_rows = tuple(
            ValidationRow(
                id=contact['id'],
                transaction_id=contact['id'],  # Transaction ID matches record ID in fixtures
                date=contact['date'],
                name=contact['name'],
                email=contact['email'],
                phone=contact['phone'],
                amount=contact['amount'],
                address=contact['address'],
                raw_import_row_id=idx + 1,  # Use 1-based index as row identifier for fixtures
                issue_type=contact.get('issue_type'),
                issue_description=contact.get('issue_description'),
                issue_field=contact.get('issue_field'),
            )
            for idx, contact in enumerate(CONTACTS)
        )

        return ValidationPageViewModel(
            batch_id=IMPORT_BATCH['id'],
            filename=IMPORT_BATCH['filename'],
            progress=IMPORT_BATCH['progress'],
            validation_rows=validation_rows,
            validation_issues_count=QUEUE_STATUS.get('validation_issues', 0),
            total_records=IMPORT_BATCH['record_count'],
        )

    @staticmethod
    def get_households(import_id: str, index: int = 0) -> HouseholdPageViewModel:
        """
        Return households review page data as HouseholdPageViewModel.

        Adapts IMPORT_BATCH and HOUSEHOLD_SUGGESTIONS fixtures into
        household page view model. Returns current household with batch info.

        Args:
            import_id: Import ID (unused for fixture data, preserved for API consistency)
            index: Zero-based index of household to display. Clamped to valid range.

        Returns:
            HouseholdPageViewModel with batch, current household, and navigation state.
        """
        total = len(HOUSEHOLD_SUGGESTIONS)

        # Clamp index to valid range
        if total == 0:
            clamped_index = 0
        else:
            clamped_index = max(0, min(index, total - 1))

        # Get household at clamped index or create empty one if none available
        current_household_data = (
            HOUSEHOLD_SUGGESTIONS[clamped_index] if clamped_index < total else None
        )

        if not current_household_data:
            # Handle empty households list gracefully
            current_household = HouseholdRow(
                id="",
                suggested_name="",
                address="",
                confidence="",
                proposed_members=(),
                evidence=(),
                conflicts=(),
                status="Pending",
            )
        else:
            current_household = HouseholdRow(
                id=current_household_data['id'],
                suggested_name=current_household_data['suggested_name'],
                address=current_household_data['address'],
                confidence=current_household_data['confidence'],
                proposed_members=tuple(current_household_data['proposed_members']),
                evidence=tuple(current_household_data['evidence']),
                conflicts=tuple(current_household_data.get('conflicts', [])),
                status=current_household_data.get('status', 'Pending'),
            )

        return HouseholdPageViewModel(
            batch_id=IMPORT_BATCH['id'],
            filename=IMPORT_BATCH['filename'],
            progress=IMPORT_BATCH['progress'],
            current_household=current_household,
            current_household_index=clamped_index + 1,  # 1-based for display
            total_households=total,
        )

    @staticmethod
    def get_duplicates(import_id: str, index: int = 0) -> DuplicatePageViewModel:
        """
        Return duplicates review page data as DuplicatePageViewModel.

        Adapts IMPORT_BATCH and DUPLICATE_CANDIDATES fixtures into
        duplicate page view model. Returns current candidate with batch info.

        Args:
            import_id: Import ID (unused for fixture data, preserved for API consistency)
            index: Zero-based index of duplicate pair to display. Clamped to valid range.

        Returns:
            DuplicatePageViewModel with batch, current candidate, and navigation state.
        """
        total = len(DUPLICATE_CANDIDATES)

        # Clamp index to valid range
        if total == 0:
            clamped_index = 0
        else:
            clamped_index = max(0, min(index, total - 1))

        # Get candidate at clamped index or create empty one if none available
        current_candidate_data = (
            DUPLICATE_CANDIDATES[clamped_index] if clamped_index < total else None
        )

        if not current_candidate_data:
            # Handle empty candidates list gracefully
            current_candidate = DuplicateCandidate(
                id="",
                contact_a=DuplicateContact("", "", "", "", ""),
                contact_b=DuplicateContact("", "", "", "", ""),
                supporting_evidence=(),
                conflicting_evidence=(),
                status="Pending",
            )
        else:
            contact_a_data = current_candidate_data['contact_a']
            contact_b_data = current_candidate_data['contact_b']
            current_candidate = DuplicateCandidate(
                id=current_candidate_data['id'],
                contact_a=DuplicateContact(
                    id=contact_a_data['id'],
                    name=contact_a_data['name'],
                    email=contact_a_data['email'],
                    phone=contact_a_data['phone'],
                    address=contact_a_data['address'],
                ),
                contact_b=DuplicateContact(
                    id=contact_b_data['id'],
                    name=contact_b_data['name'],
                    email=contact_b_data['email'],
                    phone=contact_b_data['phone'],
                    address=contact_b_data['address'],
                ),
                supporting_evidence=tuple(current_candidate_data['supporting_evidence']),
                conflicting_evidence=tuple(current_candidate_data.get('conflicting_evidence', [])),
                status=current_candidate_data.get('status', 'Pending'),
            )

        return DuplicatePageViewModel(
            batch_id=IMPORT_BATCH['id'],
            filename=IMPORT_BATCH['filename'],
            progress=IMPORT_BATCH['progress'],
            current_candidate=current_candidate,
            current_candidate_index=clamped_index + 1,  # 1-based for display
            total_candidates=total,
        )

    @staticmethod
    def get_audit(import_id: str) -> AuditPageViewModel:
        """
        Return audit log page data as AuditPageViewModel.

        Adapts IMPORT_BATCH and AUDIT_LOG_ENTRIES fixtures into audit
        page view model. Returns all entries for immutable compliance record.

        Args:
            import_id: Import ID (unused for fixture data, preserved for API consistency)

        Returns:
            AuditPageViewModel with batch and all audit entries.
        """
        audit_entries = tuple(
            AuditLogEntry(
                timestamp=str(entry['timestamp']),
                reviewer=entry['reviewer'],
                action=entry['action'],
                details=entry.get('notes', ''),
            )
            for entry in AUDIT_LOG_ENTRIES
        )

        return AuditPageViewModel(
            batch_id=IMPORT_BATCH['id'],
            filename=IMPORT_BATCH['filename'],
            progress=IMPORT_BATCH['progress'],
            audit_entries=audit_entries,
        )

    @staticmethod
    def get_exports(import_id: str) -> ExportConsoleViewModel:
        """
        Return export console page data as ExportConsoleViewModel.

        Adapts IMPORT_BATCH and EXPORT_CARDS fixtures into export console
        view model with staging statistics. Returns all export options.

        Args:
            import_id: Import ID (unused for fixture data, preserved for API consistency)

        Returns:
            ExportConsoleViewModel with batch, export cards, and staging statistics.
        """
        export_cards = tuple(
            ExportCard(
                id=card['id'],
                title=card['name'],
                description=card['description'],
                status=card['status'],
                files_ready=card['files_ready'],
            )
            for card in EXPORT_CARDS
        )

        # Calculate staging statistics from fixtures
        staged_record_count = len(CONTACTS)
        total_decisions = sum(
            len(dc.get('supporting_evidence', [])) for dc in DUPLICATE_CANDIDATES
        )
        household_count = len(HOUSEHOLD_SUGGESTIONS)

        return ExportConsoleViewModel(
            batch_id=IMPORT_BATCH['id'],
            filename=IMPORT_BATCH['filename'],
            progress=IMPORT_BATCH['progress'],
            export_cards=export_cards,
            staged_record_count=staged_record_count,
            total_decisions=total_decisions,
            household_count=household_count,
            recent_exports=(),
        )

    @staticmethod
    def _format_relative_time(dt: datetime) -> str:
        """
        Format datetime as relative time string (e.g., '2h ago').

        Consistent with existing app.py format_relative_time utility.
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
