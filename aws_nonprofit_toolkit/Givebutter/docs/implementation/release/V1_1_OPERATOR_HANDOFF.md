# Householder v1.1 Operator Handoff Package

**Release Version:** v1.1  
**Release Date:** 2026-06-13  
**Status:** READY FOR OPERATOR DEPLOYMENT  
**Baseline:** 1202 tests passing (zero regressions)  
**Release Model:** Export-only (no CRM/Givebutter writeback)

---

## 1. Release Summary

Householder v1.1 is a production-ready export-only donor import review and management tool. Users upload CSV files, reviewers make decisions on validation/normalization/duplicates/households, and v1.1 generates a CSV export for manual CRM import.

**v1.1 does NOT:**
- Sync to CRM/Givebutter
- Store credentials
- Merge contacts
- Assign households
- Support bulk actions
- Support background jobs
- Support new export formats

**v1.1 is production-ready for export-only workflows.**

---

## 2. What Is Already Verified

### Code & Tests (VERIFIED)
✓ All 1202 tests passing (760 unit + 442 integration, zero regressions)  
✓ All critical workflows functional (upload, validate, normalize, duplicates, households, readiness, export, download)  
✓ All security tests passing (path traversal blocked, symlink escapes prevented, batch isolation enforced)  
✓ All data safety guarantees confirmed (zero mutations detected in testing)  
✓ All 15 hard guardrails maintained and enforced  
✓ Export-only architecture locked in  
✓ Audit trail functionality complete (45 audit tests passing)  

### Documentation (VERIFIED)
✓ Release notes complete and accurate  
✓ User workflow guide (EXPORT_ONLY_WORKFLOW.md)  
✓ Reviewer workflow guide (REVIEWER_WORKFLOW.md)  
✓ Known limitations documented (15 limitations)  
✓ Deployment checklist created  
✓ Smoke-test plan documented  
✓ Rollback plan defined  

### Security (VERIFIED)
✓ No CRM/Givebutter API calls in code  
✓ No hardcoded credentials  
✓ No external API calls in export routes  
✓ Path traversal attacks blocked  
✓ Symlink escapes prevented  
✓ Batch isolation enforced  
✓ Export files created with correct permissions  

---

## 3. Operator Must Complete Before Deployment

### ⚠️ BEFORE GOING LIVE

