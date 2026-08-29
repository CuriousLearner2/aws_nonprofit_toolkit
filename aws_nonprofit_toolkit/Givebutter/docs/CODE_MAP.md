# Householder v1 — Code & Test Map

**Purpose:** Trace each P1 use case from UI to service to persistence to tests.

**Verification Date:** 2026-08-28 (verified against HEAD)

---

## P1 Use Case Map

| Use Case | UI/Template | Route/API | Primary Service | Persistence Model/Repository | Focused Tests |
|----------|-------------|-----------|-----------------|------------------------------|---------------|
| **Upload Batch** | `list.html` | POST `/upload` | `import_service.py` | `ImportBatch`, `RawImportRow`, `database_repository.py` | `tests/integration/test_upload_ingestion_route.py` |
| **View Dashboard** | `dashboard.html` | GET `/imports/<id>/dashboard` | `dashboard_service.py` | `ImportContact`, `ReviewItem`, `ReviewDecision` | `tests/integration/test_dashboard_route.py` |
| **Review Validation** | `validation.html` | GET `/imports/<id>/validation` | `validation_service.py` | `ReviewItem`, `ReviewItemSubject`, `ReviewDecision`, `ImportContact` | `tests/integration/test_validation_decision_route.py`, `test_autosave_validation.py` |
| **Save Correction** | `validation.html` (inline edit) | POST `/imports/<id>/autosave` | `row_status_service.py`, `issue_recalculation_service.py` | `AutosaveDecision`, `ImportContact` | `tests/integration/test_autosave_validation.py`, `test_autosave_validation_sync.py` |
| **Record Validation Decision** | `validation.html` | POST `/imports/<id>/validation/<review_item_id>/decision` | `validation_service.py`, `row_decision_service.py` | `ReviewDecision`, `AuditLogRecord` | `tests/integration/test_validation_decision_route.py` |
| **Review Duplicates** | `duplicates.html` | GET `/imports/<id>/duplicates` | `duplicates_service.py` | `ReviewItem` (item_type='duplicate'), `ReviewDecision` | `tests/integration/test_duplicate_decision_route.py` |
| **Record Duplicate Decision** | `duplicates.html` | POST `/imports/<id>/duplicates/<review_item_id>/decision` | `duplicates_service.py`, `row_decision_service.py` | `ReviewDecision`, `AuditLogRecord` | `tests/integration/test_duplicate_decision_route.py` |
| **Review Households** | `households.html` | GET `/imports/<id>/households` | `households_service.py` | `ReviewItem` (item_type='household'), `ReviewDecision` | `tests/integration/test_household_decision_route.py` |
| **Record Household Decision** | `households.html` | POST `/imports/<id>/households/<review_item_id>/decision` | `households_service.py`, `row_decision_service.py` | `ReviewDecision`, `AuditLogRecord` | `tests/integration/test_household_decision_route.py` |
| **Review Normalizations** | `normalizations.html` | GET `/imports/<id>/normalizations` | `normalizations_service.py` | `ReviewItem` (item_type='normalization'), `ReviewDecision` | `tests/integration/test_normalizations_route.py` |
| **Record Normalization Decision** | `normalizations.html` | POST `/imports/<id>/normalizations/<review_item_id>/decision` | `normalizations_service.py`, `row_decision_service.py` | `ReviewDecision`, `AuditLogRecord` | `tests/integration/test_normalizations_route.py` |
| **Check Readiness** | `readiness.html` | GET `/imports/<id>/readiness` | `approval_service.py`, `row_status_service.py` | `ReviewItem`, `ReviewDecision`, `ImportContact` | `tests/integration/test_readiness_route.py` |
| **Approve Batch** | `readiness.html` button | POST `/imports/<id>/approve-batch` | `approval_service.py` | `ImportBatch`, `AuditLogRecord` | `tests/integration/test_readiness_route.py` |
| **Generate Export** | `exports.html` | POST `/imports/<id>/exports/generate` | `export_file_service.py`, `export_preview_service.py` | `AutosaveDecision`, `ReviewDecision`, `ImportContact` | `tests/integration/test_export_file_route.py`, `test_export_preview_consistency.py` |
| **Download Export** | `exports.html` download link | GET `/imports/<id>/exports/<export_id>/download` | `export_download_service.py` | `ExportRecord` | `tests/integration/test_export_download_route.py` |

