# Phase 1C-Step 1: Database Import Ingestion Planning Report

**Date**: 2026-06-12  
**Phase**: 1C (Database Import Ingestion)  
**Status**: PLANNING (No Implementation Yet)

---

## 1. Current Upload/Import Flow Summary

### Existing Upload Route
**Route**: `POST /upload` (scripts/uploader/app.py:148)

**Current flow**:
1. User uploads CSV file via form
2. File saved to `INTAKE_DIR` with timestamp-prefixed name
3. `run_processor()` called to validate and process file
4. Processed file written to `PROCESSING_DIR`
5. Route returns counts: record_count, warning_count, fail_count
6. Returns JSON response with status 'processed'

### Existing Processing Logic
**Processor**: `scripts/processor.py`

**Processor responsibilities**:
- Reads Givebutter CSV export (exact column names from Givebutter)
- Maps core headers (transaction_id, name, email, phone, address, amount, date, campaign, etc.)
- Validates records against rules (rules_v2.4.json)
- Validates dates, emails, phone numbers, amounts, addresses
- Checks reference list for known invalid values
- Detects duplicates using SequenceMatcher fuzzy matching
- Assigns validation tier (PASS, WARNING, FAIL)
- Identifies issues: missing-required, format-invalid, etc.
- Outputs processed CSV with validation results

**Output columns** (in processed CSV):
- Original Givebutter columns
- Validation_Tier (PASS, WARNING, FAIL)
- Issues (validation issues found)
- Suggested_Modifications (normalization suggestions)
- Operator_Decision (empty initially, filled by reviewer)
- Operator_Notes (empty initially, filled by reviewer)

### Current Fixture-Based Behavior
**Fixtures location**: `scripts/uploader/fixtures.py`

**Fixture structure**:
- IMPORTS_LIST: list of import batches
- IMPORT_BATCH: single batch details (id, filename, record_count, status, progress)
- CONTACTS: list of donor contacts
- VALIDATION_SUGGESTIONS: list of validation issues
- NORMALIZATION_SUGGESTIONS: suggested field cleanups
- HOUSEHOLD_SUGGESTIONS: potential household groupings
- DUPLICATE_CANDIDATES: potential duplicate pairs
- AUDIT_LOG_ENTRIES: audit trail entries
- EXPORT_CARDS: export definition cards

### Current Service Boundaries
**Services** (all read-only, fixture-backed):
- `import_service.get_imports()`: returns list of import batches
- `dashboard_service.get_import_dashboard()`: returns batch details + queue counts
- `validation_service.get_validation_review()`: returns validation issues
- `normalizations_service.get_normalizations_review()`: returns normalization suggestions
- `households_service.get_households_review()`: returns household suggestions
- `duplicates_service.get_duplicates_review()`: returns duplicate candidates
- `audit_service.get_audit_log()`: returns audit entries
- `exports_service.get_export_console()`: returns export options

**All services**:
- Accept optional `config` parameter for database selection
- Use repository_provider to select FixtureImportRepository (default) or DatabaseImportRepository
- Return template-ready view models (to_template_dict())
- Make NO database writes

### Current Tests
**Upload/processor tests**:
- `tests/integration/test_processor_full.py`: End-to-end processor tests

**Route tests**:
- `tests/integration/test_dashboard_route.py`: Dashboard route tests
- `tests/integration/test_validation_route.py`: Validation route tests
- `tests/integration/test_audit_route.py`: Audit route tests
- `tests/integration/test_exports_route.py`: Exports route tests
- `tests/integration/test_households_route.py`: Households route tests
- `tests/integration/test_normalizations_route.py`: Normalizations route tests
- Similar for duplicates, import service

**Database-mode tests**:
- `tests/integration/test_database_mode_routes.py`: 8 route integration tests with database-seeded data

### Existing Database Schema
**Schema location**: `scripts/householder/database_models.py`

