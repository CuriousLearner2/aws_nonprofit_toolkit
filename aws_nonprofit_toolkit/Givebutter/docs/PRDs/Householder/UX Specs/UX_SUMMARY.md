# DonorTrust v1 — User Experience Summary

**Date:** 2026-06-11  
**Project:** Givebutter / Householder v1 UX Workflow  
**Design Approach:** Local implementation-reference mocks (specification-first)  
**Status:** Audit Log & Export Console accepted; remaining screens in progress

---

## Executive Overview

DonorTrust v1 is a **human-in-the-loop data review system** that allows nonprofit staff to safely import and validate donor contact data from CSV files. The system guides reviewers through a structured workflow to:

1. **Inspect** all imported records for validation issues
2. **Review** suggested matches, households, and normalizations
3. **Confirm** decisions with explicit human approval (no auto-apply)
4. **Audit** every action taken for compliance and transparency
5. **Export** clean, reviewed data files for downstream use

**Core Design Philosophy:** Raw import rows are **never mutated**. All reviewer decisions affect **export staging only**. Every action is **logged and auditable**. External systems (Givebutter, CRM) are **never updated directly**.

---

## Workflow Overview

The DonorTrust v1 experience follows this sequence:

```
[1. Upload Givebutter CSV] — Upload CSV file, enter batch metadata
    ↓
[2. Import Dashboard] — View batch status, queue of work, review progress
    ↓
[3–6. Review Queues] — Enter as needed:
    • [3. Possible Duplicates] — Side-by-side comparison: mark records as same person
    • [4. All Records / Validation Review] — Inspect records, identify validation issues
    • [5. Normalization Review] — Review field cleanup suggestions
    • [6. Households Review] — Confirm/defer household groupings
    ↓
[7. Audit Log] — Review all decisions made (available throughout)
    ↓
[8. Export Console] — Download prepared CSV files
```

Each screen:
- Operates on the **current import batch only** (import-scoped)
- Shows **system suggestions** (matches, households, cleanups) for human review
- Requires **explicit approval** (no automatic apply)
- **Logs all decisions** to the audit trail
- **Preserves raw import rows** unchanged

---

## Screen-by-Screen Breakdown

### 1. Upload Givebutter CSV ✅ **IMPLEMENTED**
**Route:** `/imports/upload` (or similar)  
**Status:** Finalized & Implemented  
**Purpose:** Safe, non-destructive entry point for uploading CSV files and viewing active import batches

**Key Features:**
- **CSV file upload** with validation
- **Active import batches table** showing status of all pending imports
- **9-column table**: Batch ID, Source File, Date Uploaded, Records, Status, Review Status, Assigned To, Last Updated, Action
- **Safety banner** (prominent): "Raw data is unchanged" reassurance message
- **v1 Safety Mode panel** (explicit checklist):
  - ✅ Immutable raw data
  - ✅ Current import only (no cross-import matching)
  - ✅ Human-in-the-loop (no automatic merges)
  - ✅ Staging & suggestions only
  - ✅ No Givebutter writeback
- **Status/Action separation**: Status column shows state; Action column shows primary interaction (e.g., "Review", "In Progress", "Complete")
- **Sticky action column** (always visible on right)

**User Actions:**
- Upload new CSV file
- View all active import batches
- Click "Review" to enter the batch workflow
- See progress of pending imports

**Safety Principles:**
- ✅ Immutable raw data preserved
- ✅ Current import batch only
- ✅ Human-in-the-loop verified
- ✅ All changes are suggestions, not mutations
- ✅ No Givebutter writeback

---

### 2. Import Dashboard ✅ **FINALIZED**
**Route:** `/imports/<import_id>/dashboard`  
**Status:** Design Final (Stitch iteration-004)  
**Purpose:** Status dashboard showing batch progress, review queue, and navigation to all review screens

**Key Features:**
- **Read-only dashboard** (navigation only, no direct actions)
- **Batch metadata**: Import ID, source file, upload date, record count, review progress
- **Queue status cards** showing work remaining:
  - Duplicates pending: # records
  - Validation issues: # records
  - Normalizations pending: # records
  - Households pending: # records
