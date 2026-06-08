Perfect! Now I have all the context needed. Let me create a comprehensive implementation plan for Householder v1.

## HOUSEHOLDER V1 IMPLEMENTATION PLAN

### Executive Summary

This plan details the step-by-step implementation of Householder v1, a human-in-the-loop data hygiene app that extends the Givebutter Processor. Householder ingests CSV contact data, generates suggestions for normalization and household grouping, and requires explicit human approval for all changes. The implementation prioritizes data safety with an append-only audit trail and zero auto-mutations.

**Key Design Principles:**
- Raw data immutability (append-only audit trail)
- Suggestion-only engines (no auto-writes)
- Explicit approval workflows (every change requires a click)
- Deterministic household ID generation
- View-based exports (read-only queries)

**Compressed 1-Week Timeline:**
- Day 1: Database & Processor Adapter
- Day 2: Upload & Extraction
- Day 3: Suggestion Engines
- Day 4: Persistence & Normalization Approvals
- Day 5: Household & Duplicate Workflows
- Day 6: UI & Exports
- Day 7: Testing & Verification

---

## PHASE 1: INFRASTRUCTURE & SETUP (Days 1, Steps 1-2)

### Step 1: Processor Adapter & Validation Functions Import

**Objective:** Verify and establish clean import of validation functions from Processor; create adapter if needed.

**Tasks:**
1. Create `/scripts/householder/__init__.py` (package marker)
2. Create `/scripts/householder/processor_adapter.py` 
   - Import `fuzzy_email_match`, `normalize_phone`, `validate_email_format` from `scripts.processor`
   - Add version check: `assert processor.__version__ >= '3.4'`
   - Provide clear error messages if functions not found
   - Re-export functions to make them available to Householder modules
3. Create `/scripts/householder/processor_compat.py` 
   - Wrapper utilities for safe function calls
   - Error handling for missing/incompatible signatures
4. Add unit tests: `/tests/unit/test_processor_adapter.py`
   - Test all three functions are importable and callable
   - Verify function signatures match expectations
   - Test version checking at startup

**Data Safety Checkpoints:**
- Verify processor functions are read-only (no database mutations)
- Confirm fuzzy_email_match uses 70% threshold as per PRD

**Test Requirements:**
- `test_processor_dependencies_available()` — Import verification
- `test_processor_version_check()` — Version compatibility
- `test_fuzzy_email_match_signature()` — Correct function signature
- `test_normalize_phone_signature()` — Correct function signature

**Blocking Issues:**
- If processor functions don't exist, implementation blocks; must refactor processor first

---

### Step 2: Database Schema & Migrations

**Objective:** Create SQLite schema for Householder tables; design for Postgres migration path.

**Tasks:**
1. Create `/scripts/householder/db_schema.py` with SQLAlchemy ORM models
   - Define models: `RawImportRow`, `Import`, `Contact`, `ContactSuggestion`, `HouseholdSuggestion`, `Household`, `DuplicateCandidate`
   - Include CHECK constraints for enum fields (status, decision)
   - Add UNIQUE constraints for idempotency indexes
   - Include audit fields: `reviewed_by`, `reviewed_at`, `ip_address`, `user_agent`
   
2. Create `/scripts/householder/migrations/001_initial_schema.py`
   - Alembic migration to create all new tables
   - Extend existing Processor database (shared SQLite instance)
   - Use raw SQL with explicit column definitions for Postgres compatibility

3. Create `/scripts/householder/db.py` 
   - Database connection management
   - Session factory (thread-safe)
   - Helper functions for audit trail insertion

4. Create `/scripts/householder/models.py` 
   - SQLAlchemy ORM class definitions
   - Implement relationship properties
   - Add validation helpers (e.g., validate_enum_field)
   - Add to_dict() methods for JSON serialization

5. Database initialization script: `/scripts/householder/init_db.py`
   - Create tables if missing
   - Support both in-memory (for tests) and file-based (for production) SQLite
   - Add seed data for tests

**Data Safety Checkpoints:**
- Verify `raw_import_rows` has no UPDATE/DELETE triggers or constraints that allow mutation
- Confirm `contacts.household_id` is the ONLY mutable baseline field
- Check that all suggestion tables use `status IN ('pending', 'approved', 'rejected', 'deferred')`
- Verify duplicate_candidates enforces `contact_id_a < contact_id_b`

