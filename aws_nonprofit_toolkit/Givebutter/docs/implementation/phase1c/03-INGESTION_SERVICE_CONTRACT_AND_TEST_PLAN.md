# Phase 1C-Step 3: Ingestion Service Contract and Test Plan

**Date**: 2026-06-12  
**Phase**: 1C-Step 3 (Ingestion Service Specification)  
**Status**: 📋 CONTRACT & TEST PLAN DEFINED (No Implementation in This Step)

---

## Executive Summary

This document specifies the ingestion service contract that will transform processor output (validated CSV) into Option C database records. It defines the interface, data contracts, validation rules, and test strategy without implementing code.

**Scope**: Specification only. Implementation is Phase 1C-Step 4.

**Key Decisions**:
1. Batch ID: `IMP-YYYYMMDD-HHMMSS-<hash8>` (timestamp + file hash)
2. Duplicate scope: Within-import only (no cross-import detection)
3. Household suggestions: Deferred to Phase 2 (see recommendation section)
4. FAIL rows: Ingest all rows (PASS/WARNING/FAIL), represent issues as pending items
5. Review decisions: Create zero during ingestion (future reviewer work)
6. Audit: Single ingestion entry on successful commit

---

## 1. Proposed Ingestion Service Interface

### Location:
```
scripts/householder/ingestion_service.py (to be created in Step 4)
```

### Function Signature:

```python
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class IngestionResult:
    """Result of successful ingestion (see Section 2 for full spec)."""
    pass  # Detailed in Section 2

def ingest_processed_csv(
    processed_csv_path: str,
    original_filename: str,
    database_url: str,
    uploader: Optional[str] = None,
    imported_at: Optional[datetime] = None,
) -> IngestionResult:
    """
    Ingest processed CSV into Option C database schema.

    Args:
        processed_csv_path: Path to processed CSV with Validation_Tier, Issues, Suggested_Modifications columns.
        original_filename: Original filename (before upload timestamp was added).
        database_url: Database connection URL (e.g., 'sqlite:///./givebutter.db').
        uploader: User/service identity for audit trail. Defaults to 'system'.
        imported_at: Timestamp for import. Defaults to datetime.now().

    Returns:
        IngestionResult containing:
        - batch_id: Generated batch ID (IMP-YYYYMMDD-HHMMSS-<hash8>)
        - filename: processed_csv_path filename
        - raw_row_count: Count of data rows ingested
        - contacts_created: Count of ImportContact records
        - validation_items_created: Count of validation ReviewItems
        - normalization_items_created: Count of normalization ReviewItems
        - duplicate_items_created: Count of duplicate ReviewItems
        - household_items_created: Count of household ReviewItems (0 if deferred)
        - audit_log_id: ID of ingestion AuditLogRecord
        - status: 'success' or specific error code

    Raises:
        IngestionValidationError: CSV missing required columns or malformed
        IngestionIOError: File not found or unreadable
        IngestionDatabaseError: Database connection or transaction failed
        IngestionRowError: Individual row processing failed (includes row details)

    Transactional:
        - All writes are atomic (commit or rollback together)
        - Audit record is created only after successful commit
        - Failed ingestion leaves no partial records

    Database Session:
        - Creates its own session from database_url
        - Closes session in finally block (no resource leak)
        - Does not accept pre-built session/engine (simplified for Phase 1C)

    Idempotency:
        - Same file can be ingested again as new batch (different timestamp)
        - Batch ID includes timestamp + hash, collision practically impossible
        - No duplicate-upload detection in Phase 1C (future enhancement)
    """
```

### Expected Exceptions:

```python
class IngestionValidationError(Exception):
    """CSV structure validation failed."""
    # Examples:
    # - Required column 'Validation_Tier' missing
    # - Required column 'Issues' missing
    # - CSV has zero data rows
    # - CSV is not readable as valid CSV

class IngestionIOError(Exception):
    """File I/O failure."""
    # Examples:
    # - processed_csv_path does not exist
    # - File is not readable
    # - File encoding issue

class IngestionDatabaseError(Exception):
    """Database operation failed."""
    # Examples:
    # - Cannot connect to database
    # - Transaction failed
    # - Foreign key constraint violation
    # - Schema mismatch (missing tables)

class IngestionRowError(Exception):
    """Individual row processing failed (non-fatal to other rows if implementing row-level recovery)."""
    # Examples:
    # - Amount column cannot be parsed as float
    # - Name cannot be split into first/last
    # - Email is completely invalid (not just typo)
    # Contains: row_index, field_name, raw_value, reason

class BatchIDCollisionError(Exception):
    """Generated batch ID already exists (should be rare with timestamp+hash)."""
    # Phase 1C: If this occurs, log and retry with incremented timestamp
```

### Integration with Upload Flow:

**Note**: Phase 1C-Step 4 will decide whether to:
- Option A: Call `ingest_processed_csv()` from POST /upload route
- Option B: Expose as separate endpoint (POST /api/ingest)
- Option C: Both (upload triggers ingestion automatically)

This contract is agnostic to that decision.

---

## 2. IngestionResult Shape

### Dataclass Definition:

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(frozen=True)
class IngestionResult:
    """Immutable result of successful ingestion."""

    # Primary identifiers
    batch_id: str  # Generated ID: IMP-YYYYMMDD-HHMMSS-<hash8>
    filename: str  # Processed CSV filename (with upload timestamp prefix)

    # Counts
    raw_row_count: int  # Total data rows ingested (PASS + WARNING + FAIL)
    contacts_created: int  # ImportContact records created
    validation_items_created: int  # Validation ReviewItems created
    normalization_items_created: int  # Normalization ReviewItems created
    duplicate_items_created: int  # Duplicate ReviewItems created
    household_items_created: int  # Household ReviewItems (0 if deferred to Phase 2)

    # Audit trail
    audit_log_id: int  # ID of AuditLogRecord for this ingestion
    audit_action_type: str  # 'batch_imported'
    audit_timestamp: datetime  # When ingestion completed

    # Status
    status: str  # 'success'
    uploader: Optional[str]  # User/service identity from request

    # Validation summary (optional, for transparency)
    pass_count: Optional[int] = None  # Rows with Validation_Tier == PASS
    warning_count: Optional[int] = None  # Rows with Validation_Tier == WARNING
    fail_count: Optional[int] = None  # Rows with Validation_Tier == FAIL

    def __repr__(self) -> str:
        return (
            f"IngestionResult(batch_id={self.batch_id}, "
            f"rows={self.raw_row_count}, items={self.validation_items_created + self.normalization_items_created + self.duplicate_items_created})"
        )
