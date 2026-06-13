#!/usr/bin/env python3
"""
Householder v1.1 Demo Batch Seeder

Seeds a synthetic demo batch into an isolated demo SQLite database.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add scripts directory to path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))
sys.path.insert(0, str(script_dir / "householder"))

# Import SQLAlchemy directly
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Define Base for models
Base = declarative_base()


class ImportBatch(Base):
    """Import batch metadata."""
    __tablename__ = "import_batches"
    batch_id = Column(String, primary_key=True)
    batch_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    record_count = Column(Integer, nullable=False)
    import_date = Column(DateTime, nullable=False)
    raw_import_rows = relationship("RawImportRow", back_populates="batch")


class RawImportRow(Base):
    """Raw import data (immutable)."""
    __tablename__ = "raw_import_rows"
    id = Column(Integer, primary_key=True)
    batch_id = Column(String, ForeignKey("import_batches.batch_id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone = Column(String)
    amount = Column(Float)
    date = Column(String)
    transaction_id = Column(String)
    batch = relationship("ImportBatch", back_populates="raw_import_rows")


class ImportContact(Base):
    """Contact snapshot from import."""
    __tablename__ = "import_contacts"
    id = Column(Integer, primary_key=True)
    batch_id = Column(String, ForeignKey("import_batches.batch_id"), nullable=False)
    row_index = Column(Integer, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone = Column(String)


class ReviewItem(Base):
    """Review item (suggestion)."""
    __tablename__ = "review_items"
    id = Column(Integer, primary_key=True)
    batch_id = Column(String, ForeignKey("import_batches.batch_id"), nullable=False)
    issue_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    description = Column(Text)
    row_indices = Column(JSON)
    subjects = relationship("ReviewItemSubject", back_populates="review_item")


class ReviewItemSubject(Base):
    """Subject reference for review item."""
    __tablename__ = "review_item_subjects"
    id = Column(Integer, primary_key=True)
    review_item_id = Column(Integer, ForeignKey("review_items.id"), nullable=False)
    batch_id = Column(String, ForeignKey("import_batches.batch_id"), nullable=False)
    row_index = Column(Integer)
    contact_id = Column(Integer)
    review_item = relationship("ReviewItem", back_populates="subjects")


# Synthetic demo data
DEMO_RECORDS = [
    {"first_name": "John", "last_name": "Doe", "email": "john.doe@gmail.com", "phone": "555-0001", "amount": 100.00, "date": "2024-01-01", "transaction_id": "TX001"},
    {"first_name": "Jane", "last_name": "Smith", "email": "jane.smith@gmial.com", "phone": "555-0002", "amount": 250.00, "date": "2024-01-02", "transaction_id": "TX002"},
    {"first_name": "Robert", "last_name": "Smith", "email": "bob.smith@example.com", "phone": "555-0003", "amount": 150.00, "date": "2024-01-03", "transaction_id": "TX003"},
    {"first_name": "Bob", "last_name": "Smith", "email": "bob.smith@example.com", "phone": "555-0003", "amount": 300.00, "date": "2024-01-04", "transaction_id": "TX004"},
    {"first_name": "Carol", "last_name": "White", "email": "carol.white@example.com", "phone": "", "amount": 500.00, "date": "2024-01-05", "transaction_id": "TX005"},
    {"first_name": "David", "last_name": "Brown", "email": "david.brown@yahoo.com", "phone": "555-0007", "amount": 75.00, "date": "2024-01-06", "transaction_id": "TX006"},
    {"first_name": "Eve", "last_name": "Davis", "email": "eve@example.com", "phone": "555-0008", "amount": 200.00, "date": "2024-01-07", "transaction_id": "TX007"},
    {"first_name": "Frank", "last_name": "Davis", "email": "frank@example.com", "phone": "555-0009", "amount": 125.00, "date": "2024-01-08", "transaction_id": "TX008"},
    {"first_name": "Grace", "last_name": "Miller", "email": "grace.miller@example.com", "phone": "(555) 004-1234", "amount": 80.00, "date": "2024-01-09", "transaction_id": "TX009"},
    {"first_name": "Henry", "last_name": "Wilson", "email": "henry@example.com", "phone": "555-0011", "amount": 180.00, "date": "2024-01-10", "transaction_id": "TX010"},
    {"first_name": "Iris", "last_name": "Moore", "email": "iris.moore@example.com", "phone": "555-0012", "amount": 220.00, "date": "2024-01-11", "transaction_id": "TX011"},
    {"first_name": "Jack", "last_name": "Green", "email": "jack.green@example.com", "phone": "555-0013", "amount": 95.00, "date": "2024-01-12", "transaction_id": "TX012"},
]


def verify_demo_environment():
    """Verify demo environment."""
    db_url = os.getenv("GIVEBUTTER_DATABASE_URL", "")
    export_dir = os.getenv("EXPORT_OUTPUT_DIR", "")

    if "demo" not in db_url.lower():
        print("ERROR: GIVEBUTTER_DATABASE_URL should contain 'demo'")
        sys.exit(1)

    if "demo" not in export_dir.lower():
        print("ERROR: EXPORT_OUTPUT_DIR should contain 'demo'")
        sys.exit(1)

    print("✓ Demo environment verified")
    print(f"  Database: {db_url}")
    print(f"  Export dir: {export_dir}")


def seed_demo_batch():
    """Seed the demo batch."""
    db_url = os.getenv("GIVEBUTTER_DATABASE_URL", "sqlite:///./householder_demo.db")
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        batch_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        batch = ImportBatch(
            batch_id=batch_id,
            batch_name="DEMO",
            status="ready_for_review",
            record_count=len(DEMO_RECORDS),
            import_date=datetime.now(),
        )
        session.add(batch)
        session.commit()

        # Add raw rows
        for idx, record in enumerate(DEMO_RECORDS):
            session.add(RawImportRow(
                batch_id=batch_id,
                row_index=idx,
                first_name=record["first_name"],
                last_name=record["last_name"],
                email=record["email"],
                phone=record["phone"],
                amount=record["amount"],
                date=record["date"],
                transaction_id=record["transaction_id"],
            ))
        session.commit()

        # Add contacts
        for idx, record in enumerate(DEMO_RECORDS):
            session.add(ImportContact(
                batch_id=batch_id,
                row_index=idx,
                first_name=record["first_name"],
                last_name=record["last_name"],
                email=record["email"],
                phone=record["phone"],
            ))
        session.commit()

        # Add review items
        review_count = 0

        # Email typo
        item = ReviewItem(batch_id=batch_id, issue_type="validation", severity="warning",
                         description="Email may have typo: gmial.com", row_indices=[1])
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(review_item_id=item.id, batch_id=batch_id, row_index=1))
        review_count += 1

        # Missing phone (BLOCKER)
        item = ReviewItem(batch_id=batch_id, issue_type="validation", severity="error",
                         description="Required field missing: phone number", row_indices=[4])
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(review_item_id=item.id, batch_id=batch_id, row_index=4))
        review_count += 1

        # Duplicates
        item = ReviewItem(batch_id=batch_id, issue_type="duplicate", severity="info",
                         description="Potential duplicate: same email and phone", row_indices=[2, 3])
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(review_item_id=item.id, batch_id=batch_id, row_index=2))
        session.add(ReviewItemSubject(review_item_id=item.id, batch_id=batch_id, row_index=3))
        review_count += 1

        # Household
        item = ReviewItem(batch_id=batch_id, issue_type="household", severity="info",
                         description="Potential household match: same phone", row_indices=[6, 7])
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(review_item_id=item.id, batch_id=batch_id, row_index=6))
        session.add(ReviewItemSubject(review_item_id=item.id, batch_id=batch_id, row_index=7))
        review_count += 1

        # Normalization
        item = ReviewItem(batch_id=batch_id, issue_type="normalization", severity="info",
                         description="Phone formatting: (555) 004-1234 → 555-0041234", row_indices=[8])
        session.add(item)
        session.flush()
        session.add(ReviewItemSubject(review_item_id=item.id, batch_id=batch_id, row_index=8))
        review_count += 1

        session.commit()
        return batch_id, review_count

    finally:
        session.close()


def main():
    """Main function."""
    print("\n" + "=" * 70)
    print("Householder v1.1 — Demo Batch Seeder")
    print("=" * 70)

    print("\nVerifying demo environment...")
    verify_demo_environment()

    export_dir = os.getenv("EXPORT_OUTPUT_DIR")
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    print(f"✓ Export directory ready")

    print("\nSeeding demo batch...")
    batch_id, review_count = seed_demo_batch()

    print("\n" + "=" * 70)
    print("✓ Demo batch created!")
    print("=" * 70)
    print(f"\nBatch ID: {batch_id}")
    print(f"Records: {len(DEMO_RECORDS)}")
    print(f"Review items: {review_count}")
    print(f"\nExport readiness: BLOCKED (Carol White missing phone)")
    print(f"\n✓ Ready for: http://localhost:8000/dashboard")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
