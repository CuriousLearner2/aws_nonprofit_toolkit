# Phase 2-Step 8: Household Decision Workflow — Planning Document

**Date**: 2026-06-12  
**Phase**: 2-Step 8 (Planning)  
**Status**: 🔍 PLANNING (No implementation yet)

---

## Executive Summary

Phase 2-Step 8 will implement a household decision workflow enabling reviewers to record decisions on household grouping candidates while preserving strict immutability guardrails. This is the fourth and final decision workflow (following validation, normalization, and duplicate decisions).

**Key Design Principle**: A household decision records reviewer intent only. It does not mutate contacts, does not assign `import_contacts.household_id`, does not create durable household master records, and does not write back to external systems.

**Scope**: This document plans the workflow design. Implementation follows established patterns from validation/normalization/duplicate decision workflows.

---

## Current Household Infrastructure

### Existing GET Route
```
GET /imports/<import_id>/households
```

**Handler**: `scripts/uploader/app.py` line 990–994
```python
@app.route('/imports/<import_id>/households')
def import_households(import_id):
    data = households_service.get_households_review(import_id)
    return render_template('imports/households.html', **data)
```

### Service Layer
**File**: `scripts/householder/households_service.py`
- `get_households_review(import_id, config=None)` → `Dict[str, Any]`
- Calls `repository.get_households(import_id)`
- Returns template-ready dictionary

### Data Model
**ReviewItem.item_type**: `'household'`

**ReviewItem.payload_json shape**:
```json
{
  "id": "HH-001",
  "suggested_name": "Smith Family",
  "address": "123 Main St, Springfield, IL 62701",
  "confidence": "98%",
  "proposed_members": ["John Smith (TXN-001)", "Robert Smith (TXN-003)"],
  "evidence": ["Shared last name: Smith", "Same address"],
  "conflicts": ["Different phone numbers"],
  "status": "Pending"
}
```

### Service Contracts
**HouseholdRow** (`service_contracts.py`):
```python
@dataclass(frozen=True)
class HouseholdRow:
    id: str
    suggested_name: str
    address: str
    confidence: str
    proposed_members: tuple
    evidence: tuple
    conflicts: tuple
    status: str = "Pending"
```

**HouseholdPageViewModel**:
```python
@dataclass(frozen=True)
class HouseholdPageViewModel:
    batch_id: str
    filename: str
    progress: int
    current_household: HouseholdRow
    current_household_index: int
    total_households: int
```

### Template
**File**: `scripts/uploader/templates/imports/households.html`

**Current UI**:
- Displays household suggestion with name, address, confidence
- Shows proposed members list
- Shows supporting evidence (green, checkmarks)
- Shows conflicting evidence (yellow, if any)
- Has placeholder buttons: "Confirm Household", "Reject", "Defer"
- Buttons are not currently wired to any decision route
- Safety message: "Confirmed households affect export staging only. Raw import rows remain unchanged."

**Current Button State**: Buttons exist but do not post to any route (no decision recording yet)

### Repository
**Method**: `DatabaseImportRepository.get_households(import_id)` (line 587)
- Queries ReviewItem with `item_type='household'` and `status='pending'`
- Extracts payload_json for household data
- Returns first household as current candidate
- Computes progress across all review items (not just households)

### Ingestion
**Current State**: Household ReviewItems are not created during ingestion yet. They must be seeded in tests or fixtures.

---

## Proposed Household Decision Workflow

### 1. Allowed Decision Types

Three decisions allowed:

| Decision | Semantics | Effective Status | Usage |
|----------|-----------|-----------------|-------|
| `confirm_household` | Reviewer decides these imported contacts should be treated as a household grouping for this import batch | `confirmed` / Confirmed Household | Accept household grouping |
| `reject_household` | Reviewer decides the household grouping is incorrect | `rejected` / Rejected Household | Reject household grouping |
| `defer` | Reviewer defers decision for later | `deferred` / Deferred | Leave open for later |

**Language Principle**: Avoid terms implying mutation or permanent assignment:
- ✅ `confirm_household` (records intent)
- ❌ `create_household` (implies creation)
- ❌ `assign_household` (implies assignment)
- ❌ `merge_household` (implies merge)
- ❌ `link_household` (implies persistent linking)