```

### Semantics:

| Field | Required | Type | Source | Notes |
|-------|----------|------|--------|-------|
| batch_id | ✓ | str | Generated | IMP-YYYYMMDD-HHMMSS-<hash8> |
| filename | ✓ | str | Input | From processed_csv_path |
| raw_row_count | ✓ | int | CSV | Rows with data (excluding header) |
| contacts_created | ✓ | int | Database | ImportContact count |
| validation_items_created | ✓ | int | Database | ReviewItem count (type=validation) |
| normalization_items_created | ✓ | int | Database | ReviewItem count (type=normalization) |
| duplicate_items_created | ✓ | int | Database | ReviewItem count (type=duplicate) |
| household_items_created | ✓ | int | Database | ReviewItem count (type=household) or 0 if deferred |
| audit_log_id | ✓ | int | Database | ID of AuditLogRecord created |
| audit_action_type | ✓ | str | Constant | Always 'batch_imported' for Phase 1C |
| audit_timestamp | ✓ | datetime | Ingestion | When ingestion completed |
| status | ✓ | str | Constant | Always 'success' (failures raise exceptions) |
| uploader | ○ | str | Input | From uploader parameter |
| pass_count | ○ | int | CSV | Optional for transparency |
| warning_count | ○ | int | CSV | Optional for transparency |
| fail_count | ○ | int | CSV | Optional for transparency |

---

## 3. Processor Output Validation Rules

### Required CSV Columns (From Processor):

All processed CSVs must have these 3 columns added by processor:

| Column | Type | Required | Source | Examples |
|--------|------|----------|--------|----------|
| `Validation_Tier` | String | ✓ | Processor | PASS, WARNING, FAIL |
| `Issues` | String | ✓ | Processor | "Email: typo detected; Phone: format invalid" or "None" |
| `Suggested_Modifications` | String | ✓ | Processor | "Consider: john@gmail.com" or "" |

**Error Handling**:
- If any of these 3 columns is missing → `IngestionValidationError`
- If column names don't match exactly (case-sensitive) → `IngestionValidationError`

### Required Contact/Donor Fields (From Givebutter CSV):

Processor uses header mapping to find these fields. Ingestion must also use the same mapping:

| Field | Logical Key | CORE_HEADERS (Exact) | FUZZY_HEADERS (Fallbacks) | Nullable in DB | Required for Ingestion |
|-------|-------------|----------------------|---------------------------|-----------------|------------------------|
| Name | name | Name | Full Name, Donor Name, ... | ✓ (split fails) | ✓ |
| Email | email | Email | Email Address, Primary Email, ... | ✓ | ✓ |
| Phone | phone | Phone | Phone Number, Contact Phone, ... | ✓ | ○ (WARNING ok) |
| Address 1 | address_1 | Address 1 | Street Address, Address Line 1, ... | ✓ | ○ (WARNING ok) |
| Address 2 | address_2 | Address 2 | Address Line 2, Apt/Suite, ... | ✓ | ○ |
| City | city | City | - | ✓ | ○ (WARNING ok) |
| State | state | State | - | ✓ | ○ (WARNING ok) |
| Zip | zip | Zip | Zipcode, Postal Code, ZIP Code, ... | ✓ | ○ (WARNING ok) |
| Amount | amount | Amount | - | ✓ | ✓ |
| Transaction ID | transaction_id | Transaction ID | Donation ID, Gift ID, ... | ✗ (FK to RawImportRow) | ✓ |
| Date | date | Date | Donation Date, Gift Date, ... | ✗ (for audit) | ✓ |

**Strategy**:
- Reuse `build_header_mapping()` from processor.py
- If header mapping succeeds, proceed
- If header mapping fails to find required fields → `IngestionValidationError`

### CSV Structure Validation:

| Condition | Behavior | Exception |
|-----------|----------|-----------|
| CSV file does not exist | Log path, raise error | IngestionIOError |
| CSV not readable (encoding, format) | Log error, raise | IngestionIOError |
| CSV has 0 data rows (only header) | Log warning, raise error | IngestionValidationError |
| CSV is not valid CSV format | Log parse error, raise | IngestionValidationError |
| Missing Validation_Tier column | Log, raise | IngestionValidationError |
| Missing Issues column | Log, raise | IngestionValidationError |
| Missing Suggested_Modifications column | Log, raise | IngestionValidationError |
| Malformed amount (cannot parse as float) | Row-level: include in Issues, process as WARNING | IngestionRowError OR continue with null amount |

### Decision: Row-Level Error Handling

**Phase 1C Recommendation**: Fail fast at CSV level (schema validation), then proceed row-by-row with lenient field-level parsing:

```
For each row:
  1. Extract required fields using header mapping
  2. If field is missing or empty:
     - If nullable in DB: use None
     - If not nullable: log issue, represent as validation item, use empty string or default
  3. If field is unparseable (e.g., amount="abc"):
     - Log issue, represent as validation item, use null or 0
  4. Continue processing row (no early termination per row)
     - Rationale: FAIL rows are valid data that should be reviewed
```

---

## 4. Database Write Contract

This section specifies EXACTLY what ingestion writes to each Option C table.

### 4.1 ImportBatch Table

**Phase 1C writes exactly one ImportBatch record per ingestion.**

| Field | Type | Source | Value | Immutable |
|-------|------|--------|-------|-----------|
| `id` | String(50) | Generated | IMP-YYYYMMDD-HHMMSS-<hash8> | ✓ |
| `filename` | String(255) | Input: original_filename | Original filename (from upload_filename parameter) | ✓ |
| `upload_timestamp` | DateTime | Input: imported_at | Default: datetime.utcnow() | ✓ |
| `uploader` | String(255) | Input: uploader | Value or 'system' if None | ✓ |
| `status` | String(50) | Default | 'pending' (batch is ready for review) | ○ (mutable by future reviewer ops) |
| `raw_row_count` | Integer | CSV | Count of data rows ingested | ✓ |
| `created_at` | DateTime | Default | datetime.utcnow() | ✓ |
| `updated_at` | DateTime | Default | datetime.utcnow() | ○ (updated on status change by reviewers) |

**Batch ID Generation Algorithm**:
```
hash = sha256(csv_file_contents).hexdigest()[:8].upper()
timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
batch_id = f"IMP-{timestamp_str[:8]}-{timestamp_str[8:]}-{hash}"
# Example: IMP-20260612-121530-A7F2B3C1
```

**Constraint**: Batch ID is primary key. If generated ID collides with existing record → `BatchIDCollisionError` → retry with incremented timestamp (unlikely with hash component).

### 4.2 RawImportRow Table

**Phase 1C writes exactly one RawImportRow record per CSV data row.**

| Field | Type | Source | Value | Immutable |
|-------|------|--------|-------|-----------|
| `id` | Integer | Auto-increment | Generated by database | ✓ |
| `batch_id` | String(50) FK | ImportBatch | Batch ID created in step 4.1 | ✓ |
| `row_index` | Integer | CSV position | 0-based row number in CSV (0 = first data row) | ✓ |
| `raw_csv_data` | JSON | CSV row | Original row as dict: `{header: value, ...}` | ✓ |
| `created_at` | DateTime | Default | datetime.utcnow() | ✓ |

**Immutability**: RawImportRow is never modified after creation. Future phases may archive or link prior imports, but original row is preserved forever.

**Data Preservation**: `raw_csv_data` includes ALL original columns from upload (before any processor columns were added). This preserves the exact input state.

### 4.3 ImportContact Table

**Phase 1C writes exactly one ImportContact record per CSV data row (denormalized snapshot).**

| Field | Type | Source | Value | Immutable |
|-------|------|--------|-------|-----------|
| `id` | Integer | Auto-increment | Generated by database | ✓ |
| `batch_id` | String(50) FK | ImportBatch | Batch ID | ✓ |
| `raw_import_row_id` | Integer FK | RawImportRow | ID of corresponding raw row | ✓ |
| `first_name` | String(255) nullable | Name column split | Extract first name from 'Name' field | ✓ |
| `last_name` | String(255) nullable | Name column split | Extract last name from 'Name' field | ✓ |
| `email` | String(255) nullable | Email column | Mapped via header_mapping | ✓ |
| `phone` | String(50) nullable | Phone column | Mapped via header_mapping, digits only | ✓ |
| `address_line1` | String(255) nullable | Address 1 column | Mapped via header_mapping | ✓ |
| `address_line2` | String(255) nullable | Address 2 column | Mapped via header_mapping | ✓ |
| `city` | String(100) nullable | City column | Mapped via header_mapping | ✓ |
| `state` | String(10) nullable | State column | Mapped via header_mapping | ✓ |
| `postal_code` | String(20) nullable | Zip column | Mapped via header_mapping | ✓ |
| `amount` | Float nullable | Amount column | Parsed as float, null if unparseable | ✓ |
| `created_at` | DateTime | Default | datetime.utcnow() | ✓ |

**Name Splitting**:
```
Algorithm (Phase 1C):
  Input: "John Smith" or "John Q. Smith Jr." or "Jane" or ""
  
  1. Strip whitespace
  2. If empty: first_name=None, last_name=None
  3. If single word: first_name=word, last_name=None
  4. If two+ words: 
     a. Split on space(s)
     b. first_name = first part
     c. last_name = remaining parts joined with space
  
  Example: "John Michael Smith" → first="John", last="Michael Smith"
  Example: "John Smith Jr." → first="John", last="Smith Jr."
  Example: "John" → first="John", last=None
  Example: "" → first=None, last=None

