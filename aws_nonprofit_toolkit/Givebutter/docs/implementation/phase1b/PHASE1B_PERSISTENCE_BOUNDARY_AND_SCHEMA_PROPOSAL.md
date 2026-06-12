# Phase 1B Persistence Boundary and Schema Proposal

**Status:** Documentation-only proposal. No implementation code.

**Purpose:** Design Phase 1B database persistence behind the Phase 1A service boundary while preserving routes, services, templates, and Phase 0 UI.

**Next Step:** Review and acceptance by stakeholders before Phase 1B implementation begins.

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

**Key principle:** Services and templates remain data-source agnostic. The repository implementation (fixture-backed or database-backed) is swappable.

### What Changes in Phase 1B
- Underlying repository implementation switches from fixtures to database
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
- All normalization, deduplication, household grouping are decisions about export staging only

✅ **Reviewer decisions are stored separately from raw data.**
- Separate tables for validation findings, normalization suggestions, duplicate decisions, household decisions
- Raw rows are never mutated by review decisions
- Decisions reference raw rows by ID without modifying them

### Review Decision Semantics
✅ **Reviewer decisions affect export staging only.**
- Approve/reject/defer decisions determine what gets staged for export
- Decisions do not change raw row data
- Decisions do not create permanent global master records
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
- No cross-import deduplication
- No cross-import household matching
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
Service Module (e.g., dashboard_service.get_dashboard_overview())
    ↓
FixtureImportRepository (in-memory fixture data)
    ↓
View Models (frozen dataclasses: DashboardOverviewViewModel, etc.)
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
Service Module (same interface)
    ↓
Repository Interface/Protocol (abstract contract)
    ├─→ FixtureImportRepository (Phase 1A fallback)
    └─→ DatabaseImportRepository (Phase 1B implementation)
    ↓
View Models (same frozen dataclasses)
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

## 4. Repository Contract Proposal

All methods return frozen view model instances that are converted to dicts for templates. None mutate raw data.

### `list_imports() → List[ImportSummaryViewModel]`
**Purpose:** List all import batches with metadata.

**Behavior:**
- Read-only
- Returns list of imports with batch ID, filename, upload date, reviewer count, status counts
- Fixture implementation: wraps IMPORT_BATCH list
- Database implementation: queries `imports` table with summary counts

**Immutability:** Does not mutate any data

---

### `get_dashboard(import_id: str) → DashboardOverviewViewModel`
**Purpose:** Get high-level import review status and metrics.

**Behavior:**
- Read-only
- Returns: batch info, total records, validation status, duplicate count, household count, review statistics
- Database implementation: computes counts from raw rows and review decisions

**Immutability:** Does not mutate any data

---

### `get_validation(import_id: str) → ValidationReviewViewModel`
**Purpose:** Get validation review page data (validation findings per record).

**Behavior:**
- Read-only
- Returns: validation findings grouped by severity, record-by-record details
- Database implementation: queries raw rows and validation findings table

**Immutability:** Does not mutate any data

---

### `get_normalizations(import_id: str) → NormalizationReviewViewModel`
**Purpose:** Get normalization review page data (suggested corrections per field).

**Behavior:**
- Read-only
- Returns: normalization suggestions grouped by field and confidence, record-by-record details
- Database implementation: queries raw rows and normalization suggestions table

**Immutability:** Does not mutate any data

---

### `get_households(import_id: str) → HouseholdReviewViewModel`
**Purpose:** Get household grouping suggestions and current decisions.

**Behavior:**
- Read-only
- Returns: suggested household groups, members per group, confidence, basis, existing decisions
- Database implementation: queries household suggestions and review decisions tables

**Immutability:** Does not mutate any data

---

### `get_duplicates(import_id: str) → DuplicateReviewViewModel`
**Purpose:** Get duplicate candidate pairs and current decisions.

**Behavior:**
- Read-only
- Returns: duplicate candidate pairs, confidence, evidence, conflicts, existing decisions
- Database implementation: queries duplicate candidates and review decisions tables

**Immutability:** Does not mutate any data

---

### `get_audit(import_id: str) → AuditLogViewModel`
**Purpose:** Get audit log of all reviewer decisions.

**Behavior:**
- Read-only
- Returns: chronological log of decisions (approvals, rejections, confirmations, edits)
- Append-only: new entries added, never edited or deleted
- Database implementation: queries audit log table in order

**Immutability:** Does not mutate any data

---

### `get_exports(import_id: str) → ExportConsoleViewModel`
**Purpose:** Get export staging and export package metadata.

**Behavior:**
- Read-only for display
- Returns: export staging record count, export card definitions, recent export packages (metadata only)
- No file generation
- Database implementation: queries export staging and export packages tables

**Immutability:** Does not mutate any data (read-only in Phase 1B)

---

## 5. Proposed Database Schema

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
  (import_id, email) for dedup matching
  (import_id, phone) for dedup matching
  (import_id, name) for fuzzy matching
