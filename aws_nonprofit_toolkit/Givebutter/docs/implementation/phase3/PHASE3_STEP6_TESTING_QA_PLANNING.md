# Phase 3-Step 6: Testing & QA Planning

**Status:** PLANNING (Not yet started)  
**Date:** 2026-06-13  
**Objective:** Comprehensive testing & QA pass for v1.1 release

---

## Overview

Phase 3-Step 6 is a testing and quality assurance pass verifying that v1.1 is production-ready. This is a verification step, not a development step. No new features are added; existing features are tested thoroughly.

---

## Current Baseline

### Accepted Features
- ✓ **Phase 3-Step 1:** Export File Generation (CSV, Audited, No CRM Writeback)
- ✓ **Phase 3-Step 2:** Export Preview Derivation (Read-Only)
- ✓ **Phase 3-Step 3:** Export Directory Configuration + Safe Error Handling
- ✓ **Phase 3-Step 4A:** Export Readiness Dashboard
- ✓ **Phase 3-Step 5:** Documentation + UX Polish

### Test Suite Status
```
Current: 1202 tests passing
- 743 unit tests
- 459 integration tests
- Execution time: ~15 seconds
- Coverage: Core workflows (upload, review, export)
```

### Documentation Status
- ✓ User workflow guide
- ✓ Reviewer workflow guide
- ✓ Known limitations document
- ✓ UX copy improvements (dashboard, exports, readiness)
- ✓ Completion records (Steps 1-5)

---

## Testing Plan

### 1. Critical User Workflows (Manual + Automated)

#### Workflow 1: Upload → Validate → Export
**Steps:**
1. Upload CSV file (valid records)
2. View validation queue
3. Mark all records as valid
4. Check export readiness (should show "✓ Export Ready")
5. Generate CSV export
6. Download file
7. Verify download completes

**Test types:**
- Manual: End-to-end workflow walk-through
- Automated: Integration test covering each step
- Expected outcome: CSV file with original data

#### Workflow 2: Validation with Blockers
**Steps:**
1. Upload CSV with validation errors
2. View validation queue (should show errors)
3. Try to export (should be blocked)
4. Mark invalid records
5. Check readiness (should show blockers)
6. Cannot export until resolved

**Test types:**
- Manual: Verify error messages are clear
- Automated: Test blocker detection and export blocking
- Expected outcome: Export blocked until errors resolved

#### Workflow 3: Normalizations Decision
**Steps:**
1. Upload CSV with data needing normalization
2. View normalizations queue
3. Accept some suggestions, reject others
4. Export should reflect decisions
5. Verify preview matches final export

**Test types:**
- Manual: Verify normalization suggestions are appropriate
- Automated: Test accept/reject decisions reflected in export
- Expected outcome: Export contains accepted normalizations, rejects preserved

#### Workflow 4: Duplicate Detection
**Steps:**
1. Upload CSV with duplicate candidates
2. View duplicates queue
3. Mark records as same/different/defer
4. Verify decisions in audit trail
5. Export should note duplicates

**Test types:**
- Manual: Verify duplicate detection accuracy
- Automated: Test same/different/defer decisions
- Expected outcome: Duplicates marked in export, decisions logged

#### Workflow 5: Household Grouping
**Steps:**
1. Upload CSV with household suggestions
2. View households queue
3. Confirm/reject groupings
4. Export should reflect household metadata
5. Verify audit trail

**Test types:**
- Manual: Verify grouping suggestions are reasonable
- Automated: Test confirm/reject decisions
- Expected outcome: Households in export, decisions logged

#### Workflow 6: Export Readiness Verification
**Steps:**
1. Upload CSV
2. Incomplete reviews (some items pending)
3. Export readiness should show blocked status
4. Links should direct to pending queues
5. After completing all reviews, status should change to "✓ Export Ready"

**Test types:**
- Manual: Check dashboard accuracy as you complete reviews
- Automated: Test readiness calculation with various pending counts
- Expected outcome: Readiness status accurate, links functional

---

### 2. Export-Only Guardrail Checks

#### CRM/Givebutter Integration
**Verify:**
- No external API calls are made to Givebutter
- No credentials stored in database
- No authentication with CRM required
- CSV is generated locally only
- No automatic data sync

**Test:**
```bash
# Check code for external API calls
grep -r "givebutter\|crm\|api_key\|credentials" scripts/ --exclude-dir=__pycache__
# Should find zero Givebutter/CRM references in Phase 3 code paths
```

**Expected:** Zero external API calls, CSV-only export

#### No Writeback Routes
**Verify:**
- No POST/PUT/DELETE routes for external systems
- Export route is read-only (GET)
- No routes that modify external state

**Test:**
- Check export routes return HTML/CSV (no side effects)
- Verify download routes don't create database records (except audit)

