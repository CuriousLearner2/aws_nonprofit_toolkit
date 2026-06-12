# Phase 1B Schema Simplification Review (Updated)

**Date:** 2026-06-11  
**Status:** Design Review (Not Implementation)  
**Purpose:** Verify simplest v1 schema that does NOT block future larger match domain

**Updated Scope:** Added Option C (subject-reference design) to support future cross-import and existing-record matching

---

## Executive Summary

This review compares three database schema approaches:

- **Option A (Current):** Typed tables (8 tables, one per suggestion type)
- **Option B:** Simple generic review-items (5 tables, polymorphic JSON payload)
- **Option C (NEW):** Extensible review-items with subject references (6-7 tables, supports future matching without global master-person design)

**Key Product Insight:** v1 reviews current import only, but future must support:
- Comparing current import rows against existing database records
- Identifying duplicates across prior imports
- Detecting household relationships involving existing records
- WITHOUT requiring a global master-person/CRM system in Phase 1B

**Recommendation:** Option C is optimal. It preserves v1 simplicity while creating a path for future larger match domain through polymorphic subject references (not global identity tables).

Current Step 4 implementation should adopt Option C architecture before acceptance.

---

## Product Direction: Match Domain Evolution

### Phase 1B (Current)
- Review scope: Current import batch only
- Subjects: Rows within current batch only
- Examples: "Row 3 might be duplicate of Row 7", "Rows 2, 4, 5 could be one household"

### Phase 2+ (Future)
- Review scope: Current import + existing records
- Subjects: Current rows + prior import rows + future existing contact records
- Examples: "Row 3 matches existing contact #456", "Row 5 household relates to existing household #12"

**Schema must not lock us into Phase 1B subjects only.**

---

## Option A: Current Typed-Table Design

### Schema
```
imports
├─ id (PK)
├─ filename, upload_timestamp, metadata

raw_import_rows (append-only)
├─ id (PK)
├─ batch_id (FK), row_index
├─ raw_csv_data (JSON)

import_contacts (denormalized)
├─ id (PK)
├─ batch_id (FK), raw_import_row_id (FK)
├─ name, email, phone, address, amount fields

normalization_suggestions (import-scoped, typed)
├─ id (PK), batch_id (FK), raw_import_row_id (FK)
├─ field_name, raw_value, normalized_value, confidence

duplicate_candidates (import-scoped, typed)
├─ id (PK), batch_id (FK)
├─ raw_row_id_a, raw_row_id_b (FK pairs)
├─ match_type, confidence, evidence (JSON)

household_suggestions (import-scoped, typed)
├─ id (PK), batch_id (FK)
├─ suggested_label, confidence
├─ member_raw_row_ids (JSON array)

review_decisions
├─ id (PK), batch_id (FK)
├─ decision_type, target_id, decision, reviewer

audit_log (append-only)
├─ id (PK), batch_id (FK)
├─ action_type, actor, target_type, target_id, details (JSON)
```

**Total: 8 tables**

---

## Option B: Simple Generic Review-Items Design

### Schema
```
imports
├─ id (PK), filename, upload_timestamp, metadata

raw_import_rows (append-only)
├─ id (PK), batch_id (FK), row_index, raw_csv_data (JSON)

import_contacts (denormalized, optional in this option)
├─ id (PK), batch_id (FK), raw_import_row_id (FK)
├─ name, email, phone, address fields

review_items (append-only, polymorphic)
├─ id (PK), batch_id (FK)
├─ item_type ('normalization', 'duplicate', 'household')
├─ primary_row_id (FK → raw_import_rows)
├─ secondary_row_id (FK → raw_import_rows, nullable)
├─ item_data (JSON, polymorphic payload)
├─ confidence (Float), created_at

review_decisions
├─ id (PK), batch_id (FK), item_id (FK → review_items)
├─ decision ('accept', 'reject', 'same_person', 'different_person')
├─ reviewer, created_at

audit_log (append-only)
├─ id (PK), batch_id (FK)
├─ action_type, actor, item_id (FK), decision_id (FK)
├─ details (JSON), created_at
```

**Total: 6 tables**

**Problem:** Assumes all subjects are raw_import_rows from current batch. Cannot reference existing records without major refactoring.

---

## Option C: Extensible Review-Items with Subject References (RECOMMENDED)

### Schema