Recommendation: Keep simple; complex name parsing (suffix handling, international names) 
deferred to Phase 2 or future normalization items.
```

**Phone Normalization**:
```
Extract digits only: "(" ")" "-" "." etc. removed.
Store in database as digits only (e.g., "5551234567").
Template rendering can apply formatting.
```

**Immutability**: ImportContact is never modified after creation. It's a snapshot of the contact at import time.

### 4.4 ReviewItem Table

**Phase 1C writes ReviewItem records for suggestions/findings (validation, normalization, duplicate). NOT for review decisions.**

**Records are created based on processor output and within-import duplicate detection.**

#### Validation ReviewItems (item_type='validation')

**Created when**: Validation_Tier != PASS OR Issues contains diagnostic text.

**One ValidationItem per affected field per row.**

| Field | Value |
|-------|-------|
| `id` | Auto-increment |
| `batch_id` | Batch ID |
| `item_type` | 'validation' |
| `status` | 'pending' |
| `confidence` | 1.0 (deterministic processor finding) |
| `payload_json` | See below |
| `created_at` | datetime.utcnow() |

**payload_json for validation**:
```python
{
    "field": "email",  # or "name", "phone", "amount", "address", etc.
    "issue": "Email: Email typo detected",  # From Issues column
    "suggestion": "Consider: john@gmail.com",  # From Suggested_Modifications if applicable
    "validation_tier": "WARNING",  # From Validation_Tier column
}
```

**Example**:
```
If CSV row has:
  Validation_Tier = "WARNING"
  Issues = "Email: Email typo detected; Phone: Phone too short"
  Suggested_Modifications = "Consider: john@gmail.com; Use a valid phone number"

Create two ReviewItems:
  1. item_type='validation', payload={field:"email", issue:"...", suggestion:"..."}
  2. item_type='validation', payload={field:"phone", issue:"...", suggestion:"..."}
```

#### Normalization ReviewItems (item_type='normalization')

**Created when**: Suggested_Modifications contains normalization suggestions (not validation remediations).

**Challenge**: Processor output conflates validation failure reasons with improvement suggestions in a single text column. Phase 1C must distinguish:

**Normalization Heuristic** (Phase 1C):
```
Suggestion is NORMALIZATION if:
  - It's not already in the validation item's suggestion field
  - It represents optional field standardization
  - Examples:
    - "Phone format: Consider: (555) 123-4567"
    - "Email domain typo: Consider: john@gmail.com"
    - "Name capitalization: Consider: John Smith"

Suggestion is VALIDATION REMEDIATION if:
  - It directly addresses a FAIL issue
  - Examples:
    - "Email field is empty" (FAIL) → no normalization item
    - "Transaction ID is missing" (FAIL) → no normalization item

Phase 1C Recommendation:
  Create normalization items ONLY for non-empty Suggested_Modifications entries
  that are not already captured as validation item suggestions.
  
  Conservative rule: If Validation_Tier == 'PASS' and Suggested_Modifications is non-empty,
  create normalization items.
```

| Field | Value |
|-------|-------|
| `id` | Auto-increment |
| `batch_id` | Batch ID |
| `item_type` | 'normalization' |
| `status` | 'pending' |
| `confidence` | 0.85 (processor default or null) |
| `payload_json` | See below |
| `created_at` | datetime.utcnow() |

**payload_json for normalization**:
```python
{
    "field": "email",
    "raw_value": "john@gmai.com",
    "normalized_value": "john@gmail.com",
    "basis": "email domain typo",  # or "phone format", "name standardization", etc.
    "confidence": 0.85,
}
```

#### Duplicate ReviewItems (item_type='duplicate')

**Created when**: Processor Issues column contains "Duplicate: ..." or within-import duplicate detection identifies matches.

**Within-Import Detection** (Phase 1C):
- Reuse processor's `check_duplicates()` function OR
- Implement minimal within-import check:
  ```
  For each row:
    Check if (email, phone, address) exact match another row in same import
    If match found:
      Create duplicate ReviewItem with both contacts as subjects
  ```

| Field | Value |
|-------|-------|
| `id` | Auto-increment |
| `batch_id` | Batch ID |
| `item_type` | 'duplicate' |
| `status` | 'pending' |
| `confidence` | 0.75 or null |
| `payload_json` | See below |
| `created_at` | datetime.utcnow() |

**payload_json for duplicate**:
```python
{
    "match_type": "email",  # or "phone", "address", "name_fuzzy"
    "evidence": ["Email match: TXN-002"],  # What matched
    "conflicts": [],  # Fields that differ (future)
    "confidence": 0.75,
}
```

**Matched Contact Identification**:
```
If processor output includes "Duplicate: Email match: TXN-002":
  - Identify the matched transaction ID
  - Look up the ImportContact with matching email
  - Create ReviewItemSubject for both primary and secondary contacts
  
If processor output does not identify the matched contact:
  - Create ReviewItem with only primary contact as subject
  - Reviewer must manually identify the secondary contact (future work)
```

#### Household ReviewItems (item_type='household')

**Phase 1C Decision: DEFERRED TO PHASE 2**

Rationale:
- Processor has no household detection logic
- Household grouping requires multi-record heuristics (address + name matching)
- Phase 1B guardrails: no automatic approvals; household suggestions must be pending
- Current household route shows fixture data, not database-backed household items

**Result**: `household_items_created = 0` for Phase 1C.

**Alternative** (if Phase 1C wants to include households):
```
Define narrow rule: Same address + same last name = household
  1. Group rows by (address_line1, city, state, postal_code, last_name)
  2. For groups with 2+ contacts: create household ReviewItem
  3. Example:
     - John Smith, 123 Main St
     - Jane Smith, 123 Main St
     → Create household ReviewItem linking both
     
Implementation burden: Low
Recommendation: Include if time permits; otherwise defer to Phase 2
```

---

### 4.5 ReviewItemSubject Table

**Phase 1C writes ReviewItemSubject records to link ReviewItems to affected contacts.**

| Field | Value |
|-------|-------|
| `id` | Auto-increment |
| `review_item_id` | ReviewItem.id created in 4.4 |
| `subject_type` | 'import_contact_snapshot' (Phase 1C only value) |
| `subject_id` | ImportContact.id |
| `role` | 'primary' or 'secondary' |
| `created_at` | datetime.utcnow() |

**Linking Rules**:
```
Validation item:
  - 1:1 mapping: ReviewItemSubject.subject_id = affected ImportContact.id
  - role = 'primary'

