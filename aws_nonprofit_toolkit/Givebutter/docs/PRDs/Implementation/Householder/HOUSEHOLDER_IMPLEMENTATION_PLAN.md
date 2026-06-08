# HOUSEHOLDER V1 IMPLEMENTATION PLAN

**Last Updated:** 2026-06-08  
**Status:** Final (Quality-first, aspirational timeline)

---

## BEFORE IMPLEMENTATION: CRITICAL DIRECTIVES

**These directives take precedence over all file paths and technical choices below.**

### ⚠️ PRD IS SOURCE OF TRUTH

Use this implementation plan as sequencing guidance. **If this plan and the Householder PRD conflict, follow the PRD unless this plan is explicitly safer.**

### ⚠️ DO NOT PROCEED WITHOUT ADAPTATION DOCUMENT

**Do not begin schema or route implementation until you have:**
1. Produced a repository adaptation document listing actual file paths (Flask app location, DB pattern, test layout, CSV column mapping)
2. Confirmed the Processor validation functions (actual names and signatures)
3. Verified how the Processor initializes its database and defines tables
4. Understood the existing test fixtures and patterns

**Pause after Step 1 (Processor Adapter) and show the adaptation document before proceeding to Step 2.**

### 1. Repository Structure First

Before writing any code, inspect the existing Givebutter Processor repository:
- File paths in this plan are **proposed, not mandatory**
- Adapt to the actual Flask app structure (where is app.py really?)
- Use the existing database initialization pattern (not SQLAlchemy/Alembic if repo doesn't use them)
- Use the existing test layout (pytest fixtures, conftest, test structure)
- Reuse Processor conventions: routing patterns, template structure, database access

**Action:** Inspect the repository and create an adaptation document listing actual paths before starting.

### 2. No New Frameworks Unless Necessary

- **Do not introduce Alembic** unless the Processor already uses it
- **Do not force SQLAlchemy ORM** if the Processor uses raw SQL or a different ORM
- **Do not create new app structures** — integrate into existing Flask app
- Use the existing Processor's database initialization pattern (SQL scripts, click commands, or ORM)
- If the repo doesn't use ORMs at all, use raw SQL with parameterized queries

**Action:** Use the Processor's actual database pattern. If no pattern exists, use the simplest approach that matches the existing codebase.

### 3. Suggestion Engines Return Plain Data, Not ORM Objects

Suggestion engines (normalization, household, duplicate detection) must:
- Return **plain dictionaries or dataclasses**, not SQLAlchemy ORM objects
- Never return session-bound ORM instances (they can be accidentally committed)
- Return minimal data needed for persistence (no relationship loading)

Example:
```python
# ✅ GOOD: Return plain dict
def suggest_normalizations(contact: dict) -> list[dict]:
    return [
        {
            "contact_id": contact["id"],
            "field_name": "email",
            "current_value": contact["email"],
            "suggested_value": contact["email"].lower(),
            "reason": "standardize case",
            "confidence_score": 100
        }
    ]

# ❌ WRONG: Return ORM objects
def suggest_normalizations(contact) -> list[ContactSuggestion]:
    suggestion = ContactSuggestion(...)  # ORM object
    return [suggestion]  # Risk: accidentally attached to session
```

**Persistence only happens in `suggestion_persistence.py`** — that's the only place suggestions are committed to the database.

### 4. CSV Column Mapping (Use Existing Processor Pattern)

The plan says "required columns: name, email, phone, address, zip, amount, date, campaign." That's too rigid.

Instead:
- Inspect the Processor's existing Givebutter CSV column mapping
- Reuse that mapping for Householder (same source data)
- If columns differ, implement a mapping layer, not hard-coded column names
- Support multiple column name variations (e.g., "full_name" vs "name" vs "contact_name")

**Action:** Use `processor.column_mapping()` or equivalent before implementing column extraction.

### 5. Contact Extraction is Read-Only; Suggestion Generation is Separate

**Do NOT mix extraction with suggestion generation.**

- **Step 4A: Contact Extraction Only**
  - Read raw_import_rows
  - Create contacts records with EXACT raw values (no cleaning, no normalization, no validation)
  - Zero transformations
  
- **Step 4B: Suggestion Generation** (separate step)
  - Once contacts are extracted, run suggestion engines
  - Engines examine raw contacts and generate suggestions
  - Return plain dicts, not ORM objects

This separation prevents accidental normalization during extraction.

### 6. Immutability Enforcement (Application + Tests, Not Triggers)

The plan says "raw_import_rows immutability enforced by DB (no UPDATE/DELETE triggers)." That's backwards.

**Correct approach:**

**Option A: Application-Layer Policy** (Recommended)
- No application code path may UPDATE/DELETE raw_import_rows
- Tests verify no such code path exists (grep, code review, AST analysis)
- Optional: SQLite BEFORE UPDATE/DELETE triggers may block mutations as an extra safety layer
  ```sql
  CREATE TRIGGER prevent_raw_import_rows_delete
    BEFORE DELETE ON raw_import_rows
    BEGIN SELECT RAISE(ABORT, 'raw_import_rows is immutable'); END;
  ```

**Option B: Database Triggers Only**
- SQLite BEFORE UPDATE/DELETE triggers block all mutations
- Simpler for enforcement but less flexible if we need admin overrides

**Choose one and test it explicitly.**

### 7. Baseline Contact Field Immutability (Application Guards, Not ORM Properties)

The plan says "implement read-only ORM properties." That's often awkward and incomplete.

Instead:
- Do NOT expose any service method that updates baseline contact fields (full_name, email, phone, address_line_1, city, state, postal_code)
- Only `approve_household()` may update `contacts.household_id`
- Tests verify no other code path updates these fields (grep for UPDATE contacts SET, code review)
- ORM properties can help but aren't sufficient alone

**Action:** Establish a clear policy: "ContactRepository has no update_contact_field() method. All mutations to contacts happen through specific approval functions."

### 8. Timeline is Aspirational, Not Binding

The 1-week timeline is a goal for focused execution, not a requirement. **Quality > Speed.**

- If a phase takes 3 days instead of 1, that's fine
- If tests reveal bugs, fix them thoroughly
- If the Processor structure is different than expected, adapt gracefully
- Ship when all 8 guardrails are tested and verified, not on a calendar date

---

## HOUSEHOLDER V1 IMPLEMENTATION PLAN

### Executive Summary

This plan details the step-by-step implementation of Householder v1, a human-in-the-loop data hygiene app that extends the Givebutter Processor. Householder ingests CSV contact data, generates suggestions for normalization and household grouping, and requires explicit human approval for all changes. The implementation prioritizes data safety with an append-only audit trail and zero auto-mutations.

**Key Design Principles:**
- Raw data immutability (append-only audit trail)
- Suggestion-only engines (no auto-writes)
- Explicit approval workflows (every change requires a click)
- Deterministic household ID generation
- View-based exports (read-only queries)

**Aspirational Timeline (Quality-First):**

This is a guideline for focused execution, not a deadline. Adjust as needed based on repository structure and unforeseen complexity.

- **Phase 1 (1-3 days):** Infrastructure & Setup
- **Phase 2 (1-2 days):** Upload & Extraction
- **Phase 3 (1-2 days):** Core Suggestion Engines
- **Phase 4 (2-3 days):** Approval Workflows (highest complexity)
- **Phase 5 (1-2 days):** Views & Exports
- **Phase 6 (2-3 days):** Comprehensive Testing
- **Phase 7 (1 day):** Final Audit & Documentation

**Total: 9-18 days** (2-4 weeks) depending on codebase complexity and discovery time.

---

## PHASE 1: INFRASTRUCTURE & SETUP

### Step 1: Processor Adapter & Validation Functions Import

**Objective:** Verify and establish clean import of validation functions from Processor; create adapter if needed.

**Before Starting:**
- Inspect `scripts/processor.py` (or actual location) to find:
  - Where are `fuzzy_email_match`, `normalize_phone`, `validate_email_format` defined?
  - Do they have `__version__` attribute?
  - What are their actual signatures?
  - **If Processor exposes equivalent functionality under different names, create an adapter that maps Householder's expected function names to the actual Processor functions.**

**Proposed File Location:** `/scripts/householder/processor_adapter.py` (adapt if repo structure differs)

**Tasks:**
1. Create package: `/scripts/householder/__init__.py`
2. Create adapter module with functions imported from Processor
   - Import the three validation functions
   - Add version check (3.4+) with clear error messages
   - Re-export functions
3. Add unit tests verifying imports and signatures work

---

### Step 2: Database Schema & Migrations

**Objective:** Create database schema for Householder tables without introducing new frameworks.

**Before Starting:**
- Inspect the Processor's database setup:
  - How does it initialize the database? (Alembic? Raw SQL? Click command? ORM migrations?)
  - What ORM does it use? (SQLAlchemy? Raw SQL? Other?)
  - How are tests set up? (In-memory SQLite? Fixtures? Test database?)
  - Where does it define tables? (models.py? migrations/ folder? SQL scripts?)

**Use the Processor's pattern.** If it uses Alembic, use Alembic. If it uses raw SQL scripts, use that. Do not introduce a new framework.

**Proposed File Locations** (adapt to match Processor):
- `/scripts/householder/models.py` — table/model definitions
- `/scripts/householder/db.py` — database connection, session factory
- `/[migrations-folder]/[timestamp]_householder_initial_schema.py` — migration (if Processor uses migrations)

**Tables to Define:**
1. `raw_import_rows` — immutable audit trail of uploaded CSV rows
2. `imports` — import batches metadata
3. `contacts` — baseline extracted contacts (raw values only)
4. `contact_suggestions` — normalization suggestions
5. `household_suggestions` — household grouping suggestions
6. `households` — confirmed household groups (created only after approval)
7. `duplicate_candidates` — likely duplicate pairs

**Key Constraints:**
- CHECK constraints for enum fields (status, decision)
- UNIQUE constraints for idempotency (prevent duplicate suggestions on re-run)
- Optional: SQLite triggers to block UPDATE/DELETE on raw_import_rows

---

## PHASE 2: UPLOAD & EXTRACTION

### Step 3: Raw Data Upload & Preservation

**Objective:** Implement CSV upload flow that preserves raw data immutably.

**Before Starting:**
- Inspect the Processor's Flask app structure
- Where are upload routes defined?
- How does it accept file uploads?
- What Flask patterns does it use?

**Proposed File Locations** (adapt to match Processor):
- Extend `/scripts/uploader/app.py` (or actual app file) with new routes
- `/scripts/householder/csv_validator.py` — CSV validation helpers
- `/scripts/uploader/templates/householder_upload.html` (or existing template folder)

**Routes:**
- `POST /householder/imports` — Accept CSV upload
- `GET /householder/imports` — List imports
- `GET /householder/imports/<id>` — View import details

**Key Requirement:**
- Store raw CSV rows as-is in `raw_import_rows.raw_json` field (no transformations)

---

### Step 4A: Contact Extraction (Read-Only)

**Objective:** Extract baseline contacts from raw_import_rows. Zero normalization, zero validation.

**Proposed File Location:** `/scripts/householder/extraction.py`

**Function:**
```python
def extract_contacts(import_id: int) -> list[dict]:
    """Extract contacts from raw_import_rows.
    
    Returns plain dicts (not ORM objects) with EXACT raw values for baseline fields.
    Derived/index fields (zip5, amount_cents) may be computed for matching/querying only.
    """
    raw_rows = query_raw_import_rows(import_id)
    contacts = []
    for row in raw_rows:
        contact = {
            "import_id": import_id,
            "raw_row_id": row["id"],
            "full_name": row["name"],  # Use Processor's column mapping — EXACT raw value
            "email": row["email"],  # EXACT raw value
            "phone": row["phone"],  # EXACT raw value
            "address_line_1": row["address"],  # Map to actual column name — EXACT raw value
            "city": row.get("city"),  # EXACT raw value
            "state": row.get("state"),  # EXACT raw value
            "postal_code": row.get("zip"),  # EXACT raw value
            # Derived/index fields only (for matching/querying, never replace originals):
            "zip5": extract_zip5(row.get("zip")),
            "amount_cents": parse_amount(row["amount"]),  # Parse for querying, not validation
            "campaign_title": row.get("campaign"),  # EXACT raw value
            "donation_date": row.get("date"),  # EXACT raw value
            # No validation_tier here; that comes from Processor
        }
        contacts.append(contact)
    return contacts  # Plain dicts, not ORM objects
```

**Key Requirement:**
- Contact extraction must preserve all baseline display/contact fields exactly as provided
- Derived/index fields (zip5, amount_cents) may be computed for matching/querying, but must not replace or mutate the original raw values
- Return plain dictionaries, not ORM objects

---

### Step 4B: Normalization Suggestion Generation

**Objective:** Generate email/phone/name/address suggestions from extracted contacts.

**Proposed File Location:** `/scripts/householder/suggestion_engines.py`

**Function:**
```python
def suggest_normalizations(contact: dict) -> list[dict]:
    """Generate normalization suggestions for a contact.
    
    Returns plain dicts (not ORM objects) with suggested improvements.
    """
    suggestions = []
    
    # Email: lowercase + domain typo detection
    if contact["email"]:
        normalized = contact["email"].lower().strip()
        if normalized != contact["email"]:
            suggestions.append({
                "field_name": "email",
                "current_value": contact["email"],
                "suggested_value": normalized,
                "reason": "standardize case",
                "confidence_score": 100
            })
        
        # Fuzzy match (e.g., gmai.com → gmail.com)
        confidence, suggested = fuzzy_email_match(contact["email"])
        if confidence > 0.7:
            suggestions.append({
                "field_name": "email",
                "current_value": contact["email"],
                "suggested_value": suggested,
                "reason": "domain typo correction",
                "confidence_score": int(confidence * 100)
            })
    
    # Phone, name, address similarly
    # ...
    
    return suggestions  # Plain dicts
```

**Key Requirement:**
- Return plain dictionaries with suggestion data
- No database writes; engines are purely computational

---

## PHASE 3: CORE SUGGESTION ENGINES

### Step 5: Suggestion Engine Implementations (Complete)

**Objective:** Build household and duplicate detection engines.

**Proposed File Location:** `/scripts/householder/suggestion_engines.py` (continued from Step 4B)

**Functions:**
- `suggest_households(import_id: int) -> list[dict]` — household grouping suggestions
- `suggest_duplicates(import_id: int) -> list[dict]` — duplicate candidate pairs
- `get_primary_contact(contact_ids: list[int]) -> int` — waterfall logic
- `generate_household_id(address: str, zip5: str) -> tuple[str, str]` — deterministic household ID
- `generate_sorted_contact_ids_key(contact_ids: list[int]) -> str` — idempotency key

**All return plain dicts/values, not ORM objects.**

---

### Step 6: Suggestion Persistence (Pending Only)

**Objective:** Commit suggestions to database without approving them.

**Proposed File Location:** `/scripts/householder/suggestion_persistence.py`

**Functions:**
- `persist_contact_suggestions(import_id, contact_id, suggestions)` — check UNIQUE before insert
- `persist_household_suggestions(import_id, suggestions)` — check UNIQUE (idempotency key)
- `persist_duplicate_candidates(import_id, candidates)` — check UNIQUE

**Key Requirement:**
- All suggestions created with `status='pending'` (normalization, household) or `decision='unreviewed'` (duplicates)
- Idempotency: re-running doesn't create duplicates

---

## PHASE 4: APPROVAL WORKFLOWS

### Step 7-9: Approval Functions (Normalization, Household, Duplicate)

**Objective:** Implement approval actions that update suggestion status + audit trail.

**Proposed File Location:** `/scripts/householder/approvals.py`

**Functions:**
- `approve_normalization(suggestion_id, approved_by, ip_address, user_agent)` — UPDATE suggestion, never contacts
- `reject_normalization(...)` — UPDATE status='rejected'
- `defer_normalization(...)` — UPDATE status='deferred'
- `approve_household(...)` — ⚠️ **CRITICAL: ATOMIC TRANSACTION**
  - Verify contact conflicts
  - Elect primary contact
  - Generate household_id
  - INSERT households row
  - UPDATE contacts.household_id for ALL members
  - Mark suggestion='approved'
  - **ROLLBACK if any step fails**
- `reject_household(...)`, `defer_household(...)`
- `resolve_duplicate(...)` — record decision only (no merge in v1)

**Flask Routes:**
- `GET /householder/imports/<id>/normalizations` — review queue
- `POST /householder/normalizations/<id>/approve`, `reject`, `defer`
- `POST /householder/imports/<id>/normalizations/approve-bulk`
- Similar for households and duplicates

---

## PHASE 5: VIEWS & EXPORTS

### Step 10-13: Derived Views, Dashboard, Review Queues, Exports

**Objective:** Create query-time views, dashboard, and four export types.

**Proposed File Locations:**
- `/scripts/householder/views.py` — view definitions (SQL or ORM)
- `/scripts/householder/exports.py` — export functions
- `/scripts/uploader/templates/householder_*.html` — HTML templates

**Views:**
- `approved_contacts` — COALESCE approved suggestions with baseline contacts
- `households_summary` — one row per household with member info

**Dashboard:**
- Total contacts + validation tier breakdown
- Pending suggestion counts
- Action buttons

**Exports:**
1. **Export Clean** — approved_contacts view → CSV
2. **Export by Household** — households_summary view → CSV
3. **Export Backlog** — pending/deferred suggestions → CSV
4. **Export Raw** — raw_import_rows → original CSV (value-for-value equivalent)
   - **Note:** Since raw rows are stored as JSON, byte-for-byte reconstruction may not be possible due to column order, quoting, line endings, and whitespace variations. Export should be value-for-value equivalent to the uploaded CSV. Byte-for-byte equivalence is only achievable if the original uploaded file bytes are stored separately.

---

## PHASE 6: COMPREHENSIVE TESTING

### Step 15: Unit, Integration, E2E Tests

**Objective:** Verify all 8 guardrails, approve workflows, immutability, etc.

**Critical Tests (Must Have):**

1. **Immutability Tests:**
   - `test_raw_import_rows_never_updated()` — Verify no code path UPDATEs raw_import_rows
   - `test_contact_baseline_immutable()` — Verify no code updates baseline fields except via approve_household()

2. **Approval Workflow Tests:**
   - `test_approve_household_atomic_transaction()` — Verify rollback on failure
   - `test_household_id_deterministic()` — Same address+zip = same ID always
   - `test_primary_contact_waterfall()` — Correct member elected
   - `test_resolve_duplicate_record_only()` — No merge in v1

3. **Suggestion Engine Tests:**
   - `test_suggestion_engines_return_plain_dicts()` — No ORM objects returned
   - `test_suggestion_engines_no_database_writes()` — Engines don't commit

4. **Guardrail Tests:**
   - `test_no_auto_approval()` — All suggestions pending after upload
   - `test_no_contact_field_mutation()` — No update path for baseline fields
   - `test_bulk_same_person_disabled()` — Can't bulk-approve "Same Person"
   - `test_export_readonly()` — Exports never mutate DB

5. **E2E Test:**
   - `test_e2e_upload_review_approve_export()` — Full workflow

---

## PHASE 7: FINAL AUDIT

### Step 16: Code Audit & Documentation

**Objective:** Verify all guardrails, document API, prepare for handoff.

**Audit Checklist:**
- ✅ All 8 guardrails tested and enforced
- ✅ No forbidden function names (auto_*, merge_*)
- ✅ Suggestion engines return plain dicts only
- ✅ All DB transactions are atomic
- ✅ All mutations require explicit approval
- ✅ All exports are read-only
- ✅ All audit fields (reviewed_by, ip_address, etc.) captured

**Documentation:**
- API endpoints reference
- Database schema diagram
- User workflow guide (upload → review → approve → export)
- Testing guide (how to run tests, coverage)

---

## CRITICAL GUARDRAILS ENFORCEMENT

| # | Guardrail | Enforcement | Test |
|---|-----------|------------|------|
| 1 | Never mutate raw_import_rows | Application policy + optional SQLite trigger | `test_raw_import_rows_immutable` |
| 2 | Never mutate baseline contact fields except household_id | No update methods in application + code review | `test_contact_baseline_immutable` |
| 3 | Only approve_household() sets household_id | Single function enforces this; code review | `test_only_approve_household_sets_household_id` |
| 4 | Suggestion engines return suggestions only | Return plain dicts, no db.session.add/commit | `test_suggestion_engines_no_db_writes` |
| 5 | Upload processing never auto-approves | Upload calls suggest_* but not approve_* | `test_upload_no_auto_approve` |
| 6 | Duplicate decisions are record-only | resolve_duplicate() updates decision only | `test_no_duplicate_merge_v1` |
| 7 | Exports read-only; never mutate | Exports query views, never UPDATE/INSERT/DELETE | `test_export_readonly` |
| 8 | No Givebutter API writeback | No `import givebutter_api` in householder code | `test_no_givebutter_api_writeback` |

---

## HIGH-RISK AREAS

1. **Household Approval Transaction** — Must succeed or fail atomically
2. **Household ID Determinism** — Token-based address normalization ensures stability
3. **Idempotency Keys** — Sorted contact IDs prevent duplicates on re-run
4. **Primary Contact Waterfall** — amount → date → id (deterministic order)
5. **Immutability Enforcement** — Application policy + tests, not just triggers
6. **Approved Contacts View** — Must reflect approved suggestions only
7. **CSV Column Mapping** — Use Processor's mapping, not hard-coded columns

---

## READY TO BEGIN

Start with **Phase 1, Step 1:** Inspect the Processor repository and adapt file locations.

No code until you've confirmed:
- Where is the Flask app actually located?
- How does the Processor initialize its database?
- What patterns does it use for models, migrations, tests?
- Where are CSV columns mapped?

Then proceed with implementation, prioritizing quality and guardrail enforcement over speed.
