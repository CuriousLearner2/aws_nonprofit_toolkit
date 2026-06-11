# DonorTrust v1 — Export Console Screen

## Design + Implementation Specification

**Status:** Specification created  
**Screen:** Export Console (v1 Final)  
**Primary purpose:** Safe, reviewer-controlled export of prepared import data files with audit logging and no data mutation  
**Design approach:** Desktop-first, export-safe language, transparent action logging, no CRM/Givebutter writeback  
**Visual style:** Consistent with DonorTrust v1

---

## 1. Core Principle

> The system prepares export files. The reviewer chooses what to download. Raw import rows remain unchanged. No data is written back to Givebutter or any CRM.

**Core guarantee:** Every export action is logged with timestamp, actor, export type, filename, and generated file metadata. Raw import rows remain unchanged. Exports affect downloadable files only. All reviewer decisions are preserved in export staging.

---

## 2. v1 Safety Constraints

The screen must preserve:

* All export actions are logged to audit trail
* Timestamps are accurate and searchable
* Export packages are clearly identified (import ID, type, date generated)
* Action descriptions do not use unsafe language:
  - ❌ NO: "sync", "CRM ingestion", "CRM writeback", "writeback"
  - ❌ NO: "finalized", "apply all", "approve all", "auto-export", "auto-apply"
  - ❌ NO: "master record", "master database", "permanent merge", "push to CRM"
  - ❌ NO: "connected to vault" (unless explicitly part of v1 infrastructure)
* Raw import rows are never changed from export actions
* All data belongs to current import batch (import-scoped)
* Exports affect downloadable files only, not external systems
* Reviewer decisions are human-in-the-loop verified
* Clear messaging: "No data is written back to Givebutter or any CRM"
* Full audit trail remains accessible for compliance

---

## 3. Navigation & Layout

### Top Navigation Bar

DonorTrust navigation with "Exports" tab active:

```
[DonorTrust] | Upload | Imports | Review | Matches | People | Households | Exports | Audit
```

### Safety Banner

Below navigation, above main content:

```
✓ Review decisions logged  |  Raw import rows unchanged  |  Exports ready to download
```

### Left Sidebar

**Title:** Data Controls  
**Subtitle:** Export Filtering

**Controls:**
- Filters (by batch status, review completion, export type)
- Date Range (searchable)
- Import Sources (by file)
- Review Status (by completion level)

### Main Content Area

**Page Title:** Export Console

**Page Description:**
```
Prepare and download reviewed import data with logged reviewer decisions.
Raw import rows remain unchanged. No data is written back to Givebutter or any CRM.
```

**Export Cards:** 4 canonical types

---

## 4. Export Cards (Main Content)

### Card Structure (Each Card)

**Header**
- Export type name (Reviewed Export, Household Export, etc.)
- Status badge (Generated, Ready, Pending Review)
- Metadata: files ready, date generated, size

**Description Section**
- Purpose of this export (1-2 lines)
- Data contents (what records included, any filtering applied)
- Key indicators (e.g., "Contains X contacts in Y households")

**Caution Copy (if applicable)**
- Backlog Export: "For internal review only. Contains unresolved suggestions or pending reviewer decisions."
- Raw Export: "Original uploaded CSV exactly as received. No reviewer decisions or staged changes included."

**Action Row**
- Download button (primary blue)
- View Details link
- Status indicator

**Footer Copy**
- "Exports ready for download. Raw import rows remain unchanged."

### Canonical Export Cards

#### 1. Reviewed Export
**Purpose:** Contacts with finalized reviewer decisions applied to export staging.  
**Description:** CSV export with all reviewer-confirmed duplicates, household links, and validation decisions applied. Ready for manual downstream import or review.  
**Badge:** Generated  
**Action:** Download Reviewed CSV

#### 2. Household Export
**Purpose:** Household groupings with confirmed members per import-scoped decisions.  
**Description:** CSV with suggested households confirmed by reviewers. Contains household IDs, member counts, and composition.  
**Badge:** Generated  
**Action:** Download Household CSV