**Option C tables** (accepted):
- `import_batches`: batch metadata (id, filename, upload_timestamp, uploader, status, raw_row_count)
- `raw_import_rows`: immutable raw CSV row data (batch_id, row_index, raw_csv_data as JSON)
- `import_contacts`: denormalized contact snapshots (batch_id, raw_import_row_id, first_name, last_name, email, phone, address_*, amount)
- `review_items`: polymorphic review items (batch_id, item_type, status, confidence, payload_json)
- `review_item_subjects`: links review items to contacts (review_item_id, subject_type, subject_id, role)
- `review_decisions`: reviewer decisions (batch_id, review_item_id, decision, reviewer, created_at)
- `audit_log`: audit trail (batch_id, action_type, action_timestamp, actor, item_id, decision_id, details)

**ORM models**:
- SQLAlchemy declarative models
- All tables append-only (immutable after creation except review_decisions which accumulates)
- Alembic migrations (already initialized)

### Existing Database Helpers
**Database initialization**:
- `init_db(database_url)`: Create all tables from models
- `create_db_engine(database_url)`: Create SQLAlchemy engine
- `get_session(engine)`: Get new database session

**Alembic**:
- Migration system set up
- One migration exists: `a9d993964dd4_update_schema_polymorphic_review_items_.py`
- Ready for new migrations

---

## 2. Proposed Phase 1C Scope

### Primary Goal
**Move from file-based processing to database-backed import ingestion while preserving all v1 guardrails.**

### What Phase 1C Will Deliver

1. **CSV parsing → database ingestion flow**
   - Reuse existing processor for validation logic
   - Ingest validated rows into database instead of file system
   - Create import batch record
   - Store raw rows immutably

2. **Import contact snapshot creation**
   - Denormalize contact data from raw rows
   - Create ImportContact records for query efficiency
   - Separate from review decisions (immutable snapshots)

3. **Pending suggestion generation**
   - Validation review items for detected validation issues
   - Normalization review items for field standardization
   - Duplicate review items for candidate pairs
   - Household review items for potential groupings
   - All created as PENDING (require reviewer action)

4. **Route/read-model compatibility**
   - Verify all 8 canonical routes still work after ingestion
   - Database-backed data replaces fixture data
   - Templates render unchanged

5. **Audit trail integration**
   - Record ingestion event in audit_log
   - Track import source, row count, processing results
   - Timestamp and actor attribution

### What Phase 1C Will NOT Include

**Explicitly excluded**:
- Reviewer write APIs (approve, reject, decide)
- Merge/combine contact APIs
- Household confirmation APIs
- Auto-approval mechanisms
- Export file generation
- Givebutter/CRM writeback
- Cross-import matching
- Global person identity
- Lifetime giving tracking
- Production deployment changes (unless already required for testing)

---

## 3. Proposed Ingestion Architecture

### High-Level Flow

```
CSV Upload
    ↓
Save to INTAKE_DIR
    ↓
Run Processor (existing logic)
    ├─ Validate CSV structure
    ├─ Validate field formats
    ├─ Detect duplicates within batch
    ├─ Identify normalizable fields
    └─ Mark validation issues
    ↓
Processor Output (processed CSV)
    ↓
Ingest Flow (NEW - Phase 1C)
    ├─ Create ImportBatch record
    ├─ Parse processed CSV
    ├─ Insert RawImportRows (immutable, one per row)
    ├─ Create ImportContact snapshots (denormalized)
    ├─ Generate ValidationReviewItems (from Issues column)
    ├─ Generate NormalizationReviewItems (from Suggested_Modifications)
    ├─ Generate DuplicateReviewItems (from processor duplicate detection)
    ├─ Generate HouseholdReviewItems (from address/name heuristics)
    ├─ Create ReviewItemSubjects (link items to contacts)
    └─ Record AuditLog entry
    ↓
Database State
    └─ Ready for route queries (read-only)
```

### Responsibility Boundaries

