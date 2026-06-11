# Audit Log Review — Refinement Plan

**Status:** Refinement requirements identified  
**Screen:** Audit Log (v1 Final)  
**Stitch Node ID:** Not used (local reference mock)  
**Authority:** audit_log-spec.md + design-reference.html  
**Approach:** Local implementation-reference mock (no Stitch API calls)

---

## 📋 Critical Changes Required

### 1. **Remove Unsafe Language: Master ID** (Replace with Import Row ID)
**Current:** References to "Master ID" or master entity concept  
**Replace with:** "Import Row ID" or just "#P-99281-X" format  
**Why:** v1 is import-scoped only; no master database concept  
**Example:** 
- ❌ "Master ID: 12345"
- ✅ "Target: #P-99281-X" (import row ID)

---

### 2. **Remove Unsafe Language: Master database** (Replace with Import Batch)
**Current:** References to "Master database" or "master records"  
**Replace with:** "Import batch" or "staging"  
**Why:** v1 operates on import-scoped rows, not a master database  
**Example:**
- ❌ "Applied to master database"
- ✅ "Confirmed for export staging"

---

### 3. **Remove Unsafe Language: primary donor profile** (Replace with Existing Contact)
**Current:** References to "primary donor profile" or "primary records"  
**Replace with:** "Existing contact" or "related contact" or no reference at all  
**Why:** v1 doesn't create or reference primary profiles  
**Example:**
- ❌ "Merged into primary donor profile"
- ✅ "Marked as Same Person (import row #P-99281-X)"

---

### 4. **Remove Unsafe Language: merge/merged** (Replace with Marked Same Person / Grouped)
**Current:** Language like "merged", "merge operation", "merged records"  
**Replace with:** "marked as Same Person", "grouped as", "confirmed as duplicate"  
**Why:** v1 doesn't merge; it marks decisions for export staging  
**Example:**
- ❌ "Alex Rivers merged record #99281 into master"
- ✅ "Alex Rivers marked as Same Person (#P-99281-X)"

---

### 5. **Remove Unsafe Language: auto-verified** (Replace with System Flagged / Suggested)
**Current:** References to "auto-verified", "automatic verification"  
**Replace with:** "system flagged", "system suggested", or "needs review"  
**Why:** v1 uses human-in-the-loop; no auto-verification  
**Example:**
- ❌ "AUTO VERIFIED (100%)"
- ✅ "System flagged for review"

---

### 6. **Remove Unsafe Language: entity audit** (Replace with Row Audit History)
**Current:** "entity audit", "entity audit trail"  
**Replace with:** "row audit history", "record audit trail", "decision log"  
**Why:** Vague term; v1 audits import rows, not entities  
**Example:**
- ❌ "Entity audit shows..."
- ✅ "Row audit history shows..."

---

