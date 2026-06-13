# Phase 2-Step 11: Export Generation Planning — Derived Export Only

**Date**: 2026-06-12  
**Phase**: 2-Step 11 (Planning)  
**Status**: 🔍 PLANNING (No implementation yet)

---

## Executive Summary

Phase 2-Step 11 plans export generation based on accepted reviewer decisions. The export is derived only—it constructs downloadable CSV output by combining immutable import contact snapshots with append-only reviewer decisions. No source data is mutated. No files are generated until explicit reviewer action.

**Core Principle**: Export generation interprets reviewer decisions to produce derived output without mutating raw rows, contact snapshots, review items, or decisions.

**Scope**: This document plans the export derivation and preview workflow. No code implementation yet.

---

## Part 1: Current Export Console Summary

### Route and Service Behavior

**Route**: `GET /imports/<import_id>/exports`

**Handler** (`scripts/uploader/app.py`):
```python
@app.route('/imports/<import_id>/exports')
def import_exports(import_id):
    """Export console for generating and downloading exports."""
    data = exports_service.get_export_console(import_id)
    return render_template('imports/exports.html', **data)
```

**Service** (`exports_service.py`):
- `get_export_console(import_id, config)` → `Dict[str, Any]`
- Calls `repository.get_exports(import_id)`
- Returns template-ready dictionary with batch metadata and export cards

### View Model

**ExportConsoleViewModel** (`service_contracts.py`):
```python
@dataclass(frozen=True)
class ExportConsoleViewModel:
    batch_id: str
    filename: str
    progress: int
    export_cards: tuple  # Tuple of ExportCard
    staged_record_count: int
    total_decisions: int
    household_count: int
    recent_exports: tuple
```

### Template Behavior

**File**: `scripts/uploader/templates/imports/exports.html`

**Current UI**:
- Displays staged record count
- Shows reviewer decision count
- Shows household count
- Displays 4 static export format cards (Reviewed, Household, Backlog, Raw)
- Shows "Generate Export Package" button (no functional implementation yet)
- Displays recent exports table (placeholder for future file history)

**Safety Messages**:
- "Raw import rows are never changed by exports"
- "Exports prepare files for download only"
- "No data is written back to Givebutter or any CRM"
- "All export actions are logged"

### Database Query Behavior

**Method** (`database_repository.py`, `get_exports()`):
1. Counts total `ReviewItem` records (all types)
2. Counts `ReviewDecision` records (overall progress)
3. Counts `ImportContact` records (staged records)
4. Counts `ReviewItem` with `item_type='duplicate'` and sums supporting_evidence
5. Counts `ReviewItem` with `item_type='household'`
6. Builds export cards from static card definitions (no dynamic calculation)

### Current State Assessment

**What exists**:
- ✅ Export console route (read-only, GET)
- ✅ Static export card definitions
- ✅ View model with metadata
- ✅ Template with UI scaffolding
- ✅ Test coverage (31 tests)

**What does NOT exist**:
- ❌ Export derivation service (no decision interpretation)
- ❌ Export row generation (no CSV building)
- ❌ Export file generation
- ❌ Export download/streaming
- ❌ Export history persistence
- ❌ Blocker/warning detection
- ❌ POST route for export generation
- ❌ Audit logging for export actions

---

## Part 2: Proposed Export Scope

### Phase 2-Step 12 Scope (Conservative, Derived-Only)

**Primary Goal**: Build and preview derived export rows in memory, without file generation.

**Scope**:
1. ✅ Create `build_export_preview()` service function
2. ✅ Interpret reviewer decisions to derive export rows
3. ✅ Detect blockers (unresolved validation failures)
4. ✅ Detect warnings (deferred/unresolved normalization/duplicate/household)
5. ✅ Return preview data (rows + metadata) for template display
6. ✅ Display readiness status in UI
7. ✅ NO file generation (Phase 2-Step 12 is preview-only)
8. ✅ NO Givebutter/CRM writeback
9. ✅ NO durable contact merges or household records

