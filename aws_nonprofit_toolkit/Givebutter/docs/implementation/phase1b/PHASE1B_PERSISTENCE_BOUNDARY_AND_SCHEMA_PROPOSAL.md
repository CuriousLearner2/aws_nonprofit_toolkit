# Phase 1B Persistence Boundary and Schema Proposal

**Status:** Documentation-only proposal. No implementation code.

**Purpose:** Design Phase 1B database persistence behind the Phase 1A service boundary while preserving routes, services, templates, and Phase 0 UI.

**Next Step:** Stakeholder review and acceptance before Phase 1B implementation begins.

---

## 1. Executive Summary

Phase 1A successfully migrated all 8 DonorTrust review routes to a service-boundary pattern:
```
Route → Service → FixtureImportRepository → View Models → Template
```

Phase 1B will introduce persistent storage behind this boundary:
```
Route → Service → Repository Interface → Database-backed Repository → View Models → Template
```

**Key principle:** Services and templates remain data-source agnostic. The repository implementation (fixture-backed or database-backed) is swappable without changing service code or templates.

### What Changes in Phase 1B
- Underlying repository implementation switches from in-memory fixtures to database
- View models, service contracts, and routes remain unchanged
- Phase 0 UI remains preserved
- All Phase 1A constraints remain enforceable

### What Does NOT Change in Phase 1B
- Flask remains the only app server
- No frontend runtime (React, Node, Vite, etc.)
- No templates are modified
- No route signatures are modified
- Service method signatures remain the same
- No Givebutter or CRM writeback
- No real export file generation (metadata-only)

---

## 2. Non-Negotiable Guardrails

These constraints are enforced in Phase 1A and must remain enforced in Phase 1B:

### Raw Data Protection
✅ **Raw import rows are append-only and immutable after upload.**
- No UPDATE or DELETE on raw row data
- No in-place field modifications of raw import rows
- Raw data is source of truth for audit trail
- All validation findings, normalization suggestions, duplicate candidates, and household groupings are decisions about export staging only

✅ **Reviewer decisions are stored separately from raw data.**
- Separate tables for validation findings, normalization suggestions, duplicate decisions, household decisions
- Raw rows are never mutated by review decisions
- Decisions reference raw rows by ID without modifying them

### Review Decision Semantics
✅ **Reviewer decisions affect export staging only.**
- Accept/reject/defer decisions determine what gets staged for export
- Decisions do not change raw row data
- Decisions do not create permanent global master records or canonical identities
- Decisions are import-specific

✅ **No automatic approval or confirmation.**
- No automatic normalization confirmation
- No automatic duplicate resolution
- No automatic household confirmation
- All confirmation requires explicit reviewer action

### System Constraints
✅ **No Givebutter or CRM writeback.**
- No calls to Givebutter API
- No calls to CRM APIs
- No syncing decisions back to external systems
- No external system state changes as a result of DonorTrust decisions

✅ **No real export file generation until explicitly approved.**
- Phase 1B exports are metadata-only
- Export staging records define what would be exported
- File generation (CSV, etc.) is Phase 2 or later
- No files written to disk during Phase 1B

✅ **Current import batch only.**
- Each import is isolated
- No cross-import duplicate identification
- No cross-import household grouping
- Reviews are import-specific

✅ **Flask remains the only application server.**
- No additional runtime environments
- No background workers or task queues in Phase 1B
- No microservices
- Single Flask process for all routes

---

## 3. Persistence Boundary

### Current Phase 1A Architecture
```
Flask Route
    ↓
Service Module (e.g., dashboard_service.get_dashboard())
    ↓
FixtureImportRepository (in-memory fixture data)
    ↓
View Models (frozen dataclasses from service_contracts.py)
    ↓
to_template_dict() → Plain dicts
    ↓
Jinja Template
```

**Data flow:** Routes never access fixtures directly. Services call repository methods. Repository returns view model instances. View models convert to plain dicts for templates.

### Proposed Phase 1B Architecture
```
Flask Route
    ↓
Service Module (same interface, unchanged)
    ↓
Repository Interface/Protocol (abstract contract)
    ├─→ FixtureImportRepository (Phase 1A fallback)
    └─→ DatabaseImportRepository (Phase 1B implementation)
    ↓
View Models (same frozen dataclasses from service_contracts.py)
    ↓
to_template_dict() → Plain dicts
    ↓
Jinja Template
```