Normalization item:
  - 1:1 mapping
  - role = 'primary'

Duplicate item:
  - 2:1 mapping: Primary contact + secondary (matched) contact
  - Primary contact: role = 'primary'
  - Matched contact: role = 'secondary'
  - Both subject_id point to ImportContact records in same batch

Household item (if implemented):
  - N:1 mapping: All contacts in household
  - One contact: role = 'primary' (group representative)
  - Others: role = 'member'
```

---

### 4.6 AuditLogRecord Table

**Phase 1C writes exactly one AuditLogRecord on successful ingestion commit.**

| Field | Value |
|-------|-------|
| `id` | Auto-increment |
| `batch_id` | Batch ID |
| `action_type` | 'batch_imported' |
| `action_timestamp` | datetime.utcnow() (or imported_at parameter) |
| `actor` | uploader parameter or 'system' |
| `item_id` | None (not applicable for batch-level action) |
| `decision_id` | None (no decisions created) |
| `details` | See below |
| `created_at` | datetime.utcnow() |

**details JSON**:
```python
{
    "source": "givebutter_export",
    "filename": original_filename,
    "record_count": raw_row_count,
    "validation_summary": {
        "PASS": pass_count,
        "WARNING": warning_count,
        "FAIL": fail_count,
    },
    "items_created": {
        "validation": validation_items_created,
        "normalization": normalization_items_created,
        "duplicate": duplicate_items_created,
        "household": household_items_created,
    },
}
```

**Timing**: AuditLogRecord is created ONLY AFTER successful transaction commit (as part of commit or immediately after).

---

### 4.7 ReviewDecision Table (NOT WRITTEN IN PHASE 1C)

**Ingestion creates ZERO ReviewDecision records.**

ReviewDecision records represent reviewer decisions (accept, reject, same_person, confirmed, etc.). These are future work only; they are created when reviewers interact with the dashboard.

---

### Summary: Write Contract by Table

| Table | Records | Mutability | Phase 1C | Notes |
|-------|---------|------------|---------|-------|
| import_batches | 1 per ingestion | Immutable (id, filename, timestamp) | ✓ Write | status field mutable by reviewers |
| raw_import_rows | 1 per row | Immutable | ✓ Write | Preserves original CSV data |
| import_contacts | 1 per row | Immutable | ✓ Write | Denormalized snapshot |
| review_items | N (validation, normalization, duplicate) | Immutable | ✓ Write | Polymorphic items, pending status |
| review_item_subjects | N (links items to contacts) | Immutable | ✓ Write | Enables flexible entity references |
| review_decisions | 0 | - | ✗ No Write | Future reviewer work |
| audit_log | 1 per ingestion | Immutable | ✓ Write | Records ingestion event |

---

## 5. Review Item Generation Rules (Detailed)

### 5.1 Validation Review Items

**Generation Rule**:
```
For each row in processed CSV:
  If Validation_Tier != 'PASS':
    Parse Issues column (semicolon-separated)
    For each issue string (e.g., "Email: Email typo detected"):
      Extract field name: first part before colon
      Extract issue description: rest of string
      Create ReviewItem(
        item_type='validation',
        status='pending',
        confidence=1.0,
        payload={field, issue, suggestion, validation_tier}
      )
      Create ReviewItemSubject(review_item_id, subject_type='import_contact_snapshot', subject_id=contact_id, role='primary')
```

**Edge Cases**:
- Issues column is "None" → No validation items created (row is PASS)
- Issues column is empty string "" → No validation items created
- Multiple issues in same row → Multiple ReviewItems created (one per issue)
- Issue text is malformed (missing colon) → Use entire string as issue description

### 5.2 Normalization Review Items

**Generation Rule** (CONSERVATIVE):
```
For each row in processed CSV:
  If Validation_Tier == 'PASS' and Suggested_Modifications is non-empty:
    Parse Suggested_Modifications column (semicolon-separated)
    For each suggestion that looks like a field improvement (not validation fix):
      Create ReviewItem(
        item_type='normalization',
        status='pending',
        confidence=0.85,
        payload={field, raw_value, normalized_value, basis}
      )
      Create ReviewItemSubject(...)
  
  Alternatively:
  If Validation_Tier == 'WARNING' and Suggested_Modifications has additional improvements:
    Create normalization items for non-validation-related suggestions
```

**Clarification**: Avoid "double-counting" a suggestion:
- If Issues says "Email typo" and Suggested_Modifications says "Consider: john@gmail.com",
- That suggestion goes in the validation item payload
- Do NOT create a separate normalization item for the same suggestion

**Phase 1C Recommendation**: Conservative rule: Only create normalization items for PASS rows with non-empty Suggested_Modifications.

### 5.3 Duplicate Review Items

**Generation Rule**:
```
Phase 1C: Within-import duplicates only

Option A (Reuse Processor Output):
  For each row:
    If Issues contains "Duplicate: ...":
      Parse duplicate evidence from Issues
      Try to identify matched contact via transaction ID or other identifier
      If identified:
        Create ReviewItem(item_type='duplicate', payload={evidence})
        Create ReviewItemSubject(role='primary', subject_id=current_contact_id)
        Create ReviewItemSubject(role='secondary', subject_id=matched_contact_id)
      Else:
        Create ReviewItem with only primary subject
        (Reviewer must manually find the secondary contact)

Option B (Re-detect Within Import):
  After all rows ingested:
    For each pair of rows:
      Check if (email, phone, address) exact match
      If match:
        Create ReviewItem(item_type='duplicate', payload={match_type, evidence})
        Create two ReviewItemSubjects
        
Recommendation: Use Option A (reuse processor output).
If processor output is ambiguous, fallback to Option B.
```

**Matched Contact Identification Strategy**:
```
If Issues contains "Duplicate: Email match: TXN-002":
  1. Extract transaction ID from evidence string
  2. Query ImportContact table: WHERE email = current_email AND batch_id = batch_id
  3. Match should find exactly one contact (email is unique per batch for duplicates)
  4. If multiple matches: use first match, log warning
  5. If no match: create item with only primary subject
```

### 5.4 Household Review Items

**Phase 1C: DEFERRED**

No household items created in Phase 1C.

**Household Route Behavior**:
```
GET /imports/<batch_id>/households
  → Database mode queries ReviewItem WHERE item_type='household' AND batch_id=?
  → Result: empty list (no items created in Phase 1C)
  → Route renders template with empty households list (or "None found" message)
```

**Future Phase 2 Option** (if narrow rule is chosen):
```
Rule: Same address + same last_name = household
  
Implementation:
  1. Group import_contacts by (address_line1, city, state, postal_code, last_name)
  2. For groups with 2+ contacts:
     a. Create ReviewItem(item_type='household', payload={suggested_label, basis, members})
     b. Create ReviewItemSubject for each member:
        - First member: role='primary'
        - Others: role='member'

Recommended narrow rule threshold: 2+ contacts at same address with same last name
```

---

## 6. Idempotency and Transaction Strategy

### 6.1 Batch ID Generation and Collision Avoidance

**Algorithm**:
```python
import hashlib
from datetime import datetime

def generate_batch_id(csv_file_contents: bytes, original_filename: str = None) -> str:
    """Generate unique batch ID with timestamp and content hash."""
    # Calculate file hash (first 8 chars of SHA256)
    file_hash = hashlib.sha256(csv_file_contents).hexdigest()[:8].upper()
    
    # Format: IMP-YYYYMMDD-HHMMSS-<hash8>
    now = datetime.utcnow()
    timestamp_str = now.strftime("%Y%m%d%H%M%S")
    batch_id = f"IMP-{timestamp_str[:8]}-{timestamp_str[8:]}-{file_hash}"
    
    return batch_id
    # Example: IMP-20260612-121530-A7F2B3C1
