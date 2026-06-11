# DonorTrust v1 — Screen Design Status Index

**Last Updated:** 2026-06-11 (Export Console accepted)  
**Project:** DonorTrust / Householder v1 UX Workflow  
**Approach:** Local implementation-reference mocks (specification-first)  
**Architecture:** No Stitch SDK usage; all screens have authoritative specs + local HTML references

---

## Acceptance Status Overview

| Screen | Status | Spec | Reference | Verification | Ready for Implementation |
|--------|--------|------|-----------|--------------|--------------------------|
| **Audit Log** | ✅ v1 Accepted | audit_log-spec.md | design-reference.html | 49/49 PASS | ✅ Yes |
| **Export Console** | ✅ v1 Accepted | export_console-spec.md | design-reference.html | 52/52 PASS | ✅ Yes |
| **Import Dashboard** | ⏳ Stitch Final / Pending Cleanup | (Stitch design) | Import Dashboard/ | (visual approved) | ⏳ Pending vocab cleanup |
| All Records / Validation Review | (See directory) | (in progress) | (in progress) | (pending) | (pending) |
| Households Review | (See directory) | (in progress) | (in progress) | (pending) | (pending) |
| Normalization Review | (See directory) | (in progress) | (in progress) | (pending) | (pending) |

---

## ✅ AUDIT LOG — v1 DESIGN REFERENCE ACCEPTED

### Screen Metadata
- **Screen Name:** Audit Log
- **Route:** `/imports/<import_id>/audit`
- **Purpose:** Comprehensive activity tracking for current import batch with audit-safe human-in-the-loop action history
- **Version:** v1 Final (Strict v1 Vocabulary Compliance)
- **Status:** Design Reference Accepted / Ready for Implementation

### Authority & References
- **Source of Truth:** `audit_log-spec.md` (12 sections, 11 acceptance criteria)
- **Implementation Reference:** `design-reference.html` (DonorTrust v1 local mock)
- **Verification:** `verification.json` (49/49 checks passing)
- **Documentation:** `README.md`, `REFERENCE_MOCK_NOTES.md`, `REFINEMENT_PLAN.md`

### Verification Result
```
Total Checks: 49
Passed: 49
Failed: 0
Pass Rate: 100%
Compliance Mode: Strict v1 vocabulary (zero tolerance for unsafe language)
Forbidden Terms Found: 0
Required Safe Terms Present: 12/12
Status: ✅ STRICT V1 COMPLIANCE VERIFIED
```

### Accepted Vocabulary
| Element | Canonical Name | Status |
|---------|---|--------|
| Column header | Audit Status | ✅ Enforced |
| Status: Data conflict | Conflict Flagged | ✅ Enforced |
| Status: Requires review | Needs Review | ✅ Enforced |
| Status: Valid | Validation Passed | ✅ Enforced |
| Status: System recorded | System Logged | ✅ Enforced |
| Right sidebar | Row Audit History | ✅ Enforced |
| Export button | Full Import Audit Report or Export PDF | ✅ Enforced |

### Safety Guarantees
- ✅ Raw import rows are **never mutated**
- ✅ Audit log records **decisions only**, not mutations
- ✅ Every reviewer action is **logged with timestamp, actor, decision, and target**
- ✅ All references are **import-scoped** (row ID, not master ID)
- ✅ Language is **transparent** (marked as Same Person, not merged)
- ✅ Decisions are **human-in-the-loop verified**
- ✅ Full audit trail is **searchable and exportable for compliance**

### Design Structure
- **Navigation:** DonorTrust v1 top bar with Audit tab active
- **Left Sidebar:** Data Controls with 5 filters (Action Type, Reviewer, Date Range, Target Search, Audit Status)
- **Main Content:** Audit log table (6 columns), pagination, safety messaging
- **Right Sidebar:** Row Audit History (optional)
- **System Health:** Indicators (Integrity Score, Review Velocity, Pending Conflicts, Anomalies)
- **Styling:** DonorTrust v1 (white/light gray, subtle borders, color-coded badges, WCAG AA accessibility)

