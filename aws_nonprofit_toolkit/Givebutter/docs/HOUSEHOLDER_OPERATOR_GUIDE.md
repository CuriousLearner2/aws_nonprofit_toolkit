# Householder Operator Guide

**Purpose:** Step-by-step instructions for non-technical operators to run and use Householder.

**Prerequisites:** Mac or Linux machine with Python 3.11+ installed.

---

## Quick Start (5 minutes)

### 1. Activate Environment

**First time only:**
```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Every time you start:**
```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
source venv/bin/activate
```

### 2. Start Householder

```bash
python3 scripts/uploader/app.py
```

**Expected Output:**
```
Running on http://127.0.0.1:8000
Press CTRL+C to quit
```

### 3. Open Browser

Visit: **http://127.0.0.1:8000/imports**

You should see the Imports List screen (empty if this is your first time).

---

## Full Workflow: Step-by-Step

### Step 1: Upload a Batch (2 minutes)

**On the Imports List screen** (`http://127.0.0.1:8000/imports`):

1. Click **"Upload CSV"** or drag-and-drop a CSV file
2. Select your Givebutter CSV export (must have columns: Name, Email, Phone, Amount, Date)
3. Wait for upload to complete (progress bar shows status)
4. System runs validation (typically < 5 seconds)

**You'll see:**
- Batch created with ID (e.g., `IMP-2026-0828-ABC123`)
- Summary of results: total records, PASS count, WARNING count, FAIL count

**What's happening behind the scenes:**
- System validates each row (email format, phone format, amount present, date format)
- System identifies potential duplicates
- System detects household grouping candidates
- ReviewItems created for each issue

---

### Step 2: Review Dashboard (2 minutes)

**Click the batch → Dashboard tab** (`/imports/<id>/dashboard`)

**You'll see:**
- Total records processed
- Validation issues to review (count by type)
- Duplicate issues to review (count)
- Household issues to review (count)
- Normalizations to review (count)

**What to do:**
- Review the summary
- Note which issue types need attention
- Proceed to validation review if there are validation issues

---

### Step 3: Review & Fix Validation Issues (variable time)

**Click Validation tab** (`/imports/<id>/validation`)

**For EACH record with issues:**

**You'll see:**
| Column | What It Shows |
|--------|---|
| Name | Donor name |
| Email | Current email, issues flagged |
| Phone | Current phone, issues flagged |
| Amount | Current amount, issues flagged |
| Date | Current date, issues flagged |
| Status | System-derived status (PASS/WARNING/FAIL) |

**Your decision for each issue:**

**Option 1: Accept System Suggestion**
- Click the suggested fix (e.g., "Did you mean gmail.com?")
- System saves the correction
- Row status recalculates

**Option 2: Manually Edit**
- Click the field and type the correct value
- Press Enter or click away to save
- System validates before saving (rejects if invalid)
- Row status recalculates

**Option 3: Keep Raw Value**
- Do nothing (leave it as-is)
- System records "reviewed but not corrected"

**Example Scenario:**
```
Raw data: gmai.com
System: "⚠️ Invalid email domain. Did you mean gmail.com?"
You: Click the suggestion
Result: Email updated to gmail.com, row status changes from WARNING → PASS
Audit: Entry recorded "validation_autosave: field=email, old=gmai.com, new=gmail.com"
```

**When to Move On:**
- All rows with FAIL status are either:
  - Corrected (now PASS), or
  - Explicitly kept as-is (acknowledged as FAIL)
- All WARNING rows are reviewed

**If you see "Missing Email" and can't fix it:**
- This is a FAIL (critical blocker)
- Record a disposition: "Reject Row" (exclude from export) or "Needs Follow-up"
- Move to next row

---

### Step 4: Review Duplicates (variable time)

**Click Duplicates tab** (`/imports/<id>/duplicates`)

**You'll see:**
- Potential duplicate pairs with similarity score
- Both donors' information side-by-side

**Your decision for each pair:**

**Option 1: Same Person**
- Click "This is the same person"
- System merges records
- Audit: Entry recorded

**Option 2: Different People**
- Click "These are different people"
- System keeps them separate
- Audit: Entry recorded

**Option 3: Follow-up Later**
- Click "I'll decide later"
- Record comes back later for review
- Audit: Entry recorded

**Decision Required?**
- Reviewer name is required to record any decision
- System prompts for your name if not already entered
- Notes are optional but recommended (e.g., "Spelling variation but definitely different person")

---

### Step 5: Review Households (variable time)

**Click Households tab** (`/imports/<id>/households`)

**You'll see:**
- Potential household groupings (family members, shared addresses, etc.)
- All members in each group displayed together

**Your decision for each group:**

