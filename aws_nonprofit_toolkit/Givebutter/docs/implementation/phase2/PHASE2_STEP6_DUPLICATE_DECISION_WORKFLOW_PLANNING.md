# Phase 2-Step 6: Duplicate Decision Workflow Planning

**Date**: 2026-06-12  
**Phase**: 2-Step 6 (Planning)  
**Status**: PLANNING (No implementation)  
**Objective**: Define duplicate decision workflow, reusing validation/normalization decision pattern

---

## Executive Summary

Phase 2-Step 6 plans the duplicate decision workflow, the third reviewer-controlled write workflow. The design mirrors Phase 2-Step 2/Step 5 (validation and normalization decisions) while accounting for duplicate-specific semantics: a decision records whether contacts represent the same person within this import batch, without merging or deleting anything.

**Core Principle**: A duplicate decision records reviewer intent only (same_person, different_people, or defer). The decision preserves candidate contact information for potential future export/merge logic, but does not perform any mutation, merge, or deletion.

---

## 1. Current Duplicate Infrastructure Summary

### Current Duplicate Route

**Route Handler**: `GET /imports/<import_id>/duplicates` (scripts/uploader/app.py)

- Shows one duplicate candidate pair at a time
- Displays contact_a and contact_b side-by-side
- Shows supporting and conflicting evidence
- Has three placeholder buttons: Mark as Same Person, Different Person, Defer
- No decision submission route exists yet

### Current Service Layer

**Service Function**: `duplicates_service.get_duplicates_review(import_id)`

- Calls repository to fetch duplicate candidate data
- Returns DuplicatePageViewModel
- No write capability yet

### Current Template

**Template**: `scripts/uploader/templates/imports/duplicates.html`

- Side-by-side contact comparison (contact_a vs contact_b)
- Displays supporting evidence (green checkmarks)
- Displays conflicting evidence (red X marks)
- Optional notes textarea (required when conflicting evidence exists)
- Three buttons with data-action attributes (not wired to routes yet)
- Safety message: "Mark as Same Person records a reviewer decision only. Raw import rows remain unchanged."
- Navigation buttons: Previous/Next pair, Back to Dashboard

### Current View Model Shape

**DuplicateCandidate** (service_contracts.py:301):
```python
@dataclass(frozen=True)
class DuplicateCandidate:
    id: str
    contact_a: DuplicateContact
    contact_b: DuplicateContact
    supporting_evidence: tuple
    conflicting_evidence: tuple
    status: str = "Pending"  # Currently hardcoded, not derived
```

**DuplicatePageViewModel** (service_contracts.py:328):
```python
@dataclass(frozen=True)
class DuplicatePageViewModel:
    batch_id: str
    filename: str
    progress: int
    current_candidate: DuplicateCandidate
    current_candidate_index: int
    total_candidates: int
```

### Current Duplicate ReviewItem Payload

**From fixture data** (scripts/uploader/fixtures.py:94-173):

```json
{
    "id": "DUP-001",
    "contact_a": {
        "id": "P-001",
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "(555) 123-4567",
        "address": "123 Main St, Springfield, IL 62701"
    },
    "contact_b": {
        "id": "P-006",
        "name": "John Smith",
        "email": "jsmith@email.com",
        "phone": "(555) 123-4567",
        "address": "123 Main Street, Springfield, IL 62701"
    },
    "supporting_evidence": [
        "Full name match",
        "Phone match",
        "Address match (minor formatting)"
    ],
    "conflicting_evidence": [
        "Different email addresses"
    ],
    "status": "Pending"
}
```

**Note**: Ingestion service does not yet create duplicate ReviewItems. These come from fixture data only.

### Current Empty-State Behavior

- If no duplicate candidates exist, page shows empty DuplicateCandidate with blank fields
- Total candidates = 0
- Safety message still displayed
- No error message

---

## 2. Proposed Duplicate Decisions

### Decision Types

| Decision | Meaning | Closes Item? | Semantics |
|----------|---------|--------------|-----------|
| `same_person` | Reviewer decides contacts represent the same real person within this batch | Yes | Intent: these imported snapshots are the same individual |
| `different_people` | Reviewer decides contacts are different people (false positive) | Yes | Intent: these are distinct individuals |
| `defer` | Reviewer leaves decision open for later review | No | Intent: undecided, needs more context |

### Decision Semantics