```

**Collision Probability**:
- Timestamp precision: 1 second (unlikely to upload 2 files in same second)
- Hash precision: 8 characters (256M possible hashes, statistically unique)
- Combined: Collision is practically impossible in normal workflow

**Collision Handling** (Phase 1C):
```
1. Generate batch_id as above
2. Try to insert ImportBatch record
3. If unique constraint violation (batch_id already exists):
   a. Log warning
   b. Increment timestamp by 1 second
   c. Retry (max 10 attempts)
   d. If still collision: raise BatchIDCollisionError
   
Rationale: Collision should not happen in practice; error is diagnostic.
```

### 6.2 Duplicate File Upload Behavior

**Phase 1C Policy**:
```
Same file can be uploaded again as new batch:
  - File uploaded at 2026-06-12 10:15:30 → batch IMP-20260612-101530-HASH1
  - Same file uploaded at 2026-06-12 14:30:00 → batch IMP-20260612-143000-HASH1
  - Result: Two separate batches in database (different batch_ids, same file hash)
  
Rationale:
  - Batch ID includes timestamp, so same file at different time = different batch
  - This allows re-importing the same file if needed (e.g., reviewing again)
  - No duplicate-upload detection in Phase 1C (can be added in Phase 2 if needed)
```

### 6.3 Transaction Semantics

**Atomicity**:
```
All writes must succeed or all fail together.

Transaction flow:
  1. BEGIN TRANSACTION
  2. Create ImportBatch record
  3. For each row:
     a. Create RawImportRow record
     b. Create ImportContact record
     c. Create ReviewItem(s) for validation/normalization/duplicate
     d. Create ReviewItemSubject(s)
  4. Create AuditLogRecord
  5. COMMIT
  
If any write fails:
  6. ROLLBACK (all writes undone)
  7. Raise IngestionDatabaseError
```

**Post-Commit Audit**:
```
AuditLogRecord is created as part of successful transaction.
If transaction rolls back, AuditLogRecord is also rolled back (no partial records).
After COMMIT succeeds, IngestionResult is returned.
```

**Retry Strategy** (Phase 1C):
```
No automatic retry in Phase 1C.
If transaction fails, raise exception and let caller decide whether to retry.
Caller can retry by re-running ingest_processed_csv() with same file.
Retries will generate new batch_id (different timestamp).

Phase 2 could implement idempotency key or duplicate batch detection.
```

### 6.4 Unique Constraints and Foreign Keys

**Expected Database Constraints**:
```
ImportBatch:
  - PK: id (batch_id)
  - Unique: (id)

RawImportRow:
  - PK: id (auto-increment)
  - FK: batch_id → ImportBatch(id)
  - Unique: (batch_id, row_index)  # One row per index per batch

ImportContact:
  - PK: id (auto-increment)
  - FK: batch_id → ImportBatch(id)
  - FK: raw_import_row_id → RawImportRow(id)
  - Unique: (batch_id, raw_import_row_id)  # 1:1 relationship

ReviewItem:
  - PK: id (auto-increment)
  - FK: batch_id → ImportBatch(id)

ReviewItemSubject:
  - PK: id (auto-increment)
  - FK: review_item_id → ReviewItem(id)
  - Unique: (review_item_id, subject_type, subject_id, role)  # Prevent duplicate subjects

ReviewDecision:
  - PK: id (auto-increment)
  - FK: batch_id → ImportBatch(id)
  - FK: review_item_id → ReviewItem(id)

AuditLogRecord:
  - PK: id (auto-increment)
  - FK: batch_id → ImportBatch(id)
  - FK: item_id → ReviewItem(id) (nullable)
  - FK: decision_id → ReviewDecision(id) (nullable)
```

**Implication**: Duplicate subject records are prevented by unique constraint. Ingestion must check before creating ReviewItemSubject.

---

## 7. Test Plan (Detailed Matrix)

### 7.1 Unit Tests

#### Batch ID Generation

```python
# tests/unit/test_ingestion_batch_id_generation.py

class TestBatchIDGeneration:
    def test_batch_id_includes_timestamp(self):
        """Batch ID includes YYYYMMDD-HHMMSS."""
        csv_content = b"test data"
        batch_id = generate_batch_id(csv_content)
        assert batch_id.startswith("IMP-")
        assert len(batch_id) == 21  # IMP-YYYYMMDD-HHMMSS-HASH8
        
    def test_batch_id_includes_file_hash(self):
        """Batch ID includes 8-char file content hash."""
        csv_content = b"test data"
        batch_id1 = generate_batch_id(csv_content)
        hash_part = batch_id1.split("-")[-1]
        assert len(hash_part) == 8
        assert hash_part.isupper()
        
    def test_different_files_generate_different_hashes(self):
        """Different file contents → different hashes."""
        batch_id1 = generate_batch_id(b"file1 content")
        batch_id2 = generate_batch_id(b"file2 content")
        hash1 = batch_id1.split("-")[-1]
        hash2 = batch_id2.split("-")[-1]
        assert hash1 != hash2
        
    def test_same_file_different_time_generates_different_batch_ids(self):
        """Same file, different timestamp → different batch IDs."""
        csv_content = b"same content"
        # Would require mocking datetime, so mock or use deterministic test
        # This is an integration test concern more than unit test
        pass
```

#### Processor Output Validation

```python
# tests/unit/test_ingestion_csv_validation.py

class TestProcessedCSVValidation:
    def test_missing_validation_tier_column_raises_error(self, temp_dir):
        """CSV without Validation_Tier column → IngestionValidationError."""
        csv_content = "Name,Email\nJohn,john@gmail.com"
        csv_file = temp_dir / "missing_tier.csv"
        csv_file.write_text(csv_content)
        
        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "Validation_Tier" in str(exc.value)
        
    def test_missing_issues_column_raises_error(self, temp_dir):
        """CSV without Issues column → IngestionValidationError."""
        csv_content = "Name,Email,Validation_Tier\nJohn,john@gmail.com,PASS"
        csv_file = temp_dir / "missing_issues.csv"
        csv_file.write_text(csv_content)
        
        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "Issues" in str(exc.value)
        
    def test_missing_suggested_modifications_column_raises_error(self, temp_dir):
        """CSV without Suggested_Modifications column → IngestionValidationError."""
        csv_content = "Name,Email,Validation_Tier,Issues\nJohn,john@gmail.com,PASS,None"
        csv_file = temp_dir / "missing_mods.csv"
        csv_file.write_text(csv_content)
        
        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "Suggested_Modifications" in str(exc.value)
        
    def test_empty_csv_raises_error(self, temp_dir):
        """CSV with only headers (no data rows) → IngestionValidationError."""
        csv_content = "Name,Email,Validation_Tier,Issues,Suggested_Modifications"
        csv_file = temp_dir / "empty.csv"
        csv_file.write_text(csv_content)
        
        with pytest.raises(IngestionValidationError) as exc:
            ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert "zero" in str(exc.value).lower() or "empty" in str(exc.value).lower()
        
    def test_nonexistent_file_raises_error(self):
        """CSV file does not exist → IngestionIOError."""
        with pytest.raises(IngestionIOError):
            ingest_processed_csv("/nonexistent/path.csv", "test.csv", "sqlite:///:memory:")
            
    def test_valid_processed_csv_passes_validation(self, temp_dir):
        """Valid CSV with all required columns passes validation."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,100.00,2026-06-12,PASS,None,"""
        csv_file = temp_dir / "valid.csv"
        csv_file.write_text(csv_content)
        
        result = ingest_processed_csv(str(csv_file), "test.csv", "sqlite:///:memory:")
        assert result.status == 'success'
