# Householder v1.1 — UX Interactivity Demo Setup

**Purpose:** Interactive walkthrough of major Householder v1.1 UX workflows using synthetic donor data.

**Safety Model:** Completely isolated from production (separate database and export directory).

---

## Quick Start

### Step 1: Set Demo Environment Variables

```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

export GIVEBUTTER_DATABASE_URL="sqlite:///householder_demo.db"
export EXPORT_OUTPUT_DIR="./exports_demo"
export HOUSEHOLDER_REPOSITORY=database
```

### Step 2: Migrate and Seed Demo Database

Create the demo database with the correct schema and seed it with demo data:

```bash
source .venv/bin/activate
python scripts/migrate_demo_db.py
```

Expected output:
```
======================================================================
Householder Demo Database Migration
======================================================================

✓ Demo batch created!
======================================================================

Batch ID: demo-20260613-162339
Records: 12
Review items: 5

Export readiness: BLOCKED (Carol White missing phone)

✓ Ready for: http://localhost:8000/imports
======================================================================
```

### Step 3: Start Flask App

```bash
export FLASK_APP=scripts/uploader/app:app
flask run --host=127.0.0.1 --port=8000
```

### Step 4: Open Browser

Navigate to: **`http://localhost:8000/imports`**

---

## Phase 1B Implementation (Current Release)

**What Works** ✅
- View import list and batch summary
- View all review queues (validation, duplicates, households, normalizations)
- View audit log (pre-populated with batch creation)
- View export console with available export options
- Navigate between all 8 routes
- **Autosave field corrections** (edit and save inline)
- **Row status updates** based on corrections
- **Issue badge display** with field and reason
- **Decision recording** (validation, normalization, duplicates, households)

**What's Not Yet Implemented** ⏳
- Export generation (no real CSV files created)
- Export download (no files available to download)
- Batch approval workflow (Approve File button)
- Override logic for approving with remaining issues

Phase 2+ will add export generation and batch approval workflows.

---

## Email Validation Logic

The validation system uses a **three-tier approach** to balance accuracy with usability:

### Tier 0: Common Typo Domains (Detected First)

We check for the most common typo domains that don't match any real domain:

**Typos detected & suggested:**
- "gamil.com" → Suggests "gmail.com" ✓ (i-l swap)
- "gmial.com" → Suggests "gmail.com" ✓ (letter swap)
- "gmal.com" → Suggests "gmail.com" ✓ (missing i)
- "gmai.com" → Suggests "gmail.com" ✓ (incomplete)
- "yahooo.com" → Suggests "yahoo.com" ✓ (extra o)
- "yaho.com" → Suggests "yahoo.com" ✓ (missing o)
- "hotmial.com" → Suggests "hotmail.com" ✓ (letter swap)
- "hotmal.com" → Suggests "hotmail.com" ✓ (missing i)

When detected, the issue shows: **"Possible typo. Did you mean gmail.com?"**

### Tier 1: Recognized Domains (Strict Validation)

For the top 30 most common email providers (gmail, yahoo, outlook, hotmail, aol, icloud, mail.com, gmx, web.de, protonmail, yandex, qq, sina, and regional variants), we apply strict validation to catch typos:

**Typos detected:**
- "gmial.com" → Flagged (gmail typo)
- "gmal.com" → Flagged (gmail typo)
- "yahooo.com" → Flagged (yahoo typo)
- "hotmial.com" → Flagged (hotmail typo)

**Valid corrections:**
- "jane.smith@gmail.com" → Accepted
- "jane.smith@hotmail.com" → Accepted

### Tier 2: Unrecognized Domains (Lenient Validation)

For any domain not on our recognized list, we accept it if it has valid canonical email format (something@something.something):

**Accepted without issues:**
- "user@mycompany.com" → Corporate email
- "user@mail.cz" → Regional email provider
- "user@university.edu" → University email

### Format Validation (All Domains)

All emails must satisfy the canonical format. These are rejected:
- "@@gmail.com" → Invalid (double @)
- "@gmail.com" → Invalid (missing local part)
- "user@gmail" → Invalid (missing TLD)
- "usergmail.com" → Invalid (missing @)

---

## Guided Walkthrough

Follow this sequence to exercise all major UX flows:

### 1. Imports List

**URL:** `http://localhost:8000/imports`

**What to see:**
- List of all imports including demo batch
- Batch ID: demo-20260613-162339
- Records: 12
- Status: pending_review

**Action:** Click on the demo batch to access its dashboard.

---

### 2. Import Dashboard

**URL:** `http://localhost:8000/imports/<batch_id>/dashboard`

