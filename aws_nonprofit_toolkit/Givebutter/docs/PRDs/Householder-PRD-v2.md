# Givebutter Data Hygiene & Householding — v2 PRD for Claude Code (Human-in-Loop Only)

**Last updated:** 2026-06-07  
**Owner:** Gautam Biswas  
**Status:** v2 (Revised for integration with Givebutter Processor)

---

## 1. Mission

Build v1 of a lightweight web app that ingests Givebutter contact data via CSV upload, analyzes it for data quality issues and household relationships, and presents suggestions for cleaning and grouping. The app must never modify raw data automatically. Every normalization, duplicate resolution, and household grouping requires explicit human approval.

Householder builds ON TOP OF the existing Givebutter Processor validation system, focusing on deduplication and household grouping rather than field-level validation.

---

## 2. Non-Negotiables for Claude Code

- **Preserve raw imported data forever.** Never overwrite raw_rows.
- **No automatic cleaning.** No automatic merging. No automatic household assignment.
- **All engine outputs are suggestions with confidence scores.**
- **Human must click Approve before any suggestion is applied** to derived tables.
- **Bulk approvals require confirmation dialogs** with preview of changes.
- **Reuse existing validation** from Givebutter Processor (fuzzy email matching, phone validation) — do not duplicate.
- **Do not implement** API writeback, retention features, source attribution, or Meta CAPI in v1 (deferred to v2).

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
- CSV upload with raw preservation (raw_import table)
- Contact extraction and normalization suggestions (email case, phone format, address)
- Household matching engine (same email, address+zip, phone+name patterns)
- Duplicate candidate detection (pairs likely to be same person)
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

---

## 6. Data Model

### Existing (from Processor)
- `donations` — Transaction-level records from Givebutter CSV
- `validation_tier` — PASS / WARNING / FAIL status per transaction

### New Tables for Householder

**raw_import** — Raw CSV ingestion (NEVER modified)
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

**contacts** — Denormalized view of importable contacts (raw values, never auto-cleaned)
- id (PK)
- import_id (FK)
- raw_row_id (FK to raw_import)
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

**contact_suggestions** — Proposed normalizations (email case, phone format, address cleanup)
- id (PK)
- contact_id (FK)
- field_name (email / phone / address / name)
- current_value
- suggested_value
- reason (e.g., "standardize email case", "extract digits only")
- confidence_score (80-100)
- status (pending / approved / rejected)
- suggested_by
- approved_by (nullable)
- approved_at (nullable)

**household_suggestions** — Proposed groupings (multiple people → same household)
- id (PK)
- import_id (FK)
- contact_id_primary (FK)
- contact_ids_other (JSON array of contact IDs)
- match_reason (e.g., "same email", "address + zip + name")
- match_confidence_score (65-95)
- status (pending / approved / rejected / deferred)
- suggested_by
- approved_by (nullable)
- approved_at (nullable)

**households** — Confirmed household groups (created ONLY after approval)
- id (PK)
- import_id (FK)
- household_id (text, format: `HH_` + first 8 chars of MD5 hash)
- primary_contact_id (FK to contacts)
- member_count
- created_by
- created_at

**Household ID Generation Algorithm:**
```python
def generate_household_id(primary_contact: Contact) -> str:
    """
    Generate stable household ID from address + zip5.
    Format: HH_<8-char-md5>
    
    Input: normalized_address (lowercase, no punctuation) + zip5
    Example: 
      primary_contact.address = "123 Main Street"
      primary_contact.zip5 = "94301"
      normalized = "123 main street94301"
      md5_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
      household_id = f"HH_{md5_hash}"
    
    Generated: Only at approval time (when household_suggestion status → approved)
    Stability: Same across imports (deterministic, based on address + zip only)
    """
    normalized = (
        f"{primary_contact.address_line_1.lower().replace(' ', '')} "
        f"{primary_contact.zip5}"
    ).encode()
    return f"HH_{hashlib.md5(normalized).hexdigest()[:8]}"
```