```
imports
├─ id (PK)
├─ filename, upload_timestamp, uploader
├─ status, raw_row_count
├─ created_at, updated_at

raw_import_rows (append-only, immutable)
├─ id (PK)
├─ batch_id (FK → imports)
├─ row_index, raw_csv_data (JSON)
├─ created_at

import_contacts (append-only, immutable snapshot)
├─ id (PK)
├─ batch_id (FK → imports)
├─ raw_import_row_id (FK → raw_import_rows)
├─ first_name, last_name, email, phone
├─ address_line1, address_line2, city, state, postal_code
├─ amount (Float, nullable)
├─ created_at

review_items (append-only, polymorphic, open-domain subjects)
├─ id (PK)
├─ batch_id (FK → imports)
├─ item_type ('validation', 'normalization', 'duplicate', 'household')
├─ status ('pending', 'reviewed', 'deferred', nullable)
├─ confidence (Float, nullable)
├─ payload_json (JSON, polymorphic: {field_name, raw_value, normalized_value} for normalization, {evidence, conflicts} for duplicate, etc.)
├─ created_at

review_item_subjects (explicit subject references, polymorphic)
├─ id (PK)
├─ review_item_id (FK → review_items)
├─ subject_type (String)  # Enum-like: 'import_raw_row', 'import_contact_snapshot', 'prior_import_row', 'prior_import_contact', 'existing_contact', 'existing_household'
├─ subject_id (Integer)  # ID within the subject_type entity
├─ role (String, nullable)  # 'primary', 'secondary', 'member', 'existing_match', etc.
├─ created_at

review_decisions (append-only)
├─ id (PK)
├─ batch_id (FK → imports)
├─ review_item_id (FK → review_items)
├─ decision (String)  # 'accept', 'reject', 'same_person', 'different_person', 'defer', 'confirmed'
├─ reviewed_values (JSON, nullable)
├─ reviewer (String, nullable)
├─ created_at

audit_log (append-only, immutable)
├─ id (PK)
├─ batch_id (FK → imports)
├─ action_type (String)  # 'item_created', 'decision_recorded', 'batch_imported'
├─ action_timestamp (DateTime)
├─ actor (String, nullable)
├─ item_id (FK → review_items, nullable)
├─ decision_id (FK → review_decisions, nullable)
├─ details (JSON, nullable)
├─ created_at

[FUTURE - NOT IN PHASE 1B]
existing_contacts
├─ id (PK)
├─ external_source_id, external_source_type
├─ first_name, last_name, email, phone, address
├─ created_from_import_date (if known)

existing_households
├─ id (PK)
├─ label (canonical household name)
├─ members (JSON array of existing_contact_ids)

prior_import_batches (archival)
├─ id (PK)
├─ original_batch_id (FK → imports, or null if data archival only)
├─ archive_date
```

**Total in Phase 1B: 7 tables**
**Future tables (Phase 2+): 3 optional tables for existing records**

---

## How Option C Supports Both v1 and Future

### Phase 1B (Current) Usage

Duplicate candidate within current import:
```
review_items:
  item_type='duplicate', payload_json={'evidence': [...], 'conflicts': [...]}

review_item_subjects (2 rows):
  [0] subject_type='import_raw_row', subject_id=3, role='primary'
  [1] subject_type='import_raw_row', subject_id=7, role='secondary'
```

Household suggestion within current import:
```
review_items:
  item_type='household', payload_json={'suggested_label': 'Smith Household', 'basis': '...'}

review_item_subjects (3 rows):
  [0] subject_type='import_raw_row', subject_id=2, role='member'
  [1] subject_type='import_raw_row', subject_id=4, role='member'
  [2] subject_type='import_raw_row', subject_id=5, role='member'
```

### Phase 2+ (Future) Usage

Duplicate between current import and existing record:
```
review_items:
  item_type='duplicate', payload_json={'evidence': [...], 'conflicts': [...]}

review_item_subjects (2 rows):
  [0] subject_type='import_raw_row', subject_id=3, role='primary'
  [1] subject_type='existing_contact', subject_id=456, role='existing_match'
```

Household relationship involving existing records:
```
review_items:
  item_type='household', payload_json={'basis': 'existing_member_found'}

review_item_subjects (2 rows):
  [0] subject_type='import_raw_row', subject_id=5, role='primary'
  [1] subject_type='existing_household', subject_id=12, role='existing_match'
```

