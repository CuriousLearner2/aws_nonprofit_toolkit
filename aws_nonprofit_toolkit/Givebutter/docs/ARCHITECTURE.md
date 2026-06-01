# System Architecture
## How the Givebutter Donation Processor is Built

**Version:** 3.0 | **Last Updated:** June 1, 2026

This document explains how the system works internally. If you're an operator, start with [OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md) instead. For design details and UI patterns, see [UX_GUIDE.md](../UX_GUIDE.md).

---

## High-Level System Architecture (v3.0)

```
┌────────────────────────────────────────────────────────────────┐
│           GIVEBUTTER DONATION PROCESSOR v3.0                   │
│         Web-Based Operator Review System                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  OPERATOR: Download CSV from Givebutter                       │
│                 ↓                                             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  FLASK WEB APP (http://localhost:8000)               │    │
│  │  (scripts/uploader/app.py)                           │    │
│  │                                                      │    │
│  │  • File upload endpoint                             │    │
│  │  • CSV parsing with validation                      │    │
│  │  • Processing queue management                      │    │
│  │  • Web UI for operator review                       │    │
│  └──────────┬──────────────────────────────────────────┘    │
│             │                                               │
│             ├─ Upload CSV                                  │
│             │                                               │
│             ↓                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PROCESSOR ENGINE (scripts/processor.py)             │   │
│  │                                                      │   │
│  │  • 7 validation types:                             │   │
│  │    - Email (typo detection, format)                │   │
│  │    - Phone (USA format, patterns)                  │   │
│  │    - Amount (range, high-dollar flagging)          │   │
│  │    - Name (length, special chars, unicode)         │   │
│  │    - Address (completeness)                        │   │
│  │    - Headers (column mapping, fuzzy match)         │   │
│  │    - Tier Assignment (PASS/WARNING/FAIL)          │   │
│  │                                                      │   │
│  │  • Duplicate detection:                            │   │
│  │    - Exact match: email, phone, address            │   │
│  │    - Fuzzy match: donor names (70% threshold)      │   │
│  │                                                      │   │
│  │  • Rules-based corrections:                        │   │
│  │    - Email typo suggestions                        │   │
│  │    - Phone format normalization                    │   │
│  │    - Amount categorization                         │   │
│  │                                                      │   │
│  │  • Output: Validation tiers + suggestions           │   │
│  └──────────┬──────────────────────────────────────────┘   │
│             │ (for each record)                             │
│             ↓                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  WEB UI: Per-Record Decision Interface              │   │
│  │  (scripts/uploader/templates/review.html)           │   │
│  │                                                      │   │
│  │  Display for each record:                           │   │
│  │  • Donor name, email, amount, phone                 │   │
│  │  • Validation tier (PASS/WARNING/FAIL)             │   │
│  │  • Issues found + suggestions                       │   │
│  │  • Decision dropdown (Approved/Followup/Rejected)   │   │
│  │  • Notes textarea (operator comments)               │   │
│  │                                                      │   │
│  │  Operator workflow:                                 │   │
│  │  1. Review each record                              │   │
│  │  2. Select decision from dropdown                   │   │
│  │  3. Add optional notes                              │   │
│  │  4. Click Save (per-record)                         │   │
│  │  5. Repeat for all records                          │   │
│  │  6. Click Submit when done                          │   │
│  │                                                      │   │
│  │  Features:                                          │   │
│  │  • Multi-session support (resume later)            │   │
│  │  • Decision persistence (decisions saved to CSV)   │   │
│  │  • Bulk actions (approve all, reject all)          │   │
│  │  • Responsive design (mobile, tablet, desktop)     │   │
│  │  • Full keyboard navigation                        │   │
│  │  • Screen reader accessible                        │   │
│  └──────────┬──────────────────────────────────────────┘   │
│             │ (operator makes decisions)                    │
│             ↓                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  OUTPUT GENERATION                                   │   │
│  │  (app.py: /api/processing/<file>/submit endpoint)  │   │
│  │                                                      │   │
│  │  When operator clicks Submit:                       │   │
│  │  1. Read all decisions from web form                │   │
│  │  2. Add Operator_Decision column to CSV             │   │
│  │  3. Add Operator_Notes column to CSV                │   │
│  │  4. Split into three files:                         │   │
│  │     • *_APPROVED.csv (for import)                   │   │
│  │     • *_FOLLOWUP.csv (needs attention)              │   │
│  │     • *_REJECTED.csv (don't import)                 │   │
│  │  5. Save to review/approved/, followup/, rejected/  │   │
│  │  6. Move source to review/completed/                │   │
│  │  7. Notify operator: "Done!"                        │   │
│  └──────────────────────────────────────────────────────┘   │
│             │ (file available for export)                   │
│             ↓                                               │
│  OPERATOR: Download output files and import to CRM           │
│                                                              │
└────────────────────────────────────────────────────────────────┘
```

