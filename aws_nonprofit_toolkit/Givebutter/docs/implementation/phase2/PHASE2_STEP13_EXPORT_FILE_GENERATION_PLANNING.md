# Phase 2-Step 13: Export File Generation Planning

**Phase:** 2-Step 13  
**Status:** Planning (no implementation yet)  
**Date:** 2026-06-12  
**Prerequisite:** Phase 2-Step 12 (Export Preview Derivation) ✅ ACCEPTED

## Executive Summary

Define how a reviewer explicitly generates a downloadable CSV export file from the derived export preview while maintaining complete source-data immutability and audit guarantees. This step introduces the first durable artifact (the export file) and explicit audit logging for export generation.

**Core Principle:** Export file generation may create a file artifact and write one audit log record, but it must NOT mutate any source data or call external systems.

---

## Part 1: Current Export Preview Summary

### Export Preview Service Interface

**Location:** `scripts/householder/export_preview_service.py`

```python
def build_export_preview(
    import_id: str,
    config: Optional[Mapping[str, Any]] = None,
) -> ExportPreviewResult:
    """
    Build preview of derived export rows based on reviewer decisions.
    
    Does NOT mutate any source data, generate files, write audit logs, or call external systems.
    """
```

**Input:**
- `import_id`: Batch ID to derive export for
- `config`: Optional database URL for flexible repository selection

**Output:** `ExportPreviewResult` (immutable dataclass)

### ExportRow Shape

**Location:** `scripts/householder/service_contracts.py:464`

```python
@dataclass(frozen=True)
class ExportRow:
    # Original contact snapshot fields
    source_row_index: Optional[int]
    transaction_id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    amount: Optional[str]
    
    # Decision-derived status and metadata
    validation_status: str  # 'pending', 'accepted', 'dismissed', 'deferred', 'blocked'
    validation_issues: tuple
    normalized_fields: tuple  # e.g., ('email', 'phone')
    normalization_warnings: tuple
    
    # Derived duplicate grouping (derived only, not persisted)
    duplicate_group_id: Optional[str]  # e.g., 'DUP-GROUP-{hash8}'
    duplicate_decision: Optional[str]  # 'same_person', 'different_people', 'deferred'
    duplicate_warnings: tuple
    
    # Derived household grouping (derived only, not persisted)
    household_group_id: Optional[str]
    household_group_label: Optional[str]
    household_members: tuple
    household_decision: Optional[str]  # 'confirmed', 'rejected', 'deferred'
    household_warnings: tuple
    
    # Aggregate warnings and readiness
    export_warnings: tuple
    export_blocked: bool
    export_derived_at: datetime
```

### ExportPreviewResult Shape

**Location:** `scripts/householder/service_contracts.py:540`

```python
@dataclass(frozen=True)
class ExportPreviewResult:
    import_id: str
    export_rows: tuple  # Tuple of ExportRow objects
    blockers: tuple  # Tuple of blocker strings
    warnings: tuple  # Tuple of warning strings
    row_count: int
    blocked_count: int
    warning_count: int
    is_export_ready: bool  # True iff blocked_count == 0
    derived_at: datetime
```

### Current Preview Route Behavior

**Location:** `scripts/uploader/app.py:1034`

```python
@app.route('/imports/<import_id>/exports/preview', methods=['POST'])
def preview_export(import_id):
    """Generate export preview based on reviewer decisions."""
    try:
        preview = export_preview_service.build_export_preview(import_id)
        data = exports_service.get_export_console(import_id)
        data['preview'] = preview.to_template_dict()
        data['preview_available'] = True
        return render_template('imports/exports.html', **data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error generating export preview: {str(e)}")
        return jsonify({'error': 'Error generating preview'}), 500
```

**Behavior:**
- Calls `build_export_preview()` which derives export rows from decisions
- Does NOT create any file
- Does NOT write audit log
- Does NOT mutate any source data
- Returns template rendering with preview data embedded

### Current Blocker/Warning Behavior

**Blocker Logic (from export_preview_service.py):**
- Blockers are unresolved critical validation issues (missing_email, invalid_email_format, missing_transaction_id, invalid_amount)
- One blocker per unresolved critical issue
- `is_export_ready = (blocked_count == 0)`

