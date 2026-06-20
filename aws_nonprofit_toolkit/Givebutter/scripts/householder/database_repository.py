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

from .database_models import Base, ImportBatch, ImportContact, RawImportRow, ReviewItem, ReviewDecision, ReviewItemSubject, AuditLogRecord
from .service_contracts import (
    ImportSummary, ImportDashboardViewModel, DashboardQueueCard,
    ValidationRow, ValidationPageViewModel,
    NormalizationRow, NormalizationPageViewModel,
    HouseholdRow, HouseholdPageViewModel,
    DuplicateContact, DuplicateCandidate, DuplicatePageViewModel,
    AuditLogEntry, AuditPageViewModel,
    ExportCard, ExportConsoleViewModel
)
from .export_config import EXPORT_CARD_DEFINITIONS


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

    def get_dashboard(self, import_id: str) -> ImportDashboardViewModel:
        """
        Return import dashboard data as ImportDashboardViewModel.

        Queries ImportBatch and ReviewItem records to compute dashboard
        queue counts. Returns view model ready for template rendering.

        Args:
            import_id: Import batch ID to retrieve dashboard for.

        Returns:
            ImportDashboardViewModel with batch metadata and queue card data.

        Raises:
            Exception: If database connection fails or batch not found.
        """
        session = get_db_session(self.database_url)
        try:
            # Query the batch
            batch = session.query(ImportBatch).filter_by(id=import_id).first()
            if not batch:
                # Return empty/default dashboard if batch not found
                return ImportDashboardViewModel(
                    batch_id=import_id,
                    filename='',
                    progress=0,
                    queues=(),
                    audit_log_url=f'/imports/{import_id}/audit',
                    export_console_url=f'/imports/{import_id}/exports',
                    back_to_imports_url='/imports',
                )

            # Compute progress
            total_items = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id
            ).scalar() or 0

            if total_items > 0:
                decided_items = session.query(func.count(ReviewDecision.id)).filter(
                    ReviewDecision.batch_id == import_id
                ).scalar() or 0
                progress = int((decided_items / total_items) * 100)
            else:
                progress = 0

            # Compute queue pending counts by review_item type and status
            duplicates_pending = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'duplicate',
                ReviewItem.status == 'pending'
            ).scalar() or 0

            validation_pending = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'validation',
                ReviewItem.status == 'pending'
            ).scalar() or 0

            normalizations_pending = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'normalization',
                ReviewItem.status == 'pending'
            ).scalar() or 0

            households_pending = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'household',
                ReviewItem.status == 'pending'
            ).scalar() or 0

            # Build queue cards (frozen dataclasses)
            queue_cards = (
                DashboardQueueCard(
                    name='Possible Duplicates',
                    description='Side-by-side comparison: mark records as the same person',
                    pending_count=duplicates_pending,
                    badge_color='badge-amber',
                    action_label='Review Duplicates',
                    action_url=f'/imports/{import_id}/duplicates',
                ),
                DashboardQueueCard(
                    name='Validation Review',
                    description='Inspect all records, identify validation issues',
                    pending_count=validation_pending,
                    badge_color='badge-red',
                    action_label='Review Records',
                    action_url=f'/imports/{import_id}/validation',
                ),
                DashboardQueueCard(
                    name='Normalizations',
                    description='Review field cleanup suggestions',
                    pending_count=normalizations_pending,
                    badge_color='badge-blue',
                    action_label='Review Normalizations',
                    action_url=f'/imports/{import_id}/normalizations',
                ),
                DashboardQueueCard(
                    name='Households',
                    description='Confirm/defer household groupings',
                    pending_count=households_pending,
                    badge_color='badge-green',
                    action_label='Review Households',
                    action_url=f'/imports/{import_id}/households',
                ),
            )

            return ImportDashboardViewModel(
                batch_id=batch.id,
                filename=batch.filename,
                progress=progress,
                queues=queue_cards,
                audit_log_url=f'/imports/{import_id}/audit',
                export_console_url=f'/imports/{import_id}/exports',
                back_to_imports_url='/imports',
            )

        finally:
            session.close()

    def get_validation(self, import_id: str) -> ValidationPageViewModel:
        """
        Return validation review page data as ValidationPageViewModel.

        Queries ImportBatch and ImportContact records to build validation page
        with all contact records and validation issues. Returns view model ready
        for template rendering.

        Args:
            import_id: Import batch ID to retrieve validation data for.

        Returns:
            ValidationPageViewModel with batch metadata and validation rows.

        Raises:
            Exception: If database connection fails.
        """
        session = get_db_session(self.database_url)
        try:
            # Query the batch
            batch = session.query(ImportBatch).filter_by(id=import_id).first()
            if not batch:
                # Return empty validation page if batch not found
                return ValidationPageViewModel(
                    batch_id=import_id,
                    filename='',
                    progress=0,
                    validation_rows=(),
                    validation_issues_count=0,
                    total_records=0,
                )

            # Compute progress
            total_items = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id
            ).scalar() or 0

            if total_items > 0:
                decided_items = session.query(func.count(ReviewDecision.id)).filter(
                    ReviewDecision.batch_id == import_id
                ).scalar() or 0
                progress = int((decided_items / total_items) * 100)
            else:
                progress = 0

            # Count validation issues (review_items with item_type='validation', status='pending')
            validation_issues_count = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'validation',
                ReviewItem.status == 'pending'
            ).scalar() or 0

            # Query all ImportContact records for this batch
            contacts = session.query(ImportContact).filter_by(batch_id=import_id).all()

            # Build mapping of contact_id -> validation issue details
            validation_map = {}
            validation_reviews = session.query(ReviewItem, ReviewItemSubject).join(
                ReviewItemSubject
            ).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'validation'
            ).all()

            for review_item, subject in validation_reviews:
                if subject.subject_type == 'import_contact_snapshot':
                    contact_id = subject.subject_id
                    payload = review_item.payload_json or {}
                    if contact_id not in validation_map:
                        # Map reason codes to issue_type codes that validation_service expects
                        reason = payload.get('reason', '')
                        reason_to_issue_type = {
                            'missing': 'missing-required',
                            'possible_typo': 'format-invalid',
                            'format': 'format-invalid',
                            'typo': 'format-invalid',
                        }
                        issue_type = reason_to_issue_type.get(reason, 'format-invalid' if reason else None)

                        validation_map[contact_id] = {
                            'issue_type': issue_type,
                            'issue_description': payload.get('description'),
                            'field': payload.get('field'),
                            'reason': payload.get('reason'),
                            'review_item_id': review_item.id,
                        }

            # Import effective values function and issue recalculation
            from .autosave_service import get_effective_values
            from .issue_recalculation_service import recalculate_row_issues

            # Build validation rows from contacts
            validation_rows = []
            for contact in contacts:
                # Fetch transaction_id from raw import row
                raw_row = session.query(RawImportRow).filter_by(id=contact.raw_import_row_id).first()
                raw_csv_data = raw_row.raw_csv_data if raw_row else {}
                transaction_id = raw_csv_data.get('transaction_id', '')

                # Get effective values (raw + corrections) first
                try:
                    effective = get_effective_values(import_id, contact.raw_import_row_id, self.database_url)
                except Exception:
                    # Fall back to raw values if effective values can't be computed
                    effective = {}

                # Use effective name, fall back to contact values if not in corrections
                effective_name = effective.get('name', '')
                if not effective_name:
                    if contact.first_name and contact.last_name:
                        effective_name = f'{contact.first_name} {contact.last_name}'
                    elif contact.first_name:
                        effective_name = contact.first_name
                    elif contact.last_name:
                        effective_name = contact.last_name

                # Use effective address, fall back to contact values if not in corrections
                effective_address = effective.get('address', '')
                if not effective_address:
                    address_parts = []
                    if contact.address_line1:
                        address_parts.append(contact.address_line1)
                    if contact.address_line2:
                        address_parts.append(contact.address_line2)
                    if contact.city:
                        address_parts.append(contact.city)
                    if contact.state:
                        address_parts.append(contact.state)
                    if contact.postal_code:
                        address_parts.append(contact.postal_code)
                    effective_address = ', '.join(address_parts) if address_parts else ''

                # Use effective email and phone, fall back to contact values if not in corrections
                effective_email = effective.get('email', contact.email or '')
                effective_phone = effective.get('phone', contact.phone or '')

                # Format amount from effective values, fall back to contact amount
                amount_str = ''
                effective_amount = effective.get('amount')
                if effective_amount is not None:
                    try:
                        amount_val = float(str(effective_amount).replace('$', '').replace(',', '').strip())
                        amount_str = f'${amount_val:,.2f}'
                    except (ValueError, AttributeError):
                        amount_str = ''
                elif contact.amount is not None:
                    amount_str = f'${contact.amount:,.2f}'

                # Get current validation issues (recalculated based on effective values)
                try:
                    current_issues = recalculate_row_issues(import_id, contact.raw_import_row_id, self.database_url)
                except Exception:
                    current_issues = []

                # Use first issue if any exist
                issue_type = None
                issue_description = None
                issue_field = None
                issue_reason = None
                review_item_id = None
                if current_issues:
                    first_issue = current_issues[0]
                    issue_field = first_issue.get('field')
                    issue_description = first_issue.get('description')
                    review_item_id = first_issue.get('issue_id')
                    severity = first_issue.get('severity', 'warning')

                    # Map severity and field to issue_type codes that validation_service expects
                    if severity == 'error':
                        issue_type = 'missing-required'
                        issue_reason = 'missing'
                    else:
                        issue_type = 'format-invalid'
                        issue_reason = 'possible_typo'

                # Determine effective status from latest ReviewDecision
                effective_status = 'pending'
                if review_item_id:
                    latest_decision = (
                        session.query(ReviewDecision)
                        .filter_by(review_item_id=review_item_id)
                        .order_by(ReviewDecision.created_at.desc())
                        .first()
                    )
                    if latest_decision:
                        status_map = {
                            'accept_issue': 'accepted',
                            'dismiss_issue': 'dismissed',
                            'defer': 'deferred',
                        }
                        effective_status = status_map.get(latest_decision.decision, 'pending')

                # Create ValidationRow (using contact.id as string for consistency)
                # Use effective values for all editable fields (show corrections/reviewed_values)
                row = ValidationRow(
                    id=str(contact.id),
                    transaction_id=transaction_id,
                    date=effective.get('date', ''),  # Effective date from corrections if any
                    name=effective_name,  # Effective name (corrected or raw)
                    email=effective_email,  # Effective email (corrected or raw)
                    phone=effective_phone,  # Effective phone (corrected or raw)
                    amount=amount_str,  # Effective amount (corrected or raw)
                    address=effective_address,  # Effective address (corrected or raw)
                    raw_import_row_id=contact.raw_import_row_id,
                    issue_type=issue_type,
                    issue_description=issue_description,
                    issue_field=issue_field,
                    issue_reason=issue_reason,
                    effective_status=effective_status,
                )
                validation_rows.append(row)

            return ValidationPageViewModel(
                batch_id=batch.id,
                filename=batch.filename,
                progress=progress,
                validation_rows=tuple(validation_rows),
                validation_issues_count=validation_issues_count,
                total_records=len(contacts),
            )

        finally:
            session.close()

    def get_households(self, import_id: str, index: int = 0) -> HouseholdPageViewModel:
        """
        Return household review page data as HouseholdPageViewModel.

        Queries ImportBatch and household review_items to build household page
        with current household and navigation state. Returns view model ready
        for template rendering.

        Args:
            import_id: Import batch ID to retrieve household data for.
            index: Zero-based index of household to display. Clamped to valid range.

        Returns:
            HouseholdPageViewModel with batch metadata, current household, and index.

        Raises:
            Exception: If database connection fails.
        """
        session = get_db_session(self.database_url)
        try:
            # Query the batch
            batch = session.query(ImportBatch).filter_by(id=import_id).first()
            if not batch:
                # Return empty household page if batch not found
                return HouseholdPageViewModel(
                    batch_id=import_id,
                    filename='',
                    progress=0,
                    current_household=HouseholdRow(
                        id='',
                        suggested_name='',
                        address='',
                        confidence='',
                        proposed_members=(),
                        evidence=(),
                        conflicts=(),
                        status='Pending',
                        effective_status='pending',
                    ),
                    current_household_index=1,
                    total_households=0,
                )

            # Compute progress
            total_items = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id
            ).scalar() or 0

            if total_items > 0:
                decided_items = session.query(func.count(ReviewDecision.id)).filter(
                    ReviewDecision.batch_id == import_id
                ).scalar() or 0
                progress = int((decided_items / total_items) * 100)
            else:
                progress = 0

            # Query all household items, ordered by creation
            # Include all households (pending and decided), not just pending.
            # Effective status is derived from latest ReviewDecision.
            household_items = session.query(ReviewItem).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'household'
            ).order_by(ReviewItem.created_at.asc()).all()

            total_households = len(household_items)

            # Clamp index to valid range
            if total_households == 0:
                clamped_index = 0
            else:
                clamped_index = max(0, min(index, total_households - 1))

            # Get the household at clamped index as current household
            if household_items and clamped_index < len(household_items):
                current_item = household_items[clamped_index]
                payload = current_item.payload_json or {}

                # Extract proposed_members and convert to tuple
                proposed_members = payload.get('proposed_members', [])
                if isinstance(proposed_members, list):
                    proposed_members = tuple(proposed_members)

                # Extract evidence and convert to tuple
                evidence = payload.get('evidence', [])
                if isinstance(evidence, list):
                    evidence = tuple(evidence)

                # Extract conflicts and convert to tuple
                conflicts = payload.get('conflicts', [])
                if isinstance(conflicts, list):
                    conflicts = tuple(conflicts)

                # Derive effective status from latest ReviewDecision
                latest_decision = (
                    session.query(ReviewDecision)
                    .filter_by(review_item_id=current_item.id)
                    .order_by(ReviewDecision.created_at.desc())
                    .first()
                )
                effective_status = 'pending'
                if latest_decision:
                    status_map = {
                        'confirm_household': 'confirmed',
                        'reject_household': 'rejected',
                        'defer': 'deferred',
                    }
                    effective_status = status_map.get(latest_decision.decision, 'pending')

                current_household = HouseholdRow(
                    id=payload.get('id', str(current_item.id)),
                    suggested_name=payload.get('suggested_name', ''),
                    address=payload.get('address', ''),
                    confidence=payload.get('confidence', ''),
                    proposed_members=proposed_members,
                    evidence=evidence,
                    conflicts=conflicts,
                    status=payload.get('status', 'Pending'),
                    effective_status=effective_status,
                )
            else:
                # No households - return empty household
                current_household = HouseholdRow(
                    id='',
                    suggested_name='',
                    address='',
                    confidence='',
                    proposed_members=(),
                    evidence=(),
                    conflicts=(),
                    status='Pending',
                    effective_status='pending',
                )

            return HouseholdPageViewModel(
                batch_id=batch.id,
                filename=batch.filename,
                progress=progress,
                current_household=current_household,
                current_household_index=clamped_index + 1,  # 1-based for display
                total_households=total_households,
            )

        finally:
            session.close()

    def get_duplicates(self, import_id: str, index: int = 0) -> DuplicatePageViewModel:
        """
        Return duplicate review page data as DuplicatePageViewModel.

        Queries ImportBatch and duplicate review_items to build duplicate page
        with current candidate and navigation state. Returns view model ready
        for template rendering.

        Args:
            import_id: Import batch ID to retrieve duplicate data for.
            index: Zero-based index of duplicate pair to display. Clamped to valid range.

        Returns:
            DuplicatePageViewModel with batch metadata, current candidate, and index.

        Raises:
            Exception: If database connection fails.
        """
        session = get_db_session(self.database_url)
        try:
            # Query the batch
            batch = session.query(ImportBatch).filter_by(id=import_id).first()
            if not batch:
                # Return empty duplicate page if batch not found
                return DuplicatePageViewModel(
                    batch_id=import_id,
                    filename='',
                    progress=0,
                    current_candidate=DuplicateCandidate(
                        id='',
                        contact_a=DuplicateContact('', '', '', '', ''),
                        contact_b=DuplicateContact('', '', '', '', ''),
                        supporting_evidence=(),
                        conflicting_evidence=(),
                        status='Pending',
                    ),
                    current_candidate_index=1,
                    total_candidates=0,
                )

            # Compute progress
            total_items = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id
            ).scalar() or 0

            if total_items > 0:
                decided_items = session.query(func.count(ReviewDecision.id)).filter(
                    ReviewDecision.batch_id == import_id
                ).scalar() or 0
                progress = int((decided_items / total_items) * 100)
            else:
                progress = 0

            # Query all duplicate items, ordered by creation
            duplicate_items = session.query(ReviewItem).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'duplicate',
                ReviewItem.status == 'pending'
            ).order_by(ReviewItem.created_at.asc()).all()

            total_candidates = len(duplicate_items)

            # Clamp index to valid range
            if total_candidates == 0:
                clamped_index = 0
            else:
                clamped_index = max(0, min(index, total_candidates - 1))

            # Get the duplicate candidate at clamped index
            if duplicate_items and clamped_index < len(duplicate_items):
                current_item = duplicate_items[clamped_index]
                payload = current_item.payload_json or {}

                # Extract contact data from payload
                contact_a_data = payload.get('contact_a', {})
                contact_b_data = payload.get('contact_b', {})

                contact_a = DuplicateContact(
                    id=contact_a_data.get('id', ''),
                    name=contact_a_data.get('name', ''),
                    email=contact_a_data.get('email', ''),
                    phone=contact_a_data.get('phone', ''),
                    address=contact_a_data.get('address', ''),
                )

                contact_b = DuplicateContact(
                    id=contact_b_data.get('id', ''),
                    name=contact_b_data.get('name', ''),
                    email=contact_b_data.get('email', ''),
                    phone=contact_b_data.get('phone', ''),
                    address=contact_b_data.get('address', ''),
                )

                # Extract supporting and conflicting evidence
                supporting_evidence = payload.get('supporting_evidence', [])
                if isinstance(supporting_evidence, list):
                    supporting_evidence = tuple(supporting_evidence)

                conflicting_evidence = payload.get('conflicting_evidence', [])
                if isinstance(conflicting_evidence, list):
                    conflicting_evidence = tuple(conflicting_evidence)

                # Derive effective status from latest ReviewDecision
                latest_decision = (
                    session.query(ReviewDecision)
                    .filter_by(review_item_id=current_item.id)
                    .order_by(ReviewDecision.created_at.desc())
                    .first()
                )
                effective_status = 'pending'
                if latest_decision:
                    status_map = {
                        'same_person': 'same_person',
                        'different_people': 'different_people',
                        'defer': 'deferred',
                    }
                    effective_status = status_map.get(latest_decision.decision, 'pending')

                current_candidate = DuplicateCandidate(
                    id=payload.get('id', str(current_item.id)),
                    contact_a=contact_a,
                    contact_b=contact_b,
                    supporting_evidence=supporting_evidence,
                    conflicting_evidence=conflicting_evidence,
                    status=payload.get('status', 'Pending'),
                    effective_status=effective_status,
                )
            else:
                # No duplicates - return empty candidate
                current_candidate = DuplicateCandidate(
                    id='',
                    contact_a=DuplicateContact('', '', '', '', ''),
                    contact_b=DuplicateContact('', '', '', '', ''),
                    supporting_evidence=(),
                    conflicting_evidence=(),
                    status='Pending',
                    effective_status='pending',
                )

            return DuplicatePageViewModel(
                batch_id=batch.id,
                filename=batch.filename,
                progress=progress,
                current_candidate=current_candidate,
                current_candidate_index=clamped_index + 1,  # 1-based for display
                total_candidates=total_candidates,
            )

        finally:
            session.close()

    def get_audit(self, import_id: str) -> AuditPageViewModel:
        """
        Return audit log page data as AuditPageViewModel.

        Queries ImportBatch and audit log records to build audit page with all entries.
        Returns view model ready for template rendering.

        Args:
            import_id: Import batch ID to retrieve audit data for.

        Returns:
            AuditPageViewModel with batch metadata and audit log entries.

        Raises:
            Exception: If database connection fails.
        """
        session = get_db_session(self.database_url)
        try:
            # Query the batch
            batch = session.query(ImportBatch).filter_by(id=import_id).first()
            if not batch:
                # Return empty audit page if batch not found
                return AuditPageViewModel(
                    batch_id=import_id,
                    filename='',
                    progress=0,
                    audit_entries=(),
                )

            # Compute progress
            total_items = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id
            ).scalar() or 0

            if total_items > 0:
                decided_items = session.query(func.count(ReviewDecision.id)).filter(
                    ReviewDecision.batch_id == import_id
                ).scalar() or 0
                progress = int((decided_items / total_items) * 100)
            else:
                progress = 0

            # Query all audit log records for this batch, ordered by timestamp ascending
            audit_records = session.query(AuditLogRecord).filter_by(
                batch_id=import_id
            ).order_by(AuditLogRecord.action_timestamp.asc()).all()

            # Build audit entries from records
            audit_entries = []
            for record in audit_records:
                # Format details: handle dict, string, or None
                # Prefer displaying notes if available; fall back to full details
                details_str = ''
                if isinstance(record.details, dict):
                    import json
                    # Extract notes if present (displayed for Follow Up, Defer, etc.)
                    notes = record.details.get('notes')
                    if notes:
                        details_str = notes
                    else:
                        # Fall back to full details if no notes
                        details_str = json.dumps(record.details)
                elif isinstance(record.details, str):
                    details_str = record.details
                else:
                    details_str = ''

                entry = AuditLogEntry(
                    timestamp=str(record.action_timestamp) if record.action_timestamp else '',
                    reviewer=record.actor or 'System',
                    action=record.action_type or '',
                    details=details_str,
                )
                audit_entries.append(entry)

            return AuditPageViewModel(
                batch_id=batch.id,
                filename=batch.filename,
                progress=progress,
                audit_entries=tuple(audit_entries),
            )

        finally:
            session.close()

    def get_exports(self, import_id: str) -> ExportConsoleViewModel:
        """
        Return export console page data as ExportConsoleViewModel.

        Queries ImportBatch and computes export statistics from Option C database state.
        Returns view model ready for template rendering.

        Args:
            import_id: Import batch ID to retrieve export data for.

        Returns:
            ExportConsoleViewModel with batch metadata and export options.

        Raises:
            Exception: If database connection fails.
        """
        session = get_db_session(self.database_url)
        try:
            # Query the batch
            batch = session.query(ImportBatch).filter_by(id=import_id).first()
            if not batch:
                # Return empty exports page if batch not found
                return ExportConsoleViewModel(
                    batch_id=import_id,
                    filename='',
                    progress=0,
                    export_cards=(),
                    staged_record_count=0,
                    total_decisions=0,
                    household_count=0,
                    recent_exports=(),
                )

            # Compute progress
            total_items = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id
            ).scalar() or 0

            if total_items > 0:
                decided_items = session.query(func.count(ReviewDecision.id)).filter(
                    ReviewDecision.batch_id == import_id
                ).scalar() or 0
                progress = int((decided_items / total_items) * 100)
            else:
                progress = 0

            # Build export cards from static export card definitions
            export_cards = []
            for card in EXPORT_CARD_DEFINITIONS:
                export_cards.append(
                    ExportCard(
                        id=card['id'],
                        title=card['name'],
                        description=card['description'],
                        status=card['status'],
                        files_ready=card['files_ready'],
                    )
                )

            # Count staged records (import_contacts for this batch)
            staged_record_count = session.query(func.count(ImportContact.id)).filter(
                ImportContact.batch_id == import_id
            ).scalar() or 0

            # Calculate total decisions (sum of supporting_evidence counts from duplicate items)
            total_decisions = 0
            duplicate_items = session.query(ReviewItem).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'duplicate'
            ).all()

            for item in duplicate_items:
                if item.payload_json and 'supporting_evidence' in item.payload_json:
                    evidence_list = item.payload_json.get('supporting_evidence', [])
                    total_decisions += len(evidence_list)

            # Count household items
            household_count = session.query(func.count(ReviewItem.id)).filter(
                ReviewItem.batch_id == import_id,
                ReviewItem.item_type == 'household'
            ).scalar() or 0

            # Recent exports are empty in Phase 1B
            recent_exports = ()

            return ExportConsoleViewModel(
                batch_id=batch.id,
                filename=batch.filename,
                progress=progress,
                export_cards=tuple(export_cards),
                staged_record_count=staged_record_count,
                total_decisions=total_decisions,
                household_count=household_count,
                recent_exports=recent_exports,
            )

        finally:
            session.close()