### Table Columns
1. Date/Timestamp (ISO format with timezone)
2. Reviewer & Action (name/avatar + import-scoped verb phrase)
3. Target (import row ID, e.g., #P-99281-X)
4. Notes (reviewer comment or system message)
5. Audit Status (color-coded badge)
6. Action (link to view record detail)

### Implementation Notes
- This is a **local implementation-reference mock**, not a Stitch update
- The spec is the **authority for all design decisions**
- The HTML is a **visual/structural reference only** (do not ship directly)
- Implementation should be built in the app's **production component/CSS system**
- All routing, state management, and backend integration required per app architecture

### Acceptance Sign-Off
```
Screen: Audit Log
Date Accepted: 2026-06-11
Verified By: Specification + Local Reference Mock (49/49 checks)
Authority: audit_log-spec.md
Status: v1 Design Reference Accepted / Ready for Implementation
Next: Implementation in app code per spec requirements
```

---

## ✅ EXPORT CONSOLE — v1 DESIGN REFERENCE ACCEPTED

### Screen Metadata
- **Screen Name:** Export Console
- **Route:** `/imports/<import_id>/exports`
- **Purpose:** Safe, reviewer-controlled export preparation and download with audit logging and no external system integration
- **Version:** v1 Final (Strict v1 Export-Safe Vocabulary Compliance)
- **Status:** Design Reference Accepted / Ready for Implementation

### Authority & References
- **Source of Truth:** `export_console-spec.md` (14 sections, 11 acceptance criteria)
- **Implementation Reference:** `design-reference.html` (DonorTrust v1 local mock)
- **Verification:** `verification.json` (52/52 checks passing)
- **Documentation:** `README.md`, `REFERENCE_MOCK_NOTES.md`, `REFINEMENT_PLAN.md`

### Verification Result
```
Total Checks: 52
Passed: 52
Failed: 0
Pass Rate: 100%
Compliance Mode: Strict v1 export-safe vocabulary (zero tolerance for unsafe language)
Forbidden Terms Found: 0
Required Safe Terms Present: 12/12
Status: ✅ STRICT V1 EXPORT-SAFE COMPLIANCE VERIFIED
```

### Canonical Export Cards
| Export Type | Status | Purpose |
|-------------|--------|---------|
| Reviewed Export | Generated | CSV with reviewer-confirmed duplicates and household links |
| Household Export | Generated | Confirmed household groupings with member composition |
| Backlog Export | Pending Review | Unresolved suggestions or pending reviewer decisions |
| Raw Export | Ready | Original data unchanged, no reviewer modifications |

### Canonical Action Labels
- ✅ **Download Reviewed CSV**
- ✅ **Download Household CSV**
- ✅ **Download Backlog CSV**
- ✅ **Download Raw CSV**
- ✅ **Generate Export Package** (button label, with confirmation modal)

### Safety Guarantees
- ✅ Exports prepare **files for download only**
- ✅ Raw import rows are **never changed** by exports
- ✅ No automatic sync to **external systems** (Givebutter, CRM, vault)
- ✅ Every export action is **logged to audit trail** (timestamp, actor, type, filename, metadata)
- ✅ All references are **import-scoped** (current batch only, not external)
- ✅ Reviewer has **explicit control** (no auto-export, confirmation modal required)
- ✅ Full **transparency** (caution messaging on pending/original data)

### Design Structure
- **Navigation:** DonorTrust v1 top bar with Exports tab active
- **Safety Banner:** "Review decisions logged | Raw import rows unchanged | Exports ready to download"
- **Left Sidebar:** Data Controls with 5 filters (Batch Status, Review Completion, Export Type, Date Range, Source File)
- **Main Content:** 4 export cards with headers, descriptions, metadata, caution copy (where applicable), footers, download buttons
- **Right Sidebar:** Export History (optional)
- **Sticky Action Bar:** "Generate Export Package" button with status display and secondary actions
- **Confirmation Modal:** Non-dismissible, lists 4 export types, includes export-safe messaging
- **Footer:** 4-item safety guarantee statement
- **Styling:** DonorTrust v1 (white/light gray, subtle borders, color-coded badges, WCAG AA accessibility)

### Caution Copy (Required)
- ✅ **Backlog Export:** "For internal review only. Contains unresolved suggestions or pending reviewer decisions."
- ✅ **Raw Export:** "Original uploaded CSV exactly as received. No reviewer decisions or staged changes included."

### Implementation Notes
- This is a **local implementation-reference mock**, not a Stitch update
- The spec is the **authority for all design decisions**
- The HTML is a **visual/structural reference only** (do not ship directly)
- Implementation should be built in the app's **production component/CSS system**
- All routing, state management, and backend integration required per app architecture

### Acceptance Sign-Off
```
Screen: Export Console
Date Accepted: 2026-06-11
Verified By: Specification + Local Reference Mock (52/52 checks)
Authority: export_console-spec.md
Status: v1 Design Reference Accepted / Ready for Implementation
Core Guarantee: Exports prepare downloadable files only. Raw rows unchanged. No data written back to Givebutter or any CRM.
Next: Implementation in app code per spec requirements
```

---

## ⏳ IMPORT DASHBOARD — STITCH FINAL / PENDING LOCAL REFERENCE CLEANUP

### Screen Metadata
- **Screen Name:** Import Dashboard
- **Route:** `/imports/<import_id>/dashboard`
- **Purpose:** Status dashboard showing batch progress, review queue, and navigation to all review screens
- **Version:** v1 Final (Stitch iteration-004)
- **Status:** Stitch Design Final / Pending Local Reference Cleanup

### Folder Organization
- **Canonical Quick-Access Reference:** `Import Dashboard/`
  - Final artifacts (design.html, screenshots, FINAL_STATUS.md, README.md)
  - Use for fast visual review
  - 52KB screenshot, 16KB HTML export
  
- **Historical Design Archive:** `import-dashboard/`
  - Full iteration history (001, 002, 003, 004)
  - Preserve for audit trail
  - `iteration-004/` mirrors `Import Dashboard/`

### Authority Reference
- **Final Stitch Screen ID:** `76ae1ecb02ec4c559bea438ad0012d0f`
- **Final Iteration Folder:** `import-dashboard/iteration-004/`
- **Quick-Access Folder:** `Import Dashboard/`
- **Design Method:** Stitch SDK `screen.edit()` with GEMINI_3_FLASH

### Design Status
```
Design Changes Applied: 13/13 ✅
  - 8 major improvements (hierarchy, validation, queue cards, audit trail, guardrails, export button, visual polish)
  - 5 polish refinements (button text, note visibility, language format, safety badge)

Design Constraints Maintained:
  ✅ Read-only dashboard (navigation only)
  ✅ Human-in-the-loop reinforced
  ✅ Audit-safe design
  ✅ Safe navigation language (Review, Open, View)
  ✅ No data mutations
  ✅ DonorTrust v1 consistent

Status: Stitch Design Final ✅
```

### Pending Local Reference Cleanup
**Why Not Yet Accepted as v1 Design Reference:**
- Stitch HTML contains vocabulary that needs import-scoped/export-staging refinement
- Terms requiring cleanup:
  - "Bulk Approval" → safer language
  - "Approved Normalization" → safer language
  - "cleaned files" → "reviewed data" or "files with decisions reflected"
  - "householded files" → safer import-scoped language

**Next Steps:**
1. Create local implementation-reference mock/spec
2. Vocabulary cleanup and verification
3. Once complete → v1 Design Reference Accepted

### Implementation Notes
- ✅ This is a **Stitch-generated design** (not a local reference mock)
- ⏳ **Do not ship raw HTML directly** — wait for local spec cleanup
- **Visual/structural reference** for implementation use
- Stitch HTML serves as visual baseline, not implementation authority
- Local implementation-reference mock will become authority when created

### Key Principle
**Current State:** Visual design approved and complete  
**Pending:** Local vocabulary cleanup and specification creation  
**Goal:** v1 Design Reference Accepted with safe import-scoped language

---

## Screens in Progress

See respective folders in current directory (`/docs/PRDs/Householder/UX Specs/`):
- `all-records-validation-review/` — In progress
- `households-review/` — In progress
- `normalization-review/` — In progress

**Note:** Earlier versions were in `/testing/workspace/ChatGPT/stitch-review/` (archived). Current canonical location is `/docs/PRDs/Householder/UX Specs/`.

(Status updates pending completion of those screens)

---

**Created:** 2026-06-11  
**Scope:** DonorTrust v1 UX Design Status  
**Authority:** audit_log-spec.md + verification.json  
**Next Update:** When next screen reaches v1 acceptance