**Warning Logic:**
- Warnings are deferred decisions, unresolved non-critical issues, malformed payloads
- Warnings do NOT block export in preview stage
- Include separate arrays for normalization_warnings, duplicate_warnings, household_warnings

**Current Tests Proving No File Generation:**
- `test_preview_does_not_create_files()` — verifies response is HTML, not download
- `test_preview_does_not_create_audit_records()` — verifies no AuditLogRecord written
- `test_preview_does_not_mutate_raw_rows()` — raw_csv_data unchanged
- `test_preview_does_not_mutate_import_contacts()` — contact fields unchanged
- `test_preview_does_not_mutate_review_decisions()` — decision count unchanged

### Current UI Behavior

**Location:** `scripts/uploader/templates/imports/exports.html`

**Current State:**
- Shows "Ready to Export" button ("Generate Export Package")
- Shows export format options (cards with placeholders)
- Shows "Recent Exports" section (currently empty)
- Safety footer confirms no CRM writeback
- No live preview data displayed in template yet

**What's Missing:**
- No actual preview data rendering
- No blocker/warning display when preview generated
- No export readiness state display
- No file generation workflow

---

## Part 2: Proposed File Generation Scope

### Recommended First Scope

**CSV Export Only**

- Generate CSV file only in Phase 2-Step 13
- Use `build_export_preview()` as source of truth
- Generate file only when explicitly requested (POST action)
- If blockers exist, refuse file generation with clear error
- If warnings exist but no blockers, allow generation and include warning summary in audit details
- DO NOT implement in first step: JSON, CRM-ready formats, multi-file export packages

### What This Step WILL Do

✅ Generate CSV file from ExportRow data  
✅ Store file in configured directory  
✅ Create one AuditLogRecord for each generation  
✅ Include decision summary in audit details  
✅ Handle warnings without blocking export  
✅ Prevent file generation when blockers exist  
✅ Sanitize filenames and prevent path traversal  

### What This Step Will NOT Do

❌ Givebutter/CRM writeback  
❌ Automatic export generation on page load  
❌ Background jobs or async processing  
❌ Persistent export history table (log to audit_log only)  
❌ Multi-format export packages  
❌ JSON export format  
❌ CRM-specific export formats  
❌ Direct browser download streaming  
❌ Mutation of contacts or source data  
❌ Durable merged contact records  
❌ Durable household master records  

---

## Part 3: Export File Service Contract

### Proposed Service Interface

**Location:** `scripts/householder/export_file_service.py` (new)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Mapping, Any

@dataclass(frozen=True)
class ExportFileResult:
    """Result of successful export file generation."""
    import_id: str
    filename: str
    file_path: str
    row_count: int
    warning_count: int
    blocked_count: int
    audit_log_id: Optional[int]
    generated_at: datetime
    
    def to_dict(self) -> dict:
        """Convert to dictionary for template/JSON response."""
        return {
            "import_id": self.import_id,
            "filename": self.filename,
            "file_path": self.file_path,
            "row_count": self.row_count,
            "warning_count": self.warning_count,
            "blocked_count": self.blocked_count,
            "audit_log_id": self.audit_log_id,
            "generated_at": self.generated_at.isoformat(),
        }


