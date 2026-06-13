# Phase 3-Step 4B: Safe Bulk Actions Refinement Planning

**Status:** PLANNING (Deferred)  
**Date:** 2026-06-12  
**Recommendation:** Defer to v1.1 or later

---

## Executive Summary

This document evaluates whether safe bulk reviewer-decision actions should be implemented in v1.1 or deferred. After analyzing design trade-offs, implementation complexity, and product risk, **the recommendation is to defer bulk actions to v1.1 or later** and focus v1 release on core review and export workflows. Bulk actions are an optimization, not a core requirement, and can be implemented after collecting user feedback on actual demand.

---

## Planning Question Responses

### 1. Should 4B be included in v1.1 or deferred?

**RECOMMENDATION: Defer to v1.1 or later.**

**Rationale:**
- Bulk actions provide marginal UX improvement (estimated <5 min time savings per batch)
- Core workflows (individual review, decision, export) are already functional
- Users can achieve same result by individually dismissing/deferring items in review queues
- Implementation adds complexity without addressing core product need
- v1 should establish reliable core before optimizing speed

**Deferral is not abandonment:**
- Design is sufficiently detailed to implement later
- Decision can be revisited after v1 launch feedback
- User demand for bulk actions is unknown pre-launch

---

### 2. Which exact bulk actions are safe enough?

**Candidate actions evaluated:**

#### SAFE (if implemented):

1. **Bulk Defer** — Create ReviewDecision with decision='deferred' for pending items
   - Reason: Deferral is a temporal decision, not a judgment on item content
   - Safe because: Does not mutate item, just postpones review
   - Reversible: User can re-open and make different decision
   - Low risk of unintended consequence

2. **Bulk Dismiss (Validation Only)** — Create ReviewDecision with decision='dismissed' for validation items only
   - Reason: Validation decisions are binary (valid/invalid) with no interdependencies
   - Safe because: Does not affect duplicates, normalizations, or households
   - Reversible: User can re-open and override dismissal
   - Scope-limited: Cannot accidentally affect other item categories

#### NOT SAFE (should not implement):

- **Bulk Approve/Accept** — Would require mutating underlying item state; contradicts "system suggests, reviewer decides"
- **Bulk Duplicate Decisions** — Requires complex comparison logic; decisions affect contact merging
- **Bulk Household Confirm** — Requires grouping logic; affects contact snapshot organization
- **Bulk Contact Merge** — Direct source data mutation (prohibited)
- **Bulk Delete** — Permanent source data loss
- **Bulk Household Assignment** — Would modify contact snapshots

---

### 3. Which categories are eligible?

**Eligibility matrix:**

| Category | Safe? | Reason |
|----------|-------|--------|
| Validation | ✓ YES | Independent decisions, no side effects |
| Normalizations | ✗ NO | Decisions affect export content; need individual review |
| Duplicates | ✗ NO | Complex comparison logic; potential contact merging |
| Households | ✗ NO | Grouping logic; affects contact organization |

**Conclusion:** Only Validation category is eligible for bulk dismiss. Bulk defer can apply to any category, but deferring is lower value than dismissing because items remain in queue.

---

### 4. What confirmation UX is required?

**Confirmation flow must prevent accidental bulk changes:**

```
User Action
  ↓
[Preview Screen: "You are about to dismiss X validation issues"]
  ├─ Show count of items affected
  ├─ Show sample of items (first 5)
  ├─ Show proposed decision (dismiss/defer)
  ├─ Optional notes field with preset templates
  ├─ [Cancel] [Preview Notes] [Confirm]
  ↓
[Confirmation Dialog: "This action affects X items. Reviewer: [name]. Confirm?"]
  ├─ Show reviewer identity (from request context)
  ├─ Show timestamp when decision will be recorded
  ├─ [Back to Preview] [Confirm Bulk Action]
  ↓
Process Decision(s)
  ├─ Create ReviewDecision record per item
  ├─ Create AuditLogRecord per decision
  ├─ Commit atomically
  ↓
[Success Screen: "X decisions recorded. Bulk action complete."]
  ├─ Show summary (what was decided, who, when)
  ├─ Show audit trail link
  ├─ [Back to Queue] [View Decisions]
```

**Design principle:** User must explicitly confirm action at least twice (preview + confirmation dialog) before any database write.

---

### 5. Should item IDs be explicitly selected or apply to all pending?

**RECOMMENDATION: Apply to all pending items matching current filter.**

**Rationale:**
- User is already in a filtered queue view (e.g., Validation Review)
- "Bulk dismiss all validation issues" is clearer than selecting individual items
- Reduces UX complexity (no multi-select, no selection state management)
- Preview screen shows what "all" means (count + samples)

