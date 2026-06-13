# Phase 3-Step 4 Planning: Export Readiness Dashboard + Safe Bulk Actions

**Status:** PLANNING ONLY (No implementation)  
**Date:** 2026-06-12  
**Baseline:** 1170 tests passing, export-only v1 product

---

## 1. Current Baseline Summary

### Product State
- **Architecture:** Export-only, no CRM writeback
- **Core principle:** System suggests. Reviewer decides. Raw data unchanged.
- **Review workflow:** Validation → Normalizations → Duplicates → Households → Export
- **Immutability:** Raw import rows never mutated by decisions
- **Readiness:** Derived from validation blocker count in export preview
- **Test coverage:** 1170 unit + integration tests passing
- **Decision records:** ReviewDecision + AuditLogRecord for all reviewer actions

### Current Export Readiness
- Preview generation: `export_preview_service.py`
- Blocker detection: Validation issues, unresolved duplicates, deferred items
- User visibility: Export console shows "Export Ready" or "Export Blocked" banner
- No persistent readiness state
- No background job computation

### Current Bulk Capability
- No bulk actions implemented
- All decisions are single-item
- Each decision creates: ReviewDecision + AuditLogRecord

---

## 2. Product Goal

**Improve batch-level visibility and decision velocity without introducing risk.**

- Make export readiness state more prominent and actionable
- Allow reviewers to defer/dismiss groups of items efficiently
- Maintain immutability and auditability
- Keep reviewer in control of all decisions
- Enable v1.1 to handle larger imports (100-500 contacts) without friction

---

## 3. Explicit Non-Goals

❌ **Out of scope for Phase 3-Step 4:**

- CRM/Givebutter writeback (Phase 4+)
- Contact merge/consolidation (Phase 4+)
- Household master records (Phase 4+)
- Automatic approval of suggestions
- Background job processing
- New export formats
- Export scheduling
- Selective export (e.g., export only confirmed items)
- Cross-import deduplication
- API credentials or external sync
- Auth/RBAC improvements
- Source data mutation

---

## 4. Export Readiness Dashboard Proposal

### What It Is
A dedicated page showing batch-level readiness state, designed to answer: **"Is this batch ready to export?"**

### Design Goals
1. **Single source of truth** for readiness state (derived from existing preview)
2. **Actionable information** about what blocks export
3. **Visual clarity** about progress toward export-ready state
4. **Read-only** (no new mutable state)
5. **No new database tables**

### Proposed Components

#### 4.1 Readiness Summary Panel
**Shows overall batch status at a glance:**

```
Batch: IMP-2025-0101-A | Progress: 85% complete

📊 READINESS: Ready to Export
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Validation Issues:     0 (all resolved)
✓ Unresolved Duplicates: 0 (all decided)
✓ Deferred Items:        0 (all confirmed or exported)
✓ Households:            5 confirmed groups

Status: EXPORT READY ✓
```

#### 4.2 Queue Status by Category
**Quick navigation to remaining review work:**

```
┌─────────────────────────────────────────┐
│ Validation Review                       │
│ 0 issues pending → All Resolved ✓      │
│ [Review Records] (disabled if 0)        │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Duplicates                              │
│ 0 pending → All Decided ✓               │
│ [Review Duplicates] (disabled)          │
└─────────────────────────────────────────┘

... (similar for normalizations, households)
```

#### 4.3 Blocker Breakdown (if blocked)
**When export is blocked, show clear reason:**

```
⚠️ EXPORT BLOCKED: 3 issues prevent export

Blockers:
  • 2 validation issues (invalid email)
  • 1 deferred item (household grouping undecided)

Next Step: Go to [Validation Review] to resolve
```

#### 4.4 Progress Timeline
**Visual progress through review workflow:**

```
Validation (Resolved) → Duplicates (Resolved) → Households (Resolved) → 
Normalizations (2 pending) → Export (Ready)
```

### Implementation Approach (Non-Code)

**Route:** GET `/imports/<batch_id>/readiness`

**Service:** New `export_readiness_service.py`
- Query existing preview logic
- Derive readiness from blocker count
- Format for template display
- No database mutations

**Template:** New `imports/readiness.html`
- Display all components above
- Use existing CSS patterns
- No new styling required

**Data Source:**
- `export_preview_service.get_export_preview()` (existing)
- `dashboard_service.get_import_dashboard()` (existing)
- Combine queue status + preview blockers

