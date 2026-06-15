#!/usr/bin/env python3
"""
Migrate Demo Database - Create correct schema and seed demo data.

Creates householder_demo.db with the production schema and seeds it with demo data.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import uuid

# Add scripts directory to path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / "householder"))

# Import database models and session management
from householder.database_models import Base, ImportBatch, RawImportRow, ImportContact, ReviewItem, ReviewItemSubject
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def verify_demo_environment():
    """Verify demo environment variables are set."""
    db_url = os.getenv('GIVEBUTTER_DATABASE_URL')
    export_dir = os.getenv('EXPORT_OUTPUT_DIR')

    if not db_url or 'demo' not in db_url or 'householder_demo.db' not in db_url:
        raise ValueError(
            "GIVEBUTTER_DATABASE_URL must be set and contain 'householder_demo.db'\n"
            "Example: sqlite:////path/to/householder_demo.db"
        )

    if not export_dir or 'demo' not in export_dir or 'exports_demo' not in export_dir:
        raise ValueError(
            "EXPORT_OUTPUT_DIR must be set and contain 'exports_demo'\n"
            "Example: /path/to/exports_demo"
        )

    return db_url, export_dir


def create_tables(engine):
    """Create all tables using database_models."""
    Base.metadata.create_all(engine)
    print("✓ Tables created")


def seed_demo_batch(session):
    """Seed demo batch with 12 records and 5 review items."""

    # Create batch
    batch_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    batch = ImportBatch(
        id=batch_id,
        filename="demo_donors_2025.csv",
        upload_timestamp=datetime.now(),
        uploader="demo_setup",
        status="pending_review",
        raw_row_count=12
    )
    session.add(batch)
    session.flush()

    # Demo donor data
    donors = [
        ("Jane", "Smith", "jane.smith@gmial.com", "555-0001", "100.00", "2025-01-01"),  # typo in email
        ("Carol", "White", "carol.white@example.com", None, "250.00", "2025-01-02"),  # missing phone
        ("Robert", "Smith", "bob.smith@example.com", "555-0003", "150.00", "2025-01-03"),
        ("Bob", "Smith", "bob.smith@example.com", "555-0003", "200.00", "2025-01-04"),  # duplicate
        ("Eve", "Davis", "eve.davis@example.com", "555-0009", "75.00", "2025-01-05"),
        ("Frank", "Davis", "frank.davis@example.com", "555-0009", "125.00", "2025-01-06"),  # household
        ("Grace", "Miller", "grace.miller@example.com", "(555) 004-1234", "300.00", "2025-01-07"),  # needs normalization
        ("Henry", "Brown", "henry.brown@example.com", "555-0008", "50.00", "2025-01-08"),
        ("Iris", "Jones", "iris.jones@example.com", "555-0010", "180.00", "2025-01-09"),
        ("Jack", "Garcia", "jack.garcia@example.com", "555-0011", "220.00", "2025-01-10"),
        ("Karen", "Martinez", "karen.martinez@example.com", "555-0012", "95.00", "2025-01-11"),
        ("Leo", "Rodriguez", "leo.rodriguez@example.com", "555-0013", "140.00", "2025-01-12"),
    ]

    # Add raw import rows
    for idx, (first, last, email, phone, amount, date) in enumerate(donors, 1):
        row = RawImportRow(
            batch_id=batch_id,
            row_index=idx,
            raw_csv_data={
                "first_name": first,
                "last_name": last,
                "email": email,
                "phone": phone,
                "amount": amount,
                "date": date,
                "transaction_id": f"TXN-{idx:04d}"
            }
        )
        session.add(row)

    session.flush()

    # Collect raw_import_row IDs for review item linking
    raw_rows = session.query(RawImportRow).filter_by(batch_id=batch_id).order_by(RawImportRow.id).all()
    raw_row_ids = [row.id for row in raw_rows[:len(donors)]]

    # Add import contacts (denormalized snapshot)
    for idx, (first, last, email, phone, amount, date) in enumerate(donors, 1):
        contact = ImportContact(
            batch_id=batch_id,
            raw_import_row_id=raw_row_ids[idx - 1],
            first_name=first,
            last_name=last,
            email=email,
            phone=phone,
            address_line1=None,
            amount=float(amount)
        )
        session.add(contact)

    session.flush()

    # Create review items (5 items as per spec)
    review_items = []

    # 1. Jane Smith - validation issue (email typo)
    item1 = ReviewItem(
        batch_id=batch_id,
        item_type="validation",
        status="pending",
        confidence=0.95,
        payload_json={
            "field": "email",
            "reason": "possible_typo",
            "severity": "warning",
            "description": "Invalid email format (gmial.com typo)"
        }
    )
    session.add(item1)
    session.flush()
    review_items.append(item1)

    # 2. Carol White - validation issue (missing phone)
    item2 = ReviewItem(
        batch_id=batch_id,
        item_type="validation",
        status="pending",
        confidence=0.98,
        payload_json={
            "field": "phone",
            "reason": "missing",
            "severity": "error",
            "description": "Required field missing (phone)"
        }
    )
    session.add(item2)
    session.flush()
    review_items.append(item2)

    # 3. Robert/Bob Smith - duplicate
    item3 = ReviewItem(
        batch_id=batch_id,
        item_type="duplicate",
        status="pending",
        confidence=0.92,
        payload_json={
            "match_type": "potential_duplicate",
            "evidence": ["same_email: bob.smith@example.com", "same_phone: 555-0003"],
            "conflicts": []
        }
    )
    session.add(item3)
    session.flush()
    review_items.append(item3)

    # 4. Eve/Frank Davis - household
    item4 = ReviewItem(
        batch_id=batch_id,
        item_type="household",
        status="pending",
        confidence=0.88,
        payload_json={
            "suggested_name": "Davis Household",
            "basis": "Same phone number (555-0009)",
            "confidence": 0.88
        }
    )
    session.add(item4)
    session.flush()
    review_items.append(item4)

    # 5. Grace Miller - normalization
    item5 = ReviewItem(
        batch_id=batch_id,
        item_type="normalization",
        status="pending",
        confidence=0.99,
        payload_json={
            "field": "phone",
            "raw_value": "(555) 004-1234",
            "normalized_value": "555-0041234",
            "basis": "Standard phone normalization"
        }
    )
    session.add(item5)
    session.flush()
    review_items.append(item5)

    # Add review item subjects linking items to raw import rows
    subjects = [
        (item1.id, "import_raw_row", raw_row_ids[0], "primary"),  # Jane Smith (idx 0)
        (item2.id, "import_raw_row", raw_row_ids[1], "primary"),  # Carol White (idx 1)
        (item3.id, "import_raw_row", raw_row_ids[2], "primary"),  # Robert Smith (idx 2)
        (item3.id, "import_raw_row", raw_row_ids[3], "secondary"),  # Bob Smith (idx 3)
        (item4.id, "import_raw_row", raw_row_ids[4], "primary"),  # Eve Davis (idx 4)
        (item4.id, "import_raw_row", raw_row_ids[5], "secondary"),  # Frank Davis (idx 5)
        (item5.id, "import_raw_row", raw_row_ids[6], "primary"),  # Grace Miller (idx 6)
    ]

    for review_item_id, subject_type, subject_id, role in subjects:
        subject = ReviewItemSubject(
            review_item_id=review_item_id,
            subject_type=subject_type,
            subject_id=subject_id,
            role=role
        )
        session.add(subject)

    session.commit()

    return batch_id, len(donors), len(review_items)


def main():
    print("=" * 70)
    print("Householder Demo Database Migration")
    print("=" * 70)

    # Verify environment
    print("\nVerifying demo environment...")
    db_url, export_dir = verify_demo_environment()
    print(f"✓ Database URL: {db_url}")
    print(f"✓ Export dir: {export_dir}")

    # Create engine and tables
    print("\nCreating database and tables...")
    engine = create_engine(db_url, echo=False)
    create_tables(engine)

    # Seed data
    print("\nSeeding demo batch...")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        batch_id, record_count, review_count = seed_demo_batch(session)

        print("\n" + "=" * 70)
        print("✓ Demo batch created!")
        print("=" * 70)
        print(f"\nBatch ID: {batch_id}")
        print(f"Records: {record_count}")
        print(f"Review items: {review_count}")
        print(f"\nExport readiness: BLOCKED (Carol White missing phone)")
        print(f"\n✓ Ready for: http://localhost:8000/imports")
        print("=" * 70)

    finally:
        session.close()


if __name__ == "__main__":
    main()
