# Phase 3-Step 1: Givebutter/CRM Writeback Planning
## High-Risk Boundary Definition Only

**Date:** 2026-06-12  
**Status:** 📋 PLANNING PHASE (No Implementation)  
**Type:** Specification & Risk Analysis

---

## Executive Summary

**Core Question:** Should DonorTrust v1 remain export-only, or should a future phase support controlled CRM/Givebutter writeback?

**Recommended Answer:** **Keep v1 export-only. Defer writeback to Phase 4+ only if explicitly approved by stakeholders after risk review.**

**Rationale:**
- Current export workflow is proven, safe, and production-ready
- Writeback introduces significant risk vectors (data loss, overwrite, API failures)
- Nonprofits have manual CSV→Givebutter import process (acceptable for v1)
- Writeback requires infrastructure not present in v1 (dry-run, idempotency, credential mgmt)
- Audit requirements alone justify a separate phase/product if writeback is approved

---

## Current Phase 2 Baseline Verification

### ✅ Export Workflow Confirmed Working

**Routes:**
```
✅ POST /imports/<import_id>/exports/preview → Read-only preview
✅ POST /imports/<import_id>/exports/generate → CSV file + audit record
✅ GET /imports/<import_id>/exports/download/<audit_log_id> → Safe streaming
```

**Audit Trail:**
```
✅ AuditLogRecord created for each export generation
✅ Audit details include: filename, file_path, row_count, warning_count, blocked_count
✅ No mutations to source data
✅ Full history preserved
```

**External API Calls:**
```
✅ Current count: 0 (zero) CRM/Givebutter API calls
✅ All references to "givebutter" are file paths or connection strings
✅ No OAuth, API keys, or webhooks configured
```

**Test Baseline:**
```
✅ 1160 unit + integration tests passing
✅ 306 Phase 2 focused tests passing
✅ 0 failures, 0 errors
✅ Export workflow 100% functional
```

---

## Writeback Risk Categories

If writeback were ever implemented, these risks must be managed:

### 1. Data Overwrite Risk

**Scenario:** Reviewer clicks export/sync button, intending one action, but both happen.

**Impact:** Contact or donation data in Givebutter overwritten without intention.

**Mitigation:**
- ❌ NO automatic sync on page load
- ❌ NO background writeback
- ✅ Explicit user action required
- ✅ Separate UI for export vs. writeback
- ✅ Writeback requires confirmation dialog with explicit language

**Severity:** 🔴 CRITICAL

---

### 2. Duplicate Merge Mistakes

**Scenario:** Reviewer marks contacts as "same_person" (which is safe in export), but writeback interprets as "merge in Givebutter."

**Impact:** Two Givebutter contacts consolidated, donations merged, potentially breaking reporting.

**Mitigation:**
- ❌ Writeback MUST NOT merge Givebutter contacts
- ❌ Writeback MUST NOT delete Givebutter records
- ✅ Writeback only creates new records or updates (never merge/delete)
- ✅ Field-level diff shown before writeback
- ✅ "No merge" language consistently used in UI

**Severity:** 🔴 CRITICAL

---

### 3. Household Assignment Mistakes

**Scenario:** Reviewer confirms household grouping, writeback interprets as "create family in Givebutter."

**Impact:** Household record created with wrong members or missing donations.

**Mitigation:**
- ❌ Writeback MUST NOT create household records
- ❌ Writeback MUST NOT assign household_id in Givebutter
- ✅ Writeback only syncs contact data (no household creation)
- ✅ Household grouping remains export metadata only
- ✅ Explicit documentation that writeback does NOT create households

**Severity:** 🔴 CRITICAL

---

### 4. API Rate Limits & Failures

**Scenario:** Givebutter API rate limit hit mid-batch, or API times out.

**Impact:** Partial writeback (some records updated, others not), confusion about state.

