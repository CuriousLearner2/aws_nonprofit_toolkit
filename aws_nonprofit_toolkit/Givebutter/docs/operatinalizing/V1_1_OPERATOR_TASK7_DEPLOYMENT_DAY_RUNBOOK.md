# Householder v1.1 — Operator Task 7: Deployment Day Runbook

**Version:** 1.1  
**Status:** Ready for Operator Deployment  
**Date:** 2026-06-13  
**Purpose:** Step-by-step operator runbook for safe, verified Householder v1.1 deployment

---

## Executive Summary

This runbook is the single source of truth for deploying Householder v1.1 on deployment day. An operator follows this checklist from start to finish to:

1. Verify all preconditions are met
2. Start the application safely
3. Run a minimal smoke test
4. Verify export and audit functionality
5. Make a go/no-go decision
6. Execute rollback if needed
7. Begin post-deployment monitoring

**Time estimate:** 30-45 minutes for full deployment + smoke test

**Success criterion:** All go/no-go items checked, app running, smoke test passing, ready for users.

---

## Section 1: Preconditions Checklist

**Before starting, confirm all of the following are complete:**

- [ ] **Task 1:** Directory verification complete
  - [ ] All intake/review/exports directories exist with correct permissions
  - [ ] Reference: `docs/operatinalizing/V1_1_OPERATOR_TASK1_DIRECTORY_VERIFICATION.md`

- [ ] **Task 1B/1C:** Folder semantics and filename rules documented
  - [ ] Operators understand `review/approved` vs `exports/`
  - [ ] Filename state suffix rule documented (PROCESSING, FLAGGED, FOLLOWUP, APPROVED, REJECTED, FAILED, ARCHIVED)
  - [ ] Reference: `docs/operatinalizing/V1_1_OPERATOR_FOLDER_SEMANTICS.md`

- [ ] **Task 2:** EXPORT_OUTPUT_DIR configured
  - [ ] Directory path defined: `/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports`
  - [ ] Directory exists and is writable
  - [ ] No files in directory (clean state for initial deployment)
  - [ ] Reference: `docs/operatinalizing/V1_1_OPERATOR_TASK2_EXPORT_OUTPUT_DIR_CONFIGURATION.md`

- [ ] **Task 3:** Database backup configured
  - [ ] SQLite database file exists: `givebutter.db`
  - [ ] Backup directory exists: `/backups/`
  - [ ] Backup command tested and documented
  - [ ] Restore procedure documented
  - [ ] Reference: `docs/operatinalizing/V1_1_OPERATOR_TASK3_DATABASE_BACKUP_CONFIGURATION.md`

- [ ] **Task 4:** HTTPS/network/security planned
  - [ ] Deployment mode chosen: local-only / private network / reverse proxy
  - [ ] Network access control documented
  - [ ] ADMIN_TOKEN decision made (if needed)
  - [ ] Reference: `docs/operatinalizing/V1_1_OPERATOR_TASK4_HTTPS_NETWORK_SECURITY.md`

- [ ] **Task 5:** Support team ready
  - [ ] Support team briefed on v1.1 features
  - [ ] Support team has access to documentation
  - [ ] Escalation procedures documented
  - [ ] Reference: `docs/operatinalizing/V1_1_OPERATOR_TASK5_SUPPORT_READINESS.md`

- [ ] **Task 6:** User/stakeholder communication ready
  - [ ] Stakeholder briefing email drafted (customized with actual names/dates)
  - [ ] User announcement email drafted (ready to send)
  - [ ] Reviewer quick-start available
  - [ ] Support team announcement drafted
  - [ ] Reference: `docs/operatinalizing/V1_1_OPERATOR_TASK6_USER_STAKEHOLDER_COMMUNICATION.md`

- [ ] **Code baseline:** Tests passing
  - [ ] Run: `pytest tests/unit tests/integration -q`
  - [ ] Result should be: 1202 passed

- [ ] **Rollback plan:** Operator understands
  - [ ] Previous known-good commit/build identified
  - [ ] Pre-deployment backup plan documented
  - [ ] Rollback triggers understood
  - [ ] Rollback procedure reviewed (see Section 17 below)

---

## Section 2: Required Environment Variables

### Required

Set before starting Flask:

```bash
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
```

**Verify:**
```bash
echo $EXPORT_OUTPUT_DIR
# Should output the full path above
```