### 2. Decision Payload

**ReviewDecision.reviewed_values shape**:
```json
{
  "candidate_household_id": "HH-001",
  "candidate_contact_ids": [123, 124, 125],
  "suggested_household_label": "Smith Family",
  "address": "123 Main St, Springfield, IL",
  "basis": ["Shared last name: Smith", "Same address"],
  "proposed_members_count": 3,
  "notes": "Confirmed same household - all transactions from same address"
}
```

**Key Design Points**:
- Extract candidate info server-side from `ReviewItem.payload_json` and `ReviewItemSubject` joins
- Do not trust hidden form fields for IDs or data
- Preserve sufficient context for auditability
- No household_id assigned to ImportContact
- No durable household record created

### 3. Write Boundary

**Allowed**:
- `ReviewDecision` (append-only, immutable after creation)
- `AuditLogRecord` (append-only, immutable after creation)

**Forbidden**:
- Updating `import_contacts.household_id` (no assignment)
- Creating durable `Household` records
- Mutating `review_items.status` (derive effective status at read time)
- Mutating `review_items.payload_json`
- Mutating `raw_import_rows`
- Mutating `import_contacts`
- Creating/deleting contacts
- Merging contacts
- Generating export files
- CRM/Givebutter writeback
- Cross-import household matching
- Cross-batch household consolidation

### 4. Effective Status Behavior

**Status Mapping**:
```
no decision           → pending / Pending
latest confirm_household → confirmed / Confirmed Household
latest reject_household  → rejected / Rejected Household
latest defer            → deferred / Deferred
```

**Multiple Decisions**:
- Same ReviewItem can have multiple ReviewDecision records (append-only)
- Latest decision (by `created_at desc`) determines effective status
- All prior decisions remain in audit log
- Allow reviewers to change decisions

**No Status Mutation**:
- `review_items.status` stays 'pending' in database
- Effective status derived at read time from latest ReviewDecision

### 5. Route Shape

**Proposed POST Route**:
```
POST /imports/<import_id>/households/<int:review_item_id>/decision
```

**Request Format**:
- Form fields: `decision`, `notes` (optional)
- Header: `X-Reviewer-ID` (optional, for reviewer identification)

**Success Response**:
- HTTP 303 redirect to `/imports/<import_id>/households`

**Validation Error Response**:
- HTTP 400 JSON with error message

**Server Error Response**:
- HTTP 500 JSON with error message

**Example Request**:
```
POST /imports/IMP-2025-0101-A/households/42/decision HTTP/1.1
Content-Type: application/x-www-form-urlencoded

decision=confirm_household&notes=Confirmed%20same%20household

Header: X-Reviewer-ID: reviewer@example.com
```

### 6. Service & Repository Design

**Service Function**:
```python
def record_household_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> HouseholdDecisionResult:
    """
    Record a household decision for a review item.

    Appends ReviewDecision and AuditLogRecord atomically.
    Does not mutate ReviewItem, RawImportRow, or ImportContact.
    Effective status derived from latest decision.

    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'confirm_household', 'reject_household', 'defer'
        notes: Optional context or explanation
        reviewer: Reviewer identifier (name or email)
        config: Optional configuration for database selection

    Returns:
        HouseholdDecisionResult with decision_id, effective_status, audit_log_id, timestamp

    Raises:
        ValueError: If validation fails
        RuntimeError: If database transaction fails
    """
```

**Write Repository Class**:
```python
class DatabaseHouseholdDecisionWriter:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def create_household_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> HouseholdDecisionResult:
        """
        Create household decision and audit log record atomically.

        Workflow:
        1. Validate inputs (batch exists, item exists, item type is 'household')
        2. Extract candidate/member details from ReviewItem.payload_json
        3. Create ReviewDecision with reviewed_values
        4. Create AuditLogRecord with full audit trail
        5. Commit atomically
        6. Return HouseholdDecisionResult with effective_status
        """
```