**Test Requirements:**
- `test_schema_creation()` — Tables created successfully
- `test_raw_import_rows_immutable()` — Explicit row prevents mutation
- `test_contact_household_id_only_mutable_field()` — Other contact fields are read-only in ORM
- `test_enum_constraints()` — CHECK constraints prevent invalid status values
- `test_idempotency_indexes()` — UNIQUE constraints prevent duplicates
- `test_audit_fields_present()` — All tables have reviewed_by, reviewed_at, etc.

---

## PHASE 2: UPLOAD & EXTRACTION (Day 2, Steps 3-4)

### Step 3: Raw Data Upload & Preservation

**Objective:** Implement CSV upload flow that preserves raw data immutably in `raw_import_rows`.

**Tasks:**
1. Create `/scripts/householder/upload.py`
   - Accept CSV file upload via Flask
   - Validate CSV format (required columns: name, email, phone, address, zip, amount, date, campaign)
   - Create `imports` record with status = 'processing'
   - Insert each row into `raw_import_rows` with raw_json field (original CSV row as JSON)
   - No transformation, no validation at this stage
   
2. Extend `/scripts/uploader/app.py` with new routes:
   - `POST /householder/imports` — Accept CSV upload
   - `GET /householder/imports` — List imports
   - `GET /householder/imports/<id>` — View import details

3. Create HTML upload form: `/scripts/uploader/templates/householder_upload.html`
   - Drag-and-drop or file picker
   - File size limit (e.g., 10MB)
   - Accept .csv only

4. Create CSV validation helper: `/scripts/householder/csv_validator.py`
   - Check required columns present
   - Detect encoding issues
   - Count rows
   - Return validation report (warnings, not errors)

**Data Safety Checkpoints:**
- Verify raw_json field stores EXACT CSV row (no normalization)
- Confirm imports.status transitions are: processing → complete → archived
- Check that raw_import_rows.id is auto-increment (never reused)
- Verify no auto-delete behavior; only logical archiving via imports.status

**Test Requirements:**
- `test_raw_import_rows_preserve_exact_csv()` — Uploaded data matches raw_json exactly
- `test_import_record_created()` — imports record with status=processing
- `test_upload_multiple_batches()` — Multiple imports tracked independently
- `test_upload_csv_validation()` — Detects missing columns

---

### Step 4: Contact Extraction & Normalization Suggestions

**Objective:** Extract contacts from raw data; generate email/phone/name/address suggestions (no approval yet).

**Tasks:**
1. Create `/scripts/householder/extraction.py`
   - Function: `extract_contacts(import_id: int) -> list[Contact]`
   - Read raw_import_rows for import_id
   - Parse each row, extract fields: full_name, email, phone, address_line_1, city, state, postal_code, zip5, amount_cents, campaign_title, donation_date
   - Create contacts records with raw field values (no normalization)
   - Link each contact to raw_import_row via raw_row_id
   - Return list of Contact ORM objects (not yet committed)

2. Create `/scripts/householder/suggestion_engines.py` (Core Logic)
   - Function: `suggest_normalizations(contact: Contact) -> list[ContactSuggestion]`
     - Email: lowercase, trim (confidence 100)
     - Phone: extract digits only via normalize_phone() (confidence 95)
     - Name: Title Case (confidence 90)
     - Address: lowercase, remove punctuation, expand abbreviations (confidence 85)
     - Returns list of ContactSuggestion objects (status='pending', not committed)

**Data Safety Checkpoints:**
- Verify `suggest_normalizations()` returns objects but does NOT commit to DB
- Confirm contacts table stores ONLY raw field values (no normalization)
- Check that contact_suggestions.status = 'pending' (never 'approved' before user click)
- Verify idempotency: re-running extraction doesn't create duplicate pending suggestions

