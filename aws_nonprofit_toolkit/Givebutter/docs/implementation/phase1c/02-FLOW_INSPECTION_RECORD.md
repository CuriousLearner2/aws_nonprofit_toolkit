# Phase 1C-Step 2: Current Upload and Import Flow Inspection Record

**Date**: 2026-06-12  
**Phase**: 1C-Step 2 (Current Flow Inspection)  
**Status**: ✅ COMPLETE & DOCUMENTED (Inspection Only - No Code Implementation)

---

## Executive Summary

This document maps the current Givebutter CSV upload and processor workflow to the Phase 1B2 Option C database schema. It identifies data flow paths, processor outputs, and opportunities for database import ingestion in Phase 1C-Step 3.

**Key Findings**:
1. Processor outputs 3 validation columns: `Validation_Tier`, `Issues`, `Suggested_Modifications`
2. Processor validates and detects duplicates but does NOT persist to database
3. Current flow: upload → process → read CSV → return JSON (no database writes)
4. Option C schema has 7 tables designed to capture processor output and decisions
5. Gaps identified: no mechanism to create review items, no link to raw data storage

---

## 1. Current Upload Flow (POST /upload Route)

**Location**: `scripts/uploader/app.py:148-190`

### Flow Steps:
```
1. Receive uploaded CSV file
   ├─ Validate file format (must be .csv)
   ├─ Generate safe filename: upload_{timestamp}_{filename}
   └─ Save to INTAKE_DIR

2. Run processor
   ├─ Call run_processor(intake_path, processing_path)
   ├─ Input: raw CSV from intake
   └─ Output: processed CSV with validation columns

3. Read processed CSV
   ├─ Load processed CSV from disk
   ├─ Extract counts: record_count, warning_count, fail_count
   └─ Return JSON response

4. Response (no database write)
   ├─ filename
   ├─ record_count
   ├─ warning_count
   ├─ fail_count
   └─ status: 'processed'
```

### Key Code:
```python
@app.route('/upload', methods=['POST'])
def upload():
    # File validation and save to INTAKE_DIR
    file.save(str(intake_path))
    
    # Run processor (processor.process_csv)
    run_processor(str(intake_path), str(processed_path))
    
    # Read processed results
    df = pd.read_csv(processed_path, dtype=str)
    record_count = len(df)
    warning_count = len(df[df['Validation_Tier'] == 'WARNING'])
    fail_count = len(df[df['Validation_Tier'] == 'FAIL'])
    
    # Return JSON (NO DATABASE WRITE)
    return jsonify({
        'filename': safe_name,
        'record_count': record_count,
        'warning_count': warning_count,
        'fail_count': fail_count,
        'status': 'processed'
    })
```

### Files Created:
- `INTAKE_DIR/{upload_timestamp}_{filename}` - Raw uploaded CSV
- `PROCESSING_DIR/{same_name}` - Processed CSV with validation columns

---

## 2. CSV Processor Pipeline

**Location**: `scripts/processor.py`

### Entry Point:
```python
def process_csv(input_file: str, output_file: str) -> None
```

### Processing Steps:
1. Load validation rules from `config/rules/rules_v2.4.json`
2. Load reference list from `config/reference_list.json`
3. Build header mapping (strict + fuzzy matching for column names)
4. Validate each record against 7 validation functions
5. Check for duplicates within the import
6. Assign validation tier (PASS/WARNING/FAIL)
7. Write processed CSV with 3 new columns

### Validation Functions Called Per Record:

| Function | Input | Output | Logic |
|----------|-------|--------|-------|
| `validate_transaction_id()` | CSV | (tier, reason, suggestion) | FAIL if missing transaction_id or date |
| `validate_date()` | CSV | (tier, reason, suggestion) | FAIL if date column missing or empty |
| `validate_email()` | CSV, rules, reference | (tier, reason, suggestion) | FAIL if empty; WARNING for typos (gmai→gmail); suggestions: correct domain |
| `validate_amount()` | CSV, reference | (tier, reason, suggestion) | FAIL if invalid/zero; WARNING if outside range; checks against reference stats |
| `validate_name()` | CSV, reference | (tier, reason, suggestion) | FAIL if missing or wrong length; uses reference patterns |
| `validate_phone()` | CSV, rules | (tier, reason, suggestion) | WARNING if missing/format odd; FAIL if invalid pattern; suggestions: reformatting |
| `validate_address()` | CSV | (tier, reason) | WARNING if incomplete (missing street/city/state) |
| `check_duplicates()` | all_records, CSV, rules | (is_dup, dup_info) | Email/phone/address exact match OR fuzzy name match (default 0.70 threshold) |