**Design Decision**: Use separate explicit `household_decision_service.py` and `DatabaseHouseholdDecisionWriter` (not refactored generic writer) to avoid accidentally enabling generalized decision recording and to keep workflows clear and independent.

### 7. Audit Behavior

**AuditLogRecord Details**:

```
action_type = 'decision_recorded'
decision_type = 'household_decision'
details = {
  'decision_type': 'household_decision',
  'decision_value': <decision>,
  'candidate_household_id': <id>,
  'candidate_contact_ids': [<ids>],
  'suggested_household_label': <label>,
  'address': <address>,
  'basis': [<evidence>],
  'proposed_members_count': <count>,
  'notes': <notes>,
  'prior_status': <prior_effective_status>,
  'effective_status': <new_effective_status>,
}
```

**Audit Requirements**:
- Every decision decision creates one AuditLogRecord
- Full context preserved for compliance/review
- No mutation of audit trail (append-only)
- Reviewer identity captured (from X-Reviewer-ID header or None)
- Timestamp captured (UTC)

### 8. UI Behavior

**Minimal Changes to Template**:
- Add effective status badge (similar to validation/normalization/duplicate)
- Wire existing buttons to POST route with decision form
- Keep existing safety message
- Do not redesign page
- Do not add bulk household decisions

**Status Badge Colors**:
```
Pending            → gray (#e5e7eb)
Confirmed Household → green (#d1fae5)
Rejected Household  → orange (#fed7aa)
Deferred           → blue (#dbeafe)
```

**Button Labels** (neutral, intent-only):
```
Confirm Household Suggestion
Reject Household Suggestion
Defer
```

**Avoid Labels** (mutation-implying):
```
❌ Create Household
❌ Assign Household
❌ Link Household
❌ Merge Household
❌ Assign to Household
```

**Form Implementation**:
- Hidden forms for each decision type
- JavaScript submitHouseholdDecision() to extract notes and post
- Follow validation/normalization/duplicate pattern

### 9. Error Handling

**Validation Errors** (400):
- Unknown import_id
- Unknown review_item_id
- Review item belongs to different import
- Review item is not `item_type='household'`
- Invalid decision value
- Household item with < 2 subjects
- Malformed payload

**Server Errors** (500):
- Database unavailable
- Transaction failure
- Unexpected exception

**All errors return clear JSON error message**:
```json
{"error": "Review item not found"}
```

### 10. Test Strategy

**Unit Tests** (`tests/unit/test_household_decision_service.py`, ~10 tests):
1. Valid `confirm_household` accepted
2. Valid `reject_household` accepted
3. Valid `defer` accepted
4. Invalid decision rejected (ValueError)
5. Empty decision rejected
6. Validation/normalization/duplicate decisions rejected
7. Missing database config rejected
8. Notes optional
9. Reviewer optional

**Integration Route Tests** (`tests/integration/test_household_decision_route.py`, ~10-12 tests):
1. Valid decision creates ReviewDecision
2. Valid decision creates AuditLogRecord
3. `confirm_household` recorded correctly
4. `reject_household` recorded correctly
5. `defer` recorded correctly
6. Invalid decision returns 400
7. Wrong item type returns 400
8. Unknown item returns 400
9. RawImportRow unchanged
10. ImportContact unchanged
11. ReviewItem.status unchanged
12. ReviewItem.payload_json unchanged
13. No household master record created
14. Candidate contact IDs stored in reviewed_values
15. Multiple decisions allowed
16. Latest decision wins
17. Reviewer identity captured

**UI Integration Tests** (`tests/integration/test_household_decision_ui.py`, ~6-8 tests):
1. Households page renders
2. Status badge displays Pending
3. Confirm submission creates ReviewDecision
4. Reject submission creates ReviewDecision
5. Defer submission creates ReviewDecision
6. Page has no merge/mutation language
7. Only household decision types in form

**Test Database**:
- Use temporary SQLite with monkeypatch
- Seed household ReviewItems
- Mirror validation/normalization/duplicate test patterns
- Verify immutability with before/after queries

### 11. Explicit Non-Goals

