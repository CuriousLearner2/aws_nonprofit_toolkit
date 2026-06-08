# Givebutter Data Hygiene & Householding — v2.4 PRD for Claude Code (Human-in-Loop Only)

**Last updated:** 2026-06-08  
**Owner:** Gautam Biswas  
**Status:** v2.4 final candidate (Reconciled with implementation plan)

---

## 1. Mission

Build v1 of a lightweight web app that ingests Givebutter contact data via CSV upload, analyzes it for data quality issues and household relationships, and presents suggestions for cleaning and grouping. The app must never modify raw data automatically. Every normalization, duplicate resolution, and household grouping requires explicit human approval.

Householder builds ON TOP OF the existing Givebutter Processor validation system, focusing on deduplication and household grouping rather than field-level validation.

---

## 2. Non-Negotiables for Claude Code

- **Preserve raw imported data forever.** Never overwrite raw_import_rows.
- **No automatic cleaning.** No automatic merging. No automatic household assignment.
- **All engine outputs are suggestions with confidence scores.**
- **Human must click Approve before any suggestion is applied** to derived tables.
- **Bulk approvals require confirmation dialogs** with preview of changes.
- **Reuse existing validation** from Givebutter Processor (fuzzy email matching, phone validation) — do not duplicate.
- **Do not implement** API writeback, retention features, source attribution, or Meta CAPI in v1 (deferred to v2).

### Critical Implementation Guardrails

These guardrails must be enforced in code and covered by tests:

1. **Never mutate raw_import_rows.** Append-only immutable audit trail.
2. **Never mutate baseline contact fields:** full_name, email, phone, address_line_1, city, state, postal_code.
3. **Only approve_household() may set contacts.household_id.** Enforce via database constraint or application guard.
4. **Suggestion engines return suggestions only; they do not write to approval targets.** No auto-apply behavior.
5. **Upload processing may create pending suggestions, but may not approve anything.** All approvals require explicit operator action.
6. **Duplicate decisions in v1 are record-only and never merge contacts.** same_person decision records judgment; v2 may use it for merge.
7. **Export Clean reads from approved_contacts; it does not update contacts.** Read-only query of derived view.
8. **Givebutter API writeback is out of scope for v1.** No external writes, no background sync jobs.

---

## 2.1 Clarifications for Claude Code

**Document Version:** v2.4 | **Product Target:** Householder v1 | **Deferred Release:** Householder v2

### Terminology & Data Model

**Immutable Data (Append-Only):**
- `raw_import_rows` — Original CSV rows as uploaded. Never modified, never deleted. Provides audit trail and rollback capability.

**Baseline Records (Field Values Immutable After Extraction):**
- `contacts` — Extracted contact records with baseline field values (full_name, email, phone, address_line_1, etc.). Field values are immutable after initial import to ensure data integrity and audit trail.
- **Exception:** `contacts.household_id` is the ONLY mutable field on contacts in v1. It may be set only after operator explicitly approves a household suggestion via `approve_household()`.

**Mutable Suggestion Records:**
- `contact_suggestions` — Proposed field-level changes. Status values: pending, approved, rejected, deferred.
- `household_suggestions` — Proposed household groupings. Status values: pending, approved, rejected, deferred.
- `duplicate_candidates` — Proposed same-person duplicate pairs. Decision values: unreviewed, same_person, different, deferred.

**Approved Household Groups:**
- `households` — Permanent household records created only after operator approval. Never created automatically.

### Allowed Mutations in v1
- Suggestion table status/decision fields and review metadata (reviewed_by, reviewed_at, ip_address, user_agent)
- `contacts.household_id` only after explicit `approve_household()`
- `households` row creation only after explicit `approve_household()`

### Disallowed Mutations in v1
- Modifying `raw_import_rows` in any way
- Modifying contact field values (full_name, email, phone, address, etc.) directly
- Auto-approving suggestions
- Auto-creating households
- Auto-merging duplicate contacts
- Givebutter API writeback
- Any background data mutation without explicit operator click

---

## 3. Architecture: Integration with Givebutter Processor

**Workflow:**
```
Givebutter CSV Upload
        ↓
[Givebutter Processor] — validates email/phone/amount, assigns PASS/WARNING/FAIL tier
        ↓
[Householder App] — deduplicates, groups into households, normalizes contact info
        ↓
Export Clean (approved suggestions) OR Export by Household
```

**Key Differences:**
- **Processor**: Field-level validation (email format, phone digits, amount range)
- **Householder**: Relationship-level analysis (who is the same person, who are in the same household)