- **Progress indicators**: % complete for each category
- **Navigation cards/buttons** (action-focused):
  - "Review Possible Duplicates" → opens Possible Duplicates screen
  - "Review Validation Issues" → opens All Records / Validation Review
  - "Review Normalizations" → opens Normalization Review
  - "Review Households" → opens Households Review
  - "View Audit Log" → opens Audit Log
  - "Open Export Console" → opens Export Console
- **Audit trail section**: Recent decisions, reviewer actions log (read-only)
- **Safety messaging**: Human-in-loop, raw rows preserved, decisions logged

**User Actions:**
- View batch status at a glance
- Navigate to any review screen
- Monitor progress
- Review recent decisions (read-only)
- Access audit history
- Go to Export Console

**Safety Principles:**
- ✅ Read-only dashboard (no direct approve/merge/delete)
- ✅ Data immutable (no changes from dashboard)
- ✅ Human-in-the-loop enforced
- ✅ All decisions deferred to specialized review screens
- ✅ Current import batch only
- ✅ Audit-safe (complete decision history visible)

---

### 3. Possible Duplicates
**Route:** `/imports/<import_id>/duplicates`  
**Status:** Design Finalized, Needs Packaging  
**Purpose:** Side-by-side comparison interface for marking records as the same person

**Key Features:**
- **Side-by-side contact cards** (Contact A | Contact B) showing identical fields for easy comparison:
  - Email, Phone, Address, Name, Transaction history
- **Supporting Evidence panel**: Explicit list of matching indicators (e.g., "Email match", "Phone match", "Address match")
- **Conflicting Evidence panel**: Explicit list of conflicts (e.g., "Different address", "Different phone number")
- **Required reviewer reasoning**: When conflicting evidence exists, reviewer must enter notes before marking as same person (forces accountability)
- **Action buttons**:
  - "Mark as Same Person" (primary blue, enabled only when reviewer has provided reasoning if conflicts exist)
  - "Different Person" (secondary)
  - "Defer" (mark for later review)
- **Right-side drawer** (persistent context):
  - Duplicate Candidate Details
  - Import context
  - Related records
  - Transaction history
- **Audit logging**: Every decision (Same Person, Different, Defer) logged with timestamp, reviewer, decision type, and notes

**User Actions:**
- Review side-by-side contact comparison
- See supporting/conflicting evidence
- Provide reasoning if conflicts exist
- Mark as same person / different / defer
- View context in right drawer
- Proceed to next duplicate candidate

**Safety Principles:**
- ✅ **Decision-only** — "Mark as Same Person" records judgment only, doesn't merge anything
- ✅ **Current import only** — comparisons limited to same `import_id`
- ✅ **No cross-import intelligence** — no historical matching, no prior import context
- ✅ **No automatic merges** — reviewer must explicitly decide
- ✅ **Forced accountability** — if conflicts exist, reviewer must provide reasoning
- ✅ **No Givebutter writeback** — decisions stored locally in suggestion tables
- ✅ **Audit logged** — every decision tracked with timestamp, reviewer, decision type

---

### 4. All Records / Validation Review
**Route:** `/imports/<import_id>/validation`  
**Status:** In progress  
**Purpose:** Inspect every record in the batch; understand validation status; navigate to details

**Key Features:**
- **10-column table** (fixed): Selection, Transaction ID, Date, Name, Email, Phone, Amount, Address, Validation Status, Action
- **Compact, high-density design** for reviewing hundreds of records at once
- **Left sidebar filters**: Validation status, source file, confidence levels, date range, tags, assignment
- **Validation Status badges**: Green (Validation Passed), Amber (Needs Review), Red (Conflict Flagged)
- **Queue progress indicator**: Shows % of batch remaining for review
- **"Review Selected" button**: Only enabled when rows are selected; drives workflow to detail review
- **Export Warnings button**: Download report of all validation issues in batch

**User Actions:**
- Select rows (checkbox column)
- Filter and search
- View row details (click "Review Issues" link)
- Export warnings report

**Safety Principles:**
- ✅ Raw import rows never change from this screen
- ✅ Validation status is informational only
- ✅ No automatic fixes applied
- ✅ Reviewer decisions and row-level review actions are logged
- ✅ No CRM or Givebutter writeback

---

### 5. Normalization Review
**Route:** `/imports/<import_id>/normalizations`  
**Status:** In progress  
**Purpose:** Human review of suggested field normalization changes (e.g., "John Smith" → "John Q. Smith")