| Responsibility | Who | When | Idempotent |
|---|---|---|---|
| **CSV validation** | Processor | Upload | Yes (reruns okay) |
| **Raw row storage** | IngestionService | After processor | No (must not duplicate) |
| **Contact snapshots** | IngestionService | After processor | Yes (derived from raw rows) |
| **Validation items** | IngestionService | After processor | Yes (derived from Issues) |
| **Normalization items** | IngestionService | After processor | Yes (derived from Suggested_Modifications) |
| **Duplicate items** | IngestionService | After processor | Yes (derived from processor duplicates) |
| **Household items** | IngestionService | After processor | Yes (address/name heuristics) |
| **Reviewer decisions** | ReviewerAPI (future) | Manual | N/A |
| **Audit logging** | IngestionService | After ingestion | Yes (timestamp-based dedup) |

### Service Responsibilities

**IngestionService** (new):
```python
def ingest_import(processed_csv_path: str, uploader: str) -> ImportBatch:
    """
    Ingest processed CSV into database.
    
    Steps:
    1. Create ImportBatch record
    2. Parse CSV and insert RawImportRows
    3. Create ImportContact snapshots
    4. Generate review items
    5. Create review item subjects
    6. Record audit entry
    7. Return ImportBatch record
    """
```

**ProcessorService** (existing, unchanged):
- Already validates and processes CSV
- Outputs processed CSV with Issues, Suggested_Modifications columns
- No database access needed

---

## 4. Proposed Database Write Boundaries

### What Gets Written

1. **import_batches**: One record per upload
   - id: Generated (e.g., IMP-2026-0612-A)
   - filename: From upload
   - upload_timestamp: Now
   - uploader: From request context
   - status: 'pending_review' (default for Phase 1)
   - raw_row_count: Count of rows ingested

2. **raw_import_rows**: One per CSV row (immutable)
   - batch_id: FK to ImportBatch
   - row_index: Position in CSV
   - raw_csv_data: JSON copy of entire row (all columns)
   - created_at: Timestamp

3. **import_contacts**: One per CSV row (snapshot)
   - batch_id: FK to ImportBatch
   - raw_import_row_id: FK to RawImportRow
   - first_name, last_name, email, phone, address_* (parsed from raw)
   - created_at: Timestamp

4. **review_items**: Multiple per batch (pending suggestions)
   - batch_id: FK to ImportBatch
   - item_type: 'validation', 'normalization', 'duplicate', 'household'
   - status: 'pending' (always)
   - confidence: 0-1 score (from processor or heuristics)
   - payload_json: Type-specific data
   - created_at: Timestamp

5. **review_item_subjects**: Multiple per review item (linking)
   - review_item_id: FK to ReviewItem
   - subject_type: 'import_contact_snapshot'
   - subject_id: FK to ImportContact
   - role: 'primary', 'secondary', etc.
   - created_at: Timestamp

6. **audit_log**: One per ingestion
   - batch_id: FK to ImportBatch
   - action_type: 'batch_imported'
   - action_timestamp: When ingestion completed
   - actor: 'system' or uploader username
   - details: {'rows_ingested': N, 'validations': M, ...}
   - created_at: Timestamp

### What Does NOT Get Written

- ❌ ReviewDecision records (only created by reviewer action)
- ❌ Givebutter API calls
- ❌ External system updates
- ❌ Mutations to raw_import_rows after creation
- ❌ Mutations to import_contacts after creation
- ❌ Auto-approval of any review items

### Safety Guarantees

- All writes within single transaction
- Raw rows are immutable (append-only)
- Contact snapshots are immutable (derived only)
- Review items start as PENDING (no auto-approval)
- Audit trail records ingestion event
- No external side effects

---

## 5. Proposed Suggestion-Generation Boundaries

### Validation Review Items
**Generated when**: CSV validation detects issues

**Item creation**:
- item_type: 'validation'
- payload_json: {field: 'X', issue: 'missing', description: '...'}
- status: 'pending'
- confidence: 1.0 (deterministic)

**Review subjects**: All rows with the issue

**Reviewer action**: Manual review + decision

### Normalization Review Items
**Generated when**: Field needs standardization

**Item creation**:
- item_type: 'normalization'
- payload_json: {field: 'email', raw: 'X', suggested: 'Y', reason: 'format'}
- status: 'pending'
- confidence: 0.9

**Review subjects**: Contacts affected by normalization