### Optional

If using non-default database location:

```bash
export GIVEBUTTER_DATABASE_URL="sqlite:////Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db"
```

**Verify:**
```bash
echo $GIVEBUTTER_DATABASE_URL
# Should be empty (default) or show custom path
```

### Optional (Bearer Token Gate)

If operator wants an optional pre-existing simple bearer-token gate for local/private network use:

```bash
export ADMIN_TOKEN="<operator-chosen-secret-token-here>"
```

**Important clarification:**
- `ADMIN_TOKEN` is a **pre-existing simple bearer-token gate**, not RBAC, not user accounts, and not user attribution.
- All authenticated users have identical full access (no role separation).
- No user tracking or audit attribution to individual users.
- For production use, rely primarily on infrastructure-level access control: localhost restriction, VPN, firewall, reverse proxy, or SSO.
- `ADMIN_TOKEN` is optional convenience for private network deployments.

**Verify:**
```bash
echo $ADMIN_TOKEN
# Should be empty (no token) or show custom token
```

---

## Section 3: Required Directories & Files

### Verify existence and permissions

**Export directory:**
```bash
ls -ld "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
# Should show: drwxr-xr-x (755)
```

**Backup directory:**
```bash
ls -ld "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups"
# Should show: drwxr-xr-x (755)
```

**Database file:**
```bash
ls -lh "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db"
# Should show: -rw-r--r-- (644)
# Size should be ~44 KB (correct schema)
```

**Database is readable and has correct schema:**
```bash
sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" ".tables"
# Should show: alembic_version audit_log import_batches import_contacts raw_import_rows review_decisions review_item_subjects review_items
```

---

## Section 4: Deployment Mode Selection

### Choose one of three modes:

#### Mode 1: Local-Only (Recommended for development/testing)

```bash
flask run --host=127.0.0.1 --port=8000
```

**Use case:** Single operator machine, not accessible from network.  
**Security:** Inherent — only accessible on localhost.  
**ADMIN_TOKEN:** Not needed (optional).

#### Mode 2: Private Network (For team/organization use)

```bash
flask run --host=0.0.0.0 --port=8000
```

**Use case:** Private network behind firewall/VPN, accessible to authorized team members.  
**Security:** Operator responsible for firewall/VPN + optional ADMIN_TOKEN.  
**ADMIN_TOKEN:** Optional bearer token gate for additional convenience.

#### Mode 3: Production (Reverse Proxy)

```bash
flask run --host=127.0.0.1 --port=8000
```

**Use case:** Internet-facing or multi-org, behind reverse proxy with HTTPS/TLS.  
**Security:** Reverse proxy (nginx/Apache) handles HTTPS, TLS, access control, and SSO integration.  
**ADMIN_TOKEN:** Not needed (proxy handles authentication).  
**Example proxy setup:** Nginx with HTTPS/TLS termination, request routing to `127.0.0.1:8000`, optional mod_auth or SSO integration.

---

## Section 5: Pre-Deployment Checklist

### 30 minutes before go-live

- [ ] **Code verification:**
  ```bash
  git log --oneline -1
  # Should show the release commit (docs: Phase 3-Step 7... or similar)
  ```

- [ ] **Test suite passes:**
  ```bash
  pytest tests/unit tests/integration -q
  # Should show: 1202 passed
  ```

- [ ] **Export directory is empty and writable:**
  ```bash
  ls -la "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
  # Should show directory exists, no CSV files
  # Should be writable: touch test.txt && rm test.txt (succeeds)
  ```

- [ ] **Database is readable:**
  ```bash
  sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" "SELECT COUNT(*) FROM import_batches;"
  # Should return 0 or a number (not an error)
  ```

- [ ] **Environment variables set:**
  ```bash
  echo "EXPORT_OUTPUT_DIR=$EXPORT_OUTPUT_DIR"
  echo "GIVEBUTTER_DATABASE_URL=$GIVEBUTTER_DATABASE_URL"
  echo "ADMIN_TOKEN=$ADMIN_TOKEN"
  # Verify EXPORT_OUTPUT_DIR is set correctly
  # Others may be empty (defaults are fine)
  ```

- [ ] **Backup of database created:**
  ```bash
  sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" ".backup '/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups/pre-deployment-$(date +%Y%m%d-%H%M%S).db'"
  
  ls -lt "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups/" | head -1
  # Should show the backup file just created
  ```

