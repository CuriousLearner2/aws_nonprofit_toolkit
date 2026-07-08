#!/usr/bin/env python3
"""
Create a local DB-backed UAT seed for Review Records / Validation Review.

This tool seeds the fixture batch IMP-2025-0101-A into a dedicated SQLite
database so browser-refresh manual UAT can run in database mode instead of the
fixture fallback.

Safety:
- Refuses to overwrite an existing DB unless --reset is supplied.
- Uses current schema models only; no migrations or product logic changes.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import sessionmaker


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "uat_review.db"
DEFAULT_EXPORT_DIR = REPO_ROOT / "exports_uat"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.householder.database_models import (  # noqa: E402
    AuditLogRecord,
    Base,
    ImportBatch,
    ImportContact,
    RawImportRow,
    ReviewItem,
    ReviewItemSubject,
    create_db_engine,
)
from scripts.uploader.fixtures import CONTACTS, IMPORT_BATCH  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed a DB-backed local UAT database for IMP-2025-0101-A."
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete any existing DB at --db-path before seeding.",
    )
    return parser.parse_args()


def split_name(name: str) -> tuple[str, str]:
    parts = [part for part in (name or "").strip().split() if part]
    if not parts:
        return "Unknown", "Donor"
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def parse_amount(amount: str) -> float:
    return float(amount.replace("$", "").replace(",", "").strip())


def build_rows() -> list[dict]:
    """Build 50 rows: the visible fixture rows plus safe synthetic filler."""
    rows: list[dict] = []

    for contact in CONTACTS:
        issue = None
        if contact["id"] == "TXN-003":
            issue = {
                "field": "address",
                "reason": "missing",
                "severity": "warning",
                "description": "Missing address",
            }
        elif contact["id"] == "TXN-005":
            issue = {
                "field": "phone",
                "reason": "missing",
                "severity": "error",
                "description": "Phone number missing",
            }

        rows.append(
            {
                "name": contact["name"],
                "date": contact["date"],
                "email": contact["email"],
                "phone": contact["phone"],
                "amount": contact["amount"],
                "address": contact["address"],
                "issue": issue,
            }
        )

    for index in range(6, 51):
        rows.append(
            {
                "name": f"Donor {index:02d}",
                "date": f"2026-05-{index:02d}" if index <= 31 else "2026-06-01",
                "email": f"donor{index:02d}@example.com",
                "phone": f"(415) 200-{index:04d}",
                "amount": f"{100 + index:.2f}",
                "address": f"{100 + index} Example Way, Springfield, IL 62701",
                "issue": None,
            }
        )

    return rows


def seed_uat_database(db_path: Path) -> tuple[str, int, int]:
    database_url = f"sqlite:///{db_path}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    batch_id = IMPORT_BATCH["id"]
    rows = build_rows()

    try:
        batch = ImportBatch(
            id=batch_id,
            filename=IMPORT_BATCH["filename"],
            upload_timestamp=datetime.now(timezone.utc),
            uploader="uat_setup",
            status="pending_review",
            raw_row_count=len(rows),
        )
        session.add(batch)
        session.flush()

        seeded_review_items = 0

        for row_index, row in enumerate(rows, start=1):
            raw_row = RawImportRow(
                batch_id=batch_id,
                row_index=row_index,
                raw_csv_data={
                    "name": row["name"],
                    "date": row["date"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "amount": row["amount"],
                    "address": row["address"],
                    "transaction_id": f"TXN-{row_index:03d}",
                },
            )
            session.add(raw_row)
            session.flush()

            first_name, last_name = split_name(row["name"])
            session.add(
                ImportContact(
                    batch_id=batch_id,
                    raw_import_row_id=raw_row.id,
                    first_name=first_name,
                    last_name=last_name,
                    email=row["email"],
                    phone=row["phone"] or None,
                    address_line1=row["address"] or None,
                    amount=parse_amount(row["amount"]),
                )
            )
            session.flush()

            issue = row["issue"]
            if issue:
                review_item = ReviewItem(
                    batch_id=batch_id,
                    item_type="validation",
                    status="pending",
                    confidence=1.0,
                    payload_json={
                        "field": issue["field"],
                        "reason": issue["reason"],
                        "severity": issue["severity"],
                        "description": issue["description"],
                    },
                )
                session.add(review_item)
                session.flush()
                session.add(
                    ReviewItemSubject(
                        review_item_id=review_item.id,
                        subject_type="import_raw_row",
                        subject_id=raw_row.id,
                        role="primary",
                    )
                )
                seeded_review_items += 1

        session.add(
            AuditLogRecord(
                batch_id=batch_id,
                action_type="batch_imported",
                action_timestamp=datetime.now(timezone.utc),
                actor="uat_setup",
                details={
                    "filename": IMPORT_BATCH["filename"],
                    "records": len(rows),
                    "seed_source": "scripts/uploader/fixtures.py",
                },
            )
        )
        session.commit()
        return database_url, len(rows), seeded_review_items
    finally:
        session.close()


def main() -> int:
    args = parse_args()
    db_path = Path(args.db_path).expanduser().resolve()

    if db_path.exists():
        if not args.reset:
            print(f"ERROR: {db_path} already exists.")
            print("Refusing to overwrite. Re-run with --reset to replace it.")
            return 1
        db_path.unlink()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    export_dir = DEFAULT_EXPORT_DIR
    export_dir.mkdir(parents=True, exist_ok=True)

    database_url, row_count, review_item_count = seed_uat_database(db_path)

    print("=" * 72)
    print("Local UAT Review DB created")
    print("=" * 72)
    print(f"Database path: {db_path}")
    print(f"Database URL:  {database_url}")
    print(f"Seeded batch:  {IMPORT_BATCH['id']}")
    print(f"Rows seeded:   {row_count}")
    print(f"Review items:  {review_item_count}")
    print()
    print("Launch in DB mode:")
    print("  export HOUSEHOLDER_REPOSITORY=database")
    print(f'  export GIVEBUTTER_DATABASE_URL="{database_url}"')
    print("  ./.venv/bin/python scripts/uploader/app.py")
    print()
    print("Sanity checks:")
    print(
        f'  sqlite3 "{db_path}" "SELECT id, filename, raw_row_count FROM import_batches WHERE id=\'{IMPORT_BATCH["id"]}\';"'
    )
    print(
        f'  sqlite3 "{db_path}" "SELECT COUNT(*) FROM raw_import_rows WHERE batch_id=\'{IMPORT_BATCH["id"]}\';"'
    )
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
