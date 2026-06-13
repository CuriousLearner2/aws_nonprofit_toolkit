# Phase 2-Step 1: Reviewer Decision Workflow Planning — Validation Decisions First

**Date**: 2026-06-12  
**Phase**: 2-Step 1 (Planning)  
**Status**: PLANNING (No implementation)  
**Objective**: Define validation decision workflow while preserving audit-safe, human-in-the-loop model

---

## Executive Summary

Phase 2-Step 1 plans the first write workflow: validation decisions. The design prioritizes:

- **Explicit reviewer actions**: Decisions are intentional, not automatic
- **Immutability of raw data**: RawImportRow and ImportContact remain append-only
- **Auditability**: Every decision appends ReviewDecision and AuditLogRecord
- **Statelessness in review items**: Status derived from latest decision, not mutated
- **Conservative boundaries**: Only validation decisions (not merges, household grouping, exports)

This plan defines the minimal safe implementation to move from read-only Flask routes (Phase 1C) to controlled write operations (Phase 2).

---

## 1. Current Validation Infrastructure Summary

### Current Validation Route

**Route Handler**: `GET /imports/<import_id>/validation` (scripts/uploader/app.py:896)

```python
@app.route('/imports/<import_id>/validation')
def import_validation(import_id):
    """Validation review for records with issues."""
    data = validation_service.get_validation_review(import_id)
    return render_template('imports/validation.html', **data)
```

**Service Layer**: `validation_service.get_validation_review(import_id)` (scripts/householder/validation_service.py:15)

- Calls repository (FixtureImportRepository or DatabaseImportRepository)
- Returns ValidationPageViewModel (frozen dataclass)
- No state mutations

**Template**: `scripts/uploader/templates/imports/validation.html`

- Displays batch ID, total records, validation issues count
- Table with 10 columns: checkbox, Transaction ID, Date, Name, Email, Phone, Amount, Address, Validation Status, Action
- "Inspect" action on each row (placeholder, no handler)
- Sticky action bar with bulk selection UI (Review Selected button)
- Modal for record details (populated by JavaScript)
- No form submission or decision recording currently

### Current View Model Shape

**ValidationPageViewModel** (service_contracts.py:123):
```python
@dataclass(frozen=True)
class ValidationPageViewModel:
    batch_id: str
    filename: str
    progress: int                  # Percentage of items with decisions
    validation_rows: tuple         # Tuple of ValidationRow
    validation_issues_count: int   # Count of pending validation items
    total_records: int

    def to_template_dict(self) -> dict:
        """Returns: {"batch": {...}, "validation_issues": [...], "queue_status": {...}, "total_records": ...}"""
```

**ValidationRow** (service_contracts.py:90):
```python
@dataclass(frozen=True)
class ValidationRow:
    id: str
    date: str
    name: str
    email: str
    phone: str
    amount: str
    address: str
    issue_type: Optional[str] = None
    issue_description: Optional[str] = None
```

### Current Database Read Behavior

**ReviewItem** (database_models.py:84):
- Stored with `item_type='validation'` for validation issues
- `status` column exists (currently 'pending', derived from latest decision in Phase 2)
- `payload_json` stores issue details: `{issue_type, issue_description}`
- Linked to one or more ReviewItemSubject records

**ReviewItemSubject** (database_models.py:117):
- `subject_type='import_contact_snapshot'` references ImportContact.id
- Polymorphic, can reference other entity types in future

**ReviewDecision** (database_models.py:147):
- `decision` column: currently unused (Phase 2 will populate)
- `reviewed_values` column: JSON, can store reviewer-provided values
- `reviewer` column: NULL (Phase 2 will populate)
- `batch_id`, `review_item_id` foreign keys
- Append-only table

**AuditLogRecord** (database_models.py:169):
- `action_type`: Phase 1 uses 'batch_imported', Phase 2 will use 'decision_recorded'
- `actor`: NULL (Phase 2 will populate)
- `item_id`: FK to ReviewItem
- `decision_id`: FK to ReviewDecision
- `details`: JSON for structured logging
- Append-only table