def generate_export_file(
    import_id: str,
    output_dir: str,
    reviewer: Optional[str] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> ExportFileResult:
    """
    Generate CSV export file from derived preview.
    
    Explicit export file generation with audit logging.
    Does NOT mutate source data or call external systems.
    
    Args:
        import_id: Import batch ID
        output_dir: Directory to write export file (must be configured, not user-provided)
        reviewer: Optional reviewer identifier for audit log
        config: Optional configuration for database selection
    
    Returns:
        ExportFileResult with file metadata and audit log reference
    
    Raises:
        ValueError: If batch not found or database config invalid
        ExportBlockedError: If blockers exist in preview
        ExportError: For filesystem or other errors
    
    Behavior:
        1. Build export preview using build_export_preview()
        2. If is_export_ready == False, raise ExportBlockedError
        3. Generate CSV from export_rows
        4. Write file to output_dir with sanitized filename
        5. Create AuditLogRecord with action_type='export_generated'
        6. Return ExportFileResult with file path and audit log reference
    
    Does NOT:
        - Mutate raw_import_rows, import_contacts, review_items, review_decisions
        - Write back to Givebutter/CRM
        - Create durable duplicate or household records
        - Perform automatic approvals or resolutions
    """
```

### Error Hierarchy

```python
class ExportError(Exception):
    """Base exception for export operations."""
    pass

class ExportBlockedError(ExportError):
    """Export blocked due to unresolved issues."""
    def __init__(self, blockers: List[str], blocked_count: int):
        self.blockers = blockers
        self.blocked_count = blocked_count
        self.message = f"Export blocked: {blocked_count} unresolved issue(s)"
        super().__init__(self.message)

class ExportIOError(ExportError):
    """File I/O error during export generation."""
    pass
```

### Input Validation

- `import_id`: Must exist in database
- `output_dir`: Must be configured path, NOT user-provided directory
- `reviewer`: Optional, used in audit log
- `config`: Optional database configuration

### File Naming Convention

**Pattern:**
```
{import_id}_export_{YYYYMMDD_HHMMSS}.csv
```

**Examples:**
```
IMP-2025-0101-A_export_20260612_143022.csv
IMP-2025-0102-B_export_20260612_143100.csv
```

**Sanitization:**
- Remove all path separators (/, \)
- Replace spaces with underscores
- Allow only alphanumeric, hyphen, underscore
- Prevent directory traversal with `os.path.basename()`

### File Location

**Configuration:**
- Must come from environment variable: `EXPORT_OUTPUT_DIR`
- Must be absolute path
- Must NOT be user-provided or query parameter
- Must NOT be relative to source tree

**Test Isolation:**
- pytest `tmp_path` fixture for test exports
- No temp files left on disk after tests
- Cleanup in test teardown

**Development:**
- Configured via environment variable
- Default: `/var/tmp/givebutter/exports` or similar (out of source tree)

**Example Configuration:**
```bash
export EXPORT_OUTPUT_DIR=/var/tmp/givebutter/exports
# OR for testing
pytest --export-output-dir=/tmp/exports tests/
```

---

## Part 4: CSV Output Contract

### CSV Header Row

**Order and Encoding:**

```
source_row_index,transaction_id,first_name,last_name,email,phone,address_line1,address_line2,city,state,postal_code,amount,validation_status,normalized_fields,normalization_warnings,duplicate_group_id,duplicate_decision,duplicate_warnings,household_group_id,household_group_label,household_members,household_decision,household_warnings,export_warnings
```

### Field Encoding Rules

| Field | Type | Encoding | Example |
|-------|------|----------|---------|
| `source_row_index` | int | Integer or empty | `1` |
| `transaction_id` | string | UTF-8, quoted if contains comma | `TXN-001` |
| `first_name` | string | UTF-8, quoted if contains comma | `John` |
| `last_name` | string | UTF-8, quoted if contains comma | `Smith` |
| `email` | string | UTF-8, quoted | `john@example.com` |
| `phone` | string | UTF-8, quoted | `555-1234` |
| `amount` | string | Numeric or empty | `100.00` |
| Tuple fields (normalized_fields, etc.) | list | Semicolon-separated or JSON array | `email;phone` OR `["email","phone"]` |
| Warning fields | list | Semicolon-separated text | `Field email normalization deferred; Missing email` |
| `validation_status` | string | Single value | `accepted`, `dismissed`, `deferred`, `pending`, `blocked` |
| `duplicate_group_id` | string | Alphanumeric or empty | `DUP-GROUP-a3f7b8c2` |
| `household_members` | list | Semicolon-separated IDs | `1;2;3` |

### Special Values

- **NULL/None:** Rendered as empty string (`""` in CSV)
- **Boolean/Blocked:** `export_warnings` tuple always included even if empty
- **Timestamps:** Not included in CSV (preserved in audit log only)

### CSV Generation Example

```csv
source_row_index,transaction_id,first_name,last_name,email,phone,address_line1,address_line2,city,state,postal_code,amount,validation_status,normalized_fields,normalization_warnings,duplicate_group_id,duplicate_decision,duplicate_warnings,household_group_id,household_group_label,household_members,household_decision,household_warnings,export_warnings
1,TXN-001,John,Smith,john@example.com,555-1234,123 Main St,,Springfield,IL,62701,100.00,accepted,email,,DUP-GROUP-a3f7b8c2,same_person,,HH-123,Smith Household,1;2,confirmed,,
2,TXN-002,Jane,Smith,jane@example.com,555-1234,123 Main St,,Springfield,IL,62701,50.00,pending,,,,deferred,Duplicate pair unresolved,HH-123,Smith Household,1;2,confirmed,,
```

---

## Part 5: Blocker/Warning Behavior

### Blocker Logic

**Definition:** Unresolved critical validation issues

**Critical Issue Types:**
- `missing_email`
- `invalid_email`
- `invalid_email_format`
- `missing_transaction_id`
- `invalid_amount`
- `invalid_amount_zero_or_negative`

**Export Generation Rule:**
```python
if preview.is_export_ready == False:
    raise ExportBlockedError(
        blockers=preview.blockers,
        blocked_count=preview.blocked_count
    )
```

**Response:**
- HTTP 400 with error message
- Include blocker summary in error response
- Do NOT generate file
- Do NOT create audit log

**Example Error Response:**
```json
{
  "error": "Export blocked: 2 unresolved critical issues",
  "blockers": [
    "Unresolved validation: missing_email",
    "Unresolved validation: invalid_amount"
  ],
  "blocked_count": 2
}
```

### Warning Logic

**Definition:** Deferred decisions, unresolved non-critical issues, malformed payloads

**Warning Sources:**
- Deferred normalization decisions
- Deferred validation decisions
- Deferred duplicate decisions
- Deferred household decisions
- Unresolved non-critical validation issues

**Export Generation Rule:**
```python
if preview.warning_count > 0:
    # Allow generation but include warnings in audit details
    include_warnings_in_audit(preview.warnings)
```

**CSV Rendering:**
- Warning columns included in CSV as semicolon-separated text
- Can be empty if no warnings

**Audit Log Inclusion:**
```json
{
  "warnings_summary": [
    "Field email normalization deferred",
    "Duplicate pair unresolved"
  ],
  "warning_count": 2
}
```

---

## Part 6: Audit Behavior

### AuditLogRecord Creation

**Action Type:**
```python
action_type = "export_generated"
```

**Audit Log Details (JSON):**

```json
{
  "export_type": "csv",
  "filename": "IMP-2025-0101-A_export_20260612_143022.csv",
  "file_path": "/var/tmp/givebutter/exports/IMP-2025-0101-A_export_20260612_143022.csv",
  "row_count": 100,
  "warning_count": 3,
  "blocked_count": 0,
  "is_export_ready": true,
  "decision_summary": {
    "validation_decisions": 10,
    "normalization_decisions": 7,
    "duplicate_decisions": 3,
    "household_decisions": 2
  },
  "warnings_summary": [
    "Field email normalization deferred",
    "Duplicate pair unresolved",
    "Household grouping unresolved"
  ],
  "generated_by": "reviewer@example.com",
  "generated_at": "2026-06-12T14:30:22Z"
}
```

### Immutability

- **NO MUTATIONS** to existing audit records
- Only append one new record
- Do NOT update or delete audit_log records
- All decisions logged in one atomic write

### Error Handling

If generation fails BEFORE file is written:
- Do NOT create audit record
- Return error response
- Database transaction rollback if needed

If generation fails AFTER file is written:
- File may exist on disk
- Create audit record with error status (optional separate error action type)
- Allow cleanup/retry

---

## Part 7: Route/API Shape

### Proposed POST Route

**Endpoint:**
```
POST /imports/<import_id>/exports/generate
```

**Request Body:** (optional)
```json
{
  "format": "csv"  // Optional, defaults to "csv"
}
```

**Response on Success (200):**
```json
{
  "status": "success",
  "file": {
    "import_id": "IMP-2025-0101-A",
    "filename": "IMP-2025-0101-A_export_20260612_143022.csv",
    "row_count": 100,
    "warning_count": 3,
    "blocked_count": 0,
    "generated_at": "2026-06-12T14:30:22Z",
    "audit_log_id": 12345
  }
}
```

**Response on Blocker (400):**
```json
{
  "status": "blocked",
  "error": "Export blocked: 2 unresolved critical issues",
  "blockers": [
    "Unresolved validation: missing_email",
    "Unresolved validation: invalid_amount"
  ],
  "blocked_count": 2
}
```

**Response on Error (500):**
```json
{
  "status": "error",
  "error": "Failed to generate export: [error details]"
}
```

### Handler Implementation Pattern

```python
@app.route('/imports/<import_id>/exports/generate', methods=['POST'])
def generate_export(import_id):
    """Explicitly generate export file from approved preview."""
    try:
        reviewer = request.headers.get('X-Reviewer-ID')
        result = export_file_service.generate_export_file(
            import_id=import_id,
            output_dir=current_app.config['EXPORT_OUTPUT_DIR'],
            reviewer=reviewer,
        )
        return jsonify({
            "status": "success",
            "file": result.to_dict()
        }), 200
    except ExportBlockedError as e:
        return jsonify({
            "status": "blocked",
            "error": e.message,
            "blockers": e.blockers,
            "blocked_count": e.blocked_count
        }), 400
    except ExportError as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": f"Failed to generate export: {str(e)}"
        }), 500
