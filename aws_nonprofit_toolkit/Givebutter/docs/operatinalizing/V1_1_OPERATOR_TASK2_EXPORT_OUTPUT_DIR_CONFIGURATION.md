# Householder v1.1 — Operator Task 2: Configure EXPORT_OUTPUT_DIR

**Version:** 1.1  
**Status:** Configuration Verification Complete  
**Date:** 2026-06-13  
**Purpose:** Configure dedicated export output directory for generated Householder CSV artifacts

---

## Executive Summary

The dedicated `exports/` directory has been created and verified for use as the Householder v1.1 export artifact location. This directory is configured via the `EXPORT_OUTPUT_DIR` environment variable and maintains strict separation from source/review file folders per the operator deployment model.

---

## Export Output Directory Configuration

### Path

```
/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports
```

### Environment Variable

```bash
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
```

**Note:** This path is deployment-specific and configured for local/development use. In production deployment, the operator will configure a production-appropriate path.

---

## Directory Verification

### Directory Existence

**Status:** ✓ EXISTS  
**Created:** 2026-06-13 13:31 UTC  
**Location:** Already present in project structure  
**Action taken:** Verified existing directory

### Directory Permissions

**Current permissions:** `drwxr-xr-x` (755)

**Permission breakdown:**
- Owner (gautambiswas): read, write, execute
- Group (staff): read, execute
- Others: read, execute

**Assessment:** ✓ SAFE
- Owner can create and modify files
- Not world-writable (no `777`)
- Consistent with project directory policy
- Appropriate for local and production deployment

### Writability Verification

**Test method:** Create and delete temporary test file  
**Result:** ✓ WRITABLE

```bash
# Test command executed
cd "/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
touch .writability_test_temp
# ✓ File created successfully
rm .writability_test_temp
# ✓ File deleted successfully
```

**Assessment:** Directory is fully writable by application user and ready for export generation.

### Existing Files

**Files in exports/ directory:** 0  
**File summary:** Directory is empty and ready for initial use

---

## Critical Distinction

### `review/approved` is NOT Generated Export Output

**`review/approved` folder:**
- Location: `review/approved` (under review/ folder hierarchy)
- Contents: Human-approved source/review CSV files
- Lifecycle: Source file → Review → Approved → Archive
- Example filename: `Givebutter_Donations_2026-06-13__APPROVED__20260613-1130.csv`

**`exports/` folder (EXPORT_OUTPUT_DIR):**
- Location: `exports/` (dedicated separate directory)
- Contents: Generated Householder CSV export artifacts
- Lifecycle: Generated → Downloaded → Uploaded to CRM
- Example filename: `export_householder_batch_001_20260613.csv`

**Operator responsibility:**
- Do NOT configure `review/approved` as `EXPORT_OUTPUT_DIR`
- Do NOT write generated exports to review/ folders
- Do use `exports/` as the sole destination for application-generated exports

---

## Configuration Checklist

✓ **Export directory path verified**  
`/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports`

✓ **Directory already exists with appropriate permissions**  
`drwxr-xr-x (755)` — Owner writable, not world-writable

✓ **Directory writability confirmed**  
Test file creation and deletion successful

✓ **Directory is empty and ready for use**  
0 existing files; ready for initial export generation

✓ **Environment variable documented**  
```bash
export EXPORT_OUTPUT_DIR="/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports"
```

✓ **Separation of concerns maintained**  
`review/approved` ≠ `exports/`; two distinct folders with distinct purposes

✓ **Operator guidance documented**  
Do not use review folders as export output; use exports/ only

---

## For Production Deployment

When deploying Householder v1.1 to production:

1. **Create or verify `exports/` directory on production server**
   ```bash
   mkdir -p /path/to/production/exports
   chmod 755 /path/to/production/exports
   ```

2. **Set `EXPORT_OUTPUT_DIR` environment variable**
   ```bash
   export EXPORT_OUTPUT_DIR="/path/to/production/exports"
   ```

3. **Verify directory is writable**
   ```bash
   python -c "
   import os
   path = os.getenv('EXPORT_OUTPUT_DIR')
   if os.path.exists(path) and os.access(path, os.W_OK):
       print('✓ Export directory writable')
   else:
       print('✗ Export directory not accessible')
   "
   ```