---

## Data Flow (Step by Step)

### 1. Upload Phase

```
Givebutter (Export CSV)
    ↓ (user downloads)
Operator's Computer
    ↓ (drag/drop or click browse)
http://localhost:8000/upload
    ↓ (POST request with file)
Flask app receives file
    ↓
1. Validate file size (max 16 MB)
2. Validate file format (.csv)
3. Save to review/processing/ with timestamp
4. Return to UI with file path
    ↓
UI shows: "File uploaded. Processing..."
```

### 2. Validation Phase

```
Flask app routes to /api/processing/<file>
    ↓
1. Read CSV from review/processing/
2. Parse with csv.reader (not pandas)
3. Load rules from config/rules/rules_v2.4.json
4. For each row:
   a. Run 7 validation checks
   b. Assign tier (PASS/WARNING/FAIL)
   c. Generate suggestions
5. Check for duplicates
6. Return JSON with all records + validations
    ↓
Web UI displays results:
  • Total records: 150
  • PASS: 140
  • WARNING: 8
  • FAIL: 2
```

### 3. Decision Phase

```
Operator sees:
┌──────────────────────────────────────┐
│ Record 1: John Smith                 │
│ Email: john@gmail.com                │
│ Tier: PASS                           │
│ Decision: [Approved dropdown]        │
│ Notes: [textarea]                    │
│ [Save]                               │
└──────────────────────────────────────┘

Operator:
1. Selects "Approved"
2. Clicks [Save]
3. Decision sent to /api/processing/<file>/update
4. Flask saves decision to in-memory store
5. Repeat for all 150 records
6. Click [Submit Decisions]
```

### 4. Output Phase

```
Operator clicks [Submit Decisions]
    ↓
POST /api/processing/<file>/submit
    ↓
1. Verify all records have decisions
2. Create three output CSVs:
   - Approved records
   - Followup records
   - Rejected records
3. Add two new columns:
   - Operator_Decision (value from dropdown)
   - Operator_Notes (value from textarea)
4. Save files to:
   - review/approved/*_APPROVED.csv
   - review/followup/*_FOLLOWUP.csv
   - review/rejected/*_REJECTED.csv
5. Archive source file to review/completed/
6. Return success message
    ↓
Operator downloads output files
    ↓
Operator imports to CRM/accounting system
```

---

## Folder Structure (v3.0)

```
Givebutter/  (root directory)
│
├── scripts/
│   ├── processor.py              ← Validation engine (634 lines)
│   │   • 7 validation functions
│   │   • Duplicate detection
│   │   • Tier assignment logic
│   │
│   └── uploader/
│       ├── app.py               ← Flask web app (293 lines)
│       │   • File upload endpoint
│       │   • Processing queue endpoints
│       │   • Decision persistence endpoints
│       │   • CSV output generation
│       │
│       └── templates/
│           └── review.html      ← Web UI (468 lines)
│               • Upload form
│               • Review table with per-record decisions
│               • Dropdown, textarea, save buttons
│
├── config/
│   ├── rules/
│   │   └── rules_v2.4.json      ← Validation rules
│   │       • Email typo patterns
│   │       • Invalid phone patterns
│   │       • High-dollar threshold
│   │       • Fuzzy match sensitivity
│   │
│   └── reference_list.json      ← Learned patterns
│       • Email domains
│       • Valid TLDs
│       • Common amounts
│       • Name patterns
│
├── review/                       ← Processing folders
│   ├── processing/              (In-progress uploads)
│   │   └── upload_timestamp_filename.csv
│   │
│   ├── approved/                (APPROVED records - ready to import)
│   │   └── *_APPROVED.csv
│   │
│   ├── followup/                (NEEDS ATTENTION)
│   │   └── *_FOLLOWUP.csv
│   │
│   ├── rejected/                (DO NOT IMPORT)
│   │   └── *_REJECTED.csv
│   │
│   └── completed/               (ARCHIVED after submit)
│       └── upload_timestamp_filename.csv
│
├── tests/                        ← Test suite (330+ tests)
│   ├── unit/                    (130 tests)
│   │   ├── test_validation_email.py
│   │   ├── test_validation_phone.py
│   │   ├── test_validation_amount.py
│   │   ├── test_validation_name.py
│   │   ├── test_validation_address.py
│   │   ├── test_validation_header.py
│   │   └── test_tier_assignment.py
│   │
│   ├── integration/             (70 tests)
│   │   ├── test_processor_full.py
│   │   ├── test_decision_persistence.py
│   │   └── test_csv_formats.py
│   │
│   └── e2e/                     (80+ tests)
│       ├── test_e2e_upload_workflow.py
│       ├── test_e2e_decision_workflow.py
│       ├── test_e2e_visual_regression.py
│       └── test_e2e_form_input.py
│
├── .env                         ← Environment variables
├── pytest.ini                   ← Pytest config
├── requirements.txt             ← Dependencies
├── requirements-test.txt        ← Test dependencies
│
└── docs/
    ├── ARCHITECTURE.md          (this file)
    ├── API.md                   (Endpoint reference)
    ├── DEVELOPER.md             (Integration guide)
    ├── UX_GUIDE.md             (UI/UX patterns)
    ├── OPERATOR_MANUAL.md       (User guide)
    ├── PROCESSOR_GUIDE.md       (Validation details)
    ├── QUICK_START.md          (Setup)
    ├── SETUP_GUIDE.md          (Detailed setup)
    ├── FAQ.md                  (Q&A)
    ├── INDEX.md                (Doc index)
    ├── CHANGELOG.md            (Version history)
    ├── TEST_PLAN.md            (Test strategy)
    ├── TESTING.md              (How to run tests)
    ├── TEST_SUMMARY.md         (Test overview)
    └── TESTS_DELIVERED.md      (Delivery checklist)
```

