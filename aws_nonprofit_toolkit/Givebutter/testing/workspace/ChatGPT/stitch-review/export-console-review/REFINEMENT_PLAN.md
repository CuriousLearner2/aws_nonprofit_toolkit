# Export Console — Refinement Plan

**Status:** Refinement requirements identified  
**Screen:** Export Console (v1 Final)  
**Type:** Local implementation-reference mock (not a Stitch update)  
**Authority:** export_console-spec.md + design-reference.html  
**Approach:** Specification-first, safe vocabulary enforcement

---

## Vocabulary Refinement (Old → New)

**Unsafe Language Replacement Table**

| Unsafe Term | Context | Replacement | Reason |
|----------|---------|-------------|--------|
| "Finalize Batch Export" | Button/action label | "Generate Export Package" | "Finalize" implies permanent mutation; "Generate" is import-scoped |
| "Export Clean" | Export card type label | "Reviewed Export" | "Clean" is vague; "Reviewed" is explicit about reviewer decisions |
| "Last sync" | Timestamp label | "Last generated" or "Last export" | "Sync" implies continuous data flow to external system |
| "donor CRM ingestion" | Feature description | "reviewed CSV output" or "manual downstream import/review" | v1 does not write to CRM |
| "Connected to Secure Audit Vault" | Status/feature | "Audit logging enabled" | Unless "Secure Audit Vault" is explicitly part of v1 infrastructure |
| "FINALIZED" | Status badge | "Generated" or "Ready" or "Reviewed Output" | "Finalized" implies permanent state |
| (Add clarity) | N/A | "No data is written back to Givebutter or any CRM" | New required message for safety |
| "apply all" / "approve all" | Hypothetical actions | (Remove entirely; individual downloads only) | v1 has no bulk export shortcuts |
| "auto-export" / "auto-apply" | Hypothetical features | (Not mentioned; exports are reviewer-triggered) | v1 requires explicit reviewer action |

---

## Core Vocabulary Definitions

### Export-Safe Language (Required)

| Concept | Safe Language | Usage |
|---------|---|--------|
| Creating export file | "generated export package" or "prepared export" | Timestamp, action log |
| Retrieving file | "downloaded CSV" or "exported to [filename]" | History, audit trail |
| Preparation complete | "export ready" or "export generated" | Status badges, messages |
| Records included | "included in export" or "staged for download" | Card descriptions |
| System operations | "export prepared" or "export file created" | Audit logging |

### Canonical Export Card Names (Enforced)

- ✅ **Reviewed Export** (not "Export Clean" or "Finalized Export")
- ✅ **Household Export** (not "Household Groups" or similar)
- ✅ **Backlog Export** (not "Pending Export" or "Unresolved Export")
- ✅ **Raw Export** (not "Original Export" or "Audit Export")

### Canonical Action Labels (Enforced)

- ✅ **Download Reviewed CSV**
- ✅ **Download Household CSV**
- ✅ **Download Backlog CSV**
- ✅ **Download Raw CSV**
- ✅ **Generate Export Package** (button label)

---

## Critical Safety Requirements

### 1. No External System Integration
- ❌ NO: "sync to CRM", "push to CRM", "CRM writeback"
- ❌ NO: "donor CRM ingestion", "CRM import"
- ✅ YES: "reviewed CSV output", "manual downstream import/review"
- **Why:** v1 exports are for download only; no automatic external system integration

### 2. No Permanent Mutations
- ❌ NO: "finalized", "permanent merge", "apply permanently"
- ✅ YES: "prepared for export", "staged for download", "generated"
- **Why:** Exports don't change raw import rows; they're files for reviewer download

### 3. Clear Givebutter/CRM Safety Message
- ✅ REQUIRED: "No data is written back to Givebutter or any CRM"
- **Location:** Page description + footer safety message
- **Prominence:** Visible, clear, unambiguous

### 4. Reviewer-Triggered Actions
- ❌ NO: "auto-export", "auto-apply", "apply all", "approve all"
- ✅ YES: Individual download buttons, confirmation modal
- **Why:** v1 requires explicit reviewer action for each export

### 5. Generate Export Package Modal
- ✅ REQUIRED: Confirmation modal before export generation
- **Title:** "Generate Export Package?"
- **Body:** Lists 4 export types + safety messaging
- **Non-dismissible:** Requires user action (Cancel or Confirm)

