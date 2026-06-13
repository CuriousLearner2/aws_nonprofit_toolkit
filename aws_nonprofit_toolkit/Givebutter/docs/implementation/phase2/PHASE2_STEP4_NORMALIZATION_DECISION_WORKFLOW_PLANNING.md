# Phase 2-Step 4: Normalization Decision Workflow Planning

**Date**: 2026-06-12  
**Phase**: 2-Step 4 (Planning)  
**Status**: PLANNING (No implementation)  
**Objective**: Define normalization decision workflow, reusing validation decision pattern

---

## Executive Summary

Phase 2-Step 4 plans the normalization decision workflow, the second reviewer-controlled write workflow. The design mirrors Phase 2-Step 2 (validation decisions) while accounting for normalization-specific semantics: accepting suggests a normalized value for future derived output, without mutating the original ImportContact snapshot.

**Core Principle**: A normalization decision records reviewer intent (accept/reject/defer). The actual resolved value is derived later from the original snapshot plus accepted decisions, not materialized immediately.

---

## 1. Current Normalization Infrastructure Summary

### Current Normalization Route

**Route Handler**: `GET /imports/<import_id>/normalizations` (scripts/uploader/app.py)

- Shows one normalization item at a time (current_suggestion)
- Navigation buttons: Previous, Next, Back to Dashboard
- No decision submission yet

**Service Layer**: `normalizations_service.get_normalizations_review(import_id)` (scripts/householder/normalizations_service.py:15)

- Calls repository to fetch normalizations data
- Returns NormalizationPageViewModel
- No write capability

**Template**: `scripts/uploader/templates/imports/normalizations.html`

- Displays current normalization item
- Shows original vs. suggested values
- Has three buttons: Confirm, Reject, Defer (currently placeholders)
- Shows progress: "Suggestion X of Y"
- Safety strip: "Raw import rows remain unchanged. Confirmed suggestions affect export staging only."

### Current View Model Shape

**NormalizationRow** (service_contracts.py:156):
```python
@dataclass(frozen=True)
class NormalizationRow:
    id: str                            # Review item ID
    contact_name: str
    field_name: str                   # e.g., "email"
    original_value: str               # e.g., "jane@gmai.com"
    suggested_value: str              # e.g., "jane@gmail.com"
    normalization_type: str           # e.g., "typo_correction"
    status: str = "Pending"           # Currently not derived from decisions
```

**NormalizationPageViewModel** (service_contracts.py:185):
```python
@dataclass(frozen=True)
class NormalizationPageViewModel:
    batch_id: str
    filename: str
    progress: int                      # Percentage of items with decisions
    current_suggestion: NormalizationRow
    current_suggestion_index: int
    total_suggestions: int
```

### Current Normalization ReviewItem Payload

**From ingestion_service.py**, normalization items created with:

```json
{
    "field": "email",                           # Field name being normalized
    "raw_value": "jane@gmai.com",              # Original value from ImportContact
    "normalized_value": "jane@gmail.com",      # Suggested normalized value
    "basis": "processor suggestion",            # How suggestion was derived
    "confidence": 0.85                          # Confidence score
}
```

**Note**: Payload stored in ReviewItem.payload_json, which remains immutable.

---

## 2. Proposed Normalization Decisions

### Decision Types (Normalization Only)

For normalization items (field_name, original_value, suggested_value present in payload):

| Decision | Meaning | Closes Item? | Status After |
|----------|---------|--------------|--------------|
| `accept_normalization` | Reviewer accepts suggested normalized value for export/resolution | Yes | `accepted` |
| `reject_normalization` | Reviewer rejects suggested value; original remains authoritative | Yes | `rejected` |
| `defer` | Reviewer defers decision for later review | No | `deferred` |

### Decision Semantics

- **accept_normalization**: Reviewer approves the suggested value. Future export/resolution logic can use this decision. Original ImportContact snapshot unchanged.
  - Example: User confirms typo correction (jane@gmai.com → jane@gmail.com)

- **reject_normalization**: Reviewer determines suggestion is incorrect. Original value is correct. No further action needed.
  - Example: Capitalization suggestion rejected ("John Smith" → "john smith")

- **defer**: Decision not made now. Item remains open for later review.
  - Example: Reviewer unsure about address normalization, needs more context

### Multiple Decisions Per Item

**Allowed**: Yes. Latest decision is current state.