### Processor Output Columns (Added to CSV):

| Column | Type | Values | Examples |
|--------|------|--------|----------|
| `Validation_Tier` | String | PASS, WARNING, FAIL | Highest severity from all validations |
| `Issues` | String | Semicolon-separated list | "Email: Email typo detected; Phone: Phone too short" |
| `Suggested_Modifications` | String | Semicolon-separated list | "Consider: john@gmail.com; (555) 123-4567" |

**Rules for Combining Results**:
- FAIL tier: Any field fails → tier=FAIL
- WARNING tier: No failures, any field warnings → tier=WARNING
- PASS tier: All fields pass → tier=PASS
- Suggestions are prioritized: required_suggestions + duplicate_suggestions + address_suggestions + optional_suggestions
- Limited to 5 issues and 5 suggestions per record (for readability)

### Example Processor Output:
```
Name,Email,Phone,Amount,Date,Validation_Tier,Issues,Suggested_Modifications
John Smith,john@gmai.com,(555)123-4567,100.00,2026-05-25,WARNING,Email: Email typo detected,Consider: john@gmail.com
Jane Doe,jane@gmail.com,,500.00,2026-05-25,WARNING,Phone: Phone number is empty,Add phone numbers
```

---

## 3. Processor Tests & Expected Behavior

**Location**: `tests/integration/test_processor_full.py`

### Test Coverage:

| Test | Purpose | Key Assertions |
|------|---------|-----------------|
| `test_process_simple_csv_valid_records` | Basic pipeline | Output exists, has validation columns, row count preserved |
| `test_process_csv_validation_tiers` | Tier assignment | All tiers are PASS/WARNING/FAIL |
| `test_process_csv_with_typos` | Email typo detection | Typo records get WARNING tier, suggestion includes correct email |
| `test_process_csv_with_missing_data` | Missing required fields | Missing data produces FAIL tier records |
| `test_process_csv_preserves_original_columns` | Data preservation | All original columns present in output |

### Expected Behavior:
- All original CSV columns are preserved (only 3 columns added)
- Header mapping handles fuzzy matching for field name variations
- Validation is per-record (one record's failure doesn't affect others)
- Duplicate detection is within-import only (current upload vs. current upload)
- Processor runs successfully on valid Givebutter exports

---

## 4. Fixtures Structure

**Location**: `scripts/uploader/fixtures.py`

### Current Phase 0 Fixture Data:
- `IMPORT_BATCH` - Single batch (IMP-2025-0101-A, 50 records, 42% progress)
- `CONTACTS` - 50 contact records with optional issue_type and issue_description
- `DUPLICATE_CANDIDATES` - Pairs of records marked as potential duplicates
- `NORMALIZATION_SUGGESTIONS` - Field value standardization suggestions
- `HOUSEHOLD_SUGGESTIONS` - Household grouping suggestions
- `AUDIT_LOG_ENTRIES` - Reviewer actions
- `EXPORT_CARDS` - Export console cards
- `IMPORTS_LIST` - List of imports for /imports route
- `QUEUE_STATUS` - Progress counters per queue

**Note**: Fixtures are hardcoded data, not derived from processor output or database.

---

## 5. Database Models (Option C Schema)

**Location**: `scripts/householder/database_models.py`

### Table Structure:

#### ImportBatch (1 per upload)
```
id (PK)                  - String, batch identifier (e.g., IMP-TEST-001)
filename                 - String, original CSV filename
upload_timestamp         - DateTime, when file was uploaded
uploader                 - String (nullable), user who uploaded
status                   - String, batch status (pending, in_review, completed, etc.)
raw_row_count            - Integer, count of raw_import_rows
created_at, updated_at   - DateTime, audit fields
```

#### RawImportRow (1 per CSV row)
```
id (PK)                  - Integer, auto-increment
batch_id (FK)            - String, link to ImportBatch
row_index                - Integer, 0-based position in CSV
raw_csv_data             - JSON, original CSV row as dict
created_at               - DateTime
```

#### ImportContact (1 per CSV row - denormalized snapshot)
```
id (PK)                  - Integer, auto-increment
batch_id (FK)            - String, link to ImportBatch
raw_import_row_id (FK)   - Integer, link to RawImportRow (1:1 relationship)
first_name, last_name    - String (nullable)
email, phone             - String (nullable)
address_line1/2          - String (nullable)
city, state, postal_code - String (nullable)
amount                   - Float (nullable)
created_at               - DateTime
```

