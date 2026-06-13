# Phase 3-Step 2: Export-Only Product Improvement Planning

**Date:** 2026-06-12  
**Status:** 📋 PLANNING PHASE (No Implementation)  
**Type:** UX/Product Specification

---

## Executive Summary

**Current State:** Phase 2 complete, v1 is export-only and production-ready (1160 tests, 0 external API calls).

**Opportunity:** Safe, high-ROI improvements to reviewer usability and audit visibility without adding CRM writeback.

**Recommendation:** Prioritize in order: P0 (UI clarity) → P1 (export readiness dashboard) → P2 (error states) → P3 (bulk actions).

---

## Current Accepted Baseline

### ✅ Phase 2 Complete
- 4 decision workflows (validation, normalization, duplicate, household)
- 4 export workflows (preview, generate, download, recent)
- 1160 tests passing
- 0 external API calls
- Full audit trail

### ✅ Current Templates Verified

| Template | Status | Current Features |
|----------|--------|------------------|
| dashboard.html | ✅ Works | 4 queue cards, audit link, export link |
| validation.html | ✅ Works | Search, filter, status badges, modal |
| normalizations.html | ✅ Works | Accept/reject UI, notes |
| duplicates.html | ✅ Works | Side-by-side comparison |
| households.html | ✅ Works | Grouping visualization |
| exports.html | ✅ Works | Preview status, generate button, recent exports |
| audit.html | ✅ Works | Full audit log table |

### ✅ Current Routes All Working
```
GET  /imports/<id>/dashboard
GET  /imports/<id>/validation
GET  /imports/<id>/normalizations
GET  /imports/<id>/duplicates
GET  /imports/<id>/households
GET  /imports/<id>/exports
POST /imports/<id>/exports/preview
POST /imports/<id>/exports/generate
GET  /imports/<id>/exports/download/<id>
GET  /imports/<id>/audit
```

---

## 1. Reviewer Workflow Usability Analysis

### Current State Evaluation

**✅ What Works Well:**
- Status badges clearly distinguish pending/accepted/dismissed/deferred
- Search filters help find records
- Modal inspection provides detailed decision interface
- Sticky action bar visible at all times
- Back to dashboard button available

**⚠️ Usability Gaps Found:**

#### Gap 1: "Latest Decision Wins" Behavior Not Visible
**Issue:** If reviewer submits decision → changes mind → submits new decision, which one is shown?

**Current:** Second decision wins (correct), but not obvious in UI.

**Improvement:** Add "(Latest)" label to active decision in modal.

**Risk:** 🟢 NONE (display only)

#### Gap 2: Deferred Items Not Prioritized
**Issue:** Deferred items sink to bottom of list, making them easy to forget.

**Improvement:** Add "Deferred" filter option that shows only deferred items, separate section on dashboard showing deferred count.

**Risk:** 🟢 NONE (read-only)

#### Gap 3: Notes Stored But Not Visible in List
**Issue:** Reviewer can add notes during decision submission, but notes aren't visible in table view.

**Current:** Notes visible only in modal after opening record.

**Improvement:** Add "Notes" column or icon (💬) in table showing "has notes" indicator.

**Risk:** 🟢 NONE (display only)

#### Gap 4: Decision Labels Could Be Clearer
**Current Labels:**
- Validation: "accept_issue" / "dismiss_issue" / "defer"
- Normalization: "accept_normalization" / "reject_normalization" / "defer"
- Duplicate: "same_person" / "different_people" / "defer"
- Household: "confirm_household" / "reject_household" / "defer"

**Evaluation:** Labels are safe (no mutation language), clear enough.

**Recommendation:** Keep as-is. No changes needed.

#### Gap 5: Export Blockers Not Visible in Review Queues
**Issue:** Reviewer is reviewing validation issues, doesn't know some are export blockers.

**Current:** Only visible in export console.

**Improvement:** Add "(Blocks export)" badge to blocker records in validation table.

**Risk:** 🟢 NONE (display only)

#### Gap 6: Navigation Between Queues Is Slow
**Issue:** To review all queues, must: click validation → finish → back to dashboard → click normalizations → etc.