**No new tables or fields needed.**

### Readiness Derivation Logic

```python
def get_export_readiness(import_id: str) -> ExportReadinessViewModel:
    preview = export_preview_service.get_export_preview(import_id)
    dashboard = dashboard_service.get_import_dashboard(import_id)
    
    is_ready = preview.blocked_count == 0 and preview.row_count > 0
    
    return ExportReadinessViewModel(
        batch_id=import_id,
        is_ready=is_ready,
        blocker_count=preview.blocked_count,
        blockers=preview.blockers,
        warnings=preview.warnings,
        queue_status=dashboard.queue_status,
        staged_records=preview.row_count,
    )
```

---

## 5. Safe Bulk Actions Proposal

### Definition: "Safe" Bulk Action
A bulk action is safe if:
1. **Reviewer remains in control** — Explicitly decides per item or applies clear rule
2. **Semantically sound** — Action is identical to single-item version
3. **Fully audited** — Creates ReviewDecision + AuditLogRecord for each item
4. **No mutation** — ReviewItem.status remains derived, never written directly
5. **Reversible** — Subsequent decision overwrites previous decision
6. **No merge/consolidation** — No contact or household mutation

### Candidate Bulk Actions for v1.1

#### ✓ APPROVED: Bulk Defer
**Definition:** "Defer all pending [category] items to later"

**Example:** "Defer all 5 pending validation issues"

**Mechanism:**
1. Show user: "This will create 5 ReviewDecision records with decision='defer'"
2. User confirms: "Yes, defer all 5"
3. For each item:
   - Create ReviewDecision(decision='defer', notes='Bulk deferred')
   - Create AuditLogRecord(action_type='decision_recorded')
4. Each decision is audited independently
5. Dashboard shows 5 deferred items (can be revisited)

**Why safe:**
- Identical to clicking defer 5 times
- No consolidation or merge
- Fully reversible (next decision overwrites)
- Clear audit trail
- No data mutation

**Implementation sketch:**
```
POST /imports/<batch_id>/bulk-defer
{
  "category": "validation|normalization|duplicate|household",
  "notes": "Deferring for later review"
}
```

#### ✓ APPROVED: Bulk Dismiss (Validation)
**Definition:** "Dismiss all pending validation issues as false positives"

**Example:** "Dismiss 3 validation issues (phone format) as false positives"

**Mechanism:**
1. Show: "This will create 3 ReviewDecision records with decision='dismiss_issue'"
2. User confirms: "Yes, dismiss all 3"
3. For each item:
   - Create ReviewDecision(decision='dismiss_issue')
   - Create AuditLogRecord
4. Validation dashboard shows 0 pending

**Why safe:**
- Identical to clicking dismiss 3 times
- No data mutation
- Fully reversible
- Clear audit trail

**Implementation sketch:**
```
POST /imports/<batch_id>/bulk-dismiss
{
  "category": "validation",
  "issue_type": "phone-format|email-format|...",
  "notes": "False positive batch"
}
```

#### ❌ NOT APPROVED: Bulk Accept/Approve
**Why unsafe:**
- Requires reviewer to verify each suggestion is correct
- Bulk approval removes individual review friction, increases risk
- Not semantically identical to single-item (loses context per item)
- More appropriate for Phase 4+ with better confidence scoring

#### ❌ NOT APPROVED: Bulk Confirm Duplicates
**Why unsafe:**
- Contact consolidation is complex
- Bulk confirm could incorrectly merge related but different people
- Requires high reviewer confidence per pair
- Phase 4+ work

#### ❌ NOT APPROVED: Bulk Assign Household
**Why unsafe:**
- Assigns household_id directly to contacts
- Could break family relationships
- Consolidation operation, not decision recording
- Phase 4+ work

### Bulk Action Constraints

**Must enforce:**
1. **Per-item audit trail** — Each item gets its own ReviewDecision + AuditLogRecord
2. **No direct ReviewItem mutation** — status remains derived from latest decision
3. **Reviewer confirmation** — Show what will happen before applying
4. **Category-specific rules** — Can't bulk-defer duplicates and validation together
5. **No data consolidation** — No contact/household merging

**Must not enable:**
- Bulk delete
- Bulk merge
- Automatic approval
- Cross-category bulk actions
- Bulk export (Phase 4+)

---

## 6. Risk Analysis