### Current Visible Actions

**Template**: "Inspect" link on each row (data-action="inspect-record")
- Currently triggers toast and opens empty modal
- No backend handler

**Bulk Selection**: Sticky action bar
- Checkboxes to select multiple records
- "Review Selected" button (disabled by default, placeholder)
- No backend handler

**No current decision submission**, validation decisions are Phase 2 work.

---

## 2. Proposed Validation Decision Workflow

### Overview

A reviewer inspects a validation issue, makes a decision, and records it. The decision closure depends on decision type.

### Decision Flow

```
Reviewer opens /imports/<import_id>/validation
  ├── Sees validation items (from database via repository)
  ├── Clicks "Inspect" on a record
  │   └── Modal shows full record details + decision form
  ├── Selects decision from dropdown
  ├── Optionally adds notes
  └── Clicks "Record Decision"
      ├── POST /imports/<import_id>/validation/<item_id>/decision
      │   ├── Service validates decision
      │   ├── Appends ReviewDecision record
      │   ├── Appends AuditLogRecord
      │   └── Returns JSON or redirects
      └── Page refreshes, item shows new status
         └── Status derived from latest decision
```

### Item Lifecycle (Per ReviewItem)

```
[pending] (created during ingestion)
   ↓
 [reviewed] (first decision recorded, any type)
   ↓
[dismissed] or [accepted] or [deferred]
   ↓
(Latest decision determines effective status)
```

---

## 3. Allowed Decisions and Semantics

### Decision Types (Validation Only)

For validation items (issue_type in {missing-required, format-invalid, length-exceeded}):

| Decision | Meaning | Closes Item? | Status After |
|----------|---------|--------------|--------------|
| `accept_issue` | Reviewer acknowledges issue exists, data is valid as-is (e.g., optional field) | Yes | `accepted` |
| `dismiss_issue` | Reviewer determines issue is false positive or inconsequential | Yes | `dismissed` |
| `defer` | Reviewer cannot decide now, needs more information or later review | No | `deferred` |
| `request_clarification` | (Optional future) Reviewer marks as needing donor follow-up | No | `awaiting_clarification` |

**For Phase 2-Step 1, focus on**: `accept_issue`, `dismiss_issue`, `defer`

(Clarification workflow deferred to Phase 2-Step 2+)

### Decision Semantics

- **accept_issue**: Data is usable as-is despite the issue. No mutation. Used when validation is overly strict or issue is cosmetic.
  - Example: missing city in address, but state and ZIP are valid; data is usable.

- **dismiss_issue**: Issue was false positive. Data is correct. No mutation needed.
  - Example: phone number flagged as invalid format, but reviewer confirms it's valid in context.

- **defer**: Decision not made now. Item remains open for later review.
  - Example: missing required field; awaiting resolution from prior stage.

### Multiple Decisions Per Item

**Allowed**: Yes. Latest decision is the current state.

**Rationale**: Reviewer may change mind, need to defer and return later, etc.

**Example**:
1. Reviewer records `defer` (awaiting clarification)
2. Later, reviewer records `dismiss_issue` (determined to be false positive)
3. Item status is now `dismissed` (derived from latest decision)

**Audit trail**: Both decisions visible in audit log, with timestamps.

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

### Status Derivation vs. Mutation

**Conservative Approach (Recommended)**:

Do **not** update `review_items.status` during Phase 2-Step 1.

Instead, derive effective status dynamically:

```python
def get_effective_status(review_item_id: int, session) -> str:
    """
    Derive current status from latest ReviewDecision.
    
    If no decision exists: return 'pending'
    If latest decision is 'defer': return 'deferred'
    If latest decision is 'dismiss_issue': return 'dismissed'
    If latest decision is 'accept_issue': return 'accepted'
    """
    latest_decision = session.query(ReviewDecision).\
        filter_by(review_item_id=review_item_id).\
        order_by(ReviewDecision.created_at.desc()).\
        first()
    
    if not latest_decision:
        return 'pending'
    
    decision_map = {
        'accept_issue': 'accepted',
        'dismiss_issue': 'dismissed',
        'defer': 'deferred',
    }
    
    return decision_map.get(latest_decision.decision, 'pending')
```