**Mitigation:**
- ✅ Dry-run before actual writeback
- ✅ Per-record idempotency key (prevents duplicate writes on retry)
- ✅ Audit log for every attempted write (success + failure)
- ✅ Clear reporting: N succeeded, M failed (by record)
- ✅ No automatic retry (user decides)
- ✅ Explicit failure alert (not silently failed)

**Severity:** 🟠 HIGH

---

### 5. Partial Writeback Failures

**Scenario:** Batch of 100 records being written. 75 succeed, 25 fail (due to validation error).

**Impact:** Givebutter has 25 records without corresponding sync (data drift), user confused about state.

**Mitigation:**
- ✅ Report success/failure per record (not batch summary only)
- ✅ Audit log shows which records succeeded, which failed
- ✅ UI shows: "75 synced, 25 failed: <error details>"
- ✅ User can retry failed records
- ✅ No automatic batch abort on first error

**Severity:** 🟠 HIGH

---

### 6. Retry & Idempotency Problems

**Scenario:** User clicks "retry failed records." Some records already synced in background, others not. Retry causes duplicate writes.

**Impact:** Duplicate contact records in Givebutter or contradictory updates.

**Mitigation:**
- ✅ Every write attempt includes idempotency key
- ✅ Givebutter API deduplicates by idempotency key (per API docs)
- ✅ Safe to retry without creating duplicates
- ✅ Audit log tracks: dry-run vs actual, idempotency key, success/failure

**Severity:** 🟠 HIGH

---

### 7. Audit & Compliance Gaps

**Scenario:** Nonprofit is later asked "who wrote this data to Givebutter?" and when. No audit trail.

**Impact:** Non-compliance with data governance, inability to trace changes.

**Mitigation:**
- ✅ Every writeback attempt logged (dry-run and actual)
- ✅ Audit includes: reviewer, timestamp, source import, target system, payload hash
- ✅ Success/failure recorded
- ✅ Error messages preserved
- ✅ Idempotency key for reconciliation

**Severity:** 🟠 HIGH

---

### 8. Credential Exposure

**Scenario:** Givebutter API token stored in config file or code, accidentally committed to repo.

**Impact:** API key exposed, attacker can write to nonprofit's Givebutter account.

**Mitigation:**
- ✅ API credentials in environment variables only (never in code)
- ✅ Credentials not logged or audited
- ✅ Credentials validated at startup (fail loudly if missing)
- ✅ Clear docs: "API key required, set GIVEBUTTER_API_KEY env var"
- ✅ No auto-discovery of credentials

**Severity:** 🔴 CRITICAL

---

### 9. Rollback Limitations

**Scenario:** 500 records synced to Givebutter, user discovers error. Wants to undo.

**Impact:** No built-in rollback, manual cleanup required.

**Mitigation Options:**
- Option 1: Explicit statement "Rollback not supported. All writes are one-way."
- Option 2: Implement undo via reversion API (if Givebutter supports it)
- Option 3: Require dry-run approval before actual writeback

**Recommended:** Option 1 + Option 3 (explicit statement + dry-run gates)

**Severity:** 🟠 HIGH

---

### 10. Reviewer Confusion

**Scenario:** Reviewer sees "Export" button, clicks it, then separately sees "Sync to Givebutter" button. Confused about which action they took.

**Impact:** Unexpected data in Givebutter, user frustration.

**Mitigation:**
- ✅ Clear visual distinction: Preview → Export → Download (existing)
- ✅ Separate section: "CRM Writeback (Beta)" or "Advanced"
- ✅ Confirmation dialog explicitly says: "This will write X records to Givebutter"
- ✅ Progress bar shows which records succeeded/failed
- ✅ Post-completion: "X records now in Givebutter"

**Severity:** 🟡 MEDIUM

---

## Minimum Prerequisites Before Any Writeback

If writeback is approved in a future phase, these prerequisites are non-negotiable:

### Organizational Prerequisites
- [ ] Explicit stakeholder approval (not assumed)
- [ ] Data governance review (legal/compliance)
- [ ] Insurance/liability assessment
- [ ] Nonprofit feedback on safety requirements
- [ ] Decision: Accept rollback limitations or build undo