**Test Requirements:**
- `test_extract_contacts_from_raw_import_rows()` — Correct field extraction
- `test_suggest_normalizations_returns_not_writes()` — Engine returns list, no DB writes
- `test_email_normalization_suggestion()` — Suggests lowercase
- `test_phone_normalization_via_adapter()` — Uses processor_adapter.normalize_phone()
- `test_suggestion_idempotency()` — Re-run doesn't duplicate suggestions
- `test_contact_suggestions_status_pending()` — All new suggestions have status='pending'

---

## PHASE 3: CORE ENGINES (Day 3, Steps 5-6)

### Step 5: Suggestion Engine Implementations

**Objective:** Build three core suggestion engines: normalization, household, duplicate detection. All return suggestions only; no auto-write behavior.

**Tasks:**
1. **Normalization Engine** (already sketched in Step 4, now complete)
   - In `/scripts/householder/suggestion_engines.py`:
   - `suggest_normalizations(contact: Contact) -> list[ContactSuggestion]`
   - Email: case normalization, domain typo detection (via fuzzy_email_match)
   - Phone: extract digits, check for test patterns (all same digit, sequential, reserved 555 ranges)
   - Name: Title Case
   - Address: lowercase, expand abbreviations (st→street, ave→avenue, etc.), remove punctuation
   - Each suggestion has confidence_score 70-100
   - Return ContactSuggestion objects with status='pending'

2. **Household Matching Engine** — New functions in suggestion_engines.py
   - `suggest_households(import_id: int) -> list[HouseholdSuggestion]`
   - Input: all contacts for an import_id
   - Matching rules (priority order):
     1. Address + zip + last name exact (confidence 85)
     2. Phone + last name + zip exact (confidence 80)
     3. Shared address + zip with different first names (confidence 80)
     4. Phone + different first names + same last name (confidence 75)
     5. Last name + zip + first initial + address fuzzy 70%+ (confidence 70)
   - Critical: Exact email match → duplicate signal, NOT household signal
   - Return HouseholdSuggestion objects with status='pending'
   - Use generate_sorted_contact_ids_key() for idempotency

3. **Duplicate Detection Engine** — New functions in suggestion_engines.py
   - `suggest_duplicates(import_id: int) -> list[DuplicateCandidate]`
   - Input: all contacts for an import_id
   - Scoring logic:
     - 95: Email exact match
     - 90: Phone exact + email fuzzy match
     - 85: Name exact + phone exact + address exact
     - 75: Name fuzzy 85%+ + phone exact
     - 70: Phone exact + address exact + name fuzzy 70%+
   - Return DuplicateCandidate objects with decision='unreviewed'
   - Enforce contact_id_a < contact_id_b
   - Return match_reasons as JSON array

4. **Helper Functions** — In suggestion_engines.py
   - `get_primary_contact(contact_ids: list[int]) -> int`
     - Query contacts table by contact_ids
     - Waterfall: highest amount_cents → most recent donation_date → oldest id
     - Return contact_id of elected primary
   - `generate_household_id(address_line_1: str, zip5: str) -> tuple[str, str]`
     - Normalize address via token-based abbreviation mapping
     - Create canonical form: normalized_address + "|" + zip5
     - MD5 hash canonical, extract 8 chars
     - Return (household_id, canonical_form)
   - `normalize_address_for_household_id(address: str) -> str`
     - Lowercase, remove punctuation, collapse spaces
     - Token-based replacement: st→street, ave→avenue, etc.
     - Remove all spaces (for hash input)
   - `generate_sorted_contact_ids_key(contact_ids: list[int]) -> str`
     - Sort contact_ids ascending
     - Return "-".join(str(cid) for cid in sorted_ids)

**Critical Guardrails Enforced Here:**
- Return statements only; no db.session.add/commit
- Household suggestions exclude exact email matches (those go to duplicates)
- Household ID uses MD5 hash of canonical_form for stability
- Primary contact waterfall is amount → date → id (deterministic)

---

### Step 6: Suggestion Persistence (Pending Only)

**Objective:** Commit pending suggestions to DB without approving them. Enforce idempotency.