**Reviewer action**: Accept/reject normalization (future API)

### Duplicate Review Items
**Generated when**: Processor detects potential duplicates

**Item creation**:
- item_type: 'duplicate'
- payload_json: {pair: [contact_A_id, contact_B_id], evidence: ['same_name', 'same_address']}
- status: 'pending'
- confidence: 0.85 (SequenceMatcher score)

**Review subjects**: Both contacts in potential pair

**Reviewer action**: Mark as same/different person (future API)

### Household Review Items
**Generated when**: Heuristics suggest household grouping

**Item creation**:
- item_type: 'household'
- payload_json: {suggested_label: 'Smith family', members: [ids], basis: 'same_address'}
- status: 'pending'
- confidence: 0.8 (address match + name similarity)

**Review subjects**: All members of potential household

**Reviewer action**: Confirm/reject household grouping (future API)

### Key Property
**All review items start as PENDING**. No item is marked as accepted/rejected/confirmed at ingestion time. Reviewer decisions always happen later, explicitly, and are recorded in review_decisions.

---

## 6. Idempotency & Safety Strategy

### Idempotent Operations

**Question**: What if the same file is uploaded twice?

**Answer**: Safe, deterministic behavior:
1. Import batch ID is deterministic (derived from filename + timestamp)
2. If exact same filename uploaded within same second: batch ID collision
3. Solution: Batch ID must be unique or timestamp-precise enough
4. Recommendation: Include hash of file contents in batch ID

**Example**:
```
IMP-{YYYY}{MM}{DD}-{HH}{MM}{SS}-{FILE_HASH_PREFIX}
```

### Raw Row Immutability

**Guarantee**: Raw rows are never updated, only inserted

**Mechanism**:
- Store entire row as JSON in raw_csv_data
- No UPDATE statement ever issued on raw_import_rows
- Index on (batch_id, row_index) for query efficiency

**Benefit**: Audit trail always reflects original data

### Partial Ingestion Failures

**Strategy**: Transactional atomicity

**Behavior**:
- All writes in single transaction
- If any step fails: entire transaction rolls back
- Retry is safe (no partial state)
- Audit log only created if ingestion succeeds

**Error handling**:
1. Parse processor output
2. Validate row count matches
3. Check for duplicate batch_id
4. Begin transaction
5. Create import batch
6. Insert raw rows (bulk)
7. Create contacts (derived)
8. Generate review items
9. Create subjects
10. Commit or rollback

### Ingestion is Transactional

**Yes**: All steps within single database transaction

**Benefit**: No orphaned records if failure occurs

### Audit Log Recording

**When**: After successful ingestion

**What's recorded**:
```json
{
  "action_type": "batch_imported",
  "actor": "system",
  "details": {
    "filename": "upload_20260612_120000_donors.csv",
    "rows_ingested": 5,
    "validation_issues": 2,
    "normalization_suggestions": 3,
    "duplicate_candidates": 1,
    "household_suggestions": 2
  }
}
```

### No Accidental External Writes

**Guarantee**: No Givebutter API calls, no external systems modified

**Mechanism**:
- IngestionService only accesses database
- No HTTP clients or external APIs
- All logic deterministic and internal

---

## 7. Test Strategy

### Unit Tests

**Ingestion Service Tests**:
- `test_import_batch_created_correctly`: Batch record has expected fields
- `test_raw_rows_stored_immutably`: Raw rows match processor output, one per row
- `test_raw_rows_never_updated`: Verify no UPDATE statements
- `test_import_contacts_created`: Denormalized contacts have correct fields
- `test_import_contacts_parsed_correctly`: Address and name parsing
- `test_validation_items_generated`: One item per detected issue
- `test_normalization_items_generated`: One item per suggested field
- `test_duplicate_items_generated`: Items created from processor duplicates
- `test_household_items_generated`: Items created from address/name heuristics
- `test_review_item_subjects_linked`: Subjects link items to contacts correctly
- `test_no_review_decisions_created_automatically`: ReviewDecision records not created at ingestion
- `test_audit_log_records_ingestion`: Audit log entry created with correct details
- `test_ingestion_is_transactional`: Rollback works on failure
- `test_malformed_csv_handling`: Graceful error messages for invalid CSV
- `test_missing_required_columns_rejected`: CSV validation before ingestion