**Why this approach:**
- Deterministic: same address + zip = same ID across imports (useful for multi-batch household linking in v2)
- Collision-resistant: 8-char hex = 2^32 combinations (sufficient for 10k+ households)
- Readable: `HH_` prefix makes it obvious it's a household ID
- Generated at approval time: ensures no accidental household_id before operator approval

**duplicate_candidates** — Likely duplicates (same person, separate transactions)
- id (PK)
- contact_id_a (FK)
- contact_id_b (FK)
- confidence_score (70-95)
- match_reasons (JSON, e.g., ["email exact match", "phone exact match"])
- decision (same_person / different / deferred / unreviewed)
- decided_by (nullable)
- decided_at (nullable)

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
  c.address_line_1,
  c.city,
  c.state,
  c.postal_code,
  c.amount_cents,
  c.campaign_title,
  c.donation_date,
  c.validation_tier,
  h.household_id,
  h.primary_contact_id
FROM contacts c
LEFT JOIN households h ON c.id = h.primary_contact_id OR c.id IN (
  SELECT primary_contact_id FROM households WHERE household_id = h.household_id
)
```

**Implementation Notes:**
- The view is computed at query time (no redundant storage)
- For each field, if there's an approved suggestion, use suggested_value; otherwise use the raw value from contacts
- "Export Clean" queries this view to generate the CSV (one row per contact with approved values + household_id)
- Household assignment only appears if the contact is in an approved household_suggestion
- The view automatically reflects current state: if an approval is withdrawn, the view reverts to raw value

**households_summary** — One row per household (for "Export by Household" report)
```sql
SELECT 
  h.household_id,
  h.primary_contact_id,
  ac_primary.full_name AS primary_name,
  ac_primary.email AS primary_email,
  COUNT(c.id) AS member_count,
  GROUP_CONCAT(c.id) AS member_ids,
  SUM(c.amount_cents) AS total_amount_cents
FROM households h
JOIN approved_contacts ac_primary ON h.primary_contact_id = ac_primary.id
JOIN contacts c ON h.household_id = c.household_id OR h.primary_contact_id = c.id
GROUP BY h.household_id
```

**Data Flow on Approval:**
1. Operator clicks "Approve" on a contact_suggestion → `contact_suggestions.status = 'approved'`
2. `approved_contacts` view automatically reflects approved values (recomputed at query time)
3. "Export Clean" CSV includes these approved values
4. Operator clicks "Approve" on a household_suggestion → `households` record created
5. `households_summary` view includes household with member info
6. "Export by Household" CSV includes household groupings

---

## 7. Suggestion Engines (Never Auto-Apply)

### 7.1 Normalization Suggestions (Low Risk, High Confidence)

For each contact, generate suggestions:

| Field | Rule | Reason | Confidence |
|-------|------|--------|-----------|
| **email** | Lowercase, trim whitespace | Standardize case | 100 |
| **phone** | Extract digits only (last 10 for US) | Standardize format | 95 |
| **name** | Title Case | Consistency | 90 |
| **address** | Lowercase, remove double spaces, expand "st" → "street" | Match households | 85 |

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

For each contact, score against all other contacts. Match rules (in priority order):

| Rule | Fields | Confidence | Reason |
|------|--------|-----------|--------|
| Exact email match | normalized_email | 95 | Same person, high confidence |
| Address + zip + last name (all exact) | address_line_1 + zip5 + last_name | 85 | Likely household |
| Phone + last name + zip (all exact) | phone_digits + last_name + zip5 | 80 | Likely household |
| Phone + name fuzzy match (70%+) | phone_digits + full_name similarity | 75 | Possible household, needs review |
| Last name + zip + first initial + address fuzzy (70%+) | last_name + zip5 + first_initial + address similarity | 70 | Weak match, likely same household |

**Important:**
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

Store as `duplicate_candidates` with status = `unreviewed`. Operator decides: "Same Person" / "Different" / "Defer".

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
- Filters: Field (email / phone / name / address), Confidence (high / medium / low)

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
   - "This cannot be undone. Approve?"
2. Require confirmation: [Cancel] [Approve]
3. Log action: timestamp, operator, # approved, change details

### 8.6 Export

**GET /imports/{id}/export** — Export options
- Button 1: "Export Clean" — Download CSV with approved normalizations + household_id
- Button 2: "Export by Household" — Download CSV, one row per household (primary contact info, member count, members list)
- Button 3: "Export Backlog" — Download CSV of pending suggestions not yet approved
- Button 4: "Export Raw" — Download original import (unchanged)

---

## 9. Function Signatures Claude Must Implement

### Suggestion Engines (never write, only suggest)

```python
def suggest_normalizations(contact: dict) -> list[dict]:
    """Return list of normalization suggestions for a single contact."""
    # Returns: [{"field": "email", "current": "Jane@Gmail.com", "suggested": "jane@gmail.com", "reason": "standardize case", "confidence": 100}]
    