#### 3. Backlog Export
**Purpose:** Records with unresolved suggestions or pending decisions.  
**Description:** Contacts where reviewers deferred decisions or conflicts remain. Requires additional review before manual downstream import or review.  
**Caution Copy:** "For internal review only. Contains unresolved suggestions or pending reviewer decisions."  
**Badge:** Pending Review  
**Action:** Download Backlog CSV

#### 4. Raw Export
**Purpose:** Original uploaded data without any reviewer modifications.  
**Description:** Exact CSV as originally uploaded. No reviewer decisions or staged changes included. Useful for audit/comparison purposes.  
**Caution Copy:** "Original uploaded CSV exactly as received. No reviewer decisions or staged changes included."  
**Badge:** Ready  
**Action:** Download Raw CSV

---

## 5. Export-Safe Action Language

### DO USE (Export-Scoped)

| Action | Safe Language |
|--------|---|
| Creating export package | "generated export package" or "prepared export" |
| Retrieving download | "downloaded CSV" or "exported to [filename]" |
| Batch preparation | "prepared export for download" or "staged for export" |
| Completion | "export ready" or "export generated" |
| Record inclusion | "included in export" or "staged for download" |
| System operations | "export prepared" or "export file created" |

### DO NOT USE

| Unsafe Language | Why |
|-----------------|-----|
| "sync" | Implies continuous data flow to external system |
| "CRM ingestion" or "CRM writeback" | v1 does not write to CRM |
| "finalized" | Implies permanent mutation (use "generated" or "ready") |
| "apply all" / "approve all" | No bulk export patterns; each export is deliberate |
| "master record" / "master database" | No master concept in v1 |
| "permanent merge" | Exports don't mutate raw rows |
| "auto-export" / "auto-apply" | Exports are reviewer-triggered, not automatic |
| "push to CRM" | v1 does not push to external systems |
| "connected to vault" | Unless explicitly part of v1 infrastructure; otherwise use "audit logging enabled" |

---

## 6. Right Sidebar: Export History (Optional)

If present, display:
- Most recent exports (timestamp, type, status, download link)
- Export count by type
- Last generation date
- Audit trail link

**Important:** All references are to imports and staged exports, not "master" or "production" systems.

---

## 7. Sticky Bottom Action Bar

**Location:** Fixed at bottom of viewport

**Primary Action:**
- **Button:** "Generate Export Package"
- **Icon:** Download + arrow
- **Color:** Primary blue
- **Behavior:** Opens confirmation modal
- **Accessibility:** High contrast, clear focus state

**Secondary Actions:**
- View Audit Log (text link)
- Cancel / Close (text link)

**Status Display:**
- "Ready to export" or "X files prepared"
- Last generated timestamp
- Export count this batch

---

## 8. Generate Export Package Modal

**Trigger:** User clicks "Generate Export Package" button

**Modal Title:**
```
Generate Export Package?
```

**Modal Body:**
```
This will prepare download files for:
- Reviewed Export (CSV with reviewed decisions)
- Household Export (confirmed groupings)
- Backlog Export (unresolved items)
- Raw Export (original data)

Raw import rows will not be changed.
Exports are ready for download only.
This action will be logged to the audit trail.
```

**Modal Buttons:**
- Cancel (secondary)
- Generate Export Package (primary blue)

**Behavior:** Non-dismissible (requires user action or explicit cancel)

---

## 9. Footer / Safety Messaging

**Location:** Below export cards, above sticky action bar

**Footer Copy:**
```
✓ Raw import rows are never changed by exports.
✓ Exports prepare files for download only.
✓ No data is written back to Givebutter or any CRM.
✓ All export actions are logged to the audit trail.
```

---

## 10. Filtering & Search (Left Sidebar)

### Filter Controls

- **Batch Status** (dropdown): All, Complete, In Review, Pending
- **Review Completion** (dropdown): All, Fully Reviewed, Partially Reviewed
- **Export Type** (multi-select): Reviewed, Household, Backlog, Raw
- **Date Range** (date picker): Last 30 Days, custom range
- **Source File** (text): e.g., donors_q3.csv (import row ID)

