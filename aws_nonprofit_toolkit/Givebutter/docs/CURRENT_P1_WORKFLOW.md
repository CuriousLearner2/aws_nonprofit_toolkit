# Householder v1 — Current P1 Workflow

**Current Phase:** Phase 1B Implementation Complete
**Status:** Production Ready
**Last Updated:** 2026-08-28

---

## The Problem Householder Solves

Nonprofit organizations receive donor records from platforms like Givebutter that contain:
- **Duplicate donors** — Same person donated twice with slightly different names (John Smith vs Jon Smith)
- **Data inconsistencies** — Email typos (gmai.com → gmail.com), phone format variations, missing fields
- **Ungrouped households** — Family members recorded as separate individuals instead of one household

These errors prevent accurate donor communication, accounting reconciliation, and analytics.

**Householder's role:** Identify duplicates, validate and normalize data, and group donors into households **before they're imported into your CRM**. Human reviewers approve or override each decision before export.

---

## P1 Scope (Phase 1B Complete)

### ✅ What P1 Includes

**8-Screen Workflow:**
1. **Imports List** — Discover and navigate batches
2. **Dashboard** — View queue summaries (issues by type)
3. **Validation** — Review and fix data issues (email, phone, amount, date)
4. **Duplicates** — Identify and resolve duplicate records
5. **Households** — Group related donors
6. **Normalizations** — Review auto-corrections to data
7. **Readiness** — Verify batch is ready for export
8. **Exports** — Generate and download output files

**Core Capabilities:**
- Upload CSV batch
- View all import records with validation status
- Review system-suggested issues and fixes
- Inline autosave corrections
- Record human disposition (approve/reject/follow-up)
- Automatic audit trail
- Generate export files
- Download clean CSV outputs

### ❌ Out of Scope (Phase 2+)

- Batch approval workflows (manager sign-off)
- Advanced override logic (beyond disposition)
- Historical comparisons/rollback
- Bulk operations
- Custom validation rules UI
- API-only access (UI-driven only in P1)

---

## End-to-End Workflow

### Phase 0: Upload

**Input:** CSV file from Givebutter (or similar donation platform)

**What Happens:**
1. System validates each row (email format, phone format, amount presence, date format)
2. System identifies potential duplicates based on name similarity
3. System checks for household grouping candidates
4. System generates review items for each issue

**Output:** Import batch with validation results (PASS/WARNING/FAIL per row)

### Phase 1: Review Validation Issues

**Screen:** Validation Review (`/imports/<id>/validation`)

**What You See:**
- Each record with validation issues flagged
- System-suggested fixes (e.g., "typo: gmai.com → gmail.com?")
- Current raw value and suggested correction

**Your Decision:** For each issue, choose:
- **Accept correction** — Save the fix
- **Reject fix** — Keep raw value
- **Manual correction** — Edit it yourself and save

**System Response:**
- Invalid corrections are rejected with error
- Valid corrections are auto-saved
- System recalculates row status based on your edits

### Phase 2: Review Duplicates

**Screen:** Duplicates Review (`/imports/<id>/duplicates`)

**What You See:**
- Potential duplicate pairs with similarity score
- Both donor records side-by-side

**Your Decision:** For each potential duplicate:
- **Same Person** — Merge records
- **Different People** — Keep separate
- **Follow-up** — Review later

### Phase 3: Review Households

**Screen:** Households Review (`/imports/<id>/households`)

**What You See:**
- Potential household groupings (family members, shared addresses)
- All members in each group

**Your Decision:** For each group:
- **Confirm Household** — Group them
- **Reject Grouping** — Keep separate
- **Follow-up** — Review later

### Phase 4: Review Normalizations

**Screen:** Normalizations Review (`/imports/<id>/normalizations`)

**What You See:**
- Auto-corrections applied (e.g., phone formatted, date standardized)

**Your Decision:** For each normalization:
- **Accept normalization** — Use corrected value
- **Reject normalization** — Use raw value
- **Follow-up** — Review later

### Phase 5: Verify Readiness

**Screen:** Readiness Check (`/imports/<id>/readiness`)

**What Householder Checks:**
- All critical validation issues resolved or approved
- All duplicate decisions made
- All household decisions made
- No unresolved blockers

**Your Decision:**
- **Approve for Export** — Batch is ready
- **Not Ready** — Review items need attention

### Phase 6: Generate & Download Export

**Screen:** Export Console (`/imports/<id>/exports`)

**What Happens:**
1. Householder validates batch readiness
2. Applies all your dispositions and corrections
3. Generates three output CSV files:
   - `cleaned.csv` — Corrected data ready for CRM
   - `duplicates.csv` — Merged duplicate records (for your records)
   - `households.csv` — Grouped household records

**Output:** Three downloadable CSV files

---

## Key Concepts

### Raw Source Data vs. Reviewed/Effective Values

| Concept | Definition | Mutable | Example |
|---------|-----------|---------|---------|
| **Raw Value** | Original data from CSV upload | No (immutable history) | `gmai.com` |
| **Effective Value** | Current value after corrections/dispositions | Yes (via autosave/decisions) | `gmail.com` |
| **Correction** | Autosave inline edit by reviewer | Yes | User manually typed `gmail.com` |
| **System Suggestion** | AI-generated fix proposal | No (display only) | "Did you mean gmail.com?" |

**Invariant:** Raw source data is never modified. All changes are tracked via autosave corrections or disposition decisions.

---

### System-Derived Row Status vs. Human Disposition

