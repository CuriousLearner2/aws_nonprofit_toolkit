# Phase 1B PRD v3 → Option C Alignment Addendum

**Date:** 2026-06-12  
**Status:** ALIGNMENT DOCUMENTATION (No Code Changes)  
**Purpose:** Clarify how PRD v3's typed-table terminology maps to Phase 1B's accepted Option C polymorphic schema before Phase 1B-Step 5 repository implementation begins.

---

## 1. Purpose

This document aligns `Householder-PRD-v3.md` with the current accepted Phase 1B Option C schema direction. PRD v3 uses typed-table language (`contact_suggestions`, `household_suggestions`, `duplicate_candidates`) to describe v1 functionality and future v2 capabilities. The accepted Phase 1B-Step 4 implementation uses Option C: a single polymorphic `review_items` table with a `subject_type` discriminator field, enabling flexible entity references without building a global master-person or master-household registry.

This addendum ensures that:
- Future implementation does not oscillate between PRD v3's typed-table language and Option C's schema
- Repository implementations (Phase 1B-Step 5+) use Option C schema as the source of truth
- PRD v3 product requirements are fully supported by Option C
- Phase 1B guardrails remain enforceable

---

## 2. Source Documents

This addendum references and aligns:

1. **`docs/PRDs/Householder/Householder-PRD-v3.md`** — Product requirements, non-negotiables, v1 screens, v2 deferral items
2. **`docs/implementation/phase1b/PHASE1B_SCHEMA_SIMPLIFICATION_REVIEW.md`** — Design analysis comparing typed tables (Option A/B) vs. polymorphic (Option C)
3. **`docs/implementation/phase1b/PHASE1B_STEP4A_DATABASE_TOOLING_DECISION_RECORD.md`** — Decision rationale for Option C
4. **`docs/implementation/PHASE1B_STEP4_SCHEMA_MODELS_MIGRATIONS_COMPLETION_RECORD.md`** — Acceptance record for Option C implementation

---

## 3. Key PRD v3 Requirements to Preserve

**Phase 1B (v1) Guardrails:**

✅ Raw imported data (`raw_import_rows`) is immutable (append-only)  
✅ Baseline contact snapshots (`import_contacts`) are immutable after extraction  
✅ No automatic cleaning, merging, or household assignment  
✅ All suggestions require explicit human review and approval  
✅ Duplicate decisions in v1 are record-only (no contact merging)  
✅ No automatic application of prior decisions  
✅ No Givebutter/API writeback in v1  
✅ Current import batch only (no cross-import matching in v1)  
✅ All suggestion approvals require confirmation dialogs  

**Phase 1B Screens (8 total):**

1. Upload Givebutter CSV
2. Import Dashboard
3. Possible Duplicates
4. All Records / Validation Review
5. Normalization Review
6. Households Review
7. Audit Log
8. Export Console

**Future v2 Deferral (not Phase 1B scope):**

- Cross-import duplicate detection
- Linking new import contact to existing approved household
- Maintaining global household/contact registries
- Using prior reviewer decisions as evidence for future suggestions
- Givebutter/CRM integration
- Automatic application of suggestions

---

## 4. Option C Mapping: PRD v3 Concepts → Phase 1B Schema

| PRD v3 Concept | Option C Implementation | Notes |
|---|---|---|
| `contact_suggestions` (field-level normalization) | `review_items(item_type='normalization')` + `review_item_subjects` | Payload contains field name, raw value, suggested normalized value, basis |
| `duplicate_candidates` (same-person pairs) | `review_items(item_type='duplicate')` + 2+ `review_item_subjects` | Subjects have role='primary' and role='potential_match' (or similar); payload contains evidence |
| `household_suggestions` (grouping proposals) | `review_items(item_type='household')` + multiple `review_item_subjects` | Subjects are members; payload contains suggested label, basis, confidence |
| Validation issues/findings | `review_items(item_type='validation')` or computed findings (not stored) | Phase 1B decision: validation findings may be computed on-demand rather than pre-stored |
| Suggestion approval | `review_decisions(decision='accept'\|'reject'\|'defer'...)` | Each decision is append-only; applied to a `review_item` as a whole |
| Audit trail | `audit_log` (immutable, append-only) | Records all significant actions: item_created, decision_recorded, batch_imported |
| Raw import rows | `raw_import_rows` (immutable, append-only) | Source of truth; never mutated or deleted |
| Baseline contact snapshot | `import_contacts` (immutable after extraction) | Extracted field values; only approved household assignment is applied for export |
| Future: existing contact match | Future subject type: `subject_type='existing_contact'` (Phase 2+) | Enables matching current import row against existing database records |
| Future: existing household link | Future subject type: `subject_type='existing_household'` (Phase 2+) | Enables linking current import contact to pre-approved household |
| Future: prior import row match | Future subject type: `subject_type='prior_import_row'` or `'prior_import_contact'` (Phase 2+) | Enables cross-import duplicate detection and household grouping |

