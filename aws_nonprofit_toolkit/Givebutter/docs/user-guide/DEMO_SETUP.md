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

## Phase 1A Limitations (Current Release)

**What Works** ✅
- View import list and batch summary
- View all review queues (validation, duplicates, households, normalizations)
- View audit log (pre-populated)
- View export console with available export options
- Navigate between all 8 routes

**What's Not Yet Implemented** ⏳
- Decision persistence (clicking "Confirm", "Accept", "Reject" doesn't save decisions)
- Audit trail updates (user actions not recorded)
- Export generation (no real CSV files created)
- Export download (no files available)
- Readiness blocking logic (export always shows UI layout, not gated by decisions)

Phase 1B (database persistence) will add decision recording and export generation.

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
- Jane Smith (email typo: gmial.com)
- Carol White (missing phone) — **This is the blocker**

**Action:** Review both validation issues. *(Decisions not yet saved in Phase 1A)*

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
⏳ Decision persistence (coming in Phase 1B)
⏳ Export generation (coming in Phase 1B)
⏳ Readiness blocking logic (coming in Phase 1B)
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

## What You're Exercising (Phase 1A)

By following this demo walkthrough, you're validating:

**Service-Boundary Architecture** ✅
- 8 canonical routes now service-backed (no direct fixture access)
- Service layer hides repository implementation (fixture vs database)
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

**Phase 1B Features** (Coming Soon) ⏳
- Decision persistence and recording
- Audit trail updates for user actions
- Export generation and file creation
- Readiness blocking logic based on decisions
- Decision-based workflow gating

All demo data is isolated from production (`householder_demo.db` vs `givebutter.db`).

---

## When You're Done

1. Stop Flask app (Ctrl+C)
2. Optionally reset demo: `python scripts/reset_demo_batch.py`
3. Production database and exports remain completely untouched

Ready for actual deployment!
