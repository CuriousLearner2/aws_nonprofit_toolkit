# Householder v1.1 — UX Interactivity Demo Plan

**Version:** 1.1  
**Status:** Planning (Implementation Pending Approval)  
**Date:** 2026-06-13  
**Purpose:** Enable operator/user to review Householder v1.1 UX flows interactively using synthetic demo data

---

## Executive Summary

This document outlines a plan to create a safe, interactive UX review environment for Householder v1.1 using a small synthetic dataset. The demo allows operators and stakeholders to click through major workflows without requiring real donor data or creating production database pollution.

**Recommended Approach:** Seeded SQLite demo batch (Option B) with clearly labeled demo data and safe reset/cleanup procedures.

---

## Section 1: Purpose

The UX demo serves these goals:

1. **Stakeholder Review:** Allow non-technical stakeholders to see the product in action
2. **Support Training:** Help support team learn workflows before go-live
3. **UX Validation:** Verify that UX flows match designed behavior
4. **Operator Confidence:** Show operator what the tool looks and feels like
5. **Bug Discovery:** Identify any remaining UX issues before production
6. **Documentation Validation:** Confirm that user guides match actual screens

**Out of scope:**
- Production testing (use full test suite for that)
- Performance benchmarking (use real data for that)
- Security testing (use dedicated security reviews for that)
- Large-scale data handling (demo is intentionally small)

---

## Section 2: Recommended Demo Approach — Option B+ (Isolated Demo SQLite)

### Choice: Isolated Demo SQLite Database + Separate Export Directory

**Approach:**
1. Create a separate demo SQLite database file: `householder_demo.db`
2. Create a separate demo exports directory: `exports_demo/`
3. Demo mode uses these isolated locations by default via environment variables
4. Create a Python script that seeds demo import batch into the isolated database
5. Includes a small set of synthetic records (10-12 fake donors)
6. Generates expected review issues (duplicates, validation problems, households, etc.)
7. Operator can interactively make decisions and generate exports
8. Cleanup: Delete demo batch and demo database (optional), or reset demo database
9. **Zero risk of production database/exports pollution**

### Default Environment Variables for Demo Mode

```bash
# Demo mode (completely isolated)
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"

# Production mode (default)
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
```

### Why This Approach (Revised)

**Pros:**
- ✓ Exercises all real workflows (routes, persistence, decisions, audit trail, export generation)
- ✓ Closest to actual operator experience
- ✓ Best for UX validation (real app behavior, not mocked)
- ✓ Shows actual export file generation and download
- ✓ Demonstrates audit trail functionality
- ✓ **ZERO risk of production data pollution** (separate database and exports)
- ✓ Completely safe (demo is isolated by default)
- ✓ Easy reset (delete demo database or single reset command)
- ✓ Operator can use production database if they explicitly choose (with flag)

**No Cons:**
- Demo database file is separate but minimal (~50-100 KB)
- Demo exports directory is separate but expected
- Both are clearly labeled "demo" for identification

**Comparison to Alternatives:**

| Aspect | Option A (Fixture) | Option B (Seeded to Prod) | **Option B+ (Isolated Demo DB)** |
|--------|-------------------|---------------------------|----------------------------------|
| Exercises real routes | ✗ Limited | ✓ Full | ✓ Full |
| Exercises persistence | ✗ No | ✓ Yes | ✓ Yes |
| Exercises audit trail | ✗ No | ✓ Yes | ✓ Yes |
| Exercises export | ✗ Limited | ✓ Yes | ✓ Yes |
| Setup complexity | ✓ Low | ◐ Medium | ◐ Medium |
| Production DB pollution | ✓ No | ◐ Mitigated | ✓ **Impossible** |
| Production export pollution | ✓ No | ✓ No | ✓ No |
| UX validation quality | ✗ Low | ✓ High | ✓ High |
| Reset/cleanup ease | ✓ Simple | ✓ Simple | ✓ Simple |
| **Safety** | ✓ Inherent | ◐ Depends on cleanup | ✓ **Maximum** |

**Recommendation:** **Option B+ (Isolated Demo SQLite Database)** provides maximum safety with no compromise on UX fidelity. Production data is completely protected by design.

---

## Section 3: Synthetic Demo Data Design

### Demo Dataset: 12 Synthetic Donor Records