**What to see:**
- Batch summary: "12 records imported"
- Review queues:
  - Validation: 2 items (Jane Smith, Carol White)
  - Duplicates: 1 item
  - Households: 1 item
  - Normalizations: 1 item

**Action:** Observe the dashboard and navigate to each queue.

---

### 3. Validation Review Queue

**URL:** `http://localhost:8000/imports/<batch_id>/validation`

**What to see:**
- Table with 10 columns: Txn ID, Date, Name, Email, Phone, Amount, Address, Row Status, Issues, Actions
- Jane Smith (email typo: gmial.com) — Shows "Invalid Format" issue
- Carol White (missing phone) — Shows "Missing Required Field" issue

**Test Autosave and Issue Recalculation:**

**Test 1: Common Typo with Suggestion (gamil.com → gmail.com):**
1. Click on Jane Smith's email field (currently `jane.smith@gmial.com`)
2. Change to `jane.smith@gamil.com` (i-l swap typo)
3. Click away or press Tab
4. **Observe: Issue appears with suggestion** "Possible typo. Did you mean gmail.com?"
5. **Row Status shows "Warning"**
6. Now change to `jane.smith@gmail.com` (correct it)
7. Click away — **Issue disappears, Row Status becomes "No issues"**

**Test 2: Recognized Domain Typo (gmial.com):**
1. Change email back to `jane.smith@gmial.com` (letter swap typo)
2. Click away — **Issue appears** (recognized typo in gmail domain)
3. **Row Status shows "Invalid Format"**
4. Correct to `jane.smith@gmail.com`
5. Click away — **Issue resolves, Row Status becomes "No issues"**

**Test 3: Unrecognized Domain (Corporate Email):**
1. Change email to `jane.smith@mycompany.com`
2. Click away — **No issues appear** (unrecognized domain accepted if format valid)
3. Row Status shows "No issues"

**Test 4: Invalid Format:**
1. Change email to `jane.smith@@mycompany.com` (double @)
2. Click away — **Issue appears** (canonical format violation detected)
3. Row Status shows "Invalid Format"

**For Carol White:** Add phone number `555-0002`
- Observe: "Missing Required Field" issue disappears
- Row Status changes to "No issues"

**Action:** Test the complete autosave and issue recalculation workflow with typo suggestions. Observe:
- Common typos show helpful suggestions
- Row status updates dynamically
- Both recognized and unrecognized domains work correctly

---

### 4. Duplicate Review Queue

**URL:** `http://localhost:8000/imports/<batch_id>/duplicates`

**What to see:**
- Robert Smith and Bob Smith (same email: bob.smith@example.com, same phone: 555-0003)
- Supporting evidence shown

**Action:** Review the duplicate pair. *(Decisions not yet saved in Phase 1A)*

---

### 5. Household Review Queue

**URL:** `http://localhost:8000/imports/<batch_id>/households`

**What to see:**
- Eve Davis and Frank Davis (same phone: 555-0009)
- Evidence and confidence level shown

**Action:** Review the household suggestion. *(Decisions not yet saved in Phase 1A)*

---

### 6. Normalization Review Queue

**URL:** `http://localhost:8000/imports/<batch_id>/normalizations`

**What to see:**
- Grace Miller (phone: (555) 004-1234 → normalized to 555-0041234)
- Original and suggested values shown

**Action:** Review the normalization suggestion. *(Decisions not yet saved in Phase 1A)*

---

### 7. Audit Trail

**URL:** `http://localhost:8000/imports/<batch_id>/audit`

**What to see:**
- Pre-populated audit log entries showing batch creation
- Timestamp, reviewer, and action columns

**Action:** Review the audit trail. *(User actions not yet recorded in Phase 1A)*

---

### 8. Export Console

**URL:** `http://localhost:8000/imports/<batch_id>/exports`

**What to see:**
- 3 export card options:
  1. Reviewed Export (CSV with reviewer decisions)
  2. Household Export (household groupings)
  3. Backlog Export (unresolved suggestions)
- Staging statistics:
  - 12 staged records
  - 5 total decisions
  - 5 households
- "Generate Export Package" button

**Action:** Review the export console. *(Export generation not yet implemented in Phase 1A)*

---

## Expected State Summary

### Initial State (After Migration)

```
Batch ID: demo-20260613-162339 (or similar timestamp)
Records: 12
Review items: 5

Queue counts:
  Validation: 2 (Jane Smith, Carol White)
  Normalization: 1 (Grace Miller)
  Duplicates: 1 (Robert & Bob Smith)
  Households: 1 (Eve & Frank Davis)

Audit entries: 1 (batch created)
Export readiness: BLOCKED (Carol White missing phone)
```