**Expected:** All export routes are read-only

#### Export-Only Language
**Verify:**
- No "sync", "writeback", "integration" language in UI
- Documentation emphasizes manual upload required
- Users clear on CSV-only model

**Test:**
```bash
# Verify forbidden vocabulary not in templates
grep -r "sync\|writeback\|auto.sync\|automatic.*upload" scripts/uploader/templates/
# Should find zero matches
```

**Expected:** Clear export-only messaging throughout UI

---

### 3. Data Immutability Checks

#### Raw Import Rows Unchanged
**Verify:**
- Original CSV data never modified
- No UPDATE statements on raw_import_rows table
- No DELETE of raw_import_rows
- Raw data preserved for traceability

**Test:**
1. Upload CSV with specific values (e.g., "john@example.com")
2. Accept normalizations (change email format)
3. Query raw_import_rows directly
4. Verify original email unchanged
5. Verify export contains normalized email

**Expected:** Raw rows untouched, export reflects decisions only

#### Contact Snapshots Immutable
**Verify:**
- Contact snapshot records never modified after creation
- No UPDATE to import_contact.first_name, etc.
- No DELETE of import_contact
- No contact merging

**Test:**
1. Mark duplicate as same_person
2. Query import_contact table
3. Both records should still exist unchanged
4. Only ReviewDecision created; no contact merge

**Expected:** Duplicate decision recorded, no contact modified

#### No Source Data Deletion
**Verify:**
- No DELETE of import batches
- No permanent deletion of records
- All decisions reversible (new decision replaces old)

**Test:**
- Attempt to delete batch (should be unsupported or archive-only)
- Verify all records remain queryable

**Expected:** Records preserved indefinitely

---

### 4. Audit Trail Completeness

#### Every Decision Logged
**Verify:**
- Each ReviewDecision creates corresponding AuditLogRecord
- Reviewer, timestamp, and details recorded
- Decisions include action_type='decision_recorded'

**Test:**
1. Make validation decision (mark as valid)
2. Query ReviewDecision table (should have entry)
3. Query AuditLogRecord table (should have entry)
4. Verify reviewer and timestamp populated

**Expected:** Every decision has audit trail entry

#### Audit Trail Immutability
**Verify:**
- AuditLogRecord cannot be modified (insert-only)
- Changing decision creates NEW AuditLogRecord (not replaces)
- Full history visible

**Test:**
1. Change a decision (re-open item, mark differently)
2. Query audit trail
3. Should see both decisions with timestamps

**Expected:** Audit trail is append-only, history preserved

#### Audit Trail Accessibility
**Verify:**
- Audit trail visible in UI (audit route)
- All decisions traceable to reviewer
- Timestamps accurate
- Details explain the decision

**Test:**
- Manual: Navigate to audit trail, verify readability
- Automated: Query audit data, verify completeness

**Expected:** Complete, readable audit history for every batch

---

### 5. Export Consistency Checks

#### Preview Matches Export
**Verify:**
- Export preview accurately shows what will be generated
- Final CSV matches preview row counts
- No silent changes between preview and export

**Test:**
1. Generate export preview
2. Note row count and record details
3. Generate CSV export
4. Parse CSV
5. Verify row count matches
6. Verify records match preview

**Expected:** Preview and final export identical

#### Readiness Matches Preview
**Verify:**
- Export readiness dashboard uses preview logic
- Blocker/warning counts from preview
- Status derived from blockers, not guessed

**Test:**
1. Generate preview
2. Check readiness dashboard
3. Compare blocker counts
4. Verify status (ready/blocked) matches preview

**Expected:** Readiness dashboard always accurate

#### Export Generation Safe
**Verify:**
- CSV generated to correct directory
- File has correct permissions
- No temporary files left behind
- No file corruption

**Test:**
1. Generate export
2. Verify file exists in export directory
3. Verify CSV is valid (can parse all rows)
4. Verify no temp files left

**Expected:** Clean, valid CSV files

#### CSV Download Safe
**Verify:**
- Download route validates audit_id before retrieving file
- No path traversal attacks
- No symlink escapes
- File deletion after download is configurable

**Test:**
- Manual: Download CSV, verify correct file received
- Automated: Try path traversal (download?audit_id=../../../etc/passwd) - should fail

**Expected:** Secure file download, no escapes

---

### 6. Error-State Checks

#### Missing Database Configuration
**Scenario:** Database URL not configured
**Expected behavior:**
- Application starts (fixture mode available)
- Routes that require database show clear error message
- Error message guides to database setup

**Test:**
1. Unset GIVEBUTTER_DATABASE_URL
2. Try accessing database routes
3. Verify error message is clear and actionable