### Integration Tests

**Route Tests After Ingestion**:
- `test_imports_list_shows_ingested_batch`: `/imports` shows newly ingested batch
- `test_dashboard_shows_ingested_counts`: `/dashboard` shows correct queue counts
- `test_validation_shows_generated_items`: `/validation` shows validation review items
- `test_normalizations_shows_generated_items`: `/normalizations` shows normalization items
- `test_duplicates_shows_generated_candidates`: `/duplicates` shows duplicate candidates
- `test_households_shows_generated_suggestions`: `/households` shows household suggestions
- `test_audit_log_shows_ingestion_entry`: `/audit` shows ingestion event

**Idempotency Tests**:
- `test_duplicate_file_upload_rejected`: Same filename twice → error or skip
- `test_repeated_ingest_fails_gracefully`: Retry same file → appropriate error

**Safety Tests**:
- `test_no_givebutter_api_calls`: Mock/verify no external API calls
- `test_no_auto_approval`: Generated items have status=pending
- `test_raw_rows_immutable`: Database constraints prevent updates

### Test Data Strategy

**Fixture CSV files**:
- `fixtures/donors_q1_2025.csv`: Valid 5-row file (all PASS)
- `fixtures/donors_mixed_validation.csv`: Mixed PASS/WARNING/FAIL
- `fixtures/donors_with_duplicates.csv`: Intentional duplicates for testing
- `fixtures/donors_malformed.csv`: Invalid CSV format

**Expected outcomes**:
- Valid file: all rows ingested, minimal review items
- Mixed file: rows ingested, validation items created
- Duplicates file: duplicate review items created
- Malformed file: rejected with clear error

---

## 8. Explicit Non-Goals

**Phase 1C will NOT include**:

1. ❌ Reviewer approval/rejection APIs
   - ReviewDecision records are not created during ingestion
   - Reviewer APIs (POST, PUT, DELETE) will come in Phase 2

2. ❌ Automatic actions
   - No auto-approval of validation issues
   - No auto-merge of duplicates
   - No automatic household confirmation
   - All actions require explicit reviewer decision

3. ❌ Export file generation
   - Export console remains read-only metadata
   - File generation deferred to Phase 2 (if needed)

4. ❌ Givebutter/CRM writeback
   - No API calls to Givebutter
   - No synchronization with external systems
   - One-way import only

5. ❌ Cross-import operations
   - Only current import considered for suggestions
   - No linking to prior imports
   - No cross-batch dedup or household inference

6. ❌ Global person identity
   - No global "person" concept
   - Each import is independent
   - Contacts linked only within batch

7. ❌ Lifetime giving tracking
   - Total giving, frequency, etc. deferred
   - Read-model statistics only (if at all)

8. ❌ Production deployment changes
   - Local testing only (Phase 1)
   - Deployment strategy deferred to later phase

9. ❌ Route/template changes
   - Upload route remains same interface
   - Routes continue using repository_provider (now backed by database)
   - Templates unchanged

10. ❌ UI changes
    - Upload form remains unchanged
    - Results display remains unchanged
    - No new UX flows

---

## 9. Risks & Open Questions

### Risk 1: Givebutter CSV Format Changes
**Risk**: Column names, formats, or structure may vary

**Current assumption**: Processor knows Givebutter column names (from CORE_HEADERS, FUZZY_HEADERS)

**Mitigation**: Processor already handles variations. IngestionService assumes processor output is correct.

**Question**: Should we validate processor output structure before ingestion?

**Recommendation**: Add schema validation for processor output before database write.

---

### Risk 2: Duplicate Detection Thresholds
**Risk**: SequenceMatcher score thresholds may be arbitrary

**Current**: Processor uses SequenceMatcher.ratio() for duplicate detection