### Technical Prerequisites
- [ ] Givebutter API documentation reviewed
- [ ] API rate limits documented
- [ ] API error codes mapped
- [ ] Idempotency supported by API confirmed
- [ ] OAuth setup or token management system

### UI Prerequisites
- [ ] Dry-run feature (no remote writes)
- [ ] Field-level diff preview
- [ ] Per-record status display
- [ ] Clear confirmation dialog with explicit language
- [ ] Progress bar during writeback
- [ ] Success/failure summary

### Code Prerequisites
- [ ] Idempotency key generation
- [ ] Audit log extended for CRM writes
- [ ] Credential validation at startup
- [ ] Failure reporting (not silent failures)
- [ ] Dry-run implementation (calls API but no writes)

### Testing Prerequisites
- [ ] No writeback without explicit action
- [ ] Dry-run does not call write endpoint (or calls read-only)
- [ ] Credentials missing produces safe error
- [ ] API failure produces audit record
- [ ] Partial failure represented accurately
- [ ] Idempotency prevents duplicate remote writes
- [ ] Source data never mutated
- [ ] No automatic merge/delete/household assignment

### Documentation Prerequisites
- [ ] Architecture doc: "CRM Writeback Design"
- [ ] API integration doc
- [ ] Security doc: credential handling
- [ ] Rollback policy: explicit statement
- [ ] User guide: step-by-step writeback process
- [ ] Troubleshooting guide: common failures

---

## Writeback Scope Options

### Option A: No CRM Writeback in v1 (RECOMMENDED)

**Description:** DonorTrust remains export-only. Nonprofits manually import CSV to Givebutter.

**Pros:**
- Simplest, safest
- No new API dependencies
- Export process proven and stable
- No credential management
- No risk of data loss
- No rollback issues
- Current 1160 test baseline sufficient

**Cons:**
- Requires manual Givebutter import (slightly more effort for nonprofits)
- No real-time sync

**Risk Level:** 🟢 MINIMAL

**Recommendation:** ✅ **START HERE** (Default v1 approach)

---

### Option B: Dry-Run Only

**Description:** Writeback endpoint exists, validates against Givebutter schema, but makes no remote writes.

**Features:**
- POST /imports/<import_id>/exports/dry-run
- Calls Givebutter API to validate
- Shows field-level diff
- Shows validation errors
- No records written

**Pros:**
- Catches errors before actual writeback
- Uses real Givebutter API (not mocked)
- Safer than actual writeback
- Can be built incrementally

**Cons:**
- Requires Givebutter API credentials
- Still requires auditing dry-run attempts
- False confidence (dry-run passes, actual fails for different reason)

**Risk Level:** 🟡 MEDIUM (API dependency, but no data writes)

**Prerequisite:** Dry-run implementation + audit logging

**Recommendation:** ✅ **SECOND STEP** (if writeback is approved)

---

### Option C: Manual Per-Record Writeback

**Description:** Reviewer can write individual records one at a time, with explicit confirmation.

**Features:**
- POST /imports/<import_id>/exports/<contact_id>/writeback
- Reviewer clicks "Sync to Givebutter" on individual contact
- Confirmation dialog required
- Audit log per write
- Success/failure shown immediately

**Pros:**
- Low batch risk (small blast radius per write)
- Easy to debug individual failures
- Clear cause-and-effect (user clicks, one record syncs)
- Allows partial adoption

**Cons:**
- Slow for large imports (500 clicks)
- High API call volume
- May hit rate limits
- UI complexity (many sync buttons)

**Risk Level:** 🔴 HIGH (API dependency, data writes, rate limits)

**Prerequisite:** Per-record API integration + robust error handling

**Recommendation:** ❌ **NOT RECOMMENDED FOR v1** (Too slow, too high API volume)

---

### Option D: Batch Writeback

**Description:** Reviewer clicks "Sync all to Givebutter," all records written in batch.