---

## Representative Trace: End-to-End Data Flow

### Scenario: Upload → Issue → Correction → Decision → Export

**Step 1: Upload CSV**
```
POST /upload
  → Route handler: scripts/uploader/app.py:308
  → Service: import_service.py (creates ImportBatch)
  → Models stored: ImportBatch, RawImportRow, ImportContact, ReviewItem
  → Test: tests/integration/test_upload_ingestion_route.py
```

**Step 2: System Detects Issue (Email Typo)**
```
Raw value: "gmai.com"
System validation: email validation_service.py:phone_validation_service.py
Issue detected: Invalid email domain
ReviewItem created with payload_json: {"field": "email", "issue": "invalid_email"}
Test coverage: tests/integration/test_autosave_validation.py
```

**Step 3: Reviewer Corrects Value (Autosave)**
```
POST /imports/<id>/autosave
  → Route handler: scripts/uploader/app.py:1490
  → Service: row_status_service.py, issue_recalculation_service.py
  → Model: AutosaveDecision stored
  → Effective value updated: "gmail.com"
  → Row status recalculated: PASS (no issues remain)
  → Test: tests/integration/test_autosave_validation_sync.py
```

**Step 4: Reviewer Records Decision (if manual correction)**
```
POST /imports/<id>/validation/<review_item_id>/decision
  → Route handler: scripts/uploader/app.py:1404
  → Service: validation_service.py, row_decision_service.py
  → Model: ReviewDecision stored with decision='accept_issue'
  → Audit: AuditLogRecord created
  → Test: tests/integration/test_validation_decision_route.py
```

**Step 5: Verify Readiness**
```
GET /imports/<id>/readiness
  → Route handler: scripts/uploader/app.py:1343
  → Service: approval_service.py, row_status_service.py
  → Check: All validation decisions made, all rows PASS/ACCEPTED
  → Result: "Ready for export"
  → Test: tests/integration/test_readiness_route.py
```

**Step 6: Generate Export**
```
POST /imports/<id>/exports/generate
  → Route handler: scripts/uploader/app.py:2078
  → Service: export_file_service.py
  → Logic:
    1. Build export_preview using export_preview_service.py
    2. Apply all AutosaveDecision effective values
    3. Apply all ReviewDecision dispositions
    4. Generate CSV with effective (reviewed) data
  → Model: ExportRecord stored
  → Output: CSV file written to disk
  → Test: tests/integration/test_export_file_route.py, test_export_preview_consistency.py
```

**Step 7: Download Export**
```
GET /imports/<id>/exports/<export_id>/download
  → Route handler: scripts/uploader/app.py:2191
  → Service: export_download_service.py
  → Result: CSV file downloaded
  → Test: tests/integration/test_export_download_route.py
```

**Audit Trail:**
```
AuditLogRecord entries created at each decision point:
  1. Batch uploaded (timestamp, uploader, row count)
  2. Validation decision recorded (timestamp, reviewer, field, decision)
  3. Batch approved (timestamp, reviewer, readiness status)
  4. Export generated (timestamp, reviewer, output files)

All entries append-only, never modified or deleted.
```

---

## Service Layer Organization

### Core Services by Function

**Data Validation & Review:**
- `validation_service.py` — Validation issue detection and decision handling
- `phone_validation_service.py` — Phone format and telecom validation
- `date_validation_service.py` — Date format and range validation
- `duplicates_service.py` — Duplicate detection and grouping
- `households_service.py` — Household relationship detection
- `normalizations_service.py` — Auto-correction application

