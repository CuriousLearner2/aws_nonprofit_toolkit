"""
Export Preview Service - Derives export rows from decisions without mutations.

Phase 2-Step 12: Builds preview of export rows based on accepted reviewer decisions.
Preview is read-only: no file generation, no audit log, no mutations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Mapping, Any
import hashlib
import json

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from .database_models import (
    ImportBatch, ImportContact, RawImportRow, ReviewItem, ReviewDecision
)
from .service_contracts import ExportRow, ExportPreviewResult


def _get_validation_issue_type(payload):
    """
    Get issue type from validation payload, supporting both real and legacy formats.

    Real ingestion creates payloads with 'issue' field.
    Tests/legacy payloads use 'issue_type' field.
    This function normalizes the lookup to support both.

    Args:
        payload: Validation review item payload (dict or None)

    Returns:
        Issue type string or 'unknown' if field not found
    """
    if not payload:
        return 'unknown'

    # Real ingestion format
    if 'issue' in payload:
        return payload.get('issue')

    # Legacy/test format
    return payload.get('issue_type', 'unknown')


def build_export_preview(
    import_id: str,
    config: Optional[Mapping[str, Any]] = None,
) -> ExportPreviewResult:
    """
    Build preview of derived export rows based on reviewer decisions.

    Workflow:
    1. Query import_contacts for this batch
    2. Query all reviewer decisions
    3. For each contact, build preview row:
       - Start with original snapshot values
       - Apply accepted normalizations
       - Detect validation blockers/warnings
       - Derive duplicate grouping if same_person
       - Derive household grouping if confirm_household
    4. Return preview with rows, blockers, warnings, readiness

    Does NOT:
    - Mutate any source data
    - Generate files
    - Write audit log entries
    - Call external systems

    Args:
        import_id: Import batch ID to derive export for
        config: Optional configuration for database selection

    Returns:
        ExportPreviewResult with rows, blockers, warnings, readiness

    Raises:
        ValueError: If batch not found or configuration invalid
    """
    from .repository_provider import get_import_repository

    if not config:
        config = {}

    # Get database URL from config or environment
    database_url = config.get('GIVEBUTTER_DATABASE_URL')
    if not database_url:
        import os
        database_url = os.environ.get('GIVEBUTTER_DATABASE_URL')

    if not database_url:
        raise ValueError(
            "Export preview requires database configuration. "
            "Set GIVEBUTTER_DATABASE_URL environment variable or pass config."
        )

    # Create database session
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Verify batch exists
        batch = session.query(ImportBatch).filter_by(id=import_id).first()
        if not batch:
            raise ValueError(f"Import batch '{import_id}' not found")

        # Query all contacts, raw rows, review items, and decisions
        contacts = session.query(ImportContact).filter_by(
            batch_id=import_id
        ).order_by(ImportContact.id.asc()).all()

        raw_rows = {
            r.id: r for r in session.query(RawImportRow).filter_by(
                batch_id=import_id
            ).all()
        }

        review_items = {
            i.id: i for i in session.query(ReviewItem).filter_by(
                batch_id=import_id
            ).all()
        }

        # Query all decisions by type
        validation_decisions = {}
        normalization_decisions = {}
        duplicate_decisions = {}
        household_decisions = {}
        row_level_autosave_decisions = {}

        for decision in session.query(ReviewDecision).filter_by(
            batch_id=import_id
        ).order_by(ReviewDecision.created_at.asc(), ReviewDecision.id.asc()).all():
            # Handle row-level autosave decisions (review_item_id=None)
            if decision.review_item_id is None:
                raw_row_id = decision.raw_import_row_id
                if raw_row_id not in row_level_autosave_decisions:
                    row_level_autosave_decisions[raw_row_id] = {}
                # Merge all reviewed_values for this row (later decisions override earlier)
                if decision.reviewed_values:
                    row_level_autosave_decisions[raw_row_id].update(decision.reviewed_values)
                continue

            # Get the latest decision for each review item
            item = review_items.get(decision.review_item_id)
            if not item:
                continue

            if item.item_type == 'validation':
                if decision.review_item_id not in validation_decisions:
                    validation_decisions[decision.review_item_id] = decision
                elif decision.created_at > validation_decisions[decision.review_item_id].created_at:
                    validation_decisions[decision.review_item_id] = decision
            elif item.item_type == 'normalization':
                if decision.review_item_id not in normalization_decisions:
                    normalization_decisions[decision.review_item_id] = decision
                elif decision.created_at > normalization_decisions[decision.review_item_id].created_at:
                    normalization_decisions[decision.review_item_id] = decision
            elif item.item_type == 'duplicate':
                if decision.review_item_id not in duplicate_decisions:
                    duplicate_decisions[decision.review_item_id] = decision
                elif decision.created_at > duplicate_decisions[decision.review_item_id].created_at:
                    duplicate_decisions[decision.review_item_id] = decision
            elif item.item_type == 'household':
                if decision.review_item_id not in household_decisions:
                    household_decisions[decision.review_item_id] = decision
                elif decision.created_at > household_decisions[decision.review_item_id].created_at:
                    household_decisions[decision.review_item_id] = decision

        # Count deferred households
        deferred_household_count = 0
        for hh_item in session.query(ReviewItem).filter(
            ReviewItem.batch_id == import_id,
            ReviewItem.item_type == 'household'
        ).all():
            hh_decision = household_decisions.get(hh_item.id)
            if hh_decision is None:
                # No decision - counts as unresolved
                deferred_household_count += 1
            elif hh_decision.decision == 'defer':
                deferred_household_count += 1

        # Count unresolved/deferred duplicates (mirror household pattern)
        deferred_duplicate_count = 0
        for dup_item in session.query(ReviewItem).filter(
            ReviewItem.batch_id == import_id,
            ReviewItem.item_type == 'duplicate'
        ).all():
            dup_decision = duplicate_decisions.get(dup_item.id)
            if dup_decision is None:
                # No decision - counts as unresolved
                deferred_duplicate_count += 1
            elif dup_decision.decision == 'defer':
                deferred_duplicate_count += 1

        # Count deferred validation items (mirror household/duplicate pattern)
        deferred_validation_count = 0
        for val_item in session.query(ReviewItem).filter(
            ReviewItem.batch_id == import_id,
            ReviewItem.item_type == 'validation'
        ).all():
            val_decision = validation_decisions.get(val_item.id)
            if val_decision and val_decision.decision == 'defer':
                deferred_validation_count += 1

        # Build preview rows
        rows = []
        blockers = []
        warnings = []

        for contact in contacts:
            row_blockers = []
            row_warnings = []

            # Start with original snapshot values
            raw_row = raw_rows.get(contact.raw_import_row_id)
            row_index = raw_row.row_index if raw_row else None

            # Extract transaction_id from raw CSV data
            transaction_id = None
            if raw_row and raw_row.raw_csv_data:
                csv_data = raw_row.raw_csv_data
                if isinstance(csv_data, str):
                    try:
                        csv_data = json.loads(csv_data)
                    except Exception:
                        csv_data = {}
                transaction_id = csv_data.get('transaction_id') or csv_data.get('TransactionID')

            # Collect normalization decisions affecting this contact
            normalized_fields = []
            normalization_warnings = []
            field_values = {
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'email': contact.email,
                'phone': contact.phone,
                'address_line1': contact.address_line1,
                'address_line2': contact.address_line2,
                'city': contact.city,
                'state': contact.state,
                'postal_code': contact.postal_code,
                'amount': str(contact.amount) if contact.amount else None,
            }

            # Apply row-level autosave corrections (merged reviewed_values from all autosaves for this row)
            row_autosave_values = row_level_autosave_decisions.get(contact.raw_import_row_id)
            if row_autosave_values:
                field_values.update(row_autosave_values)

            # Apply normalization decisions
            for norm_item in review_items.values():
                if norm_item.item_type != 'normalization':
                    continue
                if norm_item.batch_id != import_id:
                    continue

                norm_decision = normalization_decisions.get(norm_item.id)
                if not norm_decision:
                    # Unresolved normalization
                    try:
                        payload = norm_item.payload_json or {}
                        if isinstance(payload, str):
                            payload = json.loads(payload)
                        field = payload.get('field', 'unknown')
                        normalization_warnings.append(f"Field {field} normalization unresolved")
                    except Exception:
                        normalization_warnings.append("Normalization unresolved")
                    continue

                # Apply decision
                if norm_decision.decision == 'accept_normalization':
                    try:
                        payload = norm_decision.reviewed_values or {}
                        field = payload.get('field')
                        normalized_value = payload.get('normalized_value')
                        if field and field in field_values and normalized_value:
                            field_values[field] = normalized_value
                            normalized_fields.append(field)
                    except Exception:
                        normalization_warnings.append("Error applying normalization")
                elif norm_decision.decision == 'reject_normalization':
                    # Keep original, no warning
                    pass
                elif norm_decision.decision == 'defer':
                    try:
                        payload = norm_decision.reviewed_values or {}
                        field = payload.get('field', 'unknown')
                        normalization_warnings.append(f"Field {field} normalization deferred")
                    except Exception:
                        pass

            # Apply household/duplicate decision reviewed field values
            # (household confirmed or duplicate same_person may include field corrections)
            for hh_item in review_items.values():
                if hh_item.item_type != 'household' or hh_item.batch_id != import_id:
                    continue
                hh_decision = household_decisions.get(hh_item.id)
                if hh_decision and hh_decision.decision == 'confirm_household':
                    payload = hh_decision.reviewed_values or {}
                    # Apply any field corrections stored in reviewed_values (e.g., 'last_name', 'email', etc.)
                    for field_key in field_values.keys():
                        if field_key in payload:
                            field_values[field_key] = payload[field_key]

            for dup_item in review_items.values():
                if dup_item.item_type != 'duplicate' or dup_item.batch_id != import_id:
                    continue
                dup_decision = duplicate_decisions.get(dup_item.id)
                if dup_decision and dup_decision.decision == 'same_person':
                    payload = dup_decision.reviewed_values or {}
                    # Apply any field corrections stored in reviewed_values (e.g., 'email', 'first_name', etc.)
                    for field_key in field_values.keys():
                        if field_key in payload:
                            field_values[field_key] = payload[field_key]

            # Collect validation decision affecting this contact
            validation_status = 'pending'
            validation_issues = []
            row_blocker_count_before = len(row_blockers)

            for val_item in review_items.values():
                if val_item.item_type != 'validation' or val_item.batch_id != import_id:
                    continue

                val_decision = validation_decisions.get(val_item.id)
                payload = val_item.payload_json or {}
                if isinstance(payload, str):
                    payload = json.loads(payload)
                issue_type = _get_validation_issue_type(payload)

                if val_decision:
                    if val_decision.decision == 'accept_issue':
                        validation_status = 'accepted'
                    elif val_decision.decision == 'dismiss_issue':
                        validation_status = 'dismissed'
                    elif val_decision.decision == 'defer':
                        validation_status = 'deferred'
                        row_warnings.append(f"Validation issue unresolved: {issue_type}")
                else:
                    # No decision - check severity
                    critical_issues = [
                        'missing_email', 'invalid_email', 'invalid_email_format',
                        'missing_transaction_id', 'invalid_amount',
                        'invalid_amount_zero_or_negative'
                    ]
                    if any(critical in issue_type.lower() for critical in critical_issues):
                        row_blocker_count_before = len(row_blockers)
                        row_blockers.append(f"Unresolved validation: {issue_type}")
                        validation_status = 'blocked'
                    else:
                        row_warnings.append(f"Validation issue unresolved: {issue_type}")

            # Collect duplicate decision affecting this contact
            duplicate_group_id = None
            duplicate_decision = None
            duplicate_warnings = []

            for dup_item in review_items.values():
                if dup_item.item_type != 'duplicate' or dup_item.batch_id != import_id:
                    continue

                dup_decision = duplicate_decisions.get(dup_item.id)
                if dup_decision:
                    if dup_decision.decision == 'same_person':
                        # Create derived group ID from contact IDs in the duplicate pair
                        payload = dup_decision.reviewed_values or {}
                        contact_ids = payload.get('candidate_contact_ids', [])
                        if contact_ids:
                            sorted_ids = tuple(sorted([str(c) for c in contact_ids]))
                            id_hash = hashlib.md5(str(sorted_ids).encode()).hexdigest()[:8]
                            duplicate_group_id = f"DUP-GROUP-{id_hash}"
                        duplicate_decision = 'same_person'
                    elif dup_decision.decision == 'different_people':
                        duplicate_decision = 'different_people'
                    elif dup_decision.decision == 'defer':
                        duplicate_decision = 'deferred'
                        duplicate_warnings.append("Duplicate pair unresolved")
                else:
                    # No decision - warn
                    duplicate_warnings.append("Duplicate pair unresolved")

            # Collect household decision affecting this contact
            household_group_id = None
            household_group_label = None
            household_members = ()
            household_decision_status = None
            household_warnings = []

            for hh_item in review_items.values():
                if hh_item.item_type != 'household' or hh_item.batch_id != import_id:
                    continue

                hh_decision = household_decisions.get(hh_item.id)
                if hh_decision:
                    if hh_decision.decision == 'confirm_household':
                        payload = hh_decision.reviewed_values or {}
                        household_group_id = payload.get('candidate_household_id', f'HH-{hh_item.id}')
                        household_group_label = payload.get('suggested_household_label')
                        household_members = tuple(payload.get('candidate_contact_ids', []))
                        household_decision_status = 'confirmed'
                    elif hh_decision.decision == 'reject_household':
                        household_decision_status = 'rejected'
                    elif hh_decision.decision == 'defer':
                        household_decision_status = 'deferred'
                        household_warnings.append("Household grouping unresolved")
                else:
                    # No decision - warn
                    household_warnings.append("Household grouping unresolved")

            # Compile export warnings
            export_warnings = list(row_warnings) + normalization_warnings + \
                            duplicate_warnings + household_warnings

            # Create export row
            export_row = ExportRow(
                source_row_index=row_index,
                transaction_id=transaction_id,
                first_name=field_values.get('first_name'),
                last_name=field_values.get('last_name'),
                email=field_values.get('email'),
                phone=field_values.get('phone'),
                address_line1=field_values.get('address_line1'),
                address_line2=field_values.get('address_line2'),
                city=field_values.get('city'),
                state=field_values.get('state'),
                postal_code=field_values.get('postal_code'),
                amount=field_values.get('amount'),
                validation_status=validation_status,
                validation_issues=tuple(validation_issues),
                normalized_fields=tuple(normalized_fields),
                normalization_warnings=tuple(normalization_warnings),
                duplicate_group_id=duplicate_group_id,
                duplicate_decision=duplicate_decision,
                duplicate_warnings=tuple(duplicate_warnings),
                household_group_id=household_group_id,
                household_group_label=household_group_label,
                household_members=household_members,
                household_decision=household_decision_status,
                household_warnings=tuple(household_warnings),
                export_warnings=tuple(export_warnings),
                export_blocked=len(row_blockers) > 0,
                export_derived_at=datetime.utcnow(),
            )

            rows.append(export_row)

            # Accumulate blockers
            if len(row_blockers) > 0:
                blockers.extend(row_blockers)

            # Accumulate warnings (sample, not all)
            if len(row_warnings) > 0:
                warnings.extend(row_warnings[:2])  # Keep sample

        # Build result
        blocked_count = sum(1 for r in rows if r.export_blocked)
        warning_count = len(warnings)
        is_export_ready = blocked_count == 0

        result = ExportPreviewResult(
            import_id=import_id,
            export_rows=tuple(rows),
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            row_count=len(rows),
            blocked_count=blocked_count,
            warning_count=warning_count,
            is_export_ready=is_export_ready,
            derived_at=datetime.utcnow(),
            deferred_household_count=deferred_household_count,
            deferred_duplicate_count=deferred_duplicate_count,
            deferred_validation_count=deferred_validation_count,
        )

        return result

    finally:
        session.close()