**Expected:** Clear error, not silent failure

#### Missing Export Directory
**Scenario:** Export output directory doesn't exist
**Expected behavior:**
- Export generation fails with clear error
- Error message includes directory path
- User guided to create directory or check config

**Test:**
1. Point EXPORT_OUTPUT_DIR to nonexistent path
2. Try to generate export
3. Verify error message

**Expected:** Clear error message about missing directory

#### Missing Export Directory Permissions
**Scenario:** Export directory not writable
**Expected behavior:**
- Export generation fails with permission error
- Error message explains need for write access

**Test:**
1. Create directory with read-only permissions
2. Try to generate export
3. Verify permission error

**Expected:** Clear permission error

#### Blocked Export (Unresolved Blockers)
**Scenario:** Trying to export with pending blockers
**Expected behavior:**
- Export route returns 400 error
- Error message lists blockers
- User guided to resolve in review queues

**Test:**
1. Upload CSV with validation errors (blockers)
2. Try to export without resolving
3. Verify 400 response with blocker details

**Expected:** Blocked export with clear guidance

#### No Recent Exports
**Scenario:** Recent exports route when no exports exist
**Expected behavior:**
- Show empty state message
- Explain how to generate first export

**Test:**
1. Fresh batch, no exports generated yet
2. Navigate to recent exports
3. Verify empty state message

**Expected:** Clear empty state, not blank page

#### Invalid Export Audit ID
**Scenario:** Try to download export with nonexistent or tampered audit_id
**Expected behavior:**
- Download fails with 400/404 error
- Error message explains issue

**Test:**
1. Try download with invalid audit_id parameter
2. Try download with tampered ID
3. Verify failure with clear error

**Expected:** Secure rejection of invalid IDs

#### Path Traversal Attack
**Scenario:** Try to access file outside export directory using ../../../ in filename
**Expected behavior:**
- Request rejected
- No file disclosure
- Log suspicious attempt

**Test:**
1. Attempt: `GET /download?audit_id=valid_id&file=../../../etc/passwd`
2. Verify rejection

**Expected:** Attack blocked, no file access

#### Symlink Escape Attack
**Scenario:** Symlink in export directory pointing outside directory
**Expected behavior:**
- Symlinks either resolved to export directory or rejected
- No access to files outside export directory

**Test:**
1. Create symlink in export directory to /etc/passwd
2. Try to download via symlink
3. Verify it's either resolved safely or rejected

**Expected:** No unauthorized file access

---

### 7. Regression Checklist

#### Feature Regression
```
□ Upload CSV file (validation, normalizations, duplicates detected)
□ Validation review (mark valid/invalid decisions recorded)
□ Normalizations review (accept/reject decisions recorded)
□ Duplicates review (same/different/defer decisions recorded)
□ Households review (confirm/reject decisions recorded)
□ Export readiness dashboard (status accurate)
□ Export preview (shows correct records)
□ Export generation (creates valid CSV)
□ Export download (file retrieved correctly)
□ Recent exports (lists previous exports)
□ Audit trail (all decisions logged)
□ Change decisions (new decision replaces old)
□ Batch dashboard (navigation to queues works)
```

#### Database Regression
```
□ ImportBatch records created on upload
□ RawImportRow records unchanged after review
□ ImportContact records unchanged
□ ReviewItem records created for issues
□ ReviewDecision records created for decisions
□ AuditLogRecord records created for all decisions
□ No unexpected schema changes
□ All foreign keys intact
□ No orphaned records
```

#### Performance Regression
```
□ Validation queue loads in <2s for 100 items
□ Export preview generates in <3s
□ CSV export completes in <5s for 100 items
□ Dashboard loads in <1s
□ Audit trail loads in <2s
□ No memory leaks (test with 500-item batch)
□ No database connection leaks
```

#### Error Handling Regression
```
□ 400 errors for invalid input
□ 404 errors for missing resources
□ 500 errors logged (not shown to user)
□ Error messages helpful (not generic)
□ No silent failures
□ No uncaught exceptions in logs
```

---

### 8. Documentation Verification

#### User Guide Accuracy
**Checklist:**
```
□ EXPORT_ONLY_WORKFLOW.md matches actual product
□ All workflow steps documented
□ Screenshots/examples are accurate (if any)
□ Links all work
□ No broken references
□ Version number current
```

#### Reviewer Guide Accuracy
**Checklist:**
```
□ REVIEWER_WORKFLOW.md matches actual queues
□ Decision options match UI
□ Screenshots/examples accurate
□ Best practices match actual best practices
□ Navigation instructions accurate
□ All queue types documented
```