**Option 1: Confirm Household**
- Click "Confirm this household"
- System groups records
- Audit: Entry recorded

**Option 2: Reject Grouping**
- Click "These should not be grouped"
- System keeps them as separate individuals
- Audit: Entry recorded

**Option 3: Follow-up Later**
- Click "I'll decide later"
- Record comes back later
- Audit: Entry recorded

**Decision Required?**
- Reviewer name is required
- Notes optional (e.g., "Different last names, likely not related")

---

### Step 6: Review Normalizations (variable time)

**Click Normalizations tab** (`/imports/<id>/normalizations`)

**You'll see:**
- Auto-corrections applied by the system
- Original value and corrected value shown side-by-side

**Examples of normalizations:**
- Phone: `(415) 555-2671` → standardized format
- Date: `8/1/2026` → `2026-08-01`
- Amount: ` $100.00 ` → `100.00`

**Your decision for each normalization:**

**Option 1: Accept Normalization**
- The correction looks correct
- Click "Accept this normalization"
- System uses the corrected value in export

**Option 2: Reject Normalization**
- The correction is wrong or you prefer the raw value
- Click "Reject this normalization"
- System uses the original raw value in export

**Option 3: Follow-up Later**
- Click "I'll decide later"

**Decision Required?**
- Reviewer name is required
- Notes optional

---

### Step 7: Verify Readiness (2 minutes)

**Click Readiness tab** (`/imports/<id>/readiness`)

**System checks:**
- ✓ All FAIL records have been approved or rejected
- ✓ All validation decisions have been made
- ✓ All duplicate decisions have been made
- ✓ All household decisions have been made
- ✓ All normalization decisions have been made
- ✓ No legacy unresolved decisions

**Results shown:**
- Green checkmarks for items that passed
- Red warnings for anything blocking export

**If You See a Warning:**
- Go back to the relevant tab (Validation/Duplicates/Households/Normalizations)
- Complete the unfinished decisions
- Return to Readiness to verify again

**If All Checks Pass:**
- Click **"Approve for Export"** button
- Enter your reviewer name (if not already entered)
- System records batch approval in audit trail

---

### Step 8: Generate & Download Export (2 minutes)

**Click Exports tab** (`/imports/<id>/exports`)

**On the Exports screen:**
1. Click **"Generate Export Files"** button
2. Wait for files to generate (typically < 10 seconds)
3. Three CSV files appear as download links:
   - `<batch_id>_cleaned.csv` — Corrected data for CRM import
   - `<batch_id>_duplicates.csv` — Merged duplicate records (for your records)
   - `<batch_id>_households.csv` — Grouped household records

**Download each file:**
- Right-click → "Save Link As"
- Or click the link (browser downloads automatically)

**Files are now ready to import into your CRM.**

---

## Data Locations & Persistence

### Where Your Data Lives

**Active Import Batches:**
- Location: SQLite database at `givebutter.db` (in project root)
- Contains: All uploaded batches, review decisions, audit trail
- Accessible via: Householder web interface only (not meant for manual editing)

**Generated Export Files:**
- Location: Folder configured in `.env` file (default: `/tmp/givebutter/exports/`)
- Format: CSV files
- Names: `<batch_id>_cleaned.csv`, `<batch_id>_duplicates.csv`, `<batch_id>_households.csv`
- Lifetime: Kept until you delete them

**Audit Trail:**
- Location: SQLite database (`givebutter.db`)
- Contents: Every review decision, correction, and disposition
- Access: View in Householder UI (Audit Log tab) or via database tool

### Backing Up Your Work

**To preserve audit trail and decisions:**
```bash
# Backup the database (contains all review history)
cp givebutter.db givebutter_backup_$(date +%Y%m%d_%H%M%S).db
```

**To preserve export files:**
```bash
# Copy exports folder
cp -r /tmp/givebutter/exports exports_backup_$(date +%Y%m%d_%H%M%S)
```

---

## Safe Restart & Recovery

### Normal Shutdown

```bash
# In the terminal running Householder:
Press CTRL+C

# You'll see:
Quit: Bye!
```

**Before restarting:** No special steps needed. All data is saved to database.

### Restart After Shutdown

```bash
# Reactivate environment (if terminal was closed)
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter
source venv/bin/activate

# Start Householder again
python3 scripts/uploader/app.py

# Visit: http://127.0.0.1:8000/imports
# Your batches are still there
```

### If Householder Crashes

**If you see an error or app stops responding:**

1. **Restart the application:**
   ```bash
   Press CTRL+C (if still running)
   python3 scripts/uploader/app.py
   ```

2. **If the error persists:**
   - Check the error message in the terminal
   - Verify database file exists: `ls -la givebutter.db`
   - All data is safe (database persists across restarts)