**Decision & Status Management:**
- `row_decision_service.py` — Record and apply row-level decisions
- `row_status_service.py` — Calculate system-derived row status (PASS/WARNING/FAIL)
- `issue_recalculation_service.py` — Recalculate validation issues after autosave
- `approval_service.py` — Batch readiness validation

**Export & Output:**
- `export_preview_service.py` — Build export preview with current state
- `export_file_service.py` — Generate export CSV files
- `export_download_service.py` — Handle export file downloads

**Dashboard & Summary:**
- `dashboard_service.py` — Build dashboard with queue summaries

**Persistence:**
- `database_repository.py` — Data access layer (query, store, update)
- `repository_provider.py` — Inject repository for testing
- `database_models.py` — SQLAlchemy ORM models (ImportBatch, ImportContact, ReviewItem, ReviewDecision, etc.)

---

## Test Organization

### Integration Tests (Primary)
- `tests/integration/test_upload_ingestion_route.py` — Batch upload flow
- `tests/integration/test_validation_decision_route.py` — Validation review and decision
- `tests/integration/test_autosave_validation.py` — Inline correction and recalculation
- `tests/integration/test_export_preview_consistency.py` — Export preview building
- `tests/integration/test_export_file_route.py` — Export generation and download
- `tests/integration/test_readiness_route.py` — Readiness checking and batch approval
- `tests/integration/test_duplicate_decision_route.py` — Duplicate decisions
- `tests/integration/test_household_decision_route.py` — Household decisions
- `tests/integration/test_normalizations_route.py` — Normalization decisions

### Unit Tests (Service Layer)
- `tests/unit/test_row_status_service.py` — Row status calculation
- `tests/unit/test_export_preview_service.py` — Export preview logic
- `tests/unit/test_approval_service.py` — Readiness validation
- `tests/unit/test_validation_service.py` — Validation rules
- `tests/unit/test_phone_validation_service.py` — Phone validation logic

### E2E Tests
- `tests/e2e/test_validation_export_blocking.py` — Full workflow validation

---

## Key Models & Relationships

**Core Persistent Models** (in `database_models.py`):

```
ImportBatch (batch_id, filename, status, ...)
  ├─ RawImportRow (raw_import_row_id, row_index, raw_csv_data)
  │   └─ ImportContact (contact_id, first_name, last_name, email, phone, ...)
  │
  ├─ ReviewItem (review_item_id, item_type, payload_json)
  │   ├─ ReviewItemSubject (links to ImportContact for context)
  │   └─ ReviewDecision (decision, reviewed_values, timestamp, reviewer)
  │
  ├─ AutosaveDecision (autosave_id, field, user_value, timestamp)
  │   └─ Applied via row_status_service on-the-fly
  │
  └─ AuditLogRecord (audit_id, action_type, timestamp, reviewer, details)

ExportRecord (export_id, batch_id, file_path, status, timestamp)
```

**Effective Value Resolution** (not persisted, calculated):
1. Start with RawImportRow.raw_csv_data
2. Apply AutosaveDecision overrides (if any)
3. Apply ReviewDecision.reviewed_values (if any)
4. Return as effective value for export

---

## How to Use This Map

**For Feature Owners:**
- Find your use case in the table above
- Verify the route, service, and test files exist at paths listed
- Add new tests as needed to the matching test file

**For Onboarding:**
- Use the "Representative Trace" section to understand full data flow
- Trace the same path through a test file to see actual implementation
- Model files are in `database_models.py`; repository is in `database_repository.py`

**For Debugging:**
- Find the affected use case in the table
- Check the service logic in the listed service file
- Look at the test file for expected behavior
- Check the model definition in `database_models.py`

---

**Last Updated:** 2026-08-28
**Verified By:** Code inspection against HEAD