```

### UI Integration

After successful generation, return to exports.html with:
- File metadata in "Recent Exports" section
- Filename, row count, warning count, generation timestamp
- Link to view/download file (future enhancement)

---

## Part 8: File Storage Policy

### Storage Directory Configuration

**Environment Variable:**
```bash
EXPORT_OUTPUT_DIR=/var/tmp/givebutter/exports
```

**Requirements:**
- Absolute path, not relative
- Not in source tree
- World-writable (if running as unprivileged user)
- Sufficient disk space

**Default Fallback:**
```python
import os
export_dir = os.environ.get('EXPORT_OUTPUT_DIR', '/tmp/givebutter/exports')
os.makedirs(export_dir, exist_ok=True)
```

### Test File Isolation

```python
@pytest.fixture
def temp_export_dir(tmp_path):
    """Temporary export directory for tests."""
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    monkeypatch.setenv('EXPORT_OUTPUT_DIR', str(export_dir))
    yield export_dir
    # Cleanup automatic with tmp_path
```

### Filename Sanitization

```python
def sanitize_filename(filename: str) -> str:
    """Prevent directory traversal and invalid characters."""
    # Remove path separators
    filename = filename.replace('/', '').replace('\\', '')
    # Remove leading dots
    filename = filename.lstrip('.')
    # Limit to alphanumeric, hyphen, underscore, dot
    filename = ''.join(c for c in filename if c.isalnum() or c in '-_.')
    return filename