def suggest_households(contacts: list[dict]) -> list[dict]:
    """Return household grouping suggestions for a batch of contacts."""
    # Returns: [{"primary_id": "contact_1", "member_ids": ["contact_2", "contact_5"], "match_reason": "same email", "confidence": 95}]

def suggest_duplicates(contacts: list[dict]) -> list[dict]:
    """Return duplicate candidate pairs (likely same person)."""
    # Returns: [{"contact_a": "id_1", "contact_b": "id_3", "confidence": 85, "reasons": ["phone match", "address match"]}]

def get_primary_contact(household_ids: list[str]) -> str:
    """Select primary contact using waterfall logic."""
    # Waterfall: highest donation amount → most recent → oldest id

def generate_household_id(primary_contact: Contact) -> str:
    """Generate stable household ID from address + zip5."""
    # Format: HH_<8-char-md5>
    # Input: normalized_address.lower() + zip5
    # Generated: Only at approval time
    # Stability: Deterministic (same address+zip = same ID across imports)
    
def apply_suggestion(suggestion_id: str, approved_by: str) -> None:
    """Apply a single approved suggestion (write to approved tables only)."""
    # Writes to contact_suggestions (status=approved) and derived tables
    # NEVER writes to raw_import
    
def get_hygiene_status(contact_id: str) -> dict:
    """Return hygiene status for a single contact."""
    # Returns: {"contact_id": "123", "issues": ["email typo", "phone format"], "status": "WARNING"}
    
def count_pending_suggestions(import_id: str) -> dict:
    """Return pending suggestion counts for an import."""
    # Returns: {"normalizations": 12, "households": 5, "duplicates": 3}