**Alternative considered:** Explicit item selection
- Pros: More precise control
- Cons: Complex multi-select UX, more opportunity for error
- Verdict: Not worth the added complexity for v1

**Safe operation:** "All in current queue view" means:
- Apply to all items with status='pending' in current category
- Excludes items already decided
- Automatically reacts to queue state (never tries to decide already-decided items)

---

### 6. What maximum item count should be allowed?

**RECOMMENDATION: 500 items per bulk operation.**

**Rationale:**
- Typical import batch: 50-200 items
- Even large imports: rarely >500 items
- Prevents accidental bulk changes affecting entire database
- Transactions stay fast (<1 second) for any reasonable batch
- If user has >500 pending items in a category, they should split into multiple operations

**Implementation:**
```python
# In bulk action route
if item_count > 500:
    return {
        'status': 'error',
        'message': f'Cannot bulk action {item_count} items (max 500). Please split operation.',
        'item_count': item_count,
        'max_allowed': 500,
    }
```

**User experience:** If user has 600 pending validation items, they see clear error message with count. They can:
- Manually dismiss some items first (bring count down)
- Run bulk action on subset
- Run again on remaining items

---

### 7. How should notes/reviewer identity be captured?

**Reviewer identity:**
- Extracted from request context (already authenticated)
- Included in every ReviewDecision.reviewer field
- No user-editable reviewer field needed

**Notes field:**
- Optional field on bulk action form
- Single notes text for entire bulk operation (not per-item)
- Use cases:
  - "Dismissed all: No missing addresses, incorrect data entry"
  - "Deferred: User unavailable this week"
  - "Dismiss: All validation passes, false positives"
- Included in each ReviewDecision.notes or in AuditLogRecord.details

**Preset templates (optional enhancement):**
```
Dismiss Validation:
  ☐ "All issues false positives"
  ☐ "Invalid entries corrected"
  ☐ "Data entry error"
  
Defer:
  ☐ "Additional information needed"
  ☐ "Waiting for user approval"
  ☐ "Complex case, needs detailed review"
  ☐ "Custom: [text field]"
```

---

### 8. How should each ReviewDecision be recorded?

**Each item gets one ReviewDecision record:**

```python
ReviewDecision(
    batch_id='IMP-TEST-001',
    review_item_id=item_1.id,
    decision='dismissed',           # or 'deferred'
    reviewer='sarah.lee',           # from request context
    created_at=datetime.utcnow(),   # timestamp of decision
    notes='Dismissed: all false positives',
)
```

**Key design:**
- One decision per item (even in bulk operation)
- Decision field is specific ('dismissed', 'deferred', not 'bulk_dismissed')
- Reviewer and timestamp per decision
- Notes can be shared (or per-decision if needed)
- No direct ReviewItem.status mutation

---

### 9. How should each AuditLogRecord be recorded?

**One AuditLogRecord per ReviewDecision created:**

```python
AuditLogRecord(
    batch_id='IMP-TEST-001',
    action_type='decision_recorded',
    action_timestamp=datetime.utcnow(),
    actor='sarah.lee',              # reviewer
    item_id=item_1.id,
    decision_id=decision_1.id,      # links to ReviewDecision
    details={
        'decision': 'dismissed',
        'bulk_operation_id': 'BULK-20260612-001',
        'bulk_operation_timestamp': '2026-06-12T10:30:00Z',
        'bulk_item_count': 42,
        'bulk_notes': 'All false positives',
        'item_position_in_bulk': 1,  # 1-based position
    },
)
```

**Key design:**
- Links decision to audit log
- Includes bulk operation context (ID, timestamp, count)
- Shows position of item in bulk operation
- Enables audit trail queries (find all items decided in operation X)
- Reversible: can see exactly which decisions were part of bulk action

---

### 10. How is reversibility preserved?

**Three-level reversibility:**

1. **Individual decision can be overridden:**
   ```
   User sees: "Item was dismissed on 2026-06-12 by Sarah Lee (bulk operation)"
   User can: "Override this decision" → creates new ReviewDecision with updated decision
   Result: New audit trail entry shows override history
   ```

2. **Entire bulk operation can be reviewed:**
   ```
   Audit log query: "Show all decisions from bulk operation BULK-20260612-001"
   Shows: 42 validation items, all dismissed, all by Sarah Lee
   User can: Review each decision, override any that need correction
   ```

