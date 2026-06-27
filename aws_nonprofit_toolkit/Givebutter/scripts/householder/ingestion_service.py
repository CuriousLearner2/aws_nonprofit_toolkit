"""
Ingestion Service for Phase 1C: Transform processed CSV into Option C database records.

Phase 1C-Step 4: Core ingestion service that ingests validated CSV data into the
Option C database schema. Handles batch creation, raw row preservation, contact
snapshots, validation item generation, and audit logging.

Design principles:
- Atomic transactions: all writes commit together or all rollback
- Immutable records: raw rows and contacts never modified after creation
- Pending items: all generated ReviewItems are pending (no decisions)
- No external APIs: no Givebutter writeback, no export generation
- Conservative normalization: only for PASS rows with suggestions
- Deferred features: no household generation, no cross-import duplicates
"""

import csv
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .database_models import (
    Base,
    ImportBatch,
    RawImportRow,
    ImportContact,
    ReviewItem,
    ReviewItemSubject,
    AuditLogRecord,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Exception Classes
# ============================================================================

class IngestionValidationError(Exception):
    """CSV structure or content validation failed."""
    pass


class IngestionIOError(Exception):
    """File I/O failure (file not found, unreadable, etc.)."""
    pass


class IngestionDatabaseError(Exception):
    """Database operation failed (connection, transaction, schema, etc.)."""
    pass


class BatchIDCollisionError(Exception):
    """Generated batch ID already exists (rare; indicates retry situation)."""
    pass


# ============================================================================
# Result Dataclass
# ============================================================================

@dataclass(frozen=True)
class IngestionResult:
    """Immutable result of successful ingestion."""

    # Primary identifiers
    batch_id: str
    filename: str

    # Counts
    raw_row_count: int
    contacts_created: int
    validation_items_created: int
    normalization_items_created: int
    duplicate_items_created: int
    household_items_created: int

    # Audit trail
    audit_log_id: int
    audit_action_type: str
    audit_timestamp: datetime

    # Status
    status: str
    uploader: Optional[str]

    # Validation summary (optional)
    pass_count: Optional[int] = None
    warning_count: Optional[int] = None
    fail_count: Optional[int] = None

    def __repr__(self) -> str:
        return (
            f"IngestionResult(batch_id={self.batch_id}, "
            f"rows={self.raw_row_count}, items={self.validation_items_created + self.normalization_items_created})"
        )


# ============================================================================
# Helper Functions
# ============================================================================

def generate_batch_id(csv_file_contents: bytes, imported_at: Optional[datetime] = None) -> str:
    """
    Generate unique batch ID with timestamp and content hash.

    Format: IMP-YYYYMMDD-HHMMSS-<HASH8>
    Example: IMP-20260612-121530-A7F2B3C1

    Args:
        csv_file_contents: Bytes of processed CSV file
        imported_at: Timestamp to use (defaults to current UTC time)

    Returns:
        Batch ID string
    """
    # Use provided timestamp or current time
    if imported_at is None:
        imported_at = datetime.utcnow()

    # Calculate file hash (first 8 chars of SHA256, uppercase)
    file_hash = hashlib.sha256(csv_file_contents).hexdigest()[:8].upper()

    # Format timestamp
    timestamp_str = imported_at.strftime("%Y%m%d%H%M%S")
    batch_id = f"IMP-{timestamp_str[:8]}-{timestamp_str[8:]}-{file_hash}"

    return batch_id


def split_name(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Split full name into first and last name.

    Algorithm:
    - Empty or whitespace: (None, None)
    - Single token: (token, None)
    - Two+ tokens: (first_token, remaining_joined_with_space)

    Examples:
    - "John Smith" → ("John", "Smith")
    - "John Michael Smith" → ("John", "Michael Smith")
    - "John Smith Jr." → ("John", "Smith Jr.")
    - "Prince" → ("Prince", None)
    - "" → (None, None)

    Args:
        name: Full name string

    Returns:
        Tuple of (first_name, last_name)
    """
    if not name:
        return (None, None)

    name = name.strip()
    if not name:
        return (None, None)

    parts = name.split()
    if len(parts) == 1:
        return (parts[0], None)

    first_name = parts[0]
    last_name = " ".join(parts[1:])
    return (first_name, last_name)


def extract_digits_from_phone(phone: str) -> str:
    """
    Extract digits only from phone number.

    Examples:
    - "(555) 123-4567" → "5551234567"
    - "555.123.4567" → "5551234567"
    - "" → ""

    Args:
        phone: Phone number string

    Returns:
        Digits only
    """
    if not phone:
        return ""

    phone = str(phone).strip()
    if not phone:
        return ""

    digits = "".join(c for c in phone if c.isdigit())
    return digits


def parse_amount(amount_str: str) -> Optional[float]:
    """
    Parse amount string to float.

    Handles currency symbols and commas.

    Examples:
    - "100.00" → 100.0
    - "$100.00" → 100.0
    - "1,000" → 1000.0
    - "invalid" → None
    - "" → None

    Args:
        amount_str: Amount string

    Returns:
        Float or None if unparseable
    """
    if not amount_str:
        return None

    amount_str = str(amount_str).strip()
    if not amount_str:
        return None

    try:
        # Remove currency symbols and commas
        cleaned = amount_str.replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except ValueError:
        return None


def get_db_session(database_url: str) -> Session:
    """
    Create a new database session.

    Args:
        database_url: Database connection string

    Returns:
        SQLAlchemy Session instance

    Raises:
        IngestionDatabaseError: If connection fails
    """
    try:
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        return SessionLocal()
    except Exception as e:
        raise IngestionDatabaseError(f"Failed to connect to database: {str(e)}")


def find_batch_by_filename(
    filename: str,
    database_url: str,
) -> Optional[str]:
    """
    Find batch_id for a given filename (exact match).

    Used by /api/processing to match uploaded files back to their ImportBatch.
    Returns the most recent batch if multiple batches share the filename.

    Args:
        filename: Filename to search (e.g., 'test.csv' or 'upload_YYYYMMDD_HHMMSS_test.csv')
        database_url: Database connection URL

    Returns:
        batch_id if match found, None otherwise

    Raises:
        IngestionDatabaseError: If database query fails
    """
    try:
        session = get_db_session(database_url)
        try:
            # Query batches with matching filename (exact match)
            batch = session.query(ImportBatch).filter_by(filename=filename).order_by(
                ImportBatch.upload_timestamp.desc()
            ).first()

            if batch:
                return batch.id
            return None
        finally:
            session.close()
    except IngestionDatabaseError:
        raise
    except Exception as e:
        logger.warning(f"Failed to find batch by filename {filename}: {e}")
        return None


# ============================================================================
# CSV Validation and Processing
# ============================================================================

def validate_processed_csv(csv_path: str) -> pd.DataFrame:
    """
    Validate and load processed CSV.

    Checks:
    - File exists and is readable
    - CSV has at least one data row
    - Required processor columns exist

    Args:
        csv_path: Path to processed CSV file

    Returns:
        DataFrame with validated CSV data

    Raises:
        IngestionIOError: If file not found or unreadable
        IngestionValidationError: If CSV structure is invalid
    """
    csv_path = Path(csv_path)

    # Check file exists
    if not csv_path.exists():
        raise IngestionIOError(f"File not found: {csv_path}")

    # Check file is readable
    if not csv_path.is_file():
        raise IngestionIOError(f"Path is not a file: {csv_path}")

    try:
        # Read CSV
        df = pd.read_csv(str(csv_path), dtype=str)
    except Exception as e:
        raise IngestionIOError(f"Failed to read CSV: {str(e)}")

    # Check for data rows
    if len(df) == 0:
        raise IngestionValidationError("CSV has no data rows (only header or empty)")

    # Check for required processor columns
    required_columns = {"Validation_Tier", "Issues", "Suggested_Modifications"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise IngestionValidationError(
            f"CSV missing required processor columns: {', '.join(sorted(missing_columns))}"
        )

    return df


def build_header_mapping_for_ingestion(df_columns: List[str]) -> Dict[str, str]:
    """
    Build mapping of logical field names to actual CSV columns.

    Uses exact match first, then fuzzy fallback (similar to processor).
    Reuses processor's column name patterns for consistency.

    Args:
        df_columns: DataFrame column names

    Returns:
        Dict mapping logical keys to actual column names
    """
    # Define core headers (exact match)
    core_headers = {
        "name": "Name",
        "email": "Email",
        "phone": "Phone",
        "address_1": "Address 1",
        "address_2": "Address 2",
        "city": "City",
        "state": "State",
        "zip": "Zip",
        "amount": "Amount",
        "transaction_id": "Transaction ID",
        "date": "Date",
    }

    # Define fuzzy fallbacks
    fuzzy_headers = {
        "name": ["Full Name", "Donor Name", "Donor", "donor_name", "full_name"],
        "email": ["Email Address", "Primary Email", "email_address"],
        "phone": ["Phone Number", "contact_phone", "phone_number"],
        "address_1": ["Street Address", "Address Line 1", "street_address"],
        "address_2": ["Address Line 2", "address_line_2"],
        "city": ["City Name"],
        "state": ["State Code"],
        "zip": ["Zipcode", "Postal Code", "postal_code", "zip_code"],
        "amount": ["Donation Amount", "Gift Amount"],
        "transaction_id": ["Donation ID", "Gift ID", "donation_id"],
        "date": ["Donation Date", "Gift Date", "donation_date"],
    }

    # Strip whitespace from actual columns
    clean_columns = {col.strip(): col for col in df_columns}
    lowercase_columns = {col.strip().lower(): col.strip() for col in df_columns}

    mapping = {}

    # Try strict matches first
    for key, strict_name in core_headers.items():
        if strict_name in clean_columns:
            mapping[key] = clean_columns[strict_name]
        else:
            # Try fuzzy matches
            fuzzy_options = fuzzy_headers.get(key, [])
            for fuzzy_name in fuzzy_options:
                if fuzzy_name.lower() in lowercase_columns:
                    mapping[key] = lowercase_columns[fuzzy_name.lower()]
                    break

    return mapping


# ============================================================================
# Ingestion Core
# ============================================================================

def ingest_processed_csv(
    processed_csv_path: str,
    original_filename: str,
    database_url: str,
    uploader: Optional[str] = None,
    imported_at: Optional[datetime] = None,
) -> IngestionResult:
    """
    Ingest processed CSV into Option C database schema.

    Transforms a processor-output CSV into database records:
    - ImportBatch: one per ingestion
    - RawImportRow: one per CSV row (immutable)
    - ImportContact: one per CSV row (denormalized snapshot)
    - ReviewItem: validation and normalization items (pending)
    - ReviewItemSubject: links items to affected contacts
    - AuditLogRecord: one batch_imported record on success

    Does NOT create:
    - ReviewDecision records (future reviewer work)
    - Household ReviewItems (deferred to Phase 2)
    - Duplicate ReviewItems (deferred to later step)

    Args:
        processed_csv_path: Path to processed CSV with Validation_Tier, Issues, Suggested_Modifications
        original_filename: Original filename (for audit trail)
        database_url: Database connection URL
        uploader: User/service identity for audit trail (defaults to 'system')
        imported_at: Timestamp for import (defaults to now)

    Returns:
        IngestionResult with batch_id, counts, audit_log_id, status

    Raises:
        IngestionValidationError: CSV validation failed
        IngestionIOError: File I/O failed
        IngestionDatabaseError: Database operation failed
        BatchIDCollisionError: Generated batch ID already exists
    """
    # Set defaults
    if uploader is None:
        uploader = "system"
    if imported_at is None:
        imported_at = datetime.utcnow()

    # ========================================================================
    # 1. Validate and load CSV
    # ========================================================================
    logger.info(f"Ingestion: validating and loading CSV from {processed_csv_path}")
    try:
        df = validate_processed_csv(processed_csv_path)
    except (IngestionIOError, IngestionValidationError):
        raise

    # Load raw file contents for batch ID generation
    try:
        with open(processed_csv_path, "rb") as f:
            csv_file_contents = f.read()
    except Exception as e:
        raise IngestionIOError(f"Failed to read file contents: {str(e)}")

    # ========================================================================
    # 2. Generate batch ID
    # ========================================================================
    batch_id = generate_batch_id(csv_file_contents, imported_at)
    logger.info(f"Generated batch ID: {batch_id}")

    # ========================================================================
    # 3. Build header mapping
    # ========================================================================
    header_mapping = build_header_mapping_for_ingestion(df.columns.tolist())
    logger.info(f"Built header mapping: {header_mapping}")

    # ========================================================================
    # 4. Prepare database session and transaction
    # ========================================================================
    session = None
    try:
        session = get_db_session(database_url)

        # ====================================================================
        # 5. Create ImportBatch record
        # ====================================================================
        batch = ImportBatch(
            id=batch_id,
            filename=original_filename,
            upload_timestamp=imported_at,
            uploader=uploader,
            status="pending",
            raw_row_count=len(df),
        )
        session.add(batch)
        session.flush()  # Ensure batch is inserted before foreign keys reference it
        logger.info(f"Created ImportBatch: {batch_id}")

        # ====================================================================
        # 6. Process each row
        # ====================================================================
        raw_row_ids = []  # Track RawImportRow IDs for linking
        import_contact_ids = []  # Track ImportContact IDs for subject linking
        validation_items_created = 0
        normalization_items_created = 0
        pass_count = 0
        warning_count = 0
        fail_count = 0

        for row_index, (idx, row) in enumerate(df.iterrows()):
            # Convert row to dict for storage
            row_dict = row.to_dict()

            # Get validation tier (ensure it's a string)
            validation_tier = str(row.get("Validation_Tier", "FAIL")).strip()
            if validation_tier == "PASS":
                pass_count += 1
            elif validation_tier == "WARNING":
                warning_count += 1
            else:
                fail_count += 1

            # ================================================================
            # 6a. Create RawImportRow (immutable)
            # ================================================================
            raw_row = RawImportRow(
                batch_id=batch_id,
                row_index=row_index,
                raw_csv_data=row_dict,
            )
            session.add(raw_row)
            session.flush()
            raw_row_ids.append(raw_row.id)

            # ================================================================
            # 6b. Create ImportContact (denormalized snapshot)
            # ================================================================
            # Extract and split name
            name_col = header_mapping.get("name")
            name = row.get(name_col) if name_col else None
            first_name, last_name = split_name(name) if name else (None, None)

            # Extract email
            email_col = header_mapping.get("email")
            email = row.get(email_col) if email_col else None

            # Extract phone (digits only)
            phone_col = header_mapping.get("phone")
            phone = row.get(phone_col) if phone_col else None
            if phone:
                phone = extract_digits_from_phone(phone)
                if not phone:  # If extraction resulted in empty string
                    phone = None

            # Extract address components
            address_1_col = header_mapping.get("address_1")
            address_1 = row.get(address_1_col) if address_1_col else None

            address_2_col = header_mapping.get("address_2")
            address_2 = row.get(address_2_col) if address_2_col else None

            city_col = header_mapping.get("city")
            city = row.get(city_col) if city_col else None

            state_col = header_mapping.get("state")
            state = row.get(state_col) if state_col else None

            zip_col = header_mapping.get("zip")
            postal_code = row.get(zip_col) if zip_col else None

            # Extract and parse amount
            amount_col = header_mapping.get("amount")
            amount_str = row.get(amount_col) if amount_col else None
            amount = parse_amount(amount_str) if amount_str else None

            # Create ImportContact
            contact = ImportContact(
                batch_id=batch_id,
                raw_import_row_id=raw_row.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address_line1=address_1,
                address_line2=address_2,
                city=city,
                state=state,
                postal_code=postal_code,
                amount=amount,
            )
            session.add(contact)
            session.flush()
            import_contact_ids.append(contact.id)

            # ================================================================
            # 6c. Create validation ReviewItems (if Validation_Tier != PASS)
            # ================================================================
            if validation_tier != "PASS":
                issues_str = str(row.get("Issues", "")).strip()
                if issues_str and issues_str.lower() != "none":
                    # Split on semicolon
                    issues = [issue.strip() for issue in issues_str.split(";") if issue.strip()]

                    for issue_text in issues:
                        # Try to parse field name (before first colon if it exists)
                        if ":" in issue_text:
                            field_name = issue_text.split(":")[0].strip()
                            issue_description = issue_text
                        else:
                            field_name = "unknown"
                            issue_description = issue_text

                        # Get suggestion from Suggested_Modifications if available
                        suggestions_str = str(row.get("Suggested_Modifications", "")).strip()
                        suggestion = None
                        if suggestions_str and suggestions_str.lower() != "none":
                            # For simplicity, use first suggestion (could be more sophisticated)
                            suggestions = [s.strip() for s in suggestions_str.split(";") if s.strip()]
                            if suggestions:
                                suggestion = suggestions[0]

                        # Create validation ReviewItem
                        validation_item = ReviewItem(
                            batch_id=batch_id,
                            item_type="validation",
                            status="pending",
                            confidence=1.0,
                            payload_json={
                                "field": field_name,
                                "issue": issue_description,
                                "suggestion": suggestion,
                                "validation_tier": validation_tier,
                            },
                        )
                        session.add(validation_item)
                        session.flush()

                        # Create ReviewItemSubject (link to contact)
                        subject = ReviewItemSubject(
                            review_item_id=validation_item.id,
                            subject_type="import_contact_snapshot",
                            subject_id=contact.id,
                            role="primary",
                        )
                        session.add(subject)

                        validation_items_created += 1

            # ================================================================
            # 6d. Create normalization ReviewItems (conservative rule)
            # ================================================================
            # Only for PASS rows with non-empty suggestions
            if validation_tier == "PASS":
                suggestions_str = str(row.get("Suggested_Modifications", "")).strip()
                # Filter out empty strings and known "empty" values (none, nan, <NA>, etc.)
                if suggestions_str and suggestions_str.lower() not in ("none", "nan", "<na>", ""):
                    suggestions = [s.strip() for s in suggestions_str.split(";") if s.strip()]

                    for suggestion_text in suggestions:
                        # Create normalization ReviewItem
                        normalization_item = ReviewItem(
                            batch_id=batch_id,
                            item_type="normalization",
                            status="pending",
                            confidence=0.85,
                            payload_json={
                                "field": "unknown",  # Simplified; could be enhanced
                                "raw_value": None,
                                "normalized_value": suggestion_text,
                                "basis": "processor suggestion",
                                "confidence": 0.85,
                            },
                        )
                        session.add(normalization_item)
                        session.flush()

                        # Create ReviewItemSubject
                        subject = ReviewItemSubject(
                            review_item_id=normalization_item.id,
                            subject_type="import_contact_snapshot",
                            subject_id=contact.id,
                            role="primary",
                        )
                        session.add(subject)

                        normalization_items_created += 1

        session.flush()

        # ====================================================================
        # 7. Create AuditLogRecord
        # ====================================================================
        audit_record = AuditLogRecord(
            batch_id=batch_id,
            action_type="batch_imported",
            action_timestamp=datetime.utcnow(),
            actor=uploader,
            details={
                "source": "givebutter_export",
                "filename": original_filename,
                "record_count": len(df),
                "validation_summary": {
                    "PASS": pass_count,
                    "WARNING": warning_count,
                    "FAIL": fail_count,
                },
                "items_created": {
                    "validation": validation_items_created,
                    "normalization": normalization_items_created,
                    "duplicate": 0,
                    "household": 0,
                },
            },
        )
        session.add(audit_record)
        session.flush()

        # ====================================================================
        # 8. Commit transaction
        # ====================================================================
        session.commit()
        logger.info(
            f"Ingestion committed: batch={batch_id}, "
            f"rows={len(df)}, "
            f"validation_items={validation_items_created}, "
            f"normalization_items={normalization_items_created}"
        )

        # ====================================================================
        # 9. Return result
        # ====================================================================
        result = IngestionResult(
            batch_id=batch_id,
            filename=original_filename,
            raw_row_count=len(df),
            contacts_created=len(import_contact_ids),
            validation_items_created=validation_items_created,
            normalization_items_created=normalization_items_created,
            duplicate_items_created=0,  # Deferred to later step
            household_items_created=0,  # Deferred to Phase 2
            audit_log_id=audit_record.id,
            audit_action_type="batch_imported",
            audit_timestamp=audit_record.action_timestamp,
            status="success",
            uploader=uploader,
            pass_count=pass_count,
            warning_count=warning_count,
            fail_count=fail_count,
        )

        logger.info(f"Ingestion result: {result}")
        return result

    except (IngestionValidationError, IngestionIOError, BatchIDCollisionError):
        if session:
            session.rollback()
        raise
    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Unexpected error during ingestion: {str(e)}", exc_info=True)
        raise IngestionDatabaseError(f"Ingestion failed: {str(e)}")
    finally:
        if session:
            session.close()