### Search Behavior

- Real-time filtering
- Pagination (1-10 of X exports shown)
- Export filtered results list

---

## 11. Acceptance Criteria

The screen is ready when:

### Visual ✅
- [ ] DonorTrust navigation (Exports tab active)
- [ ] Left sidebar (Data Controls, filters)
- [ ] Page title and description present
- [ ] Safety banner visible below navigation
- [ ] 4 export cards visible (Reviewed, Household, Backlog, Raw)
- [ ] Each card has clear status badge and action button
- [ ] Right sidebar (Export History) present if in design
- [ ] Sticky bottom action bar present with "Generate Export Package" button
- [ ] Export modal visible when button clicked
- [ ] Footer safety messaging present

### Safety ✅
- [ ] No "sync" language
- [ ] No "CRM ingestion" or "CRM writeback" language
- [ ] No "finalized" language (use "generated" or "ready")
- [ ] No "apply all" or "approve all" language
- [ ] No "master record" or "master database" language
- [ ] No "auto-export" or "auto-apply" language
- [ ] No "push to CRM" language
- [ ] All targets reference import batches (not external systems)
- [ ] Clear message: "No data is written back to Givebutter or any CRM"
- [ ] All export actions reference import-scoped changes only

### Functional ✅
- [ ] Filters work correctly
- [ ] Date range search works
- [ ] Generate Export Package button opens modal
- [ ] Modal has clear confirmation language
- [ ] Download buttons work (or placeholder for demo)
- [ ] Export History displays correctly
- [ ] Timestamps are accurate
- [ ] All export cards visible and clickable
- [ ] Action descriptions are clear and export-scoped
- [ ] Notes field shows export metadata

---

## 12. Visual Design Direction

Use DonorTrust v1 style:

**Colors:**
- Background: White/light gray (#F5F5F5)
- Borders: Subtle gray (#E0E0E0)
- Text: Dark gray/black (#333, #000)
- Success/Ready: Green (#10B981)
- Warning/Pending: Amber (#F59E0B)
- Neutral/Generated: Blue (#2563EB)

**Typography:**
- Title: Large, bold (24px)
- Body: Regular 14-16px
- Metadata: Small, muted (12-14px)

**Cards:**
- White background, subtle shadow
- Hover states
- Clear visual hierarchy
- Action buttons prominent

**Accessibility:**
- High contrast (WCAG AA)
- Clear focus states
- Keyboard navigation supported
- Screen reader friendly

---

## 13. Key Export-Safe Decisions

1. **No External System Integration**
   - Exports prepare files for download only
   - No automatic sync to Givebutter, CRM, or vault
   - Reviewer explicitly downloads files

2. **Import-Scoped Exports**
   - All exports reference current import batch
   - No "master" or "production" system language
   - Exports are staging, not permanent writes

3. **Transparent File Preparation**
   - Every export action logged (timestamp, type, size, status)
   - Searchable export history
   - Audit trail shows who downloaded what and when

4. **Human-in-the-Loop Control**
   - Reviewer triggers each export explicitly
   - Confirmation modal prevents accidental exports
   - No bulk export shortcuts (each batch deliberate)

5. **Raw Row Immutability**
   - Exports prepare files, don't change raw import rows
   - Reviewer decisions staged for export, not applied to source
   - Downloads affect files only, not external systems

---

## 14. Export Status Definitions

**Generated:** Export package prepared and ready for download (no pending actions required)

**Ready:** All reviewer decisions complete; export can be generated immediately

**Pending Review:** Some reviewer decisions outstanding; backlog items unresolved

**Audit Ready:** Review decisions logged, export files prepared, audit trail complete

---

**Created:** 2026-06-11  
**Status:** ✅ Specification Complete  
**Authority:** This specification + reference artifacts  
**Safety Level:** Export-safe, import-scoped, human-verified, no external system integration