**Key Features:**
- **Suggestion-based interface**: System suggests cleanups; reviewer approves, rejects, or defers each one
- **Confidence scores**: Shows system's confidence in each suggestion (%, color-coded)
- **Card or table view** showing before/after for each normalization
- **Batch status sidebar**: Pending / Confirmed / Deferred / Rejected counts
- **Bulk actions**: Apply/reject selected suggestions
- **Audit logging**: Every decision logged with timestamp, reviewer, decision type

**User Actions:**
- Review suggested normalizations (one at a time or bulk)
- Confirm: Reflect suggestion in export staging
- Reject: Discard suggestion (raw data unchanged)
- Defer: Skip for now; may re-review later
- Filter by confidence, status, field type
- Selected decision actions: Confirm/reject/defer selected suggestions

**Safety Principles:**
- ✅ Suggestions affect **export staging only**, not raw import rows
- ✅ Raw rows immutable
- ✅ No automatic cleanup
- ✅ No Givebutter writeback
- ✅ Explicit approval required for each decision

---

### 6. Households Review
**Route:** `/imports/<import_id>/households`  
**Status:** In progress  
**Purpose:** Human review of system-suggested household groupings

**Key Features:**
- **Card-based interface** showing each suggested household:
  - Household name (system-generated)
  - Confidence score (e.g., "98% match")
  - Member list (names, emails, phones)
  - Suggested members with match confidence
- **Left sidebar**: Batch status, confidence threshold filter, status filter (Pending/Confirmed/Deferred/Rejected)
- **Action buttons per card**:
  - Confirm: Apply to export staging
  - Defer: Skip for later review
  - Reject: Don't group these members
- **Audit logging**: Every confirm/defer/reject decision logged