| Aspect | System-Derived Status | Human Disposition |
|--------|----------------------|-------------------|
| **What It Is** | Calculated validation tier (PASS/WARNING/FAIL) | Reviewer's decision about how to handle the record |
| **Who Sets It** | System (based on validation rules) | Reviewer (human choice) |
| **Mutable** | Yes (recalculates when corrections apply) | Yes (append-only history) |
| **Examples** | "PASS" (no issues), "WARNING" (issues but fixable), "FAIL" (critical blocker) | "Approve", "Needs Follow-up", "Reject Row" |
| **Impact on Export** | Determines if row can be exported | Determines if row IS exported |

**Row can be exported if:**
- System status is not FAIL (or FAIL is approved), AND
- Human disposition is "Approve" or equivalent, AND
- No unresolved legacy defer decisions exist

---

### Blockers vs. Warnings

| Type | Definition | Can Be Exported | Example |
|------|-----------|-----------------|---------|
| **Blocker** | Critical issue that prevents export unless explicitly approved | Only with approval | Missing email (no contact possible) |
| **Warning** | Issue that needs review but doesn't prevent export | Yes, after review | Unusual phone format |

**Distinction in Practice:**
- A missing email is a **blocker** — the record cannot be used
- An unusual phone format is a **warning** — it might be valid, but needs review

---

### Reviewer Identity & Notes Requirements

**When Required:**
- Recording a disposition (approve/reject/follow-up) on ANY issue requires:
  - **Reviewer name/email** — Who made this decision
  - **Notes/reason** (optional but recommended) — Why they made this choice

**When NOT Required:**
- Autosaving inline corrections (just edit and save)
- Accepting system suggestions (auto-approved)

**Stored:** In audit log (immutable history of all decisions)

---

### Legacy Defer Behavior

**Key Invariant:** Legacy defer decisions are UNRESOLVED and BLOCKING until superseded by a valid current decision.

**What Happens if a Row Has a Legacy Defer Decision:**

1. **Legacy defer persists** — The old decision remains in the audit trail (immutable history)
2. **Row is blocked** — Cannot be exported, even with approval/confirmation flags
3. **Must be superseded** — Reviewer must make a NEW decision (approve/reject/follow-up) that overrides the defer
4. **Approval/confirmation cannot bypass** — There is no "confirm and override legacy defer" flag
5. **Override mechanism** — Reviewer must explicitly record a new disposition via the normal review workflow

**Example:**
```
Legacy state: Row has "defer" decision from old system
Current reviewer sees: This row is blocked (legacy defer)
Reviewer's options:
  - Review the issues and make a new decision (approve/reject/follow-up)
  - Cannot use a confirmation flag to bypass the defer
Result: New decision is recorded, audit trail shows both old defer and new decision
```

**Why This Design:** Legacy defer decisions are acknowledged as unresolved. Forcing explicit override ensures human review, not silent approval-by-flag.

---

### Readiness & Export Semantics

**Readiness Check Verifies:**
1. All rows with FAIL status have been approved OR rejected
2. All duplicate decisions are made (same_person / different_people)
3. All household decisions are made (confirm / reject grouping)
4. All validation decisions are made (approve correction / reject fix / manual edit)
5. No legacy defer decisions remain unresolved
6. No critical blockers remain

**Export Process:**
1. Apply all approved corrections and dispositions
2. Generate output files with effective (reviewed) values
3. Create audit record of export (timestamp, reviewer, summary)
4. Files are ready for CRM import

**Post-Export:**
- Original raw data remains unchanged
- Audit trail captures all review history
- Output files are downloaded and archived by user

---

### Append-Only Audit & Reversal Semantics

**Audit Trail Principles:**
- Every decision (validation, duplicate, household, normalization) creates an immutable audit entry
- Entries are never deleted or modified
- History shows full timeline of changes

**Reversal Model:**
- No "undo" button (decisions are final)
- Correction: Reviewer records a NEW decision that supersedes the old one
- Old decision remains in audit for history
- New decision is appended to trail
- Export uses the LATEST decision for each item

**Example Timeline:**
```
1. Initial state: Row has email validation issue
2. Reviewer makes decision: "Reject fix, keep raw value"
   → Audit: [email_decision: reject_fix, timestamp: 10:00am]
3. Later, reviewer changes mind and edits the value
   → Autosave creates new correction: [email_autosave: user_edited, value: new@email.com, timestamp: 10:15am]
4. Reviewer records new validation decision: "Approve edited value"
   → Audit: [email_decision: approve_edited, timestamp: 10:16am]
5. Export uses LATEST: new@email.com (from step 3 autosave)
6. Audit trail shows all 3 entries (reject → autosave → approve)
```

---

## Current P1 Boundaries

### What Reviewers CAN Do
- Upload CSV batch
- View all records and issues
- Edit field values inline (autosave)
- Record disposition for each issue
- Determine readiness
- Generate/download export
- Review audit trail

### What Reviewers CANNOT Do (P2+)
- Bulk approve all issues at once
- Create custom validation rules
- Rollback a batch to pre-review state
- Skip review of specific item types
- Approve batch on behalf of others (no delegation)
- Access via API (UI-only in P1)

---

## Data Flow Summary

```
CSV Upload
    ↓
[Validation] → Issues detected → Review Screen
    ↓
[Autosave] → Corrections applied → Row status recalculated
    ↓
[Disposition] → Reviewer decision → Audit entry
    ↓
[Readiness] → All items resolved? → Export allowed?
    ↓
[Export] → Apply all corrections/dispositions → Output CSV
    ↓
Download Files
```

---

**This document defines P1 scope and workflow semantics. For implementation details, see CODE_MAP.md. For operator instructions, see HOUSEHOLDER_OPERATOR_GUIDE.md.**
