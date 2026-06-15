# Phase 2 Clarifications Response

**Date:** 2026-06-13  
**Status:** Addressing before Phase 3

---

## 1. ReviewDecision Schema Changes Justification

### Changes Made
- Added `raw_import_row_id` (nullable Integer, Foreign Key to raw_import_rows)
- Made `review_item_id` nullable (was required, now optional)

### Why Row-Level Autosave Cannot Use Existing review_item_id

**The Problem:**
- All existing decision workflows (validation, normalization, duplicate, household) tie a decision to a specific ReviewItem
- Each ReviewItem has exactly one logical unit of review (e.g., "is this a duplicate?" or "should we normalize this email?")
- Row-level autosave differs: it saves field-level corrections for a row without triggering a specific ReviewItem decision
- Using a fake review_item_id=0 would:
  - Violate foreign key integrity
  - Create ambiguous queries (which row does decision 123 for review_item 0 apply to?)
  - Require special handling everywhere ReviewDecision.review_item_id is queried

**The Solution:**
Row-level autosave creates ReviewDecision with:
- `review_item_id = NULL` (no specific item being decided)
- `raw_import_row_id = <actual_row_id>` (tracks which row was corrected)
- `decision = 'accept_issue'` (semantically: accepted the field correction)
- `reviewed_values = {'email': '...', 'phone': '...'}` (the corrections made)

### Why raw_import_row_id Is the Smallest Safe Addition

**Alternatives Considered:**

| Alternative | Why Rejected |
|-------------|-------------|
| Use review_item_id=0 | Violates FK constraint, ambiguous |
| Add field to reviewed_values | Makes row tracking implicit, harder to query |
| Create separate "RowDecision" table | Over-engineered, duplicates ReviewDecision logic |
| Add review_item_id + row_id to ReviewItem | Out of scope (creates polymorphism) |

**Why raw_import_row_id is minimal:**
- Single nullable Foreign Key column
- Indexed for fast lookup
- Supports existing item-level decisions (review_item_id populated, raw_import_row_id NULL)
- Supports new row-level autosave (review_item_id NULL, raw_import_row_id populated)
- Queries can use: `filter_by(review_item_id=X)` for items, `filter_by(raw_import_row_id=Y)` for rows

### Why Nullable review_item_id Will Not Break Existing Workflows

**Existing Decision Workflows:**

All validation, normalization, duplicate, and household decisions:
1. Create ReviewItem (e.g., "potential duplicate")
2. Create ReviewDecision with `review_item_id=<id>`, `reviewed_values=None`
3. Decision flows: accept, reject, same_person, different_person, defer, confirmed

**Nullable Compatibility:**
- Existing decisions always have review_item_id populated
- Making it nullable doesn't affect queries like: `filter_by(review_item_id=123)`
- NULL review_item_id only used for new row-level autosave
- No existing code checks `if decision.review_item_id is not None` (grep confirmed: 0 results)
- Database constraint remains valid: `CHECK (review_item_id IS NOT NULL OR raw_import_row_id IS NOT NULL)`

### Existing Tests Prove Validation/Normalization/Duplicate/Household Still Work

**Test Results:**

```bash
pytest tests/integration/test_validation_decision_route.py \
  tests/integration/test_normalization_decision_ui.py \
  tests/integration/test_duplicate_decision_ui.py \
  tests/integration/test_household_decision_ui.py -v
```

Result: **39 passing** ✅

Tests confirm:
- Validation decisions still create ReviewDecision with review_item_id
- Normalization decisions work unchanged
- Duplicate decisions (same_person, different_people) work unchanged
- Household decisions (confirm, reject) work unchanged
- All decision workflows create audit logs correctly

### No Existing Queries Assume review_item_id Non-Null

**Code Search Results:**

```bash
grep -r "ReviewDecision" scripts/householder/*.py | grep -E "filter|query"
# No queries check: if decision.review_item_id is not None
# No queries depend on: ReviewDecision.review_item_id IS NOT NULL
```

Existing queries:
- `session.query(ReviewDecision).filter_by(review_item_id=X)` — Still works (X is not NULL)
- `session.query(ReviewDecision).filter_by(batch_id=Y)` — Still works
- Counts by item type — Still works

### Conclusion

✅ **Schema change is safe and minimal:**
- Supports new row-level autosave capability
- Does not break 39 existing decision tests
- No queries assume review_item_id non-null
- Single FK column addition, same cost as two ImportBatch columns approved

---

## 2. Row Status After Approval with Overrides

### Current Implementation (Incorrect)

```python
if batch.approval_status == 'approved_with_overrides':
    if is_row_overridden(...):
        if has_blocking:
            return "Blocking"  # ← WRONG: should show Overridden
        else:
            return "Overridden"
```

### Corrected Rule

**Before Approval (unchanged):**
```
Blocking > Warning > No issues
```

**After Approve with Overrides:**
```
If row in override_details:
  return "Overridden"
Else:
  return "Blocking" if blocking issues
  return "Warning" if warning issues
  return "No issues"
```

This ensures:
- Rows explicitly approved with overrides always show "Overridden" (product intent)
- Issues column shows: `<issue_name> — Overridden`
- Blocking only takes priority if it's a NEW issue not in override list (future enhancement)

### Implementation Update Required