### Export Readiness Dashboard Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Incorrect readiness state | Medium | Derive from existing preview logic, add tests |
| User ignores warnings | Low | Distinct visual treatment of warnings vs blockers |
| Missing blocker visibility | Medium | Enumerate all blockers, test each type |
| Performance (large batches) | Low | Use existing cached preview data |

### Safe Bulk Actions Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Accidental bulk defer/dismiss | High | Require explicit confirmation per category |
| Audit trail quality | High | Create individual ReviewDecision + AuditLogRecord |
| Bulk defer creates too many items | Medium | Limit to <100 items per bulk action, show count |
| Reviewer forgets they deferred | Low | Dashboard shows deferred count, audit log provides history |
| Reviewer confusion about semantics | Medium | Clear UI: "This creates 5 defer decisions" |

### Mitigation Strategy

**For Readiness Dashboard:**
- Test each blocker type (validation, duplicate, deferred, household)
- Test with 0 blockers (ready state)
- Test with mixed blockers (blocked state)
- Verify no new database queries

**For Bulk Actions:**
- Require explicit "Confirm" UI step
- Show count of items affected
- Show example decision before applying
- Create test fixtures with 10+ items per category
- Test audit trail for correctness and completeness
- Test reversibility (next single decision overwrites bulk)

---

## 7. Guardrails

### Hard Constraints (Non-Negotiable)

✓ **Maintain guardrails:**
```
✓ No CRM/Givebutter API calls
✓ No credentials added
✓ No writeback routes
✓ No auth/RBAC changes
✓ No source data mutation (raw import rows unchanged)
✓ No contact mutation (no email/phone/address changes)
✓ No contact merge/consolidation
✓ No contact deletion
✓ No household_id assignment
✓ No durable household master records
✓ No durable merged contact records
✓ No schema changes (use existing tables)
✓ No background jobs
✓ No new export formats
✓ No cross-import matching
✓ No master contacts/households
```

### Required for Bulk Actions
```
✓ Each action creates ReviewDecision + AuditLogRecord
✓ Reviewer explicitly confirms before applying
✓ Status remains derived (never write ReviewItem.status)
✓ Action is auditable (full trail of who, what, when)
✓ Action is reversible (next decision overwrites)
```

---

## 8. Data Model Impact

### No New Tables Required

**Existing tables sufficient:**
- `review_items` — No changes
- `review_decisions` — Create one record per bulk item (as if single decisions)
- `audit_log` — Create one record per bulk item
- `import_batches` — No changes
- `import_contacts` — No changes
- `raw_import_rows` — No changes

### No Schema Changes

All bulk actions work within existing data model:
- Decision effective_status remains derived
- AuditLogRecord already supports batch operations
- ReviewDecision already tracks reviewer + timestamp

### View Models (New)

```python
@dataclass(frozen=True)
class ExportReadinessViewModel:
    batch_id: str
    is_ready: bool
    blocker_count: int
    blockers: List[str]
    warnings: List[str]
    staged_records: int
    queue_status: QueueStatus
    progress_pct: int

@dataclass(frozen=True)
class BulkActionRequest:
    category: str  # validation|normalization|duplicate|household
    action_type: str  # defer|dismiss
    notes: str
    # No item_ids list — should be implicit "all pending in category"

@dataclass(frozen=True)
class BulkActionResult:
    action_type: str
    category: str
    items_affected: int
    decisions_created: int
    audit_records_created: int
    reviewer: str
    timestamp: datetime
```

---

## 9. Route/Service/Template Impact

### New Routes

```
GET  /imports/<batch_id>/readiness
     → Show export readiness dashboard
     
POST /imports/<batch_id>/bulk-defer
     → Create bulk defer decisions
     
POST /imports/<batch_id>/bulk-dismiss
     → Create bulk dismiss decisions (validation only)
```

### New Services

**export_readiness_service.py:**
```python
def get_export_readiness(import_id: str) -> ExportReadinessViewModel
    # Combine preview + dashboard data
    # Derive readiness state
    # Format for template

def apply_bulk_defer(import_id: str, category: str, reviewer: str) -> BulkActionResult
    # Query all pending ReviewItems in category
    # Create ReviewDecision for each
    # Create AuditLogRecord for each
    # Return summary

def apply_bulk_dismiss(import_id: str, issue_type: str, reviewer: str) -> BulkActionResult
    # Query all validation items with issue_type
    # Create dismiss decisions
    # Return summary
```