### What You Can Explore

```
✅ View all 8 routes (imports, dashboard, validation, duplicates, households, normalizations, audit, exports)
✅ Review all 5 review items with supporting evidence
✅ See pre-populated audit log
✅ View export console with 3 export options
✅ Autosave field corrections (inline edits with blur trigger)
✅ Issue recalculation (issues appear/disappear based on corrected values)
✅ Row Status updates (dynamic based on effective values)
✅ Issue display with field name and reason code
⏳ Decision recording UI (validation/normalization/duplicate/household decisions)
⏳ Batch approval workflow (Approve File button)
⏳ Export generation (coming in Phase 2)
```

---

## Reset and Cleanup

### Option A: Keep Demo Data

If you want to keep the demo data and run the demo again later, just restart the app with the same environment variables.

### Option B: Reset for Next Demo

```bash
rm householder_demo.db
source .venv/bin/activate
python scripts/migrate_demo_db.py
```

This deletes the demo database and recreates it with fresh demo data.

### Option C: Nuke Demo Entirely

```bash
rm -rf householder_demo.db exports_demo
```

Then run `python scripts/migrate_demo_db.py` to recreate from scratch.

---

## Verification: Production Remains Untouched

**Demo database path:**
```bash
ls -la householder_demo.db
```
Expected: Demo file exists in current directory.

**Demo exports path:**
```bash
ls -la exports_demo
```
Expected: Demo directory exists in current directory.

**Production database (verify untouched):**
```bash
sqlite3 givebutter.db "SELECT COUNT(*) FROM import_batches WHERE id LIKE 'demo%';"
```
Expected output: `0` (no demo data in production database)

---

## Troubleshooting

### Migration Won't Run

**Error: "unable to open database file"**
- Solution: Verify you're in the correct directory and the path is accessible
- Use relative paths: `sqlite:///householder_demo.db`

**Error: "Not using demo environment"**
- Solution: Verify environment variables are set:
```bash
echo $GIVEBUTTER_DATABASE_URL
echo $EXPORT_OUTPUT_DIR
```
Both should be set to demo paths.

### Flask Won't Start

**Error: "Address already in use"**
- Solution: Kill existing Flask process
```bash
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```
Then restart Flask.

### App Shows Wrong Data

**Error: Seeing fixture data instead of demo data**
- Solution: Verify `HOUSEHOLDER_REPOSITORY=database` is set
```bash
echo $HOUSEHOLDER_REPOSITORY
```
Must be set to "database".

### Demo Database Corrupted

**Solution:** Delete and remigrate
```bash
rm householder_demo.db
python scripts/migrate_demo_db.py
```

---

## Safety Guarantees

✓ **Demo uses isolated database:** `householder_demo.db` (never touches `givebutter.db`)  
✓ **Demo uses isolated exports:** `exports_demo/` (never touches `exports/`)  
✓ **Scripts verify demo paths before running**  
✓ **Reset script only deletes demo data**  
✓ **Production data always protected**

---

## What You're Exercising (Phase 1B)

By following this demo walkthrough, you're validating:

**Service-Boundary Architecture** ✅
- 8 canonical routes now service-backed with database backend
- Service layer handles fixture vs database repository selection
- View models provide immutable contracts between services and templates
- Templates unchanged from Phase 0 (UI preserved exactly)

**Data Viewing & Navigation** ✅
1. Import listing and batch discovery
2. Dashboard with queue summaries
3. All 5 review items properly categorized
4. Duplicate detection with supporting evidence
5. Household detection with confidence levels
6. Normalization suggestions with original/suggested values
7. Audit log display
8. Export console with available export options

**Autosave & Field Corrections** ✅
- Edit inline fields (Date, Name, Email, Phone, Amount, Address)
- Click away to trigger autosave
- "Saving..." → "Saved" feedback
- Issue badges disappear when fixed
- Row status updates automatically

**Decision Recording** ✅
- Validation decisions (Accept Issue, Dismiss, Defer)
- Normalization decisions
- Duplicate decisions
- Household decisions

**Phase 2+ Features** (Coming Soon) ⏳
- Export generation and file creation
- Batch approval workflow (Approve File)
- Override logic for remaining issues
- Export download capability

All demo data is isolated from production (`householder_demo.db` vs `givebutter.db`).

---

## When You're Done

1. Stop Flask app (Ctrl+C)
2. Optionally reset demo: `python scripts/reset_demo_batch.py`
3. Production database and exports remain completely untouched

Ready for actual deployment!