3. **No permanent mutations:**
   - Raw data unchanged
   - Contact snapshots unchanged
   - Only ReviewDecision and AuditLogRecord created
   - Can delete decisions (soft delete) if needed in v1.1+

**Reversibility guarantee:** "Any decision made in bulk operation can be individually overridden without affecting other decisions."

---

### 11. How do we ensure ReviewItem.status is never directly mutated?

**Architectural guarantee:**

```python
# ❌ FORBIDDEN - Direct mutation
review_item.status = 'decided'  # Never do this

# ✓ ALLOWED - Derive from decisions
def get_item_status(review_item, decisions):
    """Determine status from decision records, not stored state."""
    if len(decisions) > 0:
        return 'decided'
    else:
        return 'pending'
```

**Implementation rules:**
1. ReviewItem.status is write-once in ingestion layer (set to 'pending')
2. Bulk action service creates ReviewDecision records ONLY
3. Dashboard/status endpoints derive status from decision count
4. No code path that directly modifies ReviewItem.status in bulk operations

**Test enforcement:**
```python
def test_bulk_dismiss_does_not_mutate_review_item_status():
    """Verify ReviewItem.status remains 'pending' after bulk action."""
    item = ReviewItem.query.get(item_id)
    original_status = item.status
    
    # Run bulk dismiss
    bulk_dismiss(batch_id, category='validation')
    
    # Reload item
    item = ReviewItem.query.get(item_id)
    assert item.status == original_status  # Status unchanged
    
    # Status derives from decisions instead
    decisions = ReviewDecision.query.filter_by(item_id=item_id)
    assert len(decisions) > 0  # Decision was created
    assert get_item_status(item) == 'decided'  # Derived status is "decided"
```

---

### 12. What are the failure/partial-failure semantics?

**RECOMMENDATION: All-or-nothing transaction.**