- **same_person**: Reviewer has reviewed the evidence and confirmed the two imported contact snapshots represent the same real person **for this batch**. This is a reviewer decision only. It does NOT:
  - Merge contact records
  - Delete either contact
  - Mutate ImportContact snapshots
  - Generate a merged person record
  - Write back to Givebutter/CRM

  It records intent for potential future export logic or analyst review.

- **different_people**: Reviewer has determined the contacts are not the same person (false positive duplicate candidate). This is purely intent recording.

- **defer**: Reviewer has deferred the decision pending more information. Item remains open.

### Multiple Decisions Per Item

**Allowed**: Yes. Latest decision is current state.

**Rationale**: Reviewer may reconsider. Each decision logged in audit trail.

**Example**:
1. Reviewer records `defer` (undecided)
2. Later, reviewer records `same_person` (decided after reviewing more context)
3. Item status is now `Same Person`

---

## 3. Decision Payload and Reviewed Values

### ReviewDecision.reviewed_values for same_person

Store relevant candidate and contact information:

```json
{
    "primary_contact_id": "P-001",
    "secondary_contact_ids": ["P-006"],
    "candidate_contact_ids": ["P-001", "P-006"],
    "evidence_supporting": [
        "Full name match",
        "Phone match",
        "Address match (minor formatting)"
    ],
    "evidence_conflicting": [
        "Different email addresses"
    ],
    "notes": "Confirmed same person despite email variation"
}
```

### ReviewDecision.reviewed_values for different_people

```json
{
    "candidate_contact_ids": ["P-001", "P-006"],
    "notes": "False positive: different individuals with similar names"
}
```

### ReviewDecision.reviewed_values for defer

```json
{
    "candidate_contact_ids": ["P-001", "P-006"],
    "notes": "Need to verify email domain - similar to another batch candidate"
}
```

**Rationale**: Preserve field names and values for audit trail and future export logic. Contact IDs extracted from ReviewItem.payload_json and ReviewItemSubject server-side (not from hidden form fields).

---

## 4. Write Boundary

### Allowed Writes

```text
review_decisions (append only)
audit_log (append only)
```

### Forbidden Writes

```text
raw_import_rows (immutable)
import_contacts (immutable)
review_items.status (derived only)
review_items.payload_json (immutable)
import_batches (immutable)
```

### Status Derivation (Not Mutation)

**Conservative Approach**: Do **not** update `review_items.status` during Phase 2-Step 7 (or ever).

Instead, derive effective status dynamically:

```python
def get_effective_status(review_item_id: int, session) -> str:
    """
    Derive current status from latest ReviewDecision.
    
    If no decision exists: return 'pending'
    If latest decision is 'same_person': return 'same_person'
    If latest decision is 'different_people': return 'different_people'
    If latest decision is 'defer': return 'deferred'
    """
    latest_decision = session.query(ReviewDecision).\
        filter_by(review_item_id=review_item_id).\
        order_by(ReviewDecision.created_at.desc()).\
        first()
    
    if not latest_decision:
        return 'pending'
    
    decision_map = {
        'same_person': 'same_person',
        'different_people': 'different_people',
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
| `same_person` | Same Person |
| `different_people` | Different People |
| `defer` | Deferred |

### Multiple Decisions

- Latest decision (by created_at DESC) determines effective status
- Full history preserved in ReviewDecision table
- Audit trail complete

### Display Semantics

- **Pending** (gray): No decision recorded
- **Same Person** (green): Reviewer confirmed same person
- **Different People** (orange): Reviewer confirmed different people
- **Deferred** (blue): Reviewer deferred decision

---

## 6. Proposed Route/API Shape

### Decision Recording Route

**Route**: `POST /imports/<import_id>/duplicates/<int:review_item_id>/decision`

**Request Format**: HTML form POST

```html
<form method="POST" action="/imports/{{ batch.id }}/duplicates/{{ item_id }}/decision">
  <input type="hidden" name="csrf_token" value="...">
  
  <label for="decision">Decision:</label>
  <select name="decision" required>
    <option value="">-- Select Decision --</option>
    <option value="same_person">Mark as Same Person</option>
    <option value="different_people">Mark as Different People</option>
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
| `decision` | string | Yes | `same_person` | One of three values |
| `notes` | string | No | "Confirmed same person" | Optional context |
| (implicit) `reviewer` | string | No | (from header) | From X-Reviewer-ID header |

**Response Behavior**:

- **Success**: HTTP 303 redirect to `/imports/<import_id>/duplicates`
  - Page refreshes, item shows updated status
- **Validation error**: HTTP 400 with error message
- **Database error**: HTTP 500 with error message