**Rationale**:
- Eliminates need to update review_items (keeps immutable)
- Latest decision is source of truth
- Audit trail is complete in review_decisions table
- No need for migration to backfill status

**Later consideration (Phase 2+)**: If performance requires denormalization, status can be cached in review_items.status as long as:
- It is updated atomically with ReviewDecision insert
- Audit trail includes both tables

For Phase 2-Step 1: Prefer derived status.

---

## 5. Proposed Route/API Shape

### Decision Recording Route

**Route**: `POST /imports/<import_id>/validation/<item_id>/decision`

**Request Format**: HTML form POST (Flask/Jinja standard)

```html
<form method="POST" action="/imports/{{ batch.id }}/validation/{{ item_id }}/decision">
  <input type="hidden" name="csrf_token" value="...">
  
  <label for="decision">Decision:</label>
  <select name="decision" required>
    <option value="">-- Select Decision --</option>
    <option value="accept_issue">Accept Issue (data is valid)</option>
    <option value="dismiss_issue">Dismiss Issue (false positive)</option>
    <option value="defer">Defer (need more information)</option>
  </select>
  
  <label for="notes">Notes (optional):</label>
  <textarea name="notes" placeholder="Any context for this decision..."></textarea>
  
  <button type="submit">Record Decision</button>
  <a href="/imports/{{ batch.id }}/validation">Cancel</a>
</form>
```

### Request Parameters

| Field | Type | Required | Example | Notes |
|-------|------|----------|---------|-------|
| `decision` | string | Yes | `accept_issue` | One of: accept_issue, dismiss_issue, defer |
| `notes` | string | No | "Donor confirmed address is valid" | Optional context |
| (implicit) `reviewer` | string | No | (from session/header) | Extracted from request context; TBD in Phase 2 (no auth yet) |

### Response Behavior

**Option A (POST + Redirect, recommended for HTML forms)**:
- POST /imports/<import_id>/validation/<item_id>/decision
- On success: HTTP 303 redirect to /imports/<import_id>/validation
  - Flash message: "Decision recorded: <decision> for <item_id>"
  - Page refreshes, item shows updated status
- On error: HTTP 400/500 with error message (redirect or form re-render)

**Option B (JSON, if future API)**:
- POST /imports/<import_id>/validation/<item_id>/decision (Accept: application/json)
- On success: HTTP 201 with JSON
  ```json
  {
    "decision_id": 42,
    "review_item_id": 15,
    "decision": "dismiss_issue",
    "effective_status": "dismissed",
    "audit_log_id": 200,
    "timestamp": "2026-06-12T14:30:00Z"
  }
  ```
- On error: HTTP 400/500 with error detail

**For Phase 2-Step 1**: Use Option A (POST + Redirect). It matches existing Flask/Jinja patterns.

---

## 6. Proposed Service/Write Repository Layer

### Service Function

**File**: `scripts/householder/validation_decision_service.py` (NEW)

```python
from typing import Optional, Mapping, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ValidationDecisionResult:
    """Result of recording a validation decision."""
    decision_id: int
    review_item_id: int
    decision: str
    effective_status: str  # 'pending', 'accepted', 'dismissed', 'deferred'
    audit_log_id: int
    timestamp: datetime

def record_validation_decision(
    import_id: str,
    review_item_id: int,
    decision: str,
    notes: Optional[str] = None,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> ValidationDecisionResult:
    """
    Record a validation decision for a review item.

    Appends ReviewDecision and AuditLogRecord. Does not mutate ReviewItem.
    Effective status is derived from latest decision.

    Args:
        import_id: Import batch ID
        review_item_id: ReviewItem.id to decide on
        decision: One of 'accept_issue', 'dismiss_issue', 'defer'
        notes: Optional context or explanation
        reviewer: Reviewer identifier (name or email); extracted from request context if None
        config: Optional configuration for database selection

    Returns:
        ValidationDecisionResult with decision_id, effective_status, etc.

    Raises:
        ValueError: If import_id not found, item not found, item belongs to different batch, item is not 'validation' type, or decision is invalid
        DatabaseError: If write transaction fails
    """
    # Implementation in Phase 2-Step 2
    pass
```