**Rationale**: Reviewer may reconsider. Each decision logged in audit trail.

**Example**:
1. Reviewer records `defer` (undecided)
2. Later, reviewer records `accept_normalization` (decided to accept)
3. Item status is now `accepted`

---

## 3. Decision Payload and Reviewed Values

### ReviewDecision.reviewed_values for Accepted Normalization

When `decision='accept_normalization'`, store in reviewed_values:

```json
{
    "field": "email",
    "raw_value": "jane@gmai.com",
    "normalized_value": "jane@gmail.com",
    "notes": "Typo correction confirmed"
}
```

### ReviewDecision.reviewed_values for Rejected Normalization

When `decision='reject_normalization'`, store:

```json
{
    "field": "email",
    "raw_value": "jane@gmai.com",
    "normalized_value": "jane@gmail.com",
    "rejection_reason": "User confirmed value is correct",
    "notes": "Original is correct, not a typo"
}
```

### ReviewDecision.reviewed_values for Deferred

When `decision='defer'`, store:

```json
{
    "field": "email",
    "raw_value": "jane@gmai.com",
    "normalized_value": "jane@gmail.com",
    "notes": "Deferring for later review"
}
```

**Rationale**: Preserve field names and values for audit trail and future export logic. Field values extracted from ReviewItem.payload_json server-side (not from hidden form fields).

---

## 4. Database Write Boundary

### Allowed Writes

```text
review_decisions (append only)
audit_log (append only)
```

### Forbidden Writes

```text
raw_import_rows (immutable)
import_contacts (immutable)
review_items.status (derived only, see below)
review_items.payload_json (immutable)
import_batches (immutable)
```

### Status Derivation (Not Mutation)

**Conservative Approach**: Do **not** update `review_items.status` during Phase 2-Step 5.

Instead, derive effective status dynamically:

```python
def get_effective_status(review_item_id: int, session) -> str:
    """
    Derive current status from latest ReviewDecision.
    
    If no decision exists: return 'pending'
    If latest decision is 'accept_normalization': return 'accepted'
    If latest decision is 'reject_normalization': return 'rejected'
    If latest decision is 'defer': return 'deferred'
    """
    latest_decision = session.query(ReviewDecision).\
        filter_by(review_item_id=review_item_id).\
        order_by(ReviewDecision.created_at.desc()).\
        first()
    
    if not latest_decision:
        return 'pending'
    
    decision_map = {
        'accept_normalization': 'accepted',
        'reject_normalization': 'rejected',
        'defer': 'deferred',
    }
    
    return decision_map.get(latest_decision.decision, 'pending')
```

---

## 5. Effective Status Behavior

### Status Mapping

| Latest Decision | Effective Status |
|-----------------|------------------|
| (No decision) | Pending |
| `accept_normalization` | Accepted |
| `reject_normalization` | Rejected |
| `defer` | Deferred |

### Multiple Decisions

- Latest decision (by created_at DESC) determines effective status
- Full history preserved in ReviewDecision table
- Audit trail complete

### Display Semantics

- **Pending** (gray): No decision recorded
- **Accepted** (green): Reviewer accepted the suggested value
- **Rejected** (red): Reviewer rejected the suggestion
- **Deferred** (blue): Reviewer deferred decision

---

## 6. Proposed Route/API Shape

### Decision Recording Route

**Route**: `POST /imports/<import_id>/normalizations/<int:review_item_id>/decision`

**Request Format**: HTML form POST

```html
<form method="POST" action="/imports/{{ batch.id }}/normalizations/{{ item_id }}/decision">
  <input type="hidden" name="csrf_token" value="...">
  
  <label for="decision">Decision:</label>
  <select name="decision" required>
    <option value="">-- Select Decision --</option>
    <option value="accept_normalization">Accept Normalization</option>
    <option value="reject_normalization">Reject Normalization</option>
    <option value="defer">Defer</option>
  </select>
  
  <label for="notes">Notes (optional):</label>
  <textarea name="notes" placeholder="Any context for this decision..."></textarea>
  
  <button type="submit">Record Decision</button>
</form>
```

**Request Parameters**:

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| `decision` | string | Yes | `accept_normalization` | One of three values |
| `notes` | string | No | "User confirmed typo" | Optional context |
| (implicit) `reviewer` | string | No | (from header) | From X-Reviewer-ID header |

**Response Behavior**:

- **Success**: HTTP 303 redirect to `/imports/<import_id>/normalizations`
  - Flash message: "Decision recorded: <decision>"
  - Page refreshes, item shows updated status
- **Validation error**: HTTP 400 with error message
- **Database error**: HTTP 500 with error message

**Note on Hidden Fields**: Do not use hidden form fields for field_name, raw_value, normalized_value. Instead, derive them server-side from ReviewItem.payload_json using review_item_id.

---

## 7. Proposed Service/Write Repository Shape

### Service Function

**File**: `scripts/householder/normalization_decision_service.py` (NEW) or extend validation_decision_service.py

**Option A: Separate Service (Recommended for Phase 2-Step 5)**

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class NormalizationDecisionResult:
    decision_id: int
    review_item_id: int
    decision: str
    effective_status: str  # 'pending', 'accepted', 'rejected', 'deferred'
    audit_log_id: int
    timestamp: datetime

def record_normalization_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> NormalizationDecisionResult:
    """
    Record a normalization decision for a review item.
    
    Appends ReviewDecision and AuditLogRecord atomically.
    Does not mutate ImportContact, RawImportRow, or ReviewItem.status.
    Effective status is derived from latest decision.
    
    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'accept_normalization', 'reject_normalization', 'defer'
        notes: Optional context for the decision
        reviewer: Reviewer identifier
        config: Optional configuration for database selection
    
    Returns:
        NormalizationDecisionResult with decision_id, effective_status, etc.
    
    Raises:
        ValueError: If validation fails
        DatabaseError: If transaction fails
    """
    # Validate decision value
    valid_decisions = {'accept_normalization', 'reject_normalization', 'defer'}
    if decision not in valid_decisions:
        raise ValueError(f"Invalid decision '{decision}'...")
    
    # Get write repository and delegate
    write_repo = _get_normalization_decision_writer(config)
    return write_repo.create_normalization_decision(...)