**Note on Hidden Fields**: Do not use hidden form fields for contact_a_id, contact_b_id, evidence. Instead, derive them server-side from ReviewItem.payload_json using review_item_id.

---

## 7. Proposed Service/Write Repository Shape

### Service Function

**File**: `scripts/householder/duplicate_decision_service.py`

```python
def record_duplicate_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> DuplicateDecisionResult:
    """
    Record a duplicate decision for a review item.
    
    Appends ReviewDecision and AuditLogRecord atomically.
    Does not mutate ReviewItem, RawImportRow, or ImportContact.
    Effective status is derived from latest decision.
    
    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'same_person', 'different_people', 'defer'
        notes: Optional context for the decision
        reviewer: Reviewer identifier (name or email)
        config: Optional configuration mapping
    
    Returns:
        DuplicateDecisionResult with decision_id, effective_status, etc.
    
    Raises:
        ValueError: If validation fails
        DatabaseError: If write transaction fails
    """
```

### Write Repository

**File**: Extend `scripts/householder/database_write_repository.py`

**Class**: `DatabaseDuplicateDecisionWriter` (mirrors `DatabaseValidationDecisionWriter` and `DatabaseNormalizationDecisionWriter`)

**Method**: `create_duplicate_decision(batch_id, review_item_id, decision, notes, reviewer)`

**Workflow**:
1. Validate import exists, item exists, item type is 'duplicate'
2. Query ReviewItem.payload_json to extract contact_a_id, contact_b_id, evidence
3. Begin transaction
4. Insert ReviewDecision with reviewed_values
5. Insert AuditLogRecord with full decision details
6. Commit transaction
7. Derive effective_status
8. Return DuplicateDecisionResult

**Decision Handling Preference**: Keep separate service and writer (conservative approach, mirrors normalization pattern).

---

## 8. Audit Behavior