def generate_export_filename(import_id: str, timestamp: datetime) -> str:
    """Generate safe export filename."""
    sanitized_id = sanitize_filename(import_id)
    ts = timestamp.strftime('%Y%m%d_%H%M%S')
    return f"{sanitized_id}_export_{ts}.csv"
```

### Collision Avoidance

- Use timestamp with second precision
- If collision occurs, append `_01`, `_02`, etc.

---

## Part 9: UI Behavior

### Export Console Template Updates

**File:** `scripts/uploader/templates/imports/exports.html`

### New Sections

1. **Preview Status Display** (if preview available)
   ```html
   <div id="preview-status" style="...">
     <p>Preview available: {{ preview.row_count }} rows</p>
     {% if preview.blocked_count > 0 %}
       <div style="background-color: #fee; ...">
         <p><strong>Export Blocked:</strong> {{ preview.blocked_count }} unresolved issue(s)</p>
         <ul>
           {% for blocker in preview.blockers %}
             <li>{{ blocker }}</li>
           {% endfor %}
         </ul>
       </div>
     {% else %}
       <p><strong>Export Ready:</strong> Click "Generate Export" to create file.</p>
     {% endif %}
     {% if preview.warning_count > 0 %}
       <div style="background-color: #fef3c7; ...">
         <p><strong>Warnings ({{ preview.warning_count }}):</strong></p>
         <ul>
           {% for warning in preview.warnings %}
             <li>{{ warning }}</li>
           {% endfor %}
         </ul>
       </div>
     {% endif %}
   </div>
   ```

2. **Generate Export Button** (enabled only if not blocked)
   ```html
   <button 
     type="button" 
     class="btn btn-primary"
     id="generate-export-btn"
     {% if preview.blocked_count > 0 %}disabled{% endif %}
     onclick="generateExportFile()"
   >
     Generate CSV Export
   </button>
   ```

3. **Generated File Display** (in Recent Exports section)
   ```html
   <div style="...">
     <p><strong>{{ recent_export.filename }}</strong></p>
     <p>Generated: {{ recent_export.generated_at }}</p>
     <p>Rows: {{ recent_export.row_count }}, Warnings: {{ recent_export.warning_count }}</p>
   </div>
   ```

### JavaScript Handler

```javascript
function generateExportFile() {
  // Show loading state
  const btn = document.getElementById('generate-export-btn');
  btn.disabled = true;
  btn.textContent = 'Generating...';
  
  fetch('/imports/{{ batch.id }}/exports/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === 'success') {
      // Refresh page to show generated file
      window.location.reload();
    } else if (data.status === 'blocked') {
      alert('Export blocked:\n' + data.blockers.join('\n'));
      btn.disabled = false;
      btn.textContent = 'Generate CSV Export';
    } else {
      alert('Error: ' + data.error);
      btn.disabled = false;
      btn.textContent = 'Generate CSV Export';
    }
  })
  .catch(err => {
    alert('Failed to generate export: ' + err.message);
    btn.disabled = false;
    btn.textContent = 'Generate CSV Export';
  });
}
```

### What NOT to Add

❌ Do NOT add CRM/send buttons  
❌ Do NOT add "Auto-Export" checkbox  
❌ Do NOT add download link yet (return file metadata only)  
❌ Do NOT show "Export History" from persistent table (not created in this step)  

---

## Part 10: Test Strategy

### Unit Tests (20 proposed)

**File:** `tests/unit/test_export_file_service.py`

1. **Configuration & Validation (3 tests)**
   - test_missing_database_config_raises_error
   - test_missing_output_dir_raises_error
   - test_invalid_import_raises_error

2. **Blocker Detection (4 tests)**
   - test_generation_blocked_if_blockers_exist
   - test_blocker_error_includes_summary
   - test_blocker_error_does_not_generate_file
   - test_blocker_error_does_not_create_audit_record

3. **Warning Handling (3 tests)**
   - test_generation_succeeds_with_warnings
   - test_warning_count_in_result
   - test_warnings_in_audit_details

4. **CSV Generation (4 tests)**
   - test_csv_header_matches_contract
   - test_csv_row_count_matches_preview
   - test_csv_normalized_fields_applied
   - test_csv_none_values_rendered_as_empty_string

5. **File Operations (4 tests)**
   - test_file_created_in_output_dir
   - test_filename_follows_convention
   - test_filename_sanitization_prevents_traversal
   - test_file_not_created_on_blockers

6. **Audit Logging (2 tests)**
   - test_audit_log_record_created_on_success
   - test_audit_log_includes_decision_summary

### Integration Tests (15 proposed)

**File:** `tests/integration/test_export_file_route.py`

1. **Route Behavior (4 tests)**
   - test_generate_route_returns_200_on_success
   - test_generate_route_returns_400_on_blockers
   - test_generate_route_returns_500_on_error
   - test_generate_route_requires_import_id

2. **Success Cases (5 tests)**
   - test_export_generated_with_no_warnings
   - test_export_generated_with_warnings
   - test_response_includes_file_metadata
   - test_response_includes_audit_log_reference
   - test_file_path_in_response_is_valid

3. **Error Cases (4 tests)**
   - test_blockers_prevent_file_generation
   - test_error_response_includes_blocker_summary
   - test_missing_config_returns_clear_error
   - test_invalid_batch_returns_clear_error

4. **Immutability Verification (2 tests)**
   - test_no_mutations_to_raw_rows_or_contacts
   - test_no_external_system_calls_made

### Guardrail Tests (8 proposed)

**File:** `tests/integration/test_export_file_guardrails.py`

1. **No File Generation on Blockers (1 test)**
   - test_no_csv_file_when_blockers_exist

2. **Audit Logging (2 tests)**
   - test_one_audit_record_created_per_generation
   - test_no_audit_record_on_blockers

3. **Source Data Immutability (5 tests)**
   - test_raw_rows_not_mutated
   - test_import_contacts_not_mutated
   - test_review_items_not_mutated
   - test_review_decisions_not_mutated
   - test_audit_log_append_only

---

## Part 11: Explicit Non-Goals

### Explicitly Excluded from Phase 2-Step 13

❌ **Givebutter/CRM Writeback**
- No API calls to Givebutter
- No duplicate merge in external system
- No household creation in external system

❌ **Automatic Export Generation**
- No export on page load
- No background jobs
- No scheduled exports
- Export only on explicit POST request

❌ **Multi-Format Exports**
- CSV only in this step
- No JSON export
- No CRM-specific formats
- No Excel/XLSX
- No multi-file packages

❌ **Download Streaming**
- Return file metadata only
- Do NOT stream file to browser in first step
- Download route can be added in Phase 2-Step 14

❌ **Persistent Export History**
- Log to audit_log only
- Do NOT create `export_history` table
- Do NOT create durable export records

❌ **Automatic Resolution**
- Do NOT automatically approve unresolved decisions
- Do NOT auto-resolve duplicates
- Do NOT auto-confirm households
- Export only reflects current explicit decisions

❌ **Data Mutation**
- Do NOT merge contacts
- Do NOT create household master records
- Do NOT denormalize contact data
- Raw data remains unchanged

❌ **CRM-Ready Formats**
- No contact dedupe fields
- No CRM ID fields
- No CRM import mapping
- Save for future phase if needed

---

## Part 12: Implementation Prompt for Phase 2-Step 14

**Recommended Phase 2-Step 14 Prompt:**

```
Phase 2-Step 14: Implement Export File Generation — CSV Only, Audited, No CRM Writeback