**Open question**: What is the confidence threshold for creating duplicate review items?
- 0.85 (very confident)
- 0.75 (confident)
- 0.60 (suggest for review)

**Recommendation**: Make threshold configurable, default to 0.75

---

### Risk 3: Household Inference Heuristics
**Risk**: Address/name matching may be too naive or too aggressive

**Current**: Processor detects duplicates via fuzzy match

**Open question**: What rules should generate household review items?
- Exact address match + last name match
- Exact address match + any name overlap
- City/state match + same last name
- Phone number match

**Recommendation**: Start with "exact address + same last name", collect feedback

---

### Risk 4: Import Batch ID Generation
**Risk**: Collision or non-uniqueness if same file uploaded twice

**Current proposal**: Deterministic from filename + timestamp + hash

**Question**: What if two files have same name and are uploaded in same second?

**Recommendation**: Use timestamp + file hash to guarantee uniqueness

```python
import hashlib
batch_id = f"IMP-{date}-{time}-{file_hash[:8]}"
```

---

### Risk 5: CSV Column Name Variations
**Risk**: Processor may fail if Givebutter changes column names

**Current**: FUZZY_HEADERS provides fallbacks

**Question**: Should IngestionService validate all required columns?

**Recommendation**: Yes, validate processor output before ingestion

---

### Risk 6: Partial Row Data
**Risk**: Some fields may be missing or malformed

**Current**: Processor marks as WARNING/FAIL

**Question**: Do we ingest FAIL rows, or reject them?

**Recommendation**: Ingest all rows (PASS/WARNING/FAIL), create validation review items for issues

---

### Risk 7: Transaction Rollback Visibility
**Risk**: If ingestion fails midway, user sees no import

**Current**: Return error to user

**Question**: Should we create a "failed" import batch for audit trail?

**Recommendation**: No. Clean up failed transactions. Only create audit log entry on success.

---

### Risk 8: Audit Log Actor Attribution
**Risk**: "system" vs actual uploader username

**Current proposal**: Record actor as "system" for Phase 1

**Question**: Should we get username from Flask session/request context?

**Recommendation**: For Phase 1, use "system". Phase 2 can add user context.

---

### Risk 9: Reviewer's Trust in Suggestions
**Risk**: Incorrectly generated suggestions undermine credibility

**Current**: Generate suggestions based on processor logic

**Question**: Should we have human review of suggestion rules before launch?

**Recommendation**: Yes, design review of suggestion generation before Phase 1C-Step 3

---

### Risk 10: Database Connection Availability
**Risk**: Ingestion fails if database unavailable

**Current**: Fixture mode continues to work

**Question**: Should ingestion gracefully fall back to fixtures?

**Recommendation**: No. Fail clearly if database unavailable. Phase 1C is database mode.

---

## 10. Recommended Phase 1C Implementation Plan

### Phase 1C-Step 2: Current Flow Inspection & Documentation
**Deliverable**: Detailed documentation of current upload, processor, and route flow

**Tasks**:
- Map processor output columns to database fields
- Document processor CSV output structure
- Document existing fixture structure
- Create database column mapping specification
- Identify any missing processor features needed for database mode

---

### Phase 1C-Step 3: Ingestion Service Contract & Tests
**Deliverable**: IngestionService interface + comprehensive unit tests (TDD)

**Tasks**:
- Define IngestionService interface
- Write test suite for ingestion (unit tests)
- Define error handling strategies
- Test CSV validation failures
- Test duplicate detection
- Test household inference

**Test count**: ~15 unit tests

---

### Phase 1C-Step 4: Raw Row & Batch Persistence
**Deliverable**: Store CSV rows immutably in database

**Tasks**:
- Create import batch record
- Parse processor CSV
- Insert raw_import_rows in bulk
- Store entire row as JSON
- Verify immutability

**Test count**: ~3 integration tests

---

### Phase 1C-Step 5: Import Contact Snapshot Creation
**Deliverable**: Denormalize contacts from raw rows

**Tasks**:
- Parse contact fields from raw JSON
- Create ImportContact records
- Test field parsing (address, name, email, phone)
- Verify snapshot immutability