**User Actions:**
- Review each suggested household
- Confirm/defer/reject in-line (per card)
- Filter by confidence threshold
- View batch status (# pending, confirmed, deferred, rejected)

**Safety Principles:**
- ✅ Suggestions affect **export staging only**
- ✅ Raw rows never mutated
- ✅ No automatic household confirmation
- ✅ No CRM writeback
- ✅ No automatic contact merging
- ✅ Explicit reviewer intent required

---

### 7. Audit Log ✅ **ACCEPTED**
**Route:** `/imports/<import_id>/audit`  
**Status:** v1 Accepted / Ready for Implementation  
**Verification:** 49/49 checks passing  
**Purpose:** Comprehensive activity tracking for the entire batch; review all decisions made

**Key Features:**
- **6-column table**: Date/Timestamp, Reviewer & Action, Target, Notes, Audit Status, Action
- **Audit-safe language**: All action verbs use import-scoped, non-mutating language:
  - "marked as Same Person" (not "merged")
  - "rejected Household Link" (not "split")
  - "marked validation pass" (not "approved")
  - "ingested batch" (system action, not writeback)
- **Left sidebar filters**: Action Type, Reviewer, Date Range, Target ID search, Audit Status
- **Right sidebar** (optional): Row Audit History — drill down to see all actions on a specific row
- **System health indicators**: Integrity Score, Review Velocity, Pending Conflicts, Anomalies
- **Export button**: Download full audit trail as PDF for compliance

**User Actions:**
- Filter audit log (by reviewer, action, date, status)
- Search for specific rows
- View drill-down history per row
- Export audit trail
- Link to view full record context

**Safety Principles:**
- ✅ **Records decisions only**, not mutations
- ✅ Raw import rows **never changed** from audit actions
- ✅ All decisions **logged with timestamp, actor, decision, target**
- ✅ **Import-scoped references** (row ID, not master ID)
- ✅ **Transparent language** (marked, not merged; rejected, not deleted)
- ✅ **Human-in-the-loop verified** (all actions explicit)
- ✅ **Searchable and exportable** for compliance

**Canonical Vocabulary** (Enforced):
| Element | Safe Name | Example |
|---------|-----------|---------|
| Column header | Audit Status | ✅ |
| Status: Conflict | Conflict Flagged | ✅ |
| Status: Review needed | Needs Review | ✅ |
| Status: Valid | Validation Passed | ✅ |
| Status: System action | System Logged | ✅ |
| Action history panel | Row Audit History | ✅ |
| Export | Full Import Audit Report | ✅ |

---

### 8. Export Console ✅ **ACCEPTED**
**Route:** `/imports/<import_id>/exports`  
**Status:** v1 Accepted / Ready for Implementation  
**Verification:** 52/52 checks passing  
**Purpose:** Safe, reviewer-controlled export of prepared import data files

**Key Features:**
- **4 canonical export cards**:
  1. **Reviewed Export** (Generated): CSV with reviewer-confirmed duplicates & household links applied
  2. **Household Export** (Ready): Confirmed household groupings with member composition
  3. **Backlog Export** (Pending Review): Records with unresolved suggestions (⚠️ includes caution copy)
  4. **Raw Export** (Ready): Original data unchanged; no reviewer modifications (⚠️ includes caution copy)
- **Left sidebar filters**: Batch Status, Review Completion, Export Type, Date Range, Source File
- **Right sidebar** (optional): Export History — recent exports, counts, last generated date
- **Sticky action bar** (bottom): "Generate Export Package" button (triggers confirmation modal)
- **Safety banner** (top): "Review decisions logged | Raw import rows unchanged | Exports ready to download"
- **Footer guarantee**: "Raw rows never changed. Exports prepare files only. No data written back to Givebutter or any CRM. All actions logged."

**Export-Safe Language** (Enforced):
- ✅ "Generate Export Package" (not "Finalize")
- ✅ "Downloaded CSV" (not "synced")
- ✅ "prepared export" (not "CRM ingestion")
- ✅ "Generated" or "Ready" (not "FINALIZED")
- ✅ "No data is written back to Givebutter or any CRM" (explicit assurance)

**User Actions:**
- View 4 export card options
- Click "Generate Export Package" button
- Confirm in modal (non-dismissible)
- Download individual CSVs
- Filter/search recent exports
- View export history

**Safety Principles:**
- ✅ **Files for download only** — no automatic sync
- ✅ **Raw rows unchanged** — exports don't mutate source data
- ✅ **No external system integration** — no Givebutter or CRM writeback
- ✅ **Every action logged** — timestamp, actor, type, filename, metadata
- ✅ **Import-scoped only** — current batch only
- ✅ **Explicit control** — reviewer clicks "Generate", confirms in modal
- ✅ **Transparent messaging** — caution copy on Backlog & Raw; clear "no writeback" statement

---

## Design System Constants

### Navigation
All screens share a **consistent DonorTrust v1 top navigation bar**:
```
[DonorTrust] | Upload | Imports | Review | Matches | People | Households | Exports | Audit
```

Each screen activates its relevant tab (Review, Households, Exports, or Audit).

### Layout Pattern
All screens follow the **DonorTrust v1 layout**:
- **Top navigation** with active tab indicator
- **Safety banner** (prominent, always visible)
- **Left sidebar** with Data Controls and filters
- **Main content area** with page title, description, and core interface (table, cards, etc.)
- **Right sidebar** (optional) with historical data or supporting information
- **Sticky action bar** (if actions are primary workflow driver)
- **Footer** with safety guarantees or metadata

### Safety Strip Pattern
Every screen includes a compact **safety strip** below the title:
- All Records: "Suggested changes only. Raw import rows are never changed."
- Households: "Suggested changes only. Confirmed households affect export staging only. Raw import rows are never changed."
- Normalization: "Human-in-loop · Raw rows preserved · Approved suggestions affect export staging only"
- Audit Log: (implicit in design)
- Export Console: "Review decisions logged | Raw import rows unchanged | Exports ready to download"

### Vocabulary Rules

**Forbidden Terms** (Zero Tolerance):
- ❌ Master ID / Master database / Primary donor
- ❌ Merge / Merged (use "marked as Same Person")
- ❌ Auto-verified / Auto-apply / Apply all
- ❌ Sync / Synced / Syncing
- ❌ CRM writeback / CRM ingestion / Push to CRM
- ❌ Finalized / Permanent merge
- ❌ Entity audit / Donor history

**Safe Replacements**:
- ✅ Import row ID (not Master ID)
- ✅ "marked as Same Person" (not merged)
- ✅ "System Logged" (not auto-verified)
- ✅ "downloaded" or "exported" (not synced)
- ✅ "No data written back..." (explicit statement)
- ✅ "Generated" or "Ready" (not finalized)
- ✅ "Row Audit History" (not entity audit)

---

## Core Principles

### 1. Raw Row Immutability
**Definition:** The original import data is never changed by any reviewer decision.

**Enforcement:**
- All decisions affect **export staging only**
- Raw rows remain in original state
- Audit log records **decisions**, not mutations
- Every screen includes a safety message about this

### 2. Human-in-the-Loop
**Definition:** Reviewers make explicit decisions; no automatic apply.

**Enforcement:**
- All suggestions require explicit approval (confirm/reject/defer)
- No "apply all" or "approve all" buttons
- Every action logged with timestamp and actor
- Bulk actions only on explicitly selected items

### 3. Import-Scoped Operations
**Definition:** All work is isolated to the current import batch.

**Enforcement:**
- References use import row IDs (not master IDs)
- No cross-import matching
- No householding decisions across batches
- Each batch is independent

### 4. Audit Transparency
**Definition:** Every action is logged and queryable for compliance.

**Enforcement:**
- All reviewer decisions logged to audit trail
- Timestamps, actor, action, target, notes captured
- Full audit trail searchable and exportable
- Clear language about what happened and why

### 5. No External System Integration
**Definition:** This system prepares data; external systems are never updated.

**Enforcement:**
- Explicit messaging: "No data is written back to Givebutter or any CRM"
- Exports are files for download, not automatic sync
- No CRM integration language
- No writeback capabilities in UI

---

## UX Workflow Example

**Scenario:** A nonprofit imports 500 donor records from a CSV file.

### Step 1: Upload Givebutter CSV
Sarah visits the Givebutter import page and uploads a CSV file (`donor_data_q3.csv`).

She sees:
- File uploaded successfully
- Batch ID: #IMP-2023-0914-A
- Record count: 500
- Status: "Pending Review"

She can now navigate to the Import Dashboard to begin the review workflow, or return later.

### Step 2: Import Dashboard
Sarah opens the Import Dashboard and sees a status overview:
- **Batch #IMP-2023-0914-A**: 500 records
- **Duplicates pending**: 47 possible duplicate pairs
- **Validation issues**: 93 records with conflicts
- **Normalizations pending**: 8 field cleanup suggestions
- **Households pending**: 12 suggested groupings
- **Progress**: 12% complete (47/500 records reviewed so far)

She can see recent audit log entries from previous reviews and has quick-access buttons to jump to any review screen. She decides to start with duplicate review.

### Step 3: Possible Duplicates
Sarah clicks "Review Possible Duplicates" and enters the duplicate review interface.

The system shows the first duplicate pair:
- **Contact A**: John Smith, john.smith@email.com, (555) 123-4567, 123 Main St
- **Contact B**: John Smith, jsmith@email.com, (555) 123-4567, 123 Main Street

**Supporting Evidence**:
- ✓ Full name match
- ✓ Phone match
- ✓ Address match (minor formatting difference)

**Conflicting Evidence**:
- ✗ Email address different

Sarah reads the conflicting evidence (different email addresses) and enters a note: "Likely same person — email typo or alternate email address. Confirmed via donation pattern."

She clicks "Mark as Same Person" (button is enabled now that she provided reasoning for the conflict). The decision is logged.

She proceeds through the remaining 46 duplicate candidates, making decisions for each.

### Step 4: All Records / Validation Review
Sarah opens the Validation Review screen and sees:
- 500 records in a table
- 42 have "Validation Passed" (green)
- 78 have "Needs Review" (amber) — duplicate candidates
- 15 have "Conflict Flagged" (red) — validation errors
- Queue shows: 93 records remaining (18.6%)

Sarah filters to show only "Conflict Flagged" records and selects 5 that need immediate attention. She clicks "Review Selected (5)" to drill into details.

### Step 5: Normalization Review
The system has flagged 8 field normalization suggestions. Sarah clicks "Review Normalizations" from the dashboard.

She reviews suggestions:
- "john smith" → "John Smith" (capitalization)
- "555-1234" → "(555) 123-4567" (phone formatting)
- "" (empty email) → "(no email provided)" (standardization)

She confirms 6 suggestions for export staging and defers 2 for later review. The system logs each decision.

### Step 6: Households Review
The system suggests 12 household groupings based on matching logic. Sarah clicks "Review Households" from the dashboard.

She reviews each card:
- Suggested household: "Smith Family"
- Members: John Smith, Jane Smith, Bob Smith
- Confidence: 97%

She confirms the Smith household and defers 2 households for later review. Each decision is logged: "Sarah Lee confirmed Household #HH-2847 on Oct 25, 2023 14:22:15 GMT."

### Step 7: Audit Log Review
Before exporting, Sarah checks the audit log to ensure all decisions are recorded correctly.

She sees entries like:
- "Oct 25, 2023 14:22 — Sarah Lee marked as Same Person — #P-99281-X"
- "Oct 25, 2023 14:45 — Sarah Lee confirmed Household #HH-2847 — 3 members"
- "Oct 25, 2023 15:10 — System Logged selected normalization decisions — 6 suggestions confirmed for export staging"

All decisions are properly logged. She exports the audit trail as a PDF for compliance.

### Step 8: Export Console
Sarah is ready to export the cleaned data. She clicks the Exports tab and sees:

**Reviewed Export** (Generated)
- CSV with reviewer-confirmed duplicate decisions, household groupings, and normalization decisions reflected in export staging
- Ready to download
- "Ready for manual downstream import or review"

**Household Export** (Ready)
- Confirmed household groupings with member composition
- Ready to download

**Backlog Export** (Pending Review)
- 3 records with unresolved suggestions
- ⚠️ "For internal review only. Contains unresolved suggestions or pending reviewer decisions."

**Raw Export** (Ready)
- Original 500 records exactly as uploaded
- ⚠️ "Original uploaded CSV exactly as received. No reviewer decisions or staged changes included."

Sarah clicks "Generate Export Package" button. A confirmation modal appears:

```
Generate Export Package?

This will prepare download files for:
- Reviewed Export (CSV with reviewed decisions)
- Household Export (confirmed groupings)
- Backlog Export (unresolved items)
- Raw Export (original data)

Raw import rows will not be changed.
Exports are ready for download only.
This action will be logged to the audit trail.

[Cancel] [Generate Export Package]
```

Sarah clicks "Generate Export Package". The system logs the action. Files are prepared.

She downloads the Reviewed Export (500 clean records with all decisions applied) and the Household Export. She then uploads these files to her downstream system (CRM, database, etc.). **The audit trail clearly shows that DonorTrust only prepared files; it never wrote back to any external system.**

---

## Implementation Status

| # | Screen | Status | Verification | Ready? |
|---|--------|--------|--------------|--------|
| 1 | Upload Givebutter CSV | ✅ Implemented | — | ✅ |
| 2 | Import Dashboard | ✅ Design Final (Stitch iter-004) | — | ✅ Ready for Implementation |
| 3 | Possible Duplicates | ✅ Design Finalized | — | ⏳ Needs Packaging |
| 4 | All Records / Validation Review | In progress | — | ❌ |
| 5 | Normalization Review | In progress | — | ❌ |
| 6 | Households Review | In progress | — | ❌ |
| 7 | Audit Log | ✅ Accepted | 49/49 PASS | ✅ |
| 8 | Export Console | ✅ Accepted | 52/52 PASS | ✅ |

**Next Steps:**
1. ✅ Upload Givebutter CSV — Implemented
2. Implement Import Dashboard (use Stitch iteration-004 design as basis)
3. Package & implement Possible Duplicates (side-by-side comparison UI)
4. Implement All Records / Validation Review (table-based, 10 fixed columns)
5. Implement Normalization Review (suggestion approval interface)
6. Implement Households Review (card-based suggestion interface)
7. Implement Audit Log (7. Audit Log specification-ready)
8. Implement Export Console (8. Export Console specification-ready)
9. End-to-end integration testing across all 8 screens
10. Deployment

---

## Key Design Files

- **SCREEN_STATUS_INDEX.md** — Overview of all screens and acceptance status
- **audit-log-review/audit_log-spec.md** — Authoritative Audit Log specification
- **export-console-review/export_console-spec.md** — Authoritative Export Console specification
- **all-records-validation-review/all_records_validation_review-spec.md** — Specification for All Records screen
- **households-review/households_review-spec.md** — Specification for Households Review
- **normalization-review/normalization_review-spec.md** — Specification for Normalization Review

All specifications include:
- Core principle and safety constraints
- Detailed navigation and layout
- Column/card/field descriptions
- Vocabulary rules (safe/unsafe language)
- Acceptance criteria
- Visual design direction

---

**Summary Last Updated:** 2026-06-11  
**Created By:** Claude Code / Specification-First Workflow  
**Authority:** Individual screen specifications + verification reports
