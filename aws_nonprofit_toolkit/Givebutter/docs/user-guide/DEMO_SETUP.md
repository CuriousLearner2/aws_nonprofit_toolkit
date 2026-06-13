# Householder v1.1 — UX Interactivity Demo Setup

**Purpose:** Interactive walkthrough of major Householder v1.1 UX workflows using synthetic donor data.

**Safety Model:** Completely isolated from production (separate database and export directory).

---

## Quick Start

### Step 1: Set Demo Environment Variables

```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"

export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"
```

### Step 2: Seed Demo Data (Optional Reset)

If you've run the demo before and want to start fresh:

```bash
python scripts/reset_demo_batch.py
```

Then seed the demo:

```bash
python scripts/seed_demo_batch.py
```

Expected output:
```
✓ Demo batch created successfully!
Batch ID: demo-20260613-143000
Records: 12
Review items: 5 (7 expected issues)
...
✓ Ready for UX review at: http://localhost:8000/dashboard
```

### Step 3: Start Flask App

```bash
flask run --host=127.0.0.1 --port=8000
```

### Step 4: Open Browser

Navigate to: **`http://localhost:8000/dashboard`**

---

## Guided Walkthrough

Follow this sequence to exercise all major UX flows:

### 1. Import Dashboard

**URL:** `http://localhost:8000/dashboard`

**What to see:**
- Batch summary: "12 records imported, 5 review items detected"
- Export status: **"BLOCKED"** (Carol White missing phone)
- Review queues list:
  - Validation: 2 items
  - Normalization: 1 item
  - Duplicates: 1 item
  - Households: 1 item

**Action:** Observe the dashboard and queue counts.

---

### 2. Validation Review Queue

**URL:** `http://localhost:8000/validation`

**What to see:**
- Jane Smith (email typo: gmial.com)
- Carol White (missing phone) — **This is the blocker**

**Action:** 
1. Review Carol White (missing phone)
2. Click "Reject" or "Flag" to mark it as blocked
3. Click "Save Decision"
4. Check audit trail (should show decision recorded)

**Expected outcome:** Decision saved, audit log updated.

---

### 3. Duplicate Review Queue

**URL:** `http://localhost:8000/duplicates`

**What to see:**
- Robert Smith and Bob Smith (same email: bob.smith@example.com, same phone: 555-0003)

**Action:**
1. Review the duplicate pair
2. Click "Different Person" (or "Same Person" — both are valid)
3. Click "Save Decision"

**Expected outcome:** Decision saved, appears in audit log.

---

### 4. Household Review Queue

**URL:** `http://localhost:8000/households`

**What to see:**
- Eve Davis and Frank Davis (same phone: 555-0009)

**Action:**
1. Review the household pair
2. Click "Confirm" (or "Reject" — both are valid)
3. Click "Save Decision"

**Expected outcome:** Decision saved, appears in audit log.

---

### 5. Normalization Review Queue

**URL:** `http://localhost:8000/normalizations`

**What to see:**
- Grace Miller (phone: (555) 004-1234 → can be normalized to 555-0041234)

**Action:**
1. Review the normalization suggestion
2. Click "Accept" to use normalized version
3. Click "Save Decision"

**Expected outcome:** Decision saved, appears in audit log.

---

### 6. Readiness Dashboard — Blocked State

**URL:** `http://localhost:8000/readiness`

**Before resolving Carol White:**
- Status: **"Export BLOCKED"** (red)
- Blocker shown: "Carol White: missing phone (validation error)"
- "Generate Export" button: **Disabled** (greyed out)

**Action:** Observe the blocked state and blocker message.

---

### 7. Resolve the Blocker

**Back to Validation:** `http://localhost:8000/validation`

1. Resolve Carol White (missing phone)
   - Click "Reject" or "Accept" (marks decision as made)
   - Click "Save Decision"

2. Back to Readiness: `http://localhost:8000/readiness`

**Expected outcome:** Status changes to **"Ready to Export"** (green), "Generate Export" button enabled.

---

### 8. Readiness Dashboard — Ready State

**URL:** `http://localhost:8000/readiness`

**After resolving all blockers:**
- Status: **"Ready to Export"** (green)
- All queues show: "✓ Resolved"
- "Generate Export" button: **Enabled** (clickable)

**Action:** Observe the ready state.

---

### 9. Export Preview

**URL:** `http://localhost:8000/exports` (or preview endpoint)

**What to see:**
- Preview of export CSV
- Columns: First Name, Last Name, Email, Phone, Amount, Date, Transaction ID
- 12 rows of data (including Carol White with resolved issues)

**Action:** Review the export preview to verify data looks correct.

---

### 10. Export Generation

**On Readiness Dashboard:** Click **"Generate Export"**

**What to see:**
- Processing message: "Generating export..."
- Success message: "Export created: householder-export-demo-[timestamp].csv"
- File appears in exports_demo/ directory

**Expected outcome:** Export file created, can be downloaded.

---

### 11. Recent Exports / Download

**URL:** `http://localhost:8000/exports`