```

### Table: `validation_findings`
**Purpose:** Validation issues detected in raw rows.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Validation finding ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  raw_row_id (TEXT NOT NULL FK→raw_import_rows.id)  — Which row
  field_name (TEXT NOT NULL)               — e.g., "email", "phone", "amount"
  finding_type (TEXT NOT NULL)             — e.g., "invalid_format", "typo_suggestion", "range_warning"
  severity (TEXT NOT NULL)                 — "error", "warning", "info"
  message (TEXT)                           — Human-readable description
  suggested_value (TEXT)                   — Suggested correction (if applicable)
  created_at (TIMESTAMP DEFAULT NOW())     — When finding was detected
  (Append-only after creation)

Constraints:
  FK: raw_row_id references raw_import_rows.id
  FK: import_id references imports.id

Example:
  id: "VF-001"
  import_id: "IMP-2025-0101-A"
  raw_row_id: "IMP-2025-0101-A/row-42"
  field_name: "email"
  finding_type: "typo_suggestion"
  severity: "warning"
  message: "Did you mean gmail.com? (found: gmai.com)"
  suggested_value: "john@gmail.com"
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
**Purpose:** Suggested duplicate pairs.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Candidate ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  raw_row_id_a (TEXT NOT NULL FK→raw_import_rows.id)  — First row
  raw_row_id_b (TEXT NOT NULL FK→raw_import_rows.id)  — Second row
  match_type (TEXT)                        — "exact_email", "exact_phone", "fuzzy_name", "address_overlap"
  confidence (DECIMAL 0-1)                 — Confidence of match
  evidence (JSON)                          — Details of matching (e.g., {"field": "email", "a": "john@gmail.com", "b": "john@gmail.com"})
  conflicts (JSON)                         — Fields that differ (e.g., {"name": ["John Doe", "J. Doe"], "phone": ["555-1234", "555-1235"]})
  created_at (TIMESTAMP DEFAULT NOW())
  (Append-only after creation)

Constraints:
  FK: raw_row_id_a references raw_import_rows.id
  FK: raw_row_id_b references raw_import_rows.id
  FK: import_id references imports.id
  RULE: raw_row_id_a < raw_row_id_b (to avoid duplicates)

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
**Purpose:** Suggested household groupings.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Household suggestion ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  suggested_label (TEXT)                   — e.g., "Doe Household", "Account #12345"
  confidence (DECIMAL 0-1)                 — Confidence of grouping
  basis (TEXT)                             — How grouped (e.g., "shared_address", "shared_email_domain", "matching_last_name")
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
**Purpose:** Reviewer decisions on validation, normalization, duplicates, and households.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Decision ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  decision_type (TEXT NOT NULL)            — "validation_approval", "normalization_choice", "duplicate_judgment", "household_judgment"
  target_id (TEXT)                         — ID of what's being reviewed (finding, suggestion, candidate, etc.)
  target_raw_row_ids (JSON ARRAY)          — Raw row IDs affected by this decision
  decision (TEXT NOT NULL)                 — "approve", "reject", "defer", "confirm", "different", "same_person", "group_yes", "group_no"
  reviewed_values (JSON)                   — For normalization decisions: {"field": "phone", "raw": "555-1234", "normalized": "5551234567", "chosen": "normalized"}
  reviewer (TEXT)                          — User who made decision (if applicable)
  created_at (TIMESTAMP DEFAULT NOW())
  (Append-only, never modified)

Constraints:
  FK: import_id references imports.id
  RULE: Append-only, immutable after creation

Example (normalization approval):
  id: "RD-001"
  import_id: "IMP-2025-0101-A"
  decision_type: "normalization_choice"
  target_id: "NS-001"
  target_raw_row_ids: ["IMP-2025-0101-A/row-42"]
  decision: "approve"
  reviewed_values: {"field": "phone", "raw": "(555) 123-4567 ext 890", "normalized": "5551234567", "chosen": "normalized"}
  reviewer: "alice@example.com"

Example (duplicate judgment):
  id: "RD-002"
  import_id: "IMP-2025-0101-A"
  decision_type: "duplicate_judgment"
  target_id: "DC-001"
  target_raw_row_ids: ["IMP-2025-0101-A/row-42", "IMP-2025-0101-A/row-87"]
  decision: "same_person"
  reviewed_values: null
  reviewer: "bob@example.com"
```

### Table: `export_staging_records`
**Purpose:** Records staged for export (computed from raw rows + decisions).

```
Columns:
  id (TEXT PRIMARY KEY)                    — Staging record ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  raw_row_id (TEXT NOT NULL FK→raw_import_rows.id)  — Source raw row
  staged_status (TEXT)                     — "staged", "rejected", "review_needed"
  staging_reason (TEXT)                    — Why in this status (e.g., "approved", "validation_failed", "awaiting_decision")
  applied_decisions (JSON ARRAY)           — List of decision IDs that affect this record
  export_data (JSON)                       — Data to be exported (raw + normalization choices)
  created_at (TIMESTAMP DEFAULT NOW())
  updated_at (TIMESTAMP DEFAULT NOW())
  (Updated when decisions change)

Constraints:
  FK: raw_row_id references raw_import_rows.id
  FK: import_id references imports.id

Example:
  id: "ESR-001"
  import_id: "IMP-2025-0101-A"
  raw_row_id: "IMP-2025-0101-A/row-42"
  staged_status: "staged"
  staging_reason: "approved"
  applied_decisions: ["RD-001", "RD-002"]
  export_data: {"name": "John Doe", "email": "john@example.com", "phone": "5551234567", ...}
```