**Current:** Dashboard has 4 links, reviewer must use back button.

**Improvement:** Add breadcrumb or queue navigator showing "Validation → Normalizations → Duplicates → Households".

**Risk:** 🟢 NONE (display only)

---

## 2. Export Readiness Dashboard Proposal

### Current State

**What Exists:** Export console shows preview status (blocked/ready) + counts.

**Gap:** No single place shows "what must be done before export is ready?"

### Proposed: Export Readiness Dashboard Card

**Location:** Export console (before "Generate CSV Export" section)

**Content (Read-Only):**

```
┌─ EXPORT READINESS SUMMARY ──────────────────────┐
│                                                   │
│ Validation Issues: ✓ 0 blocking, 3 warnings      │
│   Actions:                                        │
│     • 15 accepted and resolved                    │
│     • 3 warnings noted (non-blocking)             │
│     • 2 issues deferred for later                 │
│                                                   │
│ Normalizations: ✓ All reviewed                    │
│   Actions:                                        │
│     • 42 accepted suggestions applied             │
│     • 8 rejected suggestions (kept original)      │
│     • 3 deferred for later                        │
│                                                   │
│ Duplicate Pairs: ✓ All reviewed                   │
│   Actions:                                        │
│     • 5 marked as same_person (grouped)           │
│     • 18 marked as different_people               │
│     • 2 pairs deferred                            │
│                                                   │
│ Household Groupings: ✓ All reviewed               │
│   Actions:                                        │
│     • 12 confirmed groupings                      │
│     • 8 rejected groupings                        │
│     • 1 deferred                                  │
│                                                   │
│ EXPORT READY: ✓ Yes                               │
│   Last export: 2026-06-12 10:30 (47 records)      │
│   Download: [Link to latest CSV]                  │
│                                                   │
│ ⓘ All source data remains unchanged in system    │
│                                                   │
└─────────────────────────────────────────────────┘
```

**Implementation Details:**
- Read-only (no mutations)
- Derived from existing audit log
- Shows summary per decision type
- Shows what user must do to unblock
- Shows last export if exists
- Shows export readiness status

**Risk:** 🟢 NONE (read-only derivation)

**Example Code Path:**
```python
def get_export_readiness_summary(import_id: str, config: dict) -> dict:
    # Query audit log for all decision types
    # Count accepted/rejected/deferred per type
    # Determine if export is ready (no blockers)
    # Return summary dict for template
    # NO MUTATIONS
```

---

## 3. Bulk-Safe Decision Helpers Analysis

### Evaluated Actions

#### ✅ SAFE: Bulk Defer Selected Items

**What:** Reviewer selects multiple items, clicks "Defer Selected", all get defer decision.

**Why Safe:**
- Defer is lowest-commitment decision
- No data modification in export
- Can be changed later by submitting new decision
- Latest-decision-wins makes it reversible

**Impact:** Time-saver for "I'll come back to these later"

**Recommendation:** ✅ **IMPLEMENT IN PHASE 3**

**Implementation Effort:** Small (10 lines UI + form handler)

**Risk:** 🟢 NONE

---

#### ✅ SAFE: Bulk Dismiss Advisory Validation Issues

**What:** Reviewer selects multiple "advisory" (non-blocking) issues, clicks "Dismiss These", all get dismiss decision.

**Why Safe:**
- Only advisory issues (warnings, not blockers)
- Dismiss is reversible (can submit accept later)
- No export data changed

**Impact:** Time-saver for "these warnings don't concern us"

**Recommendation:** ✅ **IMPLEMENT IN PHASE 3**

**Implementation Effort:** Medium (20 lines UI + form handler)

**Risk:** 🟢 NONE (advisory only)

**Caveat:** Must show explicit warning: "This applies to advisory issues only. Blocking issues must be resolved individually."

---

#### ✅ SAFE: Bulk Reject Low-Confidence Normalizations

**What:** Reviewer sees normalizations with <50% confidence, clicks "Reject Low-Confidence", all rejected.