**Later Phase** (Phase 2-Step 13 or beyond):
- File generation and streaming (explicit button, audit log)
- Export history persistence
- Scheduled/background export jobs

### Why Preview-First?

1. **Safety**: Let reviewers see derived output before file is generated
2. **Auditability**: Understand how decisions affect output
3. **Validation**: Check for missing/blocked items before committing
4. **Transparency**: Full traceability of decision → output mapping

---

## Part 3: Decision Interpretation Rules

### Validation Decision Rules

**Validation item can block export or allow with warning.**

```
accept_issue:
  → Include row in export with original values
  → No blocker (reviewer accepted the issue)

dismiss_issue:
  → Include row in export with original values
  → No blocker (reviewer dismissed as false positive)

defer:
  → Include row in export with original values
  → Emit WARNING: "Validation issue unresolved, export may be incomplete"
  → Row is NOT blocked (conservative: assume accept)

no decision (pending):
  → Validation issue remains unresolved
  → If issue is CRITICAL (e.g., missing_email): BLOCKER
  → If issue is ADVISORY (e.g., formatting): WARNING
  → Row may be blocked or warned depending on severity
```

**Critical validation issues** (block unless accepted/dismissed):
- `missing_email` or `missing_phone` (no contact mechanism)
- `invalid_email_format` (unparseable)
- `invalid_amount_zero_or_negative` (can't process)
- `missing_transaction_id` (no transaction record)

**Advisory issues** (warning only, don't block):
- `address_incomplete` (partial address OK)
- `phone_format_unusual` (non-standard format OK)
- `name_special_characters` (can normalize)

---

### Normalization Decision Rules

**Normalization applies to specific field only.**

```
accept_normalization:
  → Use normalized_value in derived export output
  → Include decision metadata in row context
  → No warning

reject_normalization:
  → Use original snapshot value in derived export output
  → Include decision metadata in row context
  → No warning (reviewer consciously chose original)

defer:
  → Use original snapshot value (conservative)
  → Emit WARNING: "Field <name> normalization unresolved, using original value"
  → Row is NOT blocked

no decision (pending):
  → Use original snapshot value (conservative)
  → Emit WARNING: "Field <name> has suggested normalization, not yet reviewed"
  → Row is NOT blocked
```

**Example**:
```python
# Original: "john.smith@example.com"
# Normalized: "JOHN.SMITH@EXAMPLE.COM"

if normalization_decision == 'accept_normalization':
    export_value = "JOHN.SMITH@EXAMPLE.COM"
elif normalization_decision == 'reject_normalization':
    export_value = "john.smith@example.com"
else:  # deferred or no decision
    export_value = "john.smith@example.com"
    warnings.append("Email normalization pending")
```

---

### Duplicate Decision Rules

**Duplicate decision creates derived grouping only, no merge.**

```
same_person:
  → Both contacts included in export
  → Assign derived duplicate_group_id to both rows
  → Include decision in export metadata
  → No warning

different_people:
  → Both contacts included in export
  → Assign separate duplicate_group_id (or null)
  → Include decision in export metadata
  → No warning

defer:
  → Both contacts included in export
  → Assign tentative duplicate_group_id (nullable)
  → Emit WARNING: "Duplicate pair unresolved, grouping may change"
  → Row is NOT blocked

no decision (pending):
  → Both contacts included in export
  → Assign tentative/null grouping
  → Emit WARNING: "Duplicate pair unresolved"
  → Row is NOT blocked
```

**Derived duplicate_group_id**:
- If `same_person`: `duplicate_group_{hash(contact_ids)}`
- If `different_people`: null or unique ID for each
- If deferred/unresolved: null with warning

---

### Household Decision Rules

**Household decision creates derived grouping label only, no contact mutation.**

```
confirm_household:
  → Assign derived household_group_label from payload
  → Assign derived household_group_id from payload
  → Include all confirmed contacts with grouping
  → No warning

reject_household:
  → Do NOT group contacts
  → Each contact exports separately
  → household_group_label = null
  → No warning

defer:
  → Do NOT group contacts yet
  → Each contact exports separately
  → household_group_label = null
  → Emit WARNING: "Household grouping unresolved, exporting individually"
  → Row is NOT blocked

no decision (pending):
  → Do NOT group contacts
  → Each contact exports separately
  → household_group_label = null
  → Emit WARNING: "Household grouping pending"
  → Row is NOT blocked
```

**Derived household metadata**:
```json
{
  "household_group_id": "HH-001",
  "household_group_label": "Smith Family",
  "household_confirmed": true,
  "household_members": ["TXN-001", "TXN-003", "TXN-005"]
}
```

---

## Part 4: Unresolved Item Policy

### Policy: Permissive with Warnings

**Recommended approach**:
- ✅ Export proceeds (no hard blockers for deferred items)
- ✅ Critical validation failures DO block
- ✅ All unresolved items are marked with warnings
- ✅ Reviewer can see warnings before file generation

### Blocker Conditions (Prevent Export)

Export is blocked if:
1. ✅ Critical validation issue NOT accepted/dismissed
   - Examples: `missing_email`, `invalid_amount`, `missing_transaction_id`
2. ✅ More than N% of rows have validation blockers
   - Threshold: configurable (e.g., 10% unresolved = block)

### Warning Conditions (Allowed, Tracked)

Export includes warnings if:
1. ✅ Advisory validation issue is deferred/unresolved
2. ✅ Normalization field is deferred/unresolved
3. ✅ Duplicate pair is deferred/unresolved
4. ✅ Household grouping is deferred/unresolved

---

## Part 5: Proposed Export Output Shape

### CSV Column Definition

```
source_row_index          # Original row position in import
transaction_id            # From import_contact
first_name                # From import_contact snapshot (or normalized if accepted)
last_name                 # From import_contact snapshot (or normalized if accepted)
email                     # From import_contact snapshot (or normalized if accepted)
phone                     # From import_contact snapshot (or normalized if accepted)
address_line1             # From import_contact snapshot
address_line2             # From import_contact snapshot
city                      # From import_contact snapshot
state                     # From import_contact snapshot
postal_code               # From import_contact snapshot
amount                    # From import_contact snapshot
donation_date             # From import_contact snapshot (or normalized if accepted)

# Validation context
validation_status         # 'accepted', 'dismissed', 'pending', 'blocked'
validation_issues         # JSON list of unresolved issues (if any)

# Normalization context
normalized_fields         # JSON list of field names with accepted normalizations
normalization_warnings    # JSON list of pending normalization decisions

# Duplicate context
duplicate_group_id        # Derived ID if same_person decision, null otherwise
duplicate_decision        # 'same_person', 'different_people', 'pending', or null
duplicate_warnings        # JSON list of unresolved duplicate decisions

# Household context
household_group_id        # Derived ID if confirm_household decision, null otherwise
household_group_label     # "Smith Family" if confirm_household, null otherwise
household_members         # JSON list of contact IDs if grouped
household_decision        # 'confirmed', 'rejected', 'pending', or null
household_warnings        # JSON list of unresolved household decisions

# Export context
export_warnings           # JSON list of all warnings affecting this row
export_blocked            # true if critical validation issues prevent export
export_derived_at         # ISO timestamp of when this row was derived
```

### Example Row (with decisions)

```csv
source_row_index,transaction_id,first_name,last_name,email,phone,address_line1,...,validation_status,duplicate_group_id,household_group_id,export_warnings

1,TXN-001,JOHN,SMITH,john.smith@example.com,555-1234,123 Main St,...,accepted,DUP-GROUP-A,HH-001,[]

2,TXN-003,Robert,Smith,robert@example.com,555-1234,123 Main St,...,dismissed,DUP-GROUP-A,HH-001,"[""Normalization pending on email""]"

3,TXN-005,MARY,SMITH,mary@example.com,555-1234,123 Main St,...,pending,DUP-GROUP-A,HH-001,"[""Household grouping unresolved""]"
```

---

## Part 6: Proposed Export Derivation Service

### Service Function Signature

```python
def build_export_preview(
    import_id: str,
    config: Optional[Mapping[str, Any]] = None,
) -> ExportPreviewResult:
    """
    Build a preview of derived export rows based on reviewer decisions.

    Workflow:
    1. Query import_contacts for this batch
    2. Query all reviewer decisions (validation, normalization, duplicate, household)
    3. For each contact:
       a. Start with original contact snapshot values
       b. Apply accepted normalizations
       c. Detect blockers and warnings from decisions
       d. Derive duplicate grouping if same_person
       e. Derive household grouping if confirm_household
       f. Build export row
    4. Return preview with rows, blockers, warnings, summary

    Does NOT:
    - Mutate any source data
    - Generate files
    - Write to Givebutter/CRM
    - Create durable records

    Args:
        import_id: Import batch ID to derive export for
        config: Optional configuration for database selection

    Returns:
        ExportPreviewResult with:
        - export_rows: list of ExportRow namedtuples
        - blockers: list of blocker summaries
        - warnings: list of warning summaries
        - row_count: int
        - blocked_count: int
        - warning_count: int
        - is_export_ready: bool (True if no blockers)

    Raises:
        ValueError: If batch not found or invalid configuration
    """
```

### Return Type

```python
@dataclass(frozen=True)
class ExportRow:
    """Derived export row."""
    source_row_index: int
    transaction_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    address_line1: str
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    amount: str
    donation_date: str
    # Validation context
    validation_status: str  # 'accepted', 'dismissed', 'pending', 'blocked'
    validation_issues: list  # JSON serializable
    # Normalization context
    normalized_fields: list  # Field names with accepted normalizations
    normalization_warnings: list  # Pending decisions
    # Duplicate context
    duplicate_group_id: Optional[str]
    duplicate_decision: Optional[str]  # 'same_person', 'different_people', 'pending'
    duplicate_warnings: list
    # Household context
    household_group_id: Optional[str]
    household_group_label: Optional[str]
    household_members: list  # Contact IDs if grouped
    household_decision: Optional[str]  # 'confirmed', 'rejected', 'pending'
    household_warnings: list
    # Export context
    export_warnings: list  # All warnings for this row
    export_blocked: bool  # True if critical issue prevents export
    export_derived_at: datetime


@dataclass(frozen=True)
class ExportPreviewResult:
    """Result of export preview derivation."""
    import_id: str
    export_rows: tuple  # Tuple of ExportRow
    blockers: tuple  # Tuple of blocker summaries
    warnings: tuple  # Tuple of warning summaries
    row_count: int
    blocked_count: int
    warning_count: int
    is_export_ready: bool  # True if no blockers
    derived_at: datetime
```

### Pseudocode Workflow

```python
def build_export_preview(import_id, config):
    # 1. Query source data
    session = get_db_session(...)
    contacts = session.query(ImportContact).filter_by(batch_id=import_id).all()
    decisions = {
        'validation': query ValidationDecision by batch_id,
        'normalization': query NormalizationDecision by batch_id,
        'duplicate': query DuplicateDecision by batch_id,
        'household': query HouseholdDecision by batch_id,
    }
    
    # 2. Build rows
    rows = []
    blockers = []
    warnings = []
    
    for contact in contacts:
        # Start with snapshot values
        row = ExportRow(
            source_row_index=contact.raw_import_row.row_index,
            transaction_id=contact.transaction_id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone=contact.phone,
            # ... other fields
        )
        
        # Apply normalization decisions
        normalized_fields = []
        for norm_decision in decisions['normalization']:
            if norm_decision.decision == 'accept_normalization':
                field = norm_decision.field
                normalized_value = norm_decision.payload_json['normalized_value']
                row[field] = normalized_value
                normalized_fields.append(field)
        
        # Detect validation blockers/warnings
        validation_decision = decisions['validation'].get(contact.review_item_id)
        if not validation_decision:
            # Unresolved validation issue
            if is_critical(review_item.payload_json['issue_type']):
                blockers.append(f"Contact {contact.id}: Unresolved critical validation")
                row.export_blocked = True
            else:
                warnings.append(f"Contact {contact.id}: Advisory validation unresolved")
        
        # Derive duplicate grouping
        dup_decision = decisions['duplicate'].get(...)
        if dup_decision and dup_decision.decision == 'same_person':
            row.duplicate_group_id = derive_group_id(...)
        
        # Derive household grouping
        hh_decision = decisions['household'].get(...)
        if hh_decision and hh_decision.decision == 'confirm_household':
            row.household_group_id = hh_decision.payload_json['id']
            row.household_group_label = hh_decision.payload_json['suggested_name']
        
        rows.append(row)
    
    # 3. Return preview
    return ExportPreviewResult(
        import_id=import_id,
        export_rows=tuple(rows),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        row_count=len(rows),
        blocked_count=sum(1 for r in rows if r.export_blocked),
        warning_count=len(warnings),
        is_export_ready=len(blockers) == 0,
        derived_at=datetime.utcnow(),
    )
```

---

## Part 7: Whether Any Writes Occur

### Phase 2-Step 12 (Preview-Only): NO WRITES

```python
build_export_preview():
  - ✅ Reads only (queries import_contacts, review_decisions)
  - ✅ Returns in-memory objects
  - ❌ Does NOT write anything
  - ❌ Does NOT create export files
  - ❌ Does NOT call Givebutter/CRM
  - ❌ Does NOT create audit log entry (preview is read-only)
  - ❌ Does NOT mutate any source data
```

### Phase 2-Step 13+ (File Generation): EXPLICIT WRITE

**Future export file generation** (not Phase 2-Step 12):
```python
generate_export_file(import_id, export_format):
  - ✅ Calls build_export_preview() first
  - ✅ IF blockers exist: return error, do NOT generate
  - ✅ IF no blockers: generate CSV file
  - ✅ MUST create audit log entry:
    - action_type='export_generated'
    - actor=current_user (if auth implemented)
    - file_metadata={format, row_count, size}
    - warnings_summary=..., blockers_summary=...
  - ✅ File is saved or streamed for download
  - ✅ File is NOT written back to Givebutter
```

---

## Part 8: Audit Behavior

### Preview-Only (Phase 2-Step 12)

**No audit log entry** for viewing the preview.

Rationale: Preview is read-only, exploratory. Reviewer can view preview multiple times without logging.

### File Generation (Phase 2-Step 13+)

**Explicit audit log entry** when file is generated/downloaded.

```python
# When export file is generated:
audit_record = AuditLogRecord(
    batch_id=import_id,
    action_type='export_generated',
    action_timestamp=datetime.utcnow(),
    actor=current_user_id or None,
    details={
        'export_format': 'CSV',
        'row_count': len(export_rows),
        'blocked_count': blocked_count,
        'warning_count': warning_count,
        'blockers': blockers_summary,
        'warnings': warnings_summary,
        'decision_snapshot': {
            'validation_decisions': validation_count,
            'normalization_decisions': normalization_count,
            'duplicate_decisions': duplicate_count,
            'household_decisions': household_count,
        },
        'file_metadata': {
            'filename': f'{import_id}_export_{timestamp}.csv',
            'file_size': size_bytes,
            'generated_at': timestamp,
        },
    },
)
```

---

## Part 9: UI Behavior

### Export Console Enhancements (Phase 2-Step 12)

**Current** (read-only):
- ✅ Shows static export cards
- ✅ Shows staged record count
- ✅ Shows decision count
- ✅ Button: "Generate Export Package" (no handler)

**Enhanced** (after Phase 2-Step 12 preview implementation):
- ✅ Add "Export Preview" or "Build Preview" button
- ✅ On click, call `build_export_preview()` endpoint
- ✅ Show preview summary:
  - Total rows
  - Blocked rows (if any) — RED warning
  - Warning count — YELLOW warning
  - Blockers list (if any)
  - Warnings list
- ✅ Show preview table (sample first 20 rows)
- ✅ Status indicator: "Ready to Export" (if no blockers) or "Blocked" (if blockers exist)
- ✅ Optional: "Download Preview as CSV" (optional feature)

**Do NOT**:
- ❌ Auto-generate preview on page load
- ❌ Auto-generate files
- ❌ Show preview unless explicitly requested

### Example UI State

```
┌─ Export Console ─────────────────────────┐
│ Batch: IMP-2025-0101-A                   │
│                                          │
│ ⚠️  Blockers Found: 3 rows               │
│ ⚠️  Warnings: 12 rows                    │
│                                          │
│ Blocker Summary:                         │
│  - Contact TXN-001: Missing email        │
│  - Contact TXN-005: Critical validation  │
│  - Contact TXN-012: Invalid amount       │
│                                          │
│ Warning Summary:                         │
│  - 8 contacts: Normalization unresolved  │
│  - 3 contacts: Duplicate grouping unres. │
│  - 1 contact: Household grouping unres.  │
│                                          │
│ [📋 View Full Preview] [↓ Download CSV]  │
│                                          │
│ ❌ Export is blocked until blockers      │
│    are resolved.                         │
│                                          │
│ [← Back] [→ Next]                       │
└──────────────────────────────────────────┘
```

---

## Part 10: Test Strategy

### Unit Tests for Export Derivation

**Test suite**: `tests/unit/test_export_preview_service.py` (~25-30 tests)

**Test categories**:

1. **Base Case** (3 tests)
   - No decisions → export uses original values
   - Single contact with no decisions
   - Multiple contacts with mixed decisions

2. **Validation Decision Rules** (4 tests)
   - accept_issue: row included, no blocker
   - dismiss_issue: row included, no blocker
   - defer: row included with warning
   - No decision, critical issue: blocker

3. **Normalization Decision Rules** (5 tests)
   - accept_normalization: use normalized value
   - reject_normalization: use original value
   - defer: use original, emit warning
   - Multiple normalizations on same row
   - Normalization on non-existent field (ignored)

4. **Duplicate Decision Rules** (4 tests)
   - same_person: group_id assigned to both
   - different_people: separate group_ids
   - defer: warning, no grouping
   - Multiple duplicate pairs (isolation)

5. **Household Decision Rules** (3 tests)
   - confirm_household: group_label assigned
   - reject_household: no grouping
   - defer: warning, no grouping

6. **Immutability** (3 tests)
   - import_contacts unchanged
   - review_decisions unchanged
   - raw_import_rows unchanged

7. **Blocker/Warning Detection** (3 tests)
   - Blocker count correct
   - Warning count correct
   - is_export_ready flag correct

### Integration Tests for Export Route

**Test suite**: `tests/integration/test_export_preview_route.py` (~15-20 tests)

**Test categories**:

1. **Route Behavior** (3 tests)
   - GET /imports/<id>/exports renders (existing)
   - POST /imports/<id>/exports/preview builds and returns preview (new)
   - Invalid import_id returns 404

2. **Preview Completeness** (3 tests)
   - All contacts included in preview
   - All decisions applied
   - All blockers detected
   - All warnings detected

3. **CSV Column Presence** (2 tests)
   - All required columns present
   - JSON fields properly formatted

4. **Decision Application** (4 tests)
   - Validation decisions affect validation_status
   - Normalization decisions affect field values
   - Duplicate decisions affect duplicate_group_id
   - Household decisions affect household_group_label

5. **Immutability Verification** (2 tests)
   - No writes to import_contacts
   - No writes to review_decisions

6. **Edge Cases** (2 tests)
   - Empty batch (no contacts)
   - All rows blocked
   - Mixed decisions (some resolved, some pending)

---

## Part 11: Explicit Non-Goals

### Out of Scope (Phase 2-Step 12)

**Not implementing**:
- ❌ File generation or download
- ❌ Export history persistence
- ❌ Givebutter/CRM writeback
- ❌ Automatic export on page load
- ❌ Contact merge operations
- ❌ Durable merged contact records
- ❌ Durable household master records
- ❌ Cross-import matching
- ❌ Background/async processing
- ❌ Auth/login system
- ❌ Automatic duplicate resolution
- ❌ Automatic contact consolidation

### Deferred to Later Phases

**Phase 2-Step 13** (future):
- File generation and CSV download
- Export history storage and listing
- Scheduled/background export jobs

**Later phases** (post-Phase 2):
- Givebutter/CRM integration
- Durable household master records
- Cross-import duplicate consolidation
- Advanced export filters

---

## Part 12: Recommended Phase 2-Step 12 Implementation Prompt

```
Phase 2-Step 12: Implement Export Preview Derivation

You are working in the DonorTrust / Householder v1 Flask/Jinja codebase.

Current accepted state:
* Phase 1B complete and accepted
* Phase 1B2 complete and accepted
* Phase 1C complete and accepted
* Phase 2 validation decision workflow complete and accepted
* Phase 2 normalization decision workflow complete and accepted
* Phase 2 duplicate decision workflow complete and accepted
* Phase 2 household decision workflow complete and accepted
* Phase 2-Step 11 export generation planning accepted

Goal:

Implement export preview derivation based on accepted reviewer decisions.

Core rule:

Export preview derives output from immutable source data and append-only decisions.
No source data is mutated. No files are generated. Preview is read-only.

Supported export derivation:
1. Original snapshot values from import_contacts
2. Apply accepted normalizations (field value override)
3. Detect validation blockers (critical issues)
4. Detect warnings (unresolved decisions)
5. Derive duplicate grouping (same_person → group_id)
6. Derive household grouping (confirm_household → label)

Decision interpretation:
- Validation: accept/dismiss/defer/pending → status + warnings
- Normalization: accept/reject/defer/pending → value override
- Duplicate: same_person/different_people/defer/pending → grouping
- Household: confirm/reject/defer/pending → grouping + label

[Include detailed decision rules from Phase 2-Step 11 planning]

Deliverables:
1. build_export_preview(import_id, config) service function
2. ExportRow and ExportPreviewResult dataclasses
3. POST /imports/<id>/exports/preview route
4. Enhanced export console UI with preview display
5. ~25-30 unit tests for preview service
6. ~15-20 integration tests for preview route
7. Completion record with test results

Verification:
- 1041+ tests passing (no regressions)
- No mutations to source data
- All decisions correctly interpreted
- Blockers and warnings correctly detected
- Preview is read-only, no file generation

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

---

## Summary

**Phase 2-Step 11 planning complete.** The export preview derivation will:

1. ✅ Build derived export rows in memory from decisions
2. ✅ Interpret validation, normalization, duplicate, household decisions
3. ✅ Detect blockers (critical validation failures) and warnings (unresolved items)
4. ✅ Preserve all immutability guardrails
5. ✅ Return preview with full traceability
6. ✅ Enable future file generation via explicit action

**Key design decisions**:
1. ✅ Preview-only in Phase 2-Step 12 (no file generation)
2. ✅ Permissive policy (unresolved items warned, not blocked)
3. ✅ Derived IDs (duplicate_group_id, household_group_id) — no merges
4. ✅ Full traceability (every row shows which decisions affected it)
5. ✅ Read-only service (no audit log, no mutations)

**No implementation yet** — This is planning/spec only. Ready for Phase 2-Step 12 implementation.

---

**Verified**: 2026-06-12  
**Test Command**: `pytest tests/unit tests/integration -q`  
**Current Result**: 1041 passed (no changes, planning only)  
**Status**: 🔍 PLANNING — Ready for Phase 2-Step 12 implementation