### 7. **Remove Unsafe Language: CRM writeback** (Remove Entirely)
**Current:** References to "CRM writeback", "sync to CRM", "writeback"  
**Replace with:** (Remove entirely; not part of this screen)  
**Why:** v1 audit log does not perform CRM operations  
**Example:**
- ❌ "Decision will be written back to CRM"
- ✅ (Simply remove; don't mention)

---

### 8. **Remove Unsafe Language: sync** (Remove Entirely or Replace with Export)
**Current:** References to "sync", "syncing", "synced"  
**Replace with:** "Export staging" or (remove entirely)  
**Why:** v1 doesn't sync; it stages for export  
**Example:**
- ❌ "Synced to external system"
- ✅ "Confirmed for export staging" or (remove)

---

### 9. **Remove Unsafe Language: apply all / approve all** (Replace with Individual Decision Language)
**Current:** Any mention of "apply all", "approve all", "bulk approve"  
**Replace with:** Individual action language (e.g., "Confirm Household", "Mark as Reviewed")  
**Why:** v1 requires explicit, human reviewer decision per row  
**Example:**
- ❌ "Approve all 142 suggested matches"
- ✅ "Alex Rivers confirmed household link for 3 records" (individual decisions logged)

---

### 10. **Remove Unsafe Language: Master / Primary / Entity** (General Pass)
**Current:** Any remaining master/primary/entity references in table or descriptions  
**Replace with:** Import-scoped language (row, import, batch, staging, record)  
**Why:** Consistency; v1 is purely import-batch-scoped  
**Example:**
- ❌ "Primary donor information"
- ✅ "Import record information"

---

## ✅ Safety Strip & Footer

### Top of Table (Below Title)
```
Suggested changes only. Raw import rows are never changed.
```

### Footer (Below Pagination)
```
All actions are logged to the audit trail. Suggested changes affect export staging only. 
Raw import rows are never changed from this screen.
```

---

## ✅ Audit Log Entry Pattern

**Safe Language to Use:**
- "Alex Rivers marked as Same Person" → Import-scoped duplicate identification
- "Morgan Lee rejected Household Link for record" → Import-scoped household decision
- "Jordan Smith marked validation pass for row" → Import-scoped validation outcome
- "System ingested batch donors_q3.csv" → Batch operation
- "Reviewer decision recorded" → Generic decision logging
- "Row audit history" → Decision trail for specific import row

**Table Columns (6 total):**
1. Date/Timestamp (ISO with timezone)
2. Reviewer & Action (name/avatar + verb phrase, import-scoped)
3. Target (import row ID, e.g., #P-99281-X)
4. Notes (reviewer comment or system note)
5. Audit Status (badge: Conflict Flagged / Needs Review / Validation Passed / System Logged)
6. Action (link to view record detail)

---

## Status Taxonomy (Updated)

**Old v1-Unsafe Names → New v1-Safe Names**

| Old Name | New Name | Color | Use Case |
|----------|----------|-------|----------|
| CONFLICTED | Conflict Flagged | Red (#FEE2E2) | Row has data conflicts requiring reviewer resolution |
| VERIFICATION NEEDED | Needs Review | Amber (#FEF3C7) | Row requires human reviewer verification |
| AUTO VERIFIED | System Logged | Blue (#E0E7FF) | System operation logged (not human decision) |
| (New) | Validation Passed | Green (#DCFCE7) | Reviewer confirmed row is valid |

**Column Name Change:**
- OLD: "Conflict Status" 
- NEW: "Audit Status"

---

## 📊 Design Reference to Create

**File:** `design-reference.html`

**Sections:**
- [x] DonorTrust v1 top navigation (Audit tab active)
- [x] Left sidebar: Data Controls (Filters: Action Type, Reviewer, Date Range, Target Search, Audit Status)
- [x] Page title: "Audit Log (v1 Final)"
- [x] Page description (from spec)
- [x] Export PDF button
- [x] Safety strip: "Suggested changes only. Raw import rows are never changed."
- [x] Audit log table with 6 columns (Date/Timestamp, Reviewer & Action, Target, Notes, Audit Status, Action)
- [x] 8 sample entries using safe, import-scoped language
- [x] Pagination controls
- [x] Right sidebar: Row Audit History (optional, not "Donor History") with import row reference
- [x] System Health indicators (Integrity Score, Review Velocity, Pending Conflicts, Anomalies Detected)
- [x] Footer message
- [x] DonorTrust v1 styling (white/light gray background, subtle borders, color-coded status badges)

**V1 Vocabulary Changes Applied:**
- [x] Removed: "Master ID", "Master database", "primary donor profile" 
- [x] Removed: "merge/merged", "auto-verified", "entity audit", "CRM writeback", "sync", "apply all", "approve all"
- [x] Removed: "Donor History" (replaced with "Row Audit History")
- [x] Removed: "Conflict Status" column (replaced with "Audit Status")
- [x] Removed: Status values "CONFLICTED", "VERIFICATION NEEDED", "AUTO VERIFIED"
- [x] Added: Safe status labels "Conflict Flagged", "Needs Review", "Validation Passed", "System Logged"
- [x] All audit entries use safe language (marked as Same Person, rejected Household Link, marked validation pass, etc.)
- [x] All color-coded status badges with new safe names (red, amber, green, blue)

---

## 📸 Screenshots to Generate

1. **screenshot-2x-above-fold.png** (2880×1800px)
   - Captures: Navigation, page title, description, safety strip, table header, first 2-3 rows
   - Verification: All columns visible, layout correct, safe language present

2. **screenshot-2x-full.png** (2880×full height)
   - Captures: Entire page including bottom pagination, footer message, optional sidebar
   - Verification: Complete design review, all sections visible

---

## ✅ Acceptance Criteria

### Visual ✅
- [ ] DonorTrust navigation (Audit tab active)
- [ ] Left sidebar (Data Controls, filters)
- [ ] Page title and description present
- [ ] Export PDF button visible
- [ ] Audit log table with all 6 columns visible at 1440px
- [ ] Pagination controls present
- [ ] Right sidebar (Row Audit History) present if in design
- [ ] System Health indicators displayed
- [ ] Safety strip visible below title

### Safety ✅
- [ ] No "Master ID" language
- [ ] No "Master database" language
- [ ] No "primary donor profile" language
- [ ] No "merged" language (use "marked as Same Person" or "rejected Household Link")
- [ ] Only safe status names: Conflict Flagged, Needs Review, Validation Passed, System Logged
- [ ] No "CRM writeback" language
- [ ] No "sync" language
- [ ] No "entity audit" language
- [ ] No "apply all" or "approve all" language
- [ ] All targets use import row IDs (e.g., #P-99281-X)
- [ ] All actions reference import batch scope
- [ ] Safety strip present with correct message

### Functional ✅
- [ ] Filters work correctly (by action type, reviewer, date, status)
- [ ] Date range search works
- [ ] Target search works (by import row ID)
- [ ] Pagination works
- [ ] Export PDF generates compliance-ready document
- [ ] Timestamps are accurate
- [ ] Reviewer names/avatars display correctly
- [ ] Action descriptions are clear and import-scoped
- [ ] Notes field shows reviewer comments or system messages
- [ ] Conflict status badges are color-coded and accurate

---

## 🔒 Key Safety Guarantees

This design ensures:
- ✅ Raw import rows are **never mutated**
- ✅ Audit log records **decisions only**, not mutations
- ✅ Every reviewer action is **logged with timestamp, actor, decision, and target**
- ✅ All references are **import-scoped** (row ID, not master ID)
- ✅ Language is **transparent** (marked Same Person, not merged)
- ✅ Decisions are **human-in-the-loop verified**
- ✅ Full audit trail is **searchable and exportable for compliance**

---

## Timeline

1. ✅ Specification created (audit_log-spec.md)
2. → Create design-reference.html with safe language
3. → Generate 2x DPI screenshots
4. → Create verification.json (machine-readable checks)
5. → Create REFERENCE_MOCK_NOTES.md (explains local mock)
6. → Implementation in app code
7. → QA verification against spec
8. → Deployment

---

**Created:** 2026-06-11  
**Type:** Local refinement plan (not a Stitch update)  
**Authority:** audit_log-spec.md + this refinement plan  
**Status:** Ready for design-reference.html creation  
**Safety Level:** Audit-safe, import-scoped, human-verified