```

**Forbidden function names:** `merge`, `auto_clean`, `auto_fix`, `auto_write`, `auto_apply`

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

**Expected behavior after upload:**
- 0 changes to raw_import (verified by test)
- 12+ pending normalizations appear in queue
- 3+ household suggestions appear in queue
- 2+ duplicate candidates appear in queue
- Operator must click Approve for each change

---

## 11. Tests Claude Must Write

### Unit Tests

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
    assert suggestions[0]["suggested"] == "jane@gmail.com"
    # Verify DB was NOT written to
    assert Contact.query.filter_by(email="jane@gmail.com").first() is None

def test_suggest_household_does_not_create_household_id():
    """Household engine returns suggestions only, no household created."""
    contacts = [{"id": "1", "email": "same@email.com"}, {"id": "2", "email": "same@email.com"}]
    suggestions = suggest_households(contacts)
    assert suggestions[0]["suggested_household_id"] is None
    assert Household.query.count() == 0
    assert HouseholdSuggestion.query.count() > 0

def test_household_id_generated_at_approval_time():
    """Household ID generated only when household_suggestion approved, not before."""
    # Create suggestion (no ID yet)
    suggestion = HouseholdSuggestion.create(
        contact_id_primary=1, contact_ids_other=[2],
        match_reason="same email", confidence_score=95
    )
    assert suggestion.household_id is None  # Not yet
    
    # Approve
    apply_suggestion(suggestion.id, approved_by="operator")
    
    # After approval: household_id generated (HH_<8-char-md5>)
    household = Household.query.filter_by(primary_contact_id=1).first()
    assert household.household_id is not None
    assert household.household_id.startswith("HH_")
    assert len(household.household_id) == 11  # HH_ + 8 chars

def test_household_id_deterministic_across_imports():
    """Same address + zip5 → same household_id across different imports."""
    contact_1 = Contact.create(
        id=1, address_line_1="123 Main St", zip5="94301"
    )
    contact_2 = Contact.create(
        id=2, address_line_1="123 Main St", zip5="94301"  # Same address
    )
    
    hh_id_1 = generate_household_id(contact_1)
    hh_id_2 = generate_household_id(contact_2)
    
    assert hh_id_1 == hh_id_2  # Deterministic

def test_apply_suggestion_writes_only_to_approved_table():
    """Approving a suggestion updates approved tables, not raw."""
    suggestion = ContactSuggestion.create(contact_id=1, field="email", suggested="jane@gmail.com")
    apply_suggestion(suggestion.id, approved_by="operator@example.com")
    
    # Verify: suggestion marked approved
    assert suggestion.status == "approved"
    assert suggestion.approved_by == "operator@example.com"
    
    # Verify: raw contact unchanged
    assert Contact.query.get(1).email != "jane@gmail.com"  # Raw value unchanged

def test_primary_contact_waterfall():
    """Primary contact selected by highest donation → most recent → oldest id."""
    contacts = [
        {"id": "a", "amount": 100, "date": "2026-01-01"},
        {"id": "b", "amount": 500, "date": "2026-01-02"},  # Highest donation
        {"id": "c", "amount": 100, "date": "2026-06-01"},  # Most recent
    ]
    primary = get_primary_contact(["a", "b", "c"])
    assert primary == "b"  # Highest donation wins

def test_fuzzy_email_matching_reuses_processor():
    """Email suggestions reuse Processor's 70% fuzzy threshold."""
    contact = {"email": "jane@gmai.com"}
    suggestions = suggest_normalizations(contact)
    # Should suggest gmail.com based on Processor's fuzzy logic
    assert any("gmail.com" in s.get("suggested", "") for s in suggestions)
```

### Integration Tests

```python
def test_csv_upload_preserves_raw():
    """Raw import table is never modified after processing."""
    raw_json = {"email": "Jane@Gmail.com", "phone": "555.123.4567"}
    import_id = upload_csv([raw_json])
    
    # Verify raw is unchanged
    raw = RawImport.query.filter_by(import_id=import_id).first()
    assert raw.raw_json == raw_json
    
    # Verify suggestions were created (not auto-applied)
    suggestions = ContactSuggestion.query.filter_by(import_id=import_id).all()
    assert len(suggestions) > 0
    assert all(s.status == "pending" for s in suggestions)

def test_approve_email_suggestion_updates_approved_view_only():
    """Approving a suggestion writes to approved view, not raw."""
    suggestion = ContactSuggestion.create(
        contact_id=1, field="email",
        current="Jane@Gmail.com", suggested="jane@gmail.com"
    )
    apply_suggestion(suggestion.id, approved_by="operator")
    
    # Raw contact unchanged
    contact = Contact.query.get(1)
    assert contact.email == "Jane@Gmail.com"
    
    # Approved view (derived from contact_suggestions) shows approved suggestion
    approved = db.session.execute(
        "SELECT email FROM approved_contacts WHERE contact_id = 1"
    ).first()
    assert approved[0] == "jane@gmail.com"

def test_household_approval_creates_household():
    """Household suggestion approval creates household record."""
    suggestion = HouseholdSuggestion.create(
        import_id=1, contact_id_primary=1,
        contact_ids_other=[2, 3], match_reason="same email",
        confidence_score=95
    )
    
    # Before approval: no household
    assert Household.query.count() == 0
    
    # Approve
    apply_suggestion(suggestion.id, approved_by="operator")
    
    # After approval: household created
    household = Household.query.filter_by(primary_contact_id=1).first()
    assert household is not None
    assert household.member_count == 3

def test_no_auto_merge():
    """CRITICAL: Zero automatic merging or household creation."""
    import_id = upload_csv(sample_csv_with_duplicates)
    
    # Verify: no households created
    assert Household.query.filter_by(import_id=import_id).count() == 0
    
    # Verify: suggestions pending only
    suggestions = HouseholdSuggestion.query.filter_by(import_id=import_id).all()
    assert len(suggestions) > 0
    assert all(s.status == "pending" for s in suggestions)
```

