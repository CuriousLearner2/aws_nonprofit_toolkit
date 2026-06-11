# Audit Log — v1 Design Reference Acceptance Record

**Date:** 2026-06-11  
**Screen:** Audit Log  
**Status:** ✅ v1 Design Reference Accepted  
**Acceptance Level:** Ready for Production Implementation

---

## Screen Metadata

| Field | Value |
|-------|-------|
| **Screen Name** | Audit Log |
| **Route** | `/imports/<import_id>/audit` |
| **Purpose** | Comprehensive activity tracking for current import batch with audit-safe human-in-the-loop action history |
| **Version** | v1 Final |
| **Compliance** | Strict DonorTrust v1 vocabulary (zero tolerance for unsafe language) |

---

## Authority & Artifacts

| Artifact | Status | Purpose |
|----------|--------|---------|
| **audit_log-spec.md** | ✅ Authority | Source of truth for all design decisions (12 sections, 11 acceptance criteria) |
| **design-reference.html** | ✅ Reference | Visual/structural implementation reference (DonorTrust v1 local mock) |
| **verification.json** | ✅ 49/49 PASS | Machine-readable strict v1 vocabulary verification |
| **README.md** | ✅ Documentation | Orientation guide for developers/designers |
| **REFINEMENT_PLAN.md** | ✅ Reference | Mapping of old-to-new vocabulary (migration guide) |
| **REFERENCE_MOCK_NOTES.md** | ✅ Documentation | Explanation of local reference mock approach |

---

## Verification Results

```
VERIFICATION SUMMARY
====================
Total Checks: 49
Passed: 49
Failed: 0
Pass Rate: 100%

COMPLIANCE BREAKDOWN
Forbidden Terms Found: 0/15 ✅
  (Zero tolerance enforced)
Required Safe Terms: 12/12 ✅
  (All canonical vocabulary present)

DESIGN STRUCTURE: ✅ PASS
- Navigation: DonorTrust v1
- Table: 6 columns, 1440px viewport compatible
- Status Badges: 4 safe names (color-coded)
- Right Sidebar: Row Audit History
- Messaging: Safety strip + footer

SAFE LANGUAGE VERIFICATION: ✅ PASS
- All audit entries import-scoped ✅
- All targets use row IDs (not master IDs) ✅
- All action verbs safe ✅
- No master/primary/merge references ✅
- No auto-verified language ✅

SPECIFICATION ALIGNMENT: ✅ PASS
- All 11 acceptance criteria met
- All 8 safety constraints preserved
- v1 styling direction followed
```

---

## Accepted Vocabulary (Canonical)

### Status Names (Audit Status Column)
- ✅ **Conflict Flagged** (red) — Row has data conflicts requiring reviewer resolution
- ✅ **Needs Review** (amber) — Row requires human reviewer verification
- ✅ **Validation Passed** (green) — Reviewer confirmed row is valid
- ✅ **System Logged** (blue) — System operation logged (not human decision)

### Component Labels
- ✅ **Audit Status** (column header, not "Conflict Status")
- ✅ **Row Audit History** (right sidebar, not "Donor History")
- ✅ **Full Import Audit Report** (export, not "Full Entity Audit Report")
- ✅ **Export PDF** (also acceptable)

### Action Language (Safe Import-Scoped Verbs)
- ✅ marked as Same Person
- ✅ marked as Different Person
- ✅ marked as Deferred
- ✅ marked validation pass
- ✅ rejected Household Link
- ✅ confirmed Household Link
- ✅ flagged for [reason]
- ✅ ingested batch [filename]
- ✅ reviewed record [ID]

---

## Forbidden Vocabulary (Zero Tolerance)

The following terms are **completely removed** from active UI/spec/reference copy:

| Forbidden | Why | Replacement |
|-----------|-----|-------------|
| CONFLICTED | Unsafe status name | Conflict Flagged |
| VERIFICATION NEEDED | Unsafe status name | Needs Review / Validation Passed |
| AUTO VERIFIED | Unsafe status name | System Logged / Validation Passed |
| Conflict Status | Unsafe column label | Audit Status |
| Donor History | Unsafe sidebar label | Row Audit History |
| Full Entity Audit Report | Unsafe export label | Full Import Audit Report |
| Master ID | References non-existent master | Import row ID (e.g., #P-99281-X) |
| Master database | References non-existent master | Import batch / export staging |
| primary donor profile | References non-existent master | (Remove entirely) |
| merge / merged | Implies raw data mutation | marked as Same Person |
| auto-verified | Overstates system confidence | System Logged / Validation Passed |
| entity audit | Vague and unsafe | Row Audit History / audit trail |
| CRM writeback | Not part of v1 scope | (Remove entirely) |
| sync | Not part of v1 scope | export staging |
| apply all / approve all | No bulk approval in v1 | Individual decision per row |

**Note:** These terms appear ONLY in:
- Migration tables (explicitly labeled "Old → New")
- Historical documentation (clearly marked as stale)

---

## Safety Guarantees

✅ **Raw Import Row Immutability**
- Raw import data never changes from this screen
- Audit log records decisions only, not mutations

✅ **Audit Trail Completeness**
- Every reviewer action logged with timestamp, actor, decision, target
- Searchable and exportable for compliance

✅ **Human-in-the-Loop Verification**
- All decisions made by reviewers (not auto-applied)
- System provides context/flags, reviewers confirm/defer/reject

✅ **Import-Scoped Language**
- All references to import rows (not master entities)
- No CRM/sync/writeback implications
- Staged for export, not permanent mutations

✅ **Transparency**
- Action language clear and unambiguous
- Evidence displayed with conflicts shown
- Reviewer intent explicit (not hidden bulk operations)

---

## Design Structure Summary

### Top Navigation
- DonorTrust brand + tabs
- **Audit tab active**

### Left Sidebar (Data Controls)
- Action Type filter
- Reviewer filter
- Date Range filter
- Target Search (by import row ID)
- Audit Status filter

### Main Content
- Page title: "Audit Log (v1 Final)"
- Page description
- Export PDF button
- **Safety strip:** "Suggested changes only. Raw import rows are never changed."
- **Audit log table** (6 columns)
- **Pagination controls**

### Table Columns
1. Date/Timestamp (ISO format with timezone)
2. Reviewer & Action (name + import-scoped verb)
3. Target (import row ID)
4. Notes (reviewer comment or system message)
5. Audit Status (color-coded badge)
6. Action (link to details)

### Right Sidebar (Optional)
- **Row Audit History** label
- Reference ID
- Last Action timestamp
- Total Actions count
- Current Status
- Decision Timeline

### Bottom
- System Health Indicators (4 cards)
- **Footer message:** "All actions are logged to the audit trail. Suggested changes affect export staging only. Raw import rows are never changed from this screen."

---

## Implementation Requirements

✅ **Authority:** Follow `audit_log-spec.md` exactly (not the HTML)  
✅ **Visual Reference:** Use `design-reference.html` for layout/styling guidance only  
✅ **Do Not Ship:** The static HTML directly; build in production component system  
✅ **Do Include:** All 6 table columns with safe vocabulary  
✅ **Do Include:** All 4 safe status names with correct colors  
✅ **Do Include:** Right sidebar as "Row Audit History"  
✅ **Do Implement:** All filters and search functionality  
✅ **Do Verify:** Against 11 acceptance criteria before shipping  

---

## Sign-Off

```
Screen:           Audit Log
Date Accepted:    2026-06-11
Verification:     49/49 checks passing
Vocabulary:       Strict v1 compliance (zero unsafe terms)
Status:           ✅ v1 Design Reference Accepted
Ready For:        Production Implementation
Authority:        audit_log-spec.md
Reference:        design-reference.html
Next:             Build in app code per spec requirements
```

---

**Document Type:** Formal Acceptance Record  
**Authority:** Specification + Verification  
**Next Update:** Upon completion of implementation or v2 planning  