**Benefits:**
- Services are data-source agnostic
- Can test with fixtures, deploy with database
- Can run both implementations in parallel for verification
- Repository is the only place that knows about database schema
- Templates and routes never change

### Key Principle
**The repository interface is a contract.** Phase 1B introduces a database implementation of this contract while keeping the Phase 1A fixture implementation available for testing and fallback.

---

## 4. Repository Contract (Read-Only, Phase 1B-Step 5)

All Phase 1B methods return frozen view model instances (from `service_contracts.py`) converted to dicts for templates. None mutate raw data. Methods are read-only for Phase 1B.

### `list_imports() → List[ImportSummary]`
**Purpose:** List all import batches with metadata.

**Returns:** List of ImportSummary view models
**Behavior:**
- Read-only
- Fixture implementation: wraps IMPORT_BATCH list
- Database implementation: queries imports table with record counts and statuses

**Immutability:** Does not mutate any data

---

### `get_dashboard(import_id: str) → ImportDashboardViewModel`
**Purpose:** Get import review status and queue counts for all review queues.

**Returns:** ImportDashboardViewModel (batch info + queue status cards)
**Behavior:**
- Read-only
- Fixture implementation: wraps IMPORT_BATCH, computes queue counts from fixture data
- Database implementation: computes counts from raw rows and decisions

**Immutability:** Does not mutate any data

---

### `get_validation(import_id: str) → ValidationPageViewModel`
**Purpose:** Get validation review page data with records and issues.

**Returns:** ValidationPageViewModel (batch info + validation rows + issue count)
**Behavior:**
- Read-only
- Fixture implementation: wraps validation rows from fixtures
- Database implementation: queries raw rows, computes validation findings on-demand (see section 9)

**Immutability:** Does not mutate any data

---

### `get_normalizations(import_id: str) → NormalizationPageViewModel`
**Purpose:** Get normalization review page data (current suggestion with pagination).

**Returns:** NormalizationPageViewModel (batch info + current suggestion + navigation)
**Behavior:**
- Read-only
- Fixture implementation: wraps normalization suggestions from fixtures
- Database implementation: queries normalization suggestions table

**Immutability:** Does not mutate any data

---

### `get_households(import_id: str) → HouseholdPageViewModel`
**Purpose:** Get household grouping suggestions and current reviewer decision (if any).

**Returns:** HouseholdPageViewModel (batch info + current household + navigation)
**Behavior:**
- Read-only
- Fixture implementation: wraps household suggestions from fixtures
- Database implementation: queries household suggestions table

**Immutability:** Does not mutate any data

---

### `get_duplicates(import_id: str) → DuplicatePageViewModel`
**Purpose:** Get duplicate candidate pair and current reviewer decision (if any).

**Returns:** DuplicatePageViewModel (batch info + current duplicate pair + navigation)
**Behavior:**
- Read-only
- Fixture implementation: wraps duplicate candidates from fixtures
- Database implementation: queries duplicate candidates table

**Immutability:** Does not mutate any data

---

### `get_audit(import_id: str) → AuditPageViewModel`
**Purpose:** Get audit log of all reviewer actions (immutable for compliance).

**Returns:** AuditPageViewModel (batch info + audit entries)
**Behavior:**
- Read-only
- Fixture implementation: wraps audit entries from fixtures
- Database implementation: queries audit log table in timestamp order

**Immutability:** Does not mutate any data. Audit log is append-only.

---

### `get_exports(import_id: str) → ExportConsoleViewModel`
**Purpose:** Get export staging summary and export card definitions.

**Returns:** ExportConsoleViewModel (batch info + export cards + staging counts)
**Behavior:**
- Read-only for Phase 1B
- Fixture implementation: wraps export cards from fixtures, computes staging counts from fixture data
- Database implementation: computes staging from raw rows + decisions

**Immutability:** Does not mutate any data. (Export file generation deferred to Phase 2.)

---

## 5. Future Write Operations (Out of Scope for Phase 1B-Step 5)

Decision recording will be required for Phase 1B completion, but is explicitly **not part of Phase 1B-Step 5**. These APIs are listed here for clarity and planning only:

### Future: `record_decision(decision_data) → None`
**Purpose:** Record a reviewer decision (to be defined in Phase 1B-Step 6+).

**Note:** This method does NOT exist in Phase 1B-Step 5. Decision recording will be designed separately after repository interface is accepted and implemented.