**Out of Scope** (Phase 2-Step 8):
- Durable household master record creation
- Assigning `import_contacts.household_id` (no field mutation)
- Household assignment materialization
- Contact merge/consolidation
- Duplicate resolution
- Export generation
- CRM/Givebutter writeback
- Bulk household decisions
- Cross-import household matching
- Cross-batch household consolidation
- Household master identity
- Auto-confirmation of households
- Auth/login implementation
- Household creation from scratch
- Nested household hierarchies

**Deferred to Later Phases**:
- Phase 2-Step 9: Export generation (will use accepted household decisions)
- Phase 2-Step 10+: CRM writeback (will use export data)
- Future: Durable household master records (if needed for cross-import linking)

---

## Files to Inspect (Completed)

✅ `scripts/householder/households_service.py` — Simple orchestration, no changes needed
✅ `scripts/householder/database_repository.py` (get_households) — Read-only, will add status derivation
✅ `scripts/householder/service_contracts.py` (HouseholdRow) — Add `effective_status` field
✅ `scripts/uploader/app.py` — Will add POST route
✅ `scripts/uploader/templates/imports/households.html` — Will wire buttons to form
✅ `tests/unit/test_households_service.py` — Existing tests, no changes
✅ `tests/integration/test_households_route.py` — Existing tests, no changes

---

## Files to Create (Phase 2-Step 9 Implementation)

```
scripts/householder/household_decision_service.py
scripts/householder/write_repository_contracts.py (add HouseholdDecisionResult, HouseholdDecisionWriter)
scripts/householder/database_write_repository.py (add DatabaseHouseholdDecisionWriter)
tests/unit/test_household_decision_service.py
tests/integration/test_household_decision_route.py
tests/integration/test_household_decision_ui.py
docs/implementation/phase2/PHASE2_STEP9_HOUSEHOLD_DECISION_WORKFLOW_COMPLETION_RECORD.md
```

---

## Files to Modify (Phase 2-Step 9 Implementation)

```
scripts/householder/write_repository_contracts.py
scripts/householder/database_write_repository.py
scripts/householder/service_contracts.py (add effective_status to HouseholdRow)
scripts/householder/database_repository.py (derive effective_status in get_households)
scripts/uploader/app.py (add POST route)
scripts/uploader/templates/imports/households.html (wire forms, add status badge)
```

---

## Recommended Phase 2-Step 9 Implementation Prompt

```
Phase 2-Step 9: Implement Household Decision Workflow

You are working in the DonorTrust / Householder v1 Flask/Jinja codebase.

Current accepted state:
* Phase 1B complete and accepted
* Phase 1B2 complete and accepted
* Phase 1C complete and accepted
* Phase 2 validation decision workflow complete and accepted
* Phase 2 normalization decision workflow complete and accepted
* Phase 2 duplicate decision workflow complete and accepted
* Phase 2-Step 8 household decision workflow planning accepted

Goal:

Implement the household decision workflow as planned in Phase 2-Step 8, following the exact pattern of validation/normalization/duplicate decisions.

Core rule:

A household decision records reviewer intent only. It must not mutate contacts, must not assign household_id, must not create durable household records, and must not write back to external systems.

Supported decisions:
- confirm_household
- reject_household
- defer

[Include all detailed requirements from Phase 2-Step 8 planning document]
```

---

## Summary

Phase 2-Step 8 planning is complete. The household decision workflow will:

1. ✅ Follow established validation/normalization/duplicate decision patterns
2. ✅ Preserve all immutability guardrails (no contact/row/item mutation)
3. ✅ Record reviewer intent only (no durable household assignment)
4. ✅ Create ReviewDecision + AuditLogRecord atomically
5. ✅ Derive effective status from latest decision
6. ✅ Provide clear status badges and decision forms in UI
7. ✅ Enable future export generation (uses decisions, not mutations)
8. ✅ Maintain full auditability

**No implementation yet** — This is planning/spec only. Ready for Phase 2-Step 9 implementation following this design.

---

**Verified**: 2026-06-12  
**Test Command**: `pytest tests/unit tests/integration -q`  
**Test Result**: 1011 passed, 0 failed (unchanged by planning)  
**Status**: 🔍 PLANNING — Ready for Phase 2-Step 9 implementation