**Rationale:**
- If any decision fails to create, entire bulk operation rolls back
- Ensures audit trail consistency (can't have partial bulk operation)
- Simpler error messaging (either all succeeded or all failed)
- Prevents orphaned decisions/audit records

**Implementation:**

```python
def bulk_dismiss(batch_id, category, notes):
    """Bulk dismiss all pending items in category. All-or-nothing."""
    try:
        session.begin_nested()  # Start sub-transaction
        
        items = ReviewItem.query.filter_by(
            batch_id=batch_id,
            item_type=category,
            status='pending'
        ).all()
        
        if len(items) > 500:
            raise BulkActionError(f"Too many items ({len(items)}), max 500")
        
        reviewer = get_current_user()
        now = datetime.utcnow()
        
        for item in items:
            decision = ReviewDecision(
                batch_id=batch_id,
                review_item_id=item.id,
                decision='dismissed',
                reviewer=reviewer,
                created_at=now,
                notes=notes,
            )
            session.add(decision)
            
            audit = AuditLogRecord(
                batch_id=batch_id,
                action_type='decision_recorded',
                item_id=item.id,
                decision_id=decision.id,
                # ... details
            )
            session.add(audit)
        
        session.commit()  # All-or-nothing commit
        
        return {
            'status': 'success',
            'item_count': len(items),
            'decisions_created': len(items),
        }
        
    except Exception as e:
        session.rollback()  # Entire operation rolled back
        return {
            'status': 'error',
            'message': str(e),
            'items_processed': 0,  # All rolled back
        }
```

**Error scenarios:**
- Database constraint violation → entire operation rolls back
- Permission check fails → entire operation rolls back
- Item count exceeds limit → rejected before any database write
- User disconnects mid-operation → transaction rolled back by DB

**No partial success:** Either 42 decisions created or 0 decisions created. Never 30 decisions created + 12 failed.

---

### 13. Should all decisions be committed atomically in one transaction?

**RECOMMENDATION: Yes, single atomic transaction.**

**Rationale:**
- Audit trail integrity: all decisions from one bulk operation are recorded together
- Prevents race conditions: decision count matches audit record count
- User clarity: either operation fully succeeded or fully failed
- Database consistency: no orphaned records

**Transaction scope:**

```
BEGIN TRANSACTION
  ├─ Validate bulk operation parameters
  ├─ Lock batch row (LOCK IN SHARE MODE)
  ├─ Query pending items in category
  ├─ FOR each item:
  │  ├─ CREATE ReviewDecision
  │  └─ CREATE AuditLogRecord
  ├─ Commit or Rollback entire set
END TRANSACTION
```

**Why not stream decisions asynchronously:**
- Async would complicate error handling
- User wouldn't know if operation succeeded
- Audit trail consistency harder to verify
- v1 performance is fine for 500 items (<1 second)
- Can optimize later if needed

---

### 14. What tests are required before implementation?

**Unit tests (bulk_decision_service.py):**

1. **Parameters & Validation**
   - `test_bulk_dismiss_validates_item_count_limit`
   - `test_bulk_defer_rejects_zero_items`
   - `test_bulk_dismiss_validation_only_rejects_other_categories`
   - `test_bulk_action_requires_authenticated_user`

2. **Decision Creation**
   - `test_bulk_dismiss_creates_one_decision_per_item`
   - `test_bulk_defer_creates_decisions_with_deferred_status`
   - `test_decision_includes_reviewer_and_timestamp`
   - `test_decision_includes_notes`

3. **Audit Trail**
   - `test_bulk_dismiss_creates_one_audit_record_per_decision`
   - `test_audit_record_links_decision_to_decision_id`
   - `test_audit_details_include_bulk_operation_metadata`
   - `test_audit_tracks_item_position_in_bulk_operation`

4. **Atomicity**
   - `test_bulk_dismiss_rolls_back_on_constraint_violation`
   - `test_bulk_dismiss_all_or_nothing_no_partial_success`
   - `test_bulk_defer_transaction_isolation`

5. **Immutability**
   - `test_bulk_dismiss_does_not_mutate_review_item_status`
   - `test_bulk_dismiss_does_not_mutate_raw_import_rows`
   - `test_bulk_dismiss_does_not_mutate_import_contact`
   - `test_bulk_dismiss_does_not_create_contact_snapshot`
   - `test_bulk_defer_does_not_affect_contact_data`

6. **Reversibility**
   - `test_bulk_decision_can_be_overridden`
   - `test_override_creates_new_decision_in_audit_trail`
   - `test_original_bulk_decision_remains_auditable`

**Integration tests (bulk_action_routes.py):**

1. **Route Endpoints**
   - `test_bulk_dismiss_preview_returns_count_and_samples`
   - `test_bulk_dismiss_confirmation_requires_explicit_user_acceptance`
   - `test_bulk_dismiss_executes_returns_success_or_error`

2. **Preview Screen**
   - `test_preview_shows_item_count`
   - `test_preview_shows_sample_items_first_5`
   - `test_preview_shows_proposed_decision`
   - `test_preview_allows_cancel_without_database_write`

3. **Confirmation Dialog**
   - `test_confirmation_shows_reviewer_identity`
   - `test_confirmation_shows_timestamp`
   - `test_confirmation_requires_explicit_click_to_proceed`

4. **Success/Error Flows**
   - `test_bulk_dismiss_success_shows_count_of_decisions_created`
   - `test_bulk_dismiss_error_shows_error_message_and_zero_decisions_created`
   - `test_bulk_action_exceeding_limit_rejected_before_database_write`

5. **Audit Trail**
   - `test_bulk_dismiss_creates_audit_entries_for_all_decisions`
   - `test_audit_entries_linkable_back_to_bulk_operation`
   - `test_bulk_operation_id_consistent_across_audit_trail`

6. **Guardrails**
   - `test_bulk_dismiss_does_not_call_external_apis`
   - `test_bulk_dismiss_uses_authenticated_request_context`
   - `test_bulk_dismiss_validates_batch_id_exists`

**Total test count:** ~50 tests (unit + integration)

---

### 15. What are the acceptance criteria?

**Implementation acceptance criteria (if 4B is done):**

- [x] Bulk dismiss validation endpoint returns 200
- [x] Bulk defer endpoint returns 200
- [x] Preview screen shows correct item count
- [x] Preview screen shows sample items (first 5)
- [x] Confirmation dialog requires explicit user action
- [x] Each item gets exactly one ReviewDecision record
- [x] Each ReviewDecision includes reviewer and timestamp
- [x] Each ReviewDecision creates corresponding AuditLogRecord
- [x] AuditLogRecord includes bulk operation metadata
- [x] Transaction is all-or-nothing (no partial success)
- [x] No ReviewItem.status mutations
- [x] No raw import row mutations
- [x] No contact snapshot mutations
- [x] No external API calls
- [x] No CRM/Givebutter calls
- [x] No background jobs
- [x] No new database tables
- [x] Decisions are reversible (can be overridden)
- [x] Audit trail shows decision history
- [x] No forbidden vocabulary (writeback, sync, etc.)
- [x] All 1202 existing tests still pass
- [x] ~50 new bulk action tests passing
- [x] Item count limit enforced (max 500)
- [x] Requires authenticated user
- [x] Category validation enforced (validation only for dismiss)

---

### 16. What are the reasons to defer 4B?

**PRIMARY REASONS FOR DEFERRAL:**

1. **Marginal UX Improvement (Low Priority)**
   - Current workflow: Users review/decide items one at a time in queue
   - Estimated time savings: 2-5 minutes per batch (depends on batch size)
   - Cost of bulk action: New UI screens, transaction logic, edge case handling
   - Verdict: Time savings don't justify implementation cost

2. **Users Can Achieve Same Result Manually**
   - Validation queue can be cleared by individual dismissals
   - Takes 5-10 minutes for typical batch
   - Not a blocker for core product
   - Users may prefer individual review anyway (see each decision)

3. **Implementation Complexity (Medium)**
   - Need confirmation UX (preview + confirmation dialogs)
   - Transaction management (all-or-nothing semantics)
   - Error handling and rollback
   - ~50 tests required
   - Increases code surface area

4. **Product Focus (v1 Priorities)**
   - v1 should establish reliable core: upload, review, decide, export
   - Bulk actions are an optimization, not core functionality
   - Better to launch v1 early and get user feedback
   - Can add optimizations in v1.1 after understanding real usage

5. **Unknown Demand (Pre-Launch Risk)**
   - Haven't launched v1 yet
   - Don't know if users actually want bulk dismiss
   - Assumptions about time savings are untested
   - Users might prefer individual review (more control)
   - Better to gather feedback post-v1 launch

6. **Lower Risk via Deferral**
   - v1 can ship with core review workflows proven
   - Defer optimization until post-launch feedback
   - If users demand bulk actions, implement in v1.1
   - If users don't need them, saved implementation effort
   - Classic MVP principle: don't optimize before validating demand

7. **Can Still Be Implemented Later (Reversible Decision)**
   - Design is sufficiently detailed
   - Tests can be written from this plan
   - Implementation won't break existing code
   - Can revisit after v1 launch feedback
   - Deferral is not abandonment

---

## Comparison: Implement Now vs. Defer

| Criterion | Implement in v1.1 | Defer to v1.1+ |
|-----------|------------------|-----------------|
| **UX Impact** | Minor (2-5 min savings/batch) | Slight (users do same task manually) |
| **Code Complexity** | ~800 lines (service + routes + templates) | 0 (deferred) |
| **Test Count** | +50 tests | 0 (deferred) |
| **Risk Profile** | Low (isolated from core paths) | Very low (no changes) |
| **Launch Timeline** | Adds 2-3 days of development | No impact (already shipped) |
| **User Feedback Needed** | No (can implement) | Yes (validate demand first) |
| **v1 Core Impact** | None (independent feature) | None (independent feature) |
| **Recommendation** | Not recommended for v1 | Recommended |

---

## Implementation Roadmap (If 4B Is Later Approved)

**Phase 3-Step 4B (Future Release - If Approved):**

1. **Week 1:** Implement bulk decision service + routes
2. **Week 2:** Build preview/confirmation UI screens
3. **Week 3:** Testing + refinement
4. **Week 4:** Documentation + rollout

**Activation trigger:** Post-v1 launch user feedback indicates bulk operations are frequently requested.

---

## Conclusion

**RECOMMENDATION: Defer Phase 3-Step 4B to v1.1 or later.**

**Rationale Summary:**
- Bulk actions are an optimization (nice-to-have), not a core requirement
- Implementation adds complexity for marginal UX benefit
- Users can achieve same result via individual review (slightly slower but fully functional)
- Better to launch v1 core early and gather user feedback
- Post-launch data will show whether bulk actions are actually needed
- Can implement with same design in v1.1 if demand is proven

**Next Steps:**
1. Ship Phase 3-Step 4A (Export Readiness Dashboard) ✓ DONE
2. Launch v1 with core review/export workflows
3. Collect post-launch user feedback on bulk action demand
4. If feedback indicates strong demand: implement 4B in v1.1
5. If feedback indicates low demand: defer indefinitely or reprioritize differently

**This planning document is preserved for future implementation if 4B is approved.**

---

## Design Principles Maintained Throughout

✓ **Export-only architecture** — No CRM writeback in v1  
✓ **System suggests, reviewer decides** — Bulk actions create decisions, don't override judgment  
✓ **Raw data stays unchanged** — No source data mutations  
✓ **Reversibility** — All decisions can be overridden  
✓ **Audit trail** — Complete history of all decisions  
✓ **No mass mutations** — Individual ReviewDecision per item  
✓ **Atomic transactions** — All-or-nothing semantics  
✓ **Type safety** — Frozen dataclasses, explicit decision types  
✓ **No hidden side effects** — Decision creation only, no derived effects  