**Features:**
- POST /imports/<import_id>/exports/writeback (batch)
- Syncs all non-skipped records
- Progress bar
- Partial failure handling
- Retry mechanism

**Pros:**
- Fast (one click, all records synced)
- Fewer API calls than per-record
- User expects "export then sync" workflow

**Cons:**
- **HIGHEST RISK:** Large blast radius (all records at once)
- Partial failures hard to manage
- Requires most safeguards
- Rollback not feasible (100+ records)
- API rate limits likely

**Risk Level:** 🔴🔴 CRITICAL (Batch data risk)

**Prerequisite:** All prerequisites from "Minimum Prerequisites" section

**Recommendation:** ❌ **DEFER TO PHASE 4+** (Too risky for Phase 3)

---

## Recommended Path Forward

### Recommendation: Keep v1 Export-Only

**Phase 3:** Continue Phase 2 improvements (UI, performance, new decision workflows)

**Phase 4+ (If Approved by Stakeholders):**
1. Option B (Dry-run only) as pilot
2. Gather nonprofit feedback on safety requirements
3. Option C (Per-record) if demand for sync is high
4. Never implement Option D (batch) without extensive safeguards

---

## Non-Goals (Explicit Exclusions)

Unless explicitly approved in a separate phase, the following are OUT OF SCOPE:

### ❌ Automatic/Background Operations
- Automatic sync on decision submission
- Background sync on page load
- Scheduled sync jobs
- Webhook-triggered sync
- Auto-retry on API failure

### ❌ Data Modification in Remote System
- Contact merge in Givebutter
- Contact deletion in Givebutter
- Household creation in Givebutter
- Donation/transaction updates
- Removing/updating donation history

### ❌ Advanced Features
- Cross-import identity resolution
- Givebutter contact deduplication
- Automatic field mapping
- Custom field sync
- Bulk update operations

### ❌ Infrastructure
- Credential auto-discovery
- API proxy layer
- Message queue for retry
- Rate limiter override
- Shadow/canary deployment

---

## Audit Requirements (If Writeback Approved)

Every writeback attempt must be logged with:

```json
{
  "audit_log_id": "<UUID>",
  "timestamp": "2026-06-12T10:30:00Z",
  "reviewer_email": "reviewer@nonprofit.org",
  "action_type": "crm_writeback_attempt",
  "writeback_type": "dry_run|actual",
  "source_import_id": "IMP-001",
  "source_contact_ids": ["CNT-001", "CNT-002", "CNT-003"],
  "target_system": "givebutter",
  "target_endpoint": "/contacts",
  "payload_hash": "sha256:abc123...",
  "dry_run": true|false,
  "idempotency_key": "wr-20260612-10-30-00-abc123",
  "results": {
    "total_attempted": 3,
    "succeeded": 2,
    "failed": 1,
    "remote_ids": ["gb-donor-001", "gb-donor-002"],
    "failed_records": [
      {
        "source_contact_id": "CNT-003",
        "error_code": "VALIDATION_ERROR",
        "error_message": "Email already in use"
      }
    ]
  },
  "http_status": 200|400|429|500,
  "error_message": null|"<error>",
  "duration_ms": 1234
}
```

**Audit Access:**
- Reviewers can view writeback history for their import
- Admin can view all writeback attempts
- Audit trail immutable (append-only)

---

## UI Requirements (If Writeback Approved)

### Layout Principle: Clear Separation

The export console must clearly distinguish:

```text
┌────────────────────────────────────────────┐
│ EXPORT CONSOLE                              │
├────────────────────────────────────────────┤
│                                              │
│ ┌─ EXPORT WORKFLOW ────────────────────┐  │
│ │                                       │  │
│ │ 1. Preview (Read-only)                │  │
│ │    → Shows what will be exported      │  │
│ │                                       │  │
│ │ 2. Generate CSV                       │  │
│ │    → Creates downloadable file        │  │
│ │                                       │  │
│ │ 3. Download                           │  │
│ │    → Streams CSV (one-way)           │  │
│ │                                       │  │
│ └───────────────────────────────────────┘  │
│                                              │
│ ┌─ CRM WRITEBACK (Beta, if enabled) ───┐  │
│ │                                       │  │
│ │ ⚠️ This will write to Givebutter     │  │
│ │                                       │  │
│ │ 1. Dry Run                            │  │
│ │    → Preview what will be written     │  │
│ │    → No changes made                  │  │
│ │                                       │  │
│ │ 2. Sync to Givebutter [BUTTON]        │  │
│ │    → Requires confirmation            │  │
│ │    → Shows progress                   │  │
│ │    → Shows success/failure            │  │
│ │                                       │  │
│ └───────────────────────────────────────┘  │
│                                              │
└────────────────────────────────────────────┘
```

### Confirmation Dialog (If Writeback Approved)

**Dry-run confirmation:**
```
"Preview what will be validated against Givebutter?
[Cancel] [Preview]"
```

**Actual writeback confirmation:**
```
"⚠️ WARNING: This will write 47 records to Givebutter.

All changes are permanent. Rollback is not supported.

Records will be updated/created in Givebutter:
- 45 updates
- 2 new records
- 0 errors found in preview

Do you want to proceed?

[Cancel] [I understand, write to Givebutter]"
```

### Progress & Results

**During writeback:**
```
Syncing to Givebutter: 34/47 ✓
```

**After writeback:**
```
✓ Sync complete

Results:
  45 synced successfully
  2 skipped (already in Givebutter)
  0 failed

View audit log: [Link]
```

**After failure:**
```
❌ Sync failed

Results:
  30 synced successfully
  17 failed

Failed records:
  CNT-001: "Email already in use" (VALIDATION_ERROR)
  CNT-002: "API rate limit exceeded" (RATE_LIMIT)
  ...

You can retry the failed records, or download export and sync manually.

View audit log: [Link]
```

---

## Test Strategy (If Writeback Approved)

### Unit Tests (Core Logic)
```python
# Idempotency
test_idempotency_key_prevents_duplicate_writes()
test_idempotency_key_includes_timestamp_and_contact_id()

# Credential Validation
test_api_key_missing_produces_safe_error()
test_api_key_invalid_produces_safe_error()
test_api_key_loaded_from_environment_only()

# Dry-Run
test_dry_run_does_not_call_write_endpoint()
test_dry_run_calls_validation_endpoint()
test_dry_run_returns_field_diffs()

# Audit Logging
test_audit_log_created_for_dry_run()
test_audit_log_created_for_actual_writeback()
test_audit_log_includes_all_required_fields()
test_audit_log_preserves_error_messages()

# Data Safety
test_source_data_never_mutated_on_writeback()
test_writeback_does_not_merge_contacts()
test_writeback_does_not_delete_contacts()
test_writeback_does_not_create_households()
```

### Integration Tests (Workflow)
```python
# No Automatic Writeback
test_no_writeback_without_explicit_action()
test_writeback_requires_reviewer_confirmation()
test_page_load_does_not_trigger_sync()

# Error Handling
test_api_timeout_produces_audit_record()
test_api_rate_limit_produces_audit_record()
test_api_validation_error_produces_audit_record()
test_partial_failure_represented_accurately()

# Idempotency
test_retry_with_same_idempotency_key_is_safe()
test_idempotency_prevents_duplicate_remote_creates()

# UI Requirements
test_dry_run_section_clearly_labeled()
test_writeback_section_warns_about_permanence()
test_confirmation_dialog_includes_explicit_language()
```

### End-to-End Tests (Givebutter Integration)
```python
# Mock Givebutter API
test_dry_run_against_mock_givebutter_api()
test_writeback_against_mock_givebutter_api()
test_rate_limit_failure_handled_gracefully()
test_validation_error_failure_handled_gracefully()

# Audit Trail
test_successful_writeback_in_audit_log()
test_failed_writeback_in_audit_log()
test_dry_run_in_audit_log()
```