```

#### Name Splitting

```python
# tests/unit/test_ingestion_name_splitting.py

class TestNameSplitting:
    def test_two_part_name_splits_correctly(self):
        """John Smith → first=John, last=Smith."""
        first, last = split_name("John Smith")
        assert first == "John"
        assert last == "Smith"
        
    def test_three_part_name_splits_as_first_and_rest(self):
        """John Michael Smith → first=John, last=Michael Smith."""
        first, last = split_name("John Michael Smith")
        assert first == "John"
        assert last == "Michael Smith"
        
    def test_suffix_remains_in_last_name(self):
        """John Smith Jr. → first=John, last=Smith Jr."""
        first, last = split_name("John Smith Jr.")
        assert first == "John"
        assert last == "Smith Jr."
        
    def test_single_name_has_no_last_name(self):
        """Prince → first=Prince, last=None."""
        first, last = split_name("Prince")
        assert first == "Prince"
        assert last is None
        
    def test_empty_name_returns_none_none(self):
        """'' → first=None, last=None."""
        first, last = split_name("")
        assert first is None
        assert last is None
        
    def test_whitespace_only_name_returns_none_none(self):
        """'   ' → first=None, last=None."""
        first, last = split_name("   ")
        assert first is None
        assert last is None
```

#### Row Insertion

```python
# tests/unit/test_ingestion_row_insertion.py

class TestRowInsertion:
    def test_raw_row_inserted_exactly_once_per_csv_row(self, temp_db):
        """Each CSV row → exactly one RawImportRow."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John,john@gmail.com,100,2026-06-12,PASS,None,
Jane,jane@gmail.com,200,2026-06-13,PASS,None,"""
        # CSV has 2 data rows
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.raw_row_count == 2
        
        # Verify RawImportRow table
        session = get_session(temp_db)
        rows = session.query(RawImportRow).filter_by(batch_id=result.batch_id).all()
        assert len(rows) == 2
        
    def test_raw_csv_data_preserved_as_json(self, temp_db):
        """RawImportRow.raw_csv_data preserves original row as JSON."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@example.com,100.50,2026-06-12,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        
        session = get_session(temp_db)
        raw_row = session.query(RawImportRow).filter_by(batch_id=result.batch_id).first()
        
        # raw_csv_data should be dict with all original columns
        assert isinstance(raw_row.raw_csv_data, dict)
        assert raw_row.raw_csv_data['Name'] == 'John Smith'
        assert raw_row.raw_csv_data['Email'] == 'john@example.com'
        assert raw_row.raw_csv_data['Amount'] == '100.50'
        
    def test_import_contact_created_per_row(self, temp_db):
        """Each CSV row → exactly one ImportContact."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,100,2026-06-12,PASS,None,
Jane Doe,jane@gmail.com,200,2026-06-13,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.contacts_created == 2
        
        session = get_session(temp_db)
        contacts = session.query(ImportContact).filter_by(batch_id=result.batch_id).all()
        assert len(contacts) == 2
        assert contacts[0].first_name == 'John'
        assert contacts[0].last_name == 'Smith'
```

#### Validation Item Creation

```python
# tests/unit/test_ingestion_validation_items.py

class TestValidationItemCreation:
    def test_pass_row_creates_no_validation_items(self, temp_db):
        """Row with Validation_Tier=PASS → no validation ReviewItems."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,100,2026-06-12,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.validation_items_created == 0
        
    def test_warning_row_creates_validation_items(self, temp_db):
        """Row with Validation_Tier=WARNING → validation ReviewItems."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmai.com,100,2026-06-12,WARNING,Email: Email typo detected,Consider: john@gmail.com"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.validation_items_created >= 1
        
        session = get_session(temp_db)
        items = session.query(ReviewItem).filter(
            ReviewItem.batch_id == result.batch_id,
            ReviewItem.item_type == 'validation'
        ).all()
        assert len(items) >= 1
        assert items[0].status == 'pending'
        assert items[0].confidence == 1.0
        
    def test_fail_row_creates_validation_items(self, temp_db):
        """Row with Validation_Tier=FAIL → validation ReviewItems."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,,100,2026-06-12,FAIL,Email: Email field is empty,Verify email address"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.validation_items_created >= 1
        
    def test_multiple_issues_create_multiple_items(self, temp_db):
        """Row with multiple issues → multiple validation ReviewItems."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmai.com,abc,2026-06-12,FAIL,Email: Email typo detected; Amount: Invalid amount,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        # At least 2 validation items (Email + Amount)
        assert result.validation_items_created >= 2
```

#### Normalization Item Creation

```python
# tests/unit/test_ingestion_normalization_items.py

class TestNormalizationItemCreation:
    def test_pass_row_with_suggestions_creates_normalization_items(self, temp_db):
        """Row with PASS + non-empty Suggested_Modifications → normalization items."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmai.com,100,2026-06-12,PASS,None,Consider: john@gmail.com"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.normalization_items_created >= 1
        
    def test_pass_row_without_suggestions_creates_no_items(self, temp_db):
        """Row with PASS + empty Suggested_Modifications → no normalization items."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,100,2026-06-12,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.normalization_items_created == 0
```

#### Duplicate Item Creation

```python
# tests/unit/test_ingestion_duplicate_items.py

class TestDuplicateItemCreation:
    def test_duplicate_in_issues_creates_duplicate_item(self, temp_db):
        """Row with 'Duplicate:' in Issues → duplicate ReviewItem."""
        csv_content = """Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,5551234567,100,2026-06-12,WARNING,Duplicate: Email match: TXN-002,Review duplicate entries
Jane Doe,jane@gmail.com,5559876543,200,2026-06-13,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.duplicate_items_created >= 1
        
    def test_duplicate_item_has_primary_and_secondary_subjects(self, temp_db):
        """Duplicate item links both primary and secondary contacts."""
        # (Test setup: 2 rows with email match within batch)
        # Verify: ReviewItemSubject exists with both role='primary' and role='secondary'
        pass
        
    def test_within_import_duplicate_detection(self, temp_db):
        """Two rows with same email in same batch → duplicate item created."""
        csv_content = """Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,5551234567,100,2026-06-12,PASS,None,
John Smith 2,john@gmail.com,5551234568,100,2026-06-13,PASS,None,"""
        # Both rows have same email (within-import duplicate)
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        assert result.duplicate_items_created >= 1
```

#### Transaction and Rollback

```python
# tests/unit/test_ingestion_transactions.py

class TestTransactionBehavior:
    def test_successful_ingestion_commits(self, temp_db):
        """Successful ingestion → records committed."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,100,2026-06-12,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        
        # Verify records persist in new session
        session = get_session(temp_db)
        batch = session.query(ImportBatch).filter_by(id=result.batch_id).first()
        assert batch is not None
        
    def test_failed_ingestion_rolls_back(self, temp_db):
        """Failed ingestion (e.g., malformed amount) → rollback, no partial records."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,not_a_number,2026-06-12,FAIL,Amount: Invalid amount,"""
        # Simulating a row parsing error that would cause rollback
        # (Implementation detail: may not raise immediately if lenient parsing)
        # This test depends on implementation choices in Phase 1C-Step 4
        pass
        
    def test_audit_log_created_on_success(self, temp_db):
        """Successful ingestion → AuditLogRecord created."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,100,2026-06-12,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        
        session = get_session(temp_db)
        audit = session.query(AuditLogRecord).filter_by(id=result.audit_log_id).first()
        assert audit is not None
        assert audit.action_type == 'batch_imported'
        assert audit.batch_id == result.batch_id
        
    def test_no_review_decisions_created(self, temp_db):
        """Ingestion creates zero ReviewDecision records."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,100,2026-06-12,PASS,None,"""
        result = ingest_processed_csv(csv_content_path, "test.csv", temp_db)
        
        session = get_session(temp_db)
        decisions = session.query(ReviewDecision).filter_by(batch_id=result.batch_id).all()
        assert len(decisions) == 0