**Test count**: ~4 integration tests

---

### Phase 1C-Step 6: Validation & Normalization Item Generation
**Deliverable**: Generate pending validation and normalization suggestions

**Tasks**:
- Read validation issues from processor output
- Create ValidationReviewItem records
- Create NormalizationReviewItem records
- Link items to contacts via ReviewItemSubject
- Test suggestion generation

**Test count**: ~4 integration tests

---

### Phase 1C-Step 7: Duplicate & Household Item Generation
**Deliverable**: Generate pending duplicate and household suggestions

**Tasks**:
- Generate duplicate candidates from processor output
- Create DuplicateReviewItem records
- Infer household groupings from address/name
- Create HouseholdReviewItem records
- Test heuristics

**Test count**: ~4 integration tests

---

### Phase 1C-Step 8: Audit Trail Integration
**Deliverable**: Record ingestion events in audit log

**Tasks**:
- Create audit log entry after ingestion
- Record counts and statistics
- Test audit trail accuracy

**Test count**: ~2 integration tests

---

### Phase 1C-Step 9: Route/Read-Model Verification
**Deliverable**: Verify all 8 routes work after ingestion

**Tasks**:
- Test /imports shows ingested batch
- Test /dashboard shows ingested queue counts
- Test /validation, /normalizations, /households, /duplicates
- Test /audit shows ingestion event
- Test /exports shows updated metrics

**Test count**: ~8 integration tests (reuse existing route tests)

---

### Phase 1C-Step 10: Idempotency & Safety Verification
**Deliverable**: Verify ingestion is safe and repeatable

**Tasks**:
- Test duplicate file uploads
- Test transaction rollback
- Test no external API calls
- Test no auto-approvals
- Closure verification

**Test count**: ~5 integration tests

---

## Summary: Phase 1C Implementation

**Estimated scope**: 10 steps, 3-4 weeks

**Test additions**: ~40 new tests (unit + integration)

**Files created**: ~5 new files
- IngestionService
- Service tests
- Integration test fixtures
- Migration (if needed)

**Files modified**: ~3 files
- Upload route (add database mode)
- Services (if any changes needed)
- Repository provider (if any changes needed)

**Result**: CSV uploads ingest into database, routes continue working, all guardrails intact

---

## Recommendation: Ready for Phase 1C-Step 2

**Go/No-Go**: ✅ **GO**

**Planning confidence**: High

**Blockers**: None identified

**Next step**: Phase 1C-Step 2 - Current Flow Inspection & Documentation

**Claude Code prompt for Phase 1C-Step 2**:

```
Phase 1C-Step 2: Current Upload and Import Flow Inspection

You are working in the DonorTrust / Householder v1 Flask/Jinja codebase.

Goal:

Inspect and document the current upload, CSV processor, and import flow to establish baseline understanding for Phase 1C database import ingestion.

Do not modify code yet. Documentation only.

Tasks:

1. Inspect current upload route (POST /upload in scripts/uploader/app.py)
   - Document endpoint behavior
   - Document input/output contract
   - Document file handling

2. Inspect CSV processor (scripts/processor.py)
   - Document processor input/output
   - Document all output columns
   - Document validation rules
   - Document duplicate detection logic
   - Identify any CSV format assumptions

3. Map processor output to database fields
   - Document which processor output columns map to which database fields
   - Identify any mismatches or gaps
   - Identify any data transformations needed

4. Document current fixture structure (scripts/uploader/fixtures.py)
   - Compare fixture structure to database schema
   - Identify any fields in fixtures not in database
   - Identify any database fields with no fixture equivalent

5. Create ingestion specification document
   - Column mapping specification
   - Data transformation rules
   - Error handling scenarios
   - Validation rules for processor output

Deliver:

1. Current upload/import flow diagram (text-based)
2. Processor input/output specification
3. Column mapping specification
4. Any identified gaps or assumptions
5. Recommendation: ready for Phase 1C-Step 3 or investigation needed
```

---

**Planning date**: 2026-06-12  
**Status**: Planning complete, ready for implementation planning