### New Templates

**readiness.html:**
- Display readiness summary panel
- Show queue status by category
- Show blocker breakdown (if blocked)
- Show progress timeline
- Link to review pages or export

**bulk-defer-confirm.html (Modal or Page):**
- Show: "This will create N defer decisions"
- Show example of what will be deferred
- Require "Confirm" button
- Show notes field

**bulk-dismiss-confirm.html (Modal or Page):**
- Similar to defer
- Show which issue_type will be dismissed

### Service Changes

**dashboard_service.py:**
- No changes (existing data)

**export_preview_service.py:**
- No changes (existing data)

**review_decision services:**
- extend to support bulk operations
- (could also create generic bulk service)

---

## 10. Test Plan

### Unit Tests

**export_readiness_service.py:**
```
✓ test_readiness_ready_when_no_blockers
✓ test_readiness_blocked_when_validation_issues_exist
✓ test_readiness_blocked_when_duplicates_pending
✓ test_readiness_blocked_when_deferred_items_exist
✓ test_readiness_includes_all_blocker_types
✓ test_readiness_includes_warnings
✓ test_readiness_progress_calculation
✓ test_readiness_queue_status_integration

✓ test_bulk_defer_creates_decisions_for_all_items
✓ test_bulk_defer_creates_audit_logs_for_all_items
✓ test_bulk_defer_returns_correct_count
✓ test_bulk_defer_requires_reviewer
✓ test_bulk_defer_respects_category
✓ test_bulk_defer_empty_category_returns_0

✓ test_bulk_dismiss_creates_dismiss_decisions
✓ test_bulk_dismiss_supports_validation_category_only
✓ test_bulk_dismiss_filters_by_issue_type
✓ test_bulk_dismiss_empty_result_returns_0
```

### Integration Tests

**readiness_route.py:**
```
✓ test_readiness_route_returns_200
✓ test_readiness_route_returns_ready_page
✓ test_readiness_route_shows_blockers_if_blocked
✓ test_readiness_route_no_database_mutation
✓ test_readiness_route_caches_preview_data
```

**bulk_defer_route.py:**
```
✓ test_bulk_defer_route_returns_200_on_success
✓ test_bulk_defer_route_creates_decisions
✓ test_bulk_defer_route_requires_confirmation
✓ test_bulk_defer_route_limits_to_100_items
✓ test_bulk_defer_route_no_database_mutation_except_decisions
✓ test_bulk_defer_creates_audit_trail
✓ test_bulk_defer_empty_category_returns_0
```

**bulk_dismiss_route.py:**
```
✓ test_bulk_dismiss_route_creates_dismiss_decisions
✓ test_bulk_dismiss_route_validation_only
✓ test_bulk_dismiss_route_filters_by_issue_type
✓ test_bulk_dismiss_creates_audit_trail
```

### E2E Tests (if running locally with Flask)

```
✓ test_e2e_navigate_to_readiness_dashboard
✓ test_e2e_readiness_shows_ready_state
✓ test_e2e_readiness_shows_blockers
✓ test_e2e_bulk_defer_confirmation_flow
✓ test_e2e_bulk_defer_creates_decisions
✓ test_e2e_bulk_dismiss_confirmation_flow
✓ test_e2e_audit_trail_shows_bulk_actions
```

### Backwards Compatibility Tests

```
✓ test_single_defer_still_works_after_bulk_defer
✓ test_readiness_unaffected_by_single_decisions
✓ test_bulk_actions_not_visible_to_phase1_fixtures
```

---

## 11. Acceptance Criteria

### Phase 3-Step 4A: Export Readiness Dashboard

**Must have:**
- [ ] Route GET `/imports/<batch_id>/readiness` returns 200
- [ ] Readiness state derived correctly from preview
- [ ] "Export Ready" shown when no blockers
- [ ] "Export Blocked" shown with blocker enumeration when blocked
- [ ] Queue status shows pending counts for all categories
- [ ] Progress timeline visible
- [ ] No new database tables created
- [ ] No source data mutation
- [ ] All 1170 tests still pass + 10+ new readiness tests
- [ ] Readiness state matches export console state

**Nice to have:**
- Visual styling distinguishes ready vs blocked
- Warnings section shows non-blocking issues
- Links to review pages (disabled if queue empty)

### Phase 3-Step 4B: Safe Bulk Actions