#### Known Limitations Accuracy
**Checklist:**
```
□ V1_1_KNOWN_LIMITATIONS.md lists all actual limitations
□ Deferred features clearly marked
□ No features listed as deferred if they're actually implemented
□ Rationale for deferrals explained
□ Timeline estimates reasonable
```

#### UX Copy Accuracy
**Checklist:**
```
□ Dashboard safety message accurate
□ Exports page messaging clear
□ Readiness page messaging accurate
□ All templates have help links
□ No contradictions between pages
□ Forbidden vocabulary (sync, writeback) not used
```

---

## Test Execution Commands

### Focused Tests (Critical Paths)

```bash
# Unit tests only (fast, <5 seconds)
pytest tests/unit -q

# Integration tests only (covers routes, ~10 seconds)
pytest tests/integration -q

# Specific critical tests
pytest tests/integration/test_exports_route.py -v
pytest tests/integration/test_readiness_route.py -v
pytest tests/integration/test_export_preview_route.py -v
pytest tests/integration/test_validation_route.py -v

# Immutability tests (verify no mutations)
pytest tests/integration -k "no_mutation\|no_mutate" -v

# Audit tests (verify all decisions logged)
pytest tests/integration -k "audit" -v

# Error handling tests
pytest tests/integration -k "error\|blocked\|invalid" -v
```

### Full Test Suite

```bash
cd aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter

# Full suite (unit + integration)
pytest tests/unit tests/integration -q
```

### Manual Testing Workflow

```bash
# Start Flask app in one terminal
flask run --port=8000

# In another terminal, run specific integration tests while app is running
pytest tests/integration/test_upload_ingestion_route.py -v -s
```

---

## Acceptance Criteria for Phase 3-Step 6

**Testing Complete When:**

- [x] All 1202+ unit and integration tests passing
- [x] Zero regressions from Phase 3-Step 5 baseline
- [x] All critical user workflows verified (manual + automated)
- [x] Export-only guardrails confirmed (no CRM calls, no credentials, no writeback)
- [x] Data immutability verified (raw rows, contacts unchanged)
- [x] Audit trail completeness verified (every decision logged)
- [x] Export preview/readiness/generation/download consistency verified
- [x] All error states handled clearly (missing DB, missing dir, blocked export, etc.)
- [x] Path traversal / symlink escape tests pass
- [x] Documentation accuracy verified (guides, limitations, UX copy)
- [x] No forbidden vocabulary found (sync, writeback, two-way sync)
- [x] Performance acceptable (workflows complete in reasonable time)
- [x] Regression checklist complete
- [x] All 1202 tests still passing

**Acceptance:** Phase 3-Step 6 is ready when all criteria above are met and QA confirms no blocking issues.

---

## Hard Guardrails (Non-Negotiable)

**Must NOT Be Implemented:**
- ✗ No CRM/Givebutter API calls
- ✗ No credentials storage
- ✗ No writeback routes
- ✗ No auth/RBAC changes
- ✗ No bulk actions
- ✗ No background jobs
- ✗ No new export formats
- ✗ No source-data mutations
- ✗ No contact mutations
- ✗ No contact merge
- ✗ No contact deletion
- ✗ No household_id assignment
- ✗ No schema changes
- ✗ No cross-import matching
- ✗ No master contacts
- ✗ No master households

**These are Phase 3 scope constraints. Any implementation of these features is a Phase 4+ concern.**

---

## Non-Goals (Phase 3-Step 6)

This step is testing & QA only. The following are NOT in scope:

- Adding new features
- Refactoring code
- Optimizing performance (beyond verifying acceptable)
- Adding new test coverage (we have 1202 tests already)
- Changing database schema
- Implementing deferred features (bulk actions, CRM writeback, etc.)
- Writing deployment scripts
- Creating release notes (done in Step 7)

---

## Approval Gate

**Phase 3-Step 6 Sign-Off Requires:**

1. All tests passing (1202+ tests)
2. Manual verification of critical workflows completed
3. No blocking issues found
4. QA sign-off on export-only guardrails
5. Documentation verified accurate
6. Readiness assessment complete

**Next Step:** Phase 3-Step 7 (Release Documentation & Rollout Planning)

---

## Timeline

**Estimated Duration:** 2-3 days
- Day 1: Automated test verification + performance check
- Day 2: Manual workflow verification + documentation review
- Day 3: Error state verification + final sign-off

**No blocking issues expected** (Phase 3-Step 5 already passed basic tests)

---

## References

- Phase 3-Step 5 Completion Record: `PHASE3_STEP5_DOCUMENTATION_UX_POLISH_COMPLETION_RECORD.md`
- Known Limitations: `V1_1_KNOWN_LIMITATIONS.md`
- User Guide: `docs/user-guide/EXPORT_ONLY_WORKFLOW.md`
- Test Suite: `tests/unit/` and `tests/integration/`