**Tasks:**
1. Create `/scripts/householder/suggestion_persistence.py`
   - Function: `persist_normalization_suggestions(import_id, contact_id, suggestions)`
     - Check UNIQUE constraint: (import_id, contact_id, field_name, suggested_value)
     - If exists, skip (idempotent)
     - If not, insert with status='pending'
   
   - Function: `persist_household_suggestions(import_id, suggestions)`
     - Generate sorted_contact_ids_key from contact_ids
     - Check UNIQUE constraint: (import_id, sorted_contact_ids_key)
     - If exists, skip (idempotent)
   
   - Function: `persist_duplicate_candidates(import_id, candidates)`
     - Ensure contact_id_a < contact_id_b
     - Check UNIQUE constraint: (import_id, contact_id_a, contact_id_b)
     - If exists, skip (idempotent)

2. Update Flask routes: `POST /householder/imports/<id>/process`
   - Calls extraction → suggest_* → persist_* (all in single transaction)
   - Return summary of pending counts

3. Create `/scripts/householder/processing.py`
   - Function: `process_import(import_id: int) -> dict`
   - Orchestrates entire upload → extract → suggest → persist flow

---

## PHASE 4: APPROVAL WORKFLOWS (Days 4-5, Steps 7-9)

### Step 7: Normalization Approval Workflow

**Objective:** Implement review queue and approval actions for field-level normalizations. Never mutate contacts; only approve suggestions.

**Tasks:**
1. Create `/scripts/householder/approvals.py`
   - Function: `approve_normalization(suggestion_id, approved_by, ip_address, user_agent)`
     - Update: status='approved', reviewed_by, reviewed_at, ip_address, user_agent
     - Does NOT mutate contacts table
   
   - Function: `reject_normalization(...)`
     - Update: status='rejected' with notes
   
   - Function: `defer_normalization(...)`
     - Update: status='deferred' with notes

2. Create Flask routes:
   - `GET /householder/imports/<id>/normalizations` — Review queue (paginated table)
   - `POST /householder/normalizations/<id>/approve` — Approve single
   - `POST /householder/imports/<id>/normalizations/approve-bulk` — Bulk approve

3. Create HTML: `/scripts/uploader/templates/householder_normalizations.html`
   - Table: contact name, field, current, suggested, reason, confidence, actions
   - Filters: by field, by confidence
   - Bulk action with modal confirmation

**Critical Guardrails:**
- Verify contacts table is NOT updated during approval
- Confirm approved_contacts view reflects approved suggestions

---

### Step 8: Household Approval Workflow ⚠️ CRITICAL

**Objective:** Implement household approval with transactional household creation + contact.household_id assignment.

**Tasks:**
1. Create `/scripts/householder/approvals.py` (extending Step 7)
   - Function: `approve_household(suggestion_id, approved_by, ip_address, user_agent)`
     - **CRITICAL: Single database transaction. Rollback if any step fails.**
     - Verify contact household conflicts
     - Elect primary contact via waterfall
     - Prepare address (use approved suggestion if available, else raw)
     - Generate household_id
     - Insert households row
     - Update contacts.household_id for ALL members (ATOMIC)
     - Mark suggestion as approved
   
   - Function: `reject_household(...)`
     - Update: status='rejected'
   
   - Function: `defer_household(...)`
     - Update: status='deferred'

2. Create Flask routes:
   - `GET /householder/imports/<id>/households` — Household review queue
   - `POST /householder/households/<id>/approve` — Approve single
   - `POST /householder/imports/<id>/households/approve-bulk` — Bulk approve

3. Create HTML: `/scripts/uploader/templates/householder_households.html`
   - Card layout: primary + members side-by-side
   - Match reason + confidence
   - Waterfall explanation: "Primary: Jane (highest donation: $1000)"

**Critical Guardrails:**
- ALL STEPS IN SINGLE TRANSACTION; rollback if any fails
- Verify household_id is deterministic (same address+zip = same ID)
- Confirm all members get same household_id

---

### Step 9: Duplicate Candidate Workflow

**Objective:** Implement duplicate decision recording (record-only in v1; no merge).

**Tasks:**
1. Create Flask routes:
   - `GET /householder/imports/<id>/duplicates` — Duplicate review queue
   - `POST /householder/duplicates/<id>/resolve` — Record decision
   - `POST /householder/imports/<id>/duplicates/bulk-different` — Bulk "Different" (no bulk "Same Person")

