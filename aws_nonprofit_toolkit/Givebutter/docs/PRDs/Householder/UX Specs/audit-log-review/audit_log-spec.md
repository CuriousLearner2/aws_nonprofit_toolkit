# DonorTrust v1 — Audit Log Screen

## Design + Implementation Specification

**Status:** Specification created  
**Screen:** Audit Log (v1 Final)  
**Primary purpose:** Comprehensive activity tracking for current import batch with audit-safe human-in-the-loop action history  
**Design approach:** Desktop-first, audit-safe language, transparent action logging  
**Visual style:** Consistent with DonorTrust v1

---

## 1. Core Principle

> Comprehensive activity tracking for the current import batch. Maintain institutional donor integrity through verified human-in-the-loop actions for DonorTrust v1.

**Core guarantee:** Every reviewer action is logged with timestamp, actor, decision, and target. Raw import rows remain unchanged. All actions are audit-traceable.

---

## 2. v1 Safety Constraints

The screen must preserve:

* All reviewer actions are logged to audit trail
* Timestamps are accurate and searchable
* Target records are clearly identified (import row ID, not master ID)
* Action descriptions do not use unsafe language:
  - ❌ NO: "Master ID", "Master database", "primary donor profile", "merge/merged"
  - ❌ NO: "auto-verified", "entity audit", "CRM writeback", "sync"
  - ❌ NO: "apply all", "approve all"
* Raw import rows are never changed from audit actions
* All data belongs to current import batch (import-scoped)
* Reviewer decisions are human-in-the-loop verified
* Full audit trail remains accessible for compliance

---

## 3. Navigation & Layout

### Top Navigation Bar

DonorTrust navigation with "Audit" tab active:

```
[DonorTrust] | Upload | Imports | Review | Matches | People | Households | Exports | Audit
```

### Left Sidebar

**Title:** Data Controls  
**Subtitle:** Audit-Safe Filtering

**Controls:**
- Filters (by action type, reviewer, etc.)
- Sources (by import file)
- Confidence (thresholds)
- Date Range (searchable)
- Tags
- Assignment

### Main Content Area

**Page Title:** Audit Log (v1 Final)

**Page Description:**
```
Comprehensive activity tracking for the current import batch. 
Maintain institutional donor integrity through verified human-in-the-loop actions for DonorTrust v1.
```

**Export Button:** "Export PDF" (for compliance/documentation)

---

## 4. Audit Log Table

### Columns

| Column | Purpose | Content |
|--------|---------|---------|
| **Date/Timestamp** | When action occurred | ISO format with timezone |
| **Reviewer & Action** | Who and what they did | Name/avatar + verb phrase (import-scoped) |
| **Target** | What was affected | Import row ID (not master ID) |
| **Notes** | Why/context | Reviewer comment or system note |
| **Audit Status** | Current review state indicator | Color-coded badge (green/amber/red) |
| **Action** | Access to details | Link to view full record |

### Sample Audit Log Entries

**Entry 1: Duplicate Candidate Review**
```
Date/Timestamp: Oct 24, 2023 14:22:15 GMT
Reviewer & Action: Alex Rivers marked as Same Person
Target: #P-99281-X
Notes: "Matching email and phone verified via internal database."
Status: Conflict Flagged (42%)
Action: [View]
```

Explanation: "marked as Same Person" is import-scoped (not "merged into primary donor profile").

**Entry 2: Household Link Rejection**
```
Date/Timestamp: Oct 24, 2023 13:05:44 GMT
Reviewer & Action: Morgan Lee rejected Household Link for record
Target: #H-44102-B
Notes: "Data collision on address field. Significant mismatch."
Status: Conflict Flagged (42%)
Action: [View]
```

**Entry 3: Record Validation Pass**
```
Date/Timestamp: Oct 23, 2023 16:48:02 GMT
Reviewer & Action: Jordan Smith marked validation pass for row
Target: #P-77611-M
Notes: "Duplicate identified from CSV import. Validated manually."
Status: Validation Passed (81%)
Action: [View]
```

Explanation: "marked validation pass" (not "merged Record #77611 into primary donor profile").

**Entry 4: Batch Ingestion (System)**
```
Date/Timestamp: Oct 23, 2023 15:16:33 GMT
Reviewer & Action: System ingested batch donors_q3.csv
Target: #B-88122-A
Notes: "Initial ingestion of 4,200 records successful."
Status: System Logged (100%)
Action: [View]
```

---

## 5. Audit-Safe Action Language

### DO USE (Import-Scoped)

| Action | Import-Scoped Language |
|--------|------------------------|
| Identifying duplicates | "marked as Same Person" or "marked as Different Person" |
| Deferring decisions | "marked as Deferred" |
| Field validation | "marked validation pass" or "marked needs review" |
| Household linking | "confirmed household link" or "rejected household link" |
| Batch operations | "ingested batch [filename]" |
| Record review | "reviewed record [ID]" |
| Data flagging | "flagged for [reason]" |

### DO NOT USE