**What to see:**
- List of export files
- Filename: householder-export-demo-[timestamp].csv
- Size and timestamp
- "Download" link

**Action:** Click "Download" to download the export CSV.

**Expected outcome:** File downloads to your machine (check Downloads folder).

---

### 12. Audit Trail

**URL:** `http://localhost:8000/audit`

**What to see:**
- Log entries for:
  - `import_batch_created` (when demo batch was seeded)
  - `decision_made` (for each decision you made: Carol White, Robert/Bob, Eve/Frank, Grace, Jane)
  - `export_generated` (when export was created)
  - (optionally) `export_downloaded` (when file was downloaded)

**Expected outcome:** All actions logged with timestamps.

---

## Expected State Summary

### Initial State (After Seed)

```
Batch ID: demo-20260613-143000
Records: 12
Review items: 5

Queue counts:
  Validation: 2 (Jane Smith, Carol White)
  Normalization: 1 (Grace Miller)
  Duplicates: 1 (Robert & Bob Smith)
  Households: 1 (Eve & Frank Davis)

Export readiness: BLOCKED (Carol White)
```

### After Decisions

```
All issues resolved:
  Validation: ✓ 2 decided
  Normalization: ✓ 1 decided
  Duplicates: ✓ 1 decided
  Households: ✓ 1 decided

Export readiness: READY (green)
Export file: householder-export-demo-[timestamp].csv
Audit trail: 7+ entries
```

---

## Reset and Cleanup

### Option A: Keep Demo Data

If you want to keep the demo data and run the demo again later, just restart the app with the same environment variables.

### Option B: Reset for Next Demo

```bash
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/householder_demo.db"
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports_demo"

python scripts/reset_demo_batch.py
```

Expected output:
```
✓ Demo cleanup complete!
Deleted from demo database: 12 records, 5 review items
Deleted from demo exports: 1 export files
Demo is clean. Ready for next seeding.
```

Then run `python scripts/seed_demo_batch.py` to seed fresh data.

### Option C: Nuke Demo Entirely

```bash
rm -rf householder_demo.db exports_demo
```

Then run `python scripts/seed_demo_batch.py` to recreate.

---

## Verification: Production Remains Untouched

**Demo database path:**
```bash
ls -la householder_demo.db
```
Expected: Demo file exists (separate from production).

**Demo exports path:**
```bash
ls -la exports_demo
```
Expected: Demo directory exists (separate from production).

**Production database (verify untouched):**
```bash
ls -la givebutter.db
```
Expected: Unchanged from before demo.

**Production exports (verify untouched):**
```bash
ls -la exports
```
Expected: Unchanged from before demo (should be empty initially).

**Verify no demo data in production:**
```bash
sqlite3 givebutter.db "SELECT COUNT(*) FROM import_batches WHERE batch_name LIKE 'DEMO%';"
```
Expected output: `0` (no demo data in production)

---

## Troubleshooting

### Demo Won't Seed

**Error: "Not using demo database!"**
- Solution: Verify `GIVEBUTTER_DATABASE_URL` contains "demo" and "householder_demo.db"

**Error: "Not using demo export directory!"**
- Solution: Verify `EXPORT_OUTPUT_DIR` contains "demo" and "exports_demo"

### Demo Database Corrupted

**Solution:** Delete and reseed
```bash
rm householder_demo.db
python scripts/seed_demo_batch.py
```

### Need Fresh Demo State

**Solution:** Run reset script
```bash
python scripts/reset_demo_batch.py
python scripts/seed_demo_batch.py
```

### App Won't Start

**Check environment variables:**
```bash
echo $GIVEBUTTER_DATABASE_URL
echo $EXPORT_OUTPUT_DIR
```

Both should contain "demo".

---

## Safety Guarantees

✓ **Demo uses isolated database:** `householder_demo.db` (never touches `givebutter.db`)  
✓ **Demo uses isolated exports:** `exports_demo/` (never touches `exports/`)  
✓ **Scripts verify demo paths before running**  
✓ **Reset script only deletes demo data**  
✓ **Production data always protected**

---

## What You're Exercising

By following this demo walkthrough, you're validating:

1. ✓ **Import & Dashboard** — Batch creation, issue detection, queue display
2. ✓ **Validation Workflow** — Flagging validation issues, decision recording
3. ✓ **Duplicate Detection** — Finding duplicates, making decisions
4. ✓ **Household Detection** — Finding household matches, making decisions
5. ✓ **Normalization** — Suggesting field cleanups, accepting/rejecting
6. ✓ **Readiness Logic** — Blocking on required decisions, enabling export when ready
7. ✓ **Export Generation** — Creating export CSV, verifying format
8. ✓ **Export Download** — Downloading export file from browser
9. ✓ **Audit Trail** — Recording all actions and decisions
10. ✓ **Data Immutability** — Raw data unchanged, decisions are metadata only

All without touching production data or exports.

---

## When You're Done

1. Stop Flask app (Ctrl+C)
2. Optionally reset demo: `python scripts/reset_demo_batch.py`
3. Production database and exports remain completely untouched

Ready for actual deployment!