**Expected scope (Phase 1B-Step 6+):**
- Accept normalization choices (accept/reject suggestions)
- Accept duplicate judgments (same-person / different / defer)
- Accept household confirmations (confirm / reject grouping)
- Record in review_decisions table with audit trail
- Recompute export staging if needed

**Important:** Phase 1B-Step 5 is read-only. Write operations are planned for Phase 1B-Step 6 or later.

---

## 6. Proposed Database Schema

**Note:** This is a schema proposal, not implementation code. Actual table creation, indexes, and migrations are Phase 1B-Step 4 or later.

### Table: `imports`
**Purpose:** Metadata for each import batch.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Import ID (e.g., "IMP-2025-0101-A")
  filename (TEXT NOT NULL)                 — Original CSV filename
  upload_date (TIMESTAMP NOT NULL)         — When file was uploaded
  uploader (TEXT)                          — User or system that uploaded
  import_status (TEXT)                     — Status: "uploaded", "in_review", "staged", "exported"
  raw_row_count (INTEGER)                  — Total rows in import
  created_at (TIMESTAMP DEFAULT NOW())     — Record creation time
  updated_at (TIMESTAMP DEFAULT NOW())     — Last update time

Example:
  id: "IMP-2025-0101-A"
  filename: "donors_q1_2025.csv"
  upload_date: 2025-01-15 10:30:00
  import_status: "in_review"
  raw_row_count: 1547
```

### Table: `raw_import_rows`
**Purpose:** Immutable snapshot of uploaded CSV rows.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Unique row ID (e.g., "IMP-2025-0101-A/row-42")
  import_id (TEXT NOT NULL FK→imports.id)  — Which import this row belongs to
  csv_line_number (INTEGER)                — Original line number in CSV (for audit)
  raw_data (JSON or COLUMNS)               — Full row data as JSON or normalized columns
  created_at (TIMESTAMP DEFAULT NOW())     — Record creation time
  (NO UPDATE or DELETE after created)

Constraints:
  IMMUTABLE: No updates or deletes after creation
  FK: import_id references imports.id
  
Example:
  id: "IMP-2025-0101-A/row-42"
  import_id: "IMP-2025-0101-A"
  csv_line_number: 43
  raw_data: {"name": "John Doe", "email": "john@example.com", "phone": "555-1234", "amount": "100.00"}
```

### Table: `import_contacts`
**Purpose:** Denormalized contact snapshot from raw rows (for efficient filtering/search).

```
Columns:
  id (TEXT PRIMARY KEY)                    — Contact ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  raw_row_id (TEXT NOT NULL FK→raw_import_rows.id)  — Reference to raw row
  name (TEXT)
  email (TEXT)
  phone (TEXT)
  address (TEXT)
  amount (DECIMAL)
  created_at (TIMESTAMP)
  (NO UPDATE or DELETE after created)

Constraints:
  IMMUTABLE: No updates or deletes
  FK: raw_row_id references raw_import_rows.id
  FK: import_id references imports.id

Index:
  (import_id, email) for duplicate matching
  (import_id, phone) for duplicate matching
  (import_id, name) for fuzzy matching
```

### Table: `normalization_suggestions`
**Purpose:** Suggested normalized values for raw fields.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Suggestion ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  raw_row_id (TEXT NOT NULL FK→raw_import_rows.id)  — Which row
  field_name (TEXT NOT NULL)               — e.g., "phone", "address", "name"
  raw_value (TEXT)                         — Original value from CSV
  normalized_value (TEXT)                  — Suggested normalized value
  confidence (DECIMAL 0-1)                 — Confidence of suggestion
  basis (TEXT)                             — How suggestion was derived (e.g., "phone_formatter", "address_parser")
  created_at (TIMESTAMP DEFAULT NOW())
  (Append-only after creation)

Constraints:
  FK: raw_row_id references raw_import_rows.id
  FK: import_id references imports.id

Example:
  id: "NS-001"
  import_id: "IMP-2025-0101-A"
  raw_row_id: "IMP-2025-0101-A/row-42"
  field_name: "phone"
  raw_value: "(555) 123-4567 ext 890"
  normalized_value: "5551234567"
  confidence: 0.95
  basis: "phone_formatter"