```

---

### 7.2 Integration Tests

#### End-to-End Ingestion

```python
# tests/integration/test_ingestion_e2e.py

class TestIngestionEndToEnd:
    def test_ingest_processed_csv_into_sqlite(self, temp_db):
        """Full ingestion: processed CSV → Option C database."""
        # Setup: Create processed CSV with valid data
        csv_content = """Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,
Jane Doe,jane@gmai.com,5559876543,200.00,2026-06-13,WARNING,Email: Email typo detected,Consider: jane@gmail.com"""
        csv_file = temp_db_dir / "processed.csv"
        csv_file.write_text(csv_content)
        
        # Execute ingestion
        result = ingest_processed_csv(str(csv_file), "original_export.csv", temp_db)
        
        # Verify result
        assert result.status == 'success'
        assert result.raw_row_count == 2
        assert result.contacts_created == 2
        assert result.validation_items_created >= 1  # Jane's email typo
        assert result.household_items_created == 0  # Deferred
        
    def test_imports_route_shows_ingested_batch(self, client_with_database_mode, temp_db):
        """Database mode: /imports shows ingested batch."""
        # First ingest
        # ...then fetch /imports
        # Verify batch appears in response HTML
        pass
        
    def test_dashboard_shows_ingested_data(self, client_with_database_mode, temp_db):
        """Database mode: /dashboard shows ingested records and progress."""
        # Ingest batch with 4 items, 1 decision
        # GET /imports/<batch_id>/dashboard
        # Verify:
        # - batch ID, filename in HTML
        # - record count = 4
        # - progress = 25% (1 of 4 items decided)
        pass
        
    def test_validation_route_shows_validation_items(self, client_with_database_mode, temp_db):
        """Database mode: /validation shows ingested validation items."""
        # Ingest batch with 2 validation items
        # GET /imports/<batch_id>/validation
        # Verify: validation items appear in HTML with issue descriptions
        pass
        
    def test_normalizations_route_shows_normalization_items(self, client_with_database_mode, temp_db):
        """Database mode: /normalizations shows ingested normalization items."""
        pass
        
    def test_duplicates_route_shows_duplicate_items(self, client_with_database_mode, temp_db):
        """Database mode: /duplicates shows ingested duplicate items."""
        pass
        
    def test_households_route_shows_no_items_phase1c(self, client_with_database_mode, temp_db):
        """Database mode: /households shows empty (households deferred to Phase 2)."""
        # Ingest batch (no household items created)
        # GET /imports/<batch_id>/households
        # Verify: empty list or "no households" message
        pass
        
    def test_audit_route_shows_ingestion_event(self, client_with_database_mode, temp_db):
        """Database mode: /audit shows ingestion AuditLogRecord."""
        # Ingest batch
        # GET /imports/<batch_id>/audit
        # Verify: 'batch_imported' action visible with batch info
        pass
        
    def test_exports_route_shows_derived_metrics(self, client_with_database_mode, temp_db):
        """Database mode: /exports shows metrics from ingested data."""
        # (Export console should show counts, no file generation in Phase 1C)
        pass
```

#### Error Conditions

```python
# tests/integration/test_ingestion_errors.py

class TestIngestionErrors:
    def test_malformed_csv_raises_validation_error(self, temp_dir):
        """Completely unparseable CSV → IngestionValidationError."""
        csv_file = temp_dir / "bad.csv"
        csv_file.write_text("not,valid,csv\x00 with \x00 nulls")
        
        with pytest.raises((IngestionValidationError, IngestionIOError)):
            ingest_processed_csv(str(csv_file), "test.csv", ":memory:")
            
    def test_missing_processor_columns_raises_error(self, temp_dir):
        """CSV without processor columns → IngestionValidationError."""
        csv_file = temp_dir / "no_processor.csv"
        csv_file.write_text("Name,Email\nJohn,john@gmail.com")
        
        with pytest.raises(IngestionValidationError):
            ingest_processed_csv(str(csv_file), "test.csv", ":memory:")
            
    def test_database_not_found_raises_error(self, temp_dir):
        """Invalid database URL → IngestionDatabaseError."""
        csv_content = """Name,Email,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John,john@gmail.com,100,2026-06-12,PASS,None,"""
        csv_file = temp_dir / "valid.csv"
        csv_file.write_text(csv_content)
        
        with pytest.raises(IngestionDatabaseError):
            ingest_processed_csv(str(csv_file), "test.csv", "postgresql://nonexistent")