---

## Component Details

### 1. Flask Web Application (`scripts/uploader/app.py`)

**Purpose:** Manages file uploads, processing queue, decision persistence, and output generation.

**Key Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve HTML form |
| `/upload` | POST | Receive CSV file, save to review/processing/ |
| `/api/processing` | GET | List files in processing queue |
| `/api/processing/<file>` | GET | Load file, validate, return records with validation results |
| `/api/processing/<file>/update` | POST | Save per-record decision (dropdown + notes) |
| `/api/processing/<file>/submit` | POST | Finalize decisions, generate output CSVs, archive file |
| `/api/processing/<file>/cancel` | POST | Cancel review, move file back (or delete) |
| `/health` | GET | API health check |

**Internal Flow:**

```python
# Upload
@app.route('/upload', methods=['POST'])
1. Receive file from browser
2. Validate filename, size, format
3. Save to review/processing/ as upload_TIMESTAMP_FILENAME
4. Return success with file path

# Get records for review
@app.route('/api/processing/<file>', methods=['GET'])
1. Load CSV from review/processing/
2. Parse with csv.reader
3. Load rules from config/
4. Run processor.validate_row() on each row
5. Detect duplicates
6. Return JSON: {file, records: [{name, email, tier, issues, suggestions, decision, notes}, ...]}

# Save decision
@app.route('/api/processing/<file>/update', methods=['POST'])
1. Receive {record_id, decision, notes}
2. Store in in-memory dict (keyed by file + record_id)
3. Return 200 OK

# Submit all decisions
@app.route('/api/processing/<file>/submit', methods=['POST'])
1. Load original CSV
2. Add Operator_Decision column (from in-memory store)
3. Add Operator_Notes column (from in-memory store)
4. Split into three CSVs (approved, followup, rejected)
5. Save to review/approved/, review/followup/, review/rejected/
6. Move source to review/completed/
7. Return success message
```

**State Management:**

- Files: Stored on disk in `review/processing/`
- Decisions: Stored in-memory during review session
- Persistence: Decisions written to output CSVs on submit
- Multi-session: If user closes browser, decisions are lost (user must resume and re-make decisions)

---

### 2. Validation Engine (`scripts/processor.py`)

**Purpose:** All validation logic for donation records.

**Seven Validation Functions:**

```python
def validate_email(email, rules)
  # Check format, detect typos (gmai.com → gmail.com)
  # Return: {tier, issues, suggestions}

def validate_phone(phone, rules)
  # USA phone format (10-11 digits)
  # Detect unusual patterns (extensions, letters)
  # Return: {tier, issues, suggestions}

def validate_amount(amount, rules)
  # Parse currency ($1,234.56)
  # Check range, flag high-dollar (>= $1000)
  # Return: {tier, issues, suggestions}

def validate_name(name, rules)
  # Check length, special chars, unicode support
  # Return: {tier, issues, suggestions}

def validate_address(address, rules)
  # Check completeness (street, city, state, zip)
  # Return: {tier, issues, suggestions}

def validate_headers(row, rules)
  # Map columns (fuzzy match on header names)
  # Return: {tier, issues, suggestions}

def assign_tier(issues_per_validation)
  # FAIL if any validation = FAIL
  # WARNING if any = WARNING
  # PASS if all = PASS
  # Return: PASS | WARNING | FAIL
```