**Objectives:** Trigger all major review workflows and decision types while keeping data realistic and fake.

**Dataset:**

```csv
First Name,Last Name,Email,Phone,Amount,Date,Transaction ID
John,Doe,john.doe@gmail.com,555-0001,100.00,2024-01-01,TX001
Jane,Smith,jane.smith@gmial.com,555-0002,250.00,2024-01-02,TX002
Robert,Smith,bob.smith@example.com,555-0003,150.00,2024-01-03,TX003
Bob,Smith,bob.smith@example.com,555-0003,300.00,2024-01-04,TX004
Carol,White,carol.white@example.com,,500.00,2024-01-05,TX005
David,Brown,david.brown@yahoo.com,555-0007,75.00,2024-01-06,TX006
Eve,Davis,eve@example.com,555-0008,200.00,2024-01-07,TX007
Frank,Davis,frank@example.com,555-0009,125.00,2024-01-08,TX008
Grace,Miller,grace.miller@example.com,(555) 004-1234,80.00,2024-01-09,TX009
Henry,Wilson,henry@example.com,555-0011,180.00,2024-01-10,TX010
Iris,Moore,iris.moore@example.com,555-0012,220.00,2024-01-11,TX011
Jack,Green,jack.green@example.com,555-0013,95.00,2024-01-12,TX012
```

### Expected Validation/Normalization/Duplicate/Household Issues