#### ReviewItem (1 per suggestion/finding - polymorphic)
```
id (PK)                  - Integer, auto-increment
batch_id (FK)            - String, link to ImportBatch
item_type                - String: validation, normalization, duplicate, household
status                   - String (nullable): pending, approved, rejected, etc.
confidence               - Float (nullable): 0.0-1.0 confidence score
payload_json             - JSON: varies by item_type
created_at               - DateTime
```

#### ReviewItemSubject (N:1 relationship - links items to entities)
```
id (PK)                  - Integer, auto-increment
review_item_id (FK)      - Integer, link to ReviewItem
subject_type             - String: import_contact_snapshot (current); prior_import_row, existing_contact (future)
subject_id               - Integer: ID in subject_type table
role                     - String (nullable): primary, secondary, member, etc.
created_at               - DateTime
```

#### ReviewDecision (1+ per item - append-only audit trail)
```
id (PK)                  - Integer, auto-increment
batch_id (FK)            - String, link to ImportBatch
review_item_id (FK)      - Integer, link to ReviewItem
decision                 - String: accept, reject, same_person, different_person, defer, confirmed
reviewed_values          - JSON (nullable): data used for decision
reviewer                 - String (nullable): reviewer name
created_at               - DateTime
```

#### AuditLogRecord (1+ per action - immutable action log)
```
id (PK)                  - Integer, auto-increment
batch_id (FK)            - String, link to ImportBatch
action_type              - String: item_created, decision_recorded, batch_imported, etc.
action_timestamp         - DateTime, when action occurred
actor                    - String (nullable): user who performed action
item_id (FK, nullable)   - Integer, related ReviewItem (if applicable)
decision_id (FK, nullable) - Integer, related ReviewDecision (if applicable)
details                  - JSON (nullable): action-specific details
created_at               - DateTime
```

---

## 6. Processor Output → Option C Schema Mapping

### Current State (No Integration):
The processor outputs validation columns but **does not create database records**.

### Proposed Mapping for Phase 1C:

#### Step 1: Create ImportBatch Record
```
ImportBatch:
  id = generate_id(filename, upload_timestamp)
  filename = original filename
  upload_timestamp = current datetime
  uploader = current user (or from upload context)
  status = 'pending'  # Will be updated as processing progresses
  raw_row_count = len(df)
```

#### Step 2: Create RawImportRow Records (1 per CSV row)
```
For each row in processed CSV:
  RawImportRow:
    batch_id = ImportBatch.id
    row_index = row number (0-based)
    raw_csv_data = original CSV row as JSON dict
```

#### Step 3: Create ImportContact Records (Denormalized Snapshots)
```
For each row in processed CSV:
  ImportContact:
    batch_id = ImportBatch.id
    raw_import_row_id = RawImportRow.id
    first_name = extract from 'Name' column (split)
    last_name = extract from 'Name' column (split)
    email = 'Email' column
    phone = 'Phone' column
    address_line1 = 'Address 1' column
    address_line2 = 'Address 2' column
    city = 'City' column
    state = 'State' column
    postal_code = 'Zip' column
    amount = 'Amount' column (parsed as float)
```

#### Step 4: Create ReviewItem Records (Suggestions)

**For each record with Validation_Tier != PASS:**

**Validation Issues** (item_type='validation'):
```
ReviewItem:
  batch_id = ImportBatch.id
  item_type = 'validation'
  status = 'pending'
  confidence = null (or 1.0 for definite issues)
  payload_json = {
    "field": "field name",
    "issue": "issue description from Issues column",
    "suggestion": "suggestion if available"
  }
ReviewItemSubject:
  review_item_id = ReviewItem.id
  subject_type = 'import_contact_snapshot'
  subject_id = ImportContact.id
  role = 'primary'
```

**Duplicate Detection** (item_type='duplicate'):
```
For "Duplicate: ..." entries in Issues column:
ReviewItem:
  batch_id = ImportBatch.id
  item_type = 'duplicate'
  status = 'pending'
  confidence = null (or estimated from match evidence)
  payload_json = {
    "match_type": "email" | "phone" | "address" | "name_fuzzy",
    "evidence": ["email match", "phone match", ...],
    "conflicts": []
  }
ReviewItemSubject (primary):
  review_item_id = ReviewItem.id
  subject_type = 'import_contact_snapshot'
  subject_id = ImportContact.id (current record)
  role = 'primary'
ReviewItemSubject (secondary):
  review_item_id = ReviewItem.id
  subject_type = 'import_contact_snapshot'
  subject_id = ImportContact.id (matched record)
  role = 'secondary'
```