Current state:
- Phase 2-Step 13 planning complete and accepted
- All prerequisites complete (preview derivation)
- Full test suite passing (1082 tests)

Goal:
Implement explicit CSV export file generation from approved preview.

Tasks:
1. Create export_file_service.py with generate_export_file() function
2. Create ExportFileResult and error classes
3. Create POST /imports/<id>/exports/generate route
4. Create unit tests (20 tests)
5. Create integration tests (15 tests)
6. Create guardrail tests (8 tests)
7. Update exports.html template to show preview status and generate button
8. Update exports_service.py to optionally return generated file metadata
9. Run full test suite and confirm 1082+ tests passing
10. Create completion record with test results

Do not implement:
- Download streaming (defer to later)
- CRM writeback
- Multi-format exports
- Persistent export history table
- Automatic approval or resolution

Guardrails:
- No mutations to source data
- No external system calls
- Audit every generation
- Block generation on unresolved issues
- Allow warnings but include in audit details
```

---

## Summary

### Key Decisions

1. **CSV Only** — Simplify Phase 2-Step 13 scope to CSV format only
2. **Explicit Generation** — POST request only, no automatic export
3. **Block on Blockers** — Refuse file generation if critical issues unresolved
4. **Allow Warnings** — Proceed with generation if warnings but no blockers
5. **Audit Everything** — Log each generation attempt (success or failure)
6. **No CRM Writeback** — Export is file preparation only
7. **Config-Based Storage** — Export directory from environment, not user input
8. **One File Per Request** — Generate file immediately on POST

### Test Coverage Plan

- 20 unit tests (CSV generation, filename handling, error cases)
- 15 integration tests (route behavior, success/error cases)
- 8 guardrail tests (immutability, audit logging, no external calls)
- 43 total new tests + existing 1082 = 1125 tests expected

### Files to Create/Modify

**Create:**
- `scripts/householder/export_file_service.py` (~300 lines)
- `tests/unit/test_export_file_service.py` (~400 lines)
- `tests/integration/test_export_file_route.py` (~400 lines)
- `tests/integration/test_export_file_guardrails.py` (~300 lines)

**Modify:**
- `scripts/uploader/app.py` (add generate route, ~50 lines)
- `scripts/uploader/templates/imports/exports.html` (add preview display, ~100 lines)
- `scripts/householder/exports_service.py` (optional, ~20 lines)

### Open Questions

1. **File Download Later?** Should Phase 2-Step 14 add streaming download, or defer to later?
2. **File Retention?** How long should export files be kept? Delete after 7 days? Query audit_log to list?
3. **File Size Limits?** Should there be a max CSV size? Recommendations for large batches?
4. **Concurrent Exports?** Multiple reviewers generating exports simultaneously — handled by timestamp collision logic?

---

**Status:** ✅ Planning Complete, Ready for Phase 2-Step 14 Implementation