**Why Safe:**
- Only affects normalization queue (not merge/delete)
- Rejection keeps original value (safe)
- Reversible (can accept later)

**Impact:** Time-saver for "I don't trust these suggestions"

**Recommendation:** ✅ **IMPLEMENT IN PHASE 3**

**Implementation Effort:** Small (15 lines UI + filter logic)

**Risk:** 🟢 NONE

---

#### ❌ NOT SAFE: Bulk Accept Normalizations

**Why Not Safe:**
- Automatically accepts without review
- Could silently apply unwanted transformations
- If reviewer clicks bulk accept, unaware of specific changes
- Best practice: accept intentionally per-item or per-type

**Recommendation:** ❌ **DO NOT IMPLEMENT**

---

#### ❌ NOT SAFE: Bulk Mark Duplicates as Same Person

**Why Not Safe:**
- "Same person" creates grouping in export
- Applying without detailed review risks wrong grouping
- Affects final export data
- Could be misinterpreted as "merge" (even though it's not)

**Recommendation:** ❌ **DO NOT IMPLEMENT**

---

#### ❌ NOT SAFE: Bulk Confirm Households

**Why Not Safe:**
- Same reason as duplicates
- Could accidentally confirm wrong groupings
- Affects final export data

**Recommendation:** ❌ **DO NOT IMPLEMENT**

---

### Bulk Actions Summary

| Action | Safe? | Recommendation | Effort | Risk |
|--------|-------|-----------------|--------|------|
| Bulk defer selected | ✅ YES | Implement P1 | S | 🟢 None |
| Bulk dismiss advisory | ✅ YES | Implement P1 | M | 🟢 None |
| Bulk reject low-conf norm | ✅ YES | Implement P1 | S | 🟢 None |
| Bulk accept normalizations | ❌ NO | Skip | — | 🔴 High |
| Bulk mark duplicates | ❌ NO | Skip | — | 🔴 High |
| Bulk confirm households | ❌ NO | Skip | — | 🔴 High |

---

## 4. Audit Visibility Improvements

### Current State

**What Exists:** Audit page shows all records as table with action_type, timestamp, user, status.

**Gaps:**
- No filtering by action_type
- No grouping by decision workflow
- Reviewer notes not visible in audit log view
- No filtering by status (accepted/rejected/deferred)
- No summary of "what happened this session"

### Proposed Improvements

#### ✅ IMPROVEMENT: Audit Filters

**Add Filters:**
```
Filter by:
  [ ] Action Type (validation_decision, normalization_decision, etc.)
  [ ] Status (pending, accepted, rejected, deferred)
  [ ] Reviewer Email
  [ ] Date Range
  
[ ] Include export generation events
```

**Risk:** 🟢 NONE (read-only filtering)

**Effort:** Medium

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### ✅ IMPROVEMENT: Audit Summary View

**Add "Session Summary" card before table:**

```
┌─ THIS SESSION ──────────────────┐
│                                  │
│ Session: 2026-06-12 10:00-11:30 │
│ Reviewer: alice@nonprofit.org    │
│                                  │
│ Decisions Made:                  │
│  • 15 validation decisions       │
│    - 8 accepted                  │
│    - 3 dismissed                 │
│    - 4 deferred                  │
│                                  │
│  • 12 normalization decisions    │
│    - 10 accepted                 │
│    - 2 rejected                  │
│                                  │
│  • 8 duplicate decisions         │
│    - 3 same_person               │
│    - 5 different_people          │
│                                  │
│  • 7 household decisions         │
│    - 5 confirmed                 │
│    - 2 rejected                  │
│                                  │
│ Exports Generated: 2             │
│  • 2026-06-12 11:00 (47 rows)    │
│  • 2026-06-12 11:15 (47 rows)    │
│                                  │
└──────────────────────────────────┘
```

**Risk:** 🟢 NONE (read-only aggregation)

**Effort:** Medium

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### ✅ IMPROVEMENT: Show Reviewer Notes in Audit

**Current:** Notes stored in audit.details, not displayed.

**Proposed:** Add "Notes" column to audit table (or expand notes in details row).

**Example:**
```
Timestamp | Action Type | Reviewer | Details | Notes | Status
---
2026-06-12 10:05 | validation_decision | alice@nonprofit.org | ID-042 | "Email invalid but legacy donor, keeping as-is" | accepted
```

**Risk:** 🟢 NONE (read-only display)

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### ✅ IMPROVEMENT: Audit Search

**Add:** Full-text search for reviewer names, notes, record IDs.

**Risk:** 🟢 NONE (read-only search)

**Effort:** Medium

**Recommendation:** ✅ **IMPLEMENT P2**

---

---

## 5. Error & Empty-State Improvements

### Current Gaps

#### Gap 1: Missing Database Config

**Current:** Silent failure or vague error.

**Proposed Message:**
```
❌ Database not configured

This application requires a SQLite database.

Configuration:
  Set environment variable: GIVEBUTTER_DATABASE_URL
  
  Example:
    export GIVEBUTTER_DATABASE_URL="sqlite:///./givebutter.db"
    
Or modify: scripts/householder/database_models.py

Contact: [link to docs]
```

**Risk:** 🟢 NONE (UX improvement)

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P0**

---

#### Gap 2: Missing Export Directory

**Current:** File generation fails silently or with cryptic error.

**Proposed Message:**
```
❌ Export directory not configured or missing

The application cannot write generated CSV files.

Configuration:
  Set environment variable: EXPORT_OUTPUT_DIR
  
  Example:
    export EXPORT_OUTPUT_DIR="/tmp/givebutter/exports"
    
Directory must:
  • Exist and be writable
  • Have at least 100MB free
  • Not be a symlink (security)
  
Contact: [link to docs]
```

**Risk:** 🟢 NONE (UX improvement)

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P0**

---

#### Gap 3: No Review Items

**Current:** Empty table with no guidance.

**Proposed:** 

**If batch has 0 review items:**
```
✓ All records processed

No validation issues, normalizations, duplicates, or
households to review.

You can proceed directly to export if desired.

[Go to Export]
```

**If all items already decided:**
```
✓ All review items completed

Every validation issue, normalization, duplicate, and
household has a decision recorded.

You can proceed to export.

[Go to Export]
```

**Risk:** 🟢 NONE (UX improvement)

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### Gap 4: Export Blocked - What To Do?

**Current:** Shows blockers list, but not clear how to fix.

**Proposed Enhancement:**

```
❌ Export Blocked — 3 unresolved validation issues

You must resolve these before generating export:

1. Record IMP-042: Email missing (CRITICAL)
   → Go to [Validation Review] and accept or dismiss

2. Record IMP-055: Phone format invalid (CRITICAL)
   → Go to [Validation Review] and accept or dismiss

3. Record IMP-067: Amount missing (CRITICAL)
   → Go to [Validation Review] and accept or dismiss

[Go to Validation Review]
```

**Risk:** 🟢 NONE (UX improvement)

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### Gap 5: Missing Generated File on Download

**Current:** 404 error, not user-friendly.

**Proposed Message:**

```
❌ Export file not found

The export file that was generated is no longer available
(may have been deleted).

You can regenerate the export:
  [Go to Export Console]
  
Or download a previous export:
  [View Recent Exports]
```

**Risk:** 🟢 NONE (UX improvement)

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### Gap 6: Malformed Decision Payload

**Current:** Silent fail or cryptic error.

**Proposed:** 

```
⚠️ Decision not saved — invalid data

The decision you submitted had invalid data:
  Missing field: decision_value
  
This usually means:
  • Form was modified by browser extension
  • JavaScript error prevented form submission
  • Browser cache issue
  
Try:
  1. Close this page
  2. Go back to [Import Dashboard]
  3. Try reviewing this item again
  4. If error persists, [contact support]
```

**Risk:** 🟢 NONE (UX improvement)

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P2**

---

---

## 6. Documentation Improvements

### Current Gap
**No operator documentation exists.**

### Proposed Docs

#### Doc 1: SETUP.md (New)

**Contents:**
```markdown
# DonorTrust v1 Setup Guide

## Requirements
- Python 3.14+
- SQLite 3.x
- 500MB disk space

## Installation

### 1. Environment Setup
export GIVEBUTTER_DATABASE_URL="sqlite:///./givebutter.db"
export EXPORT_OUTPUT_DIR="/tmp/givebutter/exports"

### 2. Database Initialization
python scripts/householder/database_models.py

### 3. Run Development Server
flask run --port=5000

## Configuration
[Detailed config guide]

## Troubleshooting
[Common issues]
```

**Effort:** Medium

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### Doc 2: REVIEWER_GUIDE.md (New)

**Contents:**
```markdown
# Reviewer Guide: Making Decisions

## Workflow Overview
1. Upload CSV to DonorTrust
2. Review validation issues
3. Review normalizations
4. Review duplicates
5. Review households
6. Generate export
7. Download CSV
8. Import to Givebutter (manually)

## Understanding Decisions

### Validation Decisions
- Accept issue: Mark as addressed
- Dismiss issue: Acknowledge but keep original data
- Defer: Come back to later

### Normalization Decisions
- Accept: Apply suggested field transformation
- Reject: Keep original field value
- Defer: Decide later

### Duplicate Decisions
- Same person: Group contacts in export
- Different people: Keep separate in export
- Defer: Decide later

### Household Decisions
- Confirm: Group in export
- Reject: Keep separate in export
- Defer: Decide later

## Important Notes
- NO AUTOMATIC MERGE: Decisions group in export, don't modify Givebutter
- NO DATA LOSS: Original data remains unchanged
- REVERSIBLE: Can change any decision by submitting a new one
- AUDITED: All decisions logged

## Tips & Tricks
- Use bulk defer to save time
- Filter by status to find pending items
- Check audit log to see decision history
```

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### Doc 3: OPERATOR_GUIDE.md (New)

**Contents:**
```markdown
# Operator Guide: Running DonorTrust

## Daily Operations

### Start Application
```bash
source .venv/bin/activate
export GIVEBUTTER_DATABASE_URL="sqlite:///./givebutter.db"
export EXPORT_OUTPUT_DIR="/tmp/givebutter/exports"
flask run --port=5000
```

### Monitor Health
```bash
pytest tests/unit tests/integration -q
```

### Backup Data
```bash
sqlite3 givebutter.db ".dump" > givebutter_backup.sql
```

## Troubleshooting

### Application won't start
1. Check database exists
2. Check export directory exists
3. Check Python version (3.14+)
4. Run tests to see specific error

### Reviewer can't download export
1. Check EXPORT_OUTPUT_DIR is writable
2. Check file exists in directory
3. Check audit log for generation status
4. Check database for export record

### Tests failing
1. Run: pytest tests/unit tests/integration -q
2. If specific test fails, run with -v flag
3. Check test output for details

## Rollback & Recovery

### If generation fails
- No files created
- No audit records created
- Reviewer can retry

### If download fails
- File still on disk
- Reviewer can retry download
- Can manually copy file and provide

### Manual recovery
- All decisions are in audit log
- Can re-export from audit log if needed
- Source data never modified

```

**Effort:** Medium

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### Doc 4: ARCHITECTURE.md (Update)

**Contents:** (Already exists, needs minor updates)
```markdown
# DonorTrust v1 Architecture

[Existing content]

## Explicit Non-Goals

This is an export-only product. The following are NOT implemented:

- ❌ CRM/Givebutter writeback
- ❌ Contact merge
- ❌ Automatic approval
- ❌ Authentication/RBAC
- ❌ Background jobs
- ❌ Data synchronization

See PHASE3_STEP1_WRITEBACK_BOUNDARY_PLANNING.md for risk analysis
and why these are deferred.
```

**Effort:** Small

**Recommendation:** ✅ **IMPLEMENT P1**

---

---

## 7. Performance & Scale Review

### Load Scenarios

#### Scenario 1: Large CSV Import (50,000 records)

**Current Behavior:**
- Database handles 50K records easily (SQLite)
- Preview generation might be slow (N+1 query risk)
- Export CSV generation might take seconds

**Risk Assessment:**
- Low risk (batch job, not user-facing)
- No UI freezes
- Test with real data

**Recommendation:** Monitor, optimize if needed P2

---

#### Scenario 2: Many Review Decisions (10,000+ decisions)

**Current Behavior:**
- Audit log appends efficiently
- Decision status derivation uses indexed queries
- UI table pagination needed

**Risk Assessment:**
- Low risk for stored data
- Medium risk for status derivation (no caching)

**Optimization:** Add pagination to decision tables in P2

---

#### Scenario 3: Recent Exports Query

**Current Code:**
```python
def get_recent_exports(import_id: str):
    session.query(AuditLogRecord).filter_by(
        batch_id=import_id,
        action_type='export_generated'
    ).order_by(action_timestamp.desc()).all()
```

**Risk:** Unbounded query (all exports for import).

**Recommendation:** Limit to last 50 exports (safe cutoff).

**Effort:** Tiny (add .limit(50))

**Risk:** 🟢 NONE

---

#### Scenario 4: Status Derivation Queries

**Current:** Get effective status from review_decisions table for each record.

**Risk:** If table has 10,000+ decisions, could be slow.

**Recommendation:** Profile with real data, add indexes if needed.

**Effort:** Medium (add database indexes)

**Risk:** 🟢 LOW (safe optimization)

---

### Performance Recommendations

| Scenario | Current Risk | Recommendation | Effort | Priority |
|----------|--------------|-----------------|--------|----------|
| 50K record import | 🟢 Low | Monitor | None | P2 |
| 10K+ decisions | 🟡 Medium | Add pagination | M | P2 |
| Recent exports unbounded | 🟡 Medium | Add .limit(50) | S | P1 |
| Status derivation | 🟡 Medium | Profile + index | M | P2 |

---

## 8. UI Design Finalization

### Current State

**What Works:**
- Color scheme consistent (green=success, red=error, blue=pending)
- Status badges clear and readable
- Modal design for inspection
- Tables responsive enough

**What Could Improve:**
- Dashboard cards could show progress bars
- Export readiness status card is minimal
- Some pages missing empty states
- Decision labels could have icons/color coding

### Proposed Improvements

#### ✅ IMPROVEMENT: Dashboard Progress Bars

**Current:**
```
Validation Review: 47 issues
```

**Proposed:**
```
Validation Review
Progress: 42/47 reviewed (89%)
[████████░] 42/47 reviewed
```

**Effort:** Small

**Risk:** 🟢 NONE

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### ✅ IMPROVEMENT: Decision Status Icons

**Add icons to status badges:**
- Pending: ⏳ (hourglass)
- Accepted: ✓ (checkmark)
- Dismissed: ✗ (x)
- Deferred: ⊙ (circle)

**Effort:** Tiny

**Risk:** 🟢 NONE

**Recommendation:** ✅ **IMPLEMENT P1**

---

#### ✅ IMPROVEMENT: Color-Coded Decision Labels

**Decision type gets icon/color:**
- Validation: Red (issues)
- Normalization: Blue (suggestions)
- Duplicate: Green (grouping)
- Household: Purple (grouping)

**Effort:** Small

**Risk:** 🟢 NONE

**Recommendation:** ✅ **IMPLEMENT P2**

---

#### ✅ IMPROVEMENT: Export Readiness Card Enhancement

**Add:**
- Large green/red status indicator
- Progress bar (N blockers, M warnings)
- Link to "Go resolve blockers"

**Effort:** Medium

**Risk:** 🟢 NONE

**Recommendation:** ✅ **IMPLEMENT P1**

---

### No SPA Migration

**Decision:** Do NOT migrate to React/SPA.

**Rationale:**
- Flask/Jinja sufficient for current complexity
- No benefit for v1 export-only workflow
- Could defer to v2 if needed

**Stick with:** Flask + Jinja + Vanilla JS + CSS

---

---

## 9. Explicit Non-Goals

### ❌ Out of Scope for Phase 3

- CRM/Givebutter writeback (defer to Phase 4+)
- Background/async jobs
- Authentication/RBAC
- Automatic decision approval
- Contact merge
- Household creation
- Cross-import identity matching
- New export formats (defer to Phase 4)
- React/SPA migration
- Mobile app
- API endpoint for external integrations

### ✅ In Scope for Phase 3

- Reviewer UX improvements
- Audit visibility
- Error messaging
- Documentation
- Safe bulk actions
- Performance optimization
- Dashboard enhancements
- Export readiness clarity

---

## Prioritized Implementation Roadmap

### Priority Levels

| P0 | Critical UX | Implement immediately | Must-have for usability |
| P1 | High value | Implement in Phase 3 | Core improvements |
| P2 | Nice to have | Defer to Phase 3.5+ | Polish |
| P3 | Low value | Defer to Phase 4+ | Future enhancement |

---

### P0: Critical Fixes (Do First)

| Item | Description | Effort | Risk | Recommendation |
|------|-------------|--------|------|---|
| Missing DB config message | Show helpful error if database not configured | S | 🟢 None | ✅ DO IMMEDIATELY |
| Missing export dir message | Show helpful error if export dir missing | S | 🟢 None | ✅ DO IMMEDIATELY |
| Recent exports limit | Add .limit(50) to avoid unbounded query | S | 🟢 None | ✅ DO IMMEDIATELY |
| Blocked export messaging | Clearer "what to do" if export blocked | S | 🟢 None | ✅ DO IMMEDIATELY |

---

### P1: High-Value Improvements (Phase 3 Main)

| Item | Description | Effort | Risk | Recommendation |
|------|-------------|--------|------|---|
| Export readiness dashboard | Summary card showing what's resolved/pending | M | 🟢 None | ✅ IMPLEMENT |
| Audit filters & summary | Filter by action type, show session summary | M | 🟢 None | ✅ IMPLEMENT |
| Bulk defer action | Select items, defer all at once | M | 🟢 None | ✅ IMPLEMENT |
| Bulk dismiss advisory | Dismiss non-blocking validation issues in bulk | M | 🟢 None | ✅ IMPLEMENT |
| Bulk reject low-conf norm | Reject low-confidence normalizations in bulk | S | 🟢 None | ✅ IMPLEMENT |
| Dashboard progress bars | Show % reviewed per queue | S | 🟢 None | ✅ IMPLEMENT |
| Decision status icons | Add visual indicators (✓, ✗, ⏳, ⊙) | S | 🟢 None | ✅ IMPLEMENT |
| Error state improvements | Friendly messages for all errors | M | 🟢 None | ✅ IMPLEMENT |
| Setup documentation | Installation & configuration guide | M | 🟢 None | ✅ IMPLEMENT |
| Reviewer guide | How to make decisions | S | 🟢 None | ✅ IMPLEMENT |
| Operator guide | How to run & troubleshoot | M | 🟢 None | ✅ IMPLEMENT |
| Export readiness card | Enhanced UI for readiness status | M | 🟢 None | ✅ IMPLEMENT |
| Latest decision wins visual | Show "(Latest)" on active decision | S | 🟢 None | ✅ IMPLEMENT |
| Blocker badges in review | Mark export-blocking items | S | 🟢 None | ✅ IMPLEMENT |
| Deferred item filter | Separate section for deferred items | S | 🟢 None | ✅ IMPLEMENT |
| Notes visibility | Add notes column/indicator to tables | S | 🟢 None | ✅ IMPLEMENT |

**P1 Total Effort:** ~4 weeks (distributed across features)

---

### P2: Polish & Optimization (Phase 3.5+)

| Item | Description | Effort | Risk | Recommendation |
|------|-------------|--------|------|---|
| Color-coded decision labels | Icons/colors per decision type | S | 🟢 None | DEFER |
| Audit full-text search | Search notes & record IDs | M | 🟢 None | DEFER |
| Malformed payload message | Better error for invalid submissions | S | 🟢 None | DEFER |
| Pagination for large lists | Handle 10K+ decisions | M | 🟢 None | DEFER |
| Database indexing | Optimize queries | M | 🟢 None | DEFER |
| Queue navigator breadcrumb | Quick jump between decision types | M | 🟢 None | DEFER |
| Status derivation caching | Cache effective status | M | 🟡 Low | DEFER |

---

### P3: Future Enhancements (Phase 4+)

| Item | Description | Effort | Risk | Recommendation |
|------|-------------|--------|------|---|
| CRM writeback support | Integration with Givebutter (deferred) | L | 🔴 High | DEFER TO PHASE 4+ |
| New export formats | JSON, XML options | M | 🟡 Medium | DEFER TO PHASE 4+ |
| Cross-import matching | Detect duplicates across imports | L | 🔴 High | DEFER TO PHASE 4+ |
| Background export job | Async generation | M | 🟡 Medium | DEFER TO PHASE 4+ |

---

---

## Recommended Phase 3 Roadmap

### Phase 3-Step 3: P0 Critical Fixes
**Effort:** 1-2 days  
**Contains:** 4 quick-hit error message improvements + 1 query limit

### Phase 3-Step 4: P1 Export Readiness & Bulk Actions
**Effort:** 1.5 weeks  
**Contains:** Dashboard, bulk actions, audit visibility

### Phase 3-Step 5: P1 Documentation & UX Polish
**Effort:** 1.5 weeks  
**Contains:** Setup/reviewer/operator guides, error states, UI enhancements

### Phase 3-Step 6: Testing & QA
**Effort:** 1 week  
**Contains:** Test P0-P1 improvements, verify no regressions

### Phase 3-Step 7: Release v1.1
**Effort:** 1 day  
**Contains:** Final verification, changelog, documentation

**Total Phase 3 Effort:** 5-6 weeks  
**Risk Level:** 🟢 LOW (all changes are safe, read-only, or reversible)

---

---

## Files Inspected

- ✅ scripts/uploader/templates/base.html — Navigation & structure
- ✅ scripts/uploader/templates/imports/dashboard.html — Queue overview
- ✅ scripts/uploader/templates/imports/validation.html — Decision UI
- ✅ scripts/uploader/templates/imports/normalizations.html — Normalization review
- ✅ scripts/uploader/templates/imports/duplicates.html — Duplicate comparison
- ✅ scripts/uploader/templates/imports/households.html — Household grouping
- ✅ scripts/uploader/templates/imports/exports.html — Export console
- ✅ scripts/uploader/templates/imports/audit.html — Audit log
- ✅ scripts/householder/database_models.py — Data models
- ✅ scripts/uploader/app.py — Routes verified

## Files Created

- ✅ docs/implementation/phase3/PHASE3_STEP2_EXPORT_ONLY_PRODUCT_IMPROVEMENT_PLANNING.md (this file)

## Files Modified

- None (Planning phase only)

## Final Test Result

```bash
pytest tests/unit tests/integration -q

✅ 1160 tests passing
✅ 0 failures
✅ 0 errors
✅ Execution time: 12.74s
```

**Baseline Confirmed:** Phase 2 is stable and ready for Phase 3 improvements.

---

## Conclusion & Next Steps

### Phase 3 Direction: ✅ CONFIRMED

**Proceed with export-only improvements, not CRM writeback.**

### Recommended Phase 3 Roadmap

1. **Phase 3-Step 3:** P0 critical fixes (2 days)
2. **Phase 3-Step 4:** P1 readiness dashboard + bulk actions (1.5 weeks)
3. **Phase 3-Step 5:** P1 documentation + UX (1.5 weeks)
4. **Phase 3-Step 6:** Testing & QA (1 week)
5. **Phase 3-Step 7:** Release v1.1 (1 day)

**Total:** 5-6 weeks  
**Risk:** 🟢 LOW  
**Value:** High (makes product more usable without adding risk)

---

## Next Proposed Implementation Step

**Phase 3-Step 3:** Implement P0 critical fixes

**Scope:**
1. Better error messages for missing config
2. Add .limit(50) to recent exports query
3. Improve blocked export messaging
4. Add empty-state messages

**Expected Outcome:**
- User-friendly error handling
- Better guidance when things go wrong
- No functional changes
- 1160 tests still passing

---