### AuditLogRecord Entry for Duplicate Decision

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
        'decision_type': 'duplicate_decision',
        'decision_value': decision,                    # same_person/different/defer
        'primary_contact_id': contact_a_id,
        'secondary_contact_ids': [contact_b_id],
        'candidate_contact_ids': [contact_a_id, contact_b_id],
        'evidence_supporting': supporting_evidence,
        'evidence_conflicting': conflicting_evidence,
        'notes': notes,
        'prior_status': prior_status,                  # status before this decision
        'effective_status': effective_status,          # status after this decision
    }
)
```

**Audit trail ensures**:
- Full decision history for each duplicate candidate
- Contact IDs and evidence preserved
- Reviewer identity captured
- Timestamp recorded
- Context notes included

---

## 9. UI Behavior

### Current Template Structure

Duplicates page already has:
- Side-by-side contact comparison (contact_a vs contact_b)
- Supporting evidence (green checkmarks)
- Conflicting evidence (red X marks)
- Three buttons (Confirm, Reject, Defer) - currently placeholders
- Optional notes field (required when conflicting evidence exists)
- Navigation: Previous, Next, Back to Dashboard
- Progress display and counter

### Minimal UI Changes

**Phase 2-Step 7 should**:
1. Wire buttons to POST route (similar to validation/normalization)
2. Display effective status badge (Pending/Same Person/Different People/Deferred)
3. Add notes form field to decision form
4. Keep existing contact comparison display

**Phase 2-Step 7 should NOT**:
1. Redesign the page layout
2. Change navigation structure
3. Add merge UI or merge buttons
4. Add bulk duplicate decisions
5. Change labels to "Merge" (use neutral decision labels instead)

### Status Display

Add effective status badge showing:
- **Pending** (gray #e5e7eb) if no decision
- **Same Person** (green #dcfce7) if same_person
- **Different People** (orange #fed7aa) if different_people
- **Deferred** (blue #bfdbfe) if defer

Placement: Next to candidate ID or in header area.

### Recommended Button Labels

Instead of "Merge", use:
- **Mark as Same Person** (action: same_person)
- **Mark as Different People** (action: different_people)
- **Defer** (action: defer)

This clarifies that the button records intent, not merges.

---

## 10. Error Handling

### Validation Errors (HTTP 400)

| Error | Message |
|-------|---------|
| Invalid decision | "Invalid decision '{value}'. Must be one of: same_person, different_people, defer" |
| Unknown import | "Import batch '{batch_id}' not found" |
| Unknown item | "Review item {item_id} not found" |
| Wrong batch | "Review item {item_id} does not belong to batch '{batch_id}'" |
| Wrong type | "Review item {item_id} is not a duplicate item (type: {type})" |
| Insufficient candidates | "Duplicate candidate must have at least two subjects (found {count})" |
| Malformed payload | "Duplicate payload missing contact_a/contact_b or evidence fields" |
| No database config | "Duplicate decision recording requires database configuration..." |

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

**File**: `tests/unit/test_duplicate_decision_service.py`

**Test Cases** (~9 tests):
- Valid same_person accepted
- Valid different_people accepted
- Valid defer accepted
- Invalid decision rejected
- Empty decision rejected
- Missing database config rejected
- Unknown import rejected
- Unknown item rejected
- Wrong item type rejected

### Integration Route Tests

**File**: `tests/integration/test_duplicate_decision_route.py`

**Test Cases** (~18 tests):

1. **Decision Recording** (3 tests)
   - Valid decision creates ReviewDecision
   - Valid decision creates AuditLogRecord
   - Decision types recorded correctly (same/different/defer)

2. **Error Handling** (4 tests)
   - Invalid decision returns 400
   - Wrong item type returns 400
   - Unknown item returns 400
   - Insufficient candidates handled safely

3. **Immutability** (4 tests)
   - Raw import rows unchanged
   - Import contacts unchanged
   - ReviewItem.status unchanged
   - ReviewItem.payload_json unchanged

4. **Reviewed Values** (3 tests)
   - Contact IDs stored in audit log
   - Evidence fields stored in audit log
   - Notes stored in reviewed_values

5. **Multiple Decisions** (3 tests)
   - Multiple decisions allowed
   - Latest decision determines status
   - Reviewer identity from header

6. **No Mutations** (1 test)
   - No contacts created, deleted, or merged

### UI Tests

**File**: `tests/integration/test_duplicate_decision_ui.py`

**Test Cases** (~12 tests):
- Duplicates page renders with decision form
- Form posts to correct route
- Status badge displays
- Valid form submission creates ReviewDecision
- Same Person shows green badge
- Different People shows orange badge
- Deferred shows blue badge
- Raw rows unchanged
- Import contacts unchanged
- After decision, page shows updated status
- No merge UI present
- Only duplicate decision types in form (not validation/normalization)

**Total**: ~39 new tests expected

---

## 12. Explicit Non-Goals

### NOT Included in Phase 2-Step 7

#### Contact Merge
- **NOT**: Merge contact records
- **NOT**: Create merged person entry
- **NOT**: Delete either contact
- **NOT**: Update ImportContact fields
- **APPROACH**: Store decision intent only; defer actual merge logic to export/analyst phases

#### Cross-Import Duplicate Matching
- **NOT**: Match duplicates across import batches
- **SCOPE**: Current import batch only
- **DEFER**: Cross-batch deduplication to future phases

#### Automatic Duplicate Resolution
- **NOT**: Auto-merge candidates with 100% supporting evidence
- **NOT**: Auto-accept decisions without reviewer action
- **APPROACH**: All decisions explicit and manual

#### Household Confirmation
- **NOT**: Implement household decision workflow
- **DEFER**: To Phase 2-Step 8

#### Normalization Application
- **NOT**: Apply normalization decisions to duplicate candidates
- **DEFER**: To export/merge logic phases

#### Export Generation
- **NOT**: Generate export CSV with resolved duplicates
- **DEFER**: To Phase 2-Step 9+

#### CRM/Givebutter Writeback
- **NOT**: Call Givebutter API
- **NOT**: Sync deduplicated contacts
- **DEFER**: To Phase 2-Step 10+

#### Bulk Duplicate Decisions
- **NOT**: Record decisions for multiple pairs at once
- **START**: Single-item decisions only
- **DEFER**: Bulk actions to future phases

#### Auto-Actions
- **NOT**: Auto-merge related contacts
- **NOT**: Cascade decisions to other batches
- **APPROACH**: Each decision explicit, manual, per-candidate

#### Authentication
- **NOT**: Implement auth system
- **APPROACH**: Accept reviewer from X-Reviewer-ID header

---

## 13. Key Workflow Decisions

### Status Derivation (Like Validation & Normalization)

**Decision**: Derive effective status from latest ReviewDecision, do not mutate review_items.status.

**Why**: Keeps ReviewItem immutable, status history in ReviewDecision table, consistent with validation/normalization patterns.

### Separate Service (Conservative)

**Decision**: Create `duplicate_decision_service.py` separate from validation/normalization services.

**Why**: Allows independent testing, cleaner separation, easier to refactor if patterns emerge. Duplicates are higher-risk (contact-related decisions), so explicit separation is safer.

### No Contact Merge

**Decision**: Do not merge, delete, or mutate contacts during decision recording.

**Why**: Preserves immutability, full audit trail of decisions, allows flexible merge logic later.

### Button Labels

**Decision**: Use "Mark as Same Person" not "Merge"

**Why**: Clarifies that button records intent, not action.

---

## 14. Recommended Phase 2-Step 7 Implementation Prompt

Once this plan is accepted, Phase 2-Step 7 will implement the workflow:

**Phase 2-Step 7 Prompt**:

> Phase 2-Step 7: Implement Duplicate Decision Workflow
>
> Implement the duplicate decision workflow as planned in Phase 2-Step 6 planning document.
>
> Tasks:
> 1. Create `scripts/householder/duplicate_decision_service.py` with `record_duplicate_decision()` function
> 2. Extend `scripts/householder/database_write_repository.py` with `DatabaseDuplicateDecisionWriter` implementation
> 3. Modify `scripts/uploader/app.py` to add POST /imports/<import_id>/duplicates/<item_id>/decision route
> 4. Update service_contracts.py to add effective_status to DuplicateCandidate (if not already done)
> 5. Update duplicates_service.get_duplicates() to derive effective_status from ReviewDecision
> 6. Update duplicates.html template to wire decision buttons and display status badges
> 7. Create `tests/unit/test_duplicate_decision_service.py` with unit tests (~9 tests)
> 8. Create `tests/integration/test_duplicate_decision_route.py` with integration tests (~18 tests)
> 9. Create `tests/integration/test_duplicate_decision_ui.py` with UI tests (~12 tests)
> 10. Verify 985 + ~39 tests passing (no regressions)
> 11. Create Phase 2-Step 7 completion record
>
> Reference: docs/implementation/phase2/PHASE2_STEP6_DUPLICATE_DECISION_WORKFLOW_PLANNING.md

---

## Files Inspected

1. `scripts/householder/duplicates_service.py` - Read-only service layer
2. `scripts/uploader/app.py` - GET duplicates route (no POST yet)
3. `scripts/uploader/templates/imports/duplicates.html` - Template with placeholder buttons
4. `scripts/householder/service_contracts.py` - DuplicateCandidate and DuplicatePageViewModel
5. `scripts/householder/database_repository.py` - get_duplicates() method
6. `tests/unit/test_duplicates_service.py` - Current unit tests (read-only)
7. `scripts/uploader/fixtures.py` - Fixture duplicate candidate data

---

## Summary

**Phase 2-Step 6 Planning is complete.**

### Key Design Decisions

1. **Decision Types**: same_person, different_people, defer (3 types)
2. **Status Mapping**: Pending/Same Person/Different People/Deferred (4 states)
3. **Immutability**: No contact merges/mutations; decisions store intent only
4. **Status Derivation**: Effective status from latest ReviewDecision
5. **Route**: POST /imports/<import_id>/duplicates/<item_id>/decision
6. **Service**: Separate `duplicate_decision_service.py` (conservative approach)
7. **Audit**: Full details in AuditLogRecord (contact IDs, evidence, notes, status, reviewer)
8. **UI**: Minimal changes to existing template; wire buttons, show status badges
9. **Tests**: ~39 new tests (9 unit + 18 integration + 12 UI)
10. **Guardrails**: No merges, no deletes, no mutations, no external calls

### Key Workflow Insights

- Current template already has good structure (side-by-side comparison, evidence display)
- Three buttons exist but are not wired to routes yet
- Current status field is hardcoded "Pending", will be derived from ReviewDecision
- No database ReviewItems are created yet for duplicates (fixture data only)
- Semantics differ from validation/normalization: a decision records whether contacts are the same person, not whether data is valid/normalized

### Open Questions / Future Work

1. **Effective Status Display**: Should duplicate page show current effective status? Recommend yes (like validation/normalization pages).

2. **Duplicate Detection in Ingestion**: Should ingestion service create duplicate ReviewItems? Recommend deferring until Phase 3 (full ingestion workflow).

3. **Cross-Batch Matching**: Should future phases support duplicate matching across batches? Recommend deferring to Phase 3+.

### Blockers

None identified. All required database tables exist (ReviewItem, ReviewDecision, AuditLogRecord). All read-side infrastructure in place. Template structure already supports decision workflow.

---

**Planning Verification**:

- ✅ Current duplicate infrastructure documented
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
**Next Step**: Phase 2-Step 7 implementation (when approved)