| Unsafe Language | Why |
|-----------------|-----|
| "merged" | Implies raw data mutation |
| "primary donor profile" | References non-existent master entity |
| "Master ID" | No such concept in import scope |
| "auto-verified" | Overstates system confidence |
| "CRM writeback" | Not part of this screen |
| "sync" | Not part of this screen |
| "apply all" / "approve all" | No bulk approval patterns |
| "entity audit" | Vague and unsafe |

---

## 6. Right Sidebar: Row Audit History (Optional)

If present, display:
- Reference ID (import row ID)
- Timeline of actions on this specific row
- Data quality assessment
- Integrity details

**Important:** All references are to import rows, not "master donors" or "primary profiles".

---

## 7. Filtering & Search

### Filter Controls (Left Sidebar)

- **Action Type** (dropdown): All Actions, Marked Same Person, Marked Different Person, Marked Deferred, Validation Pass, Household Confirmed, Household Rejected, Flagged, etc.
- **Reviewer** (dropdown): All Staff Members, [names]
- **Date Range** (date picker): Last 30 Days, custom range
- **Target Search** (text): e.g., #P-99281 (import row ID)
- **Audit Status** (multi-select): Conflict Flagged, Needs Review, Validation Passed, System Logged

### Search Behavior

- Real-time filtering
- Pagination (1-25 of 1,248 records shown)
- Export filtered results

---

## 8. System Health Indicators (Optional, Bottom)

Display if relevant:

- **Integrity Score:** 98.4% (import batch quality)
- **Review Velocity:** 142/hr (audits per hour)
- **Pending Conflicts:** 38 batches (requiring review)
- **Anomalies Detected:** 0 (data quality)

**Important:** All metrics are import-batch-scoped, not system-wide.

---

## 9. Full Audit Report Export

**Button:** "Full Import Audit Report" or "Export PDF"

**Content:** Downloadable audit trail for the current import batch including:
- All actions taken by all reviewers
- Timestamps and actor information
- Target record IDs (import-scoped)
- Notes and decisions
- Compliance-ready format

---

## 10. Acceptance Criteria

The screen is ready when:

### Visual ✅
- [ ] DonorTrust navigation (Audit tab active)
- [ ] Left sidebar (Data Controls, filters)
- [ ] Page title and description present
- [ ] Export PDF button visible
- [ ] Audit log table with all columns visible
- [ ] Pagination controls present
- [ ] Right sidebar (Row Audit History) present if in design
- [ ] System Health indicators displayed

### Safety ✅
- [ ] No "Master ID" language
- [ ] No "Master database" language
- [ ] No "primary donor profile" language
- [ ] No "merged" language (use "marked Same Person" instead)
- [ ] No "auto-verified" language (use "System Logged" or "Validation Passed")
- [ ] No "CRM writeback" language
- [ ] No "sync" language
- [ ] No "apply all" or "approve all" language
- [ ] No "entity audit" language
- [ ] All targets use import row IDs (not master IDs)
- [ ] All actions reference import batch scope

### Functional ✅
- [ ] Filters work correctly
- [ ] Date range search works
- [ ] Target search works (by import row ID)
- [ ] Pagination works
- [ ] Export PDF generates compliance-ready document
- [ ] Timestamps are accurate
- [ ] Reviewer names/avatars display correctly
- [ ] Action descriptions are clear and import-scoped
- [ ] Notes field shows reviewer comments or system messages
- [ ] Audit Status badges are color-coded and accurate (Conflict Flagged, Needs Review, Validation Passed, System Logged)

---

## 11. Visual Design Direction

Use DonorTrust v1 style:

**Colors:**
- Background: White/light gray (#F5F5F5)
- Borders: Subtle gray (#E0E0E0)
- Text: Dark gray/black (#333, #000)
- Success/Verified: Green (#10B981)
- Warning/Needs Review: Amber (#F59E0B)
- Error/Conflicted: Red (#EF4444)

**Typography:**
- Title: Large, bold (24px)
- Body: Regular 14-16px
- Metadata: Small, muted (12-14px)

**Table:**
- Bordered rows
- Hover states
- Sticky header
- Clear column alignment

**Accessibility:**
- High contrast (WCAG AA)
- Clear focus states
- Keyboard navigation supported
- Screen reader friendly

---

## 12. Key Audit-Safe Decisions

1. **Import-Scoped Language Only**
   - All actions reference import rows, not master entities
   - No "master" or "primary" terminology
   - Decisions are for export staging, not permanent mutations

2. **Transparent Action History**
   - Every action logged with timestamp, actor, decision
   - Searchable and filterable
   - Exportable for compliance

3. **Human-in-the-Loop Verification**
   - All decisions made by reviewers
   - System provides context/flags, not decisions
   - Reviewer confirms, defers, or rejects

4. **Raw Row Immutability**
   - Audit log records decisions about import rows
   - Raw import data never changes from this screen
   - Staging affects only export, not source

---

**Created:** 2026-06-11  
**Status:** ✅ Specification Complete  
**Authority:** This specification + reference artifacts  
**Safety Level:** Audit-safe, import-scoped, human-verified