**Key:** No schema changes needed. Just new subject_type values and optional existing_contacts/existing_households tables later.

---

## Evaluation Against All 11 Criteria

### 1. Simplicity

| Option | Score | Notes |
|--------|-------|-------|
| A | ⭐⭐ | Complex: 8 specialized tables, hard to understand relationships |
| B | ⭐⭐⭐⭐ | Simple: 5-6 tables, generic pattern, easy to grasp |
| C | ⭐⭐⭐ | Moderate: 7 tables, but polymorphic design clear once understood |

**Winner: B for v1 simplicity, but C necessary for future**

---

### 2. Ability to Support All 8 Current Screens

| Option | V1 Support | Notes |
|--------|-----------|-------|
| A | ✅ Full | Each screen maps to its table type |
| B | ✅ Full | Each screen queries review_items filtered by item_type |
| C | ✅ Full | Each screen queries review_items + join review_item_subjects; subject_type='import_raw_row' |

**Winner: Tie (all support v1 equally)**

---

### 3. Auditability

| Option | Score | Notes |
|--------|-------|-------|
| A | ⭐⭐⭐⭐ | Explicit: "normalization_suggestion created" vs "duplicate_candidate created" |
| B | ⭐⭐⭐ | Clear: "review_item created type=normalization"; payload_json detail in audit_log |
| C | ⭐⭐⭐⭐ | Clear: "review_item created"; audit_log captures payload_json + subject references |

**Winner: A (most explicit), but C adequate**

---

### 4. Query Complexity