**Phase 1B Subject Types (v1):**
- `'import_raw_row'` — references `raw_import_rows.id`
- `'import_contact_snapshot'` — references `import_contacts.id`

**Future Subject Types (v2+, not implemented yet):**
- `'prior_import_row'` — references archived raw_import_rows from previous imports
- `'prior_import_contact'` — references archived import_contacts
- `'existing_contact'` — references future `existing_contacts` table (when added)
- `'existing_household'` — references future `existing_households` table (when added)

---

## 5. Why Option C Satisfies All v1 Screens

Option C supports all 8 canonical v1 screens without requiring typed suggestion tables:

| Screen | How Option C Supports It |
|--------|--------------------------|
| Upload | No schema dependency; Phase 1A CSV upload logic unchanged |
| Dashboard | Aggregates `review_items(item_type='*')` by status; computes queue counts |
| Duplicates | Filters `review_items(item_type='duplicate')` with `review_item_subjects` showing both records; displays decisions from `review_decisions` |
| Validation | Computes validation findings on-demand OR stores as `review_items(item_type='validation')` with payload |
| Normalizations | Filters `review_items(item_type='normalization')`; displays payload; stores approval in `review_decisions` |
| Households | Filters `review_items(item_type='household')` with multiple `review_item_subjects` (members); stores approval in `review_decisions` |
| Audit Log | Reads immutable `audit_log` entries; no schema limitations |
| Export Console | Reads approved `review_decisions` and generates export view; no mutations to raw data |

All 8 screens remain unchanged from Phase 1A UX. Repository implementations (Phase 1B-Step 5+) return view models in the same shape the templates expect.

---

## 6. Why Option C Supports Future v2 Requirements

Option C avoids premature global master registries while enabling future matching domains:

**Current Scope (v1):** Import-specific only
- Current import row vs. current import row (within same batch)

**Future Scope (v2+):** Broader match domains (no schema change needed)
- Current import row vs. **prior import contact** (cross-import dedup)
- Current import row vs. **existing contact** (match to approved global contact)
- Current import contact vs. **existing household** (link to approved household)

**No Architectural Lock-In:**
- Adding new subject types requires no schema migration
- No need to build global person/household tables in v1
- When v2 adds `existing_contacts` or `existing_households` tables, they can be referenced via new subject types
- All v2 features can re-use the same `review_items` → `review_item_subjects` structure

This approach:
✅ Keeps Phase 1B scope focused (current import only)  
✅ Avoids building unnecessary global registries  
✅ Allows v2 to add matching domains without schema redesign  
✅ Preserves human-in-the-loop for all future decisions  

---

## 7. Explicit Decision: Household Assignment Handling in Phase 1B

PRD v3 includes: "`contacts.household_id` is the ONLY mutable field on contacts in v1. It may be set only after operator explicitly approves a household suggestion."

**Phase 1B Decision:**

We choose **Option 2: Store household assignment in `review_decisions`, not in `import_contacts`.**

**Rationale:**

| Aspect | Option 1 (Mutate) | Option 2 (Immutable, Derived) |
|--------|-------------------|-------------------------------|
| `import_contacts` mutability | Mutable (`household_id` only) | Immutable (append-only) |
| Where assignment stored | Raw baseline field | `review_decisions` + computed for export |
| Audit trail | Mutation timestamp in `import_contacts.updated_at` | Full decision chain in `audit_log` |
| Rollback capability | Requires UPDATE reversal | Revert via new decision record |
| Immutability guarantee | Weakened (one exception) | Consistent (no exceptions) |
| Export computation | Direct field read | Derived from decision + subjects |