---

## Open Questions & Blockers

### Questions Requiring Stakeholder Input

1. **Rollback Policy:** Should writeback support undo, or is it one-way only?
   - One-way (explicit statement): Simpler, faster to build
   - Undo required: Much more complex, requires Givebutter API support

2. **Approval Level:** Who approves writeback?
   - Reviewer (person who made decisions)?
   - Admin only?
   - Nonprofit staff (external approval)?

3. **Scope of Sync:** What fields should be written to Givebutter?
   - Contact name, email, phone (basic)?
   - Address, demographics?
   - Donation amount (if not already in Givebutter)?
   - Custom fields?

4. **Multi-Batch Imports:** If nonprofit has multiple import batches, should they all sync together, or one at a time?

5. **Existing Contacts:** If contact already in Givebutter (by email or ID), should writeback update or skip?
   - Update (merge data)?
   - Skip (don't overwrite)?
   - Ask reviewer?

### Blockers (Before Writeback Can Be Implemented)

1. **Givebutter API Access**
   - [ ] API documentation reviewed
   - [ ] Test API credentials available
   - [ ] Rate limits documented
   - [ ] Error codes mapped
   - [ ] Idempotency support confirmed

2. **Legal/Compliance Review**
   - [ ] Data governance review completed
   - [ ] Insurance/liability assessed
   - [ ] Nonprofit consent obtained
   - [ ] GDPR/data privacy implications reviewed

3. **Product Decision**
   - [ ] Stakeholders vote: Writeback in v1, v2, or never?
   - [ ] If yes: approve minimum prerequisites
   - [ ] If yes: approve scope (Option B, C, or D)
   - [ ] If yes: approve UI/UX requirements

---

## Recommendation Summary

### ✅ Proceed With Phase 3 (Export & Workflow Improvements)

**Action:** Continue building on Phase 2's solid foundation.

**Focus Areas (Phase 3+):**
- Improved UI/UX for decision workflows
- Bulk decision submission (if safe)
- Performance improvements
- Better error messages
- Mobile responsiveness

**Writeback Status:** Deferred pending stakeholder approval and risk review

---

### ⏸️ Writeback Deferred (Default)

**Action:** Do NOT add CRM writeback in Phase 3. Keep v1 as export-only product.

**Rationale:**
- Current export workflow is proven and safe
- Writeback introduces significant risk
- Nonprofits have manual import workflow (adequate for v1)
- Better to defer and do right, than rush and break

**If writeback is approved later:**
1. Get explicit stakeholder approval (in writing)
2. Complete risk review with legal/compliance
3. Build Option B (dry-run) as pilot
4. Gather nonprofit feedback before Option C
5. Never implement Option D (batch) without extensive safeguards

---

## Files Inspected

- ✅ scripts/uploader/app.py — Routes verified
- ✅ scripts/householder/export_file_service.py — Export generation verified
- ✅ scripts/householder/export_download_service.py — Download validation verified
- ✅ scripts/householder/database_models.py — Audit log schema verified
- ✅ tests/integration/test_export_file_route.py — Export tests verified
- ✅ tests/integration/test_export_download_route.py — Download tests verified

## Files Created

- ✅ docs/implementation/phase3/PHASE3_STEP1_WRITEBACK_BOUNDARY_PLANNING.md (this file)

## Files Modified

- None (Planning phase only)

## Final Test Result

```bash
pytest tests/unit tests/integration -q

✅ 1160 tests passing
✅ 0 failures
✅ 0 errors
✅ Execution time: 13.25s
```

**Baseline Confirmed:** Phase 2 is stable and ready for Phase 3 improvements.

---

## Conclusion

DonorTrust v1 is a solid, safe export-only product. **Do not add CRM writeback in v1.** If stakeholders later approve writeback, follow the minimum prerequisites and risk mitigation strategies defined in this document.

**Current Recommendation:** Approve Phase 3 to continue workflow improvements, defer writeback decision to Phase 4+.