| Record | Issue Type | Scenario | Status |
|--------|-----------|----------|--------|
| John Doe | None | Clean, valid record | ✓ OK |
| Jane Smith | Validation | Email typo: gmial.com (misspelled Gmail) | ⚠️ Flagged |
| Robert Smith | Duplicate | Same email & phone as Bob Smith (record #4) | ◐ Suggested |
| Bob Smith | Duplicate | Same email & phone as Robert Smith (record #3) | ◐ Suggested |
| Carol White | Validation | Missing phone number (required field) | ✓ **BLOCKS EXPORT** |
| David Brown | None | Clean, valid record | ✓ OK |
| Eve Davis | Household | Same address/phone as Frank (household match) | ◐ Suggested |
| Frank Davis | Household | Same address/phone as Eve (household match) | ◐ Suggested |
| Grace Miller | Normalization | Phone format: (555) 004-1234 (can be normalized) | ◐ Formatting |
| Henry Wilson | Validation | Email incomplete: henry@example.com (missing name) | ⚠️ Warning |
| Iris Moore | None | Clean, valid record | ✓ OK |
| Jack Green | None | Clean, valid record | ✓ OK |

### Expected Issue Counts

After seeding this batch:

| Queue | Count | Notes |
|-------|-------|-------|
| Validation | 2 | Jane Smith (typo), Carol White (missing phone) |
| Normalization | 1 | Grace Miller (phone formatting) |
| Duplicates | 2 | Robert + Bob Smith (same email/phone) |
| Households | 2 | Eve + Frank Davis (same household) |
| **Total Issues** | **7** | Enough for meaningful demo walkthrough |
| **Blocked (Carol White)** | **1** | Prevents export until resolved |

### Readiness Path

**Initial state:** Export blocked (1 unresolved blocker: Carol White missing phone)

**After decisions:**
1. Resolve Carol White (missing phone) → adds decision to audit log
2. Resolve Jane Smith (email typo) → validates or flags
3. Resolve Robert/Bob duplicate → mark as "different person" or "same person"
4. Resolve Grace Miller (phone format) → accept normalization
5. Resolve Eve/Frank household → confirm or reject
6. Resolve Henry Wilson (email warning) → proceed

**Export-ready state:** All required decisions made, export can be generated

---

## Section 4: Major Screens Covered

The demo exercises these 13 major UX flows:

### 1. Upload / Import Queue
**Screen:** `/upload`
- [ ] User clicks "Choose File"
- [ ] Selects synthetic CSV (or it's pre-selected)
- [ ] Clicks "Upload"
- [ ] Sees "Importing..." message
- [ ] Receives batch ID and record count

**Expected:** "12 records imported, 7 issues detected"

---

### 2. Import Dashboard Summary
**Screen:** `/dashboard` (home)
- [ ] Shows batch summary
- [ ] Lists review queues (Validation: 2, Normalization: 1, Duplicates: 2, Households: 2)
- [ ] Shows "Export Blocked" status (due to Carol White)

---

### 3. Validation Review Queue
**Screen:** `/validation` (or navigation to validation tab)
- [ ] Shows Jane Smith (email typo)
- [ ] Shows Carol White (missing phone) — **BLOCKER**
- [ ] Reviewer can:
  - [ ] Click "Accept" (agree with data as-is)
  - [ ] Click "Reject" (flag as invalid)
  - [ ] See decision options
  - [ ] Save decision
- [ ] Decision appears in audit log

**Demo action:** Reviewer marks Carol White as "Reject" to unblock export

---

### 4. Normalization Review Queue
**Screen:** `/normalizations`
- [ ] Shows Grace Miller (phone format: (555) 004-1234)
- [ ] Suggests normalized format (555-0041234 or similar)
- [ ] Reviewer can:
  - [ ] Click "Accept" (use normalized version)
  - [ ] Click "Reject" (keep original)
  - [ ] Save decision

**Demo action:** Reviewer accepts normalization

---

### 5. Duplicate Review Queue
**Screen:** `/duplicates`
- [ ] Shows Robert Smith and Bob Smith
- [ ] Both have same email (bob.smith@example.com) and phone (555-0003)
- [ ] Reviewer can:
  - [ ] Click "Same Person" (merge metadata)
  - [ ] Click "Different Person" (keep separate)
  - [ ] Click "Defer" (skip for now)
  - [ ] Save decision

**Demo action:** Reviewer marks as "Different Person"

---

### 6. Household Review Queue
**Screen:** `/households`
- [ ] Shows Eve Davis and Frank Davis
- [ ] Same household address (inferred from same phone or explicit address field)
- [ ] Reviewer can:
  - [ ] Click "Confirm" (agree they're same household)
  - [ ] Click "Reject" (they're different households)
  - [ ] Click "Defer"
  - [ ] Save decision

**Demo action:** Reviewer confirms household

---

### 7. Readiness Dashboard (Export Blocked State)
**Screen:** `/readiness`
**Before decisions:**
- [ ] Shows batch summary (12 records)
- [ ] Shows queue status:
  - ⚠️ Validation: 2 items (1 BLOCKER: Carol White)
  - ⚠️ Normalization: 1 item
  - ⚠️ Duplicates: 2 items
  - ⚠️ Households: 2 items
- [ ] Shows "Export Blocked" message
- [ ] Lists what's blocking: "Carol White missing phone (validation issue)"
- [ ] "Generate Export" button is disabled (greyed out)

---

### 8. Readiness Dashboard (Export Ready State)
**Screen:** `/readiness`
**After decisions:**
- [ ] Shows all queues resolved (or deferred)
- [ ] Shows "Ready to Export" (green)
- [ ] "Generate Export" button is enabled (clickable)

---

### 9. Export Preview
**Screen:** `/exports` or preview endpoint
- [ ] Shows preview of export CSV
- [ ] Displays columns: First Name, Last Name, Email, Phone, Amount, Date, Transaction ID
- [ ] Shows 12 rows (one per record, including Carol White with resolved phone/decision)

---

### 10. Export Generation
**Action:** Click "Generate Export"
- [ ] Export processing message appears
- [ ] Waits 5-10 seconds for generation
- [ ] Success: "Export created: householder-export-<batch-id>-<state>-<timestamp>.csv"

**Expected:** File written to `EXPORT_OUTPUT_DIR`

---

### 11. Recent Exports List
**Screen:** `/exports`
- [ ] Shows list of exports for this batch
- [ ] Shows filename, size, creation date/time
- [ ] Shows "Download" link for each

---

### 12. Export Download
**Action:** Click "Download" on export file
- [ ] File downloads to user's machine
- [ ] Filename: householder-export-<batch-id>-<state>-<timestamp>.csv

**Expected:** Valid CSV with 12 data rows + 1 header row

---

### 13. Audit Trail
**Screen:** `/audit`
- [ ] Shows log of all actions:
  - `import_batch_created` — when demo batch seeded
  - `decision_made` — for each decision reviewer made (Carol White, Grace Miller, Robert/Bob, Eve/Frank)
  - `export_generated` — when export button clicked
  - (optionally) `export_downloaded` — when user downloaded

**Expected:** 5+ audit entries documenting the full workflow

---

## Section 5: Demo Data Seeding Implementation (Isolated)

### Seeding Approach

Create a script at:
```
scripts/seed_demo_batch.py
```

**Script does:**
1. Checks GIVEBUTTER_DATABASE_URL and EXPORT_OUTPUT_DIR environment variables
2. Verifies they point to demo locations (householder_demo.db and exports_demo)
3. Creates demo database if it doesn't exist (with correct schema)
4. Creates demo exports directory if it doesn't exist
5. Imports synthetic CSV data (from inline or file)
6. Creates import batch with label "DEMO" (easily identifiable)
7. Creates raw_import_rows (immutable source records)
8. Creates import_contacts and review_items (with expected issues)
9. Prints batch ID and record count
10. Confirms demo database and export directory are ready

**Script location:** `scripts/seed_demo_batch.py`

**Invocation (with demo database):**
```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

# Set demo environment variables
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"

# Run seeding script
python scripts/seed_demo_batch.py
```

**Output:**
```
Demo setup check...
Database: householder_demo.db ✓
Export dir: exports_demo ✓

Demo batch created successfully!
Batch ID: demo-001-[timestamp]
Records: 12
Expected issues: 7 (2 validation, 1 normalization, 2 duplicates, 2 households)
Database: /Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db
Export directory: /Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo
Ready for UX review at: http://localhost:8000/dashboard
```

**Safety Check (built into script):**
```python
# Script includes safety check to prevent accidental seeding into production
if "demo" not in db_path.lower() or "demo" not in export_path.lower():
    print("ERROR: Not seeding into production database!")
    print("Use demo environment variables to seed into isolated demo location")
    sys.exit(1)
```

**Override Flag (for operator who intentionally wants to seed into production):**
```bash
# Explicitly override safety check (not recommended)
python scripts/seed_demo_batch.py --production-override
# This would seed into givebutter.db (if GIVEBUTTER_DATABASE_URL points there)
# But default behavior is demo-only
```

---

## Section 6: Reset / Cleanup Instructions (Demo-Isolated)

### Reset Script

Create a script at:
```
scripts/reset_demo_batch.py
```

**Script does:**
1. Checks GIVEBUTTER_DATABASE_URL and EXPORT_OUTPUT_DIR point to demo locations
2. Finds all demo batches by label "DEMO" in demo database
3. Deletes import_batches entries
4. Deletes related raw_import_rows, import_contacts, review_items entries
5. Deletes related audit_log entries
6. Deletes all export files from `exports_demo/` directory
7. Confirms cleanup complete (demo database is reset, can be reseeded)

**Invocation (with demo environment variables):**
```bash
# Set demo environment variables
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"

# Run reset script
python scripts/reset_demo_batch.py
```

**Output:**
```
Demo cleanup check...
Database: householder_demo.db ✓
Export dir: exports_demo ✓

Demo batch cleanup complete!
Deleted from demo database: 1 batch, 12 records, 7 review items
Deleted from exports_demo: 1 export file
Demo database is clean. Ready for next demo seeding.
```

### Safety Check (built into script)

```python
# Script includes safety check to prevent accidental cleanup of production
if "demo" not in db_path.lower() or "demo" not in export_path.lower():
    print("ERROR: Not resetting production database!")
    print("Use demo environment variables to reset isolated demo location")
    sys.exit(1)
```

### Option: Complete Demo Database Reset

**Delete entire demo database (nuclear option):**
```bash
rm /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db
rm -rf /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo
```

Then run seed script again to recreate with fresh schema and demo data.

### Manual Cleanup (if needed)

```bash
# Reset demo database without script
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"

# Find demo batch ID
sqlite3 "$GIVEBUTTER_DATABASE_URL" "SELECT batch_id FROM import_batches WHERE batch_name LIKE 'DEMO%';"

# Delete batch
sqlite3 "$GIVEBUTTER_DATABASE_URL" "DELETE FROM import_batches WHERE batch_name LIKE 'DEMO%';"

# Delete related records
sqlite3 "$GIVEBUTTER_DATABASE_URL" "DELETE FROM raw_import_rows WHERE batch_id = '<batch-id>';"
sqlite3 "$GIVEBUTTER_DATABASE_URL" "DELETE FROM import_contacts WHERE batch_id = '<batch-id>';"
sqlite3 "$GIVEBUTTER_DATABASE_URL" "DELETE FROM review_items WHERE batch_id = '<batch-id>';"
sqlite3 "$GIVEBUTTER_DATABASE_URL" "DELETE FROM audit_log WHERE batch_id = '<batch-id>';"

# Delete demo export files
rm /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo/householder-export-<batch-id>*
```

---

## Section 7: How to Avoid Real Donor Data

### Safeguards (Demo Isolation by Design)

**Isolated database:**
- [ ] Demo uses separate SQLite file: `householder_demo.db` (not `givebutter.db`)
- [ ] Production database is completely separate and untouched
- [ ] No risk of demo data in production

**Isolated exports:**
- [ ] Demo exports go to: `exports_demo/` (not `exports/`)
- [ ] Production exports directory is completely separate
- [ ] No demo files in production exports

**Data source:**
- [ ] Use only hardcoded synthetic names/emails/phones in `seed_demo_batch.py`
- [ ] Never read from real Givebutter export or CRM
- [ ] Never import real donor CSV

**Safety checks:**
- [ ] Seeding script verifies it's using demo database (refuses to seed to production)
- [ ] Reset script verifies it's using demo database (refuses to reset production)
- [ ] Default behavior is completely safe

**Verification:**
```bash
# Confirm demo database is separate
ls -la /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db
# Should exist, separate from givebutter.db

# Confirm demo exports directory is separate
ls -la /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo
# Should exist, separate from exports/

# Confirm production database is untouched
sqlite3 /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db "SELECT COUNT(*) FROM import_batches WHERE batch_name LIKE 'DEMO%';"
# Should return: 0 (no demo batches in production)
```

---

## Section 8: Export Generation in Demo (Isolated)

### Question: Should demo export files be created?

**Answer: YES, completely safe with isolated directory**

**Rationale:**
- Demonstrates complete workflow (upload → review → export → download)
- Tests export file generation and download
- Validates that export CSV is correct format
- Allows stakeholder to see what the final deliverable looks like

**Complete Isolation (Zero Risk):**
1. Export files go to isolated `exports_demo/` directory (not production `exports/`)
2. Export files are clearly labeled with "DEMO" batch ID: `householder-export-demo-001-<timestamp>.csv`
3. Reset script cleans up demo export files
4. Export files are never shared with Givebutter/CRM (export-only model, manual upload)
5. **Production exports directory is completely separate and untouched**

**No Risk:**
- Export files are in isolated demo directory
- No automatic sync or writeback (by design)
- Operator manually controls CRM upload
- Demo export files cannot interfere with production
- Easy to delete entire `exports_demo/` directory if needed

---

## Section 9: How to Verify No External API Calls

### Verification Procedure

**During demo, monitor for external API calls:**

```bash
# Method 1: Network monitoring
# In another terminal, monitor outbound connections
lsof -i -P -n | grep python | grep ESTABLISHED | grep -v 127.0.0.1 | grep -v localhost

# Should return: EMPTY (no external connections)
```

```bash
# Method 2: Log monitoring
# Watch Flask logs for API key, credential, or external service references
tail -f /path/to/householder.log | grep -i "api\|givebutter\|crm\|external\|credential\|key"

# Should return: NOTHING (no references)
```

```bash
# Method 3: Code inspection (already done in testing)
grep -r "requests\|urllib\|http" givebutter_app/services/*.py | grep -i "givebutter\|crm\|external"

# Should return: EMPTY (no external calls in code)
```

---

## Section 10: How to Verify No Source-Data Mutation

### Verification Procedure

**Verify that demo batch data is never modified:**

```bash
# Query 1: Check that raw_import_rows are immutable
# Get the demo batch ID
BATCH_ID=$(sqlite3 givebutter.db "SELECT batch_id FROM import_batches WHERE batch_name LIKE 'DEMO%' LIMIT 1;")

# Count raw_import_rows before decisions
COUNT_BEFORE=$(sqlite3 givebutter.db "SELECT COUNT(*) FROM raw_import_rows WHERE batch_id = '$BATCH_ID';")

# Make some decisions in the UI
# (reviewer makes decisions on duplicates, validations, etc.)

# Count raw_import_rows after decisions
COUNT_AFTER=$(sqlite3 givebutter.db "SELECT COUNT(*) FROM raw_import_rows WHERE batch_id = '$BATCH_ID';")

# Verify counts are identical
[ "$COUNT_BEFORE" = "$COUNT_AFTER" ] && echo "✓ raw_import_rows unchanged" || echo "✗ raw_import_rows MUTATED"
```

```bash
# Query 2: Verify audit_log only has INSERT (no UPDATE/DELETE on raw data)
sqlite3 givebutter.db << 'EOF'
SELECT action_type FROM audit_log 
WHERE batch_id = '$BATCH_ID' 
AND action_type NOT IN ('import_batch_created', 'decision_made', 'export_generated', 'export_downloaded');

# Should return: EMPTY (only expected action types)
EOF
```

```bash
# Query 3: Verify no UPDATE statements in audit
sqlite3 givebutter.db "SELECT COUNT(*) FROM audit_log WHERE action_type LIKE '%UPDATE%' OR action_type LIKE '%DELETE%';"

# Should return: 0
```

---

## Section 11: Demo Usage Example (Complete Isolation)

**How to run demo (completely isolated from production):**

```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

# 1. Set demo environment variables (CRITICAL - isolates from production)
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"

# 2. Start Flask app (with demo database/exports)
flask run --port=8000

# 3. In another terminal, seed demo batch (in the isolated demo database)
# Make sure to set the same demo environment variables!
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"
python scripts/seed_demo_batch.py
# Output: Demo batch created in householder_demo.db

# 4. Open browser to http://localhost:8000/dashboard
# See: "12 records imported, 7 issues detected, Export Blocked"
# Note: This is using the isolated demo database, NOT production

# 5. Click through review queues
# Make decisions on each issue (or skip with "Defer")

# 6. Go to /readiness
# See: "Ready to Export" (green)

# 7. Click "Generate Export"
# See: Export file created in exports_demo/ (NOT in production exports/)

# 8. Go to /exports
# Download the export CSV from exports_demo/

# 9. When done, reset demo database
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"
python scripts/reset_demo_batch.py
# Output: Demo cleanup complete

# 10. Verify production database remains completely untouched
ls -la givebutter.db        # Should be unchanged
ls -la exports/            # Should be unchanged - demo exports are in exports_demo/
sqlite3 givebutter.db "SELECT COUNT(*) FROM import_batches WHERE batch_name LIKE 'DEMO%';"
# Output: 0 (no demo batches in production)
```

---

## Section 12: Acceptance Criteria

### Demo is ready for use if:

**Setup & Data:**
- [ ] Synthetic CSV data created (12 records, 7 expected issues)
- [ ] Seeding script creates demo batch without errors in demo database
- [ ] Reset script deletes demo batch completely from demo database
- [ ] Production database (givebutter.db) remains completely untouched
- [ ] Production exports directory remains completely untouched

**Screens & Navigation:**
- [ ] All 13 major screens are accessible and render
- [ ] Dashboard shows correct queue counts (Validation: 2, Normalization: 1, Duplicates: 2, Households: 2)
- [ ] Readiness shows "Blocked" initially (Carol White missing phone)
- [ ] Readiness shows "Ready" after decisions made

**Decisions & Audit:**
- [ ] Reviewer can make decisions in each queue
- [ ] Decisions are saved and persist after page reload
- [ ] Audit trail records all decisions
- [ ] Audit trail is complete and accurate

**Export Workflow:**
- [ ] Export is blocked initially (Carol White issue)
- [ ] Export becomes available after decisions
- [ ] Export file is generated in `exports_demo/` (isolated, not production)
- [ ] Export file is valid CSV with 12 data rows + header
- [ ] Export file can be downloaded from browser
- [ ] Export file is listed in `/exports` screen
- [ ] Production `exports/` directory is completely untouched

**Safety:**
- [ ] No real donor data in database
- [ ] No external API calls detected
- [ ] No source-data mutations detected
- [ ] Demo batch is easy to reset (script provided)
- [ ] All demo exports are in standard exports/ directory
- [ ] Test suite still passes (1202 tests)

---

## Section 13: Guardrail Confirmation

All 15 hard guardrails remain in place during demo:

✓ **No CRM/Givebutter API calls** — Demo uses synthetic data only, no external calls  
✓ **No credentials storage** — No credentials in demo scripts  
✓ **No writeback routes** — Export-only model maintained  
✓ **No auth/RBAC changes** — Demo uses standard deployment mode  
✓ **No bulk actions** — Individual decisions required  
✓ **No background jobs** — All operations synchronous  
✓ **No new export formats** — CSV only  
✓ **No source-data mutations** — raw_import_rows immutable  
✓ **No contact mutations** — Decisions create metadata only  
✓ **No contact merge** — Not implemented  
✓ **No contact deletion** — Not implemented  
✓ **No household_id assignment** — Not implemented  
✓ **No schema changes** — No database changes  
✓ **No cross-import matching** — Per-batch only  
✓ **No master contacts/households** — Not implemented  

---

## Section 13: Implementation Plan (When Approved)

**If plan is accepted, implementation will create isolated demo environment:**

1. Create `scripts/seed_demo_batch.py` (150-200 lines)
   - Verifies GIVEBUTTER_DATABASE_URL points to `householder_demo.db` (safety check)
   - Verifies EXPORT_OUTPUT_DIR points to `exports_demo/` (safety check)
   - Creates demo database if doesn't exist
   - Creates demo exports directory if doesn't exist
   - Reads synthetic data (hardcoded)
   - Creates import batch with "DEMO" label
   - Seeds raw_import_rows, import_contacts, review_items
   - Prints confirmation with batch ID and paths
   - Refuses to seed into production database

2. Create `scripts/reset_demo_batch.py` (100-150 lines)
   - Verifies using demo database and exports (safety check)
   - Finds demo batches by label in demo database
   - Deletes all related records safely
   - Deletes demo export files from `exports_demo/`
   - Prints confirmation
   - Refuses to reset production database

3. Create demo database and export directories (on first seed)
   - `householder_demo.db` — created automatically by seed script
   - `exports_demo/` — created automatically by seed script
   - Both are .gitignored to prevent committing demo data

4. Create `docs/user-guide/DEMO_SETUP.md` (2-3 pages)
   - Complete walkthrough: setting env vars, seeding, using, resetting
   - Screenshot placeholders for major screens
   - Expected issue counts and workflows
   - Safety verification steps

5. Update `CLAUDE.md` (if needed)
   - Add note about demo mode
   - Point to demo setup instructions
   - Clarify that demo uses isolated database

6. Run full test suite to verify no regressions
   - All 1202 tests must pass
   - Verify production code is unchanged

**No changes to:**
- Production code (routes, services, models)
- Database schema (demo uses same schema in separate file)
- Core business logic
- 15 hard guardrails
- Production data or exports

**Safety by Design:**
- Demo database is completely separate (`householder_demo.db` not `givebutter.db`)
- Demo exports are completely separate (`exports_demo/` not `exports/`)
- Default behavior cannot accidentally touch production
- Scripts verify demo locations and refuse to run on production

---

## Section 15: Sign-Off

**UX Interactivity Demo Plan (Revised with Isolation): COMPLETE & READY FOR APPROVAL**

- [x] Purpose documented (stakeholder review, support training, UX validation)
- [x] Recommended approach chosen: Option B (Seeded SQLite Demo Batch)
- [x] Synthetic demo data designed (12 records, 7 expected issues)
- [x] All 13 major screens covered
- [x] Major UX flows documented with expected outcomes
- [x] Seeding script approach defined (seed_demo_batch.py)
- [x] Reset/cleanup approach defined (reset_demo_batch.py)
- [x] Safeguards documented (no real data, easy reset, labeled demo)
- [x] Verification procedures provided (no external calls, no mutations)
- [x] Export generation approach clarified (allowed, safe, labeled)
- [x] Acceptance criteria defined (16 items)
- [x] All 15 hard guardrails confirmed
- [x] Implementation plan outlined (pending approval)

---

## References

- `docs/operatinalizing/V1_1_OPERATOR_TASK7_DEPLOYMENT_DAY_RUNBOOK.md` — Deployment and testing
- `docs/user-guide/EXPORT_ONLY_WORKFLOW.md` — User-facing workflow documentation
- `docs/user-guide/REVIEWER_WORKFLOW.md` — Reviewer decision guide