```

---

## 8. Implementation Risks and Blockers

### Risk 1: Processor Duplicate Output Ambiguity

**Risk**: Processor `Issues` column contains "Duplicate: Email match: TXN-002", but if there are multiple contacts with that email, the matched contact cannot be reliably identified.

**Impact**: Duplicate ReviewItem may be created with only primary subject (secondary unidentified).

**Mitigation**:
- Define clear matching strategy: if processor says "TXN-002", query ImportContact by email AND batch_id
- If unique match found: use it; if multiple matches: log warning and use first
- If no match found: create item with only primary subject (reviewer resolves later)
- Phase 2: Consider adding duplicate detection enhancement if needed

### Risk 2: Issues Column Format Inconsistency

**Risk**: Processor `Issues` column format may vary (no guarantee of "field: description" structure). Example: "Name invalid" vs. "Name: Name is empty".

**Impact**: Parsing field names from issues may fail or be unreliable.

**Mitigation**:
- Define lenient parsing: use first part before colon as field name if colon exists
- If no colon: use entire string as issue description, infer field from Validation_Tier context if possible
- Phase 1C: Accept that some issues may be unparseable; store as-is in payload
- Phase 2: Standardize processor output format

### Risk 3: Name Splitting Fragility

**Risk**: Simple split-on-space algorithm fails for international names, suffixes, initials, etc.

**Impact**: Incorrect first/last name split; reviewer must manually correct or names appear wrong in dashboard.

**Mitigation**:
- Phase 1C: Use simple algorithm; accept imperfection
- Normalization ReviewItems can suggest name corrections later
- Phase 2: Implement or integrate library for robust name parsing
- For now: Document limitation in help text; allow reviewers to correct

### Risk 4: Field/Header Mapping Reuse

**Risk**: Processor uses `build_header_mapping()` to find columns. Ingestion needs to do the same. Code must be shared or duplicated.

**Impact**: If header mapping changes, both processor and ingestion must update in sync.

**Mitigation**:
- Extract `build_header_mapping()` into shared utility module (if not already)
- Import and reuse from ingestion service
- Phase 1C-Step 4: Ensure header mapping is consistent

### Risk 5: Database Repository Payload Shape Expectations

**Risk**: Database repository (database_repository.py) expects certain payload_json shapes for ReviewItems. If ingestion creates payloads in a different structure, routes may fail.

**Impact**: Database mode routes (e.g., /validation) may crash if payload structure doesn't match.

**Mitigation**:
- Document expected payload shapes in this contract (done in Section 5)
- Verify with database_repository.py code during implementation
- Add tests to ensure payload shapes match expectations
- Phase 1C-Step 4: Inspect database_repository.py for specific payload access patterns

### Risk 6: Household Route Expectations

**Risk**: `/imports/<id>/households` route expects at least some household ReviewItems to render properly. If Phase 1C defers household items, route returns empty list.

**Impact**: Household page may appear broken or incomplete.

**Mitigation**:
- Check household route template to confirm it handles empty households gracefully
- Recommendation: Update route to show "No household suggestions pending" message
- Document in release notes that household suggestions are deferred to Phase 2
- Phase 1C-Step 4: Verify route handles empty state

### Risk 7: Upload Route Integration

**Risk**: POST /upload route and DonorTrust Householder routes may be in separate Flask apps or modules. Calling ingestion service from upload may require import restructuring.

**Impact**: Circular imports, path issues, or deployment complexity.

**Mitigation**:
- Phase 1C-Step 4 decision: Integrate ingestion into upload route directly OR expose as separate API endpoint
- Prefer: Call ingestion as library (no circular imports)
- Test: Verify import paths and module structure before implementation

### Risk 8: Idempotency and Batch ID Collision

**Risk**: Although timestamp + hash makes collision unlikely, if it happens, retry logic must work correctly.

**Impact**: Upload fails with cryptic error; user doesn't know to retry.

**Mitigation**:
- Implement retry logic with timestamp increment (Phase 1C-Step 4)
- Log collision events for monitoring
- Return user-friendly error message
- Phase 2: Add explicit duplicate-upload detection if needed

### Risk 9: Transaction Scope and Session Management

**Risk**: Database session must be properly created, committed, and closed. If session management is buggy, transactions may leak or records may not persist.

**Impact**: Ingestion appears to succeed but records don't persist; or database connections exhaust.

**Mitigation**:
- Phase 1C-Step 4: Use context managers (with statement) for session lifecycle
- Test: Verify records persist in new session after commit
- Test: Verify failed ingestion leaves no partial records
- Use pytest fixtures for test database isolation

### Risk 10: Large File Handling

**Risk**: Processor loads entire CSV into memory. Large files (100K+ rows) may cause OOM.

**Impact**: Ingestion fails for large batches.

**Mitigation**:
- Phase 1C: Accept memory limitation (document as known constraint)
- Phase 2: Consider streaming/batch processing for large files
- For now: Recommend Givebutter exports are typically <10K rows

---

## 9. Recommendation for Phase 1C-Step 4

### Ready for Implementation: YES ✅

**Conditions Met**:
1. ✅ Ingestion service interface fully specified (function signature, exceptions, transactional semantics)
2. ✅ IngestionResult shape defined (all fields and semantics)
3. ✅ Processor output validation rules documented (required columns, error handling)
4. ✅ Database write contract specified (tables, fields, sources, immutability)
5. ✅ Review item generation rules defined (validation, normalization, duplicate, household deferred)
6. ✅ Idempotency strategy defined (batch ID algorithm, collision handling, transaction semantics)
7. ✅ Test plan detailed (unit tests, integration tests, error conditions)
8. ✅ Implementation risks identified (10 risks with mitigations)

### Key Implementation Decisions Confirmed

| Decision | Value | Rationale |
|----------|-------|-----------|
| Batch ID format | IMP-YYYYMMDD-HHMMSS-<hash8> | Timestamp + hash avoids collision |
| Duplicate scope | Within-import only | Phase 1C scope limitation; cross-import deferred |
| Household items | Deferred to Phase 2 | Requires complex multi-record heuristics |
| FAIL rows | Ingest all | Represent issues as pending items, not rejected |
| Review decisions | Create zero | Future reviewer work only |
| Audit records | One per ingestion | Recorded on successful commit |
| Name splitting | Simple space-based | Imperfect but sufficient; Phase 2 can improve |
| Field mapping | Reuse processor | Consistency; shared utility |
| Session management | Create/close internally | Simplified for Phase 1C |
| Error strategy | Fail fast + report | Validation errors raised early; row-level lenient |

### Blockers: NONE

All identified risks have mitigation strategies. No blocking issues for Phase 1C-Step 4 implementation.

### Deliverables for Phase 1C-Step 4

1. `scripts/householder/ingestion_service.py` with:
   - `ingest_processed_csv()` function
   - `IngestionResult` dataclass
   - Exception classes
   - Helper functions (batch ID generation, name splitting, row processing)

2. `tests/unit/test_ingestion_*.py` with:
   - Unit tests for all functions (batch ID, CSV validation, row insertion, item creation, transactions)

3. `tests/integration/test_ingestion_e2e.py` with:
   - End-to-end ingestion tests
   - Database mode route verification
   - Error condition tests

4. Optional: Refactor processor column mapping into shared utility if needed

5. Optional: Update `/households` route template to handle empty household state

### Success Criteria for Phase 1C-Step 4

- ✅ All unit tests pass
- ✅ All integration tests pass (including database mode routes)
- ✅ 826 existing tests still pass (no regressions)
- ✅ Processed CSV ingests to database without errors
- ✅ Database mode routes show ingested data correctly
- ✅ No write APIs added (read-only preserved)
- ✅ No review decisions created during ingestion
- ✅ Audit log records ingestion event
- ✅ Household route handles deferred items gracefully

---

## Appendix: Test Database Setup (Fixture for Step 4)

### Pytest Fixture Template

```python
@pytest.fixture
def ingestion_test_csv(temp_dir) -> Path:
    """Create a valid processed CSV for ingestion testing."""
    csv_content = """Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmail.com,5551234567,100.00,2026-06-12,PASS,None,
Jane Doe,jane@gmai.com,5559876543,200.00,2026-06-13,WARNING,Email: Email typo detected,Consider: jane@gmail.com
Bob Wilson,,5551111111,150.00,2026-06-14,WARNING,Email: Email field is empty,Verify email
Carol White,carol@gmail.com,555,300.00,2026-06-15,FAIL,Phone: Phone too short; Amount: Amount above range,Use valid phone"""
    
    csv_file = temp_dir / "processed.csv"
    csv_file.write_text(csv_content)
    return csv_file


@pytest.fixture
def ingestion_test_db(temp_dir) -> str:
    """Create isolated test database for ingestion testing."""
    db_path = temp_dir / "test_ingest.db"
    database_url = f"sqlite:///{db_path}"
    
    # Initialize schema
    init_db(database_url)
    
    yield database_url
    
    # Cleanup (optional, tmp_path already cleans up)
```

---

## Document Version

| Version | Date | Author | Content |
|---------|------|--------|---------|
| 1.0 | 2026-06-12 | Claude Code | Initial contract specification: service interface, data shapes, validation rules, database writes, review items, idempotency, test plan, risks, recommendation |

---

## Verification Checklist (Before Phase 1C-Step 4)

- ✅ Service interface defined (function signature, exceptions)
- ✅ IngestionResult shape defined
- ✅ Processor output validation rules documented
- ✅ Database write contract specified (all 7 tables)
- ✅ Review item generation rules detailed (validation, normalization, duplicate, household deferred)
- ✅ Idempotency and transaction strategy defined
- ✅ Test plan detailed (unit + integration)
- ✅ Implementation risks identified and mitigated
- ✅ Recommendation: Ready for Phase 1C-Step 4 implementation
- ⏳ Phase 1C-Step 4: Code implementation