```

### Table: `duplicate_candidates`
**Purpose:** Suggested duplicate pairs (not automatic deduplication).

```
Columns:
  id (TEXT PRIMARY KEY)                    — Candidate ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  raw_row_id_a (TEXT NOT NULL FK→raw_import_rows.id)  — First row
  raw_row_id_b (TEXT NOT NULL FK→raw_import_rows.id)  — Second row
  match_type (TEXT)                        — "exact_email", "exact_phone", "fuzzy_name", "address_overlap"
  confidence (DECIMAL 0-1)                 — Confidence of match
  evidence (JSON)                          — Details of matching (e.g., {"field": "email", "a": "john@gmail.com", "b": "john@gmail.com"})
  conflicts (JSON)                         — Fields that differ (e.g., {"name": ["John Doe", "J. Doe"]})
  created_at (TIMESTAMP DEFAULT NOW())
  (Append-only after creation)

Constraints:
  FK: raw_row_id_a references raw_import_rows.id
  FK: raw_row_id_b references raw_import_rows.id
  FK: import_id references imports.id
  RULE: raw_row_id_a < raw_row_id_b (to prevent duplicates)

Example:
  id: "DC-001"
  import_id: "IMP-2025-0101-A"
  raw_row_id_a: "IMP-2025-0101-A/row-42"
  raw_row_id_b: "IMP-2025-0101-A/row-87"
  match_type: "exact_email"
  confidence: 1.0
  evidence: {"field": "email", "value": "john@example.com"}
  conflicts: {"phone": ["555-1234", "555-1235"]}
```

### Table: `household_suggestions`
**Purpose:** Suggested household groupings (suggestions only, not automatic grouping).

```
Columns:
  id (TEXT PRIMARY KEY)                    — Household suggestion ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  suggested_label (TEXT)                   — e.g., "Doe Household", "Account #12345"
  confidence (DECIMAL 0-1)                 — Confidence of grouping
  basis (TEXT)                             — How grouped (e.g., "shared_address", "email_domain", "name_matching")
  member_raw_row_ids (JSON ARRAY)          — List of raw row IDs in this group
  created_at (TIMESTAMP DEFAULT NOW())
  (Append-only after creation)

Constraints:
  FK: import_id references imports.id
  RULE: member_raw_row_ids should not be empty

Example:
  id: "HH-001"
  import_id: "IMP-2025-0101-A"
  suggested_label: "Doe Household"
  confidence: 0.92
  basis: "shared_address"
  member_raw_row_ids: ["IMP-2025-0101-A/row-42", "IMP-2025-0101-A/row-87", "IMP-2025-0101-A/row-101"]
```

### Table: `review_decisions`
**Purpose:** Reviewer decisions on normalization, duplicates, and households.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Decision ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  decision_type (TEXT NOT NULL)            — "normalization", "duplicate", "household"
  target_id (TEXT)                         — ID of what's being reviewed (suggestion, candidate, etc.)
  decision (TEXT NOT NULL)                 — "accept", "reject", "defer", "same_person", "different", "confirm", "deny"
  reviewed_values (JSON)                   — For normalization: {"field": "phone", "chosen_value": "5551234567"}
  reviewer (TEXT)                          — User who made decision (if applicable)
  created_at (TIMESTAMP DEFAULT NOW())
  (Append-only, never modified)

Constraints:
  FK: import_id references imports.id
  RULE: Append-only, immutable after creation

Example (normalization):
  id: "RD-001"
  import_id: "IMP-2025-0101-A"
  decision_type: "normalization"
  target_id: "NS-001"
  decision: "accept"
  reviewed_values: {"field": "phone", "chosen_value": "5551234567"}
  reviewer: "alice@example.com"

Example (duplicate):
  id: "RD-002"
  import_id: "IMP-2025-0101-A"
  decision_type: "duplicate"
  target_id: "DC-001"
  decision: "same_person"
  reviewed_values: null
  reviewer: "bob@example.com"
```

### Table: `audit_log`
**Purpose:** Immutable record of all reviewer actions.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Audit entry ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  action_type (TEXT NOT NULL)              — "validation_reviewed", "normalization_reviewed", "duplicate_reviewed", "household_reviewed"
  action_timestamp (TIMESTAMP DEFAULT NOW()) — When action occurred
  actor (TEXT)                             — User who performed action
  target_type (TEXT)                       — "suggestion", "candidate", "household", "raw_row"
  target_id (TEXT)                         — ID of what was acted upon
  decision_id (TEXT FK→review_decisions.id) — Associated decision (if applicable)
  details (JSON)                           — Additional context
  created_at (TIMESTAMP DEFAULT NOW())
  (Append-only, immutable)