**Database:**
- Share the same SQLite instance as Processor (extend, don't duplicate)
- Processor creates: `donations`, `validation_tier`, `issues` tables
- Householder creates: `contacts`, `contact_suggestions`, `household_suggestions`, `duplicate_candidates` tables

---

## 4. v1 Scope — Build Only

### Core Features
- CSV upload with raw preservation in raw_import_rows
- Contact extraction and normalization suggestions (email case, phone format, address)
- Household matching engine using household-level evidence: shared address+zip, shared phone+last name, different first names at same address, related name/address patterns
- Duplicate candidate detection (pairs likely to be same person, including exact email matches)
- Householder dashboard (PASS/WARNING/FAIL counts, suggestion queue status)
- Three review queues:
  - **Normalizations**: Email/phone/address format fixes
  - **Households**: Suggested groupings (confirm or defer)
  - **Duplicates**: Likely duplicate pairs (same person / different / defer)
- Inline approval UI (Approve / Reject / Defer buttons)
- Bulk approval with confirmation dialogs
- Export options:
  - **Export Clean**: Contacts with approved normalizations + household_id
  - **Export by Household**: One row per household (primary contact info, member count, full member list)
  - **Export Backlog**: Pending suggestions not yet approved

### Testing
- Unit tests: suggestion engines don't auto-apply
- Integration tests: raw data preservation, approval workflow
- E2E tests (Playwright): upload → review → approve → export workflow
- Critical test: verify zero auto-writes, all changes require clicks

### v2 Deferred
- Salutation generation (mail_salutation, email_salutation via Claude/Gemini)
- Retention alerts and lifecycle tracking
- Source attribution and campaign tracking
- Givebutter API sync / writeback
- Multi-import household linking (across multiple batches)

---

## 5. Technical Stack

- **Backend**: Python Flask (consistent with Givebutter Processor)
- **Frontend**: Server-rendered Jinja templates (consistent with Processor)
- **Storage**: SQLite (extend existing Processor database, design for Postgres migration)
- **Tests**: pytest + Playwright (consistent with Processor)
- **Data science**: Pandas for matching logic, difflib.SequenceMatcher for fuzzy matching

### Processor Dependencies (Reuse, Do Not Duplicate)

Householder reuses validation logic from Givebutter Processor. **Do not reimplement these functions.**

```python
# Import from Givebutter Processor's validation module
from scripts.processor import (
    fuzzy_email_match,      # (typo_email: str) -> (confidence: float, suggestion: str)
    normalize_phone,        # (phone: str) -> (normalized: str, valid: bool)
    validate_email_format,  # (email: str) -> (valid: bool, reason: str)
)

# Enforcement: If import fails, raise NotImplementedError
# Example:
try:
    from scripts.processor import fuzzy_email_match
except ImportError:
    raise NotImplementedError(
        "Householder requires fuzzy_email_match from Processor. "
        "Ensure scripts/processor.py exports this function."
    )
```

**Contract:**
- `fuzzy_email_match(email: str)` → `(confidence: float, suggested_value: str | None)`
  - Returns confidence 0.0-1.0 for domain typos (e.g., "jane@gmai.com" → 0.95 for "gmail.com")
  - Used in `suggest_normalizations()` for email field suggestions
  
- `normalize_phone(phone: str)` → `(normalized: str, valid: bool)`
  - Returns digits-only format (e.g., "555.123.4567" → "5551234567")
  - Used in `suggest_normalizations()` for phone field suggestions

- `validate_email_format(email: str)` → `(valid: bool, reason: str)`
  - Returns True if email matches standard format (includes @, domain, TLD)
  - Used in `suggest_normalizations()` to flag invalid emails

**Version Compatibility:**
- Householder v1 requires Givebutter Processor v3.4+
- If Processor functions change, update imports and add compatibility layer
- Never fork or reimplement these functions in Householder

**Startup Version Check:**
```python
# At application startup, verify Processor version
import scripts.processor as processor
try:
    assert processor.__version__ >= '3.4', f"Processor v3.4+ required, got {processor.__version__}"
except (AttributeError, AssertionError) as e:
    raise RuntimeError(f"Processor version incompatible: {e}")
```

**Processor Adapter Pattern:**

Before implementing Householder, Claude Code must:
1. Inspect the existing Givebutter Processor repository
2. Confirm the actual module path for validation functions (may not be `scripts.processor`)
3. If functions exist under a different path, create a thin adapter module:
   ```
   scripts/householder/processor_adapter.py
   ```
4. The adapter may import and re-export:
   - `fuzzy_email_match`
   - `normalize_phone`
   - `validate_email_format`

The adapter must NOT copy or reimplement validation logic. If functions truly do not exist, raise NotImplementedError with a clear message.

**Forbidden Behaviors vs. Forbidden Names:**

Forbidden behaviors (no exceptions):
- No automatic merge of duplicate records
- No automatic cleaning of contact fields directly
- No automatic writeback to Givebutter API
- No automatic apply of suggestions
- No modification of raw_import_rows

Forbidden function name prefixes:
- `auto_*` (auto_merge, auto_clean, auto_apply, auto_write)
- `merge_*` (merge_contacts, merge_households)

Allowed names (these are OK):
- `export_clean_contacts()` — export function, not auto-apply
- `approved_contacts` — view name, not auto-apply
- `normalize_for_matching()` — normalization helper, not auto-apply
- `clean_contacts.csv` — file name, not auto-apply

---

## 6. Data Model

### Existing (from Processor)
- `donations` — Transaction-level records from Givebutter CSV
- `validation_tier` — PASS / WARNING / FAIL status per transaction

### New Tables for Householder

**raw_import_rows** — Immutable uploaded CSV rows (NEVER modified)
- id (PK)
- import_id (FK to imports)
- row_number
- raw_json (original CSV row as JSON)
- imported_at

**imports** — Import batches
- id (PK)
- filename
- uploaded_at
- row_count
- status (processing / complete / archived)

**contacts** — Denormalized baseline contacts (raw values, never auto-cleaned)
- id (PK)
- import_id (FK)
- raw_row_id (FK to raw_import_rows)
- full_name
- email
- phone
- address_line_1
- city
- state
- postal_code
- zip5 (first 5 digits for matching)
- amount_cents
- campaign_title
- donation_date
- validation_tier (inherited from Processor)
- household_id (Text, FK to households.household_id, Nullable) — Populated ONLY when household is approved via approve_household(). Set during step 7 of household approval workflow.
  - **GUARDRAIL: Application code must NEVER UPDATE contacts.household_id except in approve_household(). Direct writes bypass approval workflow and audit trail.**

**contact_suggestions** — Proposed normalizations (email case, phone format, address cleanup)
- id (PK)
- import_id (FK to imports, for filtering by import batch)
- contact_id (FK)
- field_name (email / phone / full_name / address_line_1)
- current_value
- suggested_value
- reason (e.g., "standardize email case", "extract digits only")
- confidence_score (80-100)
- status (pending / approved / rejected / deferred)
- suggested_by (username of suggestion engine)
- suggested_at (timestamp of suggestion creation)
- reviewed_by (nullable, username of reviewer who approved/rejected/deferred)
- reviewed_at (nullable, timestamp of review action)
- reviewer_notes (nullable, notes on rejection or deferral)
- ip_address (nullable, for audit compliance)
- user_agent (nullable, for audit compliance)

**household_suggestions** — Proposed groupings (multiple people → same household)
- id (PK)
- import_id (FK, for filtering by import batch)
- contact_id_primary (FK)
- contact_ids_other (JSON array of contact IDs)
- sorted_contact_ids_key (TEXT NOT NULL) — Deterministic key for idempotency index (populated by application using generate_sorted_contact_ids_key()); stores sorted IDs as "1-4-23"
- match_reason (e.g., "shared address + zip + different first names", "phone + last name match")
- match_confidence_score (65-95)
- status (pending / approved / rejected / deferred)
- suggested_by (username of suggestion engine)
- suggested_at (timestamp of suggestion creation)
- reviewed_by (nullable, username of reviewer who approved/rejected/deferred)
- reviewed_at (nullable, timestamp of review action)
- reviewer_notes (nullable, notes on rejection or deferral)
- ip_address (nullable, for audit compliance)
- user_agent (nullable, for audit compliance)

**households** — Confirmed household groups (created ONLY after approval)
- id (PK)
- import_id (FK)
- household_id (text, format: `HH_` + first 8 chars of MD5 hash)
- canonical_form (text, the normalized address + "|" + zip5 used for household_id generation; enables collision detection)
- primary_contact_id (FK to contacts)
- member_count
- created_by
- created_at

**Household ID Generation Algorithm:**
```python
def generate_household_id(address_line_1: str, zip5: str) -> tuple[str, str]:
    """
    Generate stable household ID from address + zip5.
    
    Returns: (household_id, canonical_form)
    - household_id: HH_<8-char-lowercase-md5-hex> format
    - canonical_form: the normalized address + "|" + zip5 (used for collision detection)
    
    Uses scalar parameters only (no database lookups), ensuring deterministic
    computation in loose data loops and standalone test harnesses.
    
    Input: normalized_address (lowercase, no punctuation) + zip5
    Example: 
      address_line_1 = "123 Main Street"
      zip5 = "94301"
      normalized = normalize_address_for_household_id("123 Main Street")
      canonical = f"{normalized}|{zip5}"  → "123mainstreet|94301"
      md5_hash = hashlib.md5(canonical.encode()).hexdigest()[:8]
      household_id = f"HH_{md5_hash}"  → "HH_a1b2c3d4"
      return (household_id, canonical)
    
    Generated: Only at approval time (when household_suggestion status → approved)
    Stability: Same across imports (deterministic, based on address + zip only)
    
    Note: Caller is responsible for providing address_line_1 from either:
    - An approved contact_suggestion (if address normalization was approved), or
    - Raw contacts.address_line_1 (if no normalization exists or was rejected)
    """
    normalized = normalize_address_for_household_id(address_line_1)
    canonical = f"{normalized}|{zip5 or ''}"
    base_hash = hashlib.md5(canonical.encode()).hexdigest()
    candidate = f"HH_{base_hash[:8]}"
    return (candidate, canonical)
```

**Why this approach:**
- Deterministic: same address + zip = same ID across imports (useful for multi-batch household linking in v2)
- Collision-resistant: 8-char hex = 2^32 combinations (sufficient for 10k+ households)
- Readable: `HH_` prefix makes it obvious it's a household ID
- Generated at approval time: ensures no accidental household_id before operator approval

**duplicate_candidates** — Likely duplicates (same person, separate transactions)
- id (PK)
- import_id (FK, for filtering by import batch)
- contact_id_a (FK to contacts, first contact in pair)
- contact_id_b (FK to contacts, second contact in pair)
- confidence_score (70-95, how confident they're the same person)
- match_reasons (JSON array, e.g., ["email exact match", "phone exact match", "address + zip5 match"])
- decision (same_person / different / deferred / unreviewed, operator's judgment)
- reviewer_notes (text, nullable, operator's notes explaining decision)
- decided_by (text, nullable, username of operator who reviewed)
- decided_at (timestamp, nullable, when decision was made)

**Workflow:**
1. `suggest_duplicates()` creates rows with decision = 'unreviewed'
2. Operator reviews pair via UI: `/imports/{id}/duplicates`
3. Operator clicks "Same Person" / "Different" / "Defer" with optional notes
4. System sets: decision, reviewer_notes, decided_by, decided_at
5. If decision = 'same_person', the pair can be merged in v2 (not v1)

### Derived Views (for Export & Display)

**approved_contacts** — Clean contact data (computed view)
Derived from contacts + approved contact_suggestions:
```sql
SELECT 
  c.id,
  c.import_id,
  c.raw_row_id,
  COALESCE(
    (SELECT suggested_value FROM contact_suggestions 
     WHERE contact_id = c.id AND field_name = 'full_name' AND status = 'approved'
     LIMIT 1),
    c.full_name
  ) AS full_name,
  COALESCE(
    (SELECT suggested_value FROM contact_suggestions 
     WHERE contact_id = c.id AND field_name = 'email' AND status = 'approved'
     LIMIT 1),
    c.email
  ) AS email,
  COALESCE(
    (SELECT suggested_value FROM contact_suggestions 
     WHERE contact_id = c.id AND field_name = 'phone' AND status = 'approved'
     LIMIT 1),
    c.phone
  ) AS phone,
  COALESCE(
    (SELECT suggested_value FROM contact_suggestions 
     WHERE contact_id = c.id AND field_name = 'address_line_1' AND status = 'approved'
     LIMIT 1),
    c.address_line_1
  ) AS address_line_1,
  c.city,
  c.state,
  c.postal_code,
  c.amount_cents,
  c.campaign_title,
  c.donation_date,
  c.validation_tier,
  c.household_id
FROM contacts c
```

**Implementation Notes:**
- The view is computed at query time (no redundant storage)
- For each field, if there's an approved suggestion, use suggested_value; otherwise use the raw value from contacts
- "Export Clean" queries this view to generate the CSV (one row per contact with approved values + household_id)
- Household assignment only appears if the contact is in an approved household_suggestion
- The view automatically reflects current state: if an approval is withdrawn, the view reverts to raw value

**Address Normalization Clarification:**
- Approved address_line_1 suggestions are reflected only in approved_contacts and exports
- They never mutate contacts.address_line_1 (baseline field remains immutable)
- Household ID generation uses approved address_line_1 suggestion if present; otherwise uses raw contacts.address_line_1
- Field name standardization: all address suggestions use field_name = 'address_line_1' (not 'address')

**households_summary** — One row per household (for "Export by Household" report)
```sql
SELECT 
  h.household_id,
  h.primary_contact_id,
  ac_primary.full_name AS primary_name,
  ac_primary.email AS primary_email,
  h.member_count,
  GROUP_CONCAT(c.id) AS member_ids,
  SUM(ac.amount_cents) AS total_amount_cents
FROM households h
JOIN approved_contacts ac_primary ON h.primary_contact_id = ac_primary.id
JOIN contacts c ON c.household_id = h.household_id
JOIN approved_contacts ac ON ac.id = c.id
GROUP BY h.household_id
```

**Data Flow on Approval:**
1. Operator clicks "Approve" on a contact_suggestion → `contact_suggestions.status = 'approved'`
2. `approved_contacts` view automatically reflects approved values (recomputed at query time)
3. "Export Clean" CSV includes these approved values
4. Operator clicks "Approve" on a household_suggestion → `households` record created
5. `households_summary` view includes household with member info
6. "Export by Household" CSV includes household groupings

### Database Constraints and Enums

**SQLite Migration Note:**

SQLite has limited support for ALTER TABLE ADD CHECK constraints. CHECK constraints should be created during CREATE TABLE migrations (when first creating the table). If adding CHECK constraints to existing tables, use a migration that:
1. Creates a new table with the CHECK constraints
2. Copies data from the old table
3. Renames tables

Alternatively, use Python validation in the ORM layer to enforce these constraints.

**Enum/CHECK constraints:**

contact_suggestions:
```sql
CREATE TABLE contact_suggestions (
  id INTEGER PRIMARY KEY,
  import_id INTEGER NOT NULL,
  contact_id INTEGER NOT NULL,
  field_name TEXT NOT NULL,
  current_value TEXT,
  suggested_value TEXT NOT NULL,
  reason TEXT,
  confidence_score INTEGER,
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'deferred')),
  -- ... other fields ...
);
```

household_suggestions:
```sql
CREATE TABLE household_suggestions (
  id INTEGER PRIMARY KEY,
  import_id INTEGER NOT NULL,
  contact_id_primary INTEGER NOT NULL,
  contact_ids_other TEXT NOT NULL,
  sorted_contact_ids_key TEXT NOT NULL,
  match_reason TEXT,
  match_confidence_score INTEGER,
  status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'deferred')),
  -- ... other fields ...
);
```

duplicate_candidates:
```sql
CREATE TABLE duplicate_candidates (
  id INTEGER PRIMARY KEY,
  import_id INTEGER NOT NULL,
  contact_id_a INTEGER NOT NULL,
  contact_id_b INTEGER NOT NULL,
  confidence_score INTEGER,
  match_reasons TEXT,
  decision TEXT NOT NULL CHECK (decision IN ('unreviewed', 'same_person', 'different', 'deferred')),
  reviewer_notes TEXT,
  decided_by TEXT,
  decided_at TEXT,
  CHECK (contact_id_a < contact_id_b)
);
```

**UNIQUE constraints (prevent duplicates on re-run):**

contact_suggestions:
```sql
CREATE UNIQUE INDEX idx_contact_suggestion_idempotency 
  ON contact_suggestions(import_id, contact_id, field_name, suggested_value);
```

household_suggestions:
```sql
-- sorted_contact_ids_key is populated by application using generate_sorted_contact_ids_key() (e.g., "1-4-23")
CREATE UNIQUE INDEX idx_household_suggestion_idempotency
  ON household_suggestions(import_id, sorted_contact_ids_key);
```

duplicate_candidates:
```sql
CREATE UNIQUE INDEX idx_duplicate_idempotency
  ON duplicate_candidates(import_id, contact_id_a, contact_id_b);
```

---

## 7. Suggestion Engines (Never Auto-Apply)

### 7.1 Normalization Suggestions (Low Risk, High Confidence)

For each contact, generate suggestions:

| Field | Rule | Reason | Confidence |
|-------|------|--------|-----------|
| **email** | Lowercase, trim whitespace | Standardize case | 100 |
| **phone** | Extract digits only (last 10 for US) | Standardize format | 95 |
| **full_name** | Title Case | Consistency | 90 |
| **address_line_1** | Lowercase, remove double spaces, expand "st" → "street" | Match households | 85 |

Store each as `contact_suggestions` with status = `pending`.

### 7.2 Email/Phone Validation (Reuse from Processor)

**Email validation** — Reuse Givebutter Processor fuzzy matching:
- Email typo detection: gmai.com → gmail.com (70% similarity threshold)
- Invalid email format: suggest review or manual entry
- Store as `contact_suggestions` with reason = "Inherit from Processor validation"

**Phone validation** — Reuse Processor phone validation:
- Test patterns (all same digit, sequential, reserved 555 ranges) → flag for review
- Format standardization: (XXX) XXX-XXXX
- Store as `contact_suggestions`

### 7.3 Household Matching (Core Logic)

**Critical:** Exact email match is a duplicate signal, NOT a household signal. Household suggestions require shared household-level evidence (address + zip, phone + name, etc.), not just shared email (which indicates same person, not same household).

For each contact, score against all other contacts. Match rules (in priority order):

| Rule | Fields | Confidence | Reason |
|------|--------|-----------|--------|
| Address + zip + last name (all exact) | address_line_1 + zip5 + last_name | 85 | Likely household members |
| Phone + last name + zip (all exact) | phone_digits + last_name + zip5 | 80 | Likely household members |
| Shared address + zip with different first names | address_line_1 + zip5 + first_name variation | 80 | Likely household, different people |
| Phone + different first names + same last name | phone_digits + last_name exact + first_name different | 75 | Possible household members |
| Last name + zip + first initial + address fuzzy (70%+) | last_name + zip5 + first_initial + address similarity | 70 | Weak household candidate |

**Important:**
- Exact email match goes to duplicate detection, not household matching
- Never create household_id automatically
- Only create `household_suggestions` with status = `pending`
- Household is confirmed ONLY after operator clicks "Approve Household"

### 7.4 Duplicate Detection (Same Person, Different Transactions)

Identify contacts that likely represent the same person (separate donations):

| Score | Criteria | Example |
|-------|----------|---------|
| 95 | Email exact match | jane@example.com in 2 rows |
| 90 | Phone exact match + email match (fuzzy or exact) | Same phone, similar emails |
| 85 | Name exact + phone exact + address exact | Clearly same person, three matching fields |
| 75 | Name fuzzy (85%+) + phone exact | Possible name variation, same phone |
| 70 | Phone + address exact, name fuzzy (70%+) | Likely same person, minor name variance |

Store as `duplicate_candidates` with decision = `'unreviewed'`. Operator decides: "Same Person" / "Different" / "Defer".

---

## 8. UI Requirements

### 8.1 Upload & Dashboard

**GET /imports/new** — File upload form
- Drag-and-drop or file picker
- Show import summary: "Processed 50 contacts, 12 pending normalizations, 5 household suggestions, 3 duplicates"

**GET /imports/{id}** — Dashboard
- Card 1: Total contacts, validation tier breakdown (PASS / WARNING / FAIL)
- Card 2: Suggestion queue status (# pending normalizations, households, duplicates)
- Card 3: Action buttons: Review Normalizations, Review Households, Review Duplicates, Export
- Card 4: Recent approvals (last 5 actions by current user)

### 8.2 Normalizations Review Queue

**GET /imports/{id}/normalizations** — Paginated table
- Columns: Contact Name, Field, Current Value, Suggested Value, Reason, Confidence, Actions
- Row actions: Approve / Reject (buttons)
- Bulk actions: "Approve All" (with confirmation preview)
- Filters: Field (email / phone / full_name / address_line_1), Confidence (high / medium / low)

### 8.3 Households Review Queue

**GET /imports/{id}/households** — Household grouping suggestions
- Card layout: Side-by-side contacts with match reasons
- Show primary contact waterfall logic: "Primary: Jane (highest donation: $1000)"
- Buttons: Approve Household / Reject / Defer
- Bulk: "Approve All Households" (with confirmation: "X households will be created, Y members grouped")

### 8.4 Duplicates Review Queue

**GET /imports/{id}/duplicates** — Duplicate candidate review
- Two-column layout: Contact A | Contact B
- Match score and reasons
- Buttons: "Same Person" / "Different" / "Defer"
- Bulk: "Mark All As Same Person" (with confirmation)

### 8.5 Bulk Approval Safety

When operator clicks bulk action (e.g., "Approve All Normalizations"):
1. Show modal: "Preview Changes"
   - "50 email fields will be normalized"
   - "3 phone fields will be reformatted"
   - "These changes will affect approved exports. Raw data will remain unchanged. You can reverse the approval by changing the suggestion status later."
2. Require confirmation: [Cancel] [Approve]
3. Log action: timestamp, operator, # approved, change details

**Bulk Approval Safety Rules:**

- Bulk approval may only apply to currently filtered pending suggestions
  - Never include deferred, rejected, or already-approved items
  - Verify filter state matches expectations before confirming

- Bulk normalizations must show counts by field/type before confirmation
  - Example: "50 emails, 3 phones, 2 addresses"

- Bulk household approval must show:
  - Number of households to be created
  - Total unique contacts affected
  - Primary contact waterfall logic explanation

- Bulk duplicate decisions:
  - "Different" decisions can use bulk approval safely (no system action)
  - "Same Person" decisions are higher-risk due to v2 merge potential and must be disabled for bulk approval in v1
  - Individual "Same Person" decisions must be approved one-at-a-time, never bulk
  - v2 merge workflow will require individual approval anyway

- All bulk operations must be audit-logged with:
  - Timestamp
  - Operator username and IP address
  - Action type (approve normalizations / households / duplicates)
  - Count of items affected
  - Filter criteria applied

**Backend Optimization for Preview Metrics:**

To prevent performance degradation from parsing thousands of raw JSON objects, use optimized aggregation:

```sql
-- Fast COUNT + GROUP BY on pending suggestions (no JSON parsing)
SELECT field_name, COUNT(*) as suggestion_count
FROM contact_suggestions
WHERE import_id = ? AND status = 'pending'
GROUP BY field_name
ORDER BY suggestion_count DESC

-- Fast COUNT of pending households
SELECT COUNT(*) as household_count
FROM household_suggestions
WHERE import_id = ? AND status = 'pending'

-- Fast COUNT of unreviewed duplicates
SELECT COUNT(*) as duplicate_count
FROM duplicate_candidates
WHERE import_id = ? AND decision = 'unreviewed'
```

**Implementation:**
- Create dedicated API endpoint: `GET /api/processing/{import_id}/bulk-preview-metrics`
- Returns lightweight JSON: `{ "email": 50, "phone": 3, "households": 12, "duplicates": 5 }`
- No row-level iteration, no JSON parsing, O(1) query time
- UI populates modal from aggregation response (not raw data)

### 8.6 Export

**GET /imports/{id}/export** — Export options
- Button 1: "Export Clean" — Download CSV with approved normalizations + household_id
- Button 2: "Export by Household" — Download CSV, one row per household (primary contact info, member count, members list)
- Button 3: "Export Backlog" — Download CSV of pending suggestions not yet approved
- Button 4: "Export Raw" — Download original import (unchanged)

### 8.7 Defer State Implementation

**Schema & Lifecycle:**

The "Defer" action hides suggestions from the primary review queue without deleting or rejecting them. It maps to a discrete `status = 'deferred'` state in the suggestion tables.

**For contact_suggestions (normalizations):**
- Query primary queue: `SELECT * WHERE status = 'pending'`
- Defer action: `UPDATE contact_suggestions SET status = 'deferred' WHERE id = ?`
- Deferred items hidden from normalizations queue until explicitly un-deferred
- Operator can un-defer: shows button "Restore to Queue" in deferred view

**For household_suggestions:**
- Query primary queue: `SELECT * WHERE status = 'pending'`
- Defer action: `UPDATE household_suggestions SET status = 'deferred' WHERE id = ?`
- Deferred household suggestions do NOT create household records
- Can be un-deferred anytime during same import batch

**For duplicate_candidates:**
- Query primary queue: `SELECT * WHERE decision = 'unreviewed'`
- Defer action: `UPDATE duplicate_candidates SET decision = 'deferred' WHERE id = ?`
- Deferred duplicates hidden from review queue but decision field preserved
- Can be revisited in "Deferred Items" sidebar

**UI Behavior:**
- Each queue page shows count of deferred items: "3 normalizations deferred (show/hide)"
- Clicking "Defer" removes card from view immediately (no page refresh needed)
- Deferred items accessible via "View Deferred" link (optional secondary queue)
- Un-defer restores item to primary queue with state = 'pending'/'unreviewed'
- Deferred items can be edited before un-deferring

**Audit Trail:**
- Defer action logged: timestamp, operator, reason (optional notes)
- State transitions: pending → deferred → pending (or approved/rejected)
- Never purges deferred records; all history retained

### 8.7a Status Transitions and Terminal States

**contact_suggestions and household_suggestions allowed transitions:**
- `pending` → `approved` (operator clicks Approve)
- `pending` → `rejected` (operator clicks Reject)
- `pending` → `deferred` (operator clicks Defer)
- `deferred` → `pending` (operator clicks Un-defer or Restore to Queue)
- `deferred` → `approved` (operator approves deferred item)
- `deferred` → `rejected` (operator rejects deferred item)

Terminal states in v1:
- `approved` and `rejected` are final unless an admin-only reversal feature is explicitly implemented
- Attempting to transition from approved/rejected to other states should raise an error

**duplicate_candidates allowed transitions:**
- `unreviewed` → `same_person` (operator marks as Same Person)
- `unreviewed` → `different` (operator marks as Different)
- `unreviewed` → `deferred` (operator defers decision)
- `deferred` → `unreviewed` (operator returns to queue)
- `deferred` → `same_person` (operator decides on deferred pair)
- `deferred` → `different` (operator decides on deferred pair)

Terminal states in v1:
- `same_person` and `different` are final decisions unless an admin-only reversal feature is explicitly implemented
- Recorded decisions should not be easily reversed; treat them as audit-logged operator judgment

### 8.8 Idempotency Rules for Suggestion Generation

Suggestion generation must be idempotent per import_id to safely handle retries and re-runs.

**Normalization suggestions:**
- Before creating a contact_suggestion, query for an existing row with the same:
  - import_id, contact_id, field_name, and suggested_value
- Do not create duplicate pending suggestions on re-run
- Example: if re-processing detects the same "email: jane@gmail.com" suggestion, skip insertion

**Household suggestions:**
- Use a deterministic suggestion key based on import_id + sorted contact IDs
- Store sorted contact IDs in deterministic order in `sorted_contact_ids_key` column (lowest ID first)
- Example: contact_ids [11, 4, 23] → sorted_contact_ids_key = "4-11-23"
- Do not create duplicate household_suggestions for the same proposed group on re-run
- Example: if group [1, 2, 3] was already suggested, do not suggest it again

**Implementation (Python):**
```python
def generate_sorted_contact_ids_key(contact_ids: list[int]) -> str:
    """Generate deterministic idempotency key from contact IDs."""
    sorted_ids = sorted(contact_ids)
    return "-".join(str(cid) for cid in sorted_ids)

# Before inserting household_suggestion:
sorted_key = generate_sorted_contact_ids_key([primary_contact_id] + other_contact_ids)
# Check if this group already exists:
existing = db.query(HouseholdSuggestion).filter_by(
    import_id=import_id,
    sorted_contact_ids_key=sorted_key
).first()
if not existing:
    # Safe to insert new household_suggestion
```

**Duplicate candidates:**
- Store duplicate pairs in sorted order: contact_id_a < contact_id_b (enforced by UNIQUE constraint)
- Enforce one duplicate candidate per (import_id, contact_id_a, contact_id_b)
- Do not create duplicate pairs on re-run
- Example: pair (1, 5) is identical to pair (5, 1); store only as (1, 5)

**Database enforcement:**
- Use UNIQUE constraints to prevent duplicate suggestions:
  - contact_suggestions: UNIQUE(import_id, contact_id, field_name, suggested_value)
  - household_suggestions: UNIQUE(import_id, sorted_contact_ids_key)
  - duplicate_candidates: UNIQUE(import_id, contact_id_a, contact_id_b) where contact_id_a < contact_id_b

---

## 9. Function Signatures Claude Must Implement

### Suggestion Engines (Never Write, Only Suggest)

```python
def suggest_normalizations(contact: dict) -> list[dict]:
    """Return list of normalization suggestions for a single contact."""
    # Returns: [{"field_name": "email", "current_value": "Jane@Gmail.com", "suggested_value": "jane@gmail.com", "reason": "standardize case", "confidence_score": 100}]
    
def suggest_households(contacts: list[dict]) -> list[dict]:
    """Return household grouping suggestions for a batch of contacts."""
    # Returns: [{"primary_id": "contact_1", "member_ids": ["contact_2", "contact_5"], "match_reason": "same address + zip + different first names", "confidence": 80}]

def suggest_duplicates(contacts: list[dict]) -> list[dict]:
    """Return duplicate candidate pairs (likely same person)."""
    # Returns: [{"contact_a": "id_1", "contact_b": "id_3", "confidence": 85, "reasons": ["phone match", "address match"]}]

def get_primary_contact(contact_ids: list[int]) -> int:
    """
    Select primary contact ID using waterfall logic.
    
    Data Source: Uses baseline contacts table (NOT approved_contacts view)
    - amount_cents and donation_date are transaction facts, not normalization fields
    - Primary contact selection should use raw baseline values, not approved suggestions
    
    Args:
        contact_ids: list[int] — Native database contact IDs (integers, not strings)
    
    Waterfall Priority (first non-tie wins):
    1. Highest total donation amount (contacts.amount_cents)
    2. Most recent donation_date (contacts.donation_date)
    3. Oldest database id (contacts.id, first to be created)
    
    Returns: int — contact_id of elected primary contact
    
    Example:
        get_primary_contact([1, 2, 3]) → 2
        (where contact 2 has highest amount_cents in baseline contacts table)
    """

def generate_household_id(address_line_1: str, zip5: str) -> tuple[str, str]:
    """
    Generate stable, deterministic household ID from address data.
    
    Args:
        address_line_1: str — The address to use (caller provides either raw or approved-suggestion value)
        zip5: str — First 5 digits of postal code
    
    Returns: tuple[str, str] — (household_id, canonical_form)
      - household_id: HH_<8-char-lowercase-md5-hex> (or HH_<12-char-hex> if collision detected)
      - canonical_form: normalized address + "|" + zip5 (used for collision detection)
    
    Implementation:
    
    def normalize_address_for_household_id(address_line_1: str) -> str:
        import re
        import string
        
        value = (address_line_1 or '').lower().strip()
        # Remove punctuation
        value = value.translate(str.maketrans('', '', string.punctuation))
        # Collapse multiple spaces
        value = re.sub(r'\s+', ' ', value).strip()
        
        # Token-based abbreviation mapping (handles terminal abbreviations like "St")
        mapping = {
            'st': 'street',
            'ave': 'avenue',
            'rd': 'road',
            'dr': 'drive',
            'ln': 'lane',
            'blvd': 'boulevard',
            'ct': 'court',
            'pl': 'place',
            'ter': 'terrace',
        }
        tokens = value.split()
        tokens = [mapping.get(token, token) for token in tokens]
        return ''.join(tokens)  # Remove all spaces for hash input
    
    Steps:
    1. Normalize input address: normalized = normalize_address_for_household_id(address_line_1)
    2. Create canonical form: canonical = f"{normalized}|{zip5 or ''}"
    3. Hash: base_hash = hashlib.md5(canonical.encode()).hexdigest()
    4. Extract 8 chars: candidate = f"HH_{base_hash[:8]}"
    5. Collision safety (optional):
       - Query: SELECT COUNT(*) FROM households WHERE household_id = candidate AND NOT canonical_form = ?
       - If collision exists for different address: candidate = f"HH_{base_hash[:12]}"
    6. Return: (candidate, canonical)
    
    Example:
      address_line_1 = "123 Main St"
      zip5 = "94301"
      normalized = normalize_address_for_household_id("123 Main St") → "123mainstreet"
      canonical = "123mainstreet|94301"
      base_hash = "a1b2c3d4e5f6g7h8..."
      candidate = "HH_a1b2c3d4"
      return (candidate, canonical)
    
    Caller Responsibility:
    The approve_household() function must:
    1. Check if contact has an approved address normalization:
       SELECT suggested_value FROM contact_suggestions 
       WHERE contact_id = primary_contact_id AND field_name = 'address_line_1' 
       AND status = 'approved' LIMIT 1
    2. If approved suggestion exists, pass suggested_value as address_line_1
    3. Otherwise, pass raw contacts.address_line_1 as address_line_1
    4. Call: household_id, canonical_form = generate_household_id(input_address, zip5)
    """
```

### State Modification Actions

```python
def approve_normalization(suggestion_id: int, reviewed_by: str) -> None:
    """
    Set contact_suggestions.status = 'approved'.
    
    Never modifies the baseline contacts table.
    Updates: contact_suggestions.status = 'approved', reviewed_by, reviewed_at, ip_address, user_agent
    """

def reject_normalization(suggestion_id: int, reviewed_by: str, notes: str = '') -> None:
    """
    Reject a normalization suggestion.
    
    Args:
        suggestion_id: contact_suggestions.id
        reviewed_by: username of operator
        notes: optional explanation for rejection
    
    Updates: contact_suggestions.status = 'rejected', reviewed_by = reviewed_by, reviewed_at = now(), ip_address, user_agent
    """

def defer_normalization(suggestion_id: int, reviewed_by: str, notes: str = '') -> None:
    """
    Defer a normalization suggestion to review later.
    
    Deferred suggestions are hidden from primary queue but preserved for later review.
    
    Args:
        suggestion_id: contact_suggestions.id
        reviewed_by: username of operator
        notes: optional explanation for deferral
    
    Updates: contact_suggestions.status = 'deferred', reviewed_by = reviewed_by, reviewed_at = now(), ip_address, user_agent
    """

def approve_household(suggestion_id: int, reviewed_by: str) -> None:
    """
    Approve a household suggestion and create permanent household record.
    
    CRITICAL: This function must run in a single database transaction. If any step fails, 
    roll back all changes so no household row exists without matching contact household_id 
    assignments, and no suggestion is marked approved without a household record.
    
    Steps:
    1. Fetch household_suggestion record by suggestion_id
    2. Extract contact IDs: primary = contact_id_primary, members = contact_ids_other (JSON parse)
    3. Verify all proposed contacts have contacts.household_id IS NULL or already equal to the same household_id
       (block approval if any contact belongs to a different household)
    4. Elect primary contact via get_primary_contact(all_contact_ids)
    5. Prepare address for household ID generation:
       a. Check if primary contact has an approved address normalization:
          SELECT suggested_value FROM contact_suggestions 
          WHERE contact_id = primary_id AND field_name = 'address_line_1' AND status = 'approved'
       b. If found, use suggested_value; otherwise use contacts.address_line_1
    6. Fetch primary contact's zip5: contacts.zip5
    7. Generate household_id and canonical_form via generate_household_id(input_address, zip5)
    8. Create households row:
       - household_id = generated ID
       - canonical_form = generated canonical form
       - primary_contact_id = elected primary
       - member_count = len(all_contact_ids)
       - created_by = reviewed_by
       - created_at = now()
    9. Update contacts table for ALL members:
       UPDATE contacts SET household_id = generated_id 
       WHERE id IN (contact_ids_primary + contact_ids_other)
    10. Update household_suggestion.status = 'approved', reviewed_by, reviewed_at
    
    If any step fails, ROLLBACK the entire transaction.
    """

def reject_household(suggestion_id: int, reviewed_by: str, notes: str = '') -> None:
    """
    Reject a household suggestion.
    
    Rejected suggestions do not create household records.
    
    Args:
        suggestion_id: household_suggestions.id
        reviewed_by: username of operator
        notes: optional explanation for rejection
    
    Updates: household_suggestions.status = 'rejected', reviewed_by = reviewed_by, reviewed_at = now(), ip_address, user_agent
    """

def defer_household(suggestion_id: int, reviewed_by: str, notes: str = '') -> None:
    """
    Defer a household suggestion to review later.
    
    Deferred suggestions are hidden from primary queue but preserved for later review.
    No household record is created until explicit approve_household().
    
    Args:
        suggestion_id: household_suggestions.id
        reviewed_by: username of operator
        notes: optional explanation for deferral
    
    Updates: household_suggestions.status = 'deferred', reviewed_by = reviewed_by, reviewed_at = now(), ip_address, user_agent
    """

def resolve_duplicate(candidate_id: int, decision: str, 
                     reviewer_notes: str, decided_by: str) -> None:
    """
    Record operator's decision on a duplicate pair.
    
    Args:
        candidate_id: duplicate_candidates.id
        decision: one of 'same_person', 'different', 'deferred'
        reviewer_notes: operator's explanation (text, can be empty)
        decided_by: username of operator
    
    v1 Behavior (record-only, no merge):
    - 'same_person' decision is recorded and can be exported for audit
    - 'different' decision indicates operator confirmed they are different people
    - 'deferred' decision hides from queue for later review
    
    CRITICAL: v1 does NOT merge contacts or modify contact fields.
    No automatic merge action occurs in v1, even if decision = 'same_person'.
    The recorded decision is available for v2 merge workflow.
    
    Updates duplicate_candidates row:
        - decision = decision
        - reviewer_notes = reviewer_notes
        - decided_by = decided_by
        - decided_at = now()
    """
```

**Forbidden function name prefixes:**
- `auto_*` (e.g., auto_apply, auto_merge, auto_clean, auto_write)
- `merge_*` (e.g., merge_contacts, merge_households)

**Forbidden behaviors** (regardless of function name):
- Direct mutation of baseline contact fields (full_name, email, phone, address_line_1, city, state, postal_code)
- Automatic application of suggestions without explicit operator approval
- Automatic household creation without explicit approve_household() call
- Automatic duplicate merge (same_person decision is record-only in v1)
- Givebutter API writeback

**Allowed function names:**
- `export_clean_contacts()` — export function (queries view, no mutation)
- `approved_contacts` — view name (derived, not auto-applied)
- `clean_contacts.csv` — file name (output file)
- `normalize_for_matching()` — helper function (calculation, not write)

---

## 10. Sample Data Requirements

Create a 15-row sample CSV with:
- 6 clean contacts (no issues)
- 3 email typos (gmai.com, gmial.com, yahooo.com)
- 2 invalid emails (missing @, format broken)
- 2 missing phone numbers
- 1 high-amount donation ($5,000+)
- 2 likely duplicates (same person, different transactions)
- 3 household candidates (same address, different names)

**Expected behavior after upload (specific detections, not broad counts):**

After uploading the 15-row sample CSV, required detections are:
- 3 email typo suggestions (gmai.com, gmial.com, yahooo.com corrections)
- 2 invalid email review suggestions (missing @, format broken)
- 2 missing phone suggestions
- At least 2 duplicate candidates (same-person pairs)
- At least 3 household suggestions (same address, different names)
- Zero approved contact_suggestions before operator action
- Zero approved household_suggestions before operator action
- Zero households before operator action
- raw_import_rows count equals uploaded CSV row count (15)
- raw_import_rows raw_json field value-for-value equivalent to uploaded data (immutable)
- Operator must click Approve, Reject, or Defer for each suggestion

---

## 11. Testing Strategy

Householder uses a three-tier testing approach: unit tests (isolated functions), integration tests (database interactions with real DB assertions), and E2E tests (full UI workflows).

### 11.1 Unit Tests (Validation & Algorithms)

Unit tests verify suggestion engines and utility functions in isolation, without database writes.

```python
def test_processor_dependencies_available():
    """Householder imports required functions from Processor or raises NotImplementedError."""
    try:
        from scripts.processor import (
            fuzzy_email_match,
            normalize_phone,
            validate_email_format,
        )
        # Verify functions are callable
        assert callable(fuzzy_email_match)
        assert callable(normalize_phone)
        assert callable(validate_email_format)
    except ImportError as e:
        raise NotImplementedError(
            "Householder requires fuzzy_email_match, normalize_phone, validate_email_format "
            f"from Processor. Import failed: {e}"
        )

def test_suggest_normalization_returns_suggestion_not_write():
    """Engine returns suggestions, does not write to DB."""
    contact = {"email": "Jane@Gmail.com"}
    suggestions = suggest_normalizations(contact)
    assert suggestions[0]["suggested_value"] == "jane@gmail.com"
    # Verify DB was NOT written to
    assert Contact.query.filter_by(email="jane@gmail.com").first() is None

def test_suggest_household_does_not_create_household_id():
    """Household engine returns suggestions only, no household or DB suggestion row created."""
    contacts = [
        {
            "id": 1,
            "full_name": "Jane Smith",
            "email": "jane@example.com",
            "phone": "5551112222",
            "address_line_1": "123 Main St",
            "zip5": "94301",
        },
        {
            "id": 2,
            "full_name": "John Smith",
            "email": "john@example.com",
            "phone": "5551112222",
            "address_line_1": "123 Main St",
            "zip5": "94301",
        },
    ]
    suggestions = suggest_households(contacts)
    assert len(suggestions) > 0
    assert "household_id" not in suggestions[0]
    assert Household.query.count() == 0
    assert HouseholdSuggestion.query.count() == 0

def test_primary_contact_waterfall():
    """Primary contact selected by highest donation → most recent → oldest id."""
    # Create contacts with native database integer IDs
    Contact.create(id=1, amount_cents=10000, donation_date="2026-01-01")
    Contact.create(id=2, amount_cents=50000, donation_date="2026-01-02")  # Highest donation
    Contact.create(id=3, amount_cents=10000, donation_date="2026-06-01")  # Most recent
    
    # Test waterfall: highest donation wins
    primary = get_primary_contact([1, 2, 3])
    assert primary == 2  # ID 2 has highest donation amount

def test_fuzzy_email_matching_reuses_processor():
    """Email suggestions reuse Processor's 70% fuzzy threshold."""
    contact = {"email": "jane@gmai.com"}
    suggestions = suggest_normalizations(contact)
    # Should suggest gmail.com based on Processor's fuzzy logic
    assert any("gmail.com" in s.get("suggested_value", "") for s in suggestions)

def test_normalize_address_for_household_id():
    """Address normalization produces deterministic canonical form (token-based)."""
    # "123 Main St" and "123 Main Street" should normalize identically
    addr_st = normalize_address_for_household_id("123 Main St")
    addr_street = normalize_address_for_household_id("123 Main Street")
    assert addr_st == addr_street == "123mainstreet"
    
    # Terminal abbreviations (St at end) are converted correctly
    assert normalize_address_for_household_id("123 Main St") == "123mainstreet"
    assert normalize_address_for_household_id("123 Oak Ave") == "123oakavenue"
    
    # Punctuation removed
    addr_punct = normalize_address_for_household_id("123-A Main St, Suite B")
    assert "-" not in addr_punct and "," not in addr_punct
    
    # Token mapping works for all abbreviations
    assert normalize_address_for_household_id("456 Park Ln") == "456parklane"
    assert normalize_address_for_household_id("789 Commerce Blvd") == "789commerceboulevard"

def test_household_id_format_and_stability():
    """Generated household_id follows HH_<8-char-md5> format and is deterministic."""
    hh_id_1, canonical_1 = generate_household_id(address_line_1="123 Main St", zip5="94301")
    hh_id_2, canonical_2 = generate_household_id(address_line_1="123 Main St", zip5="94301")

    # Format check
    assert hh_id_1.startswith("HH_")
    assert len(hh_id_1) == 11  # HH_ + 8 chars
    assert all(c in "0123456789abcdef" for c in hh_id_1[3:])  # Hex chars

    # Stability check: same address + zip = same ID and canonical form (deterministic)
    assert hh_id_1 == hh_id_2
    assert canonical_1 == canonical_2

    # Determinism across imports: "123 Main St" and "123 Main Street" normalize to same value
    hh_id_st, canonical_st = generate_household_id(address_line_1="123 Main St", zip5="94301")
    hh_id_street, canonical_street = generate_household_id(address_line_1="123 Main Street", zip5="94301")
    assert hh_id_st == hh_id_street
    assert canonical_st == canonical_street
```

### 11.2 Integration Tests (Database State & Workflows)

Integration tests verify database interactions, approval workflows, and state preservation. These tests use a real database (or in-memory SQLite) and make DB assertions.

```python
def test_raw_import_rows_immutability():
    """CRITICAL: raw_import_rows table is never modified after import."""
    raw_json = {"email": "Jane@Gmail.com", "phone": "555.123.4567"}
    import_id = upload_csv([raw_json])
    
    # Fetch original raw row
    raw_before = RawImport.query.filter_by(import_id=import_id).first()
    original_json = raw_before.raw_json.copy()
    
    # Run entire workflow: create suggestions, approve some, reject some
    suggestions = ContactSuggestion.query.filter_by(import_id=import_id).all()
    approve_normalization(suggestions[0].id, reviewed_by="operator")
    
    # Verify raw_json is unchanged (byte-for-byte or value-for-value)
    raw_after = RawImport.query.get(raw_before.id)
    assert raw_after.raw_json == original_json
    # Verify no UPDATE to raw_import_rows occurred
    assert raw_after.imported_at == raw_before.imported_at

def test_suggestions_are_pending_only_after_upload():
    """All generated suggestions are pending until operator action."""
    import_id = upload_csv(sample_csv)
    
    # All contact_suggestions start pending
    contact_sugg = ContactSuggestion.query.filter_by(import_id=import_id).all()
    assert len(contact_sugg) > 0
    assert all(s.status == "pending" for s in contact_sugg)
    
    # All household_suggestions start pending
    household_sugg = HouseholdSuggestion.query.filter_by(import_id=import_id).all()
    assert len(household_sugg) > 0
    assert all(s.status == "pending" for s in household_sugg)
    
    # All duplicate_candidates start unreviewed
    duplicates = DuplicateCandidate.query.filter_by(import_id=import_id).all()
    assert len(duplicates) > 0
    assert all(d.decision == "unreviewed" for d in duplicates)

def test_approve_normalization_updates_approved_view_only():
    """Approving a normalization suggestion updates approved_contacts view, not raw contacts."""
    import_id = upload_csv(sample_csv)
    suggestion = ContactSuggestion.query.filter_by(
        field_name="email", status="pending", import_id=import_id
    ).first()
    
    # Get raw contact before approval
    contact = Contact.query.get(suggestion.contact_id)
    raw_email = contact.email
    
    # Approve suggestion
    approve_normalization(suggestion.id, reviewed_by="operator")
    
    # Verify: raw contact unchanged
    assert Contact.query.get(contact.id).email == raw_email
    
    # Verify: approved_contacts view shows approved value
    approved_row = db.session.execute(
        "SELECT email FROM approved_contacts WHERE id = ?",
        (contact.id,)
    ).first()
    assert approved_row[0] == suggestion.suggested_value

def test_approve_household_creates_household_and_sets_household_id():
    """Approving a household suggestion creates household record and sets contacts.household_id."""
    import_id = upload_csv(sample_csv_with_households)
    suggestion = HouseholdSuggestion.query.filter_by(
        import_id=import_id, status="pending"
    ).first()
    
    # Before approval: no household record
    assert Household.query.filter_by(primary_contact_id=suggestion.contact_id_primary).count() == 0
    
    # Before approval: contacts have no household_id
    contact_ids = [suggestion.contact_id_primary] + json.loads(suggestion.contact_ids_other)
    for cid in contact_ids:
        assert Contact.query.get(cid).household_id is None
    
    # Approve household
    approve_household(suggestion.id, reviewed_by="operator")
    
    # After approval: household record created
    household = Household.query.filter_by(import_id=import_id).first()
    assert household is not None
    assert household.household_id.startswith("HH_")
    assert household.member_count == len(contact_ids)
    
    # After approval: all contacts in household have household_id set
    for cid in contact_ids:
        assert Contact.query.get(cid).household_id == household.household_id

def test_no_auto_merge_critical():
    """CRITICAL GUARDRAIL: Zero automatic merging or household creation."""
    import_id = upload_csv(sample_csv_with_duplicates)
    
    # Immediately after upload: no households created
    assert Household.query.filter_by(import_id=import_id).count() == 0
    
    # All household_suggestions are pending (not approved)
    suggestions = HouseholdSuggestion.query.filter_by(import_id=import_id).all()
    assert len(suggestions) > 0
    assert all(s.status == "pending" for s in suggestions)
    
    # All contacts still have NULL household_id
    contacts = Contact.query.filter_by(import_id=import_id).all()
    assert all(c.household_id is None for c in contacts)

def test_resolve_duplicate_different_decision():
    """Operator can mark duplicates as 'different' (different people)."""
    import_id = upload_csv(sample_csv_with_duplicates)
    duplicate = DuplicateCandidate.query.filter_by(import_id=import_id).first()
    
    # Before decision: unreviewed
    assert duplicate.decision == "unreviewed"
    assert duplicate.decided_by is None
    
    # Operator marks as different
    resolve_duplicate(
        candidate_id=duplicate.id,
        decision="different",
        reviewer_notes="Name similarity is coincidence, different people",
        decided_by="operator@example.com"
    )
    
    # After decision: persisted
    updated = DuplicateCandidate.query.get(duplicate.id)
    assert updated.decision == "different"
    assert updated.reviewer_notes == "Name similarity is coincidence, different people"
    assert updated.decided_by == "operator@example.com"
    assert updated.decided_at is not None

def test_resolve_duplicate_same_person_record_only():
    """v1 allows 'same_person' decision (record-only, no merge)."""
    import_id = upload_csv(sample_csv_with_duplicates)
    duplicate = DuplicateCandidate.query.filter_by(import_id=import_id).first()
    
    # Operator marks as same_person with notes
    resolve_duplicate(
        candidate_id=duplicate.id,
        decision="same_person",
        reviewer_notes="Same person, verified by operator",
        decided_by="operator@example.com"
    )
    
    # Decision is recorded
    updated = DuplicateCandidate.query.get(duplicate.id)
    assert updated.decision == "same_person"
    assert updated.reviewer_notes == "Same person, verified by operator"
    assert updated.decided_by == "operator@example.com"
    assert updated.decided_at is not None
    
    # CRITICAL: No merge action occurs in v1 (contacts remain separate)
    # The recorded decision is available for v2 merge workflow
    contact_a = Contact.query.get(duplicate.contact_id_a)
    contact_b = Contact.query.get(duplicate.contact_id_b)
    assert contact_a.id != contact_b.id  # Still separate contacts
    assert contact_a.household_id != contact_b.household_id or (
        contact_a.household_id is None and contact_b.household_id is None
    )  # Not merged into same household

def test_exports_contain_approved_values():
    """Export Clean CSV contains approved normalization values."""
    import_id = upload_csv(sample_csv)
    
    # Approve all normalizations
    suggestions = ContactSuggestion.query.filter_by(
        import_id=import_id, status="pending"
    ).all()
    for sugg in suggestions:
        approve_normalization(sugg.id, reviewed_by="operator")
    
    # Generate export
    exported_csv = export_clean(import_id)
    
    # Verify: exported values are from approved_contacts view, not raw
    for suggestion in suggestions:
        # Find corresponding row in exported CSV
        row = next((r for r in exported_csv if r["id"] == str(suggestion.contact_id)), None)
        assert row is not None
        # Exported value should be approved suggestion, not raw
        if suggestion.field_name == "email":
            assert row["email"] == suggestion.suggested_value

**Enforcement Strategy for contacts.household_id Write Protection:**

contacts.household_id may only be modified by `approve_household()`. All household ID assignments must go through a single gatekeeper method.

**Implementation Requirement:**

Create a single `ContactRepository.assign_household_id_from_approval()` method. All updates to contacts.household_id must flow through this method. No other repository or service method may update contacts.household_id directly.

**v1 Enforcement:**
- All contacts.household_id updates must originate from `approve_household()` → `ContactRepository.assign_household_id_from_approval()`
- Tests must verify that `ContactRepository.assign_household_id_from_approval()` is called only from the approval workflow
- Code review should confirm no other code paths write to contacts.household_id

**Optional Database-Level Enforcement (SQLite Trigger):**

If you require database-level enforcement, add a SQLite BEFORE UPDATE trigger on the contacts table:

```sql
CREATE TRIGGER prevent_direct_household_id_update
BEFORE UPDATE OF household_id ON contacts
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Direct household_id updates prohibited. Use approve_household() workflow.');
END;
```

However, this trigger will also block the legitimate `approve_household()` update. To allow the approval, either:
1. Drop and recreate the trigger conditionally during approval, or
2. Use application-layer enforcement without triggers (recommended)

**Tests for approval workflow:**

```python
def test_approve_household_sets_household_id():
    """Verify approve_household() correctly sets household_id for all members."""
    import_id = upload_csv(sample_csv_with_households)
    suggestion = HouseholdSuggestion.query.filter_by(
        import_id=import_id, status="pending"
    ).first()
    
    # Before approval: no household_id
    contact_ids = [suggestion.contact_id_primary] + json.loads(suggestion.contact_ids_other)
    for cid in contact_ids:
        assert Contact.query.get(cid).household_id is None
    
    # Approve household
    approve_household(suggestion.id, reviewed_by="operator")
    
    # After approval: all members have matching household_id
    for cid in contact_ids:
        assert Contact.query.get(cid).household_id is not None
        assert Contact.query.get(cid).household_id.startswith("HH_")

def test_household_id_only_via_approval():
    """Verify ContactRepository.assign_household_id_from_approval() is the only update path."""
    # This test verifies through code inspection that no other service/repository method
    # calls UPDATE on contacts.household_id except approve_household()
    import ast
    import scripts.householder.repository as repo_module
    
    # Parse repository source and verify only assign_household_id_from_approval() touches household_id
    # (Implementation: grep the module for UPDATE statements or use AST to verify)
```

### 11.3 E2E Tests (Playwright UI Workflows)

E2E tests verify complete user workflows through the web interface. These tests use Playwright to simulate operator actions and verify UI behavior. DB assertions in E2E are limited to critical invariants verified via test fixtures (not live queries during test execution).

```python
def test_upload_csv_workflow():
    """Upload CSV, see dashboard with suggestion counts."""
    page.goto("/imports/new")
    page.set_input_files('input[type="file"]', "sample.csv")
    page.click('[data-testid="upload-submit"]')
    page.wait_for_selector('[data-testid="import-summary"]')
    
    # Verify summary shows counts
    summary = page.text_content('[data-testid="import-summary"]')
    assert "15 contacts" in summary or "Processed 15" in summary
    assert "pending" in summary.lower()

def test_review_normalizations_workflow():
    """Review normalization suggestions and approve one."""
    page.goto(f"/imports/{import_id}/normalizations")
    
    # Verify table visible
    table = page.wait_for_selector('[data-testid="normalizations-table"]')
    assert table is not None
    
    # Find and click approve on first row
    first_row = page.query_selector('[data-testid="normalization-row"]')
    first_row.scroll_into_view_if_needed()
    page.click('[data-testid="approve-normalization"]')
    
    # Verify UI feedback (e.g., row removed or marked approved)
    page.wait_for_selector('text=Approved', timeout=5000)

def test_bulk_approve_with_confirmation():
    """Bulk approve shows modal with change preview."""
    page.goto(f"/imports/{import_id}/normalizations")
    
    # Click bulk approve
    page.click('[data-testid="bulk-approve-normalizations"]')
    
    # Modal appears with preview
    modal = page.wait_for_selector('[data-testid="bulk-confirm-modal"]')
    assert modal is not None
    
    # Verify modal shows count and allows confirmation
    modal_text = modal.text_content()
    assert "normalizations" in modal_text.lower() or "changes" in modal_text.lower()
    
    # Confirm
    page.click('[data-testid="bulk-confirm-modal"] button:has-text("Confirm")')
    page.wait_for_selector('text=Approved', timeout=5000)

def test_review_households_workflow():
    """Review household suggestions and approve one."""
    page.goto(f"/imports/{import_id}/households")
    
    # Verify household card visible
    card = page.wait_for_selector('[data-testid="household-card"]')
    assert card is not None
    
    # Click approve
    page.click('[data-testid="approve-household"]')
    
    # Verify feedback
    page.wait_for_selector('text=Approved', timeout=5000)

def test_review_duplicates_workflow():
    """Review duplicate candidates and mark as different."""
    page.goto(f"/imports/{import_id}/duplicates")
    
    # Verify duplicate card visible
    card = page.wait_for_selector('[data-testid="duplicate-card"]')
    assert card is not None
    
    # Click "Different"
    page.click('[data-testid="duplicate-different"]')
    
    # Verify feedback
    page.wait_for_selector('text=Recorded', timeout=5000)

def test_export_clean_workflow():
    """Export Clean downloads CSV with approved values."""
    page.goto(f"/imports/{import_id}/export")
    
    # Click export clean
    async with page.expect_download() as download_info:
        page.click('[data-testid="export-clean"]')
    
    download = await download_info.value
    path = await download.path()
    
    # Verify file contains approved values (parse CSV and spot-check)
    import csv
    with open(path) as f:
        rows = list(csv.DictReader(f))
        assert len(rows) > 0
        # Row should have lowercase email (if email was normalized and approved)

def test_defer_suggestion_workflow():
    """Defer hides suggestion from primary queue."""
    page.goto(f"/imports/{import_id}/normalizations")
    
    # Get initial count
    initial_rows = page.query_selector_all('[data-testid="normalization-row"]')
    initial_count = len(initial_rows)
    
    # Defer first row
    first_row = initial_rows[0]
    first_row.scroll_into_view_if_needed()
    page.click('[data-testid="defer-normalization"]')
    
    # Verify row removed from primary queue (count decreased)
    page.wait_for_timeout(500)
    updated_rows = page.query_selector_all('[data-testid="normalization-row"]')
    assert len(updated_rows) == initial_count - 1
```

---

## 12. Test IDs for UI Stability

Add these `data-testid` attributes to HTML elements for reliable element selection in Playwright tests. Test IDs enable stable, semantic element selection independent of CSS changes.

### 12.1 Upload Page
```html
<input data-testid="upload-file-input" type="file">
<button data-testid="upload-submit">Upload</button>
<div data-testid="import-summary">Processed 50 contacts...</div>
```

### 12.2 Dashboard
```html
<div data-testid="total-contacts-count">50</div>
<div data-testid="validation-tier-breakdown">✓ PASS: 45, ⚠ WARNING: 5, ✗ FAIL: 0</div>
<div data-testid="pending-normalizations-count">12</div>
<div data-testid="pending-households-count">5</div>
<div data-testid="pending-duplicates-count">3</div>
```

### 12.3 Normalizations Review Queue
```html
<table data-testid="normalizations-table">
  <tr data-testid="normalization-row">
    <td data-testid="normalization-field">email</td>
    <td data-testid="normalization-current">Jane@Gmail.com</td>
    <td data-testid="normalization-suggested">jane@gmail.com</td>
    <button data-testid="approve-normalization">Approve</button>
    <button data-testid="reject-normalization">Reject</button>
    <button data-testid="defer-normalization">Defer</button>
  </tr>
</table>
<button data-testid="bulk-approve-normalizations">Approve All</button>
<div data-testid="bulk-confirm-modal">
  <p>10 email fields will be normalized...</p>
  <button data-testid="bulk-confirm-approve">Confirm</button>
  <button data-testid="bulk-confirm-cancel">Cancel</button>
</div>
```

### 12.4 Households Review Queue
```html
<div data-testid="household-card">
  <div data-testid="household-primary">Primary: Jane (Donation: $1000)</div>
  <div data-testid="household-members">Members: Jane, John, Mary</div>
  <button data-testid="approve-household">Approve Household</button>
  <button data-testid="reject-household">Reject</button>
  <button data-testid="defer-household">Defer</button>
</div>
```

### 12.5 Duplicates Review Queue
```html
<div data-testid="duplicate-card">
  <div data-testid="duplicate-contact-a">Jane Doe | jane@example.com | 555-1234</div>
  <div data-testid="duplicate-contact-b">Jane Doe | jane@example.com | 555-1234</div>
  <div data-testid="duplicate-confidence">95% confidence (email exact match)</div>
  <button data-testid="duplicate-same-person">Same Person</button>
  <button data-testid="duplicate-different">Different</button>
  <button data-testid="duplicate-defer">Defer</button>
</div>
```

### 12.6 Export Page
```html
<button data-testid="export-clean">Export Clean</button>
<button data-testid="export-household">Export by Household</button>
<button data-testid="export-backlog">Export Backlog</button>
<button data-testid="export-raw">Export Raw</button>
```

---

## 13. Revised Definition of Done

- ✅ Raw data identical to uploaded CSV after all processing
- ✅ 100% of normalizations appear as pending suggestions (not auto-applied)
- ✅ 100% of household groupings require explicit Approve click
- ✅ 100% of duplicate decisions require operator review
- ✅ Dashboard shows suggestion counts, not auto-fixed counts
- ✅ Export Clean contains only human-approved values
- ✅ Export by Household groups related contacts with primary contact info
- ✅ Bulk approvals show confirmation modal with change preview
- ✅ All tests pass without any auto-write logic
- ✅ Forbidden function name prefixes: `auto_*`, `merge_*`
- ✅ Forbidden behaviors: no auto-apply, no auto-merge, no direct field mutation, no API writeback
- ✅ Allowed: `export_clean_contacts()`, `approved_contacts` view, `clean_contacts.csv` file
- ✅ Audit trail: timestamp, operator, # approved for each action

---

### Acceptance Criteria (Detailed)

**Data Preservation:**
- ✅ raw_import_rows table is append-only and immutable (never modified, never deleted)
- ✅ raw_import_rows.raw_json field is byte-for-byte or value-for-value identical to uploaded CSV
- ✅ contacts table baseline fields (full_name, email, phone, address_line_1, city, state, postal_code) are immutable after extraction
- ✅ contacts.household_id is NULL until explicit household approval (cannot be set directly or by accident)

**Suggestion Generation & Lifecycle:**
- ✅ 100% of normalizations appear as pending contact_suggestions (not auto-applied)
- ✅ 100% of household groupings appear as pending household_suggestions (no household records created until approval)
- ✅ 100% of duplicates appear as unreviewed duplicate_candidates (not auto-merged, not auto-marked)
- ✅ All suggestions have confidence scores (no vague recommendations)
- ✅ Suggestions are not deleted or modified after generation (only status changed via operator actions: approve/reject/defer)

**Operator Workflows:**
- ✅ Single approval: operator clicks Approve/Reject/Defer button → system immediately updates suggestion status + records review metadata (reviewed_by, reviewed_at, ip_address, user_agent)
- ✅ Bulk approval: operator clicks "Approve All" → confirmation modal shows change preview → operator clicks Confirm → all approved
- ✅ Deferred items: operator can defer, hide from primary queue, and later un-defer to reconsider
- ✅ No accidental writes: all system modifications require explicit operator action (no background jobs, no auto-apply timers)

**Views & Exports:**
- ✅ approved_contacts view: derives clean contact data from contact baseline + approved contact_suggestions (COALESCE pattern)
- ✅ households_summary view: one row per approved household (primary contact info, member count, total donation amount)
- ✅ Export Clean: CSV with approved values (queries approved_contacts view) + household_id if member of approved household
- ✅ Export by Household: CSV grouped by household (one row per primary contact, member list, total donation)
- ✅ Export Backlog: CSV of pending suggestions (not yet approved)
- ✅ Export Raw: original imported CSV (unchanged)

**Audit Trail:**
- ✅ contact_suggestions: tracks reviewed_by, reviewed_at, ip_address, user_agent for all state changes (approve/reject/defer)
- ✅ household_suggestions: tracks reviewed_by, reviewed_at, ip_address, user_agent for all state changes (approve/reject/defer)
- ✅ duplicate_candidates: tracks decided_by, decided_at, reviewer_notes for all decisions
- ✅ All timestamps in UTC

**Testing:**
- ✅ All unit tests pass (suggestion engines verified, no DB writes)
- ✅ All integration tests pass (DB state preserved, approval workflows verified, immutability enforced)
- ✅ All E2E tests pass (Playwright workflows: upload → review → approve → export)
- ✅ Critical test (`test_no_auto_merge_critical`) confirms zero households/contact.household_id changes without operator click
- ✅ Test IDs present on all interactive UI elements (data-testid attributes)

**Household ID Generation:**
- ✅ Deterministic: same address + zip5 → same household_id across imports (enables v2 multi-import linking)
- ✅ Stable format: HH_<8-char-lowercase-md5-hex> or HH_<12-char-hex> if collision detected
- ✅ Generated only at approval time (when household_suggestion approved), never during suggestion generation

**Function Signatures & Guards:**
- ✅ Processor functions imported with version check (requires Processor v3.4+)
- ✅ resolve_duplicate() records 'same_person' decision (record-only, no merge in v1)
- ✅ CRITICAL: No auto-merge, no automatic household creation, no automatic contact field modification
- ✅ No functions named merge_*, auto_*, auto_apply, auto_clean, auto_write
- ✅ Allowed function names: approve_normalization, reject_normalization, defer_normalization, approve_household, reject_household, defer_household, resolve_duplicate, export_clean_contacts, suggest_normalizations, suggest_households, suggest_duplicates

**User Experience:**
- ✅ Dashboard shows live counts (pending normalizations, households, duplicates)
- ✅ Review queues are paginated and filterable
- ✅ Bulk actions include confirmation modal with change preview
- ✅ Defer state is hidden from primary queue but accessible via "View Deferred" link
- ✅ Keyboard shortcuts (Tab, Escape) optional but recommended for efficiency

---

## 14. Implementation Order

Claude Code should follow this 16-step sequence for safe, incremental development. Each step should be committed separately with passing tests before proceeding to the next.

1. **Inspect Givebutter Processor repository**
   - Verify actual module path for fuzzy_email_match, normalize_phone, validate_email_format
   - Check processor.__version__ (must be 3.4+)
   - Create processor_adapter.py if functions live under different path

2. **Create database schema migrations**
   - raw_import_rows (append-only immutable)
   - contacts (baseline extracted records, household_id mutable only after approval)
   - contact_suggestions (with status enum: pending/approved/rejected/deferred)
   - household_suggestions (with status enum: pending/approved/rejected/deferred)
   - households (created only after approval)
   - duplicate_candidates (with decision enum: unreviewed/same_person/different/deferred)
   - Add ip_address, user_agent fields to suggestion tables

3. **Implement raw_import_rows upload flow (immutable)**
   - POST /imports/new — file upload handler
   - Parse CSV, store rows in raw_import_rows (append-only)
   - Test: raw_import_rows is never modified after creation

4. **Implement contact extraction**
   - Extract baseline contact records from raw_import_rows
   - Map CSV columns to contacts table (full_name, email, phone, address_line_1, city, state, postal_code)
   - No field-level cleaning (preserve original values)
   - Test: contacts table has exact same values as raw_import_rows

5. **Implement suggestion engines (generators, no writes)**
   - suggest_normalizations(contact) → returns list of suggestions with confidence scores
   - suggest_households(contacts) → returns list of household suggestions (no household_id generation)
   - suggest_duplicates(contacts) → returns list of duplicate candidate pairs
   - Test: engines return suggestions only, do not write to DB

6. **Implement suggestion persistence (pending only)**
   - Create contact_suggestions rows (status=pending)
   - Create household_suggestions rows (status=pending)
   - Create duplicate_candidates rows (decision=unreviewed)
   - Test: all suggestions created with correct status values

7. **Implement normalization approval workflow**
   - approve_normalization(suggestion_id, reviewed_by) → UPDATE contact_suggestions SET status='approved', reviewed_by, reviewed_at
   - reject_normalization(suggestion_id, reviewed_by, notes) → UPDATE status='rejected', reviewed_by, reviewed_at
   - defer_normalization(suggestion_id, reviewed_by, notes) → UPDATE status='deferred', reviewed_by, reviewed_at
   - Test: raw contacts unchanged, approved_contacts view reflects approved values

8. **Implement household approval workflow**
   - approve_household(suggestion_id, reviewed_by) → CREATE households row, UPDATE contacts.household_id, reviewed_by, reviewed_at
   - reject_household(suggestion_id, reviewed_by, notes) → UPDATE household_suggestions SET status='rejected'
   - defer_household(suggestion_id, reviewed_by, notes) → UPDATE household_suggestions SET status='deferred'
   - implement get_primary_contact(contact_ids) waterfall logic
   - implement generate_household_id(address_line_1, zip5) with deterministic MD5 hashing (scalar parameters only)
   - Test: household record created, contacts.household_id set, no accidental writes

9. **Implement duplicate candidate workflow**
   - resolve_duplicate(candidate_id, decision, reviewer_notes, decided_by) → UPDATE duplicate_candidates
   - Allowed decisions: 'same_person', 'different', 'deferred'
   - v1 behavior: record-only; no contact merge, no household assignment, no field mutation
   - Test: same_person decision is persisted but contacts remain separate (not merged)

10. **Implement approved_contacts and households_summary views**
    - approved_contacts: COALESCE pattern for approved normalization values
    - households_summary: one row per household, member count, total donation
    - Test: views compute correctly, reflect current approval state

11. **Implement dashboard (GET /imports/{id})**
    - Show total contacts, validation tier breakdown
    - Show pending suggestion counts (normalizations, households, duplicates)
    - Show recent actions by current user
    - Test: counts are accurate, update after approvals

12. **Implement review queues (GET /imports/{id}/normalizations|households|duplicates)**
    - Normalizations queue: paginated table with approve/reject/defer per row
    - Households queue: card layout with approve/reject/defer per suggestion
    - Duplicates queue: two-column comparison with decision buttons
    - Bulk actions with confirmation modal
    - Test: queues load, elements clickable, filters work

13. **Implement exports (GET /imports/{id}/export)**
    - Export Clean: query approved_contacts view, output CSV
    - Export by Household: query households_summary view, output CSV
    - Export Backlog: query pending suggestions, output CSV
    - Export Raw: output original raw_import_rows as CSV
    - Test: exported values match expectations, files downloadable

14. **Implement deferred item management (hidden queue)**
    - Optional: secondary queue page showing deferred items
    - Allow un-defer action to restore item to primary queue
    - Test: deferred items hidden from primary queue, un-defer restores

15. **Add all unit, integration, and E2E tests**
    - Unit tests: suggestion engines, waterfall logic, household ID generation (section 11.1)
    - Integration tests: DB state preservation, approval workflows, immutability guardrails (section 11.2)
    - E2E tests: Playwright workflows with data-testid selectors (section 11.3)
    - Critical test: test_no_auto_merge_critical ensures zero auto-writes
    - Test coverage target: >90% code coverage for approval paths

16. **Final audit and documentation**
    - Run full test suite (unit + integration + E2E)
    - Verify CLAUDE.md matches implementation
    - Verify all data-testid attributes present for E2E stability
    - Generate test report with coverage metrics
    - Commit with message: "feat: Householder v1 complete — raw data preservation, human-in-the-loop approvals, household grouping, duplicate detection"

---

## 15. v2 Scope (Deferred)

- **Salutation generation**: Generate mail_salutation and email_salutation per nonprofit preferences (via Claude/Gemini prompt)
- **Retention tracking**: Flag donors at risk of lapsing (last gift >12 months ago, low lifetime value)
- **Source attribution**: Track which import batch / campaign each contact originated from
- **Givebutter API sync**: Writeback to Givebutter API (if nonprofit wants two-way sync)
- **Multi-import linking**: Link households across multiple CSV imports (same person donating in May and June)
- **Duplicate merge**: Implement 'same_person' decision with actual merge logic (only after v1 is hardened)

---

## 16. Success Metrics

**Code Quality:**
- ✅ All unit/integration/E2E tests pass
- ✅ Code coverage >90% on approval paths
- ✅ Zero linting errors (flake8, black)
- ✅ All imports verified (Processor v3.4+, processor_adapter working)

**Product Quality:**
- ✅ Operator can upload 15-row sample CSV in <10 seconds
- ✅ Dashboard loads in <2 seconds with suggestion counts
- ✅ Operator can approve 1 normalization and export clean result in <1 minute
- ✅ Operator can approve 1 household and verify 3 members grouped correctly
- ✅ Export files are well-formed CSV, importable to CRM

**Safety & Compliance:**
- ✅ Zero automatic writes (all changes logged with operator name)
- ✅ Zero raw data modifications (audit trail verified)
- ✅ Zero household_id writes except via approve_household()
- ✅ Zero merge operations (v1 only records duplicate decisions)
- ✅ All operator actions timestamped and IP-logged

---

**Next Step:** Begin implementation following the 16-step sequence in section 14.