### Write Repository Protocol

**File**: `scripts/householder/write_repository_contracts.py` (NEW)

Define separate write protocol to keep read/write concerns separate:

```python
from typing import Protocol, Optional

class ValidationDecisionWriter(Protocol):
    """Protocol for writing validation decisions."""
    
    def create_validation_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> "ValidationDecisionResult":
        """Create a validation decision record and audit log entry."""
        ...
```

### Write Repository Implementation

**File**: `scripts/householder/database_write_repository.py` (NEW)

```python
class DatabaseValidationDecisionWriter:
    """Implement ValidationDecisionWriter for database backend."""
    
    def __init__(self, database_url: str = 'sqlite:///./givebutter.db'):
        self.database_url = database_url
    
    def create_validation_decision(
        self,
        batch_id: str,
        review_item_id: int,
        decision: str,
        notes: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> ValidationDecisionResult:
        """
        1. Validate inputs (import_id, item_id, decision value, etc.)
        2. Query ReviewItem to confirm exists, type='validation', belongs to batch
        3. Begin transaction
        4. Insert ReviewDecision record
        5. Insert AuditLogRecord with reference to decision
        6. Commit transaction
        7. Derive effective status from latest decision
        8. Return ValidationDecisionResult
        
        On error: Rollback, raise exception
        """
        # Implementation in Phase 2-Step 2
        pass
```

### Route Handler Integration

**File**: `scripts/uploader/app.py` (MODIFIED in Phase 2-Step 2)

```python
@app.route('/imports/<import_id>/validation/<int:review_item_id>/decision', methods=['POST'])
def record_validation_decision(import_id, review_item_id):
    """Record a reviewer's validation decision."""
    decision = request.form.get('decision')
    notes = request.form.get('notes')
    reviewer = request.headers.get('X-Reviewer-ID')  # TBD: how to get reviewer identity
    
    try:
        result = validation_decision_service.record_validation_decision(
            import_id=import_id,
            review_item_id=review_item_id,
            decision=decision,
            notes=notes,
            reviewer=reviewer,
        )
        flash(f"Decision recorded: {decision}", "success")
        return redirect(f'/imports/{import_id}/validation')
    except ValueError as e:
        flash(str(e), "error")
        return redirect(f'/imports/{import_id}/validation'), 400
    except Exception as e:
        flash("Error recording decision", "error")
        return redirect(f'/imports/{import_id}/validation'), 500
```

---

## 7. Audit Behavior

### AuditLogRecord Entries

For every validation decision, create one AuditLogRecord:

```python
audit_record = AuditLogRecord(
    batch_id=import_id,
    action_type='decision_recorded',
    action_timestamp=datetime.utcnow(),
    actor=reviewer,  # e.g., "john.smith@example.com" or None if not authenticated
    item_id=review_item_id,
    decision_id=decision.id,
    details={
        'decision_type': 'validation_decision',
        'decision_value': decision.decision,
        'notes': notes,
        'effective_status': get_effective_status(review_item_id),
        'prior_status': prior_status,  # Status before this decision
    }
)
```

### Audit Query Support

Audit service already reads and displays audit logs (Phase 1B):

**GET** `/imports/<import_id>/audit` → displays AuditPageViewModel

Expected to show:

- Timestamp
- Actor (reviewer)
- Action: "Decision recorded"
- Details: decision value, item ID, notes
- Full history of all decisions for audit trail

### Audit Log Template