Constraints:
  FK: import_id references imports.id
  FK: decision_id references review_decisions.id (nullable)
  RULE: Immutable after creation

Example:
  id: "AL-001"
  import_id: "IMP-2025-0101-A"
  action_type: "normalization_reviewed"
  action_timestamp: 2025-01-20 10:15:00
  actor: "alice@example.com"
  target_type: "suggestion"
  target_id: "NS-001"
  decision_id: "RD-001"
  details: {"field": "phone", "suggested": "5551234567", "status": "accepted"}
```

---

## 7. Household Modeling

### Design Principles

1. **Suggestions, Not Automatic Grouping**
   - Household suggestions are generated by matching algorithms
   - Suggestions are advisory only
   - Reviewer confirms or rejects, not auto-grouped

2. **Decoupled from Raw Rows**
   - Suggestions reference raw rows by ID
   - Raw rows are never mutated to indicate household membership
   - Households are a review-time grouping, not raw data property

3. **Import-Scoped**
   - Confirmed households determine export staging treatment
   - No global household record or canonical identity
   - Multiple members may be grouped in export based on reviewer decision

### Schema Design

**`household_suggestions` table** (see schema section above)
- Stores algorithmically-generated grouping suggestions
- Includes confidence score and matching basis

**`review_decisions` table** records household confirmations
```
decision_type: "household"
decision: "confirm" or "deny"
target_id: suggestion ID
```

**Export staging** uses confirmed decisions to determine which rows are grouped

### Important Constraints

- A household suggestion is a suggestion only
- Once reviewed, the decision is recorded in `review_decisions`
- Export staging uses confirmed decisions for grouping
- No changes to household memberships after staging approved
- No cross-import household grouping

---

## 8. Duplicate Modeling

### Design Principles

1. **Candidates, Not Automatic Resolution**
   - Duplicates are algorithmic suggestions
   - No automatic deduplication
   - Reviewer makes explicit "same person" or "different" judgment

2. **Decoupled from Raw Data**
   - Suggestions are stored in `duplicate_candidates` table
   - Raw rows remain immutable
   - Decisions are recorded in `review_decisions`
   - Export staging applies decisions

3. **Import-Scoped, No Canonical Identity**
   - v1 does not create canonical person records
   - Decisions mark duplicates for export staging treatment only
   - Future cross-import deduplication is Phase 2+

### Schema Design

**`duplicate_candidates` table** (see schema section above)
- Stores algorithmically-identified pairs
- Includes match type, confidence, evidence, and conflicts

**`review_decisions` table** records duplicate judgments
```
decision_type: "duplicate"
decision: "same_person", "different", or "defer"
target_id: candidate ID
```

**Export staging** applies decisions (include both rows, one row, etc.)

### Important Constraints

- A duplicate candidate is a suggestion only
- "Same person" decision does NOT mutate either raw row
- "Same person" decision indicates export staging treatment only
- "Different" decision indicates both rows are distinct in export
- "Defer" decision leaves export staging pending
- No cross-import duplicate identification

---

## 9. Validation Findings

### Design Decision: Computed On-Demand (Phase 1B)

**For Phase 1B-Step 5, validation findings are COMPUTED ON-DEMAND, not stored.**

Rationale:
- Validation rules are defined in Phase 1A and rarely change
- Computing on-demand is simpler to implement than storing
- Supports gradual migration: Phase 1B routes use same validation engine as Phase 1A
- Can be stored in Phase 1B-Step 6+ if performance requires

### Behavior

When `get_validation(import_id)` is called:
1. Load raw rows from database
2. Apply Phase 1A validation rules (same algorithms)
3. Return ValidationPageViewModel with computed findings
4. Findings are not persisted

### Future: Optional Storage (Phase 1B-Step 6+)

If stored findings become necessary:
- Add `validation_findings` table (see original schema proposal)
- Precompute findings when import is uploaded
- Read from database instead of computing on-demand
- Change is internal to repository; service and route unchanged

**Important:** This change to storage is optional and does not affect Phase 1B-Step 5 contract.

---

## 10. Export Staging

### Design Decision: Computed From Decisions (Phase 1B)

**For Phase 1B-Step 5, export staging is COMPUTED, not stored.**

Export staging records = (raw rows) + (normalization decisions) + (duplicate decisions) + (household decisions)

Behavior:
- `get_exports()` computes staging counts from raw rows and decision_review tables
- Staging is reproducible and auditable
- No `export_staging_records` table needed for Phase 1B
- Phase 1B exports are metadata-only (no files written)

### Future: Optional Storage (Phase 2+)

If file generation becomes necessary:
- Add `export_staging_records` table to cache computed staging
- Regenerate if decisions change
- Use for Phase 2 file generation

**Important:** For Phase 1B, export staging is computed in-memory. No persistence required.

---

## 11. Migration Strategy

### Recommended Phased Approach

**Phase 1B-Step 1:** This document (documentation-only schema proposal) — ✅ Complete

**Phase 1B-Step 2:** Schema Review and Acceptance (THIS GATE)
- Stakeholders review proposal
- Ask questions, suggest changes
- **DECISION REQUIRED:** Schema formally accepted before code begins
- **BLOCKING GATE:** No migrations, ORM, database code, or repository implementation may begin until schema is approved

**Phase 1B-Step 3:** Repository Interface/Protocol Only
- Define Python protocol/abstract class for repository
- No database code yet
- Fixture implementation unchanged
- **Deliverable:** Abstract `ImportRepository` protocol defined

**Phase 1B-Step 4:** Migrations and Models (After Schema Acceptance)
- Create database migrations (schema, indexes, constraints)
- Create SQLAlchemy models or raw SQL schema
- Create fixtures or seeds for testing
- **Deliverable:** Database schema created and tested

**Phase 1B-Step 5:** First Database Repository Implementation
- Implement `DatabaseImportRepository` for `/imports` route (lowest risk)
- Implement all 8 read-only methods
- Run alongside fixture implementation for parity testing
- **Deliverable:** First route database-backed and tested

**Phase 1B-Step 6:** Fixture-vs-Database Parity Tests
- Compare fixture and database outputs for same import
- Verify they produce identical view models
- Run regression tests on Phase 1A routes
- **Deliverable:** Parity verified, no regression

**Phase 1B-Step 7+:** Migrate Remaining Routes
- One route at a time: validation, normalizations, households, duplicates, audit, exports
- Verify each route in parallel (fixture + database)
- Merge to main when fully tested
- **Deliverable:** All 8 routes database-backed

### Rationale for This Sequence

1. **Schema First:** No code until schema is agreed
2. **Acceptance Gate:** Explicit approval before implementation investment
3. **Interface Before Implementation:** Contract before implementation details
4. **Database Setup Before Code:** Migrations work before ORM code depends on them
5. **One Route at a Time:** Lowest risk, easiest to debug, easy to rollback
6. **Parity Tests:** Fixture-backed tests ensure database implementation is correct
7. **Incremental Merge:** Each step can be merged and validated independently

---

## 12. Test Strategy

### Repository Contract Tests
**Purpose:** Ensure both fixture and database implementations meet the interface contract.

For each repository method, test:
- Returns correct view model type
- Returns immutable data (frozen dataclass)
- Does not mutate raw data
- Handles missing/invalid import IDs correctly
- Handles edge cases (empty import, no decisions, etc.)

### Fixture-vs-Database Parity Tests
**Purpose:** Verify that database implementation returns identical data as fixture implementation.

For each route, test:
- Same import ID, both implementations return same view model dict
- Same record counts, same status summaries, same findings
- No differences in field values

### Route Regression Tests
**Purpose:** Ensure Phase 1A routes still work correctly with database backend.

For each route, test:
- Route returns 200 status
- Page contains expected content (titles, counts, cards, buttons)
- No forbidden vocabulary
- No forbidden technology
- Phase 0 UI preserved

### Raw-Row Immutability Tests
**Purpose:** Verify raw data is never mutated.

Tests:
- Before and after any repository operation, raw rows are identical
- No UPDATE or DELETE on raw_import_rows table
- All changes are in decision/audit tables only

### Decision/Audit Append-Only Tests
**Purpose:** Verify decisions and audit logs are immutable.

Tests:
- Review decisions table has no UPDATE or DELETE operations
- Audit log table has no UPDATE or DELETE operations
- Only INSERT operations succeed
- UPDATE/DELETE operations fail with constraint error

### No-Writeback Tests
**Purpose:** Verify no external systems are called.

Tests:
- No calls to Givebutter API
- No calls to CRM APIs
- No HTTP requests to external systems
- No file system writes (in Phase 1B)

### Export Metadata-Only Tests
**Purpose:** Verify no files are written in Phase 1B.

Tests:
- Export packages have no file paths
- No files written to disk
- Export staging is in-memory only

---

## 13. Risks and Mitigations

### Risk: ORM Objects Leak into Templates

**Risk:** SQLAlchemy model instances are passed to templates instead of plain dicts.

**Mitigation:**
- Repository must return frozen dataclasses (view models from service_contracts.py), not ORM instances
- View models have `to_template_dict()` methods that return plain dicts
- Routes call `to_template_dict()` before passing to template
- Tests verify no ORM types in template context
- Code review checks for `.objects`, `.query`, `Model()` in route handler

### Risk: UI Changes Mixed with Persistence Changes

**Risk:** Phase 1B introduces both new database code and unintended UI/route changes.

**Mitigation:**
- Phase 1B changes to repository implementation only
- No route handler modifications
- No template changes
- No service method signatures changed
- Code review enforces this separation
- Phase 1A route regression tests verify no UI changes

### Risk: Raw Data Mutation

**Risk:** Database code directly mutates raw_import_rows table.

**Mitigation:**
- raw_import_rows table has database constraint: no UPDATE or DELETE after creation
- Code review looks for any UPDATE/DELETE on raw_import_rows
- Raw-row immutability tests verify constraint works
- Decisions are stored in separate tables

### Risk: Accidental Cross-Import Matching

**Risk:** Duplicate or household algorithms accidentally match rows across different imports.

**Mitigation:**
- All suggestion tables have import_id FK
- Code review checks that all queries filter by import_id
- Tests use multiple imports and verify no cross-import matches

### Risk: Premature Export File Generation

**Risk:** Export file generation code is added in Phase 1B, before schema is tested.

**Mitigation:**
- Phase 1B allows no file writing
- Export packages are metadata-only (no file_path column)
- Code review blocks any file I/O in Phase 1B
- Tests verify no files created
- File generation deferred to Phase 2

### Risk: Accidental Givebutter/CRM Writeback

**Risk:** Code accidentally calls Givebutter or CRM APIs during review.

**Mitigation:**
- No Givebutter or CRM API calls in Phase 1B code
- Code review explicitly checks for `requests.post/get`, API client imports
- Tests mock all external calls and verify they're not invoked

### Risk: Schema Too Close to Canonical Person Design

**Risk:** Household and duplicate tables imply permanent canonical/master records.

**Mitigation:**
- No `person_id`, `master_person_id`, or `canonical_id` fields
- Household suggestions are import-specific and reviewable
- Duplicate decisions do not create merged records
- Schema explicitly rejects master-person language
- Code review questions any schema that implies global deduplication
- Documentation clarifies v1 households are import-local groupings

---

## 14. Open Questions

### Database Choice
- **Q:** SQLite (current, single-file) or PostgreSQL (production-ready)?
- **Decision Needed:** Before Phase 1B-Step 4

### ORM Framework
- **Q:** SQLAlchemy, Tortoise ORM, or raw SQL?
- **Recommendation:** SQLAlchemy (industry standard, Flask-SQLAlchemy integration)
- **Constraint:** Must not leak ORM objects to templates
- **Decision Needed:** Before Phase 1B-Step 4

### Migrations Tool
- **Q:** Alembic, Flask-Migrate, or SQL files?
- **Recommendation:** Flask-Migrate (lightweight, integrates with Flask)
- **Decision Needed:** Before Phase 1B-Step 4

### Reviewer Identity Representation
- **Q:** How is reviewer identity stored in review_decisions.reviewer?
  - Simple username (email) string?
  - UUID of reviewer account?
  - Integration with authentication system?
- **Proposal:** Simple email string, no foreign key
- **Decision Needed:** Before Phase 1B-Step 5

### Raw CSV Row Storage
- **Q:** How are raw CSV rows stored in raw_import_rows.raw_data?
  - JSON column?
  - Normalized columns + JSON for extras?
  - Full CSV line as-is?
- **Proposal:** JSON column for flexibility, indexed normalized columns (name, email, phone) for queries
- **Decision Needed:** Before Phase 1B-Step 4

### Validation Findings Storage
- **Q:** Store or compute on-demand in Phase 1B?
- **Proposal:** Compute on-demand (Phase 1B); optional storage in Phase 1B-Step 6+
- **Decision Needed:** Before Phase 1B-Step 5 (implementation)

### Export Staging Storage
- **Q:** Store or compute on-demand in Phase 1B?
- **Proposal:** Compute on-demand (Phase 1B); optional storage in Phase 2 (file generation)
- **Decision Needed:** Before Phase 1B-Step 5 (implementation)

---

## 15. Phase 1B-Step 2 Acceptance Gate (THIS DOCUMENT)

**This document is ready for stakeholder review and approval.**

### What Approval Means

✅ Schema proposal is acceptable
✅ Database design is sound
✅ Constraints are clear and enforceable
✅ Migration path is realistic
✅ Risk mitigations are adequate

### What Approval Does NOT Allow

❌ No migrations may be created
❌ No ORM models may be written
❌ No database code may be added
❌ No repository implementation may begin
❌ No schema may be created in database
❌ No application code may be modified

### What Happens After Approval

1. Phase 1B-Step 3: Repository interface/protocol is designed
2. Phase 1B-Step 4: Migrations and models are implemented
3. Phase 1B-Step 5: First database repository is implemented
4. ... (steps 6+)

### If Feedback Requires Revision

This document will be revised and resubmitted for approval before implementation begins.

---

## 16. Acceptance Criteria for This Document

This document is acceptable if:

✅ **It is documentation-only**
- No Python code
- No SQL code
- No migrations
- No ORM models
- No database implementation

✅ **It preserves Phase 1A service boundaries**
- Routes unchanged
- Service method signatures unchanged
- View model names match actual Phase 1A contracts (from service_contracts.py)
- Repository contract mirrors FixtureImportRepository methods

✅ **It preserves Phase 0 UI**
- No template changes proposed
- No route behavior changes proposed
- UI remains identical to Phase 1A

✅ **It clearly separates raw data from decisions**
- raw_import_rows table is immutable
- All review data in separate tables
- No mutation of raw rows by decisions
- Clear data flow from raw → decisions → staging

✅ **It avoids global canonical identities**
- No language implying permanent canonical/master records
- No "master person" or "merged record" fields
- Households and duplicates are import-local
- Decisions are audit-able and decision-specific

✅ **It avoids Givebutter/CRM writeback**
- No external API calls in schema
- No Givebutter sync fields
- No CRM integration in proposed schema
- Decisions are internal only

✅ **It proposes an incremental, reviewable Phase 1B path**
- Clear steps from schema to single-route implementation to all routes
- Each step is reviewable and testable independently
- Parity tests ensure database implementation is correct
- Rollback is possible at each step

✅ **It does not add implementation code**
- Can be reviewed and approved in one meeting
- No code review cycles needed
- Ready to move to Phase 1B-Step 3 (repository interface)

✅ **It clearly separates read-only from future write operations**
- Phase 1B-Step 5 repository contract is read-only
- Future decision-recording APIs are marked as out-of-scope for Phase 1B-Step 5
- Decision API is planned for Phase 1B-Step 6+

✅ **It clarifies validation findings and export staging**
- Validation findings: Computed on-demand in Phase 1B-Step 5
- Export staging: Computed from decisions in Phase 1B-Step 5
- Both can be stored in Phase 2+ if performance requires
- No storage overhead in Phase 1B

---

## Summary

This document proposes a Phase 1B database persistence design that:

1. **Preserves Phase 1A architecture** — Services and templates remain data-source agnostic
2. **Protects raw data** — Immutable raw_import_rows, all decisions in separate tables
3. **Maintains constraints** — No writeback, no cross-import matching, no canonical identities
4. **Enables incremental migration** — One route at a time, with parity testing
5. **Remains testable** — Fixture and database implementations can be verified in parallel
6. **Defers risky decisions** — File generation, external APIs, cross-import logic deferred to Phase 2+
7. **Has explicit acceptance gate** — Stakeholder approval required before Phase 1B-Step 3 begins

**Next step:** Stakeholder review and acceptance of this schema proposal (Phase 1B-Step 2).

After acceptance, Phase 1B-Step 3 (repository interface design) may begin.

---

**Document Status:** ✅ Ready for Phase 1B-Step 2 acceptance review  
**Implementation Status:** Not started  
**Phase 1A Status:** Complete and preserved  
**Phase 1B Status:** Planning phase (this document) + acceptance gate