**Normalization Suggestions** (item_type='normalization'):
```
For "Suggested_Modifications" entries related to field standardization:
ReviewItem:
  batch_id = ImportBatch.id
  item_type = 'normalization'
  status = 'pending'
  confidence = 0.85 (processor default)
  payload_json = {
    "field_name": "field",
    "raw_value": current value,
    "normalized_value": suggestion,
    "basis": "phone format", "email domain typo", etc.,
    "confidence": 0.85
  }
ReviewItemSubject:
  review_item_id = ReviewItem.id
  subject_type = 'import_contact_snapshot'
  subject_id = ImportContact.id
  role = 'primary'
```

**Household Suggestions** (item_type='household'):
```
# Phase 1C: Not yet implemented (requires multi-record grouping logic)
# Processor outputs: None (address incomplete warnings are validation, not household suggestions)
# Phase 2+: Will create household items based on address/name matching
```

#### Step 5: Create AuditLogRecord
```
AuditLogRecord:
  batch_id = ImportBatch.id
  action_type = 'batch_imported'
  action_timestamp = import completion time
  actor = 'system' or uploader name
  details = {
    "source": "givebutter_export",
    "filename": original filename,
    "record_count": count,
    "validation_summary": {
      "PASS": count,
      "WARNING": count,
      "FAIL": count
    }
  }
```

---

## 7. Gaps and Ambiguities Identified

### Critical Gaps:

1. **Batch ID Generation**
   - Current: No batch ID in processor output
   - Needed: Scheme for generating IMP-YYYY-MMDD-RANDOM
   - Question: Should batch ID be human-readable timestamp or auto-increment?

2. **Name Splitting**
   - Current: Processor receives 'Name' column (full name)
   - Needed: Logic to split "John Smith" → first_name="John", last_name="Smith"
   - Edge cases: "John Michael Smith", "Sr.", "Jr.", non-English names
   - Question: Use simple split() or external name parser library?

3. **Duplicate Detection Scope**
   - Current processor: Checks duplicates WITHIN current import only
   - Future need (Phase 2): Check against PRIOR imports and existing contacts
   - Gap: No mechanism to query prior imports or existing contacts yet
   - Question: Should Phase 1C implement cross-import dedup or only within-import?

4. **Household Grouping**
   - Current processor: No household detection logic
   - Needed: Logic to group records by address or other criteria
   - Phase 1B guards prohibit "automatic actions" (auto-merge)
   - Gap: Household suggestions require manual reviewer decision
   - Question: Should Phase 1C create household items or defer to Phase 2?

5. **Normalization vs. Validation**
   - Current processor: Mixes warnings (missing data) with suggestions (format improvements)
   - Needed: Clearer distinction between validation failures and improvement suggestions
   - Gap: Email typo suggestions are in Issues column, not a separate field
   - Question: Should Phase 1C refactor processor output format?

6. **Raw Data Persistence**
   - Current: Processed CSV saved to disk but no canonical raw data store
   - Needed: Long-term storage of raw CSV data for audit trail
   - Gap: RawImportRow stores as JSON, but where is original CSV file stored?
   - Question: Should INTAKE_DIR/PROCESSING_DIR be retained or archived?

7. **Uploader Identity**
   - Current: No uploader tracking (POST /upload has no auth context)
   - Needed: User/service identity for audit log
   - Gap: ImportBatch.uploader is nullable, filled at import time
   - Question: Will Phase 1C add auth context or use 'system' as default?

8. **Validation Confidence Scores**
   - Current processor: No confidence scores (only tier pass/fail)
   - Needed: Confidence scores for duplicate and normalization items
   - Gap: ReviewItem.confidence exists but processor doesn't populate
   - Question: Should Phase 1C estimate confidence based on match quality?

9. **Decision Values**
   - Current: ReviewDecision.decision has enum-like values (accept, reject, same_person, confirmed, etc.)
   - Gap: Not clear which decisions apply to which item_types
   - Validation items: accept/reject?
   - Duplicate items: same_person/different_person?
   - Normalization items: accept/reject?
   - Household items: confirmed/rejected?
   - Question: Should Phase 1C define decision type mapping?