The audit template should display all audit entries chronologically, including decision records:

```html
<table>
  <tr>
    <th>Timestamp</th>
    <th>Actor</th>
    <th>Action</th>
    <th>Item ID</th>
    <th>Decision</th>
    <th>Notes</th>
  </tr>
  {% for entry in audit_log %}
  <tr>
    <td>{{ entry.timestamp }}</td>
    <td>{{ entry.actor or 'System' }}</td>
    <td>{{ entry.action_type }}</td>
    <td>{{ entry.item_id }}</td>
    <td>{{ entry.details.decision_value }}</td>
    <td>{{ entry.details.notes }}</td>
  </tr>
  {% endfor %}
</table>
```

---

## 8. Error Handling

### Validation Errors (HTTP 400)

```text
unknown_import_id         → "Import batch not found"
unknown_review_item       → "Review item not found"
wrong_import_batch        → "Review item does not belong to this import"
wrong_item_type           → "This item is not a validation item (type: {type})"
invalid_decision_value    → "Invalid decision. Must be one of: accept_issue, dismiss_issue, defer"
missing_decision          → "Decision is required"
```

### Database Errors (HTTP 500)

```text
database_unavailable      → "Database connection failed"
transaction_failed        → "Failed to record decision (transaction error)"
constraint_violation      → "Database constraint violation"
```

### Unexpected Errors (HTTP 500)

```text
generic_error             → "Unexpected error recording decision"
```

### Error Response

**HTML Form POST** (redirect + flash):
```python
flash("Error message", "error")
return redirect(f'/imports/{import_id}/validation'), 400_or_500
```

**JSON API** (Option B, future):
```json
{
  "error": "Invalid decision value",
  "error_code": "invalid_decision_value",
  "status": "validation_error"
}
```

### Duplicate Submission Handling

If reviewer submits twice (click button twice):
- Second submission creates another decision record
- This is allowed; latest decision is current state
- Database constraints prevent impossible scenarios (e.g., wrong review_item_id)
- Audit trail shows both submissions with different timestamps

Prefer idempotency via client-side button disable (disable submit button after first click).

---

## 9. Test Strategy

### Unit Tests

**File**: `tests/unit/test_validation_decision_service.py` (NEW)

```python
class TestValidationDecisionService:
    """Test validation decision service logic."""
    
    def test_valid_decision_creates_result(self):
        """Valid decision returns ValidationDecisionResult with all fields."""
        result = record_validation_decision(
            import_id='IMP-2025-0101-A',
            review_item_id=1,
            decision='dismiss_issue',
            notes='False positive',
            reviewer='john@example.com',
        )
        assert result.decision_id > 0
        assert result.review_item_id == 1
        assert result.decision == 'dismiss_issue'
        assert result.effective_status == 'dismissed'
        assert result.audit_log_id > 0
    
    def test_invalid_decision_raises_error(self):
        """Invalid decision value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid decision"):
            record_validation_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=1,
                decision='invalid_value',
            )
    
    def test_unknown_import_raises_error(self):
        """Unknown import ID raises ValueError."""
        with pytest.raises(ValueError, match="Import batch not found"):
            record_validation_decision(
                import_id='IMP-NONEXISTENT',
                review_item_id=1,
                decision='dismiss_issue',
            )
    
    def test_unknown_review_item_raises_error(self):
        """Unknown review item ID raises ValueError."""
        with pytest.raises(ValueError, match="Review item not found"):
            record_validation_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=999999,
                decision='dismiss_issue',
            )
    
    def test_wrong_item_type_raises_error(self):
        """Non-validation item raises ValueError."""
        # Create duplicate item, try to decide on it as validation
        with pytest.raises(ValueError, match="not a validation item"):
            record_validation_decision(
                import_id='IMP-2025-0101-A',
                review_item_id=duplicate_item_id,  # item_type='duplicate'
                decision='dismiss_issue',
            )
    
    def test_multiple_decisions_allowed(self):
        """Multiple decisions per item allowed; latest is current state."""
        result1 = record_validation_decision(..., decision='defer')
        assert result1.effective_status == 'deferred'
        
        result2 = record_validation_decision(..., decision='dismiss_issue')
        assert result2.effective_status == 'dismissed'
        
        # Query latest: should be dismissed
        current_status = get_effective_status(item_id)
        assert current_status == 'dismissed'
```