4. **Add to backup strategy**
   - Exports should be included in regular backups
   - OR stored on separate secure backup system
   - Define retention policy for old exports

5. **Monitor disk space**
   - Budget: (avg batch size × export size per row × retention period)
   - Example: 1000 rows/batch × 0.5KB per row × 30-day retention = 15GB

---

## Remaining Operator Actions

### Task 2 — Configure EXPORT_OUTPUT_DIR ✅ COMPLETE
- [x] Export directory path verified: `/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports`
- [x] Directory permissions appropriate: `755` (owner writable, not world-writable)
- [x] Directory writability confirmed
- [x] Empty and ready for use
- [x] Environment variable documented
- [x] Separation from review/approved confirmed

### Task 3 — Database Backup Configuration (Next)
- [ ] Configure database backup schedule
- [ ] Test database backup and restoration
- [ ] Document backup location and procedure
- [ ] Verify database credentials secured
- [ ] Confirm database schema matches v1.1

### Task 4 — HTTPS/Network Security (After Task 3)
- [ ] Enable HTTPS for all connections
- [ ] Configure network access controls
- [ ] Verify no external API calls made
- [ ] Confirm export files not world-readable
- [ ] Verify database credentials not exposed

### Task 5 — Support Team Briefing (Parallel)
- [ ] Schedule stakeholder briefing
- [ ] Train support team on v1.1 features
- [ ] Review export-only model
- [ ] Review known limitations
- [ ] Prepare FAQ responses

### Task 6 — User Communication (Parallel)
- [ ] Prepare release announcement email
- [ ] Link release notes in announcement
- [ ] Link user guides in announcement
- [ ] Link known limitations in announcement
- [ ] Define support contact information

### Task 7 — Deployment Day (After Tasks 2-6)
- [ ] Pre-deployment verification checks
- [ ] Application startup verification
- [ ] Workflow smoke tests (7 tests, 15 minutes)
- [ ] Security spot-checks
- [ ] Rollback readiness verification

### Task 8 — Post-Deployment Monitoring (After Task 7)
- [ ] Week 1: Daily error log checks
- [ ] Week 1: Daily audit trail verification
- [ ] Week 1: Daily export functionality checks
- [ ] Weeks 2-4: Regular monitoring (2-3x per week)
- [ ] Week 4: Compile user feedback for v1.2 roadmap

---

## 15 Hard Guardrails Confirmed

All guardrails remain in place and enforced:

✓ **No CRM/Givebutter API calls**  
✓ **No credentials storage**  
✓ **No writeback routes**  
✓ **No auth/RBAC changes**  
✓ **No bulk actions**  
✓ **No background jobs**  
✓ **No new export formats**  
✓ **No source-data mutations**  
✓ **No contact mutations**  
✓ **No contact merge**  
✓ **No contact deletion**  
✓ **No household_id assignment**  
✓ **No schema changes**  
✓ **No cross-import matching**  
✓ **No master contacts/households**  

---

## Sign-Off

**Task 2 Completion: VERIFIED**

- [x] Export directory path configured: `/Users/gautambiswas/Claude Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter/exports`
- [x] Directory exists with safe permissions (755)
- [x] Directory writability confirmed
- [x] Directory is empty and ready for initial use
- [x] Environment variable documented for operator use
- [x] Separation of concerns maintained: `review/approved` ≠ `exports/`
- [x] Operator guidance documented
- [x] Production deployment guidance included
- [x] All 15 guardrails confirmed

**Householder v1.1 EXPORT_OUTPUT_DIR Configuration: COMPLETE AND READY FOR NEXT TASK**

---

## References

- `docs/operatinalizing/V1_1_OPERATOR_FOLDER_SEMANTICS.md` — Complete folder semantics documentation
- `docs/operatinalizing/V1_1_OPERATOR_TASK1_DIRECTORY_VERIFICATION.md` — Directory structure verification
- `docs/implementation/release/V1_1_OPERATOR_HANDOFF.md` — Operator handoff package
