# Export Console — v1 Design Reference Acceptance Record

**Date:** 2026-06-11  
**Screen:** Export Console  
**Status:** ✅ v1 Design Reference Accepted  
**Acceptance Level:** Ready for Production Implementation

---

## Screen Metadata

| Field | Value |
|-------|-------|
| **Screen Name** | Export Console |
| **Route** | `/imports/<import_id>/exports` |
| **Purpose** | Safe, reviewer-controlled export preparation and download with audit logging and no external system integration |
| **Version** | v1 Final |
| **Compliance** | Strict export-safe vocabulary (zero tolerance for unsafe language) |

---

## Authority & Artifacts

| Artifact | Status | Purpose |
|----------|--------|---------|
| **export_console-spec.md** | ✅ Authority | Source of truth for all design decisions (14 sections, 11 acceptance criteria) |
| **design-reference.html** | ✅ Reference | Visual/structural implementation reference (DonorTrust v1 local mock) |
| **verification.json** | ✅ 52/52 PASS | Machine-readable strict export-safe vocabulary verification |
| **README.md** | ✅ Documentation | Orientation guide for developers/designers |
| **REFINEMENT_PLAN.md** | ✅ Reference | Mapping of old-to-new vocabulary (migration guide) |
| **REFERENCE_MOCK_NOTES.md** | ✅ Documentation | Explanation of local reference mock approach |

---

## Verification Results

```
VERIFICATION SUMMARY
====================
Total Checks: 52
Passed: 52
Failed: 0
Pass Rate: 100%

COMPLIANCE BREAKDOWN
Forbidden Terms Found: 0/14 ✅
  (Zero tolerance enforced)
Required Safe Terms: 12/12 ✅
  (All canonical vocabulary present)

DESIGN STRUCTURE: ✅ PASS
- Navigation: DonorTrust v1
- Export Cards: 4 canonical types
- Safety Banner: Present with 3-item messaging
- Confirmation Modal: Non-dismissible, export-safe
- Sticky Action Bar: Generate Export Package button
- Footer: 4-item safety guarantee

EXPORT-SAFE LANGUAGE VERIFICATION: ✅ PASS
- All card names canonical ✅
- All action labels canonical ✅
- No external system language ✅
- No "sync/writeback/CRM" references ✅
- Explicit "No data written back..." messaging ✅
- Caution copy on Backlog & Raw ✅

SPECIFICATION ALIGNMENT: ✅ PASS
- All 11 acceptance criteria met
- All 10 safety constraints preserved
- v1 styling direction followed
```

---

## Canonical Vocabulary (Final & Enforced)

### Export Card Names
- ✅ **Reviewed Export** (CSV with reviewer decisions applied)
- ✅ **Household Export** (Confirmed groupings)
- ✅ **Backlog Export** (Unresolved suggestions)
- ✅ **Raw Export** (Original data unchanged)

### Action Labels
- ✅ **Download Reviewed CSV**
- ✅ **Download Household CSV**
- ✅ **Download Backlog CSV**
- ✅ **Download Raw CSV**
- ✅ **Generate Export Package** (button label, with confirmation modal)

### Status Badges
- ✅ **Generated** (blue)
- ✅ **Ready** (green)
- ✅ **Pending Review** (amber)

### Critical Safety Messages
- ✅ **Safety Banner:** "Review decisions logged | Raw import rows unchanged | Exports ready to download"
- ✅ **Footer:** "Raw import rows are never changed by exports. Exports prepare files for download only. No data is written back to Givebutter or any CRM. All export actions are logged to the audit trail."
- ✅ **Page Description:** "Prepare and download reviewed import data with logged reviewer decisions. Raw import rows remain unchanged. No data is written back to Givebutter or any CRM."

### Caution Copy (Required)
- ✅ **Backlog Export:** "For internal review only. Contains unresolved suggestions or pending reviewer decisions."
- ✅ **Raw Export:** "Original uploaded CSV exactly as received. No reviewer decisions or staged changes included."

---

## Forbidden Vocabulary (Zero Tolerance)

The following terms are **completely removed** from active UI/spec/reference copy:

| Forbidden | Why | Status |
|-----------|-----|--------|
| sync / synced / syncing | Implies continuous data flow to external system | ✅ Removed |
| CRM ingestion | v1 does not write to CRM | ✅ Removed |
| CRM writeback | v1 does not write to CRM | ✅ Removed |
| writeback | Implies external system data mutation | ✅ Removed |
| finalized / FINALIZED | Implies permanent mutation | ✅ Removed |
| apply all / approve all | v1 has no bulk export | ✅ Removed |
| auto-export / auto-apply | Exports are reviewer-triggered | ✅ Removed |
| master record / master database | No master concept in v1 | ✅ Removed |
| permanent merge | Exports don't mutate raw data | ✅ Removed |
| push to CRM | v1 does not push to external systems | ✅ Removed |
| destination | Can imply external system | ✅ Removed |
| downstream import (standalone) | Now qualified: "manual downstream import or review" | ✅ Qualified |

**Note:** Forbidden terms appear ONLY in:
- Forbidden language lists (properly labeled)
- Historical/old-to-new migration tables (explicitly labeled)
- Explanations of what we DO NOT do

---

## Safety Guarantees

✅ **Export File Preparation Only**
- Exports prepare downloadable CSV files
- No automatic sync to external systems
- No CRM integration or writeback

✅ **Raw Import Row Immutability**
- Raw import data never changes from this screen
- Export staging affects files only, not source

✅ **Audit Trail Completeness**
- Every export action logged with: timestamp, actor, export type, filename, metadata
- Searchable and exportable for compliance
- All reviewer decisions preserved

✅ **Human-in-the-Loop Control**
- Reviewer explicitly clicks "Generate Export Package"
- Confirmation modal prevents accidental exports
- Each export is deliberate, not automatic

✅ **Transparency**
- Clear messaging about export scope
- Caution copy on pending/original data
- Explicit "No data written back..." statement
- Full audit history available

---

## Design Structure Summary

### Top Navigation
- DonorTrust brand + tabs
- **Exports tab active**

### Safety Banner
- 3 items: Review decisions logged, Raw rows unchanged, Exports ready

### Left Sidebar (Data Controls)
- Batch Status filter
- Review Completion filter
- Export Type filter
- Date Range filter
- Source File filter

### Main Content
- Page title: "Export Console"
- Page description with safety messaging
- **4 export cards** (Reviewed, Household, Backlog, Raw)
- Each card: header + description + metadata + caution (if applicable) + footer + download button

### Sticky Action Bar (Bottom)
- Status display: "Ready to export | X files prepared | Last generated..."
- "Generate Export Package" button (triggers modal)
- Secondary actions: Audit Log link, Cancel

### Right Sidebar (Optional)
- **Export History** label
- Recent exports, counts, last generated date
- View Audit Log link

### Confirmation Modal
- Title: "Generate Export Package?"
- Body: Lists 4 export types + safety messaging
- Non-dismissible: Cancel or Confirm buttons only

---

## Implementation Requirements

✅ **Authority:** Follow `export_console-spec.md` exactly (not the HTML)  
✅ **Visual Reference:** Use `design-reference.html` for layout/styling guidance only  
✅ **Do Not Ship:** The static HTML directly; build in production component system  
✅ **Do Include:** All 4 export cards with canonical names  
✅ **Do Include:** All 5 action labels with exact text  
✅ **Do Include:** Right sidebar as "Export History"  
✅ **Do Implement:** Confirmation modal with export-safe messaging  
✅ **Do Verify:** Against 11 acceptance criteria before shipping  

---

## Sign-Off

```
Screen:           Export Console
Date Accepted:    2026-06-11
Verification:     52/52 checks passing
Vocabulary:       Strict export-safe compliance (zero unsafe terms)
Status:           ✅ v1 Design Reference Accepted
Ready For:        Production Implementation
Authority:        export_console-spec.md
Reference:        design-reference.html
Route:            /imports/<import_id>/exports
Core Guarantee:   Exports prepare downloadable files only. Raw rows unchanged. No data written back to Givebutter or any CRM.
Next:             Build in app code per spec requirements
```

---

**Document Type:** Formal Acceptance Record  
**Authority:** Specification + Verification  
**Next Update:** Upon completion of implementation or v2 planning