| Option | Complexity | Examples |
|--------|-----------|----------|
| A | High | Multiple UNIONs to get dashboard counts. Separate SELECTs per type. Foreign keys scattered. |
| B | Low | `SELECT * FROM review_items WHERE batch_id=? AND item_type=?` Simple. `GROUP BY item_type` for counts. |
| C | Low-Moderate | `SELECT * FROM review_items WHERE batch_id=? AND item_type=?` INNER JOIN review_item_subjects ON type='import_raw_row'` Slight overhead vs B, but manageable. |

**Winner: B (simplest queries), C acceptable**

---

### 5. Migration Complexity

| Option | Complexity | Notes |
|--------|-----------|-------|
| A | High | 8 tables to create, each with constraints. Future changes require separate migrations per type. |
| B | Low | 5-6 tables. JSON payload evolves without migration. Adding item_types trivial. |
| C | Moderate | 7 tables + junction table. Slightly more complex than B, but much simpler than A. Adding subject_types trivial. |

**Winner: B (fewest tables), C close second**

---

### 6. Risk of Overbuilding

| Option | Risk | Rationale |
|--------|------|-----------|
| A | 🚨 HIGH | Each table optimized for one type. Locks in validation, normalization, duplicate, household schemas. If Phase 2 adds cross-import matching, would need refactoring. |
| B | ✅ LOW | Polymorphic JSON allows flexibility. But assumes all subjects are import_raw_rows; cannot reference external entities without redesign. |
| C | ✅ LOW | Polymorphic subjects allow future entity types without schema redesign. Just add new subject_type values and optional tables later. |

**Winner: C (best path for future without premature optimization)**

---

### 7. Ability to Support Future Larger Match Domain

| Option | Score | Future Path |
|--------|-------|------------|
| A | ❌ Poor | Would require adding cross_import_duplicates, cross_import_households, existing_contact_duplicates tables. Major refactoring. |
| B | ❌ Poor | Would need to replace primary/secondary_row_id with polymorphic subject references. Redesign needed. |
| C | ✅ Excellent | Just add new subject_type values ('existing_contact', 'prior_import_row', etc.) and optional tables later. No schema redesign. |

**Winner: C (clearly superior)**

---

### 8. Ability to Compare Against Existing DB Records Later

| Option | Score | Mechanism |
|--------|-------|-----------|
| A | ❌ Poor | No reference path for external entities. Would need new tables. |
| B | ❌ Poor | primary/secondary_row_id hard-coded to raw_import_rows. Cannot reference external contacts. |
| C | ✅ Excellent | review_item_subjects.subject_type can be 'import_raw_row' or 'existing_contact'. Seamless. |

**Winner: C (polymorphic references enable future matching)**

---

### 9. Avoidance of Global Master-Person / CRM Design

| Option | Score | Notes |
|--------|-------|-------|
| A | ✅ Good | Only imports/raw_rows/suggestions. No master tables. |
| B | ✅ Good | Same as A. Generic review_items, not person database. |
| C | ✅ Excellent | Subject references allow future existing_contacts without committing to master-person schema in Phase 1B. Existing tables added only when needed. |

**Winner: C (most flexible)**

---

### 10. Ease of Testing

| Option | Complexity | Notes |
|--------|-----------|-------|
| A | High | 8 table fixtures. Separate test setup per type. Parity tests complex. |
| B | Low | One review_item factory. Filter by item_type in tests. Fast to write. |
| C | Moderate | review_item factory + review_item_subjects factory. Slightly more setup than B, but still simple. Polymorphic subjects easy to test. |

**Winner: B (simplest), C acceptable**

---

### 11. Ease of Explaining to Future Developer

| Option | Explanation |
|--------|-----------|
| A | "We have 8 separate tables, one for each suggestion type. Normalization suggestions here, duplicates there, households there... [confusion]" |
| B | "We have review_items. Each has a type (normalization, duplicate, household) and JSON payload. Decisions reference items. [Clear]" |
| C | "We have review_items and review_item_subjects. Items represent suggested reviews. Subjects are what's being reviewed (current rows now, existing records later). [Flexible and clear]" |

**Winner: B (simplest explanation), but C only slightly more complex**

---

## Summary Scorecard

| Criterion | A | B | C |
|-----------|---|---|---|
| 1. Simplicity | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 2. Support 8 Screens | ✅ | ✅ | ✅ |
| 3. Auditability | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 4. Query Complexity | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 5. Migration Complexity | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 6. Overbuilding Risk | 🚨 HIGH | ✅ LOW | ✅ LOW |
| 7. **Future Match Domain** | ❌ | ❌ | ✅✅✅ |
| 8. **Compare Existing Records** | ❌ | ❌ | ✅✅✅ |
| 9. Avoid CRM | ✅ | ✅ | ✅ |
| 10. Testing Ease | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 11. Developer Explanation | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |

**Winning Criteria for Phase 1B+:** Criteria 7 & 8 (future match domain support) are CRITICAL

**Option C is the clear winner because:**
- Supports v1 requirements equally well as B
- Provides a clear path to Phase 2+ match domain WITHOUT requiring a master-person design
- Polymorphic subject references are elegant and extensible
- No schema redesign needed when adding existing records later

---

## Recommended Schema: Option C

### Phase 1B Tables (7 total)

1. **imports** — batch metadata (unchanged)
2. **raw_import_rows** — immutable CSV data (unchanged)
3. **import_contacts** — immutable denormalized snapshot (unchanged)
4. **review_items** — polymorphic review suggestions
5. **review_item_subjects** — (NEW) polymorphic subject references
6. **review_decisions** — decisions on review items (unchanged)
7. **audit_log** — immutable action log (unchanged)

### Key Design Decisions

**review_items is polymorphic but not "free-form":**
- item_type is constrained to ('validation', 'normalization', 'duplicate', 'household')
- payload_json structure varies by item_type but is well-defined

**review_item_subjects enables flexible entity reference:**
- subject_type allows current raw rows AND future external entities
- v1: subject_type='import_raw_row' only
- v2+: subject_type can be 'existing_contact', 'prior_import_row', etc.
- No global person table required; subjects reference specific entity types

**Decisions remain decoupled:**
- review_decisions reference review_items, not subjects
- One item may have multiple subjects; one decision applies to the item as a whole

---

## How Option C Satisfies v1 PRD

✅ Raw rows immutable: raw_import_rows append-only  
✅ Human review: review_items created, decisions made by reviewer  
✅ No automatic approval: code creates items, reviewer decides  
✅ No automatic resolution: decisions are explicit  
✅ Import-scoped (v1): batch_id FKs + subject_type='import_raw_row'  
✅ No writeback: no Givebutter/CRM API calls  
✅ UI preserved: Phase 0 screens unchanged (data model internal)  
✅ Export staging: computed from decisions at query time  
✅ Simple Flask/Jinja: no complex relationships, simple queries  

---

## How Option C Supports Future Larger Match Domain (Phase 2+)

**Without requiring a global master-person or CRM design in Phase 1B:**

### New Capabilities Enabled
```
Phase 2 scenario: "This current import row might match an existing contact from a prior import"