3. **If database is corrupted (rare):**
   - Stop Householder: `CTRL+C`
   - Restore from backup: `cp givebutter_backup_*.db givebutter.db`
   - Restart: `python3 scripts/uploader/app.py`

---

## Reviewer Identity & Notes

### When Reviewer Name Is Required

When you record ANY disposition (validation decision, duplicate decision, household decision, normalization decision), the system requires:

1. **Your name or email** — Recorded in audit trail
2. **Notes** — Optional but strongly recommended

**Where to enter:**
- First screen shows a prompt for reviewer name
- Notes field on each review tab

**Example:**
```
Reviewer: john.smith@nonprofit.org
Notes: Manually corrected email typo (gmai→gmail), verified with donor contact list
Decision: Accept correction
```

### Requirements

- **Reviewer name:** Required (system prompts if missing)
- **Notes:** Optional (no review can proceed without reviewer name, but notes are voluntary)
- **Approval:** All decisions are final and appended to audit trail (cannot be undone, only superseded with a new decision)

---

## Troubleshooting

### "App won't start" or "Connection refused"

**Problem:** `http://127.0.0.1:8000` shows "Cannot connect"

**Solutions:**
1. Verify Householder is running: Check terminal, look for "Running on http://127.0.0.1:8000"
2. Verify port is free: `lsof -i :8000` (should show `python3` process, not another app)
3. Restart: `CTRL+C` and `python3 scripts/uploader/app.py` again

### "I uploaded a file but don't see it in the list"

**Problem:** Batch not appearing in Imports List

**Solutions:**
1. Refresh browser: Press F5 or CTRL+R
2. Wait for upload to complete: Progress bar must reach 100%
3. Check file format: CSV must have standard columns (Name, Email, Phone, Amount, Date)
4. Check file encoding: Must be UTF-8 (not Windows-1252 or other)

### "Correction was rejected with 'Invalid email'"

**Problem:** System won't accept your manual correction

**Solutions:**
1. Email format: Must have `@domain.com` structure
2. No spaces: Trim leading/trailing spaces
3. Real domain: `gmai.com` is rejected, `gmail.com` is accepted
4. Examples of valid: `user@gmail.com`, `donor@nonprofit.org`, `test+tag@domain.co.uk`

### "Batch is not ready for export" (Readiness shows warnings)

**Problem:** Readiness check fails

**Solutions:**
1. Check which item type has warnings (Validation/Duplicates/Households/Normalizations)
2. Go to that tab and complete all outstanding decisions
3. Return to Readiness and refresh
4. Example: If Validation has 3 items with no decision, go to Validation tab and decide on all 3

### "Export generated but no CSV files appear"

**Problem:** Generate button is pressed but no files shown

**Solutions:**
1. Wait 10-15 seconds (sometimes generation is slower)
2. Refresh the page: F5 or CTRL+R
3. Check default export folder exists: `ls -la /tmp/givebutter/exports/`
4. If folder doesn't exist, contact tech support (configuration issue)

---

## What You MUST NOT Do

### Critical Rules

- ❌ **Do not delete `givebutter.db`** — This is your complete audit trail and work history
- ❌ **Do not edit CSV files manually before review** — Always use Householder's inline edit feature
- ❌ **Do not close browser mid-review** — Reviews must complete before navigating away (data autosaves, but modal dialogs may lose state)
- ❌ **Do not reuse reviewer names across people** — Each reviewer should use their own identifier
- ❌ **Do not bypass validation by editing the database** — All changes must go through the web interface (for audit trail)
- ❌ **Do not leave FAIL records unapproved** — They will block export; must be reviewed and explicitly kept or rejected

### Safe Practices

- ✓ Use backup command above regularly: `cp givebutter.db givebutter_backup_*.db`
- ✓ Always record reviewer name (required for audit)
- ✓ Include notes when correcting data (helps audit trail)
- ✓ Verify readiness before generating export
- ✓ Download and archive export files after generation

---

## Workflow Checklist

Use this checklist for each batch:

- [ ] Upload CSV file (wait for completion)
- [ ] View Dashboard (verify record counts)
- [ ] Review Validation issues (fix or acknowledge each FAIL)
- [ ] Review Duplicates (make same_person / different_people decisions)
- [ ] Review Households (confirm or reject household groups)
- [ ] Review Normalizations (accept or reject auto-corrections)
- [ ] Check Readiness (verify no blockers)
- [ ] Approve Batch (record reviewer name)
- [ ] Generate Export (creates three CSV files)
- [ ] Download Export files (save to your system)
- [ ] Backup database (optional but recommended)

---

**Questions?** See CURRENT_P1_WORKFLOW.md for detailed concepts or CODE_MAP.md for technical architecture.