**Duplicate Detection:**

```python
def find_duplicates(records, rules)
  for each record:
    1. Exact match: Check email, phone, address
    2. Fuzzy match: Check name at 70% similarity
    3. Flag if duplicate found
  Return: Duplicate records with references
```

**Tier Assignment Logic:**

```
Precedence:
  If ANY field = FAIL → Tier = FAIL
  Elif ANY field = WARNING → Tier = WARNING
  Else → Tier = PASS

Example:
  Email: PASS, Phone: WARNING, Amount: PASS
  → Overall Tier = WARNING
```

---

### 3. Web User Interface (`scripts/uploader/templates/review.html`)

**Purpose:** Operator interface for uploading CSVs and making per-record decisions.

**Key Sections:**

1. **Upload Card**
   - Drag & drop zone
   - File browser button
   - Status messages (uploading, processing, complete, error)

2. **Processing Queue**
   - List of files in review/processing/
   - Click to view file details

3. **Record Review Table**
   - One row per donation record
   - Columns: Record #, Donor Name, Email, Tier, Issues, Suggestions, Decision
   - Decision cell: Dropdown + Notes textarea + Save button

4. **Bulk Actions**
   - Approve All, Followup All, Reject All buttons
   - Allows quick decisions for similar batches

5. **Submit Controls**
   - Submit Decisions → Generate output files
   - Cancel Review → Return to upload

**Frontend Logic (JavaScript):**

```javascript
// On page load
GET /api/processing/<file>
  → Returns array of records with validation
  → Render table with dropdowns pre-populated

// On decision dropdown change
User selects "Approved"
  → Store in local JavaScript object
  → Enable [Save] button

// On [Save] button click
POST /api/processing/<file>/update
  {record_id, decision, notes}
  → Server stores in-memory
  → Show success feedback
  → Clear notes field

// On [Submit] button click
POST /api/processing/<file>/submit
  → Server processes all decisions
  → Generates output CSVs
  → Returns success
  → Show message: "Approved: X, Followup: Y, Rejected: Z"
```

**Responsive Design:**

- Mobile (< 768px): Table becomes stacked layout
- Tablet (768px-1280px): Flexible columns
- Desktop (> 1280px): Full-width table with horizontal scroll

See [UX_GUIDE.md](../UX_GUIDE.md) for complete UI/UX documentation.

---

## Configuration

### Rules File (`config/rules/rules_v2.4.json`)

```json
{
  "email_validation": {
    "format": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
    "common_typos": {
      "gmai.com": "gmail.com",
      "yaho.com": "yahoo.com",
      "hotmial.com": "hotmail.com"
    }
  },
  "invalid_phone_patterns": [
    "^0{10}$",  // All zeros
    "^1{10}$"   // All ones
  ],
  "high_dollar_threshold": 1000,
  "fuzzy_match_threshold": 0.7,
  "thresholds": {
    "name_length_min": 2,
    "name_length_max": 100,
    "address_required_fields": ["street", "city", "state", "zip"]
  }
}
```

**Key Parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `email_common_typos` | Dict | Domain typos to suggest corrections |
| `invalid_phone_patterns` | List | Regex patterns for invalid phones |
| `high_dollar_threshold` | 1000 | Amount above which to flag for review |
| `fuzzy_match_threshold` | 0.7 | Levenshtein similarity for name duplicates |
| `name_length_min` | 2 | Minimum donor name length |

---

## Testing Architecture

### Test Suite (330+ tests)

```
tests/
├── unit/ (130 tests)
│   • Validation functions (email, phone, amount, etc.)
│   • Edge cases (unicode, special chars, encoding)
│   • Tier assignment logic
│
├── integration/ (70 tests)
│   • Full processor pipeline (upload → validation → output)
│   • Decision persistence (save → resume → submit)
│   • CSV format handling (quoting, escaping, BOM)
│
└── e2e/ (80+ tests)
    • Upload workflow (drag & drop, file browser)
    • Decision workflow (select → save → submit)
    • Visual regression (screenshots at 3 viewports)
    • Form interaction (dropdown, textarea, buttons)
```

**Test Execution:**

```bash
# All tests
pytest

# Unit only
pytest -m unit

# Integration only
pytest -m integration

# E2E only
pytest -m e2e

# Visual regression
pytest tests/e2e/test_e2e_visual_regression.py

# Form interaction
pytest tests/e2e/test_e2e_form_input.py

# With coverage
pytest --cov=scripts --cov-report=html

# Specific test
pytest tests/unit/test_validation_email.py::test_email_typo_gmai
```