**Phase 1B Implementation:**

✅ Keep `import_contacts` fully immutable  
✅ Store household approval in `review_decisions(decision='confirm_household', ...)`  
✅ Compute `household_id` for export as a derived field from approved decisions  
✅ Do not add `household_id` column to `import_contacts`  

**Future v2:**

If product requirements later require persistent household assignment on baseline records (e.g., for report querying), add an export-facing `household_id` field to a derived view or export-staging table. Do not mutate `import_contacts` without explicit re-approval of Phase 1B scope.

---

## 8. Naming Guidance

**Schema Names:**

Implementation should use Option C generic schema names (`review_items`, `review_item_subjects`, etc.). Do not recreate separate `contact_suggestions`, `household_suggestions`, or `duplicate_candidates` tables unless explicitly approved in a future scope change.

**View Model Names (Repository Return Types):**

Repository methods may return view models with PR D-aligned names for clarity:
- `get_duplicates()` may return `[DuplicatePageViewModel]` even if data comes from `review_items(item_type='duplicate')`
- `get_normalizations()` may return `[NormalizationPageViewModel]` even if data comes from `review_items(item_type='normalization')`
- `get_households()` may return `[HouseholdPageViewModel]` even if data comes from `review_items(item_type='household')`

This separation—generic schema names + domain-specific view models—keeps implementation clean and testable while maintaining semantic clarity for routes and templates.

**UI Labels:**

Visible UI copy remains as accepted in Phase 1A and PRD v3 vocabulary guidance:
- "Confirm suggestion" (not "Approve suggestion")
- "Confirm Selected" (not "Approve All")
- "Marked as Same Person" (not "Merged")
- "Audit Log" (not "Donor History")

---

## 9. Deferred Items (Not Phase 1B Scope)

The following PRD v3 features are explicitly deferred to Phase 2 or later:

**Data Model:**
- Global `contacts` registry (Phase 2+)
- Global `households` registry (Phase 2+)
- Durable cross-import identity graph
- `existing_contacts` table
- `existing_households` table

**Matching Domains:**
- Cross-import duplicate detection
- Linking current import to existing approved households
- Using prior reviewer decisions as evidence for current suggestions

**Integration & Automation:**
- Givebutter/CRM API writeback
- Automatic application of prior decisions to new suggestions
- Background matching jobs
- Real export file generation (Phase 1B exports are in-memory staging only)

**These are not Option C schema limitations.** When v2 adds these features, new subject types can be registered without schema migration. Implementation and v2 planning should assume Option C as the stable foundation.

---

## 10. Acceptance Criteria

This addendum is acceptable if it:

✅ Is documentation-only (no code changes)  
✅ Clearly maps each PRD v3 typed concept to Option C schema  
✅ Confirms all 8 v1 screens are supported by Option C  
✅ Confirms Option C supports future v2 larger match domain  
✅ Explicitly decides household assignment handling (Option 2: immutable baseline)  
✅ Provides clear naming guidance (schema names vs. view model names)  
✅ Lists deferred items explicitly  
✅ Does not start Phase 1B-Step 5 implementation  
✅ Does not modify code, tests, migrations, or models  

---

## Summary

**PRD v3** describes v1 and v2 using typed-table language: `contact_suggestions`, `household_suggestions`, `duplicate_candidates`, future `existing_contacts`/`existing_households`.

**Option C (Accepted Phase 1B Schema)** implements the same functionality using:
- Single polymorphic `review_items` table with `item_type` discriminator
- Polymorphic `review_item_subjects` for flexible entity references
- Append-only `review_decisions` for all approvals
- Immutable `audit_log` for all actions

**Alignment:**
- All PRD v3 v1 guardrails are enforced by Option C
- All 8 v1 screens are fully supported
- All v2 product capabilities can be added via new subject types (no migration required)
- Household assignment is stored in decisions, not baseline mutations (Option 2)
- Repository layer names view models for clarity; schema names remain generic

**Next Step:**
Phase 1B-Step 5 (DatabaseImportRepository implementation) should use this alignment as the single source of truth for mapping PRD requirements to Option C schema.