---

## Design Requirements (from Screenshot Inspiration)

### Preserved Structure
- ✅ Top navigation with Exports tab active
- ✅ Safety banner below navigation
- ✅ Main export cards (4 total)
- ✅ Right-side Export History panel
- ✅ Sticky bottom action bar
- ✅ Download buttons and action labels
- ✅ Audit/logging emphasis

### Safety Banner Content
```
✓ Review decisions logged  |  Raw import rows unchanged  |  Exports ready to download
```

### Card Structure (Each Card)
1. **Header:** Card title + status badge
2. **Description:** Clear purpose statement (1-2 lines)
3. **Metadata:** Files ready, date generated, size
4. **Caution Copy:** (Backlog & Raw only)
5. **Footer Copy:** "Exports ready for download. Raw import rows remain unchanged."
6. **Actions:** Download button + View link

### Caution Copy (Required)
- **Backlog Export:** "For internal review only. Contains unresolved suggestions or pending reviewer decisions."
- **Raw Export:** "Original uploaded CSV exactly as received. No reviewer decisions or staged changes included."

---

## Forbidden Language (Zero Tolerance)

**These terms must have 0 occurrences in active UI/spec/reference copy** (except in old-to-new migration tables):

- sync
- CRM ingestion
- CRM writeback
- writeback
- finalized / FINALIZED
- apply all
- approve all
- auto-export
- auto-apply
- master record
- master database
- permanent merge
- push to CRM
- "connected to vault" (unless explicitly part of v1 infrastructure)

---

## Verification Checklist

### Visual ✅
- [ ] Top navigation (Exports tab active)
- [ ] Safety banner visible below navigation
- [ ] Page title and description present
- [ ] 4 export cards visible (Reviewed, Household, Backlog, Raw)
- [ ] Each card has status badge and download button
- [ ] Right sidebar (Export History) visible
- [ ] Sticky action bar at bottom
- [ ] "Generate Export Package" button visible
- [ ] Modal appears when button clicked

### Safety ✅
- [ ] No "sync" language
- [ ] No "CRM ingestion" or "CRM writeback" language
- [ ] No "finalized" language (use "Generated" or "Ready")
- [ ] No "apply all" or "approve all" language
- [ ] No "auto-export" or "auto-apply" language
- [ ] No "push to CRM" language
- [ ] Clear message: "No data is written back to Givebutter or any CRM"
- [ ] All references import-scoped, not external systems
- [ ] Backlog caution copy present
- [ ] Raw caution copy present

### Functional ✅
- [ ] Filters work correctly
- [ ] Export cards display properly at 1440px viewport
- [ ] Download buttons visible and functional
- [ ] Modal opens when "Generate Export Package" clicked
- [ ] Modal has clear confirmation language
- [ ] Modal Cancel button closes modal
- [ ] Export History displays correctly
- [ ] Timestamps accurate
- [ ] All action descriptions clear and export-scoped

---

## Implementation Notes

### Do's
✅ Use the four canonical export card names exactly  
✅ Use canonical action labels exactly  
✅ Include the "No data is written back..." message  
✅ Add confirmation modal before export generation  
✅ Include caution copy on Backlog and Raw cards  
✅ Log all export actions to audit trail  
✅ Show safety banner prominently  

### Don'ts
❌ Don't use "Export Clean" or "Finalized Export"  
❌ Don't mention CRM integration or sync  
❌ Don't imply permanent mutations  
❌ Don't have bulk export actions (no "apply all")  
❌ Don't skip the confirmation modal  
❌ Don't remove safety messaging  

---

## Timeline

1. ✅ Specification created (export_console-spec.md)
2. ✅ Design reference created (design-reference.html) with safe vocabulary
3. → Create verification.json (machine-readable checks)
4. → Create REFERENCE_MOCK_NOTES.md (documentation)
5. → Implementation in app code
6. → QA verification against spec
7. → Deployment

---

**Created:** 2026-06-11  
**Type:** Local refinement plan (not a Stitch update)  
**Authority:** export_console-spec.md + this refinement plan  
**Status:** Ready for verification.json creation  
**Safety Level:** Export-safe, import-scoped, human-verified, no external system integration