### Table: `export_packages`
**Purpose:** Metadata for export package runs (not the files themselves).

```
Columns:
  id (TEXT PRIMARY KEY)                    — Package ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  package_type (TEXT)                      — e.g., "reviewed_export", "household_export", "donation_list"
  created_at (TIMESTAMP DEFAULT NOW())
  created_by (TEXT)                        — User who triggered export
  record_count (INTEGER)                   — How many records included
  file_status (TEXT)                       — "metadata_only" (Phase 1B) or "generated" (Phase 2+)
  file_path (TEXT)                         — Path to generated file (Phase 2+), NULL in Phase 1B
  generated_at (TIMESTAMP)                 — When file was actually generated (NULL in Phase 1B)

Constraints:
  FK: import_id references imports.id
  NOTE: In Phase 1B, file_status is always "metadata_only" and file_path is always NULL

Example:
  id: "EP-001"
  import_id: "IMP-2025-0101-A"
  package_type: "reviewed_export"
  created_at: 2025-01-20 14:30:00
  created_by: "alice@example.com"
  record_count: 1200
  file_status: "metadata_only"
  file_path: null
  generated_at: null
```

### Table: `audit_log`
**Purpose:** Immutable record of all reviewer actions.

```
Columns:
  id (TEXT PRIMARY KEY)                    — Audit entry ID
  import_id (TEXT NOT NULL FK→imports.id)  — Which import
  action_type (TEXT NOT NULL)              — "validation_reviewed", "normalization_reviewed", "duplicate_reviewed", "household_reviewed", "export_staged"
  action_timestamp (TIMESTAMP DEFAULT NOW()) — When action occurred
  actor (TEXT)                             — User who performed action
  target_type (TEXT)                       — "raw_row", "validation_finding", "normalization_suggestion", "duplicate_candidate", "household_suggestion"
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
  action_type: "validation_reviewed"
  action_timestamp: 2025-01-20 10:15:00
  actor: "alice@example.com"
  target_type: "validation_finding"
  target_id: "VF-001"
  decision_id: "RD-001"
  details: {"finding": "email_typo", "suggested": "john@gmail.com", "status": "approved"}
```

---

## 6. Household Modeling

### Design Principles

1. **Suggestions, Not Confirmations**
   - Household suggestions are generated by matching algorithms
   - Suggestions are advisory only
   - Reviewer confirms or rejects, not auto-confirmed

2. **Decoupled from Raw Rows**
   - Suggestions reference raw rows by ID
   - Raw rows are never mutated to indicate household membership
   - Households are a review-time grouping, not raw data property

3. **Export-Staging Focused**
   - Confirmed households determine export staging relationships
   - Multiple members may be grouped in export
   - No global master household record in v1

### Schema Design

**`household_suggestions` table** (see schema section above)
- `suggested_label`: Label for the grouping (e.g., "Doe Family")
- `confidence`: Match confidence (0-1)
- `basis`: Why grouped (shared address, email domain, fuzzy name match, etc.)
- `member_raw_row_ids`: JSON array of row IDs in group

**`review_decisions` table** records household confirmations
```
decision_type: "household_judgment"
decision: "group_yes" or "group_no"
target_raw_row_ids: ["row-42", "row-87", "row-101"]
```

**`export_staging_records` tracks household membership** for export
```
export_data: {..., "household_id": "HH-001", "household_members": 3}
```

### Important Constraints

- A household suggestion is NOT a permanent record
- Once reviewed (confirmed or rejected), the decision is recorded in `review_decisions`
- Export staging uses confirmed decisions to group records
- In Phase 1B, no changes to household memberships after staging
- No cross-import household matching
- No syncing to Givebutter or CRM

### Household Review Logic (Implementation Phase)

When reviewer views households:
1. Display suggestions from `household_suggestions`
2. Show current decisions from `review_decisions` (if any)
3. Reviewer confirms or rejects
4. Decision recorded in `review_decisions`
5. Export staging recomputed if needed

---

## 7. Duplicate Modeling

### Design Principles

1. **Candidates, Not Automations**
   - Duplicates are algorithmic suggestions
   - No automatic merging or deduplication
   - Reviewer makes explicit "same person" or "different" judgment

2. **Decoupled from Raw Data**
   - Suggestions are stored in `duplicate_candidates` table
   - Raw rows remain immutable
   - Decisions are recorded in `review_decisions`
   - Export staging applies decisions (one or both rows, neither, etc.)

3. **No Master Person Record**
   - v1 does not create global "master" person records
   - Decisions mark duplicates for export staging only
   - Actual deduplication/merging is Phase 2 or later