**Bulk Defer must have:**
- [ ] Route POST `/imports/<batch_id>/bulk-defer` accepts category
- [ ] Confirmation UI shows count of items affected
- [ ] Example decision shown before confirmation
- [ ] Creates ReviewDecision for each item
- [ ] Creates AuditLogRecord for each item
- [ ] Returns count of decisions created
- [ ] Reviewer ID captured in audit trail
- [ ] Audit trail shows individual decisions (not one bulk record)
- [ ] Reversible (next single decision overwrites)
- [ ] No source data mutation

**Bulk Dismiss must have:**
- [ ] Route POST `/imports/<batch_id>/bulk-dismiss` accepts issue_type
- [ ] Works only for validation category
- [ ] Creates dismiss_issue decisions
- [ ] Full audit trail per item
- [ ] Confirmation UI shows example

**Both must have:**
- [ ] All 1170 + readiness tests still pass
- [ ] 20+ new bulk action tests
- [ ] No schema changes
- [ ] No contact mutation
- [ ] Limit to <100 items per bulk action
- [ ] Clear audit trail
- [ ] Reviewer required for all actions

---

## 12. Recommendation: Split into 4A and 4B

### Recommended Approach: **SPLIT INTO 4A AND 4B**

**Rationale:**

1. **Risk stratification:**
   - 4A (Dashboard): Low risk, display-only, no new durable state
   - 4B (Bulk actions): Higher risk, creates many decision records, requires careful semantics

2. **Review and iteration:**
   - 4A can be accepted independently
   - 4B needs more design review (which bulk actions exactly?)
   - Splitting allows focused feedback on each concern

3. **Value delivery:**
   - 4A (Dashboard) provides immediate value in v1.1
   - 4B (Bulk actions) is nice-to-have but not blocking export workflow

4. **Testing complexity:**
   - 4A: ~15 tests (straightforward)
   - 4B: ~25 tests (more complex audit trail verification)
   - Separate implementation allows focused test design

5. **User adoption:**
   - 4A: Safe to deploy as soon as ready
   - 4B: May want user feedback before bulk operations
   - Can be toggled/phased independently

### Phase 3-Step 4A: Export Readiness Dashboard Only

**Scope:**
- New readiness route and service
- New readiness template
- Derived from existing preview logic
- No bulk actions
- ~5-7 hours implementation + testing

**Success criteria:**
- Readiness state accurately reflects export preview
- Clear blocker communication
- 15 new tests
- No regression in existing 1170 tests

**Deployment:** Ready for v1.1 immediately

### Phase 3-Step 4B: Safe Bulk Actions (Later)

**Scope:**
- Bulk defer route + service
- Bulk dismiss route + service
- Confirmation UI (modal or page)
- Full audit trail
- ~8-10 hours implementation + testing

**Success criteria:**
- Decisions created correctly per item
- Audit trail complete and auditable
- Reversible (next decision overwrites)
- 25 new tests
- No regression

**Deployment:** Can be delayed to v1.2 if needed, or proceed after 4A acceptance

---

## Summary

### Phase 3-Step 4A (Recommended for v1.1)
- **Effort:** ~6 hours
- **Risk:** Low (read-only, derived state)
- **Value:** High (improves visibility)
- **Tests:** 15
- **Dependencies:** None
- **Decision:** IMPLEMENT

### Phase 3-Step 4B (Candidate for v1.1 or v1.2)
- **Effort:** ~9 hours
- **Risk:** Medium (audit trail quality, semantics)
- **Value:** Medium (optional efficiency)
- **Tests:** 25
- **Dependencies:** None (but benefits from 4A context)
- **Decision:** PLAN NOW, DECIDE AFTER 4A ACCEPTANCE

### Guardrail Confirmation

All hard constraints maintained in both 4A and 4B:
```
✓ No CRM/Givebutter API calls
✓ No credentials
✓ No writeback routes
✓ No auth/RBAC changes
✓ No source data mutation
✓ No contact/household mutation
✓ No schema changes
✓ No background jobs
✓ No new export formats
```

---

## Next Steps

1. **Approve 4A (Dashboard) immediately** — low risk, high value
2. **Plan 4B (Bulk actions) separately** — decide after 4A complete
3. **Create 4A implementation task** (Phase 3-Step 4A)
4. **Create 4B planning task** (Phase 3-Step 4B, separate ticket)