- [ ] **User communication ready to send:**
  - [ ] Stakeholder briefing email customized and approved
  - [ ] User announcement email customized and ready to send
  - [ ] Support team has been notified and briefed

- [ ] **Rollback plan understood:**
  - [ ] Previous known-good build identified
  - [ ] Rollback triggers reviewed (Section 16 below)
  - [ ] Rollback procedure reviewed (Section 17 below)

---

## Section 6: Application Startup

### Start Flask application

Choose the startup command matching your deployment mode (Section 4):

**Local-only:**
```bash
cd "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
flask run --host=127.0.0.1 --port=8000
```

**Private network:**
```bash
cd "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
flask run --host=0.0.0.0 --port=8000
```

**Production (behind reverse proxy):**
```bash
cd "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter"
flask run --host=127.0.0.1 --port=8000
```

### Monitor startup logs

**Expected output (first 10-15 seconds):**
```
 * Serving Flask app 'app'
 * Debug mode: off
 * WARNING in app.py:... (this is normal)
 * Running on http://127.0.0.1:8000
 * Press CTRL+C to quit
```

**Stop if you see:**
- `ERROR` messages
- `Database connection failed`
- `File not found` (for export directory or database)
- Any uncaught exception

---

## Section 7: Health & Connectivity Checks

### 2-3 minutes after startup

**Check 1: Home page responds**
```bash
curl -s http://localhost:8000/ | head -20
# Should return HTTP 200 with HTML content
# Should NOT return 404, 500, or error
```

**Check 2: Dashboard route responds**
```bash
curl -s http://localhost:8000/dashboard | head -20
# Should return HTTP 200 with HTML content
```

**Check 3: Upload route is accessible**
```bash
curl -s http://localhost:8000/upload | head -20
# Should return HTTP 200 with HTML content
```

**Check 4: API endpoint responds (readiness check)**
```bash
curl -s http://localhost:8000/api/readiness | python3 -m json.tool
# Should return JSON (empty or with batch data)
# Should NOT return 404 or 500
```

**Check 5: No critical errors in logs**

While monitoring Flask logs (from Section 6), watch for:
- [ ] No `ERROR` messages
- [ ] No `CRITICAL` messages
- [ ] No `Database connection failed`
- [ ] No `File not found` or `Permission denied`
- [ ] No uncaught exceptions

---

## Section 8: Create Minimal Test CSV

If no sample test data exists, create a tiny temporary test CSV for smoke testing.

### Create test CSV (temporary)

```bash
cat > /tmp/householder-smoke-test.csv << 'EOF'
First Name,Last Name,Email,Phone,Amount,Date,Transaction ID
John,Doe,john.doe@example.com,555-0001,100.00,2026-01-01,TX001
Jane,Smith,jane.smith@example.com,555-0002,250.50,2026-01-02,TX002
John,Doe,john.doe@example.com,555-0001,50.00,2026-01-03,TX003
Alice,Johnson,alice.johnson@example.com,555-0003,150.00,2026-01-04,TX004
EOF

# Verify it exists
ls -lh /tmp/householder-smoke-test.csv
# Should show ~300 bytes
```

**What this CSV includes:**
- 4 records (3 after header)
- Intentional duplicate (John Doe appears twice) — triggers duplicate detection
- Valid emails and phones — pass validation
- Mixed donation amounts — no validation issues
- One record per row — no formatting errors

---

## Section 9: Smoke Test Workflow

### Run the complete smoke-test workflow

**Time estimate:** 10-15 minutes

#### Step 1: Upload CSV

Navigate to: `http://localhost:8000/upload`