```

**Option B: Refactor Validation Writer to Generic (Alternative)**

If duplication becomes excessive, refactor into generic `record_review_decision()` that handles both validation and normalization based on item_type.

**Recommendation for Planning**: Option A (Separate). Refactor only if duplication becomes severe across 3+ decision types.

### Write Repository

**File**: Separate or extended `database_write_repository.py`

**Class**: `DatabaseNormalizationDecisionWriter` (mirroring `DatabaseValidationDecisionWriter`)

**Method**: `create_normalization_decision()`

**Workflow**:
1. Validate import exists, item exists, item type is 'normalization'
2. Query ReviewItem.payload_json to extract field_name, raw_value, normalized_value
3. Build reviewed_values JSON with field, raw_value, normalized_value, notes
4. Create ReviewDecision record
5. Create AuditLogRecord with decision details
6. Commit atomically
7. Return NormalizationDecisionResult with effective_status

---

## 8. Audit Behavior

### AuditLogRecord Entry for Normalization Decision

**Fields to populate**:

```python
AuditLogRecord(
    batch_id=import_id,
    action_type='decision_recorded',
    action_timestamp=datetime.utcnow(),
    actor=reviewer,
    item_id=review_item_id,
    decision_id=decision.id,
    details={
        'decision_type': 'normalization_decision',
        'decision_value': decision,                    # accept/reject/defer
        'field': field_name,                           # from payload_json
        'raw_value': raw_value,                        # from payload_json
        'normalized_value': normalized_value,          # from payload_json
        'notes': notes,
        'prior_status': prior_status,                  # status before this decision
        'effective_status': effective_status,          # status after this decision
    }
)
```

**Audit trail ensures**:
- Full decision history for each item
- Field names and values preserved
- Reviewer identity captured
- Timestamp recorded
- Context notes included

---

## 9. UI Behavior

### Current Template Structure

Normalization page already has:
- One-at-a-time display (current_suggestion)
- Original vs. Suggested side-by-side
- Field name, contact name, normalization type displayed
- Buttons: Confirm, Reject, Defer (currently placeholders)
- Navigation: Previous, Next, Back to Dashboard
- Progress bar and counter

### Minimal UI Changes

**Phase 2-Step 5 should**:
1. Wire buttons to POST route
2. Show effective status badge
3. Possibly add a decision form or modal

**Phase 2-Step 5 should NOT**:
1. Redesign the page
2. Change navigation structure
3. Add bulk normalization actions
4. Change the one-at-a-time flow

### Status Display

Add effective status badge showing:
- Pending (gray) if no decision
- Accepted (green) if accepted
- Rejected (red) if rejected
- Deferred (blue) if deferred

Placement: Next to current suggestion, or replace current "status" display.

---

## 10. Error Handling

### Validation Errors (HTTP 400)

| Error | Message |
|-------|---------|
| Invalid decision | "Invalid decision '{value}'. Must be one of: accept_normalization, reject_normalization, defer" |
| Unknown import | "Import batch '{batch_id}' not found" |
| Unknown item | "Review item {item_id} not found" |
| Wrong batch | "Review item {item_id} does not belong to batch '{batch_id}'" |
| Wrong type | "Review item {item_id} is not a normalization item (type: {type})" |
| Malformed payload | "Normalization payload missing field/raw_value/normalized_value" |
| No database config | "Normalization decision recording requires database configuration..." |

### Database Errors (HTTP 500)

- Connection failures
- Transaction errors
- Constraint violations

### Rollback Behavior

- If ReviewDecision creation fails: No AuditLogRecord created
- If AuditLogRecord creation fails: Both rolled back (atomic)
- If transaction commits: Both records persist

---

## 11. Test Strategy

### Unit Tests

**File**: `tests/unit/test_normalization_decision_service.py`

**Test Cases**:
- Valid accept_normalization accepted
- Valid reject_normalization accepted
- Valid defer accepted
- Invalid decision rejected
- Empty decision rejected
- Missing database config rejected
- Unknown import rejected
- Unknown item rejected

**Total**: ~8 unit tests

### Integration Tests

**File**: `tests/integration/test_normalization_decision_route.py`

**Test Cases**:
- Valid decision creates ReviewDecision
- Valid decision creates AuditLogRecord
- Decision and audit created atomically
- Raw import rows unchanged
- Import contacts unchanged
- review_items.status unchanged
- review_items.payload_json unchanged
- Invalid decision returns 400
- Wrong item type rejected
- Item from wrong import rejected
- Multiple decisions allowed
- Latest decision determines status
- Reviewer identity from header
- Notes stored in reviewed_values
- Field/raw/normalized values stored

**Total**: ~15 integration tests

### UI Tests

**File**: `tests/integration/test_normalization_decision_ui.py`

**Test Cases**:
- Normalization page renders decision form
- Form posts to correct route
- Status badge displays
- Valid form submission creates ReviewDecision
- Accepted shows green badge
- Rejected shows red badge
- Deferred shows blue badge
- Raw rows unchanged
- Import contacts unchanged
- No other decision types in form

**Total**: ~10 UI tests

---

## 12. Explicit Non-Goals

### Not Included in Phase 2-Step 5

#### Normalization Value Application
- **NOT**: Apply normalized values to ImportContact
- **NOT**: Materialize resolved values in contact snapshot
- **Approach**: Store decisions; derive values later during export

#### Export Value Generation
- **NOT**: Generate export CSV with resolved values
- **NOT**: Apply all accepted normalizations to exports
- **DEFER**: Export generation to Phase 2-Step 6+

#### Export File Creation
- **NOT**: Create export files
- **NOT**: Trigger export on normalization decisions
- **Defer**: Export generation to Phase 2-Step 6+

#### CRM/Givebutter Writeback
- **NOT**: Call Givebutter API
- **NOT**: Sync normalized values
- **DEFER**: CRM integration to Phase 2-Step 7+

#### Other Decision Types
- **NOT**: Implement duplicate decisions
- **NOT**: Implement household decisions
- **DEFER**: These to Phase 2-Step 6+

#### Bulk Actions
- **NOT**: Record decisions for multiple items at once
- **START**: Single-item decisions only
- **DEFER**: Bulk actions to Phase 2-Step 6+

#### Auto-Actions
- **NOT**: Auto-apply accepted normalizations
- **NOT**: Cascade decisions to related items
- **APPROACH**: Each decision is explicit, manual, per-item

#### Authentication
- **NOT**: Implement auth system
- **APPROACH**: Accept reviewer from X-Reviewer-ID header

---

## 13. Key Workflow Decisions

### Status Derivation (Like Validation)

**Decision**: Derive effective status from latest ReviewDecision, do not mutate review_items.status.

**Why**: Keeps ReviewItem immutable, status history in ReviewDecision table.

### Separate Service (Conservative)

**Decision**: Create `normalization_decision_service.py` separate from validation_decision_service.

**Why**: Allows independent testing, cleaner separation of concerns, easier to refactor later if patterns emerge.

### No Value Application

**Decision**: Do not apply normalized values to ImportContact. Store decisions; derive values on export.

**Why**: Preserves immutability of ImportContact snapshot, full audit trail of decisions, allows future policy changes on export generation.

---

## 14. Recommended Phase 2-Step 5 Implementation Prompt

Once this plan is accepted, Phase 2-Step 5 will implement the workflow:

**Phase 2-Step 5 Prompt**:

> Phase 2-Step 5: Implement Normalization Decision Workflow
>
> Implement the normalization decision workflow as planned in Phase 2-Step 4 planning document.
>
> Tasks:
> 1. Create `scripts/householder/normalization_decision_service.py` with `record_normalization_decision()` function
> 2. Extend `scripts/householder/database_write_repository.py` with `DatabaseNormalizationDecisionWriter` implementation
> 3. Modify `scripts/uploader/app.py` to add POST /imports/<import_id>/normalizations/<item_id>/decision route
> 4. Update service_contracts.py to add effective_status to NormalizationRow (if not already done)
> 5. Update normalizations.html template to wire decision buttons and display status badges
> 6. Create `tests/unit/test_normalization_decision_service.py` with unit tests (~8 tests)
> 7. Create `tests/integration/test_normalization_decision_route.py` with integration tests (~15 tests)
> 8. Create `tests/integration/test_normalization_decision_ui.py` with UI tests (~10 tests)
> 9. Verify 951 + ~33 tests passing (no regressions)
> 10. Create Phase 2-Step 5 completion record
>
> Reference: docs/implementation/phase2/PHASE2_STEP4_NORMALIZATION_DECISION_WORKFLOW_PLANNING.md

---

## Files Inspected

1. `scripts/householder/normalizations_service.py` - Read-only service layer
2. `scripts/uploader/app.py` - GET normalizations route
3. `scripts/uploader/templates/imports/normalizations.html` - Template structure
4. `scripts/householder/service_contracts.py` - NormalizationRow, NormalizationPageViewModel
5. `scripts/householder/database_repository.py` - get_normalizations() method
6. `scripts/householder/ingestion_service.py` - ReviewItem payload structure for normalizations
7. `tests/unit/test_normalizations_service.py` - Current tests (read-only)
8. `tests/integration/test_normalizations_route.py` - Current tests (read-only)

---

## Summary

**Phase 2-Step 4 Planning is complete.**

### Key Design Decisions

1. **Decision Types**: accept_normalization, reject_normalization, defer (3 types)
2. **Status Mapping**: Pending/Accepted/Rejected/Deferred (4 states)
3. **Immutability**: No ImportContact mutations; decisions store intent only
4. **Status Derivation**: Effective status from latest ReviewDecision
5. **Route**: POST /imports/<import_id>/normalizations/<item_id>/decision
6. **Service**: Separate `normalization_decision_service.py` (mirrors validation pattern)
7. **Audit**: Full details in AuditLogRecord (field, values, notes, status, reviewer)
8. **UI**: Minimal changes to existing template; wire buttons, show status badges
9. **Tests**: ~33 new tests (8 unit + 15 integration + 10 UI)

### Open Questions / Future Work

1. **Effective Status Display**: Should normalization page show current effective status? Recommend yes (like validation page).

2. **Generic Writer Refactor**: After Phase 2-Step 5, if Phase 2-Step 6 adds duplicate/household decisions, consider refactoring into generic decision writer.

3. **Export Value Derivation**: Phase 2-Step 6+ will define how to resolve export values from original snapshot + accepted decisions.

### Blockers

None identified. All required database tables exist (ReviewItem, ReviewDecision, AuditLogRecord). All read-side infrastructure in place.

---

**Planning Verification**:

- ✅ Current normalization infrastructure documented
- ✅ Proposed decision types and semantics defined
- ✅ Write boundary clarified
- ✅ Effective status behavior specified
- ✅ Route/API shape proposed
- ✅ Service layer design documented
- ✅ Audit behavior specified
- ✅ UI behavior defined (minimal)
- ✅ Error handling planned
- ✅ Test strategy documented
- ✅ Non-goals enumerated
- ✅ Implementation prompt ready

**Status**: ✅ PLANNING COMPLETE  
**Next Step**: Phase 2-Step 5 implementation (when approved)