### Integration Tests

**File**: `tests/integration/test_validation_decision_route.py` (NEW)

```python
class TestValidationDecisionRoute:
    """Test validation decision recording via Flask route."""
    
    @pytest.fixture
    def flask_client_with_database(self):
        """Flask client with database backend."""
        # Temporary SQLite database, initialized with test batch
        ...
        yield client
    
    def test_valid_decision_creates_records(self, flask_client_with_database):
        """POST decision creates ReviewDecision and AuditLogRecord."""
        response = flask_client_with_database.post(
            '/imports/IMP-2025-0101-A/validation/1/decision',
            data={
                'decision': 'dismiss_issue',
                'notes': 'False positive in validation',
            }
        )
        assert response.status_code == 303  # Redirect
        assert response.location.endswith('/imports/IMP-2025-0101-A/validation')
        
        # Verify database records created
        session = get_db_session()
        decision = session.query(ReviewDecision).filter_by(review_item_id=1).first()
        assert decision is not None
        assert decision.decision == 'dismiss_issue'
        
        audit = session.query(AuditLogRecord).filter_by(item_id=1).first()
        assert audit is not None
        assert audit.action_type == 'decision_recorded'
        assert audit.decision_id == decision.id
    
    def test_raw_rows_unchanged_after_decision(self, flask_client_with_database):
        """Decision does not mutate RawImportRow."""
        original_rows = session.query(RawImportRow).count()
        
        flask_client_with_database.post(
            '/imports/IMP-2025-0101-A/validation/1/decision',
            data={'decision': 'dismiss_issue'},
        )
        
        new_rows = session.query(RawImportRow).count()
        assert new_rows == original_rows
    
    def test_import_contacts_unchanged_after_decision(self, flask_client_with_database):
        """Decision does not mutate ImportContact."""
        original_contacts = session.query(ImportContact).count()
        
        flask_client_with_database.post(
            '/imports/IMP-2025-0101-A/validation/1/decision',
            data={'decision': 'dismiss_issue'},
        )
        
        new_contacts = session.query(ImportContact).count()
        assert new_contacts == original_contacts
    
    def test_invalid_decision_rejected(self, flask_client_with_database):
        """Invalid decision value returns HTTP 400."""
        response = flask_client_with_database.post(
            '/imports/IMP-2025-0101-A/validation/1/decision',
            data={'decision': 'invalid_value'},
        )
        assert response.status_code == 400
        assert 'Invalid decision' in response.data.decode()
    
    def test_wrong_item_type_rejected(self, flask_client_with_database):
        """Non-validation item rejected."""
        # Use a duplicate item ID instead of validation
        response = flask_client_with_database.post(
            f'/imports/IMP-2025-0101-A/validation/{duplicate_item_id}/decision',
            data={'decision': 'dismiss_issue'},
        )
        assert response.status_code == 400
        assert 'not a validation item' in response.data.decode()
    
    def test_item_from_wrong_import_rejected(self, flask_client_with_database):
        """Item from different batch rejected."""
        response = flask_client_with_database.post(
            '/imports/IMP-2025-0101-A/validation/999/decision',
            data={'decision': 'dismiss_issue'},
        )
        assert response.status_code == 400
        assert 'not found' in response.data.decode()
    
    def test_validation_page_reflects_decision(self, flask_client_with_database):
        """After decision, validation page shows updated status."""
        flask_client_with_database.post(
            '/imports/IMP-2025-0101-A/validation/1/decision',
            data={'decision': 'dismiss_issue'},
        )
        
        response = flask_client_with_database.get(
            '/imports/IMP-2025-0101-A/validation'
        )
        assert response.status_code == 200
        # Item should show 'dismissed' or have visual indicator
        # (Template update needed to display derived status)
    
    def test_audit_page_shows_decision(self, flask_client_with_database):
        """Audit page shows decision record after submission."""
        flask_client_with_database.post(
            '/imports/IMP-2025-0101-A/validation/1/decision',
            data={
                'decision': 'dismiss_issue',
                'notes': 'Test decision',
            }
        )
        
        response = flask_client_with_database.get(
            '/imports/IMP-2025-0101-A/audit'
        )
        assert response.status_code == 200
        assert b'Decision recorded' in response.data or b'dismiss_issue' in response.data
```