- [ ] Upload page loads
- [ ] File picker is available
- [ ] Select `/tmp/householder-smoke-test.csv`
- [ ] Click "Upload"
- [ ] Wait for processing (should be < 10 seconds)
- [ ] Success message appears (or batch ID shown)
- [ ] **Record the batch ID** (you'll need it for verification)

**Expected outcome:** Batch created, 3 records imported, issues detected (duplicate and possibly normalizations).

---

#### Step 2: Review Validation Queue

Navigate to: `http://localhost:8000/dashboard`

- [ ] Dashboard loads
- [ ] Shows batch summary (3 records imported)
- [ ] Review queues visible:
  - [ ] Validation queue shows items (if any validation issues)
  - [ ] Normalization queue shows items (if any formatting suggestions)
  - [ ] Duplicates queue shows items (should show the duplicate John Doe)
  - [ ] Households queue shows items (if any household groupings detected)

**Expected outcome:** At least Duplicates queue has 1 item (John Doe duplicate).

---

#### Step 3: Review & Make Decisions

For this smoke test, make minimal decisions:

**Duplicates queue (if present):**
- [ ] Navigate to duplicates
- [ ] See the two John Doe records
- [ ] Click "Different Person" (or "Same Person" — both are valid)
- [ ] Click "Save Decision"
- [ ] **Verify decision is recorded** (reappears in next batch load or refreshed view)

**Validation/Normalization/Households (if present):**
- [ ] Accept or reject at least one item in each queue (if present)
- [ ] Click "Save Decision"
- [ ] **Verify no errors** in logs or UI

**Expected outcome:** All queues are either empty or have decisions made.

---

#### Step 4: Check Readiness Dashboard

Navigate to: `http://localhost:8000/readiness`

- [ ] Readiness dashboard loads
- [ ] Shows batch summary
- [ ] Shows status of each queue:
  - [ ] Validation: `✓ OK` or `⚠️ X items` (depends on decisions made)
  - [ ] Normalization: `✓ OK` or `⚠️ X items`
  - [ ] Duplicates: `✓ OK` (all decisions made) or `⚠️ X items`
  - [ ] Households: `✓ OK` or `⚠️ X items`
- [ ] If all queues are clear: `Ready to Export` button appears
- [ ] If any queue has undecided items: `Not Ready` message

**Expected outcome:** Either ready to export or clearly showing what's blocking export.

---

#### Step 5: Generate Export

**If readiness shows "Ready to Export":**
- [ ] Click "Generate Export"
- [ ] Wait for processing (should be < 10 seconds)
- [ ] Success message appears

**If readiness shows "Not Ready":**
- [ ] Make remaining decisions (go back to Step 3)
- [ ] Check readiness again
- [ ] Once ready, click "Generate Export"

**Expected outcome:** Export CSV is generated and written to `EXPORT_OUTPUT_DIR`.

---

#### Step 6: Verify Export File Exists

```bash
ls -lh "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports/"
# Should show the generated CSV file
# Example: householder-export-<batch-id>-<state>-<timestamp>.csv
# File size should be > 100 bytes
```

**Expected outcome:** Export file exists and is readable.

---

#### Step 7: Download Export

Navigate to: `http://localhost:8000/exports`

- [ ] Exports page loads
- [ ] Shows the generated export file (with timestamp/batch ID)
- [ ] Click on the file or "Download" button
- [ ] File downloads to your machine

**Expected outcome:** File downloads without error.

---

#### Step 8: Verify Export Content

```bash
# Check the downloaded file
# Usually downloads to ~/Downloads/householder-export-<...>.csv

# Verify it's a valid CSV with correct columns
head -5 ~/Downloads/householder-export-*.csv
# Should show: First Name, Last Name, Email, Phone, Amount, Date, Transaction ID
# Followed by 3-4 data rows
```

**Expected outcome:** Export CSV is valid and contains expected data.

---

### Step 9: Verify Audit Trail

Navigate to: `http://localhost:8000/audit`

- [ ] Audit page loads
- [ ] Shows log entries for:
  - [ ] Batch upload
  - [ ] Decisions made (validation, normalization, duplicates, households)
  - [ ] Export generation
  - [ ] Export download (if tracked)

**Expected outcome:** Audit trail shows complete decision history and export generation.

---

## Section 10: Export Verification

### Verify export file meets safety requirements

```bash
# Get the export file path
EXPORT_FILE=$(ls -t "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"/*.csv 2>/dev/null | head -1)

# Verify file exists
test -f "$EXPORT_FILE" && echo "✓ Export file exists" || echo "✗ Export file missing"

# Verify file is readable
test -r "$EXPORT_FILE" && echo "✓ Export file is readable" || echo "✗ Export file not readable"

# Verify file size is reasonable (> 100 bytes for 3 records + header)
SIZE=$(stat -f%z "$EXPORT_FILE" 2>/dev/null || stat -c%s "$EXPORT_FILE" 2>/dev/null)
test $SIZE -gt 100 && echo "✓ Export file size is reasonable ($SIZE bytes)" || echo "✗ Export file too small"

# Verify permissions are safe (644 = rw-r--r--)
PERMS=$(stat -f%Lp "$EXPORT_FILE" 2>/dev/null | tail -1 || stat -c%a "$EXPORT_FILE" 2>/dev/null)
echo "Export file permissions: $PERMS (should be 644)"

# Verify file is NOT world-writable
test $(stat -f%Lp "$EXPORT_FILE" 2>/dev/null | grep -o .$) = "-" && echo "✓ Export file not world-writable" || echo "⚠️ Check world-writable status"

# Verify header row
head -1 "$EXPORT_FILE"
# Should show: First Name,Last Name,Email,Phone,Amount,Date,Transaction ID

# Verify data rows exist
LINE_COUNT=$(wc -l < "$EXPORT_FILE")
echo "Export file line count: $LINE_COUNT (should be 4-5 for smoke test)"
```

**Expected outcome:**
- ✓ File exists
- ✓ File is readable
- ✓ File size > 100 bytes
- ✓ Permissions are 644 (rw-r--r--)
- ✓ NOT world-writable
- ✓ Header row is correct
- ✓ Data rows present (4-5 lines total)

---

## Section 11: Audit Trail Verification

### Verify audit log records expected actions

```bash
# Query the audit log directly
sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" << 'EOF'
SELECT action_type, COUNT(*) as count FROM audit_log GROUP BY action_type;
EOF

# Expected output should include:
# import_batch_created     1
# decision_made            3-4 (one per decision made in smoke test)
# export_generated         1
# Maybe export_downloaded  1
```

**Expected outcome:** Audit log contains entries for:
- 1 import batch created
- 3-4 decisions made
- 1 export generated
- (optionally) 1 export downloaded

---

## Section 12: Security Spot-Check

### Verify no unexpected external calls

**Check network activity during smoke test:**

Option A: Monitor with `lsof` (if available):
```bash
# In another terminal, while running the smoke test:
lsof -i -P -n | grep "python\|flask" | grep ESTABLISHED
# Should show NO connections to external services (Givebutter, CRM, etc.)
# May show local connections only
```

Option B: Check Flask logs:
```bash
# Watch the Flask logs from Section 6
# Should see NO entries like:
# - "Connecting to Givebutter"
# - "API key found"
# - "Calling external endpoint"
# - "CRM sync"
```

Option C: Code inspection (already done, but verify):
```bash
# Verify in source code
grep -r "requests\|urllib\|http" givebutter_app/services/*.py | grep -i "givebutter\|crm\|external"
# Should return 0 results
```

**Expected outcome:** ✓ NO external API calls detected.

---

## Section 13: Log Review Checklist

### Review application logs for issues

While Flask is running, monitor the console output. After smoke test, check for:

- [ ] **No ERROR messages:**
  ```bash
  # Grep the logs (if saved to file)
  grep "ERROR" /path/to/logs/householder.log | wc -l
  # Should return 0
  ```

- [ ] **No CRITICAL messages:**
  ```bash
  grep "CRITICAL" /path/to/logs/householder.log | wc -l
  # Should return 0
  ```

- [ ] **No database errors:**
  ```bash
  grep -i "database\|sqlite\|connection" /path/to/logs/householder.log | grep -i "error\|failed"
  # Should return 0
  ```

- [ ] **No permission errors:**
  ```bash
  grep -i "permission\|denied\|access" /path/to/logs/householder.log | grep -i "error"
  # Should return 0
  ```

- [ ] **No missing file errors:**
  ```bash
  grep -i "not found\|missing\|does not exist" /path/to/logs/householder.log
  # Should return 0
  ```

**Expected outcome:** Clean logs with no critical errors.

---

## Section 14: Go/No-Go Checklist

### Smoke test is complete. Make the deployment decision.

#### GO (Proceed to Production) if ALL of these are true:

- [ ] ✓ App started cleanly (Section 6)
- [ ] ✓ Health checks pass (Section 7)
- [ ] ✓ Export directory is writable (Section 5)
- [ ] ✓ Database is accessible (Section 5)
- [ ] ✓ Backup exists (Section 5)
- [ ] ✓ Smoke test uploads CSV (Section 9, Step 1)
- [ ] ✓ Smoke test navigates dashboard (Section 9, Step 2)
- [ ] ✓ Smoke test makes decisions (Section 9, Step 3)
- [ ] ✓ Readiness dashboard works (Section 9, Step 4)
- [ ] ✓ Export generation succeeds (Section 9, Step 5)
- [ ] ✓ Export file created in `EXPORT_OUTPUT_DIR` (Section 10)
- [ ] ✓ Export download works (Section 9, Step 7)
- [ ] ✓ Export file is valid CSV (Section 10)
- [ ] ✓ Audit trail records actions (Section 11)
- [ ] ✓ NO external API calls (Section 12)
- [ ] ✓ Logs are clean (Section 13)
- [ ] ✓ User/stakeholder communication is ready (Section 5)
- [ ] ✓ Support team is briefed (Section 5)
- [ ] ✓ Rollback plan is understood (Section 5)

**Decision: ✓ GO FOR DEPLOYMENT**

---

#### NO-GO (Do Not Proceed) if ANY of these are true:

- [ ] ✗ App failed to start (Section 6)
- [ ] ✗ Health checks failed (Section 7)
- [ ] ✗ Export directory missing or unwritable (Section 5)
- [ ] ✗ Database inaccessible (Section 5)
- [ ] ✗ Backup missing (Section 5)
- [ ] ✗ CSV upload failed (Section 9, Step 1)
- [ ] ✗ Dashboard didn't load (Section 9, Step 2)
- [ ] ✗ Decision save failed (Section 9, Step 3)
- [ ] ✗ Export generation failed (Section 9, Step 5)
- [ ] ✗ Export file not created (Section 10)
- [ ] ✗ Export download failed (Section 9, Step 7)
- [ ] ✗ Export file is corrupt or invalid (Section 10)
- [ ] ✗ Audit trail missing entries (Section 11)
- [ ] ✗ Unexpected external API calls detected (Section 12)
- [ ] ✗ Critical errors in logs (Section 13)
- [ ] ✗ User/stakeholder communication not ready
- [ ] ✗ Support team not briefed
- [ ] ✗ Rollback plan not understood

**Decision: ✗ DO NOT DEPLOY** (Investigate and remediate first)

---

## Section 15: Rollback Triggers

**Execute rollback immediately if ANY of these occur after go-live:**

### Critical Triggers (Stop immediately)

- [ ] Data mutation detected (raw source data changed, should never happen)
- [ ] Database corruption suspected (query errors, missing tables)
- [ ] Security breach (unauthorized access, external API calls detected)
- [ ] Export file consistently fails to generate
- [ ] Export files missing after reported success
- [ ] Audit trail entries missing or corrupted

### High-Priority Triggers (Rollback within 30 minutes)

- [ ] Multiple users report same critical issue
- [ ] Application crashes or restarts repeatedly
- [ ] Cannot access application at all
- [ ] File permissions changed unexpectedly
- [ ] Backup directory becomes unwritable

### Investigation Triggers (Monitor, prepare to rollback)

- [ ] Unusual CPU/memory usage
- [ ] Export generation slow (> 1 minute for small batch)
- [ ] Users report decisions not saving
- [ ] Audit trail missing recent entries

---

## Section 16: Rollback Procedure

**Only execute if a rollback trigger (Section 15) is confirmed.**

### Step 1: Stop user access (immediate)

```bash
# If internet-facing, take down reverse proxy or firewall rule
# If local/private network, optionally announce maintenance
```

### Step 2: Stop application (immediate)

```bash
# Press CTRL+C in the Flask terminal to gracefully stop the application
# Wait 10 seconds for clean shutdown
# If process doesn't stop, use:
pkill -f "flask run"
# or if that doesn't work:
pkill -9 -f "flask run"
```

### Step 3: Identify previous known-good state

```bash
# Check git log for the last known-good commit
git log --oneline -5
# Should show recent commits
# Identify the release commit (typically "docs: Phase 3-Step 7...")
```

### Step 4: Restore previous build (if needed)

```bash
# Option A: If rollback is to previous release tag
git checkout <previous-release-tag>  # e.g., git checkout v1.0

# Option B: If rollback is to previous commit
git checkout <previous-commit-hash>

# Option C: If code is fine but database is corrupted
# DO NOT restore over active database
# Only restore if migration is truly needed
# Ask engineering before restoring database
```

### Step 5: Restore database from backup (ONLY if critical)

**⚠️ WARNING: Only do this if database corruption confirmed and pre-deployment backup exists.**

```bash
# NEVER overwrite active database unless absolutely necessary
# 1. Stop the application (Step 2)
# 2. Identify the pre-deployment backup from Section 5
BACKUP_FILE="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups/pre-deployment-<timestamp>.db"

# 3. Create a temporary copy of the corrupted database for analysis
cp "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" "/tmp/corrupted-$(date +%Y%m%d-%H%M%S).db"

# 4. Restore from backup
sqlite3 "$BACKUP_FILE" ".backup '/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db'"

# 5. Verify restore
sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" "SELECT COUNT(*) FROM import_batches;"
# Should return 0 or same count as before the incident
```

### Step 6: Verify application starts cleanly

```bash
# Start application with previous code/config
flask run --port=8000

# Wait 10 seconds for startup
# Check logs for errors

# If startup succeeds, run quick smoke test (Section 9)
# If startup fails, stop and contact engineering
```

### Step 7: Notify stakeholders (CRITICAL)

Send email to:
- Internal stakeholders
- Support team
- Users (if applicable)

**Include:**
- What happened
- When rollback was initiated
- When service was restored
- Status: "Service is stable, monitoring closely"
- Next steps: "Engineering investigating root cause"

### Step 8: Document incident

Create incident report with:
- Timeline (when issue detected, when rollback initiated, when service restored)
- Trigger (what specific issue triggered the rollback)
- Actions taken (steps 1-7 above)
- Impact (how many users affected, data affected)
- Root cause (if known)
- Prevention plan (what changes to prevent recurrence)

---

## Section 17: Post-Deployment First-Hour Checklist

**After go-live decision (Section 14) and before first users:**

- [ ] **App is running:**
  ```bash
  curl -s http://localhost:8000/ | head -1
  # Should return HTML (not error)
  ```

- [ ] **Logs are clean:**
  - [ ] No ERROR messages
  - [ ] No database connection issues
  - [ ] No permission errors

- [ ] **Export directory is empty (clean state):**
  ```bash
  ls -la "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
  # Smoke test file (from Section 9) should be deleted
  # Or moved to archive if organization requires
  ```

- [ ] **Support team is standing by:**
  - [ ] Support has documentation open
  - [ ] Support team is monitoring for first user issues
  - [ ] Escalation procedure is clear

- [ ] **User communication sent:**
  - [ ] Stakeholder briefing email sent (or delivered)
  - [ ] User announcement email sent
  - [ ] Support contact information confirmed in email

- [ ] **Monitoring is active:**
  - [ ] Operator is monitoring logs
  - [ ] Operator is responsive to support escalations
  - [ ] Operator checks database is being written to

---

## Section 18: Post-Deployment Week-1 Checklist

**Daily (Monday-Friday, Week 1):**

- [ ] **Check app is running:**
  ```bash
  curl -s http://localhost:8000/dashboard 2>&1 | head -1
  # Should return HTTP 200 with HTML
  ```

- [ ] **Verify backups are created:**
  ```bash
  ls -lt "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/backups/" | head -3
  # Should show recent backups (if daily backup job configured)
  ```

- [ ] **Check database integrity:**
  ```bash
  sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" "SELECT COUNT(*) FROM import_batches;"
  # Should return a number (not error)
  ```

- [ ] **Monitor support tickets:**
  - [ ] Track common questions
  - [ ] Identify confusion points
  - [ ] Document workarounds

- [ ] **Spot-check log file (if saving to file):**
  ```bash
  tail -20 /path/to/householder.log | grep -i "error\|critical"
  # Should return 0 results
  ```

**Weekly (End of Week 1):**

- [ ] **Verify no data mutations:**
  ```bash
  # Check that raw_import_rows table has no UPDATE entries
  # Verify all audit log entries are INSERT only (no UPDATE/DELETE)
  sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" "SELECT COUNT(*) FROM audit_log;"
  # Should show growing (new entries each day)
  ```

- [ ] **Backup test:**
  ```bash
  # Create a test backup
  sqlite3 "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/givebutter.db" ".backup '/tmp/backup-test-$(date +%Y%m%d).db'"
  
  # Verify restore
  sqlite3 "/tmp/backup-test-*.db" ".tables"
  # Should show all 8 tables
  
  # Clean up
  rm /tmp/backup-test-*.db
  ```

- [ ] **Compile user feedback:**
  - [ ] What questions did users ask most?
  - [ ] What confused users?
  - [ ] What feature requests came up?
  - [ ] Any unexpected issues?

---

## Section 19: Post-Deployment Monitoring Plan

### Ongoing (Weeks 2-4)

**At least weekly:**

- [ ] Monitor application logs for unexpected errors
- [ ] Verify export files are being generated
- [ ] Verify exports can be downloaded
- [ ] Check database file size is growing (indicates usage)
- [ ] Verify backup schedule is running
- [ ] Respond to support escalations within SLA

**Week 4:**

- [ ] Compile all feedback collected
- [ ] Categorize feedback (bugs, feature requests, documentation gaps)
- [ ] Identify demand signals (% wanting bulk actions, % expecting CRM sync)
- [ ] Brief stakeholders on findings
- [ ] Recommend v1.1.1 patches vs v1.2 features vs v2.0+ priorities

---

## Section 20: 15 Hard Guardrails Confirmed

v1.1 will NOT:

✓ **Sync to CRM** — Export-only, users upload manually  
✓ **Store credentials** — No API keys, no passwords  
✓ **Merge contacts** — Decisions create metadata only  
✓ **Assign households** — Grouping metadata only  
✓ **Bulk approve** — Individual decisions required  
✓ **Call external APIs** — No Givebutter, CRM, or external calls  
✓ **Mutate source data** — Raw imports are immutable  
✓ **Mutate contacts** — Metadata only  
✓ **Delete contacts** — No deletion, only decisions  
✓ **Create background jobs** — Synchronous only  
✓ **Support new export formats** — CSV only  
✓ **Require login/RBAC** — Single operator, optional bearer token  
✓ **Change database schema** — Fixed for v1.1  
✓ **Cross-import matching** — Per-batch only  
✓ **Create master contacts** — No master data structure  

**All guardrails are locked in for v1.1. Do not implement any without explicit stakeholder approval for v2.0+.**

---

## Sign-Off

**Deployment Day Runbook: COMPLETE**

- [x] Purpose documented
- [x] Preconditions checklist created
- [x] Environment variables documented
- [x] Deployment modes explained (local-only, private network, reverse proxy)
- [x] Pre-deployment checklist (30 min before go-live)
- [x] Application startup commands documented
- [x] Health/connectivity checks included
- [x] Minimal test CSV creation instructions provided
- [x] Smoke-test workflow documented (9 steps)
- [x] Export verification procedures included
- [x] Audit trail verification documented
- [x] Security spot-check procedures included
- [x] Log review checklist provided
- [x] Go/no-go criteria defined (18 items each)
- [x] Rollback triggers documented (critical, high-priority, investigation)
- [x] Rollback procedure step-by-step documented
- [x] Post-deployment first-hour checklist included
- [x] Post-deployment week-1 checklist included
- [x] Ongoing monitoring plan (weeks 2-4)
- [x] 15 hard guardrails confirmed

**Householder v1.1 Deployment Day Runbook: READY FOR OPERATOR USE**

---

## References

- `docs/operatinalizing/V1_1_OPERATOR_TASK1_DIRECTORY_VERIFICATION.md` — Directory setup
- `docs/operatinalizing/V1_1_OPERATOR_FOLDER_SEMANTICS.md` — Folder organization
- `docs/operatinalizing/V1_1_OPERATOR_TASK2_EXPORT_OUTPUT_DIR_CONFIGURATION.md` — Export directory
- `docs/operatinalizing/V1_1_OPERATOR_TASK3_DATABASE_BACKUP_CONFIGURATION.md` — Database backup
- `docs/operatinalizing/V1_1_OPERATOR_TASK4_HTTPS_NETWORK_SECURITY.md` — Network security
- `docs/operatinalizing/V1_1_OPERATOR_TASK5_SUPPORT_READINESS.md` — Support training
- `docs/operatinalizing/V1_1_OPERATOR_TASK6_USER_STAKEHOLDER_COMMUNICATION.md` — Communications
- `docs/implementation/release/V1_1_OPERATOR_HANDOFF.md` — Operator handoff package