10. **Progress Calculation**
    - Current: list_imports() calculates progress as (decisions / items) * 100
    - Gap: Doesn't account for item priority (validation failures should block, but don't)
    - Question: Should Phase 1C track progress differently (% of PASS records vs. % of decisions)?

---

## 8. Current Flow Data Summary

### Input (Givebutter CSV):
- Columns: Transaction ID, Date, Name, Email, Phone, Address, City, State, Zip, Amount, Campaign, etc.
- Format: Standard CSV with Givebutter column names (case-sensitive)
- Headers supported: Exact names (CORE_HEADERS) + fuzzy fallbacks (FUZZY_HEADERS)

### Processing Output (CSV with 3 new columns):
- All original columns preserved
- `Validation_Tier`: PASS, WARNING, or FAIL
- `Issues`: Semicolon-separated list of validation issues found
- `Suggested_Modifications`: Semicolon-separated list of recommended changes

### Validations Applied:
- **Required fields**: Transaction ID, Date, Email, Amount, Name
- **Optional fields**: Phone, Address
- **Validation rules**: Pattern matching, format validation, reference list checking
- **Duplicate detection**: Email/phone/address exact match + fuzzy name matching (0.70 threshold)
- **Suggestions**: Email typo correction, phone formatting, domain validation

### No Database Write:
- Current: Upload endpoint returns JSON, no database state change
- Processing artifacts: Raw CSV (INTAKE_DIR) and processed CSV (PROCESSING_DIR) written to disk only
- No review items, decisions, or audit records created

---

## 9. Verification: Current Test State

**Status**: All Phase 1B2 tests passing (826 tests)

```bash
pytest tests/unit tests/integration -q
Result: 826 tests passed
```

**No changes to existing flow made in this step.**

---

## 10. Recommendations for Phase 1C-Step 3

### High Priority:
1. **Define batch ID generation** - Choose scheme (IMPYYMMDD-HASH or sequential)
2. **Define name splitting logic** - Handle edge cases for first/last name extraction
3. **Decide duplicate detection scope** - Phase 1C: within-import only or include prior?
4. **Clarify decision type mapping** - Which decisions apply to which item types?

### Medium Priority:
5. **Establish raw data storage** - Where/how to persist original CSV files?
6. **Add uploader identity** - Capture user context for audit trail
7. **Estimate confidence scores** - Add confidence to duplicate and normalization items

### Lower Priority (Consider for Phase 2):
8. **Implement household grouping** - Requires multi-record logic beyond Phase 1C scope
9. **Cross-import duplicate detection** - Requires archive querying
10. **Progress calculation refinement** - Currently (decisions/items); could be (PASS records/total)

---

## 11. Next Steps

**Phase 1C-Step 3 (When Requested)**: Implement Database Import Ingestion
- Create database write layer to transform processor output → Option C tables
- Implement atomic transaction for batch import
- Add ingestion API endpoint (or integrate with /upload)
- Create integration tests verifying processor → database flow
- Maintain all Phase 1B guardrails (read-only routes, no write APIs, etc.)

---

## Appendix: File References

| File | Purpose | Key Content |
|------|---------|-------------|
| `scripts/uploader/app.py:148-190` | Upload endpoint | POST /upload route implementation |
| `scripts/processor.py` | CSV validation | process_csv entry point, validation functions, duplicate detection |
| `scripts/processor.py:591-782` | Main processor | Record validation loop, tier assignment, output writing |
| `scripts/householder/database_models.py` | Schema | 7 SQLAlchemy table definitions |
| `scripts/householder/database_repository.py` | Read layer | DatabaseImportRepository (read-only) |
| `tests/integration/test_processor_full.py` | Processor tests | 5 integration tests validating processor behavior |
| `scripts/uploader/fixtures.py` | Phase 0 data | Hardcoded fixture data for prototype |
| `config/rules/rules_v2.4.json` | Validation config | Email typos, invalid patterns, reference data |
| `config/reference_list.json` | Reference data | Amount ranges, domain lists, name patterns |

---

## Inspection Completion

**Inspected By**: Claude Code  
**Date**: 2026-06-12  
**Status**: ✅ Complete - Documented current flow, identified 10 key gaps, ready for Phase 1C-Step 3

**No code changes in this step. Documentation only.**

---

## Document Versioning

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-12 | Claude Code | Initial inspection: current flow mapping, processor analysis, schema mapping, gaps identified |

