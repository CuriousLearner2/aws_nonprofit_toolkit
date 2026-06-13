#!/usr/bin/env python3
"""
Householder v1.1 Demo Batch Reset

Removes demo data from isolated demo database and export directory.
"""

import os
import sys
from pathlib import Path

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


def verify_demo_environment():
    """Verify that we're using demo database and export directory."""
    db_url = os.getenv("GIVEBUTTER_DATABASE_URL", "")
    export_dir = os.getenv("EXPORT_OUTPUT_DIR", "")

    if "demo" not in db_url.lower():
        print("ERROR: Not using demo database!")
        print(f"GIVEBUTTER_DATABASE_URL should contain 'demo': {db_url}")
        sys.exit(1)

    if "demo" not in export_dir.lower():
        print("ERROR: Not using demo export directory!")
        print(f"EXPORT_OUTPUT_DIR should contain 'demo': {export_dir}")
        sys.exit(1)

    print("✓ Demo environment verified")
    print(f"  Database: {db_url}")
    print(f"  Export dir: {export_dir}")


def reset_demo_database():
    """Delete all demo batches from demo database."""
    db_url = os.getenv("GIVEBUTTER_DATABASE_URL", "sqlite:///./householder_demo.db")

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find all demo batches
        demo_batches = session.query(ImportBatch).filter(
            ImportBatch.batch_name == "DEMO"
        ).all()

        if not demo_batches:
            print("  No demo batches found in database")
            return 0, 0

        total_records = 0
        total_items = 0

        for batch in demo_batches:
            batch_id = batch.batch_id

            # Count records before deletion
            raw_count = session.query(RawImportRow).filter_by(batch_id=batch_id).count()
            review_count = session.query(ReviewItem).filter_by(batch_id=batch_id).count()

            # Delete in order of dependencies
            session.query(ReviewItemSubject).filter_by(batch_id=batch_id).delete()
            session.query(ReviewItem).filter_by(batch_id=batch_id).delete()
            session.query(ImportContact).filter_by(batch_id=batch_id).delete()
            session.query(RawImportRow).filter_by(batch_id=batch_id).delete()
            session.query(ImportBatch).filter_by(batch_id=batch_id).delete()
            session.commit()

            total_records += raw_count
            total_items += review_count

            print(f"  Deleted batch {batch_id}: {raw_count} records, {review_count} review items")

        return total_records, total_items

    finally:
        session.close()


def reset_demo_exports():
    """Delete all demo export files."""
    export_dir = os.getenv("EXPORT_OUTPUT_DIR", "")

    if not export_dir or not Path(export_dir).exists():
        print("  No export directory found")
        return 0

    csv_files = list(Path(export_dir).glob("*.csv"))
    for csv_file in csv_files:
        csv_file.unlink()
        print(f"  Deleted export file: {csv_file.name}")

    return len(csv_files)


def main():
    """Main reset function."""
    print("\n" + "=" * 70)
    print("Householder v1.1 — Demo Batch Reset")
    print("=" * 70)

    # Verify environment
    print("\nVerifying demo environment...")
    verify_demo_environment()

    # Reset database
    print("\nResetting demo database...")
    record_count, item_count = reset_demo_database()

    # Reset exports
    print("\nResetting demo exports...")
    export_count = reset_demo_exports()

    print("\n" + "=" * 70)
    print("✓ Demo cleanup complete!")
    print("=" * 70)
    print(f"\nDeleted from demo database:")
    print(f"  - {record_count} import records")
    print(f"  - {item_count} review items")
    print(f"\nDeleted from demo exports:")
    print(f"  - {export_count} export files")
    print(f"\nDemo is clean. Ready for next seeding.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