- [ ] **OPERATOR ACTION:** Read this entire handoff document
- [ ] **OPERATOR ACTION:** Review V1_1_KNOWN_LIMITATIONS.md (15 limitations listed)
- [ ] **OPERATOR ACTION:** Review V1_1_RELEASE_NOTES.md (what changed, what's deferred)
- [ ] **OPERATOR ACTION:** Complete export directory setup (checklist below)
- [ ] **OPERATOR ACTION:** Complete database backup setup (checklist below)
- [ ] **OPERATOR ACTION:** Complete HTTPS/network security setup (checklist below)
- [ ] **OPERATOR ACTION:** Brief support team (checklist below)
- [ ] **OPERATOR ACTION:** Prepare user communication (checklist below)
- [ ] **OPERATOR ACTION:** Review rollback plan (section below)
- [ ] **OPERATOR ACTION:** Review smoke-test plan (section below)

---

## 4. Required Production Environment/Configuration

### Application Configuration

**Required:**
- Python 3.11+
- Flask application server
- SQLite database (or compatible)
- Export directory path (must exist, be writable)

**Environment Variables:**
```
EXPORT_OUTPUT_DIR=/path/to/export/directory  (required)
```

**NO Required:**
- CRM/Givebutter credentials
- External API keys
- Auth/RBAC configuration (uses existing context)

### Python Dependencies
```
pip install -r requirements.txt
```

### Database
```
Use existing SQLite database or initialize new one
No migrations required for v1.1
```

---

## 4.5 Folder Structure & Semantics

**IMPORTANT:** Review/understand folder semantics before configuring export directory.

**Key Distinction:**
- `review/approved` = human-approved **source files** (not export output)
- `exports/` = **generated Householder CSV artifacts** (separate directory)

**Folder Categories:**

| Folder | Purpose | Operator-Managed |
|--------|---------|-----------------|
| `intake/new` | Incoming CSVs | Upload here |
| `intake/archive` | Processed CSVs | Archive manually |
| `intake/failed` | Failed imports | Investigate |
| `review/flagged` | Data issues found | Mark for follow-up |
| `review/followup` | Need context/approval | Get clarification |
| `review/approved` | Approved source files | **NOT export output** |
| `exports/` | Generated app exports | Config `EXPORT_OUTPUT_DIR` |

**Decision Rule:**
- **Data issue visible in file?** → `review/flagged`
- **Missing context/approval?** → `review/followup`

**Critical Reminder:**
```
review/approved ≠ exports/
  approved = source file human reviewed
  exports/ = generated Householder CSV for CRM import
```

**Complete Reference:**
See `docs/release/V1_1_OPERATOR_FOLDER_SEMANTICS.md` for full folder definitions and semantics.

---

## 5. Export Directory Setup Checklist

✓ **Code-level verified:** Configuration validation works  
OPERATOR MUST:

- [ ] Create export directory on production server
- [ ] Confirm directory path is writable by application user
- [ ] Set permissions: `-rwx------` (700) or `-rwx--x---` (710)
  - NOT world-readable (do not use 777)
  - NOT world-writable
- [ ] Confirm disk space is sufficient for expected exports
  - Test: Generate one sample export, measure size
  - Budget: (avg batch size × export size per row × retention period)
- [ ] Add directory to backup strategy
  - Exports should be included in regular backups
  - OR stored on separate secure backup system
- [ ] Test directory is accessible from application
  - Deploy application
  - Run smoke test (step below)
  - Confirm export files are created in directory

**Test Command:**
```bash
# After deploying application:
python -c "
import os
path = os.getenv('EXPORT_OUTPUT_DIR')
if os.path.exists(path) and os.access(path, os.W_OK):
    print('✓ Export directory writable')
else:
    print('✗ Export directory not accessible')
"
```

---

## 6. Database Backup Checklist

✓ **Code-level verified:** Data preservation confirmed  
OPERATOR MUST:

- [ ] Configure database backup schedule
  - Recommended: Daily, full backup
  - Retention: 30+ days
- [ ] Test database backup and restoration
  - Create backup
  - Restore to test environment
  - Verify all data intact
- [ ] Document backup location and procedure
- [ ] Confirm database user credentials are secured
  - NOT in code
  - NOT in environment variables visible to code
  - Use application-level database configuration only
- [ ] Verify database connection string is in environment
  - NOT hardcoded in application code
- [ ] Confirm database schema matches v1.1 final version
  - Run: `sqlite3 givebutter.db ".tables"`
  - Should show: batches, raw_import_rows, import_contacts, review_items, decisions, audit_logs, etc.

---

## 7. HTTPS/Network/Security Checklist

✓ **Code-level verified:** No external dependencies  
OPERATOR MUST:

- [ ] Enable HTTPS for all connections
  - SSL certificate installed and valid
  - HTTPS enforced (redirect HTTP to HTTPS)
- [ ] Configure network access controls
  - Application accessible only to authorized users
  - Firewall rules configured
  - No public internet exposure for internal routes
- [ ] Verify no external API calls made
  - Network monitoring: confirm no calls to CRM/Givebutter/external services
  - Logs: no "API key" or "credential" references
- [ ] Confirm export files are not world-readable
  - File permissions verified: 600 or 640 (owner read/write only)
- [ ] Verify database credentials not exposed
  - Database password NOT in application logs
  - Database password NOT in error messages
- [ ] Confirm no sensitive data in error messages
  - Test with invalid export directory (should show path, not credentials)
  - Test with database connection error (should not expose password)

---

## 8. Deployment-Day Smoke Test

✓ **Test plan prepared**  
OPERATOR EXECUTES ON DEPLOYMENT DAY:

### Pre-Deployment (5 minutes)
```bash
# 1. Confirm code is deployed
git log --oneline -1
# Should show: docs: Phase 3-Step 7 - v1.1 Release Closure Complete

# 2. Confirm export directory
ls -l /path/to/export/directory
# Should be readable and writable

# 3. Confirm database
sqlite3 givebutter.db "SELECT COUNT(*) FROM batches;"
# Should return 0 or existing batch count
```

### Application Startup (2 minutes)
```bash
# 1. Start application
flask run --port=8000

# 2. Verify startup (no errors in logs)
# Check logs for: "WARNING" or "ERROR" messages
# None should be present

# 3. Test basic connectivity
curl http://localhost:8000/
# Should return HTTP 200
```

### Workflow Smoke Tests (15 minutes)

**Test 1: Upload & Validation**
- [ ] Navigate to upload page
- [ ] Upload sample CSV (5-10 records)
- [ ] Verify validation queue shows items
- [ ] Mark one as valid, save
- [ ] Verify decision appears in audit trail
- [ ] No errors in logs

**Test 2: Review Queues**
- [ ] Normalization queue: accept one suggestion
- [ ] Duplicate queue: mark one as "different person"
- [ ] Household queue: confirm one grouping
- [ ] Verify all decisions in audit trail
- [ ] No errors in logs

**Test 3: Readiness & Export**
- [ ] Check readiness dashboard
- [ ] Verify status is correct (ready or blocked)
- [ ] Generate export
- [ ] Verify CSV file created in export directory
- [ ] Download export file
- [ ] Verify file is readable
- [ ] No errors in logs

**Test 4: Security Spot-Check**
- [ ] Verify HTTPS is enforced (no HTTP access)
- [ ] Check logs: no "API" or "credential" references
- [ ] Verify export file has correct permissions (not world-readable)
- [ ] Check database logs: no password exposed
- [ ] No unexpected external API calls

**Expected Result:** All tests pass, zero errors in logs.

---

## 9. Rollback Triggers & Procedure

### Rollback If:

**CRITICAL — Rollback immediately:**
- Security vulnerability discovered (external API calls, credentials exposed)
- Data corruption detected (unexpected mutations, deletions)
- Uncontrollable error rate (>10% of requests failing)
- Audit trail not logging decisions
- Export files not being created
- Database connection failures
- Users unable to complete basic workflows

**HIGH — Rollback within 1 hour:**
- Workflow failures (import failures, decision saving failures)
- Performance issues (batch processing >5 min for 100 items)
- Export files created with incorrect permissions

### Rollback Procedure

**Step 1: Stop Access (5 min)**
```bash
# 1. Notify users: "System temporarily unavailable for maintenance"
# 2. Redirect traffic away from production
# 3. Document rollback start time
```

**Step 2: Restore Previous Version (10 min)**
```bash
# 1. Checkout previous commit
git checkout 9912fb3  # Phase 3-Step 6

# 2. Restore database from backup
# (specific command depends on backup method)

# 3. Restart application
flask run --port=8000

# 4. Verify application starts (no errors in logs)
```

**Step 3: Verify (5 min)**
```bash
# 1. Run smoke tests from previous version
# 2. Confirm all workflows working
# 3. Verify audit trail intact
# 4. Check for data loss (should be none)
```

**Step 4: Communicate**
```
Notify stakeholders: "Temporary issue resolved, investigating"
Provide status update: "System restored, investigating root cause"
ETA for next attempt: [date/time]
```

**Step 5: Investigate**
```
- Analyze logs from failed deployment
- Identify root cause
- Plan fix or remediation
- Create deployment remediation document
- Test fix locally before retry
```

---

## 10. Post-Deployment Monitoring Checklist

### Week 1 — Daily Checks

- [ ] **Daily:** Check application error logs (target: zero critical errors)
- [ ] **Daily:** Verify audit trail logging all decisions
- [ ] **Daily:** Verify export files being created correctly
- [ ] **Daily:** Check support requests (respond to issues)
- [ ] **Daily:** Verify no external API calls attempted

### Weeks 2-4 — 2-3x Per Week

- [ ] Check application error rate (target: <1% errors)
- [ ] Verify audit trail completeness (all decisions logged)
- [ ] Monitor export functionality (users successfully exporting)
- [ ] Track support requests and feedback
- [ ] Verify no external API calls attempted
- [ ] Monitor disk space (export directory growth)
- [ ] Verify database backups completing

### End of Week 4 — Roadmap Decision

- [ ] Compile all user feedback (issues, feature requests)
- [ ] Analyze usage patterns (batch sizes, decision types, users)
- [ ] Evaluate demand for bulk actions (>20% of batches?)
- [ ] Evaluate demand for concurrent user features (>30% multi-user?)
- [ ] Make v1.2 feature commitments
- [ ] Document findings in retrospective

---

## 11. Support/User Communication Checklist

### Before Going Live

- [ ] **PRE-DEPLOYMENT:** Schedule stakeholder briefing
  - Explain export-only model
  - Explain known limitations
  - Explain manual CRM upload required
  - Confirm deployment date/time

- [ ] **PRE-DEPLOYMENT:** Prepare user communication
  - Release announcement email with deployment time
  - Link to release notes (V1_1_RELEASE_NOTES.md)
  - Link to user guides (EXPORT_ONLY_WORKFLOW.md)
  - Link to known limitations (V1_1_KNOWN_LIMITATIONS.md)
  - Support contact information

- [ ] **PRE-DEPLOYMENT:** Notify support team
  - Training on v1.1 features
  - Review export-only model
  - Review known limitations
  - Define escalation procedures
  - Prepare FAQ responses

### Deployment Day

- [ ] **BEFORE GOING LIVE:** Send "deployment window" notification (if applicable)
- [ ] **AFTER GOING LIVE:** Send "v1.1 is live" announcement
  - Link to release notes
  - Link to user guides
  - Support contact information
  - Explanation of what changed (P0 fixes, readiness dashboard)
  - Explanation of what's NOT in v1.1 (bulk actions, CRM sync)

### Post-Deployment (Weeks 1-4)

- [ ] **WEEK 1:** Share feedback form (ask about usability, bulk actions, CRM integration)
- [ ] **WEEKLY:** Update support team with common issues
- [ ] **WEEKLY:** Document edge cases discovered
- [ ] **WEEK 4:** Compile feedback for v1.2 roadmap decisions

---

## 12. Guardrails That Must Not Change

These 15 hard guardrails are locked in for v1.1. Do not implement any of these without explicit stakeholder approval and planning for v2.0+:

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

**If a user requests any of these features, respond:**
> "This is deferred to v1.2 or v2.0+ pending user demand validation and business approval. We're collecting feedback post-launch to prioritize future work."

---

## 13. Final Go/No-Go Checklist

### Code & Tests
- [x] All 1202 tests passing (verified today)
- [x] Zero regressions from baseline
- [x] All critical workflows verified
- [x] All security tests passing
- [x] All data safety guarantees confirmed
- [x] All 15 hard guardrails maintained

### Documentation
- [x] Release notes complete and accurate
- [x] User workflow guide complete
- [x] Reviewer workflow guide complete
- [x] Known limitations documented
- [x] Deployment plan documented

### Operator Tasks (Must Complete Before Deploying)
- [ ] Export directory created and verified writable
- [ ] Database backups scheduled and tested
- [ ] HTTPS/network/security configured
- [ ] Support team briefed and ready
- [ ] User communication prepared
- [ ] Rollback plan reviewed and understood
- [ ] Smoke-test plan reviewed and understood

### Final Go/No-Go Decision
- [ ] All code-level items checked (above)
- [ ] All operator tasks completed (above)
- [ ] All guardrails understood and locked in
- [ ] Ready to deploy

**If all items above are checked: GO FOR DEPLOYMENT**

**If any items are unchecked: DO NOT DEPLOY** (address first)

---

## References

Detailed source documents:
- `V1_1_RELEASE_NOTES.md` — What changed, what's deferred
- `V1_1_KNOWN_LIMITATIONS.md` — 15 limitations with rationale
- `V1_1_RELEASE_CHECKLIST.md` — Comprehensive pre-release verification
- `V1_1_DEPLOYMENT_EXECUTION.md` — Deployment execution details
- `V1_1_DEPLOYMENT_READINESS_COMPLETION_RECORD.md` — Verification status
- `EXPORT_ONLY_WORKFLOW.md` — User workflow guide
- `REVIEWER_WORKFLOW.md` — Reviewer decision guide

---

## Support

**If issues arise during deployment:**

1. Check smoke-test plan (section 8) for verification steps
2. Check rollback triggers (section 9) to see if rollback is needed
3. Check support communication (section 11) for known questions
4. If critical issue: execute rollback procedure (section 9)
5. Document issue and contact engineering team

**Post-Deployment Support:**
- Monitor logs daily (section 10)
- Respond to user feedback (section 11)
- Track feature requests for v1.2 roadmap (section 10)

---

## Version

**Householder v1.1**  
**Release Date:** 2026-06-13  
**Status:** Ready for operator deployment  
**Baseline:** 1202 tests passing, zero regressions

**All code-level requirements met. Ready for operator handoff.**