### Schema Design

**`duplicate_candidates` table** (see schema section above)
- `match_type`: How pair was identified (exact email, fuzzy name, etc.)
- `confidence`: Match confidence (0-1)
- `evidence`: Matching details (which field, what values)
- `conflicts`: Fields that differ between the two rows

**`review_decisions` table** records duplicate judgments
```
decision_type: "duplicate_judgment"
decision: "same_person", "different", or "defer"
target_raw_row_ids: ["row-42", "row-87"]
```

**`export_staging_records`** applies decisions
```
staged_status: "staged" or "rejected" based on duplicate decisions
```

### Important Constraints

- A duplicate candidate is a suggestion only
- "Same person" decision does NOT mutate either raw row
- "Same person" decision indicates both/one row should be included in export
- "Different" decision indicates both rows are distinct
- "Defer" decision leaves staging status pending
- No cross-import deduplication
- No syncing to Givebutter or CRM

### Duplicate Review Logic (Implementation Phase)

When reviewer views duplicates:
1. Display candidates from `duplicate_candidates`
2. Show current decisions from `review_decisions` (if any)
3. Reviewer chooses: "Same Person", "Different", or "Defer"
4. Decision recorded in `review_decisions`
5. Export staging recomputed if needed

---

## 8. Normalization Modeling

### Design Principles

1. **Suggestions, Not Automatic Changes**
   - Normalization algorithms suggest corrections (phone formatting, address parsing, etc.)
   - Raw field values remain unchanged
   - Reviewer accepts or rejects suggestion
   - Export staging uses reviewer's choice (raw or normalized)

2. **Preserve Raw Values**
   - Original value always stored in `raw_import_rows`
   - Normalized suggestion stored separately in `normalization_suggestions`
   - Raw value is audit trail and fallback

3. **Per-Field Decisions**
   - Reviewer decides per field, per row
   - Some fields normalized, others kept raw in same export

### Schema Design

**`normalization_suggestions` table** (see schema section above)
- `field_name`: Which field (phone, address, name, etc.)
- `raw_value`: Value from CSV
- `normalized_value`: Suggested normalized form
- `confidence`: Confidence of suggestion
- `basis`: Which normalization rule/algorithm

**`review_decisions` table** records normalization choices
```
decision_type: "normalization_choice"
decision: "approve" (use normalized) or "reject" (use raw)
reviewed_values: {
  "field": "phone",
  "raw": "(555) 123-4567 ext 890",
  "normalized": "5551234567",
  "chosen": "normalized"
}
target_raw_row_ids: ["row-42"]
```

**`export_staging_records`** stores the chosen value
```
export_data: {
  "phone_raw": "(555) 123-4567 ext 890",
  "phone_staged": "5551234567"  // what goes to export
}
```

### Important Constraints

- Raw values are never changed in `raw_import_rows`
- Normalization suggestions are immutable after creation
- Decisions are recorded separately
- Export uses chosen value (raw or normalized)
- Normalization is import-specific

### Normalization Review Logic (Implementation Phase)

When reviewer views normalizations:
1. Display suggestions from `normalization_suggestions`
2. Show current decisions from `review_decisions` (if any)
3. Reviewer approves or rejects each suggestion
4. Decision recorded in `review_decisions`
5. Export staging updated with chosen values

---

## 9. Validation Modeling

### Design Principles

1. **Derived, Not Stored**
   - Validation findings are derived from raw row data
   - Findings reference raw rows by ID
   - Findings may be recalculated if validation rules change

2. **Non-Mutating**
   - Validation findings do not change raw rows
   - Findings are advisory (suggestions to fix, warnings)
   - Reviewer approves or rejects the fix (which is a normalization decision)

3. **Filtering and Prioritization**
   - Validation findings help reviewer prioritize rows
   - Can filter by severity (error, warning, info)
   - Can filter by field or finding type

### Schema Design

**`validation_findings` table** (see schema section above)
- `field_name`: Which field has an issue
- `finding_type`: What kind of issue (typo, range, format, etc.)
- `severity`: error, warning, or info
- `message`: Human-readable description
- `suggested_value`: For typo/format findings, suggested correction

**Review Workflow**
- Validation findings are displayed in the validation route
- Reviewer can choose to apply a finding (which creates a normalization suggestion approval) or ignore it
- Decisions are recorded in `review_decisions` (as normalization choices)

### Important Constraints

- Validation findings are ephemeral (can be regenerated)
- Findings do not change raw rows
- Findings are informational only
- Fixing a validation issue is a normalization decision (separate)

### Validation Review Logic (Implementation Phase)