### E2E Tests (Playwright)

```python
def test_upload_review_approve_export():
    """Full workflow: upload → review suggestions → approve → export clean."""
    # 1. Upload sample CSV
    page.goto("/imports/new")
    page.set_input_files('input[type="file"]', "sample.csv")
    page.click('button:has-text("Upload")')
    page.wait_for_selector('text=Processed')
    
    # 2. Verify raw data unchanged
    import_id = page.url.split("/")[-1]
    raw_count = db.query(RawImport).filter_by(import_id=import_id).count()
    assert raw_count == 15  # Sample has 15 rows
    
    # 3. Review normalizations
    page.goto(f"/imports/{import_id}/normalizations")
    suggestions = page.query_selector_all('button:has-text("Approve")')
    assert len(suggestions) > 0
    
    # 4. Approve first suggestion
    page.click('button:has-text("Approve")')
    page.wait_for_selector('text=Approved')
    
    # 5. Verify: raw unchanged, approved view updated
    raw = db.query(Contact).filter_by(import_id=import_id).first()
    assert raw.email == "Jane@Gmail.com"  # Raw unchanged
    
    # Approved view (derived from contact_suggestions) shows approved suggestion
    approved = db.session.execute(
        "SELECT email FROM approved_contacts WHERE contact_id = ?", (raw.id,)
    ).first()
    assert approved[0] == "jane@gmail.com"  # Approved view updated
    
    # 6. Export clean (queries approved_contacts view)
    page.goto(f"/imports/{import_id}/export")
    page.click('button:has-text("Export Clean")')
    # Verify downloaded file has approved values (from approved_contacts view)
```

---

## 12. Acceptance Criteria v1

- ✅ Raw data identical to uploaded CSV after all processing
- ✅ 100% of normalizations appear as pending suggestions (not auto-applied)
- ✅ 100% of household groupings require explicit Approve click
- ✅ 100% of duplicate decisions require operator review
- ✅ Dashboard shows suggestion counts, not auto-fixed counts
- ✅ Export Clean contains only human-approved values
- ✅ Export by Household groups related contacts with primary contact info
- ✅ Bulk approvals show confirmation modal with change preview
- ✅ All tests pass without any auto-write logic
- ✅ Zero functions named `merge`, `clean`, `auto_*`
- ✅ Audit trail: timestamp, operator, # approved for each action

---

## 13. Definition of Done

Claude delivers code where a nonprofit operator can:
1. Upload a Givebutter export
2. Review every suggested normalization, household grouping, and duplicate detection
3. Approve selectively via UI (single or bulk)
4. Confirm bulk actions with preview modal
5. Download clean contacts (with household_id for CRM import) or by-household export
6. With absolute guarantee: **nothing was changed without their explicit click**

Raw data is preserved forever. All changes are audit-logged. All tests pass.

---

## 14. v2 Scope (Deferred)

- **Salutation generation**: Generate mail_salutation and email_salutation per nonprofit preferences (via Claude/Gemini prompt)
- **Retention tracking**: Flag donors at risk of lapsing (last gift >12 months ago, low lifetime value)
- **Source attribution**: Track which import batch / campaign each contact originated from
- **Givebutter API sync**: Writeback to Givebutter API (if nonprofit wants two-way sync)
- **Multi-import linking**: Link households across multiple CSV imports (same person donating in May and June)

---

**Next Step:** Generate starter repo with tables, endpoints, and Playwright tests stubbed (ready for implementation).
