"""Seed test database with representative Option C data.

Provides minimal but complete data covering all 8 canonical routes.
Uses actual database models for type safety and schema alignment.
"""

from datetime import datetime
from scripts.householder.database_models import (
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    ReviewDecision,
    AuditLogRecord,
)


def seed_test_data(session):
    """Seed database with test data for all 8 routes.

    Args:
        session: SQLAlchemy session
    """
    # 1. Import batch
    batch = ImportBatch(
        id='IMP-TEST-001',
        filename='donors_q1_2025.csv',
        upload_timestamp=datetime(2026, 6, 1, 9, 0, 0),
        uploader='test_uploader',
        status='pending',
        raw_row_count=5,
    )
    session.add(batch)
    session.flush()  # Ensure batch is inserted before raw rows reference it

    # 2. Raw import rows (5 records)
    raw_rows_data = [
        {'row_index': 0, 'name': 'John Smith', 'email': 'john@example.com', 'phone': '(555) 123-4567', 'address': '123 Main St'},
        {'row_index': 1, 'name': 'Jon Smith', 'email': 'jon.smith@email.com', 'phone': '(555) 123-4567', 'address': '123 Main St'},
        {'row_index': 2, 'name': 'Jane Doe', 'email': 'jane@example.com', 'phone': '(555) 987-6543', 'address': '456 Oak Ave'},
        {'row_index': 3, 'name': 'John Smith Jr.', 'email': 'johnny@example.com', 'phone': '(555) 111-2222', 'address': '123 Main St'},
        {'row_index': 4, 'name': 'Mary Johnson', 'email': 'mary@example.com', 'phone': '(555) 555-5555', 'address': '789 Elm Dr'},
    ]

    raw_import_rows = []
    for row_data in raw_rows_data:
        raw_row = RawImportRow(
            batch_id=batch.id,
            row_index=row_data['row_index'],
            raw_csv_data=row_data,
        )
        session.add(raw_row)
        raw_import_rows.append(raw_row)

    session.flush()  # Ensure raw rows are inserted before contacts reference them

    # 3. Import contacts (5 records)
    import_contacts = []
    contact_data = [
        {'first_name': 'John', 'last_name': 'Smith', 'email': 'john@example.com', 'phone': '(555) 123-4567', 'address_line1': '123 Main St'},
        {'first_name': 'Jon', 'last_name': 'Smith', 'email': 'jon.smith@email.com', 'phone': '(555) 123-4567', 'address_line1': '123 Main St'},
        {'first_name': 'Jane', 'last_name': 'Doe', 'email': 'jane@example.com', 'phone': '(555) 987-6543', 'address_line1': '456 Oak Ave'},
        {'first_name': 'John', 'last_name': 'Smith Jr.', 'email': 'johnny@example.com', 'phone': '(555) 111-2222', 'address_line1': '123 Main St'},
        {'first_name': 'Mary', 'last_name': 'Johnson', 'email': 'mary@example.com', 'phone': '(555) 555-5555', 'address_line1': '789 Elm Dr'},
    ]

    for idx, contact_dict in enumerate(contact_data):
        import_contact = ImportContact(
            batch_id=batch.id,
            raw_import_row_id=raw_import_rows[idx].id,
            first_name=contact_dict['first_name'],
            last_name=contact_dict['last_name'],
            email=contact_dict['email'],
            phone=contact_dict['phone'],
            address_line1=contact_dict['address_line1'],
        )
        session.add(import_contact)
        import_contacts.append(import_contact)

    session.flush()  # Ensure contacts are inserted before review items reference them

    # 4. Review items (4 items: validation, normalization, duplicate, household)
    review_items_data = [
        {'item_type': 'validation', 'payload': {'field': 'address', 'issue': 'Missing address on contact'}},
        {'item_type': 'normalization', 'payload': {'field': 'email', 'issue': 'Email needs standardization'}},
        {'item_type': 'duplicate', 'payload': {'match_type': 'potential', 'evidence': ['same_address', 'similar_name']}},
        {'item_type': 'household', 'payload': {'suggested_label': 'Smith family', 'basis': 'same_address'}},
    ]

    review_items = []
    for item_data in review_items_data:
        review_item = ReviewItem(
            batch_id=batch.id,
            item_type=item_data['item_type'],
            status='pending',
            confidence=0.85,
            payload_json=item_data['payload'],
        )
        session.add(review_item)
        review_items.append(review_item)

    session.flush()  # Ensure review items are inserted before subjects reference them

    # 5. Review item subjects (map items to contacts)
    subject_mappings = [
        (0, 0, 'import_contact_snapshot'),  # VAL-001 -> contact 0 (John Smith)
        (0, 2, 'import_contact_snapshot'),  # VAL-001 -> contact 2 (Jane Doe)
        (1, 1, 'import_contact_snapshot'),  # NORM-001 -> contact 1 (Jon Smith)
        (2, 0, 'import_contact_snapshot'),  # DUP-001 -> contact 0 (John Smith)
        (2, 1, 'import_contact_snapshot'),  # DUP-001 -> contact 1 (Jon Smith)
        (3, 0, 'import_contact_snapshot'),  # HH-001 -> contact 0 (John Smith)
        (3, 3, 'import_contact_snapshot'),  # HH-001 -> contact 3 (John Smith Jr.)
    ]

    for item_idx, contact_idx, subject_type in subject_mappings:
        subject = ReviewItemSubject(
            review_item_id=review_items[item_idx].id,
            subject_type=subject_type,
            subject_id=import_contacts[contact_idx].id,
            role='primary' if item_idx != 2 else ('primary' if contact_idx == 0 else 'secondary'),
        )
        session.add(subject)

    session.flush()  # Ensure subjects are inserted before decisions reference items

    # 6. Review decisions (2 decisions for audit trail)
    decisions = [
        ReviewDecision(
            batch_id=batch.id,
            review_item_id=review_items[2].id,  # DUP-001
            decision='same_person',
            reviewer='Sarah Lee',
        ),
        ReviewDecision(
            batch_id=batch.id,
            review_item_id=review_items[3].id,  # HH-001
            decision='confirmed',
            reviewer='James Martinez',
        ),
    ]

    for decision in decisions:
        session.add(decision)

    session.flush()  # Ensure decisions are inserted before audit entries reference them

    # 7. Audit log entries (3 entries)
    audit_entries = [
        AuditLogRecord(
            batch_id=batch.id,
            action_type='decision_recorded',
            action_timestamp=datetime(2026, 6, 11, 10, 30, 0),
            actor='Sarah Lee',
            item_id=review_items[2].id,
            decision_id=decisions[0].id,
            details={'decision': 'marked as Same Person', 'evidence': 'Email variation consistent with household pattern'},
        ),
        AuditLogRecord(
            batch_id=batch.id,
            action_type='decision_recorded',
            action_timestamp=datetime(2026, 6, 11, 10, 15, 0),
            actor='James Martinez',
            item_id=review_items[3].id,
            decision_id=decisions[1].id,
            details={'decision': 'confirmed Household #HH-001', 'evidence': 'Smith family confirmed via manual lookup'},
        ),
        AuditLogRecord(
            batch_id=batch.id,
            action_type='item_created',
            action_timestamp=datetime(2026, 6, 11, 10, 0, 0),
            actor='Bob Wilson',
            item_id=review_items[0].id,
            details={'action': 'flagged missing address', 'evidence': 'Contact record missing address field'},
        ),
    ]

    for audit_entry in audit_entries:
        session.add(audit_entry)

    session.commit()