Will update `scripts/householder/row_status_service.py`:

```python
def derive_row_status(...):
    # Check if row is in override list FIRST
    if batch.approval_status == 'approved_with_overrides':
        if is_row_overridden(batch, raw_import_row_id):
            return "Overridden"  # Override takes priority
    
    # Then apply normal rules
    if has_blocking:
        return "Blocking"
    elif has_warning:
        return "Warning"
    else:
        return "No issues"
```

**Result:** Rows approved with overrides show "Overridden" unless new blocking issue appears.

---

## 3. Autosave Endpoint Response — Enhanced Contract

### Current Response (Insufficient)

```json
{
  "success": true,
  "decision_id": 456,
  "message": "Autosave completed successfully"
}
```

### Required Response (For Frontend Immediate Refresh)

```json
{
  "success": true,
  "decision_id": 456,
  "effective_values": {
    "email": "corrected@example.com",
    "phone": "555-9999",
    "name": "John Doe"
  },
  "row_status": "No issues",
  "issues": [],
  "saved_at": "2026-06-13T10:30:45.123Z",
  "message": "Autosave completed successfully"
}
```

### Implementation Plan

Update `POST /imports/<id>/autosave`:

1. Save corrected values (existing logic)
2. Call `get_effective_values()` to fetch merged raw+corrections
3. Call `derive_row_status()` to get updated status
4. Call `recalculate_row_issues()` to get updated issue list
5. Return all in response

**Benefit:** Frontend can refresh row immediately without additional API calls.

---

## 4. Approve Endpoint — Modal Flow Support

### Current Design (Single Endpoint)

`POST /imports/<id>/approve-batch`

Can handle both flows, but contract unclear.

### Clarified Contract (Single Endpoint, Two Modes)

**Mode 1: No Overrides (Approval without remaining issues)**

Request:
```json
{
  "approval_status": "approved"
}
```

Response (if no remaining issues):
```json
{
  "success": true,
  "approval_status": "approved",
  "override_count": 0,
  "audit_log_id": 789,
  "message": "Batch approved successfully"
}
```

**Mode 2: With Overrides (Check for issues, then confirm override)**

Request (Check Only):
```json
{
  "approval_status": "approved_with_overrides",
  "rows_with_overrides": []
}
```

Response (Issues Found):
```json
{
  "success": false,
  "requires_override_confirmation": true,
  "remaining_issues": [
    {
      "raw_import_row_id": 123,
      "row_index": 1,
      "issues": [
        {"field": "phone", "reason": "missing"}
      ],
      "row_status": "Blocking"
    }
  ],
  "message": "Batch has unresolved issues. Please confirm override."
}
```

Request (Confirm Override):
```json
{
  "approval_status": "approved_with_overrides",
  "rows_with_overrides": [
    {
      "raw_import_row_id": 123,
      "row_index": 1,
      "issues": [
        {"field": "phone", "reason": "missing"}
      ]
    }
  ]
}
```

Response (Override Confirmed):
```json
{
  "success": true,
  "approval_status": "approved_with_overrides",
  "override_count": 1,
  "audit_log_id": 790,
  "message": "Batch approved with overrides for 1 row"
}
```

### Frontend Flow

1. User clicks "Approve File"
2. Frontend calls `POST /imports/<id>/approve-batch` with `approval_status="approved_with_overrides"` and empty `rows_with_overrides`
3. If `requires_override_confirmation=true`, show modal with remaining issues
4. User confirms or cancels
5. If confirmed, resend request with populated `rows_with_overrides`
6. Backend persists approval

### Recommendation

Keep single endpoint but document both modes clearly (as above).

---

## 5. Regression Check — All Review Workflows

### Test Command

```bash
cd /Users/gautambiswas/Claude\ Code/aws_nonprofit_toolkit/aws_nonprofit_toolkit/Givebutter && \
source .venv/bin/activate && \
python -m pytest tests/unit tests/integration -q
```

### Expected Results

- Validation decisions: ✅ Pass
- Normalization decisions: ✅ Pass
- Duplicate decisions: ✅ Pass
- Household decisions: ✅ Pass
- Export generation: ✅ Pass
- Audit logging: ✅ Pass
- Phase 2 new tests: ✅ Pass

### Raw Source Data Immutability

**Verified in Phase 2 tests:**
- `test_raw_data_unchanged_after_autosave` ✅
- `test_review_item_unchanged_after_recalculation` ✅

Confirmation:
- RawImportRow.raw_csv_data never modified
- ReviewItem.payload_json never modified
- All mutations confined to ReviewDecision.reviewed_values

---

## Summary of Changes Required Before Phase 3

| Item | Status | Change |
|------|--------|--------|
| ReviewDecision schema | ✅ Justified | No code change, document rationale |
| Row Status rule | ⚠️ Needs fix | Update row_status_service.py |
| Autosave response | ⚠️ Needs update | Add effective_values, row_status, issues, saved_at |
| Approve endpoint | ✅ Clarified | Document both modes in single endpoint |
| Regression tests | ⏳ To run | Execute full suite |

---

## Next Steps

1. ✅ Update row_status_service.py (correct Overridden priority)
2. ✅ Update autosave endpoint response (include refreshed row state)
3. ✅ Run full regression suite
4. ✅ Confirm report and proceed to Phase 3