When reviewer views validation:
1. Display findings from `validation_findings` grouped by severity/field
2. For each finding, show suggested fix if applicable
3. Reviewer can "apply" a suggestion (creates normalization decision) or skip
4. Skipped findings are not recorded (they're just not acted upon)

---

## 10. Export Staging Model

### Design Principles

1. **Computed, Not Manual**
   - Export staging is a view computed from raw rows + decisions
   - No manual "approve for export" step in v1
   - Staging is deterministic given raw data and decisions

2. **No File Generation Yet**
   - Phase 1B: metadata-only (record counts, package definitions)
   - Phase 2: actual file generation (CSV, etc.)
   - Files are never generated during Phase 1B

3. **Reproducible and Auditable**
   - Staging state at any time can be recomputed
   - Audit log shows what decisions led to staging
   - Export packages record what was intended to be exported

### Schema Design

**`export_staging_records` table** (see schema section above)
- Records staged for export (one per raw row)
- `staged_status`: staged, rejected, or review_needed
- `staging_reason`: Why in this status
- `applied_decisions`: List of decision IDs that determined staging
- `export_data`: Data to be exported

**`export_packages` table** (see schema section above)
- Metadata for export package runs
- `package_type`: reviewed_export, household_export, etc.
- `record_count`: How many records would be included
- `file_status`: always "metadata_only" in Phase 1B
- `file_path`: always NULL in Phase 1B

### Important Constraints

- Export staging is read-only in Phase 1B
- No actual files are written
- Export packages are metadata snapshots
- Export staging can be recomputed if decisions change
- Export decisions do not affect raw data

### Export Staging Logic (Implementation Phase)

When reviewer views exports:
1. Compute staging from raw rows + decisions
2. Count staged/rejected records
3. Show export card definitions (metadata)
4. Allow "preview" of staging records (in-memory, not file)
5. Show previous export packages (if any)
6. In Phase 1B, no file generation button

---

## 11. Audit Model

### Design Principles

1. **Append-Only**
   - Audit log is immutable
   - Every reviewer action is recorded with timestamp and actor
   - No edits or deletions to audit log

2. **Comprehensive**
   - Every decision is audited
   - Decision details are recorded (raw vs normalized, etc.)
   - Timestamps allow reconstruction of state at any time

3. **UI-Independent**
   - Audit is not editable through any UI
   - Not visible to reviewers (for now) but available for administrative review
   - Can be used to debug or reconstruct decision history

### Schema Design

**`audit_log` table** (see schema section above)
- `action_type`: What was done (validation_reviewed, duplicate_reviewed, etc.)
- `action_timestamp`: When it happened
- `actor`: Who did it (user, system, etc.)
- `target_type`: What was reviewed (raw_row, finding, candidate, etc.)
- `target_id`: Which specific thing was reviewed
- `decision_id`: Link to the decision record
- `details`: JSON with context (finding type, suggested value, etc.)

### Important Constraints

- Immutable after creation
- No updates or deletions
- Timestamps are accurate
- Actor field is recorded (for accountability)
- Decision links allow tracing decisions to actions

### Audit Usage (Implementation Phase)

- No UI display in Phase 1B (but can be queried for debugging)
- Available for export or report generation
- Can reconstruct state at any time
- Can audit reviewer behavior if needed later

---

## 12. Migration Strategy

### Recommended Phased Approach

**Phase 1B-Step 1: This Document**
- Documentation-only schema proposal
- Define all tables, constraints, and relationships
- Define repository contract
- **Status:** Complete (this document)

**Phase 1B-Step 2: Schema Review and Acceptance**
- Stakeholders review proposal
- Ask questions, suggest changes
- Final schema design accepted before code
- **Deliverable:** Schema formally accepted

**Phase 1B-Step 3: Repository Interface/Protocol Only**
- Define Python protocol/abstract class for repository
- No database code yet
- Just the interface that `FixtureImportRepository` and `DatabaseImportRepository` will implement
- Fixture implementation unchanged
- **Deliverable:** Abstract `ImportRepository` protocol

**Phase 1B-Step 4: Migrations and Models**
- Create database migrations (schema, indexes, constraints)
- Create SQLAlchemy models or raw SQL schema
- Create fixtures or seeds for testing
- **Deliverable:** Database schema created and tested

**Phase 1B-Step 5: Database Repository Implementation**
- Implement `DatabaseImportRepository` for one route (e.g., `/imports`)
- Implement all methods for that route
- Run alongside fixture implementation for parity testing
- **Deliverable:** First route database-backed and tested

**Phase 1B-Step 6: Fixture-vs-Database Parity Tests**
- Compare fixture and database outputs for same import
- Verify they produce identical view models
- Run regression tests on Phase 1A routes
- **Deliverable:** Parity verified, no regression

**Phase 1B-Step 7+: Migrate Remaining Routes**
- One route at a time: validation, normalizations, households, duplicates, audit, exports
- Verify each route in parallel (fixture + database)
- Merge to main when fully tested
- **Deliverable:** All 8 routes database-backed

### Rationale for This Sequence

1. **Schema First:** No code until schema is agreed
2. **Interface Before Implementation:** Contract before implementation details
3. **Database Setup Before Code:** Migrations work before ORM code depends on them
4. **One Route at a Time:** Lowest risk, easiest to debug, easy to rollback
5. **Parity Tests:** Fixture-backed tests ensure database implementation is correct
6. **Incremental Merge:** Each step can be merged and validated independently

---

## 13. Test Strategy

### Repository Contract Tests
**Purpose:** Ensure both fixture and database implementations meet the interface contract.

**For each repository method, test:**
- Returns correct view model type
- Returns immutable data (frozen dataclass)
- Does not mutate raw data
- Handles missing/invalid import IDs correctly
- Handles edge cases (empty import, no decisions, etc.)

**Example test:**
```
def test_get_dashboard_returns_dashboard_overview_view_model():
    # Both FixtureImportRepository and DatabaseImportRepository should pass
    repo = get_repository_under_test()
    result = repo.get_dashboard("IMP-2025-0101-A")
    assert isinstance(result, DashboardOverviewViewModel)
    assert result.batch.id == "IMP-2025-0101-A"
    # Verify immutability
    with pytest.raises(AttributeError):
        result.batch.id = "different"
```

### Fixture-vs-Database Parity Tests
**Purpose:** Verify that database implementation returns identical data as fixture implementation.

**For each route, test:**
- Same import ID, both implementations return same view model dict
- Same record counts, same status summaries, same findings
- No differences in field values

**Example test:**
```
def test_dashboard_fixture_and_database_parity():
    fixture_repo = FixtureImportRepository()
    db_repo = DatabaseImportRepository()
    
    fixture_result = fixture_repo.get_dashboard("IMP-2025-0101-A")
    db_result = db_repo.get_dashboard("IMP-2025-0101-A")
    
    assert fixture_result.to_template_dict() == db_result.to_template_dict()
```

### Route Regression Tests
**Purpose:** Ensure Phase 1A routes still work correctly with database backend.

**For each route, test:**
- Route returns 200 status
- Page contains expected content (titles, counts, cards, buttons)
- No forbidden vocabulary
- No forbidden technology
- Phase 0 UI preserved

**Example test:**
```
def test_dashboard_route_with_database_backend_returns_200():
    client = app.test_client()
    response = client.get('/imports/IMP-2025-0101-A/dashboard')
    assert response.status_code == 200
    assert b'Import Dashboard' in response.data
    assert b'Status Summary' in response.data
```

### Raw-Row Immutability Tests
**Purpose:** Verify raw data is never mutated.

**Tests:**
- Before and after any repository operation, raw rows are identical
- No UPDATE or DELETE on raw_import_rows table
- All changes are in decision/staging tables only

**Example test:**
```
def test_raw_rows_never_mutated_by_decision_recording():
    repo = DatabaseImportRepository()
    
    # Get raw row before decision
    raw_before = db.execute("SELECT * FROM raw_import_rows WHERE id = ?", (row_id,))
    
    # Record a decision
    repo.record_duplicate_decision(...)  # hypothetical method
    
    # Get raw row after decision
    raw_after = db.execute("SELECT * FROM raw_import_rows WHERE id = ?", (row_id,))
    
    assert raw_before == raw_after
```

### Decision/Audit Append-Only Tests
**Purpose:** Verify decisions and audit logs are never edited or deleted.

**Tests:**
- Review decisions table has no UPDATE or DELETE operations
- Audit log table has no UPDATE or DELETE operations
- Only INSERT operations succeed
- UPDATE/DELETE operations fail with constraint error

**Example test:**
```
def test_review_decisions_append_only():
    decision_id = "RD-001"
    
    # Try to update a decision (should fail)
    with pytest.raises(Exception):  # constraint violation
        db.execute("UPDATE review_decisions SET decision = ? WHERE id = ?", 
                   ("approve", decision_id))
    
    # Verify original decision unchanged
    result = db.execute("SELECT decision FROM review_decisions WHERE id = ?", (decision_id,))
    assert result[0] == "same_person"
```

### No-Writeback Tests
**Purpose:** Verify no external systems are called.

**Tests:**
- No calls to Givebutter API
- No calls to CRM APIs
- No HTTP requests to external systems
- No file system writes (in Phase 1B)

**Example test:**
```
def test_no_givebutter_calls_during_review():
    with patch('requests.post') as mock_post:
        repo = DatabaseImportRepository()
        repo.record_decision(...)
        mock_post.assert_not_called()
```

### Export No-File-Generation Tests
**Purpose:** Verify no files are written in Phase 1B.

**Tests:**
- Export packages have file_status = "metadata_only"
- No files written to disk
- No file path is set
- Export staging is in-memory only

**Example test:**
```
def test_export_staging_metadata_only_in_phase1b():
    repo = DatabaseImportRepository()
    
    # Trigger export (should not write files)
    exports = repo.get_exports("IMP-2025-0101-A")
    
    # Verify no files written
    assert not os.path.exists('/tmp/export-*')
    
    # Verify metadata status
    package = db.execute("SELECT file_status FROM export_packages ORDER BY created_at DESC LIMIT 1")[0]
    assert package['file_status'] == 'metadata_only'
```

---

## 14. Risks and Mitigations

### Risk: ORM Objects Leak into Templates

**Risk:** SQLAlchemy model instances are passed to templates instead of plain dicts, exposing ORM behavior and database internals.

**Mitigation:**
- Repository must return frozen dataclasses (view models), not ORM instances
- View models have `to_template_dict()` methods that return plain dicts
- Routes call `to_template_dict()` before passing to template
- Tests verify no ORM types in template context
- Code review checks for `.objects`, `.query`, `Model()` in route handler

**Test:**
```
def test_no_orm_objects_in_template_context():
    response = client.get('/imports/IMP-2025-0101-A/dashboard')
    context = response.context  # Flask test client
    for value in context.values():
        assert not isinstance(value, (Base, DeclarativeMeta))  # no SQLAlchemy
```

### Risk: UI Changes Mixed with Persistence Changes

**Risk:** Phase 1B introduces both new database code and unintended UI/route changes.

**Mitigation:**
- Phase 1B changes to repository implementation only
- No route handler modifications
- No template changes
- No service method signatures changed
- Code review enforces this separation
- Phase 1A route regression tests verify no UI changes

**Test:**
```
def test_phase1a_routes_unchanged_after_phase1b_database_migration():
    # Run Phase 1A regression suite
    # All 26 tests from test_exports_route.py (Step 8) should pass unchanged
    pytest tests/integration/test_*_route.py
```

### Risk: Raw Data Mutation

**Risk:** Database code directly mutates raw_import_rows table.

**Mitigation:**
- raw_import_rows table has database constraint: no UPDATE or DELETE after creation
- Code review looks for any UPDATE/DELETE on raw_import_rows
- Raw-row immutability tests verify constraint works
- Decisions are stored in separate tables

**Test:**
```
def test_raw_import_rows_cannot_be_updated():
    with pytest.raises(IntegrityError):
        db.execute("UPDATE raw_import_rows SET name = ? WHERE id = ?", ("New Name", row_id))
```

### Risk: Accidental Cross-Import Matching

**Risk:** Duplicate or household algorithms accidentally match rows across different imports.

**Mitigation:**
- All suggestion tables (duplicate_candidates, household_suggestions) have import_id FK
- Code review checks that all queries filter by import_id
- Tests use multiple imports and verify no cross-import matches
- Queries with missing import_id filter should fail code review

**Test:**
```
def test_no_duplicate_candidates_across_imports():
    # Create two imports
    imp1 = create_import("IMP-001")
    imp2 = create_import("IMP-002")
    
    # Add same email to both imports
    add_row(imp1, "john@example.com")
    add_row(imp2, "john@example.com")
    
    # Run dedup algorithm
    run_dedup()
    
    # Verify no candidate pair cross imports
    candidates = db.execute("SELECT * FROM duplicate_candidates WHERE import_id = ?", (imp1,))
    for c in candidates:
        assert c['raw_row_id_a'].startswith(imp1)
        assert c['raw_row_id_b'].startswith(imp1)
```

### Risk: Premature Export File Generation

**Risk:** Export file generation code is added in Phase 1B, before schema is fully tested.

**Mitigation:**
- Phase 1B allows no file writing
- export_packages.file_status must always be "metadata_only"
- export_packages.file_path must always be NULL
- Code review blocks any file I/O in Phase 1B
- Tests verify no files created
- File generation deferred to Phase 2

**Test:**
```
def test_no_files_written_in_phase1b_export():
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = config.EXPORT_PATH
        config.EXPORT_PATH = tmpdir
        
        try:
            repo = DatabaseImportRepository()
            repo.get_exports("IMP-2025-0101-A")
            
            # Verify nothing written
            assert len(os.listdir(tmpdir)) == 0
        finally:
            config.EXPORT_PATH = old_path
```

### Risk: Accidental Givebutter/CRM Writeback

**Risk:** Code accidentally calls Givebutter or CRM APIs during review.

**Mitigation:**
- No Givebutter or CRM API calls in Phase 1B code
- Code review explicitly checks for `requests.post/get`, API client imports
- Tests mock all external calls and verify they're not invoked
- CI/CD can block commits with external API imports

**Test:**
```
def test_no_external_api_calls_during_repository_operations():
    with patch('requests.post') as mock_post, \
         patch('requests.get') as mock_get:
        
        repo = DatabaseImportRepository()
        repo.get_dashboard("IMP-001")
        repo.record_decision(...)
        repo.get_exports("IMP-001")
        
        mock_post.assert_not_called()
        mock_get.assert_not_called()
```

### Risk: Schema Too Close to Global CRM/Master-Person Design

**Risk:** Household and duplicate tables imply permanent global master records, violating Phase 1B assumptions.

**Mitigation:**
- No `person_id` or `master_person_id` field in any table
- Household suggestions are import-specific and reviewable, not auto-merged
- Duplicate decisions are import-specific and do not create merged records
- Schema document explicitly rejects master-person language
- Code review questions any schema that implies global deduplication
- Documentation clarifies that v1 households are import-local

**Verification:**
- Review schema proposal (this document) language: no "master", no "merged", no "golden record"
- Household and duplicate decisions are import-scoped and audit-able
- Future phases can build on this with cross-import logic (Phase 2+)

---

## 15. Open Questions

### Database Choice
- **Q:** SQLite (current, single-file) or PostgreSQL (production-ready)?
- **Status:** Open. SQLite is sufficient for Phase 1B testing. PostgreSQL can be used if deployment is planned soon.
- **Decision Needed:** Before Phase 1B-Step 4 (migrations)

### ORM Framework
- **Q:** SQLAlchemy, Tortoise ORM, or raw SQL?
- **Status:** Open. SQLAlchemy is industry standard and has Flask integration (Flask-SQLAlchemy).
- **Decision Needed:** Before Phase 1B-Step 4. Current constraint: must not leak ORM objects to templates.

### Migrations Tool
- **Q:** Alembic (SQLAlchemy migrations), simple SQL files, or Flask-Migrate?
- **Status:** Open. Flask-Migrate is lightest weight. Alembic is standard for SQLAlchemy.
- **Decision Needed:** Before Phase 1B-Step 4.

### Reviewer Identity Representation
- **Q:** How is reviewer identity stored in `review_decisions.reviewer` and `audit_log.actor`?
  - Simple username string?
  - UUID of reviewer account?
  - Integration with authentication system?
- **Status:** Open. Current proposal: simple username (email) string, no foreign key to user table.
- **Decision Needed:** Before Phase 1B-Step 5 (first decision recording).

### Raw CSV Row Storage
- **Q:** How are raw CSV rows stored in `raw_import_rows.raw_data`?
  - JSON column (requires DBMS support)?
  - Normalized columns for common fields (name, email, phone) + JSON for extras?
  - Full CSV line stored as-is?
- **Status:** Open. Proposed: JSON column for flexibility, but normalized columns for common fields to allow efficient queries.
- **Decision Needed:** Before Phase 1B-Step 4 (schema finalization).

### Export Package Persistence Duration
- **Q:** How long should export package metadata (export_packages table) be retained?
  - Forever (for audit)?
  - 30 days?
  - Until next export?
- **Status:** Open. Proposed: Forever (audit trail). Can add retention policy later if storage is concern.
- **Decision Needed:** Before Phase 1B-Step 5 (first export metadata recorded).

### Export Package Metadata Sufficiency
- **Q:** Is metadata-only export sufficient for Phase 1B, or do we need file path/status tracking for Phase 2?
- **Status:** Open. Proposed: Metadata-only is sufficient. Phase 2 can add file generation and path tracking.
- **Decision Needed:** Before Phase 1B-Step 6 (export implementation).

### Audit Log Retention and Performance
- **Q:** Audit log will grow unbounded. Should we archive or partition?
- **Status:** Open. Not a concern for Phase 1B (small data). Can be addressed in Phase 2.
- **Decision Needed:** Before Phase 2 (if audit table grows large).

### Test Database Fixtures
- **Q:** Should tests use in-memory SQLite, test-specific SQLite file, or PostgreSQL test container?
- **Status:** Open. Proposed: In-memory SQLite for unit tests (fast), test container for integration tests (realistic).
- **Decision Needed:** Before Phase 1B-Step 4 (tests written).

### Decision Recording API
- **Q:** Should repository expose `record_decision()` method, or is decision recording handled separately?
- **Status:** Open. Proposed: Decisions are recorded through a separate method or endpoint, not part of read-only repository contract. May require new abstraction.
- **Decision Needed:** Before Phase 1B-Step 5 (first write operation).

### Validation Findings Persistence
- **Q:** Should validation findings be recomputed on-demand or stored in database?
- **Status:** Open. Proposed: Store in database for efficiency and auditability. Can be regenerated if rules change.
- **Decision Needed:** Before Phase 1B-Step 5 (validation route implementation).

---

## 16. Acceptance Criteria for This Document

This document is complete and acceptable if:

✅ **It is documentation-only**
- No Python code
- No SQL code
- No migrations
- No ORM models
- No database implementation

✅ **It preserves Phase 1A service boundaries**
- Routes unchanged
- Service method signatures unchanged
- View model definitions unchanged
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

✅ **It avoids global master entity design**
- No language implying permanent merged records
- No "master person" or "golden record" fields
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
- Can be reviewed and accepted in one meeting
- No code review cycles needed
- Ready to move to Phase 1B-Step 2 (schema acceptance)

---

## Summary

This document proposes a Phase 1B database persistence design that:

1. **Preserves Phase 1A architecture** — Services and templates remain data-source agnostic
2. **Protects raw data** — Immutable raw_import_rows, all decisions in separate tables
3. **Maintains constraints** — No writeback, no cross-import matching, no global master records
4. **Enables incremental migration** — One route at a time, with parity testing
5. **Remains testable** — Fixture and database implementations can be verified in parallel
6. **Defers risky decisions** — File generation, external APIs, cross-import logic deferred to Phase 2

**Next step:** Stakeholder review and approval of this schema proposal before Phase 1B-Step 3 (repository interface) begins.

---

**Document Status:** ✅ Ready for review  
**Implementation Status:** Not started  
**Phase 1A Status:** Complete and preserved  
**Phase 1B Status:** Planning phase (this document)