2. Create HTML: `/scripts/uploader/templates/householder_duplicates.html`
   - Two-column: Contact A vs Contact B
   - Buttons: [Same Person] [Different] [Defer]
   - Note: "v1 records decisions only. Merging available in v2."

3. Update `/scripts/householder/approvals.py`:
   - Function: `resolve_duplicate(candidate_id, decision, notes, decided_by, ip_address, user_agent)`
     - Update: decision, reviewer_notes, decided_by, decided_at
     - NO merge behavior; decision is record-only

**Critical Guardrails:**
- Verify no automatic merge occurs (even with decision='same_person')
- Confirm bulk approval disabled for "Same Person" (individual only)

---

## PHASE 5: VIEWS & EXPORTS (Day 6, Steps 10-13)

### Step 10: Derived Views

**Objective:** Create derived views that combine raw data + approved suggestions. Views are computed at query time (no storage).

**Tasks:**
1. Create SQL views in database:
   - `approved_contacts` — COALESCE pattern for approved normalization values
   - `households_summary` — One row per household with member info

2. Add query helpers in `/scripts/householder/exports.py`:
   - `get_approved_contacts(import_id)` — Query view
   - `get_household_summary(import_id)` — Query view

---

### Steps 11-12: Dashboard & Review Queues

**Objective:** Create user-facing dashboard and review queue pages.

**Tasks:**
1. Update Flask routes:
   - `GET /householder/imports/<id>` — Main dashboard
     - Total contacts, validation tier breakdown
     - Suggestion queue status
     - Action buttons

2. Create HTML: `/scripts/uploader/templates/householder_dashboard.html`
   - Cards for contacts count, tier breakdown, pending queues
   - Action buttons

3. Review queue pages (from Steps 7-9):
   - Filtering, pagination, deferred toggle

---

### Step 13: Exports

**Objective:** Implement four export formats. All read-only (query views, never mutate data).

**Tasks:**
1. Create `/scripts/householder/exports.py`:
   - `export_clean_contacts(import_id)` → CSV (query approved_contacts view)
   - `export_by_household(import_id)` → CSV (query households_summary)
   - `export_backlog(import_id)` → CSV (pending + deferred suggestions)
   - `export_raw(import_id)` → CSV (exact original data from raw_import_rows)

2. Create Flask routes:
   - `GET /householder/imports/<id>/export` — Export options page
   - `GET /householder/imports/<id>/export/clean` — Download clean
   - `GET /householder/imports/<id>/export/households` — Download by household
   - `GET /householder/imports/<id>/export/backlog` — Download backlog
   - `GET /householder/imports/<id>/export/raw` — Download raw

3. Create HTML: `/scripts/uploader/templates/householder_export.html`
   - Card layout for each export
   - Download buttons

---

## PHASE 6: TESTING & VERIFICATION (Day 7, Step 15)

### Step 15: Comprehensive Test Suite

**Objective:** Implement unit, integration, and E2E tests covering all approval paths, data safety guardrails, and user workflows.

**Critical Tests (Must Have):**

1. **Data Immutability Tests:**
   - `test_raw_import_rows_immutable()` — raw_import_rows never mutated
   - `test_contact_baseline_immutable()` — contact fields immutable except household_id
   - `test_no_auto_approval_critical()` — All suggestions stay pending until clicked

2. **Approval Workflow Tests:**
   - `test_approve_household_transaction_rollback()` — Partial failure rolls back everything
   - `test_household_id_deterministic()` — Same address+zip = same household_id
   - `test_primary_contact_waterfall()` — Correct member elected as primary
   - `test_resolve_duplicate_same_person_record_only()` — No merge in v1

3. **View & Export Tests:**
   - `test_approved_contacts_view_reflects_approved_suggestions()` — View shows approved only
   - `test_export_clean_accuracy()` — Clean export has approved values
   - `test_export_raw_immutable()` — Raw export never changes after upload

4. **Guardrail Verification:**
   - `test_no_auto_merge_critical()` — Zero accidental contact merges
   - `test_only_approve_household_sets_household_id()` — No other code path mutates this
   - `test_suggestion_engines_no_db_writes()` — Engines return objects, no commits
   - `test_bulk_same_person_disabled()` — Bulk "Same Person" blocked
   - `test_export_readonly()` — Exports never mutate DB

