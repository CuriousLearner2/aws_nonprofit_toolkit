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

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from .ingestion_plan_policy import plan_ingestion
from .ingestion_value_policy import extract_digits_from_phone, parse_amount, split_name
from .repository_provider import get_ingestion_session, get_ingestion_writer, find_ingestion_batch_by_filename

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
    Generate unique batch ID with timestamp, content hash, and a unique suffix.

    Format: IMP-YYYYMMDD-HHMMSS-<HASH8><UNIQ8>
    Example: IMP-20260612-121530-A7F2B3C1D4E5F6A7

    Args:
        csv_file_contents: Bytes of processed CSV file
        imported_at: Timestamp to use (defaults to current UTC time)

    Returns:
        Batch ID string
    """
    # Use provided timestamp or current time
    if imported_at is None:
        imported_at = datetime.now(timezone.utc)

    # Calculate file hash (first 8 chars of SHA256, uppercase)
    file_hash = hashlib.sha256(csv_file_contents).hexdigest()[:8].upper()
    unique_suffix = uuid.uuid4().hex[:8].upper()

    # Format timestamp
    timestamp_str = imported_at.strftime("%Y%m%d%H%M%S")
    batch_id = f"IMP-{timestamp_str[:8]}-{timestamp_str[8:]}-{file_hash}{unique_suffix}"

    return batch_id


def get_db_session(database_url: str):
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
        return get_ingestion_session(database_url)
    except Exception as e:
        raise IngestionDatabaseError(f"Failed to connect to database: {str(e)}")


def find_batch_by_filename(
    filename: str,
    database_url: str,
) -> Optional[str]:
    """
    Find batch_id for a given filename only when it resolves unambiguously.

    Used by /api/processing for legacy rows that predate explicit queue metadata.
    Returns None when zero or multiple batches share the filename.

    Args:
        filename: Filename to search (e.g., 'test.csv' or 'upload_YYYYMMDD_HHMMSS_test.csv')
        database_url: Database connection URL

    Returns:
        batch_id if match found, None otherwise

    Raises:
        IngestionDatabaseError: If database query fails
    """
    try:
        return find_ingestion_batch_by_filename(filename, database_url)
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
        imported_at = datetime.now(timezone.utc)

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
    plan = plan_ingestion(batch_id=batch_id, original_filename=original_filename, uploader=uploader, imported_at=imported_at, header_mapping=header_mapping, rows=[row.to_dict() for _, row in df.iterrows()])

    # ========================================================================
    # 4. Prepare database session and transaction
    # ========================================================================
    try:
        write_result = get_ingestion_writer(database_url, session_factory=get_db_session).persist_ingestion_plan(plan)
        logger.info(
            f"Ingestion committed: batch={batch_id}, "
            f"rows={len(df)}, "
            f"validation_items={plan.validation_items_created}, "
            f"normalization_items={plan.normalization_items_created}"
        )

        # ====================================================================
        # 9. Return result
        # ====================================================================
        result = IngestionResult(
            batch_id=batch_id,
            filename=original_filename,
            raw_row_count=len(df),
            contacts_created=len(plan.rows),
            validation_items_created=plan.validation_items_created,
            normalization_items_created=plan.normalization_items_created,
            duplicate_items_created=0,  # Deferred to later step
            household_items_created=0,  # Deferred to Phase 2
            audit_log_id=write_result.audit_log_id,
            audit_action_type="batch_imported",
            audit_timestamp=write_result.audit_timestamp,
            status="success",
            uploader=uploader,
            pass_count=plan.pass_count,
            warning_count=plan.warning_count,
            fail_count=plan.fail_count,
        )

        logger.info(f"Ingestion result: {result}")
        return result

    except (IngestionValidationError, IngestionIOError, BatchIDCollisionError):
        raise
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {str(e)}", exc_info=True)
        raise IngestionDatabaseError(f"Ingestion failed: {str(e)}")