review_items:
  item_type='duplicate'
  payload_json={'evidence': ['email_matches'], 'conflicts': ['phone_differs']}

review_item_subjects (2 rows):
  [0] subject_type='import_raw_row', subject_id=3, role='primary' (from current import)
  [1] subject_type='prior_import_contact', subject_id=456, role='existing_match' (from prior)
```

### Optional Phase 2 Additions
- `prior_import_batches` table for historical data
- `existing_contacts` table for external records (optional, not required in Phase 1B)
- `existing_households` table (optional, not required in Phase 1B)
- New subject_type values in review_item_subjects

**No schema redesign needed. Just add optional tables and new subject_type values.**

---

## What is Intentionally Deferred

❌ **Global master-person database** — Not created in Phase 1B. Optional existing_contacts table added later if needed.  
❌ **Canonical household identity** — Not persisted in Phase 1B. Household groupings are per-import decisions only.  
❌ **Cross-import identity matching** — Logic deferred to Phase 2. Schema ready but not implemented.  
❌ **Export history tracking** — Deferred. export_runs_metadata optional in Phase 2.  
❌ **Complex decision workflows** — Simplified model: pending → reviewed → (optional) deferred.  
❌ **Validation issues table** — Handled as item_type='validation' within review_items (no separate validation table needed).  

---

## Recommendation on Current Step 4 Implementation

### Current State
- Option A (typed tables: normalization_suggestions, duplicate_candidates, household_suggestions)
- Blocks future match domain support without refactoring

### Required Changes Before Step 4 Acceptance

✅ **Replace 3 typed tables with 1 polymorphic table:**
- DELETE: separate normalization_suggestions, duplicate_candidates, household_suggestions tables
- CREATE: review_items (polymorphic) + review_item_subjects (subject references)

✅ **Update migration:**
- Simplify from 8 tables → 7 tables
- Add review_item_subjects junction table

✅ **Update models (database_models.py):**
- Delete: NormalizationSuggestion, DuplicateCandidateRecord, HouseholdSuggestion classes
- Create: ReviewItem, ReviewItemSubject classes
- Keep: ImportBatch, RawImportRow, ImportContact, ReviewDecision, AuditLogRecord

✅ **Update tests:**
- Replace 3 separate test classes with 1 ReviewItem test class
- Test polymorphic payload_json structure
- Test subject_type values

### Effort to Adjust
**~4-6 hours:**
- Delete 3 model classes
- Add 2 new model classes
- Update migration (not a refactor, just simplification)
- Update tests (consolidation)

### Risk if Not Adjusted
- **Critical:** Step 4 acceptance with Option A locks in typed-table design
- **Blocks Phase 2:** Would require full schema redesign to add cross-import matching
- **Wasted effort:** Currently implementing separate tables that will be consolidated later

---

## Decision: Is Current Typed-Table Design Acceptable?

**NO. Current Step 4 implementation should be adjusted to Option C before acceptance.**

### Why
1. **Future blocking:** Typed tables cannot accommodate existing-record matching without major refactoring
2. **Subject-reference design is elegant:** Polymorphic references solve the problem without overbuilding
3. **Effort is modest:** ~4-6 hours to adjust before Step 5 (repository implementation)
4. **Better long-term:** Option C costs slightly more in Phase 1B setup but saves significant refactoring in Phase 2

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| **Polymorphic JSON payload is flexible but less type-safe than Option A** | Document payload_json schema per item_type. Use schema validation in code. |
| **Subject references add slight query complexity vs Option B** | Simple INNER JOIN. Document common query patterns. |
| **Future existing_contacts table design unclear** | Defer design to Phase 2. Phase 1B subject_type values are for current import only. |
| **Developer confusion about polymorphism** | Clear documentation. Example queries for each item_type and subject_type. |

---

## Conclusion

**Option C (Extensible Review-Items with Subject References) is the recommended schema for Phase 1B.**

It is the only option that:
1. ✅ Satisfies all v1 PRD requirements
2. ✅ Supports all 8 current screens
3. ✅ Provides a clear path to Phase 2+ match domain
4. ✅ Avoids premature global master-person design
5. ✅ Enables future comparison of current imports against existing records
6. ✅ Requires minimal schema changes when adding external entity types

**Current Step 4 implementation (Option A) should be simplified to Option C before acceptance.**

---

**Review Status:** Ready for decision on schema direction and Step 4 adjustment