5. **E2E Workflow Test:**
   - `test_e2e_upload_review_approve_export()` — Full user workflow end-to-end

**Sample Data:**
   - Create `/tests/fixtures/sample_contacts_15_row.csv` (15 rows with 6 clean, 3 email typos, 2 invalid emails, 2 missing phones, 1 high-amount, 2 duplicates, 3 household candidates)

---

## PHASE 7: FINAL AUDIT (Step 16)

### Step 16: Final Audit & Documentation

**Objective:** Audit code against guardrails, verify no auto-mutations, document API & deployment.

**Tasks:**
1. Code Audit Checklist:
   - Verify all 8 guardrails enforced in code
   - Scan for forbidden function names (auto_*, merge_*)
   - Check all suggestion engines are return-only
   - Verify all mutations require explicit approval
   - Check all DB transactions are atomic
   - Verify all views are computed at query time

2. Documentation:
   - `/API.md` — REST API endpoints
   - `/DEPLOYMENT.md` — Database migration, environment setup
   - `/ARCHITECTURE.md` — System design, data flow diagrams
   - `/USER_GUIDE.md` — Step-by-step user workflows

3. Version: `__version__ = '1.0.0'` in `/scripts/householder/__init__.py`

---

## CRITICAL FILES FOR IMPLEMENTATION

### 5 Most Critical Files (In Dependency Order):

1. **`/scripts/householder/processor_adapter.py`**
   - Gates all validation functions; must be first
   - If processor functions unavailable, entire implementation blocks

2. **`/scripts/householder/db.py` + `/scripts/householder/models.py`**
   - Database schema is the contract between all modules
   - All other code depends on these definitions

3. **`/scripts/householder/suggestion_engines.py`**
   - Core matching logic
   - Return-only behavior must be enforced; no auto-write

4. **`/scripts/householder/approvals.py`**
   - State mutation entry point
   - Where guardrails 3 & 7 are enforced (only approve_household() sets household_id)

5. **`/tests/unit/test_householder_guardrails.py` + `/tests/integration/test_householder_immutability.py`**
   - Verify all 8 guardrails enforced
   - Safety net for data integrity

---

## DATA SAFETY GUARDRAILS VERIFICATION CHECKLIST

| # | Guardrail | Enforced By | Test |
|---|-----------|------------|------|
| 1 | Never mutate raw_import_rows | DB (no UPDATE/DELETE triggers) | test_raw_import_rows_immutable |
| 2 | Never mutate baseline contact fields except household_id | ORM model (read-only properties) | test_contact_baseline_immutable |
| 3 | Only approve_household() may set household_id | Application guard (code review) | test_only_approve_household_sets_household_id |
| 4 | Suggestion engines return suggestions only | Code (no db.session.add/commit) | test_suggestion_engines_no_db_writes |
| 5 | Upload processing never auto-approves | Code (upload calls suggest_* not approve_*) | test_upload_no_auto_approve |
| 6 | Duplicate decisions record-only; no merge | Code (resolve_duplicate updates decision only) | test_no_duplicate_merge_v1 |
| 7 | Exports read-only; never mutate | Code (exports use SELECT from views only) | test_export_readonly |
| 8 | No Givebutter API writeback | Code review (no import givebutter_api) | test_no_givebutter_api_writeback |

---

## HIGH-RISK AREAS

1. **Household Approval Transaction** — Must be atomic; test rollback
2. **Household ID Determinism** — Must use token-based normalization; test stability
3. **Idempotency Keys** — Must prevent duplicates on re-run; test UNIQUE constraints
4. **Primary Contact Waterfall** — Must be deterministic; test all scenarios
5. **Audit Trail Completeness** — Must capture ip_address, user_agent in all approvals
6. **Approved Contacts View** — Must reflect approved suggestions only; test all statuses
7. **Export Clean Accuracy** — Must match approved_contacts view exactly; test consistency

---

## READY TO BEGIN?

This plan is structured for focused, incremental execution. Each phase builds on the previous one with clear dependencies. All 8 critical guardrails are testable and enforceable.

**Next step:** Start Phase 1, Step 1 — Create Processor Adapter.