### Test Coverage Goals

- ✅ Valid decision creates ReviewDecision + AuditLogRecord
- ✅ Raw rows remain immutable
- ✅ Import contacts remain immutable
- ✅ Invalid decision rejected (HTTP 400)
- ✅ Wrong item type rejected
- ✅ Item from wrong batch rejected
- ✅ Route POST redirects on success
- ✅ Validation page reflects updated status
- ✅ Audit page shows decision record
- ✅ Multiple decisions per item allowed
- ✅ Effective status derived from latest decision
- ✅ Database mode workflow uses temporary SQLite
- ✅ No export files created
- ✅ No external API calls made
- ✅ No ReviewItem mutations

---

## 10. Explicit Non-Goals

### Not Included in Phase 2-Step 1

#### Reviewer Identity / Authentication
- **NOT**: Implement user authentication system
- **NOT**: Add login/logout
- **NOT**: Create user model or session tracking
- **Approach**: Accept reviewer from request header or placeholder for now
  - Phase 2 can add simple auth (e.g., single token, or integration with external IdP)
  - Audit log stores reviewer value as-is; no validation required yet

#### Duplicate Decisions
- **NOT**: Implement duplicate item decision workflow
- **SCOPE**: Validation decisions only (Phase 2-Step 1)
- **Defer**: Duplicate decisions to Phase 2-Step 3+

#### Contact Merges
- **NOT**: Implement merge logic
- **NOT**: Create merged contact record
- **Reason**: Risk of data loss; requires separate decision type and careful audit trail
- **Defer**: Phase 2-Step 3+

#### Household Grouping Decisions
- **NOT**: Implement household confirmation workflow
- **Defer**: Phase 2-Step 4+

#### Normalization Application
- **NOT**: Auto-apply normalization suggestions
- **NOT**: Implement normalization decision workflow
- **Defer**: Phase 2-Step 2+

#### Export Generation
- **NOT**: Generate export files
- **NOT**: Add export decision handling
- **SCOPE**: Exports are Phase 2-Step 5+

#### CRM/Givebutter Writeback
- **NOT**: Call Givebutter API
- **NOT**: Sync decisions to external system
- **Defer**: Phase 2-Step 6+ (if at all)

#### Bulk Actions
- **NOT**: Record decisions for multiple items at once
- **START**: Single-item decisions
- **Rationale**: Safer, clearer audit trail, easier to test
- **Defer**: Bulk actions to Phase 2-Step 2+

#### Undo/Redo
- **NOT**: Implement undo mechanism
- **APPROACH**: Decisions are append-only; new decision changes status
- **Rationale**: Simpler audit trail, no need for mutation tracking
- **May add**: UI to quickly record corrective decision, but not undo per se

#### Auto-Approval / Auto-Deciding
- **NOT**: Auto-decide related items
- **NOT**: Cascade decisions to other items
- **Approach**: Each decision is explicit, manual, per item
- **Reason**: Human-in-the-loop requirement; risky to auto-decide

#### Role-Based Actions
- **NOT**: Restrict decisions by reviewer role
- **Approach**: All reviewer identities can record all decision types
- **Defer**: Role-based access control to Phase 2+

---

## 11. Recommended Implementation Prompt for Phase 2-Step 2