See [TESTING.md](../TESTING.md) and [TEST_PLAN.md](../TEST_PLAN.md) for complete testing guidance.

---

## Known Limitations & Future Work

### Current Limitations (v3.0)

1. **USA Phone Only** — Validates only US format (extensible)
2. **Fuzzy Match Fixed** — 70% similarity (currently hardcoded, configurable in rules_v2.4.json)
3. **Manual Upload** — No auto-watching of folders (intentional design for v3.0)
4. **No Learning Loop** — Operators review, but system doesn't auto-update rules (planned for v2.0 upstream validation)
5. **In-Memory Decisions** — Decisions lost if server restarts during review (persisted on submit)

### Planned Future (v2.0 Upstream)

The original v2.0 plan included:
- Pre-form validation wrapper (on nonprofit's website)
- Auto-watching of intake/new/ folder
- Learning loop with rule suggestions
- Claude AI integration for rule analysis

This feature set is documented in [PRD.md](../PRD.md) as a planned future release. Current v3.0 focuses on perfecting the downstream correction system (web UI + comprehensive testing).

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| File upload | 1-2s | Depends on network, file size |
| CSV parsing | ~0.1s per record | For 150 records: ~15s |
| Validation | ~0.05s per record | For 150 records: ~7s |
| Duplicate detection | ~0.02s per record | For 150 records: ~3s |
| **Total processing** | 2-5s | Typical 150-record batch |
| Output generation | <1s | Writing 3 CSVs |

---

## Error Handling

### Upload Errors

| Error | Response | Resolution |
|-------|----------|-----------|
| Invalid file type | 400 Bad Request | Upload .csv file |
| File too large | 413 Payload Too Large | Split into smaller batches |
| Parse error (bad CSV format) | 400 Bad Request | Check encoding (UTF-8), quoting, line endings |
| Duplicate filename | 409 Conflict | Rename file or wait (timestamp usually unique) |

### Validation Errors

| Error | Handling | Result |
|-------|----------|--------|
| Missing email | Flagged as FAIL | Must reject or followup |
| Invalid phone format | Flagged as WARNING | Suggested correction shown |
| Amount parsing error | Flagged as FAIL | Must reject or followup |
| Unknown column name | Flagged as header error | File needs correct headers |

---

## Security Considerations

### Data Protection

- **No authentication** — System runs on localhost:8000 (local network only)
- **No data sent externally** — All processing local to machine
- **UTF-8 encoding** — Safe handling of international characters
- **CSV injection protection** — Input validated before processing
- **No SQL** — File-based operations only (no database attacks)

### File Handling

- **Timestamped filenames** — Prevents overwrites
- **Atomic writes** — CSV files written completely or not at all
- **No deletion** — All files archived (never permanently deleted)
- **Permissions** — Files created with default umask (readable by user)

---

## Extending the System

### Adding a New Validation

1. Add function to `processor.py`:
   ```python
   def validate_newfield(value, rules):
       # Return: {tier: 'PASS'|'WARNING'|'FAIL', issues: [...], suggestions: [...]}
   ```

2. Add rule to `config/rules/rules_v2.4.json`:
   ```json
   "newfield_validation": { ... }
   ```

3. Add test to `tests/unit/test_validation_newfield.py`

4. Call in `app.py` processing loop

### Customizing Rules

1. Edit `config/rules/rules_v2.4.json`
2. Restart Flask app (if running)
3. Next upload uses new rules

### Adding Custom Output Columns

1. Modify output CSV generation in `app.py`
2. Add new columns in the three output CSVs
3. Update [PROCESSOR_GUIDE.md](PROCESSOR_GUIDE.md) with new column documentation

---

## Related Documentation

- **[API.md](API.md)** — Full endpoint reference
- **[DEVELOPER.md](DEVELOPER.md)** — Integration guide, testing patterns
- **[UX_GUIDE.md](../UX_GUIDE.md)** — UI/UX design patterns
- **[OPERATOR_MANUAL.md](../OPERATOR_MANUAL.md)** — User guide
- **[PROCESSOR_GUIDE.md](PROCESSOR_GUIDE.md)** — Validation rules reference
- **[TEST_PLAN.md](TEST_PLAN.md)** — Testing strategy
- **[TESTING.md](TESTING.md)** — How to run tests
- **[CHANGELOG.md](CHANGELOG.md)** — Version history

---

**Version:** 3.0  
**Last Updated:** June 1, 2026  
**Maintained By:** Nonprofit Toolkit Team