Once this plan is accepted, Phase 2-Step 2 will implement the workflow:

**Phase 2-Step 2 Prompt**:

> Phase 2-Step 2: Implement Validation Decision Workflow
>
> Implement the validation decision workflow as planned in Phase 2-Step 1 planning document.
>
> Tasks:
> 1. Create `scripts/householder/validation_decision_service.py` with `record_validation_decision()` function
> 2. Create `scripts/householder/write_repository_contracts.py` with `ValidationDecisionWriter` protocol
> 3. Create `scripts/householder/database_write_repository.py` with `DatabaseValidationDecisionWriter` implementation
> 4. Modify `scripts/uploader/app.py` to add POST /imports/<import_id>/validation/<item_id>/decision route
> 5. Update validation.html template to add decision form in modal
> 6. Create `tests/unit/test_validation_decision_service.py` with unit tests
> 7. Create `tests/integration/test_validation_decision_route.py` with integration tests
> 8. Verify 911 + N tests passing (N = new tests)
> 9. Create Phase 2-Step 2 completion record
>
> Reference: docs/implementation/phase2/PHASE2_STEP1_VALIDATION_DECISION_WORKFLOW_PLANNING.md

---

## Files Inspected

1. `scripts/householder/validation_service.py` - Read-only service layer
2. `scripts/uploader/app.py` - Flask routes (validation route)
3. `scripts/uploader/templates/imports/validation.html` - Validation template (UI)
4. `scripts/householder/database_models.py` - ReviewItem, ReviewDecision, AuditLogRecord models
5. `scripts/householder/database_repository.py` - get_validation() read method
6. `scripts/householder/service_contracts.py` - ValidationPageViewModel, ValidationRow
7. `scripts/householder/audit_service.py` - Audit log read service
8. `tests/integration/test_validation_route.py` - Current validation route tests

---

## Summary

**Phase 2-Step 1 Planning is complete.**

### Key Decisions

1. **Validation decisions only** (not duplicates, households, exports)
2. **Three decision types**: accept_issue, dismiss_issue, defer
3. **Append-only writes** to review_decisions and audit_log
4. **Derived status** from latest decision (no review_items.status mutation)
5. **POST + Redirect** route pattern (matches Flask/Jinja style)
6. **Separate write service/repository** (keep read/write concerns separate)
7. **Explicit reviewer actions** (no auto-approval, no cascading)
8. **Full audit trail** (every decision logged with timestamp, actor, notes)
9. **Immutable raw data** (raw_import_rows, import_contacts never updated)
10. **Comprehensive tests** (unit + integration, database mode)

### Open Questions

1. **Reviewer identity**: How to identify reviewer without auth system? Options:
   - Request header (`X-Reviewer-ID`)
   - Session variable (if simple auth added)
   - Placeholder (all decisions attributed to "anonymous")
   - Environment variable (for CI/automation)

2. **Batch/bulk decisions**: Will Phase 2-Step 2 include bulk action UI, or defer to Phase 2-Step 3?

3. **Notes field**: Required or optional? (Plan says optional; confirm before implementation)

4. **Clarification decision**: Include in Phase 2-Step 2, or defer to Phase 2-Step 2.5?

### Blockers

None identified. All required database tables exist (ReviewItem, ReviewDecision, AuditLogRecord). All read-side infrastructure in place (repository, service, template).

Ready for Phase 2-Step 2 implementation.

---

**Planning Verification**:

- ✅ Current validation infrastructure documented
- ✅ Proposed workflow defined
- ✅ Allowed decisions specified
- ✅ Write boundary clarified
- ✅ Route/API shape proposed
- ✅ Service layer designed
- ✅ Audit behavior specified
- ✅ Error handling planned
- ✅ Test strategy documented
- ✅ Non-goals enumerated
- ✅ Open questions identified
- ✅ Implementation prompt ready

**Status**: ✅ PLANNING COMPLETE  
**Next Step**: Phase 2-Step 2 implementation (when approved)